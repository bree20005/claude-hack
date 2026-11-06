# Next Chapter: Build Plan
*Employment help + community for women after jail · Code with Claude: Women in AI Hackathon · Due 12:45 PM · Team of 4*

> Working name: **Next Chapter**. Swap it freely.

---

## 1. The idea (from our sketch)

A woman who's been to jail opens the app and gets three connected things:

| Pillar | What it does |
|---|---|
| **① My Path** | She shares her story through tailored questions (past work, prison employment, timeline, money needs). Claude turns it into a skills profile and **matches her to real jobs**, then writes a **cover letter**. |
| **② Community** | Other women's stories, **sorted into job families**. On her matched jobs she sees "women who've walked this path." |
| **③ Train Up** | **Local upskilling** programs (and resources) for the job families she matched. |

**The glue is the job family.** Jobs, stories and training programs are all tagged with the same job family. A job match then automatically pulls the stories and training for that family. That one shared key is what turns three features into one product.

**Job families = official SOC major groups.** SOC (Standard Occupational Classification) is the U.S. government's official system for categorizing every job. Each job gets a code like `35-2014` (Restaurant Cook), and the **first two digits are its "major group,"** a broad family like `35` = Food Preparation & Serving. O\*NET (job descriptions and training) and BLS (wages) both use these same codes, so we can join their data directly, and we can tag stories and training programs with the same 2-digit family. Real, consistent, and free:

| Code | Job family |
|---|---|
| 31 | Healthcare Support (CNA, medical assistant, phlebotomist) |
| 35 | Food Preparation & Serving |
| 37 | Building & Grounds (custodial, landscaping) |
| 39 | Personal Care & Service (childcare, cosmetology, home care) |
| 41 | Sales & Retail |
| 43 | Office & Administrative Support |
| 47 | Construction & Trades |
| 53 | Transportation & Warehouse |
| 21 | Community & Social Service (peer support, community health worker) |

---

## 2. The demo story (what judges will remember)

**Maria**, 34, released from county jail. She worked 3 years in the jail kitchen and 1 year on a cleaning crew. She has two kids, needs daytime hours, and has no car. She writes her story messily, run-on, in her own words.

1. She answers the questions → **"You have 3 years of high-volume food service, inventory tracking, and trained new workers."**
2. **Top matches** with real CA wages, plus a flag on any job that needs a license.
3. She clicks **Cook**. The app shows **2 stories from women in Food Service** and **a local culinary training program**.
4. **Cover letter generated**, in her voice. **Her raw story and the polished letter are shown side by side.**

Closing line: *"Her time inside isn't a gap in her résumé. It's experience."*

---

## 3. Scope, prioritized (~70 min of build time, 11:00–12:10)

| Priority | Feature | If behind schedule |
|---|---|---|
| **P0** | ① Questions → skills profile → job matches → cover letter | Never cut |
| **P1** | ② Community page, **read-only**, seeded with 6–9 synthetic stories, + "stories in this family" on job cards | Cut the separate page, keep stories on job cards |
| **P1** | ③ Training programs shown on job cards by family | Keep to 6–10 programs |
| **P2** | "Share your story" form → Claude tags its job family → appears on the page (this session only) | Cut |
| **P3** | Adaptive follow-up question from Claude, voice input, .docx export | Cut |

**Community page honesty rule:** label it *"Example stories (synthetic, for demo)."* A real version needs consent, moderation and anonymization. Say this in the pitch, because it shows judgment.

---

## 4. User flow (screens)

Streamlit app with 3 tabs: **My Path · Community · Train Up**

**Tab 1 – My Path**
1. Intro line: *"Tell us your story in your own words. Nothing is saved."*
2. Guided questions (text areas):
   - **Past:** What work have you done before, including informal work (cleaning, childcare, selling, caregiving)?
   - **Inside:** What jobs or programs did you do while incarcerated? (kitchen, laundry, maintenance, tutoring, fire crew, GED, certifications)
   - **Timeline:** When were you released or when will you be? Do you have parole/probation check-ins?
   - **Money:** What do you need to earn per hour/month? How soon do you need income?
   - **Needs:** Hours, childcare, transportation, physical limits?
   - **Interests/pride:** What are you good at or proud of?
   - **Concerns:** Anything you're worried an employer will ask?
   - City/county (default: San Francisco / Bay Area)
3. **"Show my path"** button → Claude call #1 →
   - **Skills profile card** (plain language, strengths-forward)
   - **3–5 job match cards**, each with: title, family, why it fits *her*, CA median wage, training time, ⚠️ license flag, 1–2 community stories, local training program
4. On each card: **"Write my cover letter"** → Claude call #2 → letter + "How to talk about your record" mini-script.

