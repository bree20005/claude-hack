"""PRD 7: training programs + help centers + Know your rights.

Program facts (names, costs, lengths, links) come only from data/programs.json.
Claude only writes the optional "Why this helps you" line.
"""

from __future__ import annotations

import json

import streamlit as st

import data
import llm
import nav
import ui


def _know_your_rights() -> None:
    with st.expander("Know your rights: fair-chance hiring in California", expanded=False):
        st.html(
            '<div class="rb-stack" style="gap:10px">'
            '<p class="rb-small">• In California, most employers with 5 or more employees <strong>can’t ask about '
            "conviction history before making a job offer</strong> (the Fair Chance Act).</p>"
            '<p class="rb-small">• After an offer, if they’re considering your record, they must look at your specific '
            "situation, tell you in writing, and give you a chance to respond before a final decision.</p>"
            '<p class="rb-small">• Some jobs and licensed fields have different rules.</p>'
            '<p class="rb-small"><a href="https://calcivilrights.ca.gov/fair-chance-act/" target="_blank" '
            'style="color:var(--rb-primary);font-weight:700">California Civil Rights Department: Fair Chance Act ↗</a></p>'
            '<p class="rb-small rb-muted" style="font-size:14px">This is general information, not legal advice.</p></div>'
        )


def _why_lines(programs: list[dict]) -> dict[str, str]:
    ss = st.session_state
    tags = ss.get("mp_tags")
    if not tags or not programs:
        return {}
    key = json.dumps([tags, [p["id"] for p in programs]], sort_keys=True)
    cache = ss.setdefault("res_why", {})
    if key not in cache:
        with st.spinner("Matching programs to your experience…"):
            cache[key] = llm.program_why(ss.get("mp_summary", ""), tags, programs)
    return cache[key]


def _card(p: dict, why: str, key: str) -> None:
    badges = ui.pill("Training" if p["type"] == "training" else "Help center", "small lav bold")
    if p.get("is_free"):
        badges += '<span class="rb-badge-free">Free</span>'
    if p.get("record_friendly"):
        badges += ui.pill("Serves people with records", "small mint")
    tags = "".join(ui.pill(data.tag_label(t), "small white") for t in p.get("industry_tags", [])[:4])
    if len(p.get("industry_tags", [])) > 4:
        tags += ui.pill("All kinds of work", "small white")
    why_html = (f'<div style="background:{ui.PINK_SOFT};border-radius:12px;padding:10px 14px">'
                f'<p class="rb-small"><strong style="color:var(--rb-primary)">Why this helps you:</strong> {ui.esc(why)}</p></div>'
                if why else "")
    with st.container(key=f"card_{key}"):
        st.html(
            '<div class="rb-stack" style="gap:12px">'
            f'<div class="rb-stack" style="gap:4px"><p class="rb-serif" style="font-size:22px">{ui.esc(p["name"])}</p>'
            f'<p class="rb-small rb-muted" style="font-size:14px">{ui.esc(p["provider"])}</p></div>'
            f'<div class="rb-row" style="gap:6px">{badges}</div>'
            '<div style="display:flex;gap:20px">'
            f'<div class="rb-stack" style="gap:2px;flex:1"><p class="rb-eyebrow muted" style="font-size:12px">Cost</p><p class="rb-small rb-strong">{ui.esc(p["cost"])}</p></div>'
            f'<div class="rb-stack" style="gap:2px;flex:1"><p class="rb-eyebrow muted" style="font-size:12px">Length</p><p class="rb-small rb-strong">{ui.esc(p["length"])}</p></div>'
            f'<div class="rb-stack" style="gap:2px;flex:1.4"><p class="rb-eyebrow muted" style="font-size:12px">Where</p><p class="rb-small rb-strong">{ui.esc(p["location"])}</p></div></div>'
            f'<p class="rb-small">{ui.esc(p.get("description", ""))}</p>{why_html}'
            f'<div class="rb-row" style="gap:6px">{tags}</div></div>'
        )
        st.link_button("Visit site ↗", p["url"], type="primary", use_container_width=True)
        if p.get("last_checked"):
            st.caption(f"Last checked {p['last_checked']}. Confirm details with the provider.")


def _grid(programs: list[dict], prefix: str, why: dict[str, str]) -> None:
    for i in range(0, len(programs), 2):
        cols = st.columns(2, gap="medium")
        for col, p in zip(cols, programs[i:i + 2]):
            with col:
                _card(p, why.get(p["id"], ""), f"{prefix}_{p['id']}")


def render(user: dict) -> None:
    ui.page_intro("Resources", "Get trained and get support.", "Real programs and places that help, near San Francisco.")
    _know_your_rights()

    my_tags = (st.session_state.get("mp_tags") or {}).get("industry", [])
    options = [t["id"] for t in data.industry_tags()]
    if nav.RESOURCES_TAGS_KEY not in st.session_state:
        st.session_state[nav.RESOURCES_TAGS_KEY] = list(my_tags)
    selected = st.pills("Kind of work", options, selection_mode="multi", format_func=data.tag_label,
                        key=nav.RESOURCES_TAGS_KEY) or []
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    with c1:
        kind = st.segmented_control("Type", ["All", "Training", "Help centers"], default="All", key="res_type") or "All"
    with c2:
        free_only = st.toggle("Free only", key="res_free")

    progs = data.load_programs()
    if kind == "Training":
        progs = [p for p in progs if p["type"] == "training"]
    elif kind == "Help centers":
        progs = [p for p in progs if p["type"] == "help_center"]
    if free_only:
        progs = [p for p in progs if p.get("is_free")]
    sort_tags = selected or my_tags
    if selected:
        progs = [p for p in progs if set(p.get("industry_tags", [])) & set(selected)]
    progs = sorted(progs, key=lambda p: data.program_sort_key(p, sort_tags))

    if my_tags:
        mine = [p for p in progs if set(p.get("industry_tags", [])) & set(my_tags)][:6]
        if mine:
            why = _why_lines(mine)
            st.html('<p class="rb-serif rb-h3" style="margin-top:12px">For your job matches</p>')
            _grid(mine, "mine", why)

    st.html(f'<p class="rb-serif rb-h3" style="margin-top:20px">All programs and help centers · {len(progs)}</p>')
    if progs:
        _grid(progs, "all", st.session_state.get("res_why", {}).get(
            json.dumps([st.session_state.get("mp_tags"), [p["id"] for p in progs[:6]]], sort_keys=True), {}))
    else:
        st.html('<div class="rb-notice"><p class="rb-small">Nothing here yet for these filters. '
                "Try clearing filters, or look at Help centers: they help with any kind of work.</p></div>")
    ui.footer()
