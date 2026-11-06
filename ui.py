"""Rebloom design system for Streamlit.

Tokens, global CSS and small HTML builders that mirror the Figma file
("Rebloom" prototype). Views compose these instead of hardcoding styles.

Conventions:
  - Static markup is rendered with `st.html(...)` using the `rb-*` classes below.
  - Interactive blocks (cards that hold buttons) are `st.container(key=...)`.
    Streamlit adds a `st-key-<key>` class, so a key prefix picks the look:
      card_*  -> white card         lav_*  -> lavender panel
      pink_*  -> "next step" pink   plain_* -> no chrome
"""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).parent / "assets"

# --- design tokens (from Figma) -------------------------------------------
INK = "#3d2a3a"
MUTED = "#715965"
PRIMARY = "#c2416b"
BG = "#fff5f3"
BORDER = "#eadcd8"
BORDER_SOFT = "#eadadf"
PEACH = "#ffd9cc"
LAVENDER = "#ede3f5"
MINT = "#edf4ef"
MINT_INK = "#41654c"
SAGE = "#7fa88b"
PINK_SOFT = "#fcedf1"

# Short labels for job families (SOC major group), as used on Figma chips.
SHORT_FAMILY = {
    "21": "Community Service",
    "31": "Healthcare",
    "35": "Food",
    "37": "Building & Grounds",
    "39": "Personal Care",
    "41": "Retail",
    "43": "Office",
    "47": "Trades",
    "53": "Warehouse",
}


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


@lru_cache(maxsize=None)
def asset_uri(rel_path: str) -> str:
    """Data URI for a file under assets/ (SVGs exported from Figma)."""
    data = (ASSETS / rel_path).read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(data).decode()


def icon(name: str, size: int = 20) -> str:
    return (
        f'<img src="{asset_uri(f"icons/{name}.svg")}" alt="" '
        f'style="width:{size}px;height:{size}px;display:block;flex:none" />'
    )


def initials(name: str) -> str:
    parts = [p for p in str(name).replace(".", "").split() if p]
    return "".join(p[0].upper() for p in parts[:2]) or "?"


