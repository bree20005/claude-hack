"""My Path / My Story: the shared intake and what follows it.

Stages (st.session_state["mp_stage"]):
  chat    -> PRD 2 conversational intake (Claude asks one question at a time)
  review  -> PRD 2 "Here's what I heard" (editable)
  tags    -> PRD 3 summary + tags with reasons (add / remove)
  matches -> PRD 4 job matches (seeker)            publish -> PRD 5 (sharer, views/publish.py)
  letter  -> PRD 8 cover letter (seeker)

All state is in st.session_state under `mp_*` keys (cleared by Start over / Sign out).
Seekers' answers are never stored anywhere else.
"""

from __future__ import annotations

import hashlib
import json
from urllib.parse import quote_plus

import streamlit as st

import data
import llm
import nav
import prompts as P
import ui
from views import publish

DEFAULT_LOCATION = "San Francisco, CA"

# PRD 2 section 11: demo scripts
DEMO_REPLIES = {
    "seeker": [
        "I worked in the jail kitchen for 3 years. Before that I cleaned offices on a crew for about a year.",
        "About 200 people every morning, breakfast and lunch.",
        "Yes, I trained the new girls and I did the inventory count every week.",
        "I got out last month. I have check-ins every Tuesday morning.",
        "I need about $20 an hour, as soon as I can.",
        "I have two kids and no car, so daytime hours somewhere near the bus.",
        "I'm proud I kept my family together through all of it.",
        "No, that's it. Thank you.",
    ],
    "sharer": [
        "I worked in the jail kitchen, started on dishes and ended up running the breakfast line.",
        "After I got out it took me about 4 months to get hired. I applied everywhere.",
        "I needed around $18 an hour back then to cover rent with my sister.",
        "I needed day shifts and I took two buses to get anywhere.",
        "I'm good at staying calm when it gets busy, and teaching new people.",
        "I'm a line cook now, two years at the same restaurant.",
        "A county culinary training program helped me put my kitchen time on paper and practice interviews.",
        "Don't give up after the no's. Every rejection got me closer. Write down everything you did inside.",
        "No, that's everything.",
    ],
}
EXAMPLE_ANSWERS = {
    "seeker": {
        "past_work": "Before, I cleaned offices on a crew for about a year.",
        "inside_work": "I worked in the jail kitchen for 3 years. We cooked for about 200 people every morning. I trained the new women and did the weekly inventory count.",
        "timeline": "I got out last month. I have check-ins every Tuesday morning.",
        "money": "I need about $20 an hour, as soon as I can.",
        "needs": "I have two kids and no car, so I need daytime hours somewhere near the bus.",
        "strengths": "I'm proud I kept my family together. I'm reliable and I show up.",
    },
    "sharer": {
        "inside_work": "I worked in the jail kitchen. I started on dishes and ended up running the breakfast line.",
        "timeline": "It took me about 4 months to get hired after I got out.",
        "money": "I needed about $18 an hour back then.",
        "needs": "I needed day shifts and took two buses to get anywhere.",
        "strengths": "I stay calm when it's busy and I'm good at teaching new people.",
        "current_job": "I'm a line cook now, two years at the same restaurant.",
        "how_got_there": "A county culinary training program helped me put my kitchen time on paper and practice interviews.",
        "advice": "Don't give up after the no's. Write down everything you did inside. It counts.",
    },
}


# --- state ------------------------------------------------------------------------
def persona() -> str:
    return st.session_state.get("mp_persona", "seeker")


def first_name(user: dict) -> str:
    n = user.get("name") or ""
    return "" if user.get("guest") or n in ("Friend", "Guest") else n.split()[0]


def _init(user: dict) -> None:
    ss = st.session_state
    if "mp_msgs" in ss:
        return
    name = first_name(user)
    ss.mp_stage = "chat"
    ss.mp_msgs = [{"role": "assistant", "content": P.OPENING[persona()].format(name=f" {name}" if name else "")}]
    ss.mp_covered = []
    ss.mp_qr = P.OPENING_REPLIES[persona()]
    ss.mp_ready = False
    ss.mp_crisis = False
    ss.mp_answers = {}


