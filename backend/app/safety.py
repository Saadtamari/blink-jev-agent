"""Safety rules.

- Bot checks / CAPTCHAs and logins: pause the branch and hand control to the user.
  Blink never tries to solve or bypass them.
- Payment: hard stop. Never click pay/checkout buttons, never type payment data.
"""
from __future__ import annotations

import asyncio
import re
import time

from .browser import screenshot
from .context import RunContext
from .models import HANDOFF_STATES, PageState, Step
from .site_memory import domain_of

PAY_WORDS = re.compile(
    r"\b(pay|payment|checkout|check out|purchase|buy now|place order|book now|complete booking|"
    r"confirm booking|reserve now|enter card|card details|billing|subscribe)\b", re.I)

_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_CVV_CTX = re.compile(r"\b(cvv|cvc|security code|password|passcode|pin|iban|routing|ssn|passport)\b", re.I)


def luhn_ok(digits: str) -> bool:
    d = [int(c) for c in digits if c.isdigit()]
    if len(d) < 13:
        return False
    total = 0
    for i, n in enumerate(reversed(d)):
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def is_payment_step(step: Step) -> bool:
    if step.action not in ("click", "press", "type", "select"):
        return False
    return bool(step.target and PAY_WORDS.search(step.target))


def is_sensitive_value(step: Step) -> bool:
    """Block typing card numbers, CVVs, passwords and ID numbers."""
    if step.action != "type" or not step.value:
        return False
    for m in _CARD.finditer(step.value):
        if luhn_ok(m.group()):
            return True
    if step.target and _CVV_CTX.search(step.target):
        return True
    return False


def is_blocked_domain(ctx: RunContext, url: str) -> bool:
    d = domain_of(url)
    return any(d == b or d.endswith("." + b) for b in ctx.settings.blocked_domains)


async def wait_for_user(ctx: RunContext, page, branch_id: str, state: PageState, reason: str) -> bool:
    """Pause the branch until the user resolves the bot check / login in the browser window.

    Resumes when the user clicks Continue in the UI, or when Jev sees the page is no longer
    a bot check / login. Returns False on timeout or cancel.
    """
    ctx.metrics.handoffs += 1
    ev = ctx.continue_events.setdefault(branch_id, asyncio.Event())
    ev.clear()
    shot = await screenshot(page, ctx.dir / "shots", f"{branch_id}_handoff_{int(time.time())}")
    ctx.emit("handoff", {"kind": state.value, "reason": reason, "url": page.url,
                         "screenshot": shot.path, "message":
                         "Your turn: please complete this check in the browser window, then press Continue."},
             branch_id=branch_id)
    deadline = time.time() + ctx.settings.handoff_timeout_s
    start_url = page.url
    ticks = 0
    while time.time() < deadline and not ctx.cancelled:
        try:
            await asyncio.wait_for(ev.wait(), timeout=3.0)
            break
        except asyncio.TimeoutError:
            pass
        ticks += 1
        try:
            # cheap check every tick when the URL changed, otherwise every ~6 s
            if ctx.agent != "blink":
                # the baseline has no Jev: resume only when the URL changes
                if page.url != start_url:
                    break
            elif page.url != start_url or ticks % 2 == 0:
                shot = await screenshot(page)
                p = await ctx.jev.perceive(shot, context="Checking whether the user finished a check.")
                if p.state not in HANDOFF_STATES:
                    break
        except Exception:
            pass
    else:
        ctx.emit("handoff_resolved", {"resolved": False, "reason": "timeout or cancelled"}, branch_id=branch_id)
        return False
    ctx.emit("handoff_resolved", {"resolved": True, "url": page.url}, branch_id=branch_id)
    return True


def payment_stop(ctx: RunContext, page_url: str, branch_id: str, reason: str) -> None:
    ctx.emit("handoff", {"kind": "payment", "reason": reason, "url": page_url, "message":
                         "Blink stopped before payment. It never pays: open this page to finish it yourself."},
             branch_id=branch_id)
