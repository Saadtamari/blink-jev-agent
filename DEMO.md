# Blink: 3-minute demo script

## Before you go on stage
1. Start the backend (`cd backend && .venv/Scripts/python serve.py`) and the frontend (`cd frontend && npm run dev`). Open http://localhost:3000.
2. Run the Japan goal once in **Race** mode as a warm-up. This fills the plan cache, site memory and exchange rates.
3. **Backup:** a good race run is already saved as the demo run. If the Wi-Fi or a site fails, set `DEMO_MODE=true` in `backend/.env`, restart the backend, and every **Go** replays it with real timing. You can also use **Runs → Replay**.

## Script

**1. Problem (20 s)**
> "AI agents that browse the web are slow. They send every screenshot to a big model and ask 'what next?', one step at a time. Watch."

**2. The race (60–90 s)**
Pick **Race vs LLM-only**, keep the Japan goal, and press **Go**.
> "Left: Blink. The LLM plans once, then Jev, TypeSafe's decision model, executes every step from screenshots, in 4 tabs at the same time. Right: a normal LLM agent doing the same task."

Point at:
- the 4 live tabs (flights, hotels, daily costs, visa)
- the coloured **boxes**: that's Jev locating elements, with a confidence score
- the **extra currency tab** that appears on its own: "Google showed hotel prices in Jordanian dinars, so Blink opened Wise and read the real rate. No guessing."
- the banner: **"Blink finished in ~15 s, the LLM-only agent is still running"**

**3. The answer (20 s)**
Scroll to the table: flights, hotels, daily costs, visa note, low/mid/high totals in USD and EGP, a source link on every row.
> "Every number has a source. The totals are calculated in code, not by the LLM."

**4. Under the hood (30 s)**
Open a step timeline:
> "Each row shows who handled the step: **DOM** when the page itself is obvious, **Memory** when we've seen the site before, **Jev** for visual decisions, and the **LLM** only when Jev isn't sure. One Jev call answers 'did that work, what page is this, where's the next button', in about 0.4 seconds for a fraction of a cent."

**5. Safety (15 s)**
> "Bot checks and logins: Blink stops and hands you the browser, it never solves them. Payments: hard stop, always."
(Optional: show a "Your turn" or "Stopped before payment" card from an offline run.)

**6. Numbers (20 s)**
Open the **Benchmark** page:
> "6 live tasks: **7.4× faster, 3.1× cheaper, 83% success vs 67%**. Measured, not estimated."

**Close:**
> "Blink: the LLM plans, Jev clicks."

## Numbers to remember
- Japan race: Blink **12–21 s / ~$0.012** vs LLM-only **80–155 s / $0.03–0.07**
- Benchmark (6 tasks): **7.4× faster, 3.1× cheaper, 83% vs 67% success**
- Jev: **8/8** correct boxes, **~0.4 s** and **~$0.00015** per call

## Likely judge questions
- **Why not just the LLM?** It takes ~30 LLM calls per task instead of ~3 Jev calls plus ~5 LLM calls. That's slower and costs more.
- **Why do you trust Jev's boxes?** We measured them (8/8). We trust Jev's "is it visible?" probability more than its box confidence, and verify every action afterwards.
- **What if Jev is unsure?** Below 0.60 confidence the LLM re-plans that step. Between 0.60 and 0.85 we double-check against the page.
- **Bot checks?** Blink detects them and hands them to the user. It never bypasses them.
- **Where does it fail?** On sites that block automation, like eBay in headless mode. It says "not found" instead of inventing numbers.
