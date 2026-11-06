"""PRD 5: story publishing for sharers (privacy check -> edit & preview -> consent -> publish).

Only the final approved public fields are stored (data.publish_story). Raw answers and
the `removed` list stay in this session only and are never saved.
"""

from __future__ import annotations

import streamlit as st

import data
import llm
import nav
import ui


def story_card_html(s: dict, highlight: list[str] | None = None, preview: bool = False, full: bool = False) -> str:
    """Shared StoryCard (PRD 6); `preview=True` is the PRD 5 live preview."""
    highlight = highlight or []
    badges = ""
    if s.get("is_mine"):
        badges += '<span class="rb-pill small mint">Your story</span>'
    if s.get("synthetic"):
        badges += '<span class="rb-pill small white" style="font-weight:600">Example story</span>'
    journey = s.get("journey", "")
    if not full and not preview and len(journey) > 260:
        journey = journey[:260].rsplit(" ", 1)[0] + "…"
    tags = "".join(
        f'<span class="rb-pill small {"" if t in highlight else "lav"}" style="{"font-weight:800" if t in highlight else ""}">'
        f"{ui.esc(data.tag_label(t))}</span>"
        for t in s.get("industry_tags", []) + s.get("experience_tags", [])
    )
    advice = (f'<div class="rb-panel"><p class="rb-small rb-semibold">Her advice</p>'
              f'<p class="rb-small">“{ui.esc(s["advice"])}”</p></div>') if s.get("advice") else ""
    return (
        '<div class="rb-card">'
        f'<div class="rb-row" style="gap:14px;flex-wrap:nowrap">{ui.avatar(s.get("display_name") or "A", 48)}'
        f'<div class="rb-stack" style="gap:2px;flex:1"><p class="rb-serif" style="font-size:22px">{ui.esc(s.get("display_name") or "Anonymous")}</p>'
        f'<p class="rb-small rb-muted">{ui.esc(s.get("current_job", ""))}</p></div>'
        f'<div class="rb-row" style="gap:6px">{badges}</div></div>'
        f'<p class="rb-small" style="white-space:pre-wrap">{ui.esc(journey)}</p>{advice}'
        f'<div class="rb-row" style="gap:6px">{tags}</div></div>'
    )


def _display_names(user: dict) -> list[str]:
    parts = [p for p in (user.get("name") or "").split() if p]
    first = parts[0] if parts else "Friend"
    last_i = parts[1][0].upper() if len(parts) > 1 else ""
    opts = [first]
    if last_i:
        opts += [f"{first} {last_i}.", f"{first[0].upper()}.{last_i}."]
    else:
        opts += [f"{first[0].upper()}."]
    return opts + ["Anonymous"]


def render(user: dict) -> None:
    ss = st.session_state
    author = user["email"]
    if ss.get("mp_published"):
        _confirmation(user)
        return

    ui.page_intro("My Story / Publish", "Your story, ready to share.",
                  "Review every word. Nothing is public until you publish.", eyebrow_muted=True)
    existing = data.my_story(author)
    if existing:
        st.info("You already have a story on Rebloom. Publishing will replace it.")

    if "mp_anon" not in ss:
        with st.spinner("Writing your story…"):
            draft = llm.anonymize({k: v for k, v in ss.mp_answers.items() if v})
        ss.mp_anon = draft
        ss.mp_pub_job = draft["current_job"]
        ss.mp_pub_journey = draft["journey"]
        ss.mp_pub_advice = draft["advice"]
    removed = ss.mp_anon.get("removed", [])

    edit, preview = st.columns(2, gap="large")
    with edit:
        if removed:
            items = " · ".join(f'{ui.esc(r["type"].capitalize())} ({ui.esc(r["original"])})' for r in removed)
            st.html('<div class="rb-panel"><p class="rb-small rb-strong">We removed details that could identify you</p>'
                    f'<p class="rb-small">{items}</p><p class="rb-small rb-muted" style="font-size:14px">These are never saved.</p></div>')
        name = st.radio("Display name", _display_names(user), key="mp_pub_name", horizontal=True)
        job = st.text_input("Current job", key="mp_pub_job", max_chars=60)
        journey = st.text_area("Your story", key="mp_pub_journey", height=280)
        st.caption(f"{len(journey.split())} words · aim for 150–250")
        advice = st.text_area("Advice for the next woman", key="mp_pub_advice", height=90)
        tags = ss.mp_tags["industry"] + ss.mp_tags["experience"]
        st.html('<p class="rb-small rb-strong">Tags</p><div class="rb-row" style="gap:6px">'
                + "".join(ui.pill(data.tag_label(t), "small") for t in tags) + "</div>")
        with st.container(horizontal=True, gap="small"):
            st.button("Edit tags", key="mp_pub_tags", on_click=lambda: ss.update(mp_stage="tags"))
            with st.popover("Rewrite it for me"):
                st.write("Replace your edits with a fresh draft?")
                if st.button("Yes, rewrite", key="mp_pub_rewrite"):
                    for k in ("mp_anon", "mp_pub_job", "mp_pub_journey", "mp_pub_advice"):
                        ss.pop(k, None)
                    st.rerun()

    story = {"display_name": name, "current_job": job, "journey": journey, "advice": advice,
             "industry_tags": ss.mp_tags["industry"], "experience_tags": ss.mp_tags["experience"]}
    with preview:
        st.html('<p class="rb-small rb-strong">Preview: how it will look on the community page</p>')
        st.html(story_card_html({**story, "is_mine": True}, preview=True))

    # identifier warning (client-side check, PRD 5 §6.3)
    reintroduced = [r["original"] for r in removed
                    if len(r["original"]) > 2 and any(r["original"].lower() in f.lower() for f in (job, journey, advice))]
    keep_ok = True
    for orig in reintroduced:
        keep_ok = st.checkbox(f"“{orig}” could identify you. Keep it anyway?", key=f"mp_keep_{orig}") and keep_ok

    valid = bool(job.strip()) and 50 <= len(journey.split()) <= 350 and len(advice.split()) <= 80 and bool(ss.mp_tags["industry"])
    consent = st.checkbox("I understand my story will be public on Rebloom. I can delete it anytime.", key="mp_consent")
    if st.button("Publish my story", type="primary", disabled=not (consent and valid and keep_ok), key="mp_publish"):
        if user.get("guest"):
            st.warning("Guest mode saves nothing. Log in with a phone or email to publish your story.")
        else:
            rec = data.publish_story(author, story)
            ss.mp_published = rec["id"]
            st.rerun()
    if not valid:
        st.caption("Your story needs a current job, 50–350 words, short advice, and at least one industry tag.")
    ui.footer()


def _confirmation(user: dict) -> None:
    ss = st.session_state
    ui.page_intro("My Story", "Your story is live.",
                  "Thank you. Your journey could be exactly what another woman needs to read.")
    story = data.my_story(user["email"])
    if story:
        st.html(story_card_html({**story, "is_mine": True}, full=True))
    with st.container(horizontal=True, gap="small"):
        st.button("View it on the community page", type="primary", key="mp_view_story",
                  on_click=nav.go, args=("community",), kwargs={"story": ss.mp_published})
        with st.popover("Delete my story"):
            st.write("Delete your story from Rebloom? This can't be undone.")
            if st.button("Yes, delete it", key="mp_delete_story"):
                data.delete_story(user["email"])
                ss.pop("mp_published", None)
                st.toast("Your story has been deleted.")
                st.rerun()
        if st.button("Start over", key="mp_pub_restart"):
            from views import my_path
            my_path.reset_all()
            st.session_state.pop("mp_persona", None)
            st.rerun()
    ui.footer()
