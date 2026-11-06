"""Tiny session-state router shared by the views.

`go()` is safe as a button `on_click` callback: it only writes session state.
Filter keys are widget keys, so setting them before the widget renders preselects it
(this is how "Stories from women in this field" lands with that tag chosen).
"""

from __future__ import annotations

import streamlit as st

PAGE_KEY = "page"
COMMUNITY_TAGS_KEY = "community_tags"
RESOURCES_TAGS_KEY = "resources_tags"
PATHS_FILTER_KEY = "paths_start"
OPEN_STORY_KEY = "community_open_story"
THREAD_KEY = "msg_active"


def current_page() -> str:
    return st.session_state.get(PAGE_KEY, "my_path")


def go(page: str, *, tags: list[str] | None = None, story: str | None = None, path_id: str | None = None) -> None:
    st.session_state[PAGE_KEY] = page
    if tags is not None:
        key = COMMUNITY_TAGS_KEY if page == "community" else RESOURCES_TAGS_KEY
        st.session_state[key] = list(tags)
    if story is not None:
        st.session_state[OPEN_STORY_KEY] = story
    if path_id is not None:
        st.session_state[PATHS_FILTER_KEY] = path_id


def open_thread(member_id: str) -> None:
    st.session_state[PAGE_KEY] = "messages"
    st.session_state[THREAD_KEY] = member_id


def reset() -> None:
    for k in (PAGE_KEY, COMMUNITY_TAGS_KEY, RESOURCES_TAGS_KEY, PATHS_FILTER_KEY, OPEN_STORY_KEY, THREAD_KEY):
        st.session_state.pop(k, None)
