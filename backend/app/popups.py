"""Auto-dismiss cookie banners and other popups in one quick step.

Order of preference (privacy first): reject / necessary only > close > accept (last resort,
only when nothing else exists, so the task can continue).
"""
from __future__ import annotations

import asyncio
import re

from playwright.async_api import Page

from . import dom_fastpath
from .browser import click_at, screenshot
from .context import RunContext
from .models import PageState

_REJECT = re.compile(r"^(reject( all)?|decline( all)?|deny|only necessary|necessary only|use necessary cookies only|refuse|disagree)", re.I)
_CLOSE = re.compile(r"^(close|×|✕|x|no,? thanks|not now|maybe later|skip|dismiss|continue without)", re.I)
_ACCEPT = re.compile(r"^(accept( all)?|agree|i agree|allow all|ok|got it)", re.I)


async def _dom_pick(page: Page) -> tuple[str, dict] | None:
    els = await dom_fastpath.collect(page)
    for kind, rx in (("reject", _REJECT), ("close", _CLOSE), ("accept", _ACCEPT)):
        for e in els:
            label = (e.get("text") or e.get("aria") or e.get("value") or e.get("title") or "").strip()
            if label and len(label) < 40 and rx.search(label) and not e.get("covered"):
                return kind, e
    return None


async def dismiss(ctx: RunContext, page: Page, state: PageState, branch_id: str) -> bool:
    picked = await _dom_pick(page)
    if picked:
        kind, e = picked
        await click_at(page, e["x"] + e["w"] / 2, e["y"] + e["h"] / 2)
        ctx.emit("action", {"action": "dismiss_popup", "how": f"dom:{kind}", "state": state.value},
                 branch_id=branch_id)
        await asyncio.sleep(0.5)
        return True
    shot = await screenshot(page)
    target = ("the button that rejects or declines non-essential cookies (or closes the banner)"
              if state == PageState.COOKIE_POPUP else "the close (X) or 'no thanks' button of the popup")
    p = await ctx.jev.perceive(shot, context="Dismissing a popup that covers the page.", target=target)
    if p.box and p.locate_conf >= ctx.settings.conf_check:
        await click_at(page, p.box.cx, p.box.cy)
        ctx.emit("action", {"action": "dismiss_popup", "how": "jev", "confidence": p.locate_conf,
                            "box": p.box.model_dump()}, branch_id=branch_id)
        await asyncio.sleep(0.5)
        return True
    await page.keyboard.press("Escape")
    ctx.emit("action", {"action": "dismiss_popup", "how": "escape"}, branch_id=branch_id)
    await asyncio.sleep(0.3)
    return False