def reset_all() -> None:
    for k in [k for k in st.session_state.keys() if str(k).startswith("mp_") and k != "mp_persona"]:
        st.session_state.pop(k, None)


def _minimum_met(covered_or_answers) -> bool:
    keys = set(covered_or_answers)
    ok = bool(keys & {"past_work", "inside_work"}) and len(keys) >= 2
    if persona() == "sharer":
        ok = ok and "current_job" in keys
    return ok


def _answers_contract() -> dict:
    """PRD 0 Answers: topic id -> {question, answer}."""
    return {k: {"question": P.topic_label(persona(), k), "answer": v}
            for k, v in st.session_state.get("mp_answers", {}).items() if v and v.strip()}


def _go(stage: str) -> None:
    st.session_state.mp_stage = stage


# --- render -------------------------------------------------------------------------
def render(user: dict) -> None:
    _init(user)
    if st.session_state.get("llm_error"):
        st.warning(st.session_state.pop("llm_error"))
    stage = st.session_state.mp_stage
    if stage == "review":
        _review(user)
    elif stage == "tags":
        _tags(user)
    elif stage == "matches":
        _matches(user)
    elif stage == "letter":
        _letter(user)
    elif stage == "publish":
        publish.render(user)
    else:
        _chat(user)


# --- PRD 2: chat ------------------------------------------------------------------------
def _send(user: dict, text: str) -> None:
    ss = st.session_state
    text = text.strip()[:1000]
    if not text:
        return
    ss.mp_msgs.append({"role": "user", "content": text})
    out = llm.intake_turn(persona(), first_name(user), ss.mp_msgs, ss.mp_covered)
    ss.mp_msgs.append({"role": "assistant", "content": out["reply"]})
    ss.mp_covered = out["topics_covered"]
    ss.mp_qr = out["quick_replies"]
    ss.mp_crisis = out.get("crisis", False)
    if out.get("ready_to_finish") and _minimum_met(ss.mp_covered) and not ss.mp_crisis:
        ss.mp_ready = True


def _finish(user: dict, example: bool = False) -> None:
    ss = st.session_state
    if example:
        ss.mp_answers = dict(EXAMPLE_ANSWERS[persona()])
    else:
        name = first_name(user)
        ss.mp_msgs.append({"role": "assistant",
                           "content": f"Thank you{', ' + name if name else ''}. Give me a moment to put this together…"})
        with st.spinner("Putting your story together…"):
            ss.mp_answers = llm.extract_answers(persona(), ss.mp_msgs, EXAMPLE_ANSWERS[persona()])
    _go("review")


def _progress_html(covered: list[str]) -> str:
    topics = P.TOPICS[persona()]
    chips = "".join(
        f'<span class="rb-pill small {"" if tid in covered else "white"}" style="font-weight:700">'
        f'{"✓ " if tid in covered else ""}{ui.esc(label)}</span>' for tid, label, _ in topics
    )
    return (f'<div class="rb-stack" style="align-items:flex-end;gap:10px">{ui.petals(len(covered), len(topics))}'
            f'<div class="rb-row" style="gap:6px;justify-content:flex-end">{chips}</div></div>')


