"""Public homepage + log-in dialog (Figma: "A · Homepage", "B · Log in over homepage")."""

from __future__ import annotations

import streamlit as st

import auth
import data
import nav
import ui

# Illustration layers exported from Figma, positioned with the frame's insets
# (top, right, bottom, left as % of the 540x410 frame).
_HERO_LAYERS = [
    ("winding-path", "31.22%", "20.01%", "6.1%", "23.33%"),
    ("distant-woman", "14.88%", "27.15%", "66.34%", "65.15%"),
    ("rear-garden", "31.87%", "17.04%", "50.49%", "57.47%"),
    ("hair-back", "14.77%", "47.45%", "66.34%", "37.82%"),
    ("trousers-and-shoes", "52.44%", "39.35%", "16.59%", "33.21%"),
    ("arms", "38.29%", "37.52%", "43.22%", "32.74%"),
    ("blouse", "31.2%", "47.04%", "45.85%", "38.33%"),
    ("head-and-expression", "19.02%", "48.86%", "66.3%", "41.85%"),
    ("left-flower-border", "59.22%", "68.75%", "17.8%", "13.33%"),
    ("right-flower-border", "54.02%", "15.93%", "16.1%", "66.3%"),
]


def _hero_illustration() -> str:
    layers = "".join(
        f'<div style="position:absolute;inset:{t} {r} {b} {l}">'
        f'<img src="{ui.asset_uri(f"illustration/{name}.svg")}" alt="" '
        f'style="display:block;width:100%;height:100%;max-width:none" /></div>'
        for name, t, r, b, l in _HERO_LAYERS
    )
    return (
        '<div role="img" aria-label="A woman walks along a winding, blooming path toward a friend who waves" '
        f'style="position:relative;width:540px;height:410px;max-width:100%;margin-left:auto">{layers}</div>'
    )


def _start_guest(page: str = "my_path") -> None:
    auth.login_guest()
    nav.go(page)


@st.dialog(" ", width="medium")
def _login_dialog(title: str) -> None:
    st.html(
        f'<p class="rb-serif" style="font-size:40px;margin:-28px 0 8px 0">{ui.esc(title)}</p>'
        '<p class="rb-small rb-muted" style="font-size:17px">No password to remember. Choose a text or email.</p>'
    )
    phone = st.text_input("Phone number", placeholder="(415) 555-0123", key="login_phone")
    if st.button("Text me a code", type="primary", use_container_width=True, key="login_text"):
        ok, msg = auth.login_passwordless(phone, "phone", st.session_state.get("login_program", ""))
        if ok:
            st.toast("Demo sign-in: no text message is actually sent.")
            st.rerun()
        st.error(msg)

    st.html(
        '<div style="display:flex;align-items:center;gap:16px;margin:4px 0">'
        '<div class="rb-divider"></div><span class="rb-muted" style="font-size:15px">or</span>'
        '<div class="rb-divider"></div></div>'
    )
    email = st.text_input("Email address", placeholder="you@example.com", key="login_email")
    if st.button("Send me a link", type="secondary", use_container_width=True, key="login_link"):
        ok, msg = auth.login_passwordless(email, "email", st.session_state.get("login_program", ""))
        if ok:
            st.toast("Demo sign-in: no email is actually sent.")
            st.rerun()
        st.error(msg)

    if st.checkbox("I have a code from my reentry program.", key="login_has_code"):
        st.text_input("Program code", key="login_program")

    st.html('<div class="rb-divider" style="margin:4px 0"></div>')
    if st.button("Continue as guest (nothing is saved).", use_container_width=True, key="login_guest"):
        _start_guest()
        st.rerun()
    st.html(
        '<p class="rb-small rb-muted" style="text-align:center">'
        "With an account, your story and path are saved. Delete them anytime.</p>"
    )


def _nav_bar() -> None:
    left, right = st.columns([1, 1.25], vertical_alignment="center")
    with left:
        st.html(ui.brand())
    with right:
        links, login = st.columns([4, 1], vertical_alignment="center")
        with links:
            st.html(
                '<div style="display:flex;justify-content:flex-end;gap:36px;font-weight:700;font-size:17px">'
                '<a href="#how-it-works" style="color:var(--rb-ink);text-decoration:none">How it works</a>'
                '<a href="#stories" style="color:var(--rb-ink);text-decoration:none">Stories</a>'
                '<a href="#for-organizations" style="color:var(--rb-ink);text-decoration:none">For organizations</a>'
                "</div>"
            )
        with login:
            if st.button("Log in", key="nav_login", use_container_width=True):
                _login_dialog("Welcome back.")


