"""Train Up track: local upskilling programs, filtered by job family.

TODO(stream-3): expand training.json with more real SF/Bay Area programs.
TODO(ui): match Figma.
"""

from __future__ import annotations

import streamlit as st

import data


def render() -> None:
    st.header("Train Up")
    st.caption("Local programs, grouped by job family.")

    families = data.family_options()
    labels = ["All"] + [name for _, name in families]
    codes = [None] + [code for code, _ in families]
    choice = st.selectbox("Filter by job family", options=range(len(labels)),
                          format_func=lambda i: labels[i])
    fam_code = codes[choice]

    programs = data.load_training()
    if fam_code:
        programs = [t for t in programs if t["family_code"] == fam_code]

    if not programs:
        st.info("No programs for this family yet.")
        return

    for t in programs:
        with st.container(border=True):
            st.markdown(f"### {t['name']}")
            st.caption(f"{t['provider']} · {t['location']}")
            st.write(f"**Length:** {t['length']}  |  **Cost:** {t['cost']}")
            if t.get("notes"):
                st.write(t["notes"])
            st.markdown(f"[Program link]({t['url']})")
