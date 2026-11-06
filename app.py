"""Rebloom (Next Chapter) — app entry point: auth gate + routing.

Flow:
  - Logged out  -> public homepage (log in dialog, or continue as guest)
  - Signed in   -> shared header + top tabs: My Path · Community · Train Up · Paths

Only this file wires routing. Each screen lives in views/. Cross-screen links
(e.g. "Read her story → Community") call `nav.go(...)` instead of touching tabs.
"""

from __future__ import annotations

import streamlit as st

import auth
import nav
import ui
from views import community, landing, my_path, paths, train_up

st.set_page_config(page_title="Rebloom", page_icon="🌸", layout="wide")

PAGES = {
    "my_path": ("My Path", my_path.render),
    "community": ("Community", community.render),
    "train_up": ("Train Up", train_up.render),
    "paths": ("Paths", paths.render),
}


def _header(user: dict) -> None:
    left, right = st.columns([1, 1], vertical_alignment="center")
    with left:
        st.html(ui.brand())
    with right:
        session = "Guest session" if user.get("guest") else user.get("name", "Signed in")
        promise_col, out_col = st.columns([5, 1], vertical_alignment="center")
        with promise_col:
            st.html(
                '<div class="rb-promise"><p>Your experience counts.</p>'
                f'<span class="rb-session">{ui.esc(session)}</span></div>'
            )
        with out_col:
            if st.button("Sign out" if not user.get("guest") else "Exit", type="tertiary", key="signout"):
                auth.logout()
                nav.reset()
                st.rerun()

    current = nav.current_page()
    with st.container(horizontal=True, key="topnav"):
        for page, (label, _) in PAGES.items():
            st.button(label, key=f"nav_{page}", type="tertiary", on_click=nav.go, args=(page,))
    ui.active_nav_css(f"nav_{current}")


def main() -> None:
    ui.inject_css()
    user = auth.current_user()

    if user is None:
        landing.render()
        return

    _header(user)
    _, render = PAGES.get(nav.current_page(), PAGES["my_path"])
    render(user)


if __name__ == "__main__":
    main()
