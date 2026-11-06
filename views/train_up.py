"""Train Up track: local upskilling programs, filtered by job family.

Record-aware and women-centered, per the reentry research: each program carries flags
for whether it's women-specific, record-friendly, needs a probation referral, drug-tests
(incl. marijuana), needs a driver's license, offers childcare, pays/stipends, and any
licensing warning (e.g. CNA/HHA go through CDPH, which reviews all convictions).

Honesty rules kept from the research:
  - Outcomes in notes are self-reported / program-reported, not causal effects.
  - Fields marked "unverified" / "unknown" are shown as such, never guessed.

TODO(stream-3): verify the "unknown"/"unverified" fields against current sources and
set `last_verified` dates.
"""

from __future__ import annotations

import streamlit as st

import data


def _badges(t: dict) -> str:
    """Build a compact row of badge-like tags for a program."""
    tags: list[str] = []
    if t.get("women_specific"):
        tags.append("♀ Women-specific")
    rf = t.get("record_friendly")
    if rf == "yes":
        tags.append("✅ Record-friendly")
    elif rf == "no":
        tags.append("⛔ Not record-friendly")
    else:
        tags.append("❔ Record policy unknown")
    if t.get("requires_referral") is True:
        tags.append("📋 Needs probation referral")
    elif t.get("requires_referral") is False:
        tags.append("🚪 No referral needed")
    pay = t.get("paid_or_stipend")
    if pay == "paid":
        tags.append("💵 Paid")
    elif pay == "stipend":
        tags.append("💵 Stipend")
    return "  ·  ".join(tags)


def _requirements(t: dict) -> list[str]:
    """Human-readable lines for the practical constraints that decide if she can go."""
    lines: list[str] = []
    if t.get("drug_test") is True:
        lines.append("Drug test required (may include marijuana, which is legal in CA)")
    if t.get("drivers_license_required") is True:
        lines.append("Driver's license required")
    if t.get("childcare_offered") is True:
        lines.append("Childcare offered")
    return lines


def render() -> None:
    st.header("Train Up")
    st.caption(
        "Local programs, grouped by job family. Program outcomes shown are "
        "self-reported. Fields marked *unverified/unknown* still need confirming."
    )

    programs = data.load_training()

    # --- filters ---------------------------------------------------------
    families = data.training_family_options()
    labels = ["All families"] + [name for _, name in families]
    codes = [None] + [code for code, _ in families]
    c1, c2 = st.columns([2, 3])
    with c1:
        choice = st.selectbox(
            "Job family", options=range(len(labels)), format_func=lambda i: labels[i]
        )
    with c2:
        st.write("")  # vertical spacing
        only_women = st.checkbox("Women-specific only")
        no_referral = st.checkbox("Open without a probation referral")
        record_ok = st.checkbox("Record-friendly only")

    fam_code = codes[choice]
    if fam_code:
        programs = [t for t in programs if t["family_code"] == fam_code]
    if only_women:
        programs = [t for t in programs if t.get("women_specific")]
    if no_referral:
        programs = [t for t in programs if t.get("requires_referral") is False]
    if record_ok:
        programs = [t for t in programs if t.get("record_friendly") == "yes"]

    st.caption(f"{len(programs)} program(s)")

    if not programs:
        st.info("No programs match these filters yet.")
        return

    # Tip that maps straight to the research: jail-leavers often have no PO.
    if no_referral:
        st.success(
            "Good starting points for a woman leaving jail without probation: "
            "**CASC Specialized Job Center** (open to any justice-involved SF adult)."
        )

    for t in programs:
        _render_program(t)


def _render_program(t: dict) -> None:
    with st.container(border=True):
        st.markdown(f"### {t['name']}")
        st.caption(f"{t['provider']} · {t['family']} · {t['location']}")

        badges = _badges(t)
        if badges:
            st.markdown(badges)

        st.write(f"**Length:** {t['length']}  |  **Cost:** {t['cost']}")

        if t.get("licensing_warning"):
            st.warning(f"⚠️ Licensing: {t['licensing_warning']}")
        elif t.get("licensing_body"):
            st.caption(f"Licensing body: {t['licensing_body']}")

        reqs = _requirements(t)
        if reqs:
            st.markdown("**Good to know:** " + "; ".join(reqs))

        if t.get("notes"):
            st.write(t["notes"])

        meta = []
        if t.get("last_verified"):
            meta.append(f"Last verified: {t['last_verified']}")
        st.caption(f"[Program link]({t['url']})" + ("  ·  " + " · ".join(meta) if meta else ""))
