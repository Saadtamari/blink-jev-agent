# Blink: the LLM plans, Jev clicks



https://github.com/user-attachments/assets/e480f985-feee-4487-bf9c-fb7b2d5798cb

Blink is a web agent built for the Jevathon. It does multi-site research tasks much faster and more cheaply than "LLM looks at every screenshot" agents.

- An **LLM** (via OpenRouter) turns your goal into a plan of **independent branches**.
- Each branch runs in its **own browser tab, in parallel**.
- **Jev** (TypeSafe's typed decision model, `typesafe/jev-1.14` via OpenRouter) carries out every step from screenshots. It answers *what state is this page in?* (choice), *where is the element?* (Box) and *did the action work?* (noul), each with probabilities.
- The LLM comes back only to extract prices from small crops, recover from failures and write the final answer.
- **Bot checks / CAPTCHAs and logins:** Blink pauses and hands control to you, never solving them itself. **Payments:** hard stop, every time.

> Demo goal: *"I want to go to Japan for 7 days in March from Cairo. How much will it cost?"*
> → 4 parallel tabs (flights, hotels, visa, daily costs) → cost table (low / mid / high) with a source for every number.

## Measured results (live websites, real Jev 1.14 via OpenRouter)

Japan trip goal, race mode, same machine, same models:

| | Blink | LLM-only agent |
|---|---|---|
| Time | **21.3 s** | 122.8 s |
| Cost | **$0.0118** | $0.0587 |
| Model calls | 6 Jev + 7 LLM | 46 LLM |
| Answer | flights, hotels, daily costs, visa, totals in USD and EGP | hotels missing |

Benchmark, 6 live tasks (trips to Japan and Paris, a visa question, an exchange rate, AirPods prices, Berlin vs Madrid costs),
one agent at a time, headless:

| | Blink | LLM-only agent |
|---|---|---|
| Mean time per task | **16.6 s** (median 12.6 s) | 122.4 s (median 113.5 s) |
| Mean cost per task | **$0.0115** | $0.0360 |
| Success rate | **83 %** (5/6) | 67 % (4/6) |
| Model calls per task | 2.5 Jev + 4.7 LLM | 30.2 LLM |

**7.4× faster, 3.1× cheaper.** Blink's one failure (AirPods prices) is a site limit: eBay serves headless browsers an
error page and Amazon hides real AirPods prices behind "See options". Blink reported "not found" rather than
inventing prices. Running headed (`HEADLESS=false`, the default) is closer to a real user.

Jev measurements (`scripts/jev_box_probe.py`): **8/8** Box answers landed on the right element, **~420 ms** and
**~$0.00015** per call (state + visibility + box + verify questions answered together in one call).

## Architecture

```
 Frontend (Next.js) — mission control: live tabs + Jev boxes, step timeline, timer, $ counter, race, benchmark
        ▲ WebSocket events                                  │ goal
 ┌──────┴───────────────────────────────────────────────────▼──────────────┐
 │ FastAPI orchestrator                                                      │
 │  planner (LLM) ─► task graph ─► branches in parallel (1 browser context each)
 │     step loop:  PERCEIVE ─► LOCATE ─► DECIDE ─► ACT ─► VERIFY             │
 │                 (Jev)      memory → DOM → Jev   Playwright  (Jev, fused   │
 │                                                             with next step)
 │  extractor: Jev box → crop → LLM reads crop     recovery: LLM re-plans step│
 │  safety: bot check/login → hand off to user; payment → hard stop          │
 │  synthesizer (LLM) → final answer + sources                               │
 └───────────────────────────────────────────────────────────────────────────┘
```

### Why it's fast
1. **Parallel branches:** 3–4 tabs at once instead of one long chain.
2. **Fused Jev perception:** one Jev call answers "did the last action work?", "what state is the page in?" and "where is the next target?". Most steps cost **one** Jev call.
3. **DOM fast path:** obvious buttons and fields are read from the page itself, with no model call.
4. **Site memory:** element locations are cached per site, so repeat runs skip Jev. Every remembered box is still verified.
5. **Direct URLs:** the planner uses search URLs with parameters, which skips form filling.
6. **Popup auto-dismiss:** cookie banners are closed in one step, choosing "reject" first.
7. **Crop-then-read:** the LLM reads a small crop of the page, not the whole screenshot.
8. **Plan cache, streaming partial results, resized JPEG screenshots.**
9. **Fast planner model:** Gemini 2.5 Flash plans in ~3.5 s versus ~12.5 s for Claude Sonnet 4.5 (`scripts/model_race.py`).

### Correct numbers, not guessed ones
- **Automatic currency tabs:** sites often show prices in the visitor's local currency (Google showed Jordanian dinars).
  When a branch returns a new currency, Blink opens an exchange-rate tab on Wise (executed by Jev, in parallel) and
  converts in code. Your home currency (for example EGP for a trip from Cairo) is fetched up front.
  Rates are cached for 6 hours.
- **Totals are computed in code**, not by the LLM, and the totals sentence in the summary is written by code too.
- The LLM is told which rates are missing and is never allowed to relabel a currency or estimate a price.

### What Jev's confidence means (measured)
Jev's Box confidence ranged from 0.41 to 0.94 on boxes that were all correct, so it reflects how tight the box is, not
whether it's right. Blink uses Jev's companion "is the target visible?" probability as the main signal and Box
confidence only as a sanity check.

### Confidence routing
| Jev confidence | What Blink does |
|---|---|
| ≥ 0.85 | act immediately |
| 0.60 – 0.85 | double-check against the DOM element under the box |
| < 0.60 | the LLM re-plans the step (retarget / scroll / goto / skip) |

## Setup

Requirements: Python 3.12 (via [uv](https://docs.astral.sh/uv/)), Node 20+.

```bash
cd backend
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
.venv/Scripts/python -m playwright install chromium      # macOS/Linux: .venv/bin/python
cp .env.example .env                                     # then put your OpenRouter key in .env
```

```bash
cd frontend
npm install
```

One **OpenRouter key** powers both the LLM and Jev, so no separate TypeSafe account is needed. Check that Jev works:

```bash
cd backend
.venv/Scripts/python scripts/jev_smoke.py
```

It prints Jev's page state, the box it found and the cost, and tells you which `JEV_DECISIONS_URL` / `JEV_IMAGE_MODE` to keep.

## Run

```bash
cd backend && .venv/Scripts/python serve.py        # API on :8000 (opens a real Chromium window)
```

```bash
cd frontend && npm run dev                          # UI on http://localhost:3000
```

- **Blink mode:** type a goal and press Go.
- **Race mode:** Blink and the LLM-only baseline run side by side with their own timers and $ counters.
- **Your turn:** when a tab hits a bot check or a login, solve it in the Chromium window and press **Continue**. Blink also resumes by itself when it sees the check is gone.
- **Stopped before payment:** Blink never pays. It shows the page so you can finish it yourself.

### Offline mode (no key, no internet)
```
LLM_PROVIDER=offline
JEV_PROVIDER=mock
```
This runs the full system against a local test site (`/fixture`): parallel tabs, a cookie banner, a bot-check handoff and a payment stop. Use it for UI work and as a last-resort demo.

### Demo backup
On the **Runs** page, **Replay** shows any past run again with its real timing. **Save as demo** plus `DEMO_MODE=true` makes every Go replay that run, which covers you if the Wi-Fi or a site fails on stage.

## Benchmark

```bash
cd backend
.venv/Scripts/python benchmark/run_benchmark.py                       # 20 tasks, Blink vs LLM-only
.venv/Scripts/python benchmark/run_benchmark.py --only trip_japan --repeat 3
```

The agents run one after another so they never compete for bandwidth. Blink plans fresh every time (plan cache off). Results go to `data/benchmark/results.json` and the **Benchmark** page shows time, cost, success rate and model calls per task. Only measured numbers are shown.

## Tests
 
```bash
cd backend && .venv/Scripts/python -m pytest -q
```

These cover the step loop on the local fixture site with mock Jev: confidence routing, the Jev path, site memory, LLM recovery, the bot-check handoff and resume, payment hard stops (page and button), parallel orchestration, Box conversion and Jev image limits.

## Configuration
See `backend/.env.example`: models, Jev model/endpoint, confidence thresholds, parallel tabs, timeouts, headless, domain blocklist.

## Project layout
```
backend/app/
  orchestrator.py   run manager, parallel branches, race, replay
  branch_runner.py  one branch in one browser context
  step_loop.py      PERCEIVE → LOCATE → DECIDE → ACT → VERIFY
  planner.py / synthesizer.py / extractor.py / recovery.py   LLM parts
  clients/          jev_client (OpenRouter Decisions API), jev_mock, jev_llm_fallback, llm_client, offline_llm
  dom_fastpath.py / site_memory.py / popups.py / safety.py
  baseline/         LLM-only comparison agent
  prompts/          all prompts (.md)
backend/benchmark/  tasks.yaml + run_benchmark.py
backend/tests/      pytest + fixture_site/
frontend/           Next.js mission control (/, /runs, /benchmark)
```
