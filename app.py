"""Rebloom (Next Chapter) — app entry point: auth gate, persona choice, routing.

Flow (PRD 1):
  - Signed out   -> public homepage (log in dialog: Google if configured, phone/email, guest)
  - Signed in, no persona -> "What brings you here today?" (seeker / sharer / browse stories)
  - Then shared header + tabs: My Path (or My Story) · Community · Resources · Paths · Messages
"""

from __future__ import annotations

import streamlit as st

import auth
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
        a, b, c = st.columns([4, 1.3, 1], vertical_alignment="center")
        a.html('<div class="rb-promise"><p>Your experience counts.</p>'
               f'<span class="rb-session">{ui.esc(session)}</span></div>')
        b.button("Start over", type="tertiary", key="hdr_restart", on_click=_start_over)
        if c.button("Exit" if user.get("guest") else "Sign out", type="tertiary", key="signout"):
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
    if "mp_persona" not in st.session_state:
        _persona_choice(user)
        return
    _header(user)
    PAGES.get(nav.current_page(), my_path.render)(user)


if __name__ == "__main__":
    main()
