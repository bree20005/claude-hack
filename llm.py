"""Claude wrapper for Rebloom (Next Chapter).

If no API key is configured, calls return canned demo output so the whole app runs
with no key and no network. Add ANTHROPIC_API_KEY to .streamlit/secrets.toml (never
commit it) to use Claude.

Both calls use structured outputs (JSON schema), so callers always get a dict:
  - generate_profile_and_matches -> {"skills_profile": {...}, "matches": [...]}
  - generate_cover_letter        -> {"letter": str, "record_script": [str]}
All wages/facts come from data.py, never from here.
"""

from __future__ import annotations

import json

import anthropic
import streamlit as st

_MODEL = "claude-opus-5-5"
# Server-side refusal fallback: if the model declines, the API reroutes the request.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# --- canned output so the app runs with no API key ---------------------------
_STUB_PROFILE = {
    "skills_profile": {
        "summary": "You bring 3 years of high-volume food service, inventory tracking, and "
        "training new workers. Your year on a cleaning crew adds hands-on experience keeping "
        "shared spaces clean and working with a team.",
        "skills": ["Food preparation", "Inventory tracking", "Training coworkers", "Cleaning", "Teamwork"],
        "experience": ["Kitchen worker · Jail kitchen · 3 years", "Cleaning crew member · 1 year"],
        "strengths": "Running food prep and training new workers.",
        "fits_now": "Daytime hours in San Francisco, near transit. No car; two kids to plan around.",
    },
    "matches": [
        {
            "soc": "35-2014",
            "why_it_fits": "Your kitchen experience is a strong starting point.",
            "first_step": "Look for daytime kitchens near transit; ask about shift times.",
        },
        {
            "soc": "37-2011",
            "why_it_fits": "Your year on a cleaning crew is relevant experience.",
            "first_step": "Look for day crews on transit routes; many roles run at night.",
        },
        {
            "soc": "31-1131",
            "why_it_fits": "Your teamwork and cleaning experience may transfer.",
            "first_step": "Check licensing first, before paying for a course.",
        },
    ],
}

_STUB_LETTER = {
    "letter": (
        "Dear Hiring Team,\n\n"
        "I'm applying for the Cook position. I bring three years of kitchen work and one year "
        "on a cleaning crew. I'm looking for a chance to use that experience, learn how your "
        "kitchen works, and contribute to your team.\n\n"
        "My time in a kitchen gave me real work experience that I want to build on. Cooking takes "
        "preparation, attention to the work around you, and people working together. My cleaning "
        "experience is another part of what I bring to a workplace where keeping shared spaces "
        "clean matters.\n\n"
        "I'm seeking daytime hours and a location I can reach by public transit. I would appreciate "
        "discussing the schedule so we can see whether this role is a good fit.\n\n"
        "Thank you for considering my application.\n\n"
        "Sincerely,\nMaria"
    ),
    "record_script": [
        "I have a record and have spent time in jail.",
        "During that time, I worked in a kitchen for three years and on a cleaning crew for one year.",
        "I'm focused on my next chapter and would like to talk about how that experience fits this job.",
    ],
}


def _client() -> anthropic.Anthropic | None:
    """Return an Anthropic client if a key is set, else None."""
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # noqa: BLE001 - no secrets file at all
        api_key = None
    return anthropic.Anthropic(api_key=api_key) if api_key else None


def call_claude_json(system: str, user: str, schema: dict, fallback: dict) -> dict:
    """Call Claude with a JSON schema; return the parsed dict. Falls back to
    `fallback` with no key, on refusal, or on any API error (the demo cannot hard-fail)."""
    client = _client()
    if client is None:
        return fallback
    try:
        resp = client.beta.messages.create(
            model=_MODEL,
            max_tokens=16000,
            betas=[_FALLBACK_BETA],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError:
        st.warning("Using demo output: the Claude API key was rejected (it may have expired).")
        return fallback
    except anthropic.RateLimitError:
        st.warning("Using demo output: Claude is busy right now. Try again in a minute.")
        return fallback
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        st.warning(f"Using demo output (Claude call failed: {e}).")
        return fallback

    if resp.stop_reason in ("refusal", "max_tokens"):
        st.warning("Using demo output (Claude could not complete this request).")
        return fallback
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        st.warning("Using demo output (Claude returned an unexpected format).")
        return fallback


# Convenience wrappers used by the views -------------------------------------
def generate_profile_and_matches(answers: dict, jobs: list[dict]) -> dict:
    from prompts import PROFILE_SCHEMA, PROFILE_SYSTEM, build_profile_prompt

    return call_claude_json(
        PROFILE_SYSTEM, build_profile_prompt(answers, jobs), PROFILE_SCHEMA, _STUB_PROFILE
    )


def generate_cover_letter(profile: dict, job: dict, answers: dict, name: str = "", say_where: bool = False) -> dict:
    from prompts import LETTER_SCHEMA, LETTER_SYSTEM, build_letter_prompt

    return call_claude_json(
        LETTER_SYSTEM,
        build_letter_prompt(profile, job, answers, name, say_where),
        LETTER_SCHEMA,
        _STUB_LETTER,
    )
