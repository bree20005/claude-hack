"""Claude wrapper for Rebloom (Next Chapter).

Model: claude-opus-5-5 for every call (the most capable default; context-aware intake,
richer profiles). Every JSON call uses structured outputs, then the caller validates
ids in code. If no API key is configured, or a call fails, functions return demo
output so the app never crashes (PRD 0 principle 7).
"""

from __future__ import annotations

import json

import anthropic
import streamlit as st

import prompts as P

MODEL = "claude-opus-5-5"
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _client() -> anthropic.Anthropic | None:
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # noqa: BLE001 - no secrets file
        api_key = None
    return anthropic.Anthropic(api_key=api_key) if api_key else None


def has_key() -> bool:
    return _client() is not None


def _create(system: str, messages: list[dict], effort: str, schema: dict | None, max_tokens: int = 16000):
    client = _client()
    if client is None:
        return None
    output_config: dict = {"effort": effort}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    try:
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=max_tokens, betas=[_FALLBACK_BETA], fallbacks="default",
            output_config=output_config, system=system, messages=messages,
        )
    except anthropic.AuthenticationError:
        st.session_state["llm_error"] = "The Claude API key was rejected (it may have expired). Showing demo output."
        return None
    except anthropic.RateLimitError:
        st.session_state["llm_error"] = "Claude is busy right now. Showing demo output; try again in a minute."
        return None
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        st.session_state["llm_error"] = f"Claude call failed ({type(e).__name__}). Showing demo output."
        return None
    if resp.stop_reason in ("refusal", "max_tokens"):
        return None
    return next((b.text for b in resp.content if b.type == "text"), "")


def call_json(system: str, user_or_messages, schema: dict, fallback, effort: str = "medium"):
    messages = user_or_messages if isinstance(user_or_messages, list) else [{"role": "user", "content": user_or_messages}]
    text = _create(system, messages, effort, schema)
    if text is None:
        return fallback
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return fallback


def call_text(system: str, messages: list[dict], fallback: str, effort: str = "low") -> str:
    text = _create(system, messages, effort, None, max_tokens=4000)
    return text.strip() if text else fallback


# --- PRD 2: intake chat ------------------------------------------------------------
_DEMO_SCRIPT = {
    "seeker": [
        ("Three years in a kitchen is real experience. About how many people did you cook for each day?",
         ["About 200 people", "Over 500", "Not sure", "Skip this"], ["past_work", "inside_work"]),
        ("Feeding that many people takes speed and planning. Did you ever train new workers or keep track of supplies?",
         ["Yes, I trained people", "I did inventory", "Both", "Skip this"], ["past_work", "inside_work"]),
        ("Training people means they trusted you. When were you released, and do you have check-ins to plan around?",
         ["Last month", "Weekly check-ins", "Skip this"], ["past_work", "inside_work"]),
        ("Thanks. How much do you need to earn, and how soon?",
         ["About $20 an hour", "As soon as possible", "Skip this"], ["past_work", "inside_work", "timeline"]),
        ("That's clear. What does a job need to fit around, like hours, kids, or getting there?",
         ["Daytime hours", "I take the bus", "Two kids", "Skip this"], ["past_work", "inside_work", "timeline", "money"]),
        ("That helps a lot. What are you most proud of, at work or at home?",
         ["Keeping my family together", "Being reliable", "Skip this"], ["past_work", "inside_work", "timeline", "money", "needs"]),
        ("That takes strength and organization. Is there anything else you'd like me to know?",
         ["No, that's it", "Yes, one more thing"], ["past_work", "inside_work", "timeline", "money", "needs", "strengths"]),
    ],
}


