"""Community: synthetic peer stories, filtered by job family (Figma: "Rebloom · Community").

TODO(stream-3): expand stories.json. A real version needs consent, moderation, and
anonymization before anything is posted.
"""

from __future__ import annotations

import streamlit as st

import data
import nav
import ui
from storage import get_storage

_ALL = "all"

# Figma "Women supporting women" line illustration (layer insets in %).
_ILLUSTRATION = [
    ("woman-curly-hair", "16.66%", "61.3%", "13.85%", "13.39%"),
    ("woman-loose-bun", "14.42%", "38.73%", "11.54%", "36.12%"),
    ("woman-short-bob", "25.87%", "13.94%", "13.85%", "59.75%"),
    ("petal-accents", "20%", "14.71%", "49.23%", "12.73%"),
]


def _story_card(s: dict) -> str:
    return (
        '<div class="rb-card">'
        f'<div class="rb-row" style="gap:14px;flex-wrap:nowrap">{ui.avatar(s["name"], 48)}'
        f'<div class="rb-stack" style="gap:2px"><p class="rb-serif" style="font-size:22px">{ui.esc(s["name"])}</p>'
        f'<p class="rb-small rb-muted">Now: {ui.esc(s["now"])}</p></div></div>'
        f'<div>{ui.family_pill(data.family_name(s["family_code"]))}</div>'
        f'<p class="rb-small">{ui.esc(s["story"])}</p>'
        '<div class="rb-panel"><p class="rb-small rb-semibold">Her advice</p>'
        f'<p class="rb-small">“{ui.esc(s["advice"])}”</p></div></div>'
    )


def _grid(stories: list[dict]) -> None:
    st.html(f'<div class="rb-grid2">{"".join(_story_card(s) for s in stories)}</div>')


def _illustration() -> str:
    layers = "".join(
        f'<div style="position:absolute;inset:{t} {r} {b} {l}"><img src="{ui.asset_uri(f"illustration/{n}.svg")}" '
        'alt="" style="display:block;width:100%;height:100%;max-width:none" /></div>'
        for n, t, r, b, l in _ILLUSTRATION
    )
    return (
        '<div role="img" aria-label="Three women standing together, supporting each other" '
        f'style="position:relative;width:260px;height:154px;flex:none">{layers}</div>'
    )


def render(user: dict) -> None:
    ui.page_intro("4 / Community", "Women who've walked this path.", "Example stories (synthetic, for demo).",
                  eyebrow_muted=True)

    families = data.family_options()
    codes = [_ALL] + [code for code, _ in families]
    labels = {_ALL: "All", **{code: ui.SHORT_FAMILY.get(code, name) for code, name in families}}
    st.session_state.setdefault(nav.COMMUNITY_FILTER_KEY, _ALL)
    choice = st.pills("Job family", options=codes, format_func=labels.get, key=nav.COMMUNITY_FILTER_KEY) or _ALL

    stories = data.load_stories()
    selected = stories if choice == _ALL else [s for s in stories if s["family_code"] == choice]
    others = [] if choice == _ALL else [s for s in stories if s["family_code"] != choice]

    heading = "All stories" if choice == _ALL else labels[choice]
    count = f"{len(selected)} {'story' if len(selected) == 1 else 'stories'}"
    match = next(
        (data.job_by_soc(m["soc"]) for m in get_storage().get_matches(user["email"])
         if data.job_by_soc(m["soc"]) and data.job_by_soc(m["soc"])["family_code"] == choice),
        None,
    )
    context = (
        f'<p class="rb-small rb-muted">From the {ui.esc(match["title"])} match → {ui.esc(match["family"])}. '
        "This family connects these stories to your matches and nearby training.</p>" if match else ""
    )
    st.html(
        f'<div class="rb-stack" style="margin:12px 0 4px 0"><p class="rb-serif" style="font-size:24px">'
        f"{ui.esc(heading)} · {count}</p>{context}</div>"
    )

    if selected:
        _grid(selected)
    else:
        st.html('<div class="rb-notice"><p class="rb-small">No stories for this family yet. '
                "Try another family, or share yours below.</p></div>")

    if others:
        with st.expander("Browse other families", expanded=False):
            st.html(f'<p class="rb-small rb-muted" style="margin-bottom:12px">Outside the selected '
                    f"{ui.esc(labels[choice])} results: examples from other families. Choose a family above "
                    "to make it your focus.</p>")
            _grid(others)

    _share_story()
    ui.footer()


def _share_story() -> None:
    chips = "".join(ui.pill(t, "small") for t in ["Kitchen work", "Interview prep", "Bus route", "Schedules", "Licensing"])
    st.html(
        '<div class="rb-card" style="flex-direction:row;align-items:center;justify-content:space-between;'
        'margin-top:28px;padding:32px 40px">'
        '<div class="rb-stack" style="gap:10px;max-width:640px">'
        '<span class="rb-pill mint small" style="align-self:flex-start">Growth &amp; training</span>'
        '<p class="rb-serif" style="font-size:28px">Share your story</p>'
        '<p class="rb-small rb-muted">What helped you take a next step? Leave out names, addresses, or other '
        "details you don’t want shared.</p>"
        f'<div class="rb-row" style="gap:8px">{chips}</div></div>'
        f"{_illustration()}</div>"
    )
    with st.container(key="card_share"):
        st.html('<p class="rb-serif" style="font-size:24px">Your story</p>')
        with st.form("share_story", clear_on_submit=True, border=False):
            text = st.text_area("Your story", label_visibility="collapsed", height=120,
                                placeholder="Example: the work you do now, how you got there, and one thing you wish you'd known.")
            agree = st.checkbox("I agree to have my story reviewed for sharing with this community.")
            sent = st.form_submit_button("Submit story", type="primary")
        if sent:
            if not text.strip():
                st.warning("Write a few words first.")
            elif not agree:
                st.warning("Please check the box so a reviewer can read it.")
            else:
                st.success("Thank you. In this demo, nothing is sent, saved, or posted.")
        st.html('<p class="rb-small rb-muted">Stories are reviewed before posting. Demo form only: '
                "nothing is sent, saved, or posted.</p>")
