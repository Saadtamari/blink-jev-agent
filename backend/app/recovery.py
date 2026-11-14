"""LLM recovery: when Jev is unsure or a step keeps failing, a vision LLM decides what to do."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .context import RunContext
from .imaging import Shot
from .models import Step, StepResult
from .prompts import load_prompt


class RecoveryDecision(BaseModel):
    decision: Literal["retarget", "click_xy", "goto", "scroll", "skip", "wait"]
    target: str | None = None  # new target description for "retarget"
    x_frac: float | None = None  # for click_xy, fractions of the screenshot
    y_frac: float | None = None
    url: str | None = None
    direction: Literal["up", "down"] | None = None
    reason: str = ""


async def replan_step(ctx: RunContext, shot: Shot, step: Step, branch_goal: str,
                      history: list[StepResult], problem: str) -> RecoveryDecision:
    hist = "\n".join(f"- {h.action} '{h.target}': {h.status} ({h.note or ''})" for h in history[-3:]) or "- none"
    user = (f"Branch goal: {branch_goal}\nCurrent URL: {shot.url}\n"
            f"Failing step: action={step.action} target={step.target!r} value={step.value!r} expect={step.expect!r}\n"
            f"Problem: {problem}\nRecent steps:\n{hist}\n\nThe screenshot of the current page is attached.")
    return await ctx.llm.chat_json(model=ctx.settings.llm_fast_model, system=load_prompt("recovery"), user=user,
                                   images=[shot.send], schema=RecoveryDecision, purpose="recovery",
                                   max_tokens=400)