def _chat(user: dict) -> None:
    ss = st.session_state
    _, mid, _ = st.columns([200, 820, 200])
    with mid:
        head, prog = st.columns([1, 1.3], vertical_alignment="top")
        with head:
            eyebrow = "My Path / Your story" if persona() == "seeker" else "My Story / Share your journey"
            title = "In your own words." if len(ss.mp_msgs) < 3 else "Let's keep going."
            st.html(f'<div class="rb-stack" style="gap:6px"><p class="rb-eyebrow muted">{eyebrow}</p>'
                    f'<p class="rb-serif rb-h2">{title}</p></div>')
        with prog:
            st.html(_progress_html(ss.mp_covered))

        who = first_name(user) or "You"
        st.html('<div class="rb-stack" style="gap:22px;margin-top:8px" aria-live="polite">' + "".join(
            ui.chat_bubble("user" if m["role"] == "user" else "bot", who if m["role"] == "user" else "Rebloom", m["content"])
            for m in ss.mp_msgs) + "</div>")

        if ss.mp_crisis:
            st.info("If you're in crisis, you can call or text **988** (Suicide & Crisis Lifeline) any time. "
                    "We can pick this up whenever you're ready.")

        if ss.mp_ready:
            _finish(user)
            st.rerun()

        # quick replies (PRD 2): tapping sends it as her message
        if ss.mp_qr and not ss.mp_crisis:
            with st.container(horizontal=True, gap="small", key="plain_qr"):
                for i, q in enumerate(ss.mp_qr):
                    if st.button(q, key=f"mp_qr_{len(ss.mp_msgs)}_{i}"):
                        with st.spinner(" "):
                            _send(user, q)
                        st.rerun()

        with st.container(horizontal=True, gap="small"):
            if _minimum_met(ss.mp_covered):
                if st.button("I'm done", type="primary", key="mp_done"):
                    _finish(user)
                    st.rerun()
            with st.popover("Start over"):
                st.write("Clear this conversation and start again?")
                if st.button("Yes, start over", key="mp_restart_confirm"):
                    reset_all()
                    st.rerun()

        with st.expander("Demo shortcuts"):
            script = DEMO_REPLIES[persona()]
            n_user = sum(1 for m in ss.mp_msgs if m["role"] == "user")
            demo_name = "Maria" if persona() == "seeker" else "Denise"
            if n_user < len(script):
                if st.button(f"Send {demo_name}'s next reply: “{script[n_user][:60]}…”", key="mp_demo_next"):
                    with st.spinner(" "):
                        _send(user, script[n_user])
                    st.rerun()
            if st.button(f"Skip to review with {demo_name}'s example", key="mp_demo_skip"):
                _finish(user, example=True)
                st.rerun()

    text = st.chat_input("Answer in your own words…", key="mp_composer", max_chars=1000)
    if text:
        with st.spinner(" "):
            _send(user, text)
        st.rerun()


# --- PRD 2: review ------------------------------------------------------------------------
def _review(user: dict) -> None:
    ss = st.session_state
    _, mid, _ = st.columns([200, 820, 200])
    with mid:
        ui.page_intro("My Path / Review" if persona() == "seeker" else "My Story / Review", "Here's what I heard.",
                      "Change anything that isn't quite right. These are your words.", eyebrow_muted=True)
        for tid, label, _ in P.TOPICS[persona()]:
            with st.container(key=f"card_ans_{tid}"):
                st.html(f'<p class="rb-small rb-strong">{ui.esc(label)}</p>')
                if tid in ss.mp_answers or ss.get(f"mp_add_{tid}"):
                    ss.mp_answers[tid] = st.text_area(label, value=ss.mp_answers.get(tid, ""), key=f"mp_ans_{tid}",
                                                      label_visibility="collapsed", height=100)
                else:
                    c1, c2 = st.columns([4, 1], vertical_alignment="center")
                    c1.html('<p class="rb-small rb-muted">Not covered</p>')
                    if c2.button("Add", key=f"mp_addbtn_{tid}"):
                        ss[f"mp_add_{tid}"] = True
                        st.rerun()
        use = "find jobs that fit you" if persona() == "seeker" else \
              "draft your story, which you'll review before anything is published"
        st.html(f'<p class="rb-small rb-muted">Your answers are only used to {use}. We don\'t save them.</p>')
        ok = _minimum_met([k for k, v in ss.mp_answers.items() if v and v.strip()])
        with st.container(horizontal=True, gap="small"):
            st.button("Continue", type="primary", key="mp_review_continue", disabled=not ok,
                      on_click=_go, args=("tags",))
            st.button("Something's off? Go back to the chat", key="mp_back_chat", on_click=_go, args=("chat",))
        if not ok:
            need = "work before or work inside, plus one more topic"
            if persona() == "sharer":
                need += ", and the work you do now"
            st.caption(f"To continue, add {need}.")
    ui.footer()


