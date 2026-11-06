"""Live job postings from the Adzuna API.

Adzuna is the recommended "integrate today" source (free self-serve key, title+location
search, display allowed WITH an "Adzuna" attribution label). It has no SOC filter, so we
map each SOC to search phrases below.

Graceful-fallback pattern (same as sources/wages.py): if no API keys are set, or on any
error, `search_jobs` returns [] and the UI shows nothing / a hint — never crashes.

Keys (never commit): in .streamlit/secrets.toml
    ADZUNA_APP_ID = "..."
    ADZUNA_APP_KEY = "..."

ATTRIBUTION: Adzuna's terms require showing an "Adzuna" label/link wherever listings
appear. The My Path UI does this when Adzuna results are present.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

import streamlit as st

_BASE = "https://api.adzuna.com/v1/api/jobs/us/search/1"
_TIMEOUT_S = 8

# SOC -> (primary Adzuna search phrase, [title-match synonyms for ATS filtering]).
# Covers the SOC codes in data/jobs.json; extend as jobs.json grows.
SOC_KEYWORDS: dict[str, tuple[str, list[str]]] = {
    "35-2014": ("line cook", ["cook", "kitchen", "culinary", "food service", "prep"]),
    "37-2011": ("janitor", ["janitor", "custodian", "cleaner", "porter", "housekeep"]),
    "31-1131": ("nursing assistant", ["nursing assistant", "cna", "caregiver", "home health", "patient care"]),
}


def keywords_for(soc: str, title: str = "") -> tuple[str, list[str]]:
    """Return (adzuna_phrase, synonyms) for a SOC, falling back to the job title."""
    if soc in SOC_KEYWORDS:
        return SOC_KEYWORDS[soc]
    phrase = (title or "").split(",")[0].strip().lower() or "entry level"
    return phrase, [w for w in phrase.split() if len(w) > 3] or [phrase]


def _keys() -> tuple[str, str] | None:
    try:
        app_id = st.secrets.get("ADZUNA_APP_ID")
        app_key = st.secrets.get("ADZUNA_APP_KEY")
    except Exception:
        return None
    return (app_id, app_key) if app_id and app_key else None


@st.cache_data(ttl=3600, show_spinner=False)
def search_jobs(soc: str, where: str = "San Francisco", limit: int = 5,
                title: str = "") -> list[dict]:
    """Newest Adzuna postings for a SOC near `where`. Returns [] with no keys or on error."""
    keys = _keys()
    if keys is None:
        return []
    app_id, app_key = keys
    phrase, _ = keywords_for(soc, title)
    params = urllib.parse.urlencode(
        {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": limit,
            "what": phrase,
            "where": where,
            "distance": 25,
            "sort_by": "date",
            "content-type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(f"{_BASE}?{params}", timeout=_TIMEOUT_S) as resp:
            data = json.load(resp)
    except Exception:
        return []

    out: list[dict] = []
    for r in data.get("results", [])[:limit]:
        out.append(
            {
                "title": r.get("title", "").replace("<strong>", "").replace("</strong>", ""),
                "company": (r.get("company") or {}).get("display_name", ""),
                "location": (r.get("location") or {}).get("display_name", ""),
                "snippet": r.get("description", ""),
                "salary_min": r.get("salary_min"),
                "salary_max": r.get("salary_max"),
                "salary_estimated": str(r.get("salary_is_predicted", "")) == "1",
                "contract_time": r.get("contract_time", ""),
                "posted": r.get("created", ""),
                "url": r.get("redirect_url", ""),
                "id": str(r.get("id", "")),
                "source": "Adzuna",
                "fair_chance": False,
            }
        )
    return out