def intake_turn(persona: str, first_name: str, messages: list[dict], covered: list[str]) -> dict:
    bot_turns = sum(1 for m in messages if m["role"] == "assistant")
    script = _DEMO_SCRIPT.get("seeker")
    idx = min(max(bot_turns - 1, 0), len(script) - 1)
    reply, qr, cov = script[idx]
    done = bot_turns > len(script)
    fallback = {"reply": "Thank you for sharing all of that." if done else reply, "quick_replies": [] if done else qr,
                "topics_covered": P.topic_ids(persona) if done else cov, "ready_to_finish": done, "crisis": False}
    # API requires the conversation to start with a user turn: fold the scripted opener into context.
    api_msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
    if api_msgs and api_msgs[0]["role"] == "assistant":
        api_msgs = [{"role": "user", "content": "(She opened the chat.)"}] + api_msgs
    out = call_json(P.intake_system(persona, first_name, covered, bot_turns), api_msgs, P.INTAKE_SCHEMA,
                    fallback, effort="medium")
    # PRD 2 validation
    valid = set(P.topic_ids(persona))
    out["topics_covered"] = sorted((set(covered) | {t for t in out.get("topics_covered", []) if t in valid}),
                                   key=P.topic_ids(persona).index)
    qrs = [q[:40] for q in out.get("quick_replies", []) if q.strip()][:6]
    if "Skip this" not in qrs and not out.get("ready_to_finish"):
        qrs = qrs[:5] + ["Skip this"]
    out["quick_replies"] = qrs
    out["reply"] = out.get("reply", "")[:700]
    if bot_turns >= 16:
        out["ready_to_finish"] = True
    return out


def extract_answers(persona: str, messages: list[dict], fallback: dict) -> dict:
    convo = "\n".join(f"{'Rebloom' if m['role'] == 'assistant' else 'Her'}: {m['content']}" for m in messages)
    out = call_json(P.extract_system(persona), convo, P.EXTRACT_SCHEMA, None, effort="medium")
    if not out:
        return fallback
    valid = set(P.topic_ids(persona))
    return {a["topic"]: a["answer"][:1000] for a in out["answers"] if a["topic"] in valid and a["answer"].strip()}


# --- PRD 3 ------------------------------------------------------------------------
STUB_TAGS = {
    "summary": "You have 3 years of high-volume kitchen experience, including training new workers and "
               "tracking inventory. You've also kept a household running for two kids, which takes real organization.",
    "skills": ["Cooking for 200+ people", "Training new workers", "Keeping inventory", "Cleaning to a standard",
               "Showing up every day"],
    "experience_lines": ["Kitchen worker · Jail kitchen · 3 years", "Cleaning crew member · 1 year"],
    "industry": [{"id": "food-service", "reason": "3 years in the jail kitchen, cooking for hundreds daily"},
                 {"id": "cleaning-facilities", "reason": "1 year on a cleaning crew"}],
    "experience": [{"id": "worked-inside", "reason": "Kitchen and cleaning jobs while incarcerated"},
                   {"id": "mentored-others", "reason": "Trained new kitchen workers"},
                   {"id": "caregiver-parent", "reason": "Raising two kids"},
                   {"id": "no-car", "reason": "Said she relies on the bus"},
                   {"id": "needs-daytime-hours", "reason": "Needs daytime hours for her kids"}],
}


def tag_profile(answers: dict, tags: dict) -> dict:
    return call_json(P.TAGS_SYSTEM, P.tags_prompt(answers, tags), P.TAGS_SCHEMA, STUB_TAGS, effort="high")


# --- PRD 4 ------------------------------------------------------------------------
def match_jobs(answers: dict, tags: dict, summary: str, candidates: list[dict]) -> dict:
    fallback = {"pay_floor_hourly": 20, "matches": [
        {"soc": j["soc"], "why_it_fits": "Your experience lines up with this kind of work.",
         "first_step": "Search openings near you and mention your hands-on experience."} for j in candidates[:4]]}
    return call_json(P.MATCH_SYSTEM, P.match_prompt(answers, tags, summary, candidates), P.MATCH_SCHEMA,
                     fallback, effort="high")


