"""Baseline: a typical "LLM computer-use" agent, for the race and the benchmark.

One tab, sequential. Every step: full screenshot -> vision LLM decides the next action -> execute.
No Jev, no DOM fast path, no site memory, no parallel branches. Same safety rules and metrics.
It gets the same site hints as Blink's planner so the comparison is fair.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import time
from typing import Any, Literal

from pydantic import BaseModel

from .. import safety
from ..browser import BrowserPool, click_at, screenshot, scroll, type_at, wait_settled
from ..context import RunContext
from ..models import BranchResult, FinalAnswer, PageState
from ..prompts import load_prompt
from ..synthesizer import synthesize


class BaselineAction(BaseModel):
    thought: str = ""
    action: Literal["goto", "click", "type", "press", "scroll", "extract", "need_user", "done"]
    x_frac: float | None = None
    y_frac: float | None = None
    text: str | None = None
    url: str | None = None
    key: str | None = None
    direction: Literal["up", "down"] | None = None
    data: list[dict[str, Any]] | None = None


async def run_baseline(ctx: RunContext, pool: BrowserPool, goal: str, max_steps: int = 40) -> FinalAnswer:
    t0 = time.time()
    ctx.emit("branch_start", {"branch": {"id": "baseline", "goal": goal, "start_url": "about:blank", "steps": []}},
             branch_id="baseline")
    bctx = await pool.new_context()
    page = await bctx.new_page()
    collected: list[dict] = []
    history: list[str] = []
    system = (load_prompt("baseline").replace("{today}", dt.date.today().isoformat())
              .replace("{sites}", load_prompt("sites")))
    status = "done"
    try:
        for i in range(max_steps):
            if ctx.cancelled:
                status = "stopped"
                break
            try:
                shot = await screenshot(page, ctx.dir / "shots", f"baseline_{i}")
            except Exception:
                # the page was mid-navigation (or a popup tab took over): give it a moment, then retry once
                await asyncio.sleep(1.5)
                if page.is_closed():
                    page = await bctx.new_page()
                try:
                    shot = await screenshot(page, ctx.dir / "shots", f"baseline_{i}")
                except Exception as e:
                    history.append(f"screenshot failed: {str(e)[:80]}")
                    continue
            ctx.emit("screenshot", {"path": shot.path, "url": shot.url, "step_id": f"b{i}", "tag": "before"},
                     branch_id="baseline")
            user = (f"Goal: {goal}\nCurrent URL: {page.url}\nStep {i + 1} of max {max_steps}.\n"
                    f"Data collected so far: {collected[-10:]}\nLast actions:\n" + "\n".join(history[-6:]))
            st = time.time()
            ctx.emit("step_start", {"step": {"id": f"b{i}", "action": "think", "target": None}}, branch_id="baseline")
            try:
                a = await ctx.llm.chat_json(model=ctx.settings.llm_vision_model, system=system, user=user,
                                            images=[shot.send], schema=BaselineAction, purpose="baseline_step",
                                            max_tokens=700)
            except Exception as e:
                history.append(f"error: {str(e)[:100]}")
                continue
            res = {"step_id": f"b{i}", "action": a.action, "target": a.thought[:120], "status": "ok",
                   "used": "llm_recovery", "duration_ms": 0}
            if a.action == "done":
                if a.data:
                    collected.extend(a.data)
                res["duration_ms"] = int((time.time() - st) * 1000)
                ctx.emit("step_end", {"result": res}, branch_id="baseline")
                break
            if a.action == "goto" and a.url:
                if safety.is_blocked_domain(ctx, a.url):
                    history.append(f"goto {a.url}: blocked")
                else:
                    try:
                        await page.goto(a.url, timeout=30000)
                    except Exception as e:
                        history.append(f"goto failed {str(e)[:80]}")
                    await wait_settled(page)
            elif a.action in ("click", "type") and a.x_frac is not None and a.y_frac is not None:
                x, y = a.x_frac * shot.width, a.y_frac * shot.height
                if safety.PAY_WORDS.search(a.thought or "") and a.action == "click":
                    safety.payment_stop(ctx, page.url, "baseline", "Baseline tried a payment-like click.")
                    status = "stopped"
                    break
                ctx.emit("action", {"action": a.action, "box": {"x": x - 6, "y": y - 6, "w": 12, "h": 12,
                                                                "confidence": 0}, "used": "llm",
                                    "screenshot": shot.path}, branch_id="baseline")
                if a.action == "click":
                    await click_at(page, x, y)
                else:
                    await type_at(page, x, y, a.text or "")
                await wait_settled(page, 5000)
            elif a.action == "press":
                await page.keyboard.press(a.key or "Enter")
                await wait_settled(page, 5000)
            elif a.action == "scroll":
                await scroll(page, a.direction or "down")
            elif a.action == "extract" and a.data:
                for d in a.data:
                    d.setdefault("source_url", page.url)
                collected.extend(a.data)
                ctx.emit("partial", {"items": a.data, "goal": goal}, branch_id="baseline")
            elif a.action == "need_user":
                await safety.wait_for_user(ctx, page, "baseline", PageState.BOT_CHECK, a.thought or "needs the user")
            history.append(f"{a.action} {a.url or a.text or a.key or ''} ({a.thought[:80]})")
            ctx.metrics.add_step("llm")
            res["duration_ms"] = int((time.time() - st) * 1000)
            ctx.emit("step_end", {"result": res}, branch_id="baseline")
            ctx.emit_metrics()
        else:
            status = "partial"
    finally:
        br = BranchResult(branch_id="baseline", goal=goal, status=status, extracted=collected,
                          final_url=page.url, duration_ms=int((time.time() - t0) * 1000))
        ctx.emit("branch_end", {"result": br.model_dump(exclude={"steps"})}, branch_id="baseline")
        await bctx.close()
    return await synthesize(ctx, goal, [br])