# --- PRD 3: tags -----------------------------------------------------------------------------
def _answers_hash() -> str:
    return hashlib.sha1(json.dumps(st.session_state.mp_answers, sort_keys=True).encode()).hexdigest()


def _ensure_tags() -> None:
    ss = st.session_state
    if ss.get("mp_tags_hash") == _answers_hash() and "mp_tags" in ss:
        return
    with st.spinner("Reading your story…"):
        out = llm.tag_profile(_answers_contract(), data.load_tags())
    ind = [t for t in out.get("industry", []) if t["id"] in data.valid_industry([t["id"]])][:4]
    exp = [t for t in out.get("experience", []) if t["id"] in data.valid_experience([t["id"]])]
    text = " ".join(ss.mp_answers.values()).lower()
    if not any(w in text for w in ("recovery", "sober", "clean and sober", "recuperación")):
        exp = [t for t in exp if t["id"] != "in-recovery"]
    seen = set()
    ss.mp_tags = {"industry": [t["id"] for t in ind if not (t["id"] in seen or seen.add(t["id"]))],
                  "experience": [t["id"] for t in exp if not (t["id"] in seen or seen.add(t["id"]))]}
    ss.mp_reasons = {t["id"]: t["reason"] for t in ind + exp}
    ss.mp_summary = out.get("summary", "")
    ss.mp_skills = out.get("skills", [])[:8]
    ss.mp_explines = out.get("experience_lines", [])
    ss.mp_tags_hash = _answers_hash()
    ss.pop("mp_matches", None)


def _tag_group(group: str, title: str, limit: int | None) -> None:
    ss = st.session_state
    st.html(f'<p class="rb-serif" style="font-size:22px;margin-top:8px">{title}</p>')
    current = ss.mp_tags[group]
    if not current and group == "industry":
        st.info("Help us out: which of these kinds of work interest you?")
    cols = st.columns(2, gap="small")
    for i, tid in enumerate(list(current)):
        with cols[i % 2]:
            with st.container(key=f"lavsm_tag_{tid}"):
                c1, c2 = st.columns([6, 1], vertical_alignment="top")
                c1.html(f'<div class="rb-stack" style="gap:4px">{ui.pill(data.tag_label(tid), "bold")}'
                        f'<p class="rb-small rb-muted" style="font-size:15px">{ui.esc(ss.mp_reasons.get(tid, ""))}</p></div>')
                if c2.button("✕", key=f"mp_rm_{tid}", help=f"Remove {data.tag_label(tid)}"):
                    ss.mp_tags[group].remove(tid)
                    st.toast(f"Removed {data.tag_label(tid)}.")
                    st.rerun()
                if tid == "in-recovery" and persona() == "sharer":
                    st.caption("This will be visible on your story. Keep it?")
    pool = data.industry_tags() if group == "industry" else data.experience_tags()
    remaining = [t for t in pool if t["id"] not in current]
    full = limit is not None and len(current) >= limit
    with st.popover("+ Add more", disabled=not remaining):
        if full:
            st.caption(f"Up to {limit}. Remove one to add another.")
        for t in remaining:
            if st.button(t["label"], key=f"mp_add_tag_{t['id']}", disabled=full, help=t.get("description")):
                ss.mp_tags[group].append(t["id"])
                ss.mp_reasons[t["id"]] = "Added by you."
                st.rerun()


