"""Tiny session-state router shared by the views.

`go()` is safe to use as a button `on_click` callback: it only writes session
state, and Streamlit reruns afterwards. Filter keys are the widget keys used by
Community / Train Up, so setting them before the widget renders preselects it.
"""

from __future__ import annotations

import streamlit as st

PAGE_KEY = "page"
MY_PATH_VIEW_KEY = "mp_view"          # "chat" | "results" | "letter"
COMMUNITY_FILTER_KEY = "community_family"
TRAIN_FILTER_KEY = "train_family"
PATHS_FILTER_KEY = "paths_start"


def current_page() -> str:
    return st.session_state.get(PAGE_KEY, "my_path")


def go(page: str, *, family: str | None = None, view: str | None = None, path_id: str | None = None) -> None:
    st.session_state[PAGE_KEY] = page
    if family is not None:
        if page == "community":
            st.session_state[COMMUNITY_FILTER_KEY] = family
        elif page == "train_up":
            st.session_state[TRAIN_FILTER_KEY] = family
    if view is not None:
        st.session_state[MY_PATH_VIEW_KEY] = view
    if path_id is not None:
        st.session_state[PATHS_FILTER_KEY] = path_id


def reset() -> None:
    for k in (PAGE_KEY, MY_PATH_VIEW_KEY, COMMUNITY_FILTER_KEY, TRAIN_FILTER_KEY, PATHS_FILTER_KEY):
        st.session_state.pop(k, None)
