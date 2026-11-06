"""Next Chapter — app entry point: auth gate + routing.

Flow:
  - Logged out            -> landing (sign up / sign in)
  - Just signed up (new)  -> My Path conversation (the starting point)
  - Returning user        -> the three tracks (My Path · Community · Train Up)

Only this file wires routing. Each screen lives in views/. See README for the team
workstream boundaries.
"""

from __future__ import annotations

import streamlit as st

import auth
from views import community, landing, my_path, train_up

st.set_page_config(page_title="Next Chapter", page_icon="🧭", layout="centered")


def _sidebar(user: dict) -> None:
    with st.sidebar:
        st.markdown(f"**{user['name']}**")
        st.caption(user["email"])
        if st.button("Sign out"):
            auth.logout()
            st.rerun()


def main() -> None:
    user = auth.current_user()

    if user is None:
        landing.render()
        return

    _sidebar(user)

    # New sign-ups go straight into the My Path conversation.
    if auth.is_new_user():
        my_path.render(user)
        st.divider()
        if st.button("Go to all tracks →"):
            auth.clear_new_user_flag()
            st.rerun()
        return

    # Returning users see the three tracks.
    tab_path, tab_community, tab_train = st.tabs(
        ["My Path", "Community", "Train Up"]
    )
    with tab_path:
        my_path.render(user)
    with tab_community:
        community.render()
    with tab_train:
        train_up.render()


if __name__ == "__main__":
    main()