# --- global CSS -------------------------------------------------------------
_CSS = f"""
<style>
/* Fonts (Fraunces, Nunito) are loaded via .streamlit/config.toml [theme]. */
:root {{
  --rb-ink:{INK}; --rb-muted:{MUTED}; --rb-primary:{PRIMARY}; --rb-bg:{BG};
  --rb-border:{BORDER}; --rb-border-soft:{BORDER_SOFT}; --rb-peach:{PEACH};
  --rb-lav:{LAVENDER}; --rb-mint:{MINT}; --rb-sage:{SAGE};
}}

html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: var(--rb-bg) !important;
  color: var(--rb-ink);
  font-family: 'Nunito', sans-serif;
}}
.stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button {{
  font-family: 'Nunito', sans-serif;
}}
header[data-testid="stHeader"] {{ display: none !important; }}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}

.block-container, [data-testid="stMainBlockContainer"] {{
  max-width: 1440px !important;
  padding: 32px 80px 48px 80px !important;
}}

/* ---------- type ---------- */
.rb-serif {{ font-family: 'Fraunces', serif !important; font-weight: 600; color: var(--rb-ink);
  font-variation-settings: "SOFT" 0, "WONK" 1; margin: 0; }}
.rb-eyebrow {{ font-weight: 800; font-size: 16px; letter-spacing: 1.5px; color: var(--rb-primary);
  text-transform: uppercase; margin: 0; }}
.rb-eyebrow.muted {{ color: var(--rb-muted); font-size: 14px; letter-spacing: 1px; }}
.rb-h1 {{ font-size: 42px; line-height: 1.15; }}
.rb-h2 {{ font-size: 32px; line-height: 1.2; }}
.rb-h3 {{ font-size: 26px; line-height: 1.3; }}
.rb-body {{ font-size: 18px; line-height: 1.5; color: var(--rb-ink); margin: 0; }}
.rb-small {{ font-size: 16px; line-height: 1.5; color: var(--rb-ink); margin: 0; }}
.rb-muted {{ color: var(--rb-muted) !important; }}
.rb-sage {{ color: var(--rb-sage) !important; }}
.rb-strong {{ font-weight: 800; }}
.rb-semibold {{ font-weight: 600; }}
.rb-stack {{ display: flex; flex-direction: column; gap: 8px; }}
.rb-row {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}

/* ---------- brand / header ---------- */
.rb-brand {{ display: flex; align-items: center; gap: 10px; }}
.rb-brand span {{ font-family: 'Fraunces', serif !important; font-weight: 600; font-size: 32px; color: var(--rb-ink);
  font-variation-settings: "SOFT" 0, "WONK" 1; line-height: 1; }}
.rb-promise {{ display: flex; align-items: center; justify-content: flex-end; gap: 24px; }}
.rb-promise p {{ margin: 0; font-size: 18px; color: var(--rb-muted); }}
.rb-session {{ background: #fff; border: 1px solid var(--rb-border); border-radius: 999px;
  padding: 7px 14px; font-weight: 800; font-size: 16px; color: var(--rb-primary); white-space: nowrap; }}

/* ---------- pills / chips ---------- */
.rb-pill {{ display: inline-flex; align-items: center; gap: 5px; border-radius: 999px; padding: 6px 12px;
  font-size: 16px; line-height: 1.35; color: var(--rb-ink); background: var(--rb-peach); white-space: nowrap; }}
.rb-pill.lav {{ background: var(--rb-lav); }}
.rb-pill.mint {{ background: var(--rb-mint); color: {MINT_INK}; font-weight: 700; }}
.rb-pill.white {{ background: #fff; border: 1px solid var(--rb-border); font-weight: 700; }}
.rb-pill.bold {{ font-weight: 700; }}
.rb-pill.small {{ font-size: 14px; padding: 3px 10px; }}
.rb-badge-free {{ display: inline-block; background: {SAGE}; color: #fff; font-weight: 800; font-size: 14px;
  border-radius: 999px; padding: 2px 10px; }}

/* ---------- avatars ---------- */
.rb-avatar {{ display: flex; align-items: center; justify-content: center; border-radius: 999px; flex: none;
  background: var(--rb-peach); color: var(--rb-ink); font-weight: 800; }}
.rb-avatar.lav {{ background: var(--rb-lav); }}

/* ---------- static cards ---------- */
.rb-card {{ background: #fff; border: 1px solid var(--rb-border-soft); border-radius: 20px; padding: 24px;
  box-shadow: 0 6px 24px rgba(194,65,107,.06); display: flex; flex-direction: column; gap: 14px; height: 100%;
  box-sizing: border-box; }}
.rb-panel {{ background: var(--rb-lav); border-radius: 16px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }}
.rb-panel.lg {{ border-radius: 20px; padding: 24px; }}
.rb-warn {{ background: #fff4d6; border: 1px solid #f0d27a; border-radius: 12px; padding: 12px 14px;
  font-size: 15px; color: #6b4f00; line-height: 1.45; }}
.rb-notice {{ background: #fff; border: 1px solid var(--rb-border-soft); border-radius: 16px; padding: 18px 20px;
  box-shadow: 0 6px 24px rgba(194,65,107,.06); }}
.rb-grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
.rb-divider {{ height: 1px; background: var(--rb-border-soft); width: 100%; }}

/* ---------- chat ---------- */
.rb-msg {{ display: flex; flex-direction: column; gap: 7px; margin: 0; }}
.rb-msg.user {{ align-items: flex-end; }}
.rb-msg .who {{ font-weight: 700; font-size: 16px; color: var(--rb-muted); margin: 0; }}
.rb-bubble {{ font-size: 18px; line-height: 1.5; color: var(--rb-ink); padding: 16px 24px; max-width: 75%;
  white-space: pre-wrap; box-sizing: border-box; }}
.rb-msg.bot .rb-bubble {{ background: var(--rb-lav); border-radius: 6px 20px 20px 20px; max-width: 82%; }}
.rb-msg.user .rb-bubble {{ background: #fff; border-radius: 20px 6px 20px 20px; }}
.rb-petals {{ display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }}
.rb-petals .row {{ display: flex; gap: 7px; align-items: flex-end; }}
.rb-petals p {{ margin: 0; font-size: 14px; color: var(--rb-muted); }}

/* recap table */
.rb-facts {{ background: #fff; border-radius: 20px; padding: 20px; display: flex; flex-direction: column; gap: 12px; }}
.rb-facts .r {{ display: flex; gap: 20px; line-height: 1.5; }}
.rb-facts .k {{ width: 130px; flex: none; font-weight: 800; font-size: 16px; color: var(--rb-muted); }}
.rb-facts .v {{ font-size: 18px; color: var(--rb-ink); }}

/* ---------- timeline (Paths) ---------- */
.rb-step {{ display: flex; gap: 14px; padding: 12px 0 18px 0; position: relative; }}
.rb-step::before {{ content: ""; position: absolute; left: 19px; top: 52px; bottom: -12px; width: 2px;
  background: var(--rb-border-soft); }}
.rb-step.last::before {{ display: none; }}
.rb-step .ic {{ width: 40px; height: 40px; border-radius: 999px; background: #fff; border: 1px solid var(--rb-border-soft);
  display: flex; align-items: center; justify-content: center; flex: none; position: relative; z-index: 1; }}
.rb-step .ic.done {{ background: var(--rb-mint); }}
.rb-step .ic.next {{ background: var(--rb-primary); border-color: var(--rb-primary); }}
.rb-step .t {{ font-weight: 800; font-size: 18px; color: var(--rb-ink); margin: 0; }}
.rb-step .d {{ font-size: 16px; color: var(--rb-muted); margin: 0; }}

/* ---------- full-bleed bands ---------- */
.rb-bleed {{ width: 100vw; position: relative; left: 50%; margin-left: -50vw; box-sizing: border-box; }}
.rb-trust {{ background: var(--rb-lav); height: 76px; display: flex; align-items: center;
  justify-content: space-between; padding: 0 max(180px, calc((100vw - 1440px)/2 + 180px)); }}
.rb-trust div {{ display: flex; gap: 10px; align-items: center; font-weight: 700; font-size: 16px; color: var(--rb-ink); }}
.rb-footer {{ border-top: 1px solid var(--rb-border-soft); background: #fff; margin-top: 32px;
  padding: 28px max(80px, calc((100vw - 1440px)/2 + 80px)); }}
.rb-footer p {{ margin: 0; font-size: 16px; color: var(--rb-muted); }}

/* ---------- Streamlit widgets ---------- */
/* buttons: pill shapes from Figma */
.stButton button, .stDownloadButton button, .stLinkButton a, .stFormSubmitButton button {{
  border-radius: 999px !important; min-height: 48px; padding: 12px 24px !important;
  font-weight: 800 !important; font-size: 16px !important; box-shadow: none;
}}
.stButton button p, .stDownloadButton button p, .stLinkButton a p, .stFormSubmitButton button p {{
  font-weight: 800 !important; font-size: 16px !important;
}}
button[data-testid="stBaseButton-primary"], a[data-testid="stBaseLinkButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {{
  background: var(--rb-primary) !important; border: 1px solid var(--rb-primary) !important; color: #fff !important;
  box-shadow: 0 4px 12px rgba(194,65,107,.14) !important;
}}
button[data-testid="stBaseButton-primary"]:hover, a[data-testid="stBaseLinkButton-primary"]:hover {{
  background: #a8355b !important; border-color: #a8355b !important;
}}
button[data-testid="stBaseButton-secondary"], a[data-testid="stBaseLinkButton-secondary"],
button[data-testid="stBaseButton-secondaryFormSubmit"] {{
  background: #fff !important; border: 1px solid var(--rb-border) !important; color: var(--rb-ink) !important;
}}
button[data-testid="stBaseButton-secondary"]:hover {{ border-color: var(--rb-primary) !important; color: var(--rb-primary) !important; }}
button[data-testid="stBaseButton-tertiary"] {{
  min-height: 0 !important; padding: 0 !important; color: var(--rb-primary) !important; background: none !important;
}}
button[data-testid="stBaseButton-tertiary"] p {{ text-decoration: underline; text-underline-offset: 3px; font-size: 17px !important; }}

/* top navigation tabs (buttons inside the topnav container) */
.st-key-topnav {{ border-bottom: 1px solid var(--rb-border); gap: 48px !important; margin-bottom: 20px; }}
.st-key-topnav button[data-testid="stBaseButton-tertiary"] {{
  border-radius: 0 !important; padding: 0 0 16px 0 !important; border-bottom: 3px solid transparent !important;
  color: var(--rb-muted) !important;
}}
.st-key-topnav button[data-testid="stBaseButton-tertiary"] p {{
  text-decoration: none; font-size: 18px !important; font-weight: 500 !important;
}}

/* text inputs */
.stTextInput input, .stTextArea textarea {{
  background: #fff !important; border-radius: 12px !important; font-size: 17px !important; color: var(--rb-ink) !important;
}}
.stTextInput [data-baseweb="input"], .stTextArea [data-baseweb="textarea"] {{
  border: 1px solid var(--rb-border) !important; border-radius: 12px !important; background: #fff !important;
}}
.stTextInput label p, .stTextArea label p {{ font-weight: 800 !important; font-size: 16px !important; color: var(--rb-ink) !important; }}

/* pills (filters) */
[data-testid="stButtonGroup"] button {{
  border-radius: 999px !important; border: 1px solid var(--rb-border-soft) !important; background: #fff !important;
  min-height: 40px; padding: 8px 16px !important;
}}
[data-testid="stButtonGroup"] button p {{ font-weight: 700 !important; font-size: 15px !important; color: var(--rb-ink); }}
[data-testid="stButtonGroup"] button[kind="pillsActive"], [data-testid="stButtonGroup"] button[aria-checked="true"] {{
  background: var(--rb-primary) !important; border-color: var(--rb-primary) !important;
  box-shadow: 0 4px 12px rgba(194,65,107,.14);
}}
[data-testid="stButtonGroup"] button[kind="pillsActive"] p, [data-testid="stButtonGroup"] button[aria-checked="true"] p {{ color: #fff !important; }}
[data-testid="stWidgetLabel"] p {{ font-weight: 800; font-size: 16px; color: var(--rb-ink); }}

/* expanders */
[data-testid="stExpander"] details {{ border: 1px solid var(--rb-border-soft) !important; border-radius: 16px !important; background: #fff; }}
[data-testid="stExpander"] summary p {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 18px; color: var(--rb-ink); }}

/* key-styled containers */
[class*="st-key-card_"] {{
  background: #fff; border: 1px solid #e7d6d6; border-radius: 20px; padding: 28px;
  box-shadow: 0 8px 24px rgba(61,42,58,.07); gap: 22px;
}}
[class*="st-key-lav_"] {{ background: var(--rb-lav); border-radius: 20px; padding: 26px; gap: 16px; }}
[class*="st-key-lavsm_"] {{ background: var(--rb-lav); border-radius: 16px; padding: 16px; gap: 10px; }}
[class*="st-key-indent_"] {{ padding-left: 54px; }}
[class*="st-key-pink_"] {{ background: {PINK_SOFT}; border-radius: 16px; padding: 14px 12px 14px 0; gap: 8px; }}

/* chat input = the "unified composer" */
[data-testid="stBottom"], [data-testid="stBottom"] > div {{ background: var(--rb-bg) !important; }}
[data-testid="stBottomBlockContainer"] {{ max-width: 840px !important; padding: 12px 40px 28px 40px !important; }}
[data-testid="stBottomBlockContainer"]::after {{
  content: "Nothing you type is saved. Rebloom can make mistakes."; display: block; text-align: center;
  font-size: 14px; color: var(--rb-muted); margin-top: 12px;
}}
[data-testid="stChatInput"] {{
  background: #fff !important; border: 1px solid var(--rb-border) !important; border-radius: 24px !important;
  box-shadow: 0 8px 28px rgba(108,51,71,.06); padding: 14px 12px 14px 20px;
}}
[data-testid="stChatInput"] textarea {{ font-size: 18px !important; color: var(--rb-ink) !important; min-height: 64px; }}
[data-testid="stChatInputSubmitButton"] {{ background: var(--rb-primary) !important; border-radius: 999px !important;
  width: 40px; height: 40px; color: #fff !important; }}
[data-testid="stChatInputSubmitButton"] svg {{ fill: #fff !important; color: #fff !important; }}

/* toggle */
[data-testid="stToggle"] label p {{ font-size: 16px; font-weight: 600; color: var(--rb-ink); }}

/* dialog */
div[role="dialog"] {{ border-radius: 20px !important; background: #fff !important; }}
div[role="dialog"] h2, div[role="dialog"] [data-testid="stDialogTitle"] {{
  font-family: 'Fraunces', serif !important; font-weight: 600 !important; font-size: 40px !important; color: var(--rb-ink) !important;
}}
</style>
"""


