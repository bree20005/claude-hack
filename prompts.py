"""Prompt builders + output schemas for the two Claude calls.

Design rule that matters: Claude may only PICK SOC codes from the provided list and
WRITE prose. It must never invent jobs, wages, programs, or laws — all numbers/facts
come from data.py after the call.

Outputs are constrained with JSON schemas (structured outputs), so the views always
get the fields the Rebloom screens render.
"""

from __future__ import annotations

import json

PROFILE_SYSTEM = """\
You help women find work after incarceration. Be warm, strengths-based, and plain
(about an 8th-grade reading level). Treat work done while incarcerated as real work
experience. You may ONLY recommend jobs from the provided list, by their SOC code.
Never invent jobs, wages, training programs, or laws. Respect the person's stated
constraints (hours, transportation, childcare, pay floor, timeline). Some topics may
be skipped; never guess at skipped details.

Field guide:
- skills_profile.summary: 2 sentences, second person ("You bring ...").
- skills_profile.skills: 3-6 short skill chips ("Food preparation").
- skills_profile.experience: one line per role, like "Kitchen worker · Jail kitchen · 3 years".
- skills_profile.strengths: one sentence naming what she is good at.
- skills_profile.fits_now: one sentence on hours, place, travel, and family needs.
- matches: 2-5 jobs, best fit first. why_it_fits and first_step: one sentence each,
  tied to her own words and constraints.
"""

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "skills_profile": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "skills": {"type": "array", "items": {"type": "string"}},
                "experience": {"type": "array", "items": {"type": "string"}},
                "strengths": {"type": "string"},
                "fits_now": {"type": "string"},
            },
            "required": ["summary", "skills", "experience", "strengths", "fits_now"],
            "additionalProperties": False,
        },
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "soc": {"type": "string"},
                    "why_it_fits": {"type": "string"},
                    "first_step": {"type": "string"},
                },
                "required": ["soc", "why_it_fits", "first_step"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["skills_profile", "matches"],
    "additionalProperties": False,
}

LETTER_SYSTEM = """\
Write a short cover letter (~200 words) in the applicant's own voice, warm and
confident, plain language. Use only facts from her profile and her own words; never
invent employers, dates, or credentials. Sign it with her first name if known.

Disclosure: follow the `say_where` setting exactly.
- say_where = false: do NOT mention a conviction, jail, prison, or incarceration.
  Describe the work plainly (e.g. "three years of high-volume kitchen work").
- say_where = true: she chose to name where she gained the experience. Mention it
  once, briefly and matter-of-factly, then focus on skills.

Also write `record_script`: 2-3 short, honest, forward-looking sentences she could
say if her record comes up in an interview, each as its own string. Not legal advice.
"""

LETTER_SCHEMA = {
    "type": "object",
    "properties": {
        "letter": {"type": "string"},
        "record_script": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["letter", "record_script"],
    "additionalProperties": False,
}


def build_profile_prompt(answers: dict, jobs: list[dict]) -> str:
    """User message for Claude call #1 (profile + matches)."""
    job_list = [{"soc": j["soc"], "title": j["title"], "family": j["family"]} for j in jobs]
    return (
        "Her answers (null = she skipped that topic):\n"
        f"{json.dumps(answers, indent=2)}\n\n"
        "Jobs you may choose from (use the exact soc):\n"
        f"{json.dumps(job_list, indent=2)}"
    )


def build_letter_prompt(profile: dict, job: dict, answers: dict, name: str, say_where: bool) -> str:
    """User message for Claude call #2 (cover letter + record script)."""
    return (
        f"Job: {job['title']} (SOC {job['soc']})\n"
        f"Her first name: {name or 'unknown'}\n"
        f"say_where: {str(bool(say_where)).lower()}\n\n"
        f"Her skills profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Her own words:\n{json.dumps(answers, indent=2)}"
    )
