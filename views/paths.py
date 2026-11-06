"""Paths: example journeys from a starting point inside to work outside.

Figma: "Rebloom · Paths". Stories and wages come from data/paths.json and are
synthetic/illustrative, and the screen says so.
"""

from __future__ import annotations

import streamlit as st

import data
import nav
import ui


def _tags_for_family(code: str) -> list[str]:
    return [t["id"] for t in data.industry_tags() if code in t.get("soc_families", [])][:1]


def _wage_chart(steps: list[dict]) -> str:
    """Inline SVG of hourly wage for the paid steps (Figma: 248x232 chart)."""
    paid = [(i + 1, s) for i, s in enumerate(steps) if s.get("wage")]
    if len(paid) < 2:
        return ""
    w, h = 248, 232

    def y(v: float) -> float:  # $30 -> 36px, $10 -> 176px
        return 36 + (30 - v) / 20 * 140

    x0, x1 = 51, 225
    xs = [x0 + i * (x1 - x0) / (len(paid) - 1) for i in range(len(paid))]
    grid = "".join(
        f'<text x="0" y="{y(v) + 5:.0f}" font-size="15" fill="{ui.MUTED}">${v}</text>'
        f'<line x1="39" x2="{w}" y1="{y(v):.0f}" y2="{y(v):.0f}" stroke="{ui.BORDER_SOFT}" />'
        for v in (30, 20, 10)
    )
    line = " ".join(f"{x:.1f},{y(s['wage']):.1f}" for x, (_, s) in zip(xs, paid))
    pts = "".join(
        f'<circle cx="{x:.1f}" cy="{y(s["wage"]):.1f}" r="5" fill="{ui.PRIMARY}" />'
        f'<text x="{x:.1f}" y="{y(s["wage"]) - 12:.1f}" text-anchor="middle" font-size="16" font-weight="800" '
        f'fill="{ui.PRIMARY}">${s["wage"]}</text>'
        f'<text x="{x:.1f}" y="215" text-anchor="middle" font-size="15" font-weight="700" fill="{ui.INK}">'
        f'{n} · {ui.esc(s.get("short", ""))}</text>'
        for x, (n, s) in zip(xs, paid)
    )
    desc = ", ".join(f"step {n} {ui.esc(s['title'])} ${s['wage']} per hour" for n, s in paid)
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Hourly pay: {desc}" '
        f'style="font-family:Nunito,sans-serif;overflow:visible">'
        f'<text x="0" y="14" font-size="15" fill="{ui.MUTED}">$/hr</text>{grid}'
        f'<polyline points="{line}" fill="none" stroke="{ui.PRIMARY}" stroke-width="2.5" />{pts}</svg>'
    )


def _step_html(n: int, s: dict, last: bool) -> str:
    status = s.get("status")
    meta = s["duration"] + (f" · ${s['wage']}/hr" if s.get("wage") else "")
    here = (' <span class="rb-pill small" style="font-weight:800;margin-left:8px">'
            f'{ui.icon("location-dot", 6)} You are here</span>' if status == "start" else "")
    ic_cls = "done" if status == "now" else ""
    return (
        f'<div class="rb-step{" last" if last else ""}"><div class="ic {ic_cls}">{ui.icon(s["icon"], 20)}</div>'
        f'<div class="rb-stack" style="gap:5px"><p class="t">{n} · {ui.esc(s["title"])}</p>'
        f'<p class="d">{ui.esc(meta)}{here}</p></div></div>'
    )


def _main_path(p: dict, user: dict) -> None:
    with st.container(key=f"card_path_{p['id']}"):
        st.html(
            f'<div class="rb-row" style="gap:16px;flex-wrap:nowrap">{ui.avatar(p["name"], 64)}'
            f'<div class="rb-stack" style="flex:1;gap:6px"><p class="rb-serif" style="font-size:28px">{ui.esc(p["name"])}</p>'
            f'<p class="rb-muted" style="margin:0;font-size:18px">{ui.esc(p["headline"])}</p></div>'
            f'{ui.pill(p["family_short"], "mint")}</div>'
            f'<p class="rb-small" style="margin-top:20px">{ui.esc(p["summary"])}</p>'
            '<div class="rb-divider" style="margin-top:20px"></div>'
        )
        steps = p["steps"]
        timeline, chart = st.columns([1, 0.62], gap="medium")
        with timeline:
            st.html('<p class="rb-eyebrow muted" style="font-size:16px;letter-spacing:0">HER PATH, ONE STEP AT A TIME</p>')
            for i, s in enumerate(steps):
                n, last = i + 1, i == len(steps) - 1
                if s.get("status") == "next":
                    with st.container(key=f"pink_next_{p['id']}"):
                        st.html(
                            f'<div style="display:flex;gap:14px"><div class="rb-step" style="padding:0">'
                            f'<div class="ic next">{ui.icon("badge-check", 20)}</div></div>'
                            '<div class="rb-stack" style="gap:6px">'
                            '<p class="rb-small rb-strong" style="color:var(--rb-primary)">Your next step</p>'
                            f'<p class="rb-strong" style="margin:0;font-size:18px">{n} · {ui.esc(s["title"])}</p>'
                            f'<p class="rb-small rb-muted">{ui.esc(s["duration"])}</p>'
                            f'<p class="rb-small" style="padding-top:5px">{ui.esc(s.get("action", ""))}</p></div></div>'
                        )
                        with st.container(horizontal=True, key=f"indent_cta_{p['id']}"):
                            st.button(s.get("cta", "Find a course near me."), type="primary", key=f"path_cta_{p['id']}",
                                      on_click=nav.go, args=("resources",), kwargs={"tags": _tags_for_family(p["family_code"])})
                else:
                    st.html(_step_html(n, s, last))
        with chart:
            svg = _wage_chart(steps)
            if svg:
                st.html(
                    '<div style="background:var(--rb-bg);border-radius:20px;padding:20px;margin-top:35px" class="rb-stack">'
                    f'<div class="rb-row" style="gap:8px">{ui.icon("trending-up", 20)}'
                    '<p class="rb-strong" style="margin:0;font-size:18px">Pay along this path</p></div>'
                    '<p class="rb-small rb-muted">Illustrative demo wages, not verified pay or a promise.</p>'
                    f"{svg}"
                    '<p class="rb-small rb-muted">Numbers match her steps. Only paid roles are plotted; '
                    "time inside and training have no wage shown.</p></div>"
                )
        st.html(
            '<div class="rb-panel lg" style="margin-top:8px"><p class="rb-small rb-strong">Her advice</p>'
            f'<p class="rb-body">“{ui.esc(p["advice"])}”</p></div>'
        )
        with st.container(horizontal=True, gap="small"):
            if st.button("Request an intro", type="primary", icon=":material/volunteer_activism:", key=f"path_intro_{p['id']}"):
                st.toast("Demo: a peer mentor team would reach out to you. Nothing is sent.")
            if st.button("Save this path.", icon=":material/bookmark:", key=f"path_save_{p['id']}"):
                if user.get("guest"):
                    st.toast("Guest mode saves nothing. Log in with a phone or email to save paths.")
                else:
                    saved = st.session_state.setdefault("saved_paths", set())
                    saved.add(p["id"])
                    st.toast(f"Saved {p['first_name']}'s path for this session.")
        st.html('<p class="rb-small rb-muted">Intros go through a peer mentor team, not direct messages.</p>')


