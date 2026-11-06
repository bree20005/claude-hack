# Next Chapter

Employment help + community for women after incarceration — a Streamlit app.
Share your story (including work done while incarcerated) → get a strengths-based
skills profile, real job matches, peer stories, and local training, plus a cover letter.

This repo is a **runnable skeleton** meant for a team of 4 to extend. It runs with **no
API key and no database** — the Claude calls and data are stubbed — so everyone can clone,
run, and work on one area without blocking the others.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL it prints. Create an account → you land in **My Path** → fill the form →
"Show my path" shows a stub profile + job matches → "Write my cover letter" shows a stub
letter. Sign out and back in → you land on the three tracks with your history.

## How it fits together

One Streamlit process. The glue is the **job family** = SOC major group (first 2 digits of
a SOC code); jobs, stories, and training all share `family_code`, so one job match pulls the
matching stories + training.

```
app.py        auth gate + routing (landing -> new-user My Path -> 3 tracks)
auth.py       sign up / sign in (email+password, hashed) + Google stub
storage.py    Storage interface + InSessionStorage (keyed by email, nothing on disk)
llm.py        call_claude(): real Anthropic call, or canned output when no key
prompts.py    the two system prompts + prompt builders
data.py       load + join jobs/stories/training by family_code
views/        landing · my_path · community · train_up
data/         jobs.json · stories.json · training.json  (seed data)
```

## Team workstreams (clean file boundaries, no merge conflicts)

| Stream | Owns | To do |
|---|---|---|
| 1 — App & integration | `app.py`, `llm.py` | wire real Anthropic call; deploy |
| 2 — Jobs data | `data/jobs.json`, `data.py` | ~20 SOC jobs: real O*NET training/Job Zone + **BLS CA median wages** + verified license flags (seed wages are placeholders) |
| 3 — Community & training | `data/stories.json`, `data/training.json` | 6–9 synthetic stories + 6–10 real SF/Bay Area programs |
| 4 — Prompts & demo | `prompts.py`, README, video | refine both prompts (test in Claude chat first); Maria's answers; demo |

Search the code for `TODO(` to find the plug-in points.

## Wiring the real Claude call

1. Create `.streamlit/secrets.toml` (git-ignored):
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
2. That's it — `llm.py` auto-detects the key and calls Claude; without it, it returns
   canned demo output. Uses a current model (`claude-opus-4-8`) with a try/except fallback
   so the demo never hard-fails.

## Storage / persistence

`InSessionStorage` keeps everything in `st.session_state` — **nothing is persisted to
disk**, which keeps data for this sensitive population private by default. To add real
persistence, implement `Storage` with a new class (e.g. Supabase) and swap the one line in
`get_storage()`. Note: on Streamlit Cloud the filesystem is ephemeral, so use a hosted DB.

## Design (Figma)

UI is a neutral placeholder. To match the wireframes, either drop PNG exports of each frame
into the repo, or use the Figma MCP server: `claude mcp add --scope user --transport http
figma https://mcp.figma.com/mcp`, then `/mcp` → figma → Authenticate.

## Notes

- Not legal advice. CA Fair Chance Act framing is referenced but verify per employer/location.
- Community stories are **synthetic** and labeled as such. A real version needs consent,
  moderation, and anonymization.
