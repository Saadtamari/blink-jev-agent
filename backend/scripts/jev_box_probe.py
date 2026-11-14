"""Measure Jev Box accuracy and confidence against true element positions on the fixture site.

Usage (from backend/): .venv/Scripts/python scripts/jev_box_probe.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.browser import BrowserPool, screenshot  # noqa: E402
from app.clients.jev_client import RealJev  # noqa: E402

FIX = Path(__file__).resolve().parent.parent / "tests" / "fixture_site"
CASES = [
    ("index.html", "the orange 'Search flights' button", "#go"),
    ("index.html", "the 'Leaving from' input field", "#from"),
    ("index.html", "the 'Going to' input field", "#to"),
    ("index.html", "the 'Reject all' button in the cookie banner", "#reject"),
    ("index.html", "the 'Member deals' link", "a"),
    ("results.html?from=Cairo&to=Tokyo", "the price of the Emirates flight", ".result:nth-child(2) .price"),
    ("results.html?from=Cairo&to=Tokyo", "the 'Select' button of the first result", ".result:nth-child(1) a"),
    ("checkout.html", "the 'Pay now' button", "#pay"),
]


async def main():
    calls = []
    jev = RealJev(on_call=calls.append)
    pool = BrowserPool(headless=True)
    ctx = await pool.new_context()
    page = await ctx.new_page()
    hits = 0
    for url, target, sel in CASES:
        await page.goto((FIX / url.split("?")[0]).as_uri() + ("?" + url.split("?")[1] if "?" in url else ""))
        await page.wait_for_timeout(300)
        bb = await page.locator(sel).first.bounding_box()
        shot = await screenshot(page)
        p = await jev.perceive(shot, target=target)
        inside = p.box and bb["x"] <= p.box.cx <= bb["x"] + bb["width"] and bb["y"] <= p.box.cy <= bb["y"] + bb["height"]
        hits += bool(inside)
        print(f"{'HIT ' if inside else 'MISS'} vis={p.target_visible:.2f} boxconf={p.box.confidence if p.box else None} "
              f"center=({p.box.cx:.0f},{p.box.cy:.0f}) true=({bb['x'] + bb['width'] / 2:.0f},{bb['y'] + bb['height'] / 2:.0f}) "
              f"{calls[-1]['ms']}ms  {target}")
    print(f"\n{hits}/{len(CASES)} box centers inside the true element; mean latency "
          f"{sum(c['ms'] for c in calls) / len(calls):.0f} ms; total cost ${sum(c['cost'] for c in calls):.5f}")
    await jev.aclose()
    await pool.close()


asyncio.run(main())