def _tags(user: dict) -> None:
    _ensure_tags()
    ss = st.session_state
    _, mid, _ = st.columns([160, 900, 160])
    with mid:
        ui.page_intro("Your experience", "Here's how we'd describe your experience.", eyebrow_muted=True)
        skills = "".join(ui.pill(s) for s in ss.mp_skills)
        st.html(f'<div class="rb-card" style="gap:14px"><p class="rb-body">{ui.esc(ss.mp_summary)}</p>'
                f'<div class="rb-row" style="gap:8px">{skills}</div></div>')
        _tag_group("industry", "Industries that fit you", 4)
        _tag_group("experience", "Your experience", None)
        if persona() == "sharer":
            st.html('<p class="rb-small rb-muted" style="margin-top:12px">These tags will appear on your public '
                    "story. Remove any you'd rather keep private.</p>")
        ok = bool(ss.mp_tags["industry"])
        with st.container(horizontal=True, gap="small"):
            if persona() == "seeker":
                st.button("See my job matches", type="primary", disabled=not ok, key="mp_to_matches",
                          on_click=_go, args=("matches",))
            else:
                st.button("Next: review your story", type="primary", disabled=not ok, key="mp_to_publish",
                          on_click=_go, args=("publish",))
            if st.button("Not quite right? Try again", key="mp_regen"):
                ss.pop("mp_tags_hash", None)
                st.rerun()
            st.button("Back to my answers", key="mp_tags_back", on_click=_go, args=("review",))
        if not ok:
            st.caption("Pick at least one industry.")
    ui.footer()


# --- PRD 4: matches ----------------------------------------------------------------------------
def _ensure_matches() -> None:
    ss = st.session_state
    key = json.dumps([ss.mp_tags, ss.mp_tags_hash], sort_keys=True)
    if ss.get("mp_matches_key") == key and "mp_matches" in ss:
        return
    candidates = data.jobs_for_tags(ss.mp_tags["industry"])
    with st.spinner("Finding jobs that fit you…"):
        out = llm.match_jobs(_answers_contract(), ss.mp_tags, ss.mp_summary, candidates)
    cand = {j["soc"]: j for j in candidates}
    picked, seen = [], set()
    for m in out.get("matches", []):
        if m.get("soc") in cand and m["soc"] not in seen:
            seen.add(m["soc"])
            picked.append(m)
    for j in sorted(candidates, key=lambda j: j.get("job_zone") or 9):  # fill to 3
        if len(picked) >= 3:
            break
        if j["soc"] not in seen:
            seen.add(j["soc"])
            reasons = [ss.mp_reasons.get(t) for t in data.job_industry_tags(j) if ss.mp_reasons.get(t)]
            picked.append({"soc": j["soc"], "why_it_fits": (reasons[0] + ".") if reasons else "Your experience fits this kind of work.",
                           "first_step": "Search openings near you and mention your hands-on experience."})
    floor = out.get("pay_floor_hourly")
    enriched = []
    for m in picked[:5]:
        j = dict(cand[m["soc"]])
        j.update(m)
        w = j.get("ca_median_hourly")
        j["below_pay_floor"] = bool(floor and w and w < floor)
        enriched.append(j)
    enriched.sort(key=lambda j: j["below_pay_floor"])  # stable: Claude's order, below-floor last
    ss.mp_matches, ss.mp_payfloor, ss.mp_matches_key = enriched, floor, key


