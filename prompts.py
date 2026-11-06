"""Prompt builders for the two Claude calls.

These are placeholders with the right SHAPE so the app flows end to end. Stream 4
should refine the wording (tone, reading level, constraints) and test in a Claude
chat before relying on them.

Design rule that matters: Claude may only PICK SOC codes from the provided list and
WRITE prose. It must never invent jobs, wages, programs, or laws — all numbers/facts
come from data.py after the call.
"""

from __future__ import annotations

import json

PROFILE_SYSTEM = """\
You help women find work after incarceration. Be warm, strengths-based, and plain
(about an 8th-grade reading level). Treat work done while incarcerated as real work
experience. You may ONLY recommend jobs from the provided list, by their SOC code.
Never invent jobs, wages, training programs, or laws. Respect the person's stated
constraints (hours, transportation, pay floor, timeline).

Return ONLY valid JSON of the form:
{"skills_profile": {"summary": str, "skills": [str], "experience": [str]},
 "matches": [{"soc": str, "why_it_fits": str, "first_step": str}]}
"""

LETTER_SYSTEM = """\
Write a short cover letter (~200 words) in the applicant's own voice, warm and
confident. Do NOT disclose any conviction or incarceration; frame institutional work
plainly (e.g. "high-volume kitchen experience"). After the letter, add a brief, honest,
forward-looking script titled "If your record comes up". Plain language. Not legal advice.
"""


def build_profile_prompt(answers: dict, jobs: list[dict]) -> str:
    """User message for Claude call #1 (profile + matches)."""
    job_list = [
        {"soc": j["soc"], "title": j["title"], "family": j["family"]}
        for j in jobs
    ]
    return (
        "Her answers:\n"
        f"{json.dumps(answers, indent=2)}\n\n"
        "Jobs you may choose from (use the exact soc):\n"
        f"{json.dumps(job_list, indent=2)}"
    )


def build_letter_prompt(profile: dict, job: dict, answers: dict) -> str:
    """User message for Claude call #2 (cover letter)."""
    return (
        f"Job: {job['title']} (SOC {job['soc']})\n\n"
        f"Her skills profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Her own words:\n{json.dumps(answers, indent=2)}"
    )
