"""Check that real Jev works through OpenRouter, and which image format it accepts.

Usage (from backend/):  .venv/Scripts/python scripts/jev_smoke.py
Needs OPENROUTER_API_KEY in backend/.env. Costs a fraction of a cent.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.browser import BrowserPool, screenshot  # noqa: E402
from app.clients.jev_client import RealJev  # noqa: E402
from app.config import get_settings  # noqa: E402

FIXTURE = (Path(__file__).resolve().parent.parent / "tests" / "fixture_site" / "index.html").as_uri()
URLS = ["https://openrouter.ai/api/alpha/decisions", "https://openrouter.ai/api/v1/alpha/decisions"]


async def main() -> None:
    s = get_settings()
    if not s.openrouter_api_key:
        print("Set OPENROUTER_API_KEY in backend/.env first.")
        return
    pool = BrowserPool(headless=True)
    ctx = await pool.new_context()
    page = await ctx.new_page()
    await page.goto(FIXTURE)
    shot = await screenshot(page)
    print(f"screenshot {shot.width}x{shot.height}, sending {len(shot.send) // 1024} KB {shot.send_format}")

    calls = []
    working = None
    for url in [s.jev_decisions_url] + [u for u in URLS if u != s.jev_decisions_url]:
        for mode in ("image_url", "assets"):
            jev = RealJev(on_call=calls.append, image_mode=mode, url=url)
            try:
                p = await jev.perceive(shot, context="Smoke test on a flight search page.",
                                       target="the 'Search flights' button", expect="a cookie banner is visible")
                print(f"\nOK  url={url}  image_mode={mode}")
                print(f"  page state: {p.state.value}  probs={json.dumps(p.state_probs)}")
                print(f"  target visible p={p.target_visible}  box={p.box}  locate_conf={p.locate_conf}")
                print(f"  'cookie banner visible' p={p.expect_met}")
                print(f"  latency {calls[-1]['ms']} ms, cost ${calls[-1]['cost']:.6f}, model {calls[-1]['model']}")
                working = (url, mode)
            except Exception as e:
                print(f"\nFAIL url={url} image_mode={mode}: {str(e)[:300]}")
            finally:
                await jev.aclose()
            if working:
                break
        if working:
            break
    if working:
        print(f"\nPut these in backend/.env:\nJEV_DECISIONS_URL={working[0]}\nJEV_IMAGE_MODE={working[1]}")
        if p.box:
            print(f"Expected the box near the orange 'Search flights' button; got center ({p.box.cx:.0f}, {p.box.cy:.0f}).")
    else:
        print("\nJev did not work with any combination. Set JEV_PROVIDER=llm_fallback to keep going.")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
