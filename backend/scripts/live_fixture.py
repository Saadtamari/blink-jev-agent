"""Run one branch on the local fixture site with REAL Jev + REAL LLM (DOM fast path off, so Jev does every step).

Usage (from backend/): .venv/Scripts/python scripts/live_fixture.py
"""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.branch_runner import run_branch  # noqa: E402
from app.browser import BrowserPool  # noqa: E402
from app.context import build_context  # noqa: E402
from app.events import RunEvents  # noqa: E402
from app.models import Branch, Step  # noqa: E402

FIX = (Path(__file__).resolve().parent.parent / "tests" / "fixture_site" / "index.html").as_uri()


async def main():
    ev = RunEvents("live-fixture-" + uuid.uuid4().hex[:6])
    ctx = build_context(ev.run_id, ev, memory=None)
    ctx.use_dom_fastpath = False
    ctx.use_site_memory = False
    branch = Branch(id="flights", goal="Find flights from Cairo to Tokyo", start_url=FIX, steps=[
        Step(id="s1", action="type", target="the 'Leaving from' input field", value="Cairo", expect="the 'From' field shows 'Cairo'"),
        Step(id="s2", action="type", target="the 'Going to' input field", value="Tokyo", expect="the 'To' field shows 'Tokyo'"),
        Step(id="s3", action="click", target="the orange 'Search flights' button", expect="a list of flight results to Tokyo is shown"),
        Step(id="s4", action="extract", target="the list of flight results with prices",
             extract_schema={"airline": "string", "price": "number", "currency": "string"}),
    ])
    pool = BrowserPool(headless=True)
    bctx = await pool.new_context()
    res = await run_branch(ctx, bctx, branch)
    for s in res.steps:
        print(f"{s.step_id} {s.action:8} {s.status:9} used={s.used:13} conf={s.confidence} {s.duration_ms}ms {s.note or ''}")
    print("extracted:", res.extracted)
    print("metrics:", ctx.metrics.snapshot())
    popups = [e.payload for e in ev.events if e.payload.get("action") == "dismiss_popup"]
    print("popups:", popups)
    await pool.close()


asyncio.run(main())
