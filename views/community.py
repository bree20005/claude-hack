"""PRD 6: Community page — stories sorted by tags, "Women like you", and member profiles.

Members are synthetic (data/members.json) and labeled; published stories (PRD 5) show
first. Anyone can message a member; replies are AI-simulated in that member's voice
(views/messages.py), and the UI says so.
"""

from __future__ import annotations

import streamlit as st

import data
import nav
import ui
from views.publish import story_card_html


def _viewer_tags() -> dict | None:
    return st.session_state.get("mp_tags")


@st.dialog("Her story", width="large")
def _story_dialog(story: dict, highlight: list[str]) -> None:
    st.html(story_card_html(story, highlight=highlight, full=True))
    m = data.member_by_id(story.get("member_id", "")) if story.get("member_id") else None
    if m:
        path = " → ".join(f'{ui.esc(s["step"])} <span class="rb-muted">({ui.esc(s["duration"])})</span>' for s in m.get("path", []))
        helps = "".join(ui.pill(h, "small white") for h in m.get("can_help_with", []))
        st.html(
            f'<div class="rb-stack" style="gap:10px;margin-top:8px"><p class="rb-small rb-strong">Her path</p>'
            f'<p class="rb-small">{path}</p>'
            f'<p class="rb-small rb-strong">She can help with</p><div class="rb-row" style="gap:6px">{helps}</div>'
            f'<p class="rb-small rb-muted">{ui.esc(m["city"])} · {ui.esc(m["availability"])} · {ui.esc(m["last_active"])}</p></div>'
        )
        if st.button(f"Message {m['first_name']}", type="primary", key=f"dlg_msg_{m['id']}"):
            nav.open_thread(m["id"])
            st.rerun()
    tags = _viewer_tags()
    if tags and set(story["industry_tags"]) & set(tags["industry"]) and st.session_state.get("mp_matches"):
        t = next(iter(set(story["industry_tags"]) & set(tags["industry"])))
        if st.button(f"See jobs in {data.tag_label(t)}", key="dlg_jobs"):
            st.session_state["mp_stage"] = "matches"
            nav.go("my_path")
            st.rerun()


def _card(story: dict, key: str, highlight: list[str] | None = None, why: str = "") -> None:
    with st.container(key=f"plain_story_{key}"):
        member = data.member_by_id(story.get("member_id", "")) if story.get("member_id") else None
        meta = ""
        if member:
            mentor = (f'<span class="rb-pill small mint">Mentor · helped {member["women_helped"]}</span>'
                      if member.get("mentor") else "")
            meta = (f'<div class="rb-row" style="gap:8px;margin:-6px 0 0 4px">{mentor}'
                    f'<span class="rb-small rb-muted" style="font-size:14px">● {ui.esc(member["last_active"])} · '
                    f'{ui.esc(member["city"])}</span></div>')
        why_html = f'<p class="rb-small" style="color:var(--rb-primary);font-weight:700;margin:0 0 -6px 4px">{ui.esc(why)}</p>' if why else ""
        st.html(why_html + story_card_html(story, highlight=highlight) + meta)
        with st.container(horizontal=True, gap="small"):
            if st.button("Read more", key=f"read_{key}", type="tertiary"):
                _story_dialog(story, highlight or [])
            if member:
                st.button(f"Message {member['first_name']}", key=f"msg_{key}", type="tertiary",
                          on_click=nav.open_thread, args=(member["id"],))


def _grid(stories: list[dict], prefix: str, highlight: list[str] | None = None) -> None:
    for i in range(0, len(stories), 2):
        cols = st.columns(2, gap="medium")
        for col, s in zip(cols, stories[i:i + 2]):
            with col:
                _card(s, f"{prefix}_{s['id']}", highlight)


