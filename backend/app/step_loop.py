"""The step loop: PERCEIVE -> LOCATE -> DECIDE -> ACT -> VERIFY.

Speed design:
  * LOCATE tries site memory, then the DOM fast path (no model call), then Jev.
  * VERIFY is fused with the NEXT step's perception: one Jev call answers "did the last
    action work?" + "what state is the page in?" + "where is the next target?".
    That perception is carried into the next step, so a typical step costs one Jev call.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from playwright.async_api import Page

from . import dom_fastpath, extractor, popups, recovery, safety
from .browser import click_at, screenshot, scroll, type_at, wait_settled
from .clients.jev_client import Perception
from .context import RunContext
from .imaging import Shot
from .models import HANDOFF_STATES, Box, Branch, PageState, Step, StepResult

LOCATE_ACTIONS = {"click", "type", "select"}


@dataclass
class Carry:
    """Perception computed at the end of the previous step, reused by the next one."""

    shot: Shot
    perception: Perception


def needs_target(step: Step | None) -> str | None:
    if step is None:
        return None
    if step.action in LOCATE_ACTIONS or step.action == "extract":
        return step.target
    return None


class StepFailed(Exception):
    pass


async def _shot(ctx: RunContext, page: Page, branch_id: str, step_id: str, tag: str) -> Shot:
    s = await screenshot(page, ctx.dir / "shots", f"{branch_id}_{step_id}_{tag}_{int(time.time() * 1000) % 100000}")
    ctx.emit("screenshot", {"path": s.path, "url": s.url, "step_id": step_id, "tag": tag}, branch_id=branch_id)
    return s


async def _settle_state(ctx: RunContext, page: Page, branch: Branch, step: Step, carry: Carry | None
                        ) -> tuple[Shot, Perception, str | None]:
    """Get a usable perception of the page, handling popups / loading / handoffs.

    Returns (shot, perception, stop_reason). stop_reason is "payment", "handoff_failed" or None.
    """
    target = needs_target(step)
    context = f"Goal: {branch.goal}. Next step: {step.action} {step.target or ''}".strip()
    for _ in range(5):
        if carry is not None and (carry.perception.target == target):
            shot, p = carry.shot, carry.perception
            carry = None
        else:
            shot = await _shot(ctx, page, branch.id, step.id, "before")
            p = await ctx.jev.perceive(shot, context=context, target=target)
        ctx.emit("log", {"perception": {"state": p.state.value, "state_conf": round(p.state_conf, 3),
                                        "target": target, "locate_conf": p.locate_conf,
                                        "box": p.box.model_dump() if p.box else None}}, branch_id=branch.id)
        if p.state == PageState.PAYMENT:
            safety.payment_stop(ctx, page.url, branch.id, "Jev detected a payment page.")
            return shot, p, "payment"
        if p.state in HANDOFF_STATES and p.state_conf >= 0.5:
            ok = await safety.wait_for_user(ctx, page, branch.id, p.state,
                                            f"Jev detected a {p.state.value.replace('_', ' ')}.")
            if not ok:
                return shot, p, "handoff_failed"
            continue
        if p.state in (PageState.COOKIE_POPUP, PageState.MODAL) and p.state_conf >= 0.5:
            await popups.dismiss(ctx, page, p.state, branch.id)
            continue
        if p.state == PageState.LOADING and p.state_conf >= 0.6:
            await asyncio.sleep(1.0)
            continue
        return shot, p, None
    return shot, p, None


async def _locate(ctx: RunContext, page: Page, shot: Shot, p: Perception, step: Step, force_jev: bool
                  ) -> tuple[Box | None, str, float | None, str]:
    """Returns (box, used, confidence, problem)."""
    target = step.target or ""
    vw, vh = shot.width, shot.height
    if not force_jev and ctx.use_site_memory and ctx.memory is not None:
        b = ctx.memory.lookup(page.url, target, vw, vh)
        if b is not None:
            ctx.metrics.cache_hits += 1
            return b, "site_memory", b.confidence, ""
    if not force_jev and ctx.use_dom_fastpath:
        b = await dom_fastpath.resolve(page, target)
        if b is not None:
            return b, "dom_fastpath", b.confidence, ""
    if p.box is None or p.target != target:
        p = await ctx.jev.perceive(shot, context=f"Locate: {target}", target=target)
    conf = p.locate_conf
    s = ctx.settings
    if p.box is not None and conf >= s.conf_act:
        return p.box, "jev", conf, ""
    if p.box is not None and conf >= s.conf_check:
        # double-check: does the DOM element under the box center look like the target?
        text = await dom_fastpath.element_text_at(page, p.box.cx, p.box.cy)
        if dom_fastpath.text_matches_target(text, target) >= 0.5 or (p.target_visible or 0) >= 0.75:
            return p.box, "jev", conf, ""
        return None, "jev", conf, f"Jev box confidence {conf:.2f} not confirmed by the page"
    return None, "jev", conf, f"Jev could not find the target confidently ({conf:.2f})"


async def _act(page: Page, step: Step, box: Box) -> None:
    if step.action == "click":
        await click_at(page, box.cx, box.cy)
    elif step.action == "type":
        await type_at(page, box.cx, box.cy, step.value or "")
    elif step.action == "select":
        await click_at(page, box.cx, box.cy)
        await asyncio.sleep(0.3)
        tag = await page.evaluate("([x,y]) => { const e = document.elementFromPoint(x,y); return e ? e.tagName : '' }",
                                  [box.cx, box.cy])
        if tag == "SELECT":
            await page.evaluate(
                "([x,y,v]) => { const s = document.elementFromPoint(x,y); const o = [...s.options].find("
                "o => o.text.toLowerCase().includes(v.toLowerCase()) || o.value === v); if (o) { s.value = o.value;"
                " s.dispatchEvent(new Event('change', {bubbles: true})); } }", [box.cx, box.cy, step.value or ""])
            await page.keyboard.press("Escape")
        else:
            await page.keyboard.type(step.value or "", delay=15)
            await page.keyboard.press("Enter")


async def _recover(ctx: RunContext, page: Page, shot: Shot, branch: Branch, step: Step,
                   history: list[StepResult], problem: str) -> tuple[Box | None, str]:
    """Ask the LLM what to do. Returns (box to act on, outcome) where outcome is
    'act' | 'skip' | 'retry' | 'fail'."""
    try:
        d = await recovery.replan_step(ctx, shot, step, branch.goal, history, problem)
    except Exception as e:
        ctx.emit("error", {"where": "recovery", "error": str(e)[:300]}, branch_id=branch.id)
        return None, "fail"
    ctx.emit("log", {"recovery": d.model_dump()}, branch_id=branch.id)
    if d.decision == "skip":
        return None, "skip"
    if d.decision == "wait":
        await asyncio.sleep(2.0)
        return None, "retry"
    if d.decision == "scroll":
        await scroll(page, d.direction or "down")
        return None, "retry"
    if d.decision == "goto" and d.url:
        if safety.is_blocked_domain(ctx, d.url):
            return None, "fail"
        await page.goto(d.url, timeout=30000)
        await wait_settled(page)
        return None, "retry"
    if d.decision == "click_xy" and d.x_frac is not None and d.y_frac is not None:
        return Box(x=d.x_frac * shot.width - 4, y=d.y_frac * shot.height - 4, w=8, h=8, confidence=0.5), "act"
    if d.decision == "retarget" and d.target:
        p = await ctx.jev.perceive(shot, context=f"Locate: {d.target}", target=d.target)
        if p.box is not None and p.locate_conf >= ctx.settings.conf_check:
            return p.box, "act"
        return None, "fail"
    return None, "fail"


async def run_step(ctx: RunContext, page: Page, branch: Branch, step: Step, next_step: Step | None,
                   carry: Carry | None, history: list[StepResult]) -> tuple[StepResult, Carry | None, str | None]:
    """Run one step. Returns (result, carry for next step, stop_reason)."""
    t0 = time.time()
    s = ctx.settings
    ctx.emit("step_start", {"step": step.model_dump()}, branch_id=branch.id)

    def done(status: str, used: str = "none", **kw) -> StepResult:
        r = StepResult(step_id=step.id, action=step.action, target=step.target, status=status, used=used,
                       duration_ms=int((time.time() - t0) * 1000), **kw)
        if status in ("ok", "retried", "recovered"):
            ctx.metrics.add_step(used)
        return r

    # ---- safety gates before anything else ----------------------------------------
    if safety.is_payment_step(step):
        safety.payment_stop(ctx, page.url, branch.id, f"Step '{step.target}' looks like a payment action.")
        return done("blocked", note="payment action blocked"), None, "payment"
    if safety.is_sensitive_value(step):
        return done("blocked", note="sensitive value (card / password / ID) blocked"), None, None

    # ---- actions without a target ---------------------------------------------------
    if step.action == "goto":
        url = step.value or step.target or ""
        if safety.is_blocked_domain(ctx, url):
            return done("blocked", note="domain blocked"), None, None
        try:
            await page.goto(url, timeout=int(s.step_timeout_s * 1000))
        except Exception as e:
            return done("failed", note=f"goto failed: {str(e)[:120]}"), None, None
        await wait_settled(page)
        return done("ok"), None, None
    if step.action == "wait":
        try:
            secs = float(step.value or 1.5)
        except ValueError:
            secs = 1.5
        await asyncio.sleep(min(secs, 10))
        return done("ok"), None, None
    if step.action == "scroll":
        await scroll(page, step.value or "down")
        return done("ok"), None, None

    # ---- perceive (popups, loading, handoffs, payment) -------------------------------
    shot, p, stop = await _settle_state(ctx, page, branch, step, carry)
    if stop == "payment":
        return done("blocked", note="payment page"), None, "payment"
    if stop == "handoff_failed":
        return done("handoff", note="user did not complete the check"), None, "handoff_failed"

    if step.action == "extract":
        try:
            data = await extractor.extract(ctx, page, shot, step, p, branch.goal)
            if not data.get("items"):
                # nothing found: error page -> reload once; otherwise the data may be below the fold -> scroll once
                notes = str(data.get("notes", "")).lower()
                if p.state == PageState.ERROR or "error" in notes:
                    how = "reload"
                    await page.reload(timeout=int(s.step_timeout_s * 1000))
                    await wait_settled(page)
                else:
                    how = "scroll"
                    await scroll(page, "down", 800)
                ctx.emit("log", {"extract_retry": how, "reason": notes[:200]}, branch_id=branch.id)
                shot, p, stop = await _settle_state(ctx, page, branch, step, None)
                if stop:
                    return done("blocked" if stop == "payment" else "handoff"), None, stop
                data = await extractor.extract(ctx, page, shot, step, p, branch.goal)
        except Exception as e:
            return done("failed", note=f"extract failed: {str(e)[:160]}"), None, None
        return done("ok", used="jev" if data.get("region") == "jev_crop" else "none", data=data,
                    screenshot_before=shot.path, box=p.box), None, None

    if step.action == "press":
        await page.keyboard.press(step.value or "Enter")
        await wait_settled(page, 6000)
        box, used, conf = None, "none", None
        status = "ok"
    else:
        # ---- locate + decide + act, with retries and LLM recovery ----------------------
        status = "ok"
        box: Box | None = None
        used, conf = "none", None
        attempt = 0
        force_jev = False
        while True:
            box, used, conf, problem = await _locate(ctx, page, shot, p, step, force_jev)
            if box is None:
                rbox, outcome = await _recover(ctx, page, shot, branch, step, history, problem)
                if outcome == "skip":
                    return done("skipped", note="recovery chose to skip", screenshot_before=shot.path), None, None
                if outcome == "act" and rbox is not None:
                    box, used, status = rbox, "llm_recovery", "recovered"
                elif outcome == "retry" and attempt < s.max_step_retries:
                    attempt += 1
                    shot, p, stop = await _settle_state(ctx, page, branch, step, None)
                    if stop:
                        return done("blocked" if stop == "payment" else "handoff"), None, stop
                    continue
                else:
                    return done("failed", note=problem, screenshot_before=shot.path, confidence=conf), None, None
            ctx.emit("action", {"action": step.action, "target": step.target, "value": step.value,
                                "box": box.model_dump(), "used": used, "confidence": conf,
                                "screenshot": shot.path}, branch_id=branch.id)
            await _act(page, step, box)
            await wait_settled(page, 5000)
            await asyncio.sleep(0.25)

            # ---- verify, fused with the next step's perception -------------------------
            if not step.expect:
                break
            shot2 = await _shot(ctx, page, branch.id, step.id, "after")
            p2 = await ctx.jev.perceive(shot2, context=f"Goal: {branch.goal}. Checking the last action.",
                                        target=needs_target(next_step), expect=step.expect)
            if (p2.expect_met or 0) >= 0.5:
                if ctx.memory is not None and used in ("jev", "dom_fastpath", "llm_recovery"):
                    ctx.memory.save(page.url if used != "llm_recovery" else shot.url, step.target or "",
                                    shot.width, shot.height, box)
                r = done(status if attempt == 0 else "retried", used=used, confidence=conf, box=box,
                         screenshot_before=shot.path, screenshot_after=shot2.path)
                return r, Carry(shot2, p2), None
            # verify failed
            if used == "site_memory" and ctx.memory is not None:
                ctx.memory.forget(shot.url, step.target or "", shot.width, shot.height)
            if attempt >= s.max_step_retries:
                r = done("failed", used=used, confidence=conf, box=box, screenshot_before=shot.path,
                         screenshot_after=shot2.path,
                         note=f"expected outcome not seen (p={p2.expect_met or 0:.2f})")
                return r, Carry(shot2, p2), None
            attempt += 1
            force_jev = True
            shot, p, stop = await _settle_state(ctx, page, branch, step, None)
            if stop:
                return done("blocked" if stop == "payment" else "handoff"), None, stop

    # no expectation to verify: just hand the next step a fresh look later
    return done(status, used=used, confidence=conf, box=box, screenshot_before=shot.path), None, None
