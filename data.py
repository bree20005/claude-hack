"""Data loading + joining for Rebloom / Next Chapter.

The glue is TAGS (data/tags.json, PRD 0): Claude assigns each woman industry and
experience tags from that fixed list. Jobs, programs, community members and
published stories all carry industry tags, so one set of tags drives matches,
"women like you", and training.

Files:
  - data/tags.json      fixed taxonomy (only these ids are ever shown)
  - data/jobs.json      curated entry-level jobs (wages: approximate CA medians)
  - data/programs.json  real Bay Area training programs + help centers
  - data/members.json   synthetic community members (stories + mentor profiles)
  - data/paths.json     synthetic example career paths (Paths tab)

Published stories (PRD 5) are stored in SQLite (db.py) so every user sees them.
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

_DATA_DIR = Path(__file__).parent / "data"


def _load(name: str):
    path = _DATA_DIR / name
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- tags -------------------------------------------------------------------
@st.cache_data
def load_tags() -> dict:
    return _load("tags.json")


def industry_tags() -> list[dict]:
    return load_tags()["industry"]


def experience_tags() -> list[dict]:
    return load_tags()["experience"]


def tag_label(tag_id: str) -> str:
    for t in industry_tags() + experience_tags():
        if t["id"] == tag_id:
            return t["label"]
    return tag_id


def valid_industry(ids) -> list[str]:
    allowed = {t["id"] for t in industry_tags()}
    out: list[str] = []
    for i in ids or []:
        if i in allowed and i not in out:
            out.append(i)
    return out


def valid_experience(ids) -> list[str]:
    allowed = {t["id"] for t in experience_tags()}
    out: list[str] = []
    for i in ids or []:
        if i in allowed and i not in out:
            out.append(i)
    return out


def tag_overlap(a: dict, b: dict) -> int:
    """PRD 0: industry matches count 2, experience matches count 1."""
    ind = len(set(a.get("industry", [])) & set(b.get("industry_tags", b.get("industry", []))))
    exp = len(set(a.get("experience", [])) & set(b.get("experience_tags", b.get("experience", []))))
    return ind * 2 + exp


# --- jobs ---------------------------------------------------------------------
@st.cache_data
def load_jobs() -> list[dict]:
    return _load("jobs.json")


def job_by_soc(soc: str) -> dict | None:
    return next((j for j in load_jobs() if j["soc"] == soc), None)


def job_industry_tags(job: dict) -> list[str]:
    if job.get("industry_tags"):
        return job["industry_tags"]
    fam = job.get("family_code", "")
    return [t["id"] for t in industry_tags() if fam in t.get("soc_families", [])][:1]


def jobs_for_tags(tags: list[str]) -> list[dict]:
    return [j for j in load_jobs() if set(job_industry_tags(j)) & set(tags)]


def jobs_for_family(family_code: str) -> list[dict]:
    return [j for j in load_jobs() if j.get("family_code") == family_code]


def family_name(family_code: str) -> str:
    return next((j["family"] for j in load_jobs() if j.get("family_code") == family_code), family_code)


# --- programs (PRD 7) ---------------------------------------------------------
@st.cache_data
def load_programs() -> list[dict]:
    progs = _load("programs.json")
    if progs:
        return progs
    # Fallback while programs.json is being curated: adapt training.json.
    out = []
    for t in _load("training.json"):
        tag = next((x["id"] for x in industry_tags() if t.get("family_code") in x["soc_families"]), None)
        out.append({
            "id": t["id"], "type": "training", "name": t["name"], "provider": t["provider"],
            "industry_tags": [tag] if tag else [], "description": t.get("notes", ""),
            "cost": t["cost"], "is_free": t["cost"].lower() in ("free", "no cost"),
            "length": t["length"], "length_weeks": None, "location": t["location"], "url": t["url"],
            "record_friendly": "record" in t.get("notes", "").lower(), "last_checked": "",
        })
    return out


def program_sort_key(p: dict, tags: list[str]):
    shared = len(set(p.get("industry_tags", [])) & set(tags))
    weeks = p.get("length_weeks")
    return (-shared, not p.get("is_free"), weeks if weeks is not None else 999, p["name"])


def programs_for_tags(tags: list[str]) -> list[dict]:
    return sorted([p for p in load_programs() if set(p.get("industry_tags", [])) & set(tags)],
                  key=lambda p: program_sort_key(p, tags))


# --- community members + stories (PRD 6) ---------------------------------------
@st.cache_data
def load_members() -> list[dict]:
    return _load("members.json")


def member_by_id(mid: str) -> dict | None:
    return next((m for m in load_members() if m["id"] == mid), None)


@st.cache_data
def load_paths() -> list[dict]:
    return _load("paths.json")


def published_stories() -> list[dict]:
    import db
    return db.list_stories()


def my_story(author_id: str) -> dict | None:
    import db
    return db.story_by_author(author_id)


def publish_story(author_id: str, story: dict) -> dict:
    """Upsert: one story per account. Only approved public fields are stored."""
    import db
    clean = dict(story, industry_tags=valid_industry(story.get("industry_tags")),
                 experience_tags=valid_experience(story.get("experience_tags")))
    return db.upsert_story(author_id, clean)


def delete_story(author_id: str) -> None:
    import db
    db.delete_story(author_id)


def all_stories(viewer_id: str | None = None) -> list[dict]:
    """Public story list: real (published) first, newest first, then synthetic members.
    `author_id` is never included; `is_mine` is computed here."""
    out = []
    for s in published_stories():
        pub = {k: v for k, v in s.items() if k != "author_id"}
        pub["is_mine"] = s["author_id"] == viewer_id
        out.append(pub)
    for m in load_members():
        out.append({
            "id": m["id"], "display_name": m["display_name"], "current_job": m["current_job"],
            "journey": m["journey"], "advice": m["advice"], "industry_tags": valid_industry(m["industry_tags"]),
            "experience_tags": valid_experience(m["experience_tags"]), "synthetic": True, "is_mine": False,
            "member_id": m["id"],
        })
    return out


def stories_for_tags(tags: list[str]) -> list[dict]:
    return [s for s in all_stories() if set(s["industry_tags"]) & set(tags)]