def render(user: dict) -> None:
    stories = data.all_stories(viewer_id=user["email"])
    members = data.load_members()
    ui.page_intro("Community", "Stories from women who've been there.",
                  "Real paths into real work. Every journey is different.")

    mentors = sum(1 for m in members if m.get("mentor"))
    active = sum(1 for m in members if m.get("last_active") in ("Active now", "Active today"))
    helped = sum(m.get("women_helped", 0) for m in members)
    st.html(
        '<div class="rb-row" style="gap:12px;margin-bottom:8px">'
        f'<span class="rb-pill bold">{len(stories)} stories</span>'
        f'<span class="rb-pill lav bold">{mentors} mentors</span>'
        f'<span class="rb-pill mint">● {active} active today</span>'
        f'<span class="rb-pill white">{helped} women helped by mentors</span></div>'
    )
    if sum(s["synthetic"] for s in stories) > len(stories) / 2:
        st.html('<div class="rb-notice" style="margin-bottom:12px"><p class="rb-small">Many stories and member profiles '
                "here are examples written to show what's possible (marked “Example story”), and replies from members are "
                "AI-simulated for this demo. Real stories from our community are marked as such and growing.</p></div>")

    # deep link: open a story (PRD 6 §5.6)
    open_id = st.session_state.pop(nav.OPEN_STORY_KEY, None)
    if open_id:
        target = next((s for s in stories if s["id"] == open_id), None)
        if target:
            _story_dialog(target, [])
        else:
            st.toast("That story isn't available anymore.")

    mine = [s for s in stories if s.get("is_mine")]
    if mine:
        st.html('<p class="rb-serif rb-h3" style="margin-top:12px">Your story</p>')
        _card(mine[0], "mine")
        with st.popover("Delete my story"):
            if st.button("Yes, delete it", key="comm_delete"):
                data.delete_story(user["email"])
                st.session_state.pop("mp_published", None)
                st.toast("Your story has been deleted.")
                st.rerun()

    tags = _viewer_tags()
    if tags:
        scored = sorted(((data.tag_overlap(tags, s), s) for s in stories if not s.get("is_mine")),
                        key=lambda x: -x[0])
        top = [(sc, s) for sc, s in scored if sc > 0][:3]
        if top:
            st.html('<p class="rb-serif rb-h3" style="margin-top:16px">Women like you</p>')
            cols = st.columns(len(top), gap="medium")
            mine_all = tags["industry"] + tags["experience"]
            for col, (_, s) in zip(cols, top):
                shared = [t for t in s["industry_tags"] + s["experience_tags"] if t in mine_all]
                with col:
                    _card(s, f"like_{s['id']}", highlight=shared,
                          why="Also: " + " · ".join(data.tag_label(t) for t in shared))

    st.html('<p class="rb-serif rb-h3" style="margin-top:20px">All stories</p>')
    options = [t["id"] for t in data.industry_tags()]
    st.session_state.setdefault(nav.COMMUNITY_TAGS_KEY, [])
    st.session_state[nav.COMMUNITY_TAGS_KEY] = [t for t in st.session_state[nav.COMMUNITY_TAGS_KEY] if t in options]
    selected = st.pills("Filter by kind of work", options, selection_mode="multi", format_func=data.tag_label,
                        key=nav.COMMUNITY_TAGS_KEY) or []
    shown = [s for s in stories if not selected or set(s["industry_tags"]) & set(selected)]
    label = (f"{len(shown)} stories" if not selected else
             f"{len(shown)} {'story' if len(shown) == 1 else 'stories'} in {', '.join(data.tag_label(t) for t in selected)}")
    c1, c2 = st.columns([4, 1], vertical_alignment="center")
    c1.html(f'<p class="rb-small rb-muted">{label}</p>')
    if selected:
        c2.button("Clear filters", type="tertiary", key="comm_clear",
                  on_click=lambda: st.session_state.update({nav.COMMUNITY_TAGS_KEY: []}))
    if shown:
        _grid(shown, "all", highlight=selected)
    else:
        st.html(f'<div class="rb-notice"><p class="rb-small">No stories in {ui.esc(", ".join(data.tag_label(t) for t in selected))} '
                "yet.</p></div>")

    st.html('<div class="rb-card" style="margin-top:28px;flex-direction:row;justify-content:space-between;align-items:center">'
            '<div class="rb-stack"><p class="rb-serif" style="font-size:26px">Found your footing? Share your journey.</p>'
            '<p class="rb-small rb-muted">Your story could be exactly what another woman needs to read. '
            "We remove anything that could identify you, and you approve every word.</p></div></div>")
    if st.button("Share my journey", type="primary", key="comm_share"):
        from views import my_path
        my_path.reset_all()
        st.session_state["mp_persona"] = "sharer"
        nav.go("my_path")
        st.rerun()
    ui.footer()
