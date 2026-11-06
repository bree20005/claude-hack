"""My Path: guided conversation -> recap -> job matches -> cover letter.

Figma frames: "C/D1/D2" (chat + recap), "2 · My Path · Results", "My Path · Cover letter".
Claude calls go through llm.py (canned output when no API key is set).

Conversation state lives in st.session_state under `mp_*` keys (cleared on logout);
the profile, matches and letters go through storage.py, keyed by the user's email.
"""

from __future__ import annotations

import streamlit as st

import data
import llm
import nav
import ui
from storage import get_storage

# 7 topics = the 7 progress petals. The first four are needed for matching;
# the last three can be skipped ("You can leave the rest for later").
TOPICS = [
    ("past", "Work before", False,
     "Let's start with work you know. What jobs have you done before? Informal work counts too, "
     "like cleaning, childcare, selling, or caregiving."),
    ("inside", "Work inside", False,
     "What jobs or programs did you do while you were inside? Kitchen, laundry, maintenance, "
     "tutoring, and fire crew all count."),
    ("needs", "Hours & travel", False,
     "What hours and travel would work for you now? Tell me anything a job needs to fit around, "
     "like kids, transit, health, or parole check-ins."),
    ("where", "Place & pay", False,
     "Where are you looking for work, and how much do you need to earn? How soon do you need income?"),
    ("education", "Education", True,
     "Do you have a GED, HiSET, diploma, or any college credits? You can skip this one."),
    ("credentials", "Credentials", True,
     "Any certificates or cards, like a Food Handler card, forklift, or OSHA? You can skip this one."),
    ("goals", "Goals", True,
     "What are you proud of, or hoping for in your next job? You can skip this one."),
]
_TOPIC = {k: (label, optional, q) for k, label, optional, q in TOPICS}
_SKIP_WORDS = {"skip", "skip for now", "pass", "later", "no", "none", "n/a"}


# --- state helpers -----------------------------------------------------------
def _init(user: dict) -> None:
    ss = st.session_state
    if "mp_log" in ss:
        return
    hello = f"Hi {user['name']}. " if not user.get("guest") and user.get("name") not in (None, "", "Friend") else "Hi. "
    ss.mp_answers = {}
    ss.mp_idx = 0
    ss.mp_phase = "asking"          # asking | recap | fix_pick
    ss.mp_fixing = None
    ss.mp_recap_ready = False
    ss.mp_log = [
        {"role": "bot", "text": hello + "I'll ask a few questions about the work you've done, inside and out. "
         "Answer in your own words. Short is fine."},
        {"role": "bot", "text": TOPICS[0][3]},
    ]


def _reset_conversation() -> None:
    for k in [k for k in st.session_state.keys() if str(k).startswith("mp_")]:
        st.session_state.pop(k, None)


def _current_topic() -> str | None:
    ss = st.session_state
    if ss.mp_fixing:
        return ss.mp_fixing
    if ss.mp_phase == "asking" and ss.mp_idx < len(TOPICS):
        return TOPICS[ss.mp_idx][0]
    return None


def _shared_count() -> int:
    return sum(1 for k, *_ in TOPICS if st.session_state.mp_answers.get(k))


def _who(user: dict) -> str:
    return "You" if user.get("guest") or user.get("name") in (None, "", "Friend") else user["name"]


def _first_name(user: dict) -> str:
    return "" if user.get("guest") or user.get("name") in (None, "", "Friend") else user["name"]


def _record(text: str | None) -> None:
    """Store an answer (None = skipped) and queue the next question."""
    ss = st.session_state
    topic = _current_topic()
    if topic is None:  # free text after the recap: add it as extra context
        if text:
            ss.mp_answers["more"] = " ".join(filter(None, [ss.mp_answers.get("more"), text]))
            ss.mp_log += [{"role": "user", "text": text},
                          {"role": "bot", "text": "Thank you. I added that to your story."}]
            ss.mp_recap_ready = False
            ss.mp_phase = "recap"
        return

    ss.mp_answers[topic] = text
    ss.mp_log.append({"role": "user", "text": text or "Skip for now"})
    ss.mp_recap_ready = False
    if ss.mp_fixing:
        ss.mp_fixing = None
        ss.mp_phase = "recap"
        return
    ss.mp_idx += 1
    if ss.mp_idx < len(TOPICS):
        ss.mp_log.append({"role": "bot", "text": TOPICS[ss.mp_idx][3]})
    else:
        ss.mp_phase = "recap"


