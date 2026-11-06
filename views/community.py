"""Community track: synthetic peer stories, filtered by job family.

TODO(stream-3): expand stories.json. TODO(ui): match Figma.
"""

from __future__ import annotations

import streamlit as st

import data


def render() -> None:
    st.header("Community")
    st.caption("Example stories (synthetic, for demo). A real version needs consent, "
               "moderation, and anonymization.")

    families = data.family_options()
    labels = ["All"] + [f"{name}" for _, name in families]
    codes = [None] + [code for code, _ in families]
    choice = st.selectbox("Filter by job family", options=range(len(labels)),
                          format_func=lambda i: labels[i])
    fam_code = codes[choice]

    stories = data.load_stories()
    if fam_code:
        stories = [s for s in stories if s["family_code"] == fam_code]

    if not stories:
        st.info("No stories for this family yet.")
        return

    for s in stories:
        with st.container(border=True):
            st.markdown(f"**{s['name']}** — {s['now']}")
            st.write(s["story"])
            st.caption(f"Advice: {s['advice']}")
