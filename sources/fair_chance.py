"""Fair-chance employer job postings via keyless public ATS APIs.

No fair-chance job board exposes a public search API, so we curate a list of
fair-chance-relevant employers (data/fair_chance_employers.json) and read their live
openings straight from the public, no-auth endpoints their applicant tracking systems
(ATS) expose to power their own careers pages:

    greenhouse:     https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
    lever:          https://api.lever.co/v0/postings/{site}?mode=json
    smartrecruiters https://api.smartrecruiters.com/v1/companies/{id}/postings?limit=100

Results are normalized to the same shape as sources/jobs.py, filtered to the Bay Area and
matched against the SOC keyword synonyms. A "Fair-chance employer" badge is only ever
shown with its cited evidence (see the JSON). Graceful fallback: any error -> skip that
employer, never crash.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

import streamlit as st

from sources.jobs import keywords_for

_TIMEOUT_S = 8
_EMPLOYERS_FILE = Path(__file__).parent.parent / "data" / "fair_chance_employers.json"

# Markers that count a posting as Bay Area (case-insensitive substring match).
_BAY_AREA = [
    "san francisco", "oakland", "berkeley", "san jose", "bay area", "daly city",
    "millbrae", "south san francisco", "redwood city", "fremont", "hayward",
    "richmond", "san mateo", "alameda", "emeryville", ", ca", "california",
]


def _get_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NextChapter/1.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            return json.load(resp)
    except Exception:
        return None


def _is_bay_area(location: str) -> bool:
    loc = (location or "").lower()
    return any(m in loc for m in _BAY_AREA)


def _matches(title: str, synonyms: list[str]) -> bool:
    t = (title or "").lower()
    return any(s in t for s in synonyms)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_employers() -> list[dict]:
    try:
        with open(_EMPLOYERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _norm(emp: dict, title, company, location, url, posted, job_id) -> dict:
    return {
        "title": title or "",
        "company": company or emp["employer"],
        "location": location or "",
        "snippet": "",
        "salary_min": None,
        "salary_max": None,
        "salary_estimated": False,
        "contract_time": "",
        "posted": posted or "",
        "url": url or "",
        "id": str(job_id or ""),
        "source": emp["employer"],
        "fair_chance": True,
        "fair_chance_evidence": emp.get("fair_chance_evidence", ""),
        "fair_chance_source": emp.get("source_url", ""),
    }


def _fetch_greenhouse(emp: dict) -> list[dict]:
    d = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{emp['token']}/jobs")
    jobs = (d or {}).get("jobs", []) if isinstance(d, dict) else []
    return [
        _norm(emp, j.get("title"), None, (j.get("location") or {}).get("name"),
              j.get("absolute_url"), j.get("updated_at"), j.get("id"))
        for j in jobs
    ]


def _fetch_lever(emp: dict) -> list[dict]:
    d = _get_json(f"https://api.lever.co/v0/postings/{emp['token']}?mode=json")
    jobs = d if isinstance(d, list) else []
    return [
        _norm(emp, j.get("text"), None, (j.get("categories") or {}).get("location"),
              j.get("hostedUrl"), j.get("createdAt"), j.get("id"))
        for j in jobs
    ]


def _fetch_smartrecruiters(emp: dict) -> list[dict]:
    d = _get_json(
        f"https://api.smartrecruiters.com/v1/companies/{emp['token']}/postings?limit=100"
    )
    jobs = (d or {}).get("content", []) if isinstance(d, dict) else []
    out = []
    for j in jobs:
        loc = j.get("location") or {}
        loc_str = ", ".join(x for x in [loc.get("city"), loc.get("region")] if x)
        pid = j.get("id")
        url = f"https://jobs.smartrecruiters.com/{emp['token']}/{pid}"
        out.append(_norm(emp, j.get("name"), None, loc_str, url,
                         j.get("releasedDate"), pid))
    return out


_FETCHERS = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "smartrecruiters": _fetch_smartrecruiters,
}


@st.cache_data(ttl=3600, show_spinner=False)
def fair_chance_jobs(soc: str, limit: int = 6, title: str = "") -> list[dict]:
    """Live fair-chance-employer postings matching `soc`, filtered to the Bay Area."""
    _, synonyms = keywords_for(soc, title)
    results: list[dict] = []
    for emp in _load_employers():
        fetcher = _FETCHERS.get(emp.get("ats", ""))
        if not fetcher:
            continue
        for job in fetcher(emp):
            if _matches(job["title"], synonyms) and _is_bay_area(job["location"]):
                results.append(job)
    return results[:limit]
