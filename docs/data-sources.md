# Dynamic Data Sources for Next Chapter

Research on live/open datasets we can pull from the internet to replace the hand-curated
JSON, keyed on SOC occupation codes. Verified Nov 2026. Everything below is free unless noted.

## TL;DR — the stack to build on

1. **CareerOneStop API (U.S. DOL)** — one free token covers **jobs, training, licensing,
   apprenticeships, and a reentry-programs directory**, all filterable by occupation code
   (O\*NET↔SOC) and location (ZIP/city/`CA`). This is the keystone.
2. **data.ca.gov EDD OEWS** — authoritative California wages (median + percentiles) by SOC
   and metro (SF/Oakland/San Jose), **no auth**. Use for all wage numbers.
3. **O\*NET Web Services** — occupation enrichment (Job Zones, Bright Outlook, skills). Join
   to wages on the 6-digit SOC.
4. **TrainingProviderResults.gov** — bulk download with real completion/employment/earnings
   outcomes to enrich training records.
5. **Reentry/social-services data is mostly closed** → build on the HSDS standard and
   hand-seed fair-chance employers (details below).

---

## Jobs (live postings)

| Source | SOC / location | Auth & cost | ToS / notes | Diff |
|---|---|---|---|---|
| **CareerOneStop Job Search** ⭐ | O\*NET filter + location+radius | Free DOL token (~1 day approval) | DOL attribution; display-oriented, no bulk resale | 2 |
| **Adzuna** | keyword/location, **no SOC** | Free app_id/key; 250/day, 2.5k/mo | license for publishing; add our own SOC map | 1 |
| **USAJOBS** | OPM series→SOC, location | Free key, self-serve | public/reusable; limited entry-level | 2 |
| **NLx / DirectEmployers** | ~4M postings/day, SOC+loc | **Members only** (gated) | partnership needed | 4 |
| **Honest Jobs / Orijin** | fair-chance roles (best fit) | **No public API** | partnership outreach | 5 |
| Indeed Publisher | — | **closed 2024** | unavailable | — |
| CalJOBS / CA EDD | LMI data only, **no live-job API** | open portal | link-out only | — |

**Pick:** CareerOneStop primary (native occupation filtering fits our SOC design), Adzuna
for volume/Bay-Area coverage, Honest Jobs/Orijin as a future partnership (best content fit).

## Training programs

| Source | Returns | Auth | CA filter | Diff |
|---|---|---|---|---|
| **CareerOneStop Training Finder** ⭐ | program+provider, CIP+SOC, tuition, length | Free COS token | zip+radius / `CA` / SOC | 2 |
| **TrainingProviderResults.gov** | + completion/employment/**median earnings** | Free, no key; bulk .xlsx | filter to CA; refresh yearly | 2 |
| **Credential Engine Registry** | credential, cost, SOC+CIP, geo | Free; dev agreement (90-day key) | growing CA CCC coverage | 3 |
| **Apprenticeship Finder (COS)** | sponsors, occupation, location | Free COS token | location+radius | 2 |
| CA Community Colleges (DataMart/LaunchBoard/Rising Scholars) | programs, outcomes, Rising Scholars reentry dir. | **No API** (CSV/scrape) | CA-only, TOP→SOC crosswalk | 3–5 |
| CalJOBS / CA ETPL public search | — | **No API/download** | scrape / link-out | 5 |

**Pick:** Training Finder as the live feed (replaces `training.json`), enrich with
TrainingProviderResults.gov outcomes; Credential Engine later.

## Licensing (powers the CNA/HHA warning)

**CareerOneStop License Finder** ⭐ — state-aware (`CA`). Returns license title, the
**licensing agency** (name/phone/URL), and **requirement flags including criminal
background**. For CNA/HHA it surfaces CA Dept. of Public Health. Free, same COS token, diff 2.

## Wages & labor market

| Source | Returns | Auth | CA/Bay | Diff |
|---|---|---|---|---|
| **data.ca.gov EDD OEWS** ⭐ | emp + 10/25/50/75/90 pctile (hourly+annual), ~830 SOCs, 2009–26 | **None** | statewide + SF/Oakland/SJ MSAs | 1 |
| **CareerOneStop wages** | pctiles + mean + outlook, O\*NET→SOC | COS token | state/city/ZIP | 2 |
| **BLS API v2** | OEWS pctiles via series ID | key optional (500/day) | CA=`0600000`, SF MSA `0041860` | 2 |
| **Projections Central** | occupational projections + openings | none | state (CA FIPS `6`) | 2 |
| **O\*NET Web Services** | Job Zones, Bright Outlook, skills (**no wages/geo**) | X-API-Key | national — enrich only | 1 |

**Pick:** data.ca.gov OEWS primary (authoritative CA wages, zero auth); O\*NET to enrich;
Projections Central for "is this a growing field" signal.

## Reentry / social services — honest reality

Mostly **closed, partner-only, or paid.** No single free API covers CA barriers
(childcare/housing/transport/legal) + fair-chance employers.
- **findhelp (Aunt Bertha):** best data, API is Enterprise (~$75k/yr). Future partner only.
- **211 / United Way:** ~200 independent operators, no public open API.
- **Open Referral / HSDS:** a *schema standard*, not hosted data — model our services DB on it.
- **DataSF / data.ca.gov (Socrata SODA):** free, no auth; org/service directories, but no
  dedicated reentry/fair-chance dataset.
- **Fair-chance employers:** no open dataset — hand-seed from Jails to Jobs "Second Chance
  Employers Network" + National Reentry Resource Center + county reentry councils.
- **CareerOneStop "List All ReEntry Programs":** free under the same COS token — wire it in.

**Plan:** adopt the HSDS data model; seed services from Socrata + CareerOneStop reentry
endpoint; hand-seed fair-chance employers. Treat findhelp/211 as later partner integrations.

---

## How this maps onto our architecture

Our `data.py` already abstracts `load_jobs/stories/training` + `join_match`. Add a provider
layer that mirrors the `llm.py` pattern: **if a `CAREERONESTOP_*` / data-source key is set,
fetch live (cached); otherwise fall back to the static JSON.** Same SOC/`family_code` join
downstream — nothing else changes.

Suggested module: `sources/` with `careeronestop.py` (jobs/training/license/reentry),
`wages.py` (data.ca.gov OEWS), `onet.py` (enrichment), each returning our existing dict
shapes so views don't change. Cache with `st.cache_data(ttl=...)`.

### Base URLs
- CareerOneStop: `https://api.careeronestop.org/v1/` · register: careeronestop.org/Developers/WebAPI/registration.aspx
- EDD OEWS: `https://data.ca.gov/api/3/action/datastore_search?resource_id=aef4c53a-7e17-418c-acc1-d189e39b6caa`
- BLS: `https://api.bls.gov/publicAPI/v2/` · O\*NET: `https://services.onetcenter.org/ws/`
- TrainingProviderResults.gov · credreg.net/registry/searchapi · projectionscentral.org

### Phased rollout
1. **Wages live** (data.ca.gov OEWS, no auth) — fastest real-data win; replace seed wages.
2. **CareerOneStop token** → Training Finder + License Finder live (replace `training.json`,
   power licensing warnings dynamically).
3. **Jobs live** via CareerOneStop Job Search (+ Adzuna for volume).
4. **Enrich** with O\*NET (Job Zones, Bright Outlook) + TrainingProviderResults outcomes.
5. **Reentry services**: HSDS model + hand-seeded fair-chance employers; partner feeds later.
