"""Benchmark: Blink vs the LLM-only baseline on the same tasks.

Usage (from backend/):
  .venv/Scripts/python benchmark/run_benchmark.py                 # all 20 tasks, both agents
  .venv/Scripts/python benchmark/run_benchmark.py --only trip_japan price_kindle --repeat 2
  .venv/Scripts/python benchmark/run_benchmark.py --agents blink   # Blink only

Blink runs with the plan cache OFF (it must plan every time, like the baseline). Site memory is ON,
because it is part of Blink; use --no-memory for a cold-start comparison.
Writes data/benchmark/results.json and results.csv (read by the frontend's Benchmark page).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
import sys
import time
import uuid
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.baseline.llm_only_agent import run_baseline  # noqa: E402
from app.browser import BrowserPool  # noqa: E402
from app.config import DATA_DIR  # noqa: E402
from app.context import build_context  # noqa: E402
from app.events import RunEvents  # noqa: E402
from app.models import FinalAnswer  # noqa: E402
from app.orchestrator import run_blink  # noqa: E402
from app.site_memory import SiteMemory  # noqa: E402

TASKS = Path(__file__).parent / "tasks.yaml"
OUT = DATA_DIR / "benchmark"


def check(answer: FinalAnswer | None, spec: dict) -> bool:
    if answer is None:
        return False
    rows = [r for r in answer.table if any(v is not None for v in (r.low, r.mid, r.high))]
    if len(rows) < spec.get("min_rows", 0):
        return False
    hay = " ".join([answer.summary, *answer.notes, *[f"{r.category} {r.note or ''}" for r in answer.table]]).lower()
    return all(any(w.lower() in hay for w in group) for group in spec.get("keywords", []))


async def run_one(agent: str, task: dict, pool: BrowserPool, memory: SiteMemory | None) -> dict:
    run_id = f"bench-{agent}-{task['id']}-{uuid.uuid4().hex[:4]}"
    ev = RunEvents(run_id)
    ctx = build_context(run_id, ev, agent=agent, memory=memory)
    ctx.use_site_memory = memory is not None
    t0 = time.time()
    answer, err = None, None
    try:
        coro = run_blink(ctx, pool, task["goal"], use_plan_cache=False) if agent == "blink" \
            else run_baseline(ctx, pool, task["goal"])
        answer = await asyncio.wait_for(coro, timeout=420)
    except Exception as e:
        err = str(e)[:300]
    ctx.metrics.finished = time.time()
    ev.emit("final", {"answer": answer.model_dump() if answer else None, "metrics": ctx.metrics.snapshot()},
            agent=agent)
    ev.close()
    m = ctx.metrics.snapshot()
    return {"run_id": run_id, "success": check(answer, task.get("check", {})), "time_s": round(time.time() - t0, 2),
            "cost": m["total_cost"], "jev_calls": m["jev_calls"], "llm_calls": m["llm_calls"],
            "steps": m["steps"], "handoffs": m["handoffs"], "error": err}


def summarize(rows: list[dict]) -> dict:
    def agg(agent: str, key: str, fn=statistics.mean):
        vals = [r[agent][key] for r in rows if agent in r and r[agent].get(key) is not None]
        return round(fn(vals), 4) if vals else None

    s = {"n": len(rows)}
    for a in ("blink", "baseline"):
        if any(a in r for r in rows):
            s[a] = {"mean_time_s": agg(a, "time_s"), "median_time_s": agg(a, "time_s", statistics.median),
                    "mean_cost": agg(a, "cost"), "success_rate": round(
                        sum(1 for r in rows if a in r and r[a]["success"]) / max(1, sum(1 for r in rows if a in r)), 3),
                    "mean_llm_calls": agg(a, "llm_calls"), "mean_jev_calls": agg(a, "jev_calls")}
    if "blink" in s and "baseline" in s:
        b, l = s["blink"], s["baseline"]
        s["speedup"] = round(l["mean_time_s"] / b["mean_time_s"], 2) if b["mean_time_s"] else None
        s["cost_ratio"] = round(l["mean_cost"] / b["mean_cost"], 2) if b["mean_cost"] else None
    return s


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--agents", nargs="*", default=["blink", "baseline"])
    ap.add_argument("--no-memory", action="store_true")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
    if args.only:
        tasks = [t for t in tasks if t["id"] in args.only]
    pool = BrowserPool(headless=True if args.headless else None)
    memory = None if args.no_memory else SiteMemory()
    rows = []
    OUT.mkdir(parents=True, exist_ok=True)
    for rep in range(args.repeat):
        for t in tasks:
            row = {"id": t["id"], "goal": t["goal"], "repeat": rep}
            for agent in args.agents:  # one agent at a time, so they never compete for bandwidth
                print(f"[{rep}] {t['id']} :: {agent} ...", flush=True)
                row[agent] = await run_one(agent, t, pool, memory if agent == "blink" else None)
                r = row[agent]
                print(f"    success={r['success']} time={r['time_s']}s cost=${r['cost']:.4f} "
                      f"jev={r['jev_calls']} llm={r['llm_calls']} {r['error'] or ''}", flush=True)
            rows.append(row)
            result = {"generated": time.time(), "tasks": rows, "summary": summarize(rows)}
            (OUT / "results.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    with (OUT / "results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "repeat", "agent", "success", "time_s", "cost", "jev_calls", "llm_calls", "steps", "error"])
        for r in rows:
            for a in args.agents:
                if a in r:
                    x = r[a]
                    w.writerow([r["id"], r["repeat"], a, x["success"], x["time_s"], x["cost"], x["jev_calls"],
                                x["llm_calls"], x["steps"], x["error"] or ""])
    print(json.dumps(summarize(rows), indent=1))
    await pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
