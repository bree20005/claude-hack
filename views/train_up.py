"""Train Up: local upskilling programs by job family (Figma: "5 · Train Up · Rebloom").

TODO(stream-3): expand training.json with more real SF/Bay Area programs.
"""

from __future__ import annotations

import streamlit as st

import data
import nav
import ui
from storage import get_storage

_ALL = "all"


def _earn_after(family_code: str) -> tuple[dict | None, bool]:
    """Highest-paid matching job in the family (from jobs.json) + whether any needs a license."""
    jobs = data.jobs_for_family(family_code)
    best = max(jobs, key=lambda j: j["ca_median_hourly"], default=None)
    return best, any(j.get("licensed") for j in jobs)


def _program_card(t: dict) -> None:
    job, licensed = _earn_after(t["family_code"])
    cost = (f'<span class="rb-badge-free">{ui.esc(t["cost"])}</span>' if ui.is_free(t["cost"])
            else f'<span class="rb-strong">{ui.esc(t["cost"])}</span>')
    earn = (
        '<div style="background:var(--rb-bg);border-radius:12px;padding:12px 14px">'
        f'<p class="rb-serif" style="font-size:22px;color:var(--rb-primary)">Earn after: {ui.money(job["ca_median_hourly"])}</p>'
        f'<p class="rb-small rb-muted" style="font-size:14px">CA median for {ui.esc(job["title"])}, from our demo data. '
        "Not a promise.</p></div>" if job else ""
    )
    warn = ('<div class="rb-warn"><strong>License required.</strong> A record may affect licensing; check with '
            "the CA board before paying for training.</div>" if licensed else "")
    notes = f'<p class="rb-small">{ui.esc(t["notes"])}</p>' if t.get("notes") else ""
    with st.container(key=f"card_prog_{t['id']}"):
        st.html(
            '<div class="rb-stack" style="gap:14px">'
            f'<div class="rb-stack" style="gap:4px"><p class="rb-serif" style="font-size:22px">{ui.esc(t["name"])}</p>'
            f'<p class="rb-small rb-muted" style="font-size:14px">Provider: {ui.esc(t["provider"])}</p></div>'
            f'<div>{ui.family_pill(data.family_name(t["family_code"]), "small")}</div>'
            '<div style="display:flex;gap:24px">'
            '<div class="rb-stack" style="flex:1;gap:4px"><p class="rb-eyebrow muted" style="font-size:12px">Length</p>'
            f'<p class="rb-small rb-strong">{ui.esc(t["length"])}</p></div>'
            '<div class="rb-stack" style="flex:1;gap:4px"><p class="rb-eyebrow muted" style="font-size:12px">Cost</p>'
            f"<div>{cost}</div></div></div>"
            f'<div class="rb-stack" style="gap:2px"><p class="rb-small rb-semibold">'
            f'<span style="color:var(--rb-primary)">●</span> {ui.esc(t["location"])}</p>'
            '<p class="rb-small rb-muted" style="font-size:14px">Ask about class hours, childcare, and the nearest '
            "transit stop.</p></div>"
            f"{earn}{notes}{warn}</div>"
        )
        st.link_button("Visit site", t["url"], type="primary", use_container_width=True)


def _grid(programs: list[dict]) -> None:
    for i in range(0, len(programs), 2):
        cols = st.columns(2, gap="medium")
        for col, t in zip(cols, programs[i:i + 2]):
            with col:
                _program_card(t)


def render(user: dict) -> None:
    ui.page_intro("5 / Train Up", "Build skills for the jobs you matched.",
                  "Explore a next step near San Francisco. Start with the family that interests you.")
    st.html(
        f'<div class="rb-notice" style="margin-bottom:16px"><div class="rb-row" style="gap:8px">{ui.icon("info", 18)}'
        '<p class="rb-small rb-strong">Check details before you enroll</p></div>'
        '<p class="rb-small rb-muted" style="margin-top:6px">Programs, schedules, costs, and eligibility change. '
        "Confirm hours, cost, record eligibility, licensing, and transit access with the provider before enrolling "
        "or paying. “Earn after” is a California median example, not a promise.</p></div>"
    )

    families = data.family_options()
    codes = [_ALL] + [code for code, _ in families]
    labels = {_ALL: "All", **{code: ui.SHORT_FAMILY.get(code, name) for code, name in families}}
    st.session_state.setdefault(nav.TRAIN_FILTER_KEY, _ALL)
    choice = st.pills("Job family", options=codes, format_func=labels.get, key=nav.TRAIN_FILTER_KEY) or _ALL
    free_only = st.toggle("Free only", key="train_free_only")

    programs = data.load_training()
    if free_only:
        programs = [t for t in programs if ui.is_free(t["cost"])]
    selected = programs if choice == _ALL else [t for t in programs if t["family_code"] == choice]
    others = [] if choice == _ALL else [t for t in programs if t["family_code"] != choice]

    match = next(
        (j for m in get_storage().get_matches(user["email"])
         if (j := data.job_by_soc(m["soc"])) and j["family_code"] == choice),
        None,
    )
    count = f"{len(selected)} {'program' if len(selected) == 1 else 'programs'}"
    tag = ui.pill(labels[choice], "mint small") if choice != _ALL else ""
    context = (f'<p class="rb-small rb-muted">From the {ui.esc(match["title"])} match → {ui.esc(match["family"])}. '
               "The same family appears on jobs and women’s stories.</p>" if match else "")
    st.html(f'<div class="rb-stack" style="margin:12px 0 4px 0"><div class="rb-row">{tag}'
            f'<p class="rb-serif" style="font-size:24px">{count}</p></div>{context}</div>')

    if selected:
        _grid(selected)
    else:
        st.html('<div class="rb-notice"><p class="rb-small">No programs match these filters yet. '
                "Try another family or turn off Free only.</p></div>")

    if others:
        with st.expander("Training for your other matches", expanded=False):
            st.html(f'<p class="rb-small rb-muted" style="margin-bottom:12px">Outside the selected '
                    f'{ui.esc(labels[choice])} results. Free only is {"on" if free_only else "off"}.</p>')
            _grid(others)
    ui.footer()
