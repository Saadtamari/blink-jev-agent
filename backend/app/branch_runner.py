"""Run one branch of the task graph in its own browser context."""
from __future__ import annotations

import time

from playwright.async_api import BrowserContext

from . import safety
from .browser import wait_settled
from .context import RunContext
from .models import Branch, BranchResult, StepResult
from .step_loop import Carry, run_step


async def run_branch(ctx: RunContext, bctx: BrowserContext, branch: Branch) -> BranchResult:
    t0 = time.time()
    ctx.emit("branch_start", {"branch": branch.model_dump()}, branch_id=branch.id)
    result = BranchResult(branch_id=branch.id, goal=branch.goal, status="done")
    page = await bctx.new_page()
    try:
        if safety.is_blocked_domain(ctx, branch.start_url):
            result.status = "failed"
            return result
        try:
            await page.goto(branch.start_url, timeout=int(ctx.settings.step_timeout_s * 1000))
        except Exception as e:
            ctx.emit("error", {"where": "start_url", "error": str(e)[:200]}, branch_id=branch.id)
        await wait_settled(page)

        carry: Carry | None = None
        history: list[StepResult] = []
        failures = 0
        i = 0
        while i < len(branch.steps):
            step = branch.steps[i]
            if ctx.cancelled:
                result.status = "stopped"
                break
            nxt = branch.steps[i + 1] if i + 1 < len(branch.steps) else None
            try:
                res, carry, stop = await run_step(ctx, page, branch, step, nxt, carry, history)
            except Exception as e:  # never let one step crash the run
                res = StepResult(step_id=step.id, action=step.action, target=step.target, status="failed",
                                 note=f"error: {str(e)[:200]}")
                carry, stop = None, None
            # a click opened a new tab (target=_blank, popups): follow it, like a person would
            open_pages = [p for p in bctx.pages if not p.is_closed()]
            if open_pages and open_pages[-1] is not page:
                page = open_pages[-1]
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                carry = None
                ctx.emit("log", {"followed_new_tab": page.url}, branch_id=branch.id)
            elif page.is_closed() and open_pages:
                page, carry = open_pages[-1], None
            history.append(res)
            result.steps.append(res)
            ctx.emit("step_end", {"result": res.model_dump()}, branch_id=branch.id)
            ctx.emit_metrics()
            if res.data and res.data.get("items"):
                result.extracted.extend(res.data["items"])
                ctx.emit("partial", {"items": res.data["items"], "goal": branch.goal}, branch_id=branch.id)
            if stop == "payment":
                result.status = "stopped"
                break
            if stop == "switch_site" and branch.fallback_urls:
                # this site asked for human verification: go straight to the next website and redo the branch
                blocked_url = page.url
                fb = branch.fallback_urls.pop(0)
                ctx.emit("log", {"fallback": fb, "from": blocked_url,
                                 "reason": "bot check: switching to another website"}, branch_id=branch.id)
                try:
                    await page.goto(fb, timeout=int(ctx.settings.step_timeout_s * 1000))
                except Exception as e:
                    ctx.emit("error", {"where": "fallback_url", "error": str(e)[:200]}, branch_id=branch.id)
                await wait_settled(page)
                carry, i = None, 0
                continue
            if stop in ("handoff_failed", "switch_site"):
                result.status = "waiting_user"
                break
            if res.status == "failed":
                failures += 1
                if failures >= 3:
                    result.status = "partial"
                    break
            i += 1
        wants_data = any(s.action == "extract" for s in branch.steps)
        if result.status == "done" and (failures or (wants_data and not result.extracted)):
            result.status = "partial" if (result.extracted or failures < len(branch.steps)) else "failed"
        result.final_url = page.url
    finally:
        result.duration_ms = int((time.time() - t0) * 1000)
        ctx.emit("branch_end", {"result": result.model_dump(exclude={"steps"}),
                                "steps": len(result.steps)}, branch_id=branch.id)
        try:
            await page.close()
        except Exception:
            pass
    return result