def _matches(user: dict) -> None:
    _ensure_matches()
    ss = st.session_state
    name = first_name(user)
    st.html('<div class="rb-stack" style="gap:12px;margin:8px 0 16px 0">'
            '<p class="rb-eyebrow rb-sage" style="font-size:14px">My Path · Results</p>'
            f'<p class="rb-serif rb-h1">Jobs that fit your experience{", " + ui.esc(name) if name else ""}.</p></div>')
    tags = "".join(ui.pill(data.tag_label(t), "bold") for t in ss.mp_tags["industry"])
    floor = (f'<p class="rb-small rb-strong">Looking for about ${ss.mp_payfloor:.0f}/hour.</p>' if ss.mp_payfloor else "")
    exp = "".join(f'<p class="rb-small">{ui.esc(e)}</p>' for e in ss.get("mp_explines", []))
    left, right = st.columns([3, 1], vertical_alignment="top")
    with left:
        st.html('<div class="rb-card" style="gap:14px"><p class="rb-serif rb-h3">What you bring</p>'
                f'<p class="rb-small">{ui.esc(ss.mp_summary)}</p>'
                '<p class="rb-small rb-sage">Draft from your story: keep what feels true and change anything that doesn’t.</p>'
                f'<div class="rb-row" style="gap:8px">{tags}</div>{floor}'
                f'<div class="rb-stack"><p class="rb-small rb-semibold">Your work experience</p>{exp}</div></div>')
    with right:
        st.button("Edit tags", key="mp_edit_tags", on_click=_go, args=("tags",), use_container_width=True)
        st.button("Edit my answers", key="mp_edit_answers", on_click=_go, args=("review",), use_container_width=True)

    st.html('<div class="rb-stack" style="margin-top:24px;gap:8px"><p class="rb-serif rb-h3">Your top matches</p>'
            '<p class="rb-small rb-sage">*Wages are approximate California medians from our job data, not a promise. '
            "Confirm pay, hours, transit, licensing, and training before making plans.</p></div>")
    ms = ss.mp_matches
    for i in range(0, len(ms), 2):
        cols = st.columns(2, gap="medium")
        for col, j in zip(cols, ms[i:i + 2]):
            with col:
                _job_card(j)
    ui.footer()


def _job_card(j: dict) -> None:
    ss = st.session_state
    soc = j["soc"]
    tag = data.job_industry_tags(j)[0] if data.job_industry_tags(j) else None
    w = j.get("ca_median_hourly")
    pay = (f'<p class="rb-serif rb-h3">${w:.2f}/hour</p><p class="rb-small rb-sage" style="font-size:13px">'
           f'California median · {ui.esc(j.get("wage_source", ""))}</p>') if w else \
          '<p class="rb-small rb-strong">Wage data not available</p>'
    flag = (f'<div class="rb-warn">Below the ${ss.mp_payfloor:.0f}/hour you need. Many people start here and move up.</div>'
            if j.get("below_pay_floor") else "")
    lic = f'<div class="rb-warn">⚠️ {ui.esc(j["license_note"])}</div>' if j.get("licensed") and j.get("license_note") else ""
    with st.container(key=f"card_job_{soc}"):
        st.html(
            '<div class="rb-stack" style="gap:16px">'
            f'<div class="rb-stack" style="gap:10px"><p class="rb-serif rb-h3">{ui.esc(j["title"])}</p>'
            f'<div>{ui.pill(data.tag_label(tag)) if tag else ""}</div></div>'
            f'<div class="rb-stack"><p class="rb-small rb-semibold">Why it fits you</p>'
            f'<p class="rb-small">{ui.esc(j["why_it_fits"])}</p></div>'
            f'<div style="display:flex;gap:24px"><div class="rb-stack" style="flex:1;gap:4px">'
            f'<p class="rb-small rb-sage">Pay</p>{pay}</div>'
            f'<div class="rb-stack" style="flex:1;gap:4px"><p class="rb-small rb-sage">Training</p>'
            f'<p class="rb-small">{ui.esc(j.get("training", ""))}</p></div></div>{flag}{lic}'
            f'<div style="background:{ui.PINK_SOFT};border-radius:14px;padding:14px 16px" class="rb-stack">'
            '<p class="rb-small rb-strong" style="color:var(--rb-primary)">Your first step</p>'
            f'<p class="rb-small">{ui.esc(j["first_step"])}</p></div></div>'
        )
        member = next((m for m in data.load_members() if tag in m["industry_tags"]), None)
        if member:
            with st.container(key=f"lavsm_member_{soc}"):
                st.html('<p class="rb-small rb-semibold">A woman who’s walked this path</p>'
                        f'<div style="display:flex;gap:12px;margin-top:8px">{ui.avatar(member["display_name"], 42)}'
                        f'<div class="rb-stack" style="gap:4px"><p class="rb-small rb-semibold">{ui.esc(member["display_name"])} · '
                        f'{ui.esc(member["current_job"])}</p><p class="rb-small">“{ui.esc(member["advice"])}”</p></div></div>')
                st.button(f"Message {member['first_name']}", type="tertiary", key=f"mp_msg_{soc}",
                          on_click=nav.open_thread, args=(member["id"],))
        with st.container(horizontal=True, gap="small"):
            st.button("Stories from women in this field", key=f"mp_stories_{soc}",
                      on_click=nav.go, args=("community",), kwargs={"tags": [tag] if tag else []})
            st.button("Get trained", key=f"mp_train_{soc}", on_click=nav.go, args=("resources",),
                      kwargs={"tags": [tag] if tag else []})
            st.link_button("Search openings ↗", f"https://www.indeed.com/jobs?q={quote_plus(j['title'])}"
                                                f"&l={quote_plus(DEFAULT_LOCATION)}")
        if st.button("Write a cover letter", type="primary", use_container_width=True, key=f"mp_letter_{soc}"):
            ss.mp_letter_soc = soc
            _go("letter")
            st.rerun()