def _start_fix(topic: str) -> None:
    ss = st.session_state
    ss.mp_fixing = topic
    ss.mp_phase = "asking"
    ss.mp_log.append({"role": "bot", "text": _TOPIC[topic][2]})


def _answers_for_claude(user: dict) -> dict:
    out = {k: st.session_state.mp_answers.get(k) for k, *_ in TOPICS}
    if st.session_state.mp_answers.get("more"):
        out["more"] = st.session_state.mp_answers["more"]
    if _first_name(user):
        out["first_name"] = _first_name(user)
    return out


def _compute_recap(user: dict) -> None:
    store = get_storage()
    with st.spinner("Reading your story…"):
        result = llm.generate_profile_and_matches(_answers_for_claude(user), data.load_jobs())
    store.save_profile(user["email"], result.get("skills_profile", {}))
    # Keep only matches that join to a real job in our data (drop anything invented).
    valid = [m for m in result.get("matches", []) if data.job_by_soc(m.get("soc", ""))]
    store.save_matches(user["email"], valid)
    st.session_state.mp_recap_ready = True


# --- screens -----------------------------------------------------------------
def render(user: dict) -> None:
    _init(user)
    view = st.session_state.get(nav.MY_PATH_VIEW_KEY, "chat")
    store = get_storage()
    has_matches = bool(store.get_matches(user["email"]))
    if view == "letter" and st.session_state.get("mp_letter_soc"):
        _letter(user)
    elif view in ("results", "letter") and has_matches:
        _results(user)
    else:
        _chat(user)


def _chat(user: dict) -> None:
    ss = st.session_state
    _, mid, _ = st.columns([260, 760, 260])
    with mid:
        recap = ss.mp_phase in ("recap", "fix_pick") and not ss.mp_fixing
        skipped = [k for k, _, optional, _ in TOPICS if optional and k in ss.mp_answers and not ss.mp_answers[k]]
        title = "Your story, together." if recap else ("In your own words." if ss.mp_idx == 0 else "Let's keep going.")
        head, prog = st.columns([1, 1], vertical_alignment="center")
        with head:
            st.html(
                '<div class="rb-stack" style="gap:6px">'
                '<p class="rb-eyebrow muted">My Path / Your story</p>'
                f'<p class="rb-serif rb-h2">{ui.esc(title)}</p></div>'
            )
        with prog:
            st.html(ui.petals(_shared_count(), len(TOPICS), f"{len(skipped)} optional" if recap and skipped else ""))

        st.html(
            '<div class="rb-stack" style="gap:26px;margin-top:8px">'
            + "".join(
                ui.chat_bubble(m["role"], _who(user) if m["role"] == "user" else "Rebloom", m["text"])
                for m in ss.mp_log
            )
            + "</div>"
        )

        topic = _current_topic()
        if topic and _TOPIC[topic][1]:
            with st.container(horizontal=True):
                if st.button("Skip for now", key=f"mp_skip_{topic}"):
                    _record(None)
                    st.rerun()

        if ss.mp_phase == "recap":
            if not ss.mp_recap_ready:
                _compute_recap(user)
            _recap_card(user, skipped)
        elif ss.mp_phase == "fix_pick":
            _fix_picker()

    placeholder = "Answer in your own words…" if topic else "Add anything else in your own words…"
    text = st.chat_input(placeholder, key="mp_composer")
    if text is not None:
        cleaned = text.strip()
        if topic and _TOPIC[topic][1] and cleaned.lower() in _SKIP_WORDS:
            _record(None)
        elif cleaned:
            _record(cleaned)
        st.rerun()


