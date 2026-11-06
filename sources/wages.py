"""Live California wage lookup from the data.ca.gov EDD OEWS dataset.

No API key required. Returns the newest median hourly wage for a SOC code and area.
Any failure (offline, timeout, missing data) returns None so callers keep their seed
value — same graceful-fallback pattern as llm.py.

Dataset: https://data.ca.gov/dataset/oews  (CKAN datastore_search API)
See docs/data-sources.md for the wider data-source map.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

import streamlit as st

_RESOURCE_ID = "aef4c53a-7e17-418c-acc1-d189e39b6caa"
_BASE = "https://data.ca.gov/api/3/action/datastore_search"
_MEDIAN_FIELD = "unsafe_50th_percentile__median__wage"
_TIMEOUT_S = 6


def _soc_to_int(soc: str) -> int | None:
    """'35-2014' -> 352014 (the dataset stores SOC as an integer)."""
    digits = soc.replace("-", "").strip()
    return int(digits) if digits.isdigit() else None


@st.cache_data(ttl=86_400, show_spinner=False)
def median_hourly(soc: str, area: str = "California") -> dict | None:
    """Newest median hourly wage for `soc` in `area`.

    Returns {"median_hourly": float, "year": int, "area": str} or None on any failure.
    `area` defaults to statewide ("California"); pass a metro name (e.g.
    "San Francisco-Redwood City-South San Francisco MD") for local figures.
    """
    soc_int = _soc_to_int(soc)
    if soc_int is None:
        return None
    filters = {
        "Standard Occupational Classification": soc_int,
        "Wage Type": "Hourly wage",
        "Area Name": area,
    }
    params = urllib.parse.urlencode(
        {
            "resource_id": _RESOURCE_ID,
            "filters": json.dumps(filters),
            "sort": "Year desc",
            "limit": 1,
        }
    )
    try:
        with urllib.request.urlopen(f"{_BASE}?{params}", timeout=_TIMEOUT_S) as resp:
            data = json.load(resp)
        records = data.get("result", {}).get("records", [])
        if not records:
            return None
        rec = records[0]
        val = rec.get(_MEDIAN_FIELD)
        if val in (None, ""):
            return None
        return {
            "median_hourly": float(val),
            "year": int(rec["Year"]),
            "area": rec["Area Name"],
        }
    except Exception:
        # Offline / timeout / schema change -> caller falls back to seed value.
        return None