# --- PRD 8: cover letter --------------------------------------------------------------------------
def _letter(user: dict) -> None:
    ss = st.session_state
    soc = ss.get("mp_letter_soc")
    job = data.job_by_soc(soc) if soc else None
    if not job:
        _go("matches")
        st.rerun()
    say_where = bool(ss.get("mp_say_where", False))
    key = f"mp_letterdata_{soc}_{say_where}"
    st.html('<div class="rb-stack" style="gap:12px;margin:8px 0 16px 0"><p class="rb-eyebrow">My Path · Cover letter</p>'
            '<p class="rb-serif rb-h1">Your experience, in your voice.</p>'
            f'<p class="rb-small">A draft for the {ui.esc(job["title"])} match. Read it through and change anything '
            "that doesn’t sound like you.</p></div>")
    if key not in ss:
        profile = {"summary": ss.get("mp_summary"), "skills": ss.get("mp_skills"), "experience": ss.get("mp_explines")}
        with st.spinner("Writing your letter…"):
            ss[key] = llm.generate_cover_letter(profile, job, _answers_contract(), first_name(user), say_where)
    result = ss[key]
    words = "\n\n".join(v for v in ss.mp_answers.values() if v)
    left, right = st.columns(2, gap="medium")
    with left:
        st.html('<p class="rb-serif" style="font-size:24px;margin-bottom:8px">Your words</p>'
                '<div class="rb-panel lg" style="min-height:520px;font-size:16px;line-height:1.5;white-space:pre-wrap">'
                f"{ui.esc(words)}</div>")
    with right:
        st.html('<p class="rb-serif" style="font-size:24px;margin-bottom:8px">Your cover letter</p>')
        letter = st.text_area("Your cover letter", value=result["letter"], height=520, key=f"{key}_box",
                              label_visibility="collapsed")
    st.toggle("Say where I gained this experience.", key="mp_say_where")
    st.caption("On: the letter briefly names where you gained this experience." if say_where else
               "Off: the letter describes your experience without naming the jail.")
    script = "".join(f'<p class="rb-small">“{ui.esc(x)}”</p>' for x in result.get("record_script", []))
    st.html('<div class="rb-card" style="box-shadow:none"><p class="rb-serif rb-h3">If your record comes up</p>'
            '<p class="rb-small">A brief, honest, forward-looking script. Use only what is true for you.</p>'
            f'{script}</div><p class="rb-small" style="margin:16px 0 8px 0">California’s Fair Chance Act generally '
            "limits when employers can ask about records. Not legal advice.</p>")
    with st.container(horizontal=True, gap="small"):
        st.download_button("Download", data=letter + "\n\n---\nIf your record comes up:\n" + "\n".join(result.get("record_script", [])),
                           file_name="cover-letter.txt", mime="text/plain", type="primary", key="mp_download")
        st.button("Back to matches", key="mp_back_matches", on_click=_go, args=("matches",))
    ui.footer()