**Tab 2 – Community**
- Filter by job family → story cards (name/initials, family, 3–5 sentence story, current job, one piece of advice).
- (P2) "Share your story" form.

**Tab 3 – Train Up**
- Filter by family → program cards (name, provider, length, cost, location, what you earn after, link).

---

## 5. Data (real wherever possible)

| File | Source | How | Owner |
|---|---|---|---|
| `data/jobs.json` (~20–25 jobs) | **O\*NET** database (free text/Excel download: Occupation Data, Job Zones) + **BLS OEWS** state wage file (CA rows) | Download, filter to curated SOC codes, join. Python/pandas. | Stream 2 |
| `data/stories.json` (6–9) | **Synthetic**, written by us, 1–2 per family | Write by hand or have Claude draft, then edit for realism | Stream 3 |
| `data/training.json` (6–10) | **Real** local programs from public pages (City College, county workforce/job center, nonprofit reentry training) | Hand-curate: name, provider, length, cost, link | Stream 3 |

**Curated job list (starting point; adjust to time):**
Cook · Food prep worker · Dishwasher · Janitor/cleaner · Landscaping worker · Home health aide · Nursing assistant (CNA) ⚠️ · Medical assistant · Phlebotomist ⚠️ · Childcare worker ⚠️ · Hairdresser/cosmetologist ⚠️ · Retail salesperson · Cashier · Customer service rep · Receptionist · Office clerk · Construction laborer · Painter · Warehouse/stock worker · Forklift operator · Community health worker · Peer support / social & human service assistant

⚠️ = typically state-licensed, so flag "a record may affect licensing; check with the CA licensing board before paying for training." Verify each flag quickly; don't overstate.

**Schemas**
```json
// jobs.json
{"soc": "35-2014", "title": "Cook, Restaurant", "family_code": "35",
 "family": "Food Preparation & Serving", "job_zone": 2,
 "training": "A few months on the job", "ca_median_hourly": 0.00,
 "licensed": false, "license_note": "", "skills": ["food safety", "speed", "teamwork"]}

// stories.json
{"id": "s1", "name": "Denise R.", "family_code": "35",
 "story": "...", "now": "Line cook, 2 years", "advice": "...", "synthetic": true}

// training.json
{"id": "t1", "name": "...", "provider": "...", "family_code": "35",
 "length": "12 weeks", "cost": "Free", "location": "San Francisco",
 "url": "https://...", "notes": "Open to people with records"}
```

**Data rules (hackathon):** public or synthetic only. No real people's stories, no real personal info.

---

## 6. Claude calls

