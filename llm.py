"""Claude wrapper for Next Chapter.

SKELETON BEHAVIOR: if no API key is configured, `call_claude` returns canned demo
output so the whole app runs with no key and no network. Wire the real call by adding
ANTHROPIC_API_KEY to .streamlit/secrets.toml (never commit it).

Keep the contract: callers get back a parsed dict for call #1, and a string for the
letter. All wages/facts come from data.py, never from here.
"""

from __future__ import annotations

import json

import streamlit as st

# TODO(stream-1/4): use a current model and request structured JSON output.
_MODEL = "claude-opus-4-8"

# --- canned output so the skeleton runs with no API key ------------------
_STUB_PROFILE = {
    "skills_profile": {
        "summary": "You have years of real, high-pressure work experience. You keep a "
        "team moving, handle food safely, and train others. Those are strengths "
        "employers need.",
        "skills": ["food safety", "working fast under pressure", "teamwork", "inventory"],
        "experience": [
            "Ran a high-volume kitchen line",
            "Tracked inventory and supplies",
            "Helped train new workers",
        ],
    },
    "matches": [
        {
            "soc": "35-2014",
            "why_it_fits": "Your kitchen experience maps directly to a restaurant cook role.",
            "first_step": "Apply to kitchens hiring now; mention your line experience.",
        },
        {
            "soc": "37-2011",
            "why_it_fits": "Your cleaning-crew work is steady, in-demand, and quick to start.",
            "first_step": "Ask local facilities about openings; a first steady check builds a reference.",
        },
    ],
}

_STUB_LETTER = (
    "Dear Hiring Manager,\n\n"
    "I'm writing about your cook position. I have years of hands-on experience in "
    "high-volume kitchens, preparing meals for large numbers of people every day. I know "
    "food safety, I work fast under pressure, and I help keep a team organized and calm "
    "during a rush. I've tracked inventory and trained newer workers to keep things "
    "running smoothly.\n\n"
    "I'm reliable, I show up, and I take pride in doing the job right. I'd welcome the "
    "chance to bring that energy to your kitchen.\n\n"
    "Thank you for your time.\n\n"
    "Sincerely,\nMaria\n\n"
    "---\n"
    "If your record comes up:\n"
    "\"I made mistakes in my past and I've worked hard to grow since then. What I can "
    "offer you today is real kitchen experience and someone who shows up and works hard. "
    "I'm focused on the future.\""
)


def _client():
    """Return an Anthropic client if a key is set, else None."""
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        api_key = None
    if not api_key:
        return None
    try:
        from anthropic import Anthropic

        return Anthropic(api_key=api_key)
    except Exception:
        return None


def call_claude_json(system: str, user: str, fallback: dict) -> dict:
    """Call #1 style: expect JSON back. Falls back to `fallback` with no key or on
    parse failure (so the demo cannot hard-fail)."""
    client = _client()
    if client is None:
        return fallback
    try:
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text
        return json.loads(text)
    except Exception as e:  # noqa: BLE001 - demo safety net
        st.warning(f"Using demo output (Claude call failed: {e}).")
        return fallback


def call_claude_text(system: str, user: str, fallback: str) -> str:
    """Call #2 style: expect prose back. Falls back to `fallback`."""
    client = _client()
    if client is None:
        return fallback
    try:
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=700,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text
    except Exception as e:  # noqa: BLE001 - demo safety net
        st.warning(f"Using demo output (Claude call failed: {e}).")
        return fallback


# Convenience wrappers used by the views -----------------------------------
def generate_profile_and_matches(answers: dict, jobs: list[dict]) -> dict:
    from prompts import PROFILE_SYSTEM, build_profile_prompt

    return call_claude_json(
        PROFILE_SYSTEM, build_profile_prompt(answers, jobs), _STUB_PROFILE
    )


def generate_cover_letter(profile: dict, job: dict, answers: dict) -> str:
    from prompts import LETTER_SYSTEM, build_letter_prompt

    return call_claude_text(
        LETTER_SYSTEM, build_letter_prompt(profile, job, answers), _STUB_LETTER
    )