def _recap_card(user: dict, skipped: list[str]) -> None:
    profile = get_storage().get_profile(user["email"]) or {}
    name = _first_name(user)
    rows = [
        ("Experience", "; ".join(profile.get("experience", []))),
        ("Strengths", profile.get("strengths") or ", ".join(profile.get("skills", []))),
        ("What fits now", profile.get("fits_now", "")),
    ]
    facts = '<div class="rb-divider"></div>'.join(
        f'<div class="r"><div class="k">{k}</div><div class="v">{ui.esc(v)}</div></div>' for k, v in rows if v
    )
    chips = "".join(ui.pill(f"{_TOPIC[k][0]} · skipped", "white") for k in skipped)
    later = (
        '<div class="rb-stack" style="gap:10px"><p class="rb-small rb-strong">You can leave the rest for later.</p>'
        f'<div class="rb-row" style="gap:8px">{chips}</div></div>' if skipped else ""
    )
    st.html('<p style="margin:12px 0 -8px 0;font-weight:700;font-size:16px;color:var(--rb-muted)">Rebloom</p>')
    with st.container(key="lav_recap"):
        st.html(
            f'<div class="rb-row">{ui.icon("small-petal", 22)}'
            f'<p class="rb-serif" style="font-size:28px">Here’s what you bring{", " + ui.esc(name) if name else ""}.</p></div>'
            '<p class="rb-body" style="margin-top:12px">Your work inside is real experience. '
            "Before we explore job matches, does this feel like you?</p>"
            f'<div class="rb-facts" style="margin-top:16px">{facts}</div>'
            f'<div style="margin-top:16px">{later}</div>'
        )
        with st.container(horizontal=True, gap="small"):
            st.button("Show my path", type="primary", key="mp_show_path",
                      on_click=nav.go, args=("my_path",), kwargs={"view": "results"})
            if st.button("Fix something", key="mp_fix"):
                st.session_state.mp_phase = "fix_pick"
                st.session_state.mp_log.append({"role": "bot", "text": "Of course. Which part would you like to change?"})
                st.rerun()


def _fix_picker() -> None:
    labels = {k: label for k, label, *_ in TOPICS}
    choice = st.pills("Choose a topic", options=list(labels), format_func=labels.get,
                      key="mp_fix_choice", label_visibility="collapsed")
    if choice:
        st.session_state.pop("mp_fix_choice", None)
        _start_fix(choice)
        st.rerun()


# --- results -----------------------------------------------------------------
def _results(user: dict) -> None:
    store = get_storage()
    profile = store.get_profile(user["email"]) or {}
    matches = store.get_matches(user["email"])
    name = _first_name(user)

    sub = " · ".join(filter(None, [f"A starting point for {name}" if name else "A starting point for you",
                                   profile.get("fits_now", "").rstrip(".")]))
    st.html(
        '<div class="rb-stack" style="gap:12px;margin:8px 0 16px 0">'
        '<p class="rb-eyebrow rb-sage" style="font-size:14px">2 / My Path · Results</p>'
        '<p class="rb-serif rb-h1">You have experience to build on.</p>'
        f'<p class="rb-small">{ui.esc(sub)}</p></div>'
    )

    skills = "".join(ui.pill(s) for s in profile.get("skills", []))
    exp = "".join(f'<p class="rb-small">{ui.esc(e)}</p>' for e in profile.get("experience", []))
    st.html(
        '<div class="rb-card" style="border-color:#e7d6d6;box-shadow:0 8px 24px rgba(61,42,58,.07);gap:16px">'
        '<p class="rb-serif rb-h3">What you bring</p>'
        f'<p class="rb-small">{ui.esc(profile.get("summary", ""))}</p>'
        '<p class="rb-small rb-sage">Draft from your story: keep what feels true and change anything that doesn’t.</p>'
        f'<div class="rb-row" style="gap:8px">{skills}</div>'
        f'<div class="rb-stack"><p class="rb-small rb-semibold">Your work experience</p>{exp}</div></div>'
    )

    st.html(
        '<div class="rb-stack" style="margin-top:28px;gap:10px">'
        '<p class="rb-serif rb-h3">Your top matches</p>'
        '<p class="rb-small rb-sage">*Wages are illustrative California median examples from our demo data, '
        "not verified wage data. Confirm current pay, hours, transit, licensing, and training details "
        "before making plans.</p></div>"
    )
    pairs = [matches[i:i + 2] for i in range(0, len(matches), 2)]
    for pair in pairs:
        cols = st.columns(len(pair), gap="medium")
        for col, m in zip(cols, pair):
            with col:
                _match_card(m)

    with st.expander("Want to change your answers?"):
        with st.container(horizontal=True, gap="small"):
            if st.button("Fix something", key="mp_results_fix"):
                st.session_state.mp_phase = "fix_pick"
                st.session_state.mp_log.append({"role": "bot", "text": "Of course. Which part would you like to change?"})
                nav.go("my_path", view="chat")
                st.rerun()
            if st.button("Start over", key="mp_restart"):
                _reset_conversation()
                store.save_matches(user["email"], [])
                store.save_profile(user["email"], None)
                st.rerun()
    ui.footer()