**Call #1: profile + matches** (one call, JSON out)
- Input: her answers + the **full jobs.json list** (it's small).
- System prompt essentials:
  - Strengths-based, warm, plain language (8th-grade reading level).
  - Treat prison work as real work experience.
  - **Only recommend jobs from the provided list, by SOC code.** Never invent jobs, wages, programs or laws.
  - Respect her constraints (hours, no car, pay floor).
- Output:
```json
{"skills_profile": {"summary": "...", "skills": ["..."], "experience": ["..."]},
 "matches": [{"soc": "35-2014", "why_it_fits": "...", "first_step": "..."}]}
```
- Code then joins each match to jobs.json (wage, license), stories.json and training.json **by family_code**. Claude never touches the numbers.

**Call #2: cover letter**
- Input: skills profile + chosen job + her own words.
- Rules:
  - Her voice, ~200 words.
  - **Don't mention the conviction.** California's Fair Chance Act generally bars employers from asking before a conditional offer. Frame inside work as e.g. "kitchen experience in an institutional setting" or name it plainly if she prefers. Add a toggle if time.
  - End with a short "If your record comes up in an interview" script: brief, honest, forward-looking.
- Footer on page: *"Not legal advice. Fair chance rules vary by employer and location."*

**(P2) Call #3:** tag a submitted story → family_code.

**Engineering:**
- API key in `st.secrets`, never in code; `.env` in `.gitignore`.
- Cache Maria's outputs so the demo can't fail live.
- Use structured JSON output and wrap the parse in try/except.

---

## 7. Four workstreams

| # | Workstream | Owns | Deliverables |
|---|---|---|---|
| **1** | **App & integration** | `app.py`, deploy | Streamlit 3-tab app live on Streamlit Cloud, Claude API wiring, join logic, job cards |
| **2** | **Jobs data** | `data/jobs.json` | ~20 jobs: O\*NET training/Job Zone + BLS CA median wage + license flag, matching the schema |
| **3** | **Community & training content** | `data/stories.json`, `data/training.json` | 6–9 synthetic stories (1–2 per family), 6–10 **real** local training programs with links |
| **4** | **Prompts, Maria & demo** | `prompts.py`, README, video | System prompts for Claude calls #1 and #2 (test them in Claude chat first), Maria's answers, README, demo script, record + submit |

**Rules:**
- Agree on the schemas (section 5) in the first 10 min. Stream 1 builds against stub data so nobody is blocked.
- **Only Stream 1 edits `app.py`.** Streams 2–3 only touch `/data`; Stream 4 only touches `prompts.py` + README. No merge conflicts.
- Push small commits often. Post in team chat when a file is ready.

---

## 8. Schedule (11:00 → 12:30, with a 15-min buffer before the 12:45 deadline)

| Time | Stream 1: App | Stream 2: Jobs data | Stream 3: Stories & training | Stream 4: Prompts & demo |
|---|---|---|---|---|
| **11:00–11:10** | Create repo, share link, start Streamlit Cloud deploy | Download O\*NET + BLS state wage file | Pick families to cover; find 3–4 local training sources | Confirm schemas with team; draft Maria's answers |
| **11:10–11:40** | 3 tabs, question form, stub data, **app live on URL** | Build `jobs.json` (pandas join, CA wages, license flags) | Write stories; curate programs | Write prompt #1 (profile + matches JSON); test with Maria in Claude chat |
| **11:40 ✅** | **Checkpoint 1:** app live · data files pushed · prompt #1 works | | | |
| **11:40–12:00** | Wire Claude call #1 via `prompts.py`; job cards joined to real data | Verify wages + license flags, then help Stream 1 test | Push files; check family tags | Write prompt #2 (cover letter + record script); start README |
| **12:00 ✅** | **Checkpoint 2:** Maria runs end to end (profile → jobs → stories/training) | | | |
| **12:00–12:10** | Cover letter button; Community + Train Up tabs | Bug-test on live URL | Bug-test on live URL; take screenshots | Finish README + demo script |
| **12:10 🛑** | **FEATURE FREEZE:** bug fixes only. Run Maria on the live URL and cache her output. | | | |
| **12:10–12:25** | On call for fixes | Draft LinkedIn post | Help with recording | **Record demo** (2 takes max) |
| **12:25–12:30** | Final push to GitHub | | | **Submit video + repo link** |

**Cut order if behind at 12:00:** (1) separate Community tab → stories on job cards only, (2) Train Up tab → training on job cards only, (3) record script → cover letter only. **Never cut:** Maria's story → profile → job matches → cover letter.

---

## 9. Demo video script (~2:30)

1. **(0:00–0:20) Hook.** "When women leave jail, finding work is one of the biggest factors in whether they go back. But the work many did inside never makes it onto a résumé." (Use one real stat, e.g. BJS: 63% of women released from state prison were rearrested within 5 years.)
2. **(0:20–1:30) Maria.** Messy story → skills profile → job matches with real wages + license flag → click Cook → stories from women in food service + local training → cover letter side by side with her raw words.
3. **(1:30–2:00) Community + Train Up tabs.** Quick tour; "every job, story and program connects through federal job families."
4. **(2:00–2:30) Built responsibly + what's next.** Real O\*NET/BLS data; Claude can't invent jobs or wages; nothing stored; synthetic stories. Next: real community stories with consent + moderation, more counties, partner with reentry orgs and job centers.

---

## 10. Claude Code starter prompt (Stream 1, use plan mode)

> Build a Streamlit app "Next Chapter" for women seeking work after incarceration. Three tabs: My Path, Community, Train Up. Data files in /data: jobs.json, stories.json, training.json (schemas in README). My Path: a form with guided text questions (past work, work/programs while incarcerated, timeline, money needs, constraints, strengths, concerns, city). On submit, call the Claude API once with the answers plus the full jobs list and return JSON {skills_profile, matches:[{soc, why_it_fits, first_step}]}. Claude may only pick SOC codes from the list. Render a skills profile card, then 3–5 job cards joined to jobs.json (wage, training, license flag) and, by family_code, to stories and training programs. Each card has a "Write my cover letter" button that calls Claude for a ~200-word letter in her voice that does not disclose a conviction, plus a short "if your record comes up" script. Community tab: filter stories by family. Train Up tab: filter programs by family. API key from st.secrets. Show "Nothing you type is saved" and "Not legal advice" notes. Use stub data first so the UI works before the real files land. Commit after each working step.

---

## 11. Open questions (defaults in bold, change if needed)
1. Location for wages/training: **California / San Francisco**
2. "$" on the sketch means: **her pay needs (hourly/monthly floor + how soon)**
3. Community page: **read-only seeded synthetic stories** for the demo
4. Stack: **Python + Streamlit on Streamlit Community Cloud**