def _other_card(p: dict, i: int) -> str:
    caution = (
        '<div style="background:var(--rb-bg);border-radius:16px;padding:14px" class="rb-stack">'
        '<p class="rb-small rb-strong">Check licensing first</p>'
        f'<p class="rb-small rb-muted" style="line-height:1.45">{ui.esc(p["licensing_note"])}</p></div>'
        if p.get("licensing_note") else ""
    )
    return (
        '<div class="rb-card" style="gap:18px">'
        f'<div class="rb-row" style="gap:12px;flex-wrap:nowrap">{ui.avatar(p["name"], 48, "lav" if i % 2 else "")}'
        f'<div class="rb-stack" style="gap:3px"><p class="rb-serif" style="font-size:24px">{ui.esc(p["first_name"])}</p>'
        '<p class="rb-small rb-muted">Another starting point</p></div></div>'
        f'<div>{ui.pill(p["family_short"], "lav bold" if i % 2 else "bold")}</div>'
        f'<div class="rb-row" style="gap:10px"><span style="font-weight:700;font-size:18px">{ui.esc(p["from"])}</span>'
        f'{ui.icon("arrow-right", 18)}<span style="font-weight:800;font-size:18px;color:var(--rb-primary)">'
        f'{ui.esc(p["to"])}</span></div>'
        f'<p class="rb-small rb-muted">{ui.esc(p["summary"])}</p>{caution}</div>'
    )


def render(user: dict) -> None:
    paths = data.load_paths()
    by_id = {p["id"]: p for p in paths}

    intro, deco = st.columns([5, 1], vertical_alignment="center")
    with intro:
        ui.page_intro("Paths", "Women who started where you are.",
                      "Time inside is real experience. See how it can become a next step toward work.")
    with deco:
        st.html(f'<div style="display:flex;justify-content:flex-end">'
                f'<img src="{ui.asset_uri("icons/opening-petals.svg")}" alt="" style="width:113px;height:28px" /></div>')

    head, note = st.columns([1, 1], vertical_alignment="bottom")
    with head:
        st.html('<p class="rb-small rb-strong">Where are you starting?</p>')
    with note:
        st.html('<p class="rb-small rb-muted" style="text-align:right">Example paths · synthetic demo stories</p>')
    st.session_state.setdefault(nav.PATHS_FILTER_KEY, paths[0]["id"])
    choice = st.pills("Where are you starting?", options=list(by_id), format_func=lambda k: by_id[k]["start_label"],
                      key=nav.PATHS_FILTER_KEY, label_visibility="collapsed") or paths[0]["id"]

    main, side = st.columns([1, 0.42], gap="medium")
    with main:
        _main_path(by_id[choice], user)
    with side:
        others = [p for p in paths if p["id"] != choice]
        st.html(
            '<div class="rb-stack" style="gap:20px">'
            '<div class="rb-stack"><p class="rb-serif" style="font-size:26px">Other paths</p>'
            '<p class="rb-small rb-muted">Different beginnings. Skills that carry forward.</p></div>'
            + "".join(_other_card(p, i) for i, p in enumerate(others))
            + '<div class="rb-stack" style="padding:8px 12px 0 12px;gap:12px">'
            f'<div class="rb-row" style="gap:8px"><img src="{ui.asset_uri("icons/opening-petal.svg")}" alt="" '
            'style="width:27px;height:28px" /><p class="rb-serif" style="font-size:22px">Your path can be your own.</p></div>'
            '<p class="rb-small rb-muted">These are examples, not a checklist. Start with what fits your life today.</p>'
            "</div></div>"
        )
    ui.footer()