def _hero() -> None:
    copy, art = st.columns([650, 540], gap="large", vertical_alignment="center")
    with copy:
        st.html(
            '<div class="rb-stack" style="gap:24px;padding-top:30px">'
            '<p class="rb-eyebrow" style="letter-spacing:1px">Your experience counts.</p>'
            '<p class="rb-serif" style="font-size:60px;line-height:1.1;letter-spacing:-1.5px">'
            "Everything you grew inside counts out here.</p>"
            '<p class="rb-muted" style="font-size:20px;line-height:1.5;margin:0;max-width:620px">'
            "Turn the work you did inside into a résumé, real job matches, and a path from women "
            "who started where you are.</p></div>"
        )
        with st.container(horizontal=True, gap="medium", vertical_alignment="center"):
            if st.button("Start my story", type="primary", key="hero_start"):
                _login_dialog("Start your story.")
            st.button("Continue as guest", type="tertiary", key="hero_guest", on_click=_start_guest)
        st.html('<p class="rb-muted" style="font-size:16px;margin:0">For women finding work after jail or prison. At your pace.</p>')
    with art:
        st.html(_hero_illustration())


def _how_it_works() -> None:
    steps = [
        ("message-circle", ui.PEACH, "1. Tell your story", "Type, talk or upload. Start with the work you know."),
        ("sprout", ui.LAVENDER, "2. See your path", "Explore jobs, wages and training that fit your next step."),
        ("heart-handshake", ui.MINT, "3. Take the next step", "Build a cover letter and ask for mentor intros."),
    ]
    cols = "".join(
        f'<div style="display:flex;gap:16px;flex:1">'
        f'<div style="width:48px;height:48px;border-radius:999px;background:{bg};display:flex;'
        f'align-items:center;justify-content:center;flex:none">{ui.icon(ic, 20)}</div>'
        f'<div class="rb-stack"><p style="margin:0;font-weight:800;font-size:20px">{t}</p>'
        f'<p class="rb-muted" style="margin:0;font-size:17px;line-height:1.45">{d}</p></div></div>'
        for ic, bg, t, d in steps
    )
    st.html(
        '<div id="how-it-works" class="rb-stack" style="gap:24px;padding-top:28px">'
        '<p class="rb-serif" style="font-size:34px">A next step, not a fresh start from zero.</p>'
        f'<div style="display:flex;gap:32px">{cols}</div></div>'
    )


def _paths_preview() -> None:
    head, link = st.columns([3, 1], vertical_alignment="bottom")
    with head:
        st.html(
            '<div id="stories" class="rb-stack" style="gap:6px;padding-top:20px">'
            '<p class="rb-serif" style="font-size:32px">Women who started where you are.</p>'
            '<p class="rb-muted" style="margin:0;font-size:16px">Example paths · synthetic demo stories</p></div>'
        )
    with link:
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button("Explore Paths →", type="tertiary", key="explore_paths",
                      on_click=_start_guest, args=("paths",))

    cards = []
    for i, p in enumerate(data.load_paths()[:2]):
        caution = (
            f'<p class="rb-muted" style="margin:0;font-size:16px;line-height:1.4">{ui.esc(p["licensing_note"])}</p>'
            if p.get("licensing_note") else ""
        )
        cards.append(
            '<div class="rb-card" style="box-shadow:none;border-color:var(--rb-border)">'
            f'<div class="rb-row" style="gap:14px">{ui.avatar(p["name"], 48, "lav" if i else "")}'
            f'<p class="rb-serif" style="font-size:26px">{ui.esc(p["first_name"])}</p></div>'
            f'<div class="rb-row"><span style="font-weight:700;font-size:18px">{ui.esc(p["from"])}</span>'
            f'{ui.icon("arrow-right", 20)}<span style="font-weight:800;font-size:18px;color:var(--rb-primary)">'
            f'{ui.esc(p["to"])}</span></div>'
            f'<p class="rb-muted" style="margin:0;font-size:16px;line-height:1.45">{ui.esc(p["summary"])}</p>'
            f"{caution}</div>"
        )
    st.html(f'<div class="rb-grid2">{"".join(cards)}</div>')


def _trust_and_footer() -> None:
    st.html(
        '<div class="rb-bleed rb-trust" style="margin-top:24px">'
        f'<div>{ui.icon("shield-check")}Guest mode saves nothing</div>'
        f'<div>{ui.icon("heart")}You choose what to share</div>'
        f'<div>{ui.icon("info")}Not legal advice.</div></div>'
        '<div id="for-organizations" style="display:flex;justify-content:space-between;align-items:center;'
        'padding:28px 0 0 0;font-size:16px">'
        '<div class="rb-stack" style="color:var(--rb-muted)">'
        '<span style="font-weight:800">Partner organizations · placeholders only</span>'
        '<span style="white-space:pre">[Reentry organization]     [Workforce partner]</span></div>'
        '<div style="display:flex;gap:28px;color:var(--rb-ink)"><span>Privacy</span><span>Contact</span></div></div>'
    )


def render() -> None:
    _nav_bar()
    _hero()
    _how_it_works()
    _paths_preview()
    _trust_and_footer()
