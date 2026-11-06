"""My Path: the guided conversation -> skills profile -> job matches -> cover letter.

This is the P0 core. The Claude calls run through llm.py, which returns canned output
when no API key is set, so the flow works out of the box.

TODO(ui): restyle to match the Figma wireframes.
"""

from __future__ import annotations

import streamlit as st

import data
import llm
from storage import get_storage

QUESTIONS = [
    ("past", "What work have you done before, including informal work (cleaning, childcare, selling, caregiving)?"),
    ("inside", "What jobs or programs did you do while incarcerated? (kitchen, laundry, maintenance, tutoring, GED, certifications)"),
    ("timeline", "When were you released, or when will you be? Any parole/probation check-ins?"),
    ("money", "What do you need to earn per hour or month? How soon do you need income?"),
    ("needs", "What do you need in a job? (hours, childcare, transportation, physical limits)"),
    ("pride", "What are you good at or proud of?"),
    ("concerns", "Anything you're worried an employer will ask?"),
]


def render(user: dict) -> None:
    store = get_storage()
    email = user["email"]

    st.header(f"Welcome, {user['name']}")
    st.write("Tell us your story in your own words. Nothing is saved.")

    with st.form("my_path_form"):
        answers: dict[str, str] = {}
        for key, label in QUESTIONS:
            answers[key] = st.text_area(label, key=f"q_{key}")
        answers["city"] = st.text_input("City / county", value="San Francisco, CA")
        submitted = st.form_submit_button("Show my path")

    if submitted:
        with st.spinner("Finding your strengths and matches..."):
            result = llm.generate_profile_and_matches(answers, data.load_jobs())
        store.save_profile(email, result.get("skills_profile", {}))
        # Keep only matches that join to a real job in our data.
        valid = [m for m in result.get("matches", []) if data.job_by_soc(m["soc"])]
        store.save_matches(email, valid)
        st.session_state["my_path_answers"] = answers

    _render_results(email, store)


def _render_results(email: str, store) -> None:
    profile = store.get_profile(email)
    matches = store.get_matches(email)
    if not profile and not matches:
        return

    if profile:
        st.subheader("Your strengths")
        st.success(profile.get("summary", ""))
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Skills**")
            for s in profile.get("skills", []):
                st.markdown(f"- {s}")
        with cols[1]:
            st.markdown("**Experience**")
            for e in profile.get("experience", []):
                st.markdown(f"- {e}")

    if matches:
        st.subheader("Jobs that fit you")
        for m in matches:
            _render_job_card(email, store, m, profile or {})


def _render_job_card(email: str, store, match: dict, profile: dict) -> None:
    joined = data.join_match(match["soc"])
    if not joined:
        return
    job = joined["job"]
    with st.container(border=True):
        st.markdown(f"### {job['title']} — ${job['ca_median_hourly']:.2f}/hr")
        if job.get("wage_source") == "live":
            wage_note = f"CA median wage · live data.ca.gov ({job.get('wage_year')})"
        else:
            wage_note = "CA median wage · seed estimate"
        st.caption(f"{job['family']} · Training: {job['training']} · {wage_note}")
        st.write(match.get("why_it_fits", ""))
        if match.get("first_step"):
            st.markdown(f"**First step:** {match['first_step']}")
        if job.get("licensed"):
            st.warning(f"⚠️ {job['license_note']}")

        if joined["stories"]:
            with st.expander("Women who've walked this path"):
                for s in joined["stories"]:
                    st.markdown(f"**{s['name']}** — {s['now']}")
                    st.write(s["story"])
                    st.caption(f"Advice: {s['advice']}")

        if joined["training"]:
            with st.expander("Local training for this path"):
                for t in joined["training"]:
                    st.markdown(f"**{t['name']}** · {t['provider']}")
                    st.caption(
                        f"{t['length']} · {t['cost']} · {t['location']} — [link]({t['url']})"
                    )
                    if t.get("licensing_warning"):
                        st.warning(f"⚠️ {t['licensing_warning']}")

        if st.button("Write my cover letter", key=f"letter_{job['soc']}"):
            answers = st.session_state.get("my_path_answers", {})
            with st.spinner("Writing your letter..."):
                letter = llm.generate_cover_letter(profile, job, answers)
            store.save_letter(email, job["soc"], letter)

        letter = store.get_letters(email).get(job["soc"])
        if letter:
            st.text_area(
                "Your cover letter", value=letter, height=320, key=f"letterbox_{job['soc']}"
            )
    st.caption("Not legal advice. Fair chance rules vary by employer and location.")
