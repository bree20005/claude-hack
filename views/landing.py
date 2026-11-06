"""Landing + auth screen (shown when logged out).

TODO(ui): restyle to match the Figma wireframes once screenshots are available.
"""

from __future__ import annotations

import streamlit as st

import auth


def render() -> None:
    st.title("Next Chapter")
    st.caption("Employment help + community for women after incarceration.")
    st.write(
        "Tell your story in your own words, and we'll turn your experience — including "
        "work you did while inside — into real job matches, peer stories, and local training."
    )
    st.info("Nothing you type is saved. This is not legal advice.")

    tab_signin, tab_signup = st.tabs(["Sign in", "Create account"])

    with tab_signin:
        with st.form("signin_form"):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_pw")
            submitted = st.form_submit_button("Sign in")
        if submitted:
            ok, msg = auth.login(email, password)
            if ok:
                st.rerun()
            else:
                st.error(msg)

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Your name (optional)", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input(
                "Password (6+ characters)", type="password", key="signup_pw"
            )
            submitted = st.form_submit_button("Create account")
        if submitted:
            ok, msg = auth.signup(email, password, name)
            if ok:
                st.rerun()
            else:
                st.error(msg)

    st.divider()
    if st.button("Continue with Google", use_container_width=True):
        ok, msg = auth.login_google()
        if ok:
            st.rerun()
    st.caption("Google sign-in is a demo stub in this skeleton.")