def inject_css() -> None:
    st.html(_CSS)


def active_nav_css(key: str) -> None:
    """Underline the active top tab (key of the nav button)."""
    st.html(
        f"<style>.st-key-{key} button[data-testid='stBaseButton-tertiary']"
        f"{{border-bottom-color:{PRIMARY} !important;}}"
        f".st-key-{key} button[data-testid='stBaseButton-tertiary'] p"
        f"{{color:{INK} !important;font-weight:800 !important;}}</style>"
    )


# --- building blocks ----------------------------------------------------------
def brand() -> str:
    return f'<div class="rb-brand">{icon("flower-2", 34)}<span>Rebloom</span></div>'


def pill(text: str, variant: str = "") -> str:
    return f'<span class="rb-pill {variant}">{esc(text)}</span>'


def family_pill(family: str, variant: str = "") -> str:
    return pill(family, variant)


def avatar(name: str, size: int = 48, variant: str = "") -> str:
    font = max(14, int(size * 0.36))
    return (
        f'<div class="rb-avatar {variant}" style="width:{size}px;height:{size}px;font-size:{font}px">'
        f"{esc(initials(name))}</div>"
    )


def page_intro(eyebrow: str, title: str, subtitle: str = "", eyebrow_muted: bool = False) -> None:
    sub = f'<p class="rb-small" style="margin-top:4px">{esc(subtitle)}</p>' if subtitle else ""
    st.html(
        f'<div class="rb-stack" style="gap:12px;margin:8px 0 12px 0">'
        f'<p class="rb-eyebrow {"muted" if eyebrow_muted else ""}">{esc(eyebrow)}</p>'
        f'<p class="rb-serif rb-h1">{esc(title)}</p>{sub}</div>'
    )


