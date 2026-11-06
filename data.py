"""Data loading + joining for Next Chapter.

Jobs, stories, and training programs all share one key: `family_code`
(the SOC major group = first two digits of a SOC code). A job match therefore
automatically pulls the stories and training for the same family. That shared key
is the glue that turns three features into one product.

Owners:
  - data/jobs.json      -> Stream 2 (real O*NET occupation/Job Zone + BLS CA wages)
  - data/stories.json   -> Stream 3 (synthetic peer stories)
  - data/training.json  -> Stream 3 (real local SF/Bay Area programs)

NOTE: the seed jobs.json wages are illustrative placeholders. Stream 2 should replace
them with verified BLS OEWS California medians and confirm each license flag.
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

_DATA_DIR = Path(__file__).parent / "data"


def _load(name: str) -> list[dict]:
    with open(_DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_jobs() -> list[dict]:
    return _load("jobs.json")


@st.cache_data
def load_stories() -> list[dict]:
    return _load("stories.json")


@st.cache_data
def load_training() -> list[dict]:
    return _load("training.json")


def job_by_soc(soc: str) -> dict | None:
    return next((j for j in load_jobs() if j["soc"] == soc), None)


def stories_for_family(family_code: str) -> list[dict]:
    return [s for s in load_stories() if s["family_code"] == family_code]


def training_for_family(family_code: str) -> list[dict]:
    return [t for t in load_training() if t["family_code"] == family_code]


def join_match(soc: str) -> dict | None:
    """Expand a matched SOC code into its full job record plus the stories and
    training programs that share its job family. Returns None for unknown SOC codes
    (so the UI can safely skip anything Claude invented)."""
    job = job_by_soc(soc)
    if job is None:
        return None
    fam = job["family_code"]
    return {
        "job": job,
        "stories": stories_for_family(fam),
        "training": training_for_family(fam),
    }


def family_options() -> list[tuple[str, str]]:
    """Unique (family_code, family) pairs present across jobs, for filters."""
    seen: dict[str, str] = {}
    for j in load_jobs():
        seen.setdefault(j["family_code"], j["family"])
    return sorted(seen.items())