def _match_card(match: dict) -> None:
    joined = data.join_match(match["soc"])
    if not joined:
        return
    job, stories, programs = joined["job"], joined["stories"], joined["training"]
    soc = job["soc"]
    family = job["family"]
    with st.container(key=f"card_match_{soc}"):
        warn = f'<div class="rb-warn">License required. {ui.esc(job["license_note"])}</div>' if job.get("licensed") else ""
        why = "".join(f'<p class="rb-small">{ui.esc(t)}</p>' for t in (match.get("why_it_fits"), match.get("first_step")) if t)
        st.html(
            '<div class="rb-stack" style="gap:22px">'
            f'<div class="rb-stack" style="gap:12px"><p class="rb-serif rb-h3">{ui.esc(job["title"])}</p>'
            f'<div>{ui.family_pill(family)}</div></div>{warn}'
            f'<div class="rb-stack"><p class="rb-small rb-semibold">Why it fits you</p>{why}</div>'
            '<div style="display:flex;gap:24px">'
            '<div class="rb-stack" style="width:170px;gap:6px"><p class="rb-small rb-sage">CA median wage*</p>'
            f'<p class="rb-serif rb-h3">{ui.money(job["ca_median_hourly"])}</p></div>'
            '<div class="rb-stack" style="flex:1;gap:6px"><p class="rb-small rb-sage">Training time*</p>'
            f'<p class="rb-small">{ui.esc(job["training"])}</p></div></div></div>'
        )
        if stories:
            s = stories[0]
            with st.container(key=f"lavsm_story_{soc}"):
                st.html(
                    '<p class="rb-small rb-semibold">Women who’ve walked this path</p>'
                    f'<div style="display:flex;gap:12px;margin-top:10px">{ui.avatar(s["name"], 42)}'
                    f'<div class="rb-stack" style="gap:6px"><p class="rb-small rb-semibold">{ui.esc(s["name"])}</p>'
                    f'<p class="rb-small">“{ui.esc(s["advice"])}”</p></div></div>'
                )
                st.button(f"Read her story → Community · {family}", type="tertiary", key=f"mp_story_{soc}",
                          on_click=nav.go, args=("community",), kwargs={"family": job["family_code"]})
        if programs:
            t = programs[0]
            st.html(
                '<div class="rb-stack"><p class="rb-small rb-semibold">Train up nearby</p>'
                f'<p class="rb-small">{ui.esc(t["name"])}</p>'
                f'<p class="rb-small rb-sage">{ui.esc(" · ".join([t["length"], t["cost"], t["location"]]))}</p></div>'
            )
            st.button(f"See program → Train Up · {family}", type="tertiary", key=f"mp_train_{soc}",
                      on_click=nav.go, args=("train_up",), kwargs={"family": job["family_code"]})
        if st.button("Write my cover letter", type="primary", use_container_width=True, key=f"mp_letter_{soc}"):
            st.session_state.mp_letter_soc = soc
            nav.go("my_path", view="letter")
            st.rerun()