def petals(shared: int, total: int = 7, note: str = "") -> str:
    """Progress petals: filled petals for shared topics, closed buds for the rest."""
    row = "".join(
        f'<img src="{asset_uri("icons/petal-shared.svg")}" style="width:24px;height:28px" alt="" />'
        if i < shared
        else f'<img src="{asset_uri("icons/petal-optional.svg")}" style="width:14.26px;height:28px" alt="" />'
        for i in range(total)
    )
    label = f"{shared} of {total} topics shared" + (f" · {note}" if note else "")
    return (
        f'<div class="rb-petals" role="img" aria-label="{esc(label)}">'
        f'<div class="row">{row}</div><p>{esc(label)}</p></div>'
    )


def chat_bubble(role: str, who: str, text: str) -> str:
    cls = "user" if role == "user" else "bot"
    return (
        f'<div class="rb-msg {cls}"><p class="who">{esc(who)}</p>'
        f'<div class="rb-bubble">{esc(text)}</div></div>'
    )


def footer(text: str = "Not legal advice · Licensing and fair-chance rules vary by employer and location.") -> None:
    st.html(f'<div class="rb-bleed rb-footer"><p>{esc(text)}</p></div>')


def money(x: float) -> str:
    return f"${x:,.0f}/hr"


def is_free(cost: str) -> bool:
    c = (cost or "").strip().lower()
    return c in {"free", "no cost", "$0"} or c.startswith("free")
