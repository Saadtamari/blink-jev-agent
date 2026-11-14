"""LLM synthesizer: branch results -> final answer with a cost table and sources."""
from __future__ import annotations

import json

from .context import RunContext
from .models import BranchResult, FinalAnswer
from .prompts import load_prompt


async def synthesize(ctx: RunContext, goal: str, results: list[BranchResult], instructions: str = "") -> FinalAnswer:
    payload = [{"branch": r.branch_id, "goal": r.goal, "status": r.status, "final_url": r.final_url,
                "data": r.extracted} for r in results]
    user = (f"User goal: {goal}\nExtra instructions: {instructions or 'none'}\n"
            f"Branch results (JSON):\n{json.dumps(payload, ensure_ascii=False)[:14000]}")
    try:
        ans = await ctx.llm.chat_json(model=ctx.settings.llm_planner_model, system=load_prompt("synthesizer"),
                                      user=user, schema=FinalAnswer, purpose="synthesize", max_tokens=2000)
    except Exception as e:
        ans = FinalAnswer(summary=f"Could not write the final answer ({str(e)[:120]}). Raw results are below.",
                          notes=[json.dumps(payload, ensure_ascii=False)[:2000]])
    if not ans.sources:
        ans.sources = sorted({str(i.get("source_url")) for r in results for i in r.extracted
                              if isinstance(i, dict) and i.get("source_url")})
    return ans