# --- cover letter ------------------------------------------------------------
def _letter(user: dict) -> None:
    ss = st.session_state
    store = get_storage()
    soc = ss.mp_letter_soc
    job = data.job_by_soc(soc)
    profile = store.get_profile(user["email"]) or {}
    say_where = bool(ss.get("mp_say_where", False))
    letter_key = f"{soc}|{'named' if say_where else 'plain'}"

    st.html(
        '<div class="rb-stack" style="gap:12px;margin:8px 0 16px 0">'
        '<p class="rb-eyebrow">3 / My Path · Cover letter</p>'
        '<p class="rb-serif rb-h1">Your experience, in your voice.</p>'
        f'<p class="rb-small">A draft for the {ui.esc(job["title"])} match. Read it through and change anything '
        "that doesn’t sound like you.</p>"
        f'<div class="rb-row" style="margin-top:12px"><p class="rb-serif" style="font-size:22px">{ui.esc(job["title"])}</p>'
        f'{ui.family_pill(job["family"])}</div></div>'
    )

    result = store.get_letters(user["email"]).get(letter_key)
    if not result:
        with st.spinner("Writing your letter…"):
            result = llm.generate_cover_letter(profile, job, _answers_for_claude(user), _first_name(user), say_where)
        store.save_letter(user["email"], letter_key, result)

    words = "\n\n".join(v for k, *_ in TOPICS if (v := ss.mp_answers.get(k)))
    if ss.mp_answers.get("more"):
        words += "\n\n" + ss.mp_answers["more"]
    left, right = st.columns(2, gap="medium")
    with left:
        st.html(
            '<p class="rb-serif" style="font-size:24px;margin-bottom:8px">Your words</p>'
            '<div class="rb-panel lg" style="min-height:560px;font-size:16px;line-height:1.5;white-space:pre-wrap">'
            f"{ui.esc(words) or 'Your answers from My Path will show here.'}</div>"
        )
    with right:
        st.html('<p class="rb-serif" style="font-size:24px;margin-bottom:8px">Your cover letter</p>')
        letter = st.text_area("Your cover letter", value=result["letter"], height=560,
                              key=f"mp_letterbox_{letter_key}", label_visibility="collapsed")

    st.toggle("Say where I gained this experience.", key="mp_say_where")
    st.html(
        '<p class="rb-small" style="margin-top:-8px">'
        + ("On in this draft. The letter briefly names where you gained this experience."
           if say_where else
           "Off in this draft. The letter describes your experience without naming the jail.")
        + "</p>"
    )

    script = "".join(f'<p class="rb-small">“{ui.esc(line)}”</p>' for line in result.get("record_script", []))
    st.html(
        '<div class="rb-card" style="box-shadow:none;margin-top:16px">'
        '<p class="rb-serif rb-h3">If your record comes up</p>'
        '<p class="rb-small">A brief, honest, forward-looking script. Use only what is true for you.</p>'
        f"{script}</div>"
        '<p class="rb-small" style="margin:20px 0 8px 0">California’s Fair Chance Act generally limits when '
        "employers can ask about records. Not legal advice.</p>"
    )

    download = letter + "\n\n---\nIf your record comes up:\n" + "\n".join(result.get("record_script", []))
    with st.container(horizontal=True, gap="small"):
        st.download_button("Download", data=download, file_name=f"cover-letter-{job['title'].lower().split()[0]}.txt",
                           mime="text/plain", type="primary", key="mp_download")
        st.button("Back to matches", key="mp_back", on_click=nav.go, args=("my_path",), kwargs={"view": "results"})
    ui.footer()