# --- PRD 5 ------------------------------------------------------------------------
def anonymize(answers: dict) -> dict | None:
    fallback = {
        "journey": "I worked in the kitchen at the county jail for three years. I started on dishes and ended up "
                   "running the breakfast line. When I got out, I didn't think any of that counted. I applied to "
                   "so many places and heard nothing for four months. A county culinary training program changed "
                   "that. They helped me put my kitchen time on paper and practice how to talk about it. My first "
                   "job was prep cook at a restaurant downtown. Now I've been a line cook for two years, and I help "
                   "train the new people. Some days are still hard, but I'm proud of the work I do.",
        "advice": "Don't let the no's stop you. Write down everything you did inside. It counts.",
        "current_job": "Line cook at a restaurant",
        "removed": [{"type": "facility", "original": "Santa Rita Jail"}, {"type": "employer", "original": "Joe's Diner"}],
    }
    out = call_json(P.ANON_SYSTEM, json.dumps(answers, indent=2), P.ANON_SCHEMA, fallback, effort="medium")
    # Backstop: no removed identifier may remain in the public text.
    for item in out.get("removed", []):
        orig = item.get("original", "").strip()
        if len(orig) < 3:
            continue
        for field in ("journey", "advice", "current_job"):
            if orig.lower() in out.get(field, "").lower():
                import re
                out[field] = re.sub(re.escape(orig), "[removed]", out[field], flags=re.I)
    return out


# --- PRD 7 ------------------------------------------------------------------------
def program_why(summary: str, tags: dict, programs: list[dict]) -> dict[str, str]:
    recs = [{k: p.get(k) for k in ("id", "name", "provider", "description", "industry_tags", "type")} for p in programs]
    out = call_json(P.WHY_SYSTEM, f"Her summary: {summary}\nHer tags: {json.dumps(tags)}\nPrograms:\n{json.dumps(recs)}",
                    P.WHY_SCHEMA, {"why": []}, effort="low")
    ids = {p["id"] for p in programs}
    return {w["id"]: " ".join(w["text"].split()[:28]) for w in out.get("why", []) if w["id"] in ids}


# --- Community member chat ------------------------------------------------------------
def member_reply(member: dict, history: list[dict], seeker_name: str, seeker_summary: str) -> str:
    fallback = (f"That's a real question. When I was starting out, what helped most was writing down every job I'd "
                f"done, even the ones inside. Want to tell me what you're working toward right now?")
    msgs = [{"role": m["role"], "content": m["content"]} for m in history]
    if msgs and msgs[0]["role"] == "assistant":
        msgs = [{"role": "user", "content": "(She opened a conversation with you.)"}] + msgs
    return call_text(P.member_system(member, seeker_name, seeker_summary), msgs, fallback, effort="low")


# --- PRD 8: cover letter -------------------------------------------------------------
LETTER_SYSTEM = """Write a short cover letter (~200 words) in the applicant's own voice, warm and
confident, plain language. Use only facts from her profile and her own words; never invent employers,
dates, or credentials. Sign with her first name if known.
say_where = false: do NOT mention a conviction, jail, prison, or incarceration; describe the work plainly.
say_where = true: she chose to name where she gained the experience; mention it once, briefly, then focus on skills.
record_script: 2-3 short, honest, forward-looking sentences she could say if her record comes up. Not legal advice."""

LETTER_SCHEMA = {
    "type": "object",
    "properties": {"letter": {"type": "string"}, "record_script": {"type": "array", "items": {"type": "string"}}},
    "required": ["letter", "record_script"], "additionalProperties": False,
}

_STUB_LETTER = {
    "letter": ("Dear Hiring Team,\n\nI'm applying for the Cook position. I bring three years of high-volume kitchen "
               "work and one year on a cleaning crew. I've cooked for hundreds of people a day, trained new workers, "
               "and kept track of supplies.\n\nI'm reliable, I learn fast, and I take pride in doing the job right. "
               "I'm looking for daytime hours at a location I can reach by transit.\n\nThank you for considering my "
               "application.\n\nSincerely,\nMaria"),
    "record_script": ["I have a record, and I've worked hard since then.",
                      "During that time I worked in a kitchen for three years and trained new workers.",
                      "I'm focused on my next chapter and would like to talk about how that experience fits this job."],
}


def generate_cover_letter(profile: dict, job: dict, answers: dict, name: str = "", say_where: bool = False) -> dict:
    user = (f"Job: {job['title']} (SOC {job['soc']})\nHer first name: {name or 'unknown'}\n"
            f"say_where: {str(bool(say_where)).lower()}\n\nHer profile:\n{json.dumps(profile, indent=2)}\n\n"
            f"Her own words:\n{json.dumps(answers, indent=2)}")
    return call_json(LETTER_SYSTEM, user, LETTER_SCHEMA, _STUB_LETTER, effort="medium")
