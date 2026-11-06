"""Rebloom (Next Chapter) — app entry point: auth gate, persona choice, routing.

Flow (PRD 1):
  - Signed out   -> public homepage (log in dialog: Google if configured, phone/email, guest)
  - Signed in, no persona -> "What brings you here today?" (seeker / sharer / browse stories)
  - Then shared header + tabs: My Path (or My Story) · Community · Resources · Paths · Messages
"""

from __future__ import annotations

import streamlit as st

import auth
import db
import nav
import ui
from views import community, landing, messages, my_path, paths, resources

st.set_page_config(page_title="Rebloom", page_icon="🌸", layout="wide")

PAGES = {
    "my_path": my_path.render,
    "community": community.render,
    "resources": resources.render,
    "paths": paths.render,
    "messages": messages.render,
}


# Session keys saved per signed-in user (db.user_state). Guests are never saved.
# Only plain data keys: widget keys (buttons, pills, toggles) can't be restored safely.
_PERSIST = {
    "mp_persona", "mp_stage", "mp_msgs", "mp_covered", "mp_qr", "mp_ready", "mp_crisis", "mp_answers",
    "mp_tags", "mp_reasons", "mp_summary", "mp_skills", "mp_explines", "mp_tags_hash", "mp_matches",
    "mp_payfloor", "mp_matches_key", "mp_letter_soc", "mp_published", "mp_anon", "mp_pub_job",
    "mp_pub_journey", "mp_pub_advice", "msg_threads", "msg_active", "page", "saved_paths", "res_why",
}


def _persisted(ss) -> dict:
    out = {k: ss[k] for k in _PERSIST if k in ss}
    out.update({k: v for k, v in ss.items() if str(k).startswith("mp_letterdata_") and not str(k).endswith("_box")})
    if "saved_paths" in out:
        out["saved_paths"] = sorted(out["saved_paths"])
    return out


def _restore(user: dict) -> None:
    """Load a signed-in user's saved progress once per browser session."""
    ss = st.session_state
    if user.get("guest") or ss.get("_db_loaded") == user["email"]:
        return
    db.upsert_user(user)
    state = db.load_state(user["email"])
    for k, v in state.items():
        ss[k] = set(v) if k == "saved_paths" else v
    ss["_db_loaded"] = user["email"]
    if state:
        st.toast("Welcome back. We picked up where you left off.")


def _save(user: dict) -> None:
    if not user.get("guest") and st.session_state.get("_db_loaded") == user["email"]:
        db.save_state(user["email"], _persisted(st.session_state))


def _delete_my_data(user: dict) -> None:
    db.delete_user_data(user["email"])
    auth.logout()
    nav.reset()


def _start_over() -> None:
    my_path.reset_all()
    st.session_state.pop("mp_persona", None)
    nav.reset()


def _header(user: dict) -> None:
    left, right = st.columns([1, 1.2], vertical_alignment="center")
    with left:
        st.html(ui.brand())
    with right:
        session = "Guest session" if user.get("guest") else (user.get("name") or "Signed in")
        a, b, c, d = st.columns([4, 1.3, 1.6, 1], vertical_alignment="center")
        a.html('<div class="rb-promise"><p>Your experience counts.</p>'
               f'<span class="rb-session">{ui.esc(session)}</span></div>')
        b.button("Start over", type="tertiary", key="hdr_restart", on_click=_start_over)
        if not user.get("guest"):
            with c.popover("My data"):
                st.write("Your story, answers and conversations are saved to your account so you can come back. "
                         "Delete everything, including any published story?")
                if st.button("Delete my data", key="hdr_delete", on_click=_delete_my_data, args=(user,)):
                    st.rerun()
        if d.button("Exit" if user.get("guest") else "Sign out", type="tertiary", key="signout"):
            auth.logout()
            nav.reset()
            st.rerun()

    current = nav.current_page()
    first = "My Story" if st.session_state.get("mp_persona") == "sharer" else "My Path"
    n_threads = len(st.session_state.get("msg_threads", {}))
    labels = {"my_path": first, "community": "Community", "resources": "Resources", "paths": "Paths",
              "messages": f"Messages ({n_threads})" if n_threads else "Messages"}
    with st.container(horizontal=True, key="topnav"):
        for page, label in labels.items():
            st.button(label, key=f"nav_{page}", type="tertiary", on_click=nav.go, args=(page,))
    ui.active_nav_css(f"nav_{current}")


def _choose(persona: str | None) -> None:
    my_path.reset_all()
    nav.reset()
    if persona:
        st.session_state["mp_persona"] = persona
    else:
        st.session_state["mp_persona"] = "seeker"
        nav.go("community")


def _persona_choice(user: dict) -> None:
    st.html(ui.brand())
    name = "" if user.get("guest") else (user.get("name") or "").split(" ")[0]
    st.html('<div class="rb-stack" style="gap:10px;margin:48px 0 24px 0">'
            f'<p class="rb-serif rb-h1">Hi{", " + ui.esc(name) if name else ""}.</p>'
            '<p class="rb-body rb-muted">What brings you here today?</p></div>')
    a, b = st.columns(2, gap="large")
    cards = [
        (a, "seeker", "I'm looking for work", "Find jobs that fit your experience, including work you did inside.",
         "message-circle"),
        (b, "sharer", "I want to share my journey", "Help another woman see what's possible.", "heart-handshake"),
    ]
    for col, persona, title, sub, ic in cards:
        with col:
            with st.container(key=f"card_persona_{persona}"):
                st.html(f'<div class="rb-stack" style="gap:12px">{ui.icon(ic, 32)}'
                        f'<p class="rb-serif" style="font-size:30px">{title}</p><p class="rb-body rb-muted">{sub}</p></div>')
                st.button("Start", type="primary", key=f"persona_{persona}", on_click=_choose, args=(persona,),
                          use_container_width=True)
    st.button("Browse stories from women who've been there →", type="tertiary", key="persona_browse",
              on_click=_choose, args=(None,))
    st.html('<p class="rb-small rb-muted" style="margin-top:16px">Nothing you tell us is shared without your permission.</p>')
    ui.footer()


def main() -> None:
    ui.inject_css()
    user = auth.current_user()
    if user is None:
        landing.render()
        return
    _restore(user)
    try:
        if "mp_persona" not in st.session_state:
            _persona_choice(user)
            return
        _header(user)
        PAGES.get(nav.current_page(), my_path.render)(user)
    finally:  # runs on st.rerun() too, so every change is saved
        if auth.current_user() is not None:
            _save(auth.current_user())


if __name__ == "__main__":
    main()
