"""LLM synthesizer: branch results -> final answer. Totals and currency math are done in code."""
from __future__ import annotations

import json
from typing import Any

from .context import RunContext
from .models import BranchResult, FinalAnswer
from .prompts import load_prompt


def compute_totals(ans: FinalAnswer, rates: dict[str, Any] | None) -> None:
    """Deterministic totals: sum the rows (all must be in one currency), then convert to the home currency."""
    for r in ans.table:  # keep low <= mid <= high
        vals = sorted(v for v in (r.low, r.mid, r.high) if v is not None)
        if len(vals) == 3:
            r.low, r.mid, r.high = vals
        elif len(vals) == 2 and r.mid is None:
            r.low, r.high = vals
    rows = [r for r in ans.table if any(v is not None for v in (r.low, r.mid, r.high))]
    if not rows:
        return
    currencies = {r.currency.upper() for r in rows}
    if len(currencies) != 1:
        ans.totals = {"note": f"Rows are in different currencies ({', '.join(sorted(currencies))}); no single total."}
        return
    cur = currencies.pop()

    def pick(r, k):
        v = getattr(r, k)
        return v if v is not None else r.mid if r.mid is not None else (r.low if r.low is not None else r.high)

    totals: dict[str, Any] = {k: round(sum(pick(r, k) or 0 for r in rows), 2) for k in ("low", "mid", "high")}
    totals["currency"] = cur
    missing = [r.category for r in ans.table if r not in rows]
    if missing:
        totals["excludes"] = missing
    if rates and cur == "USD" and rates.get("usd_to_home") and rates.get("home_currency"):
        fxr = float(rates["usd_to_home"])
        totals.update({"local_currency": rates["home_currency"], "fx_rate": fxr,
                       "local_low": round(totals["low"] * fxr), "local_mid": round(totals["mid"] * fxr),
                       "local_high": round(totals["high"] * fxr),
                       "fx_note": f"1 USD = {fxr} {rates['home_currency']} (wise.com, read by Blink)"})
    ans.totals = totals
    # the totals sentence is written by code, so it always matches the table
    sym = "$" if cur == "USD" else f"{cur} "
    line = (f"Estimated total: {sym}{totals['low']:,.0f} (budget) / {sym}{totals['mid']:,.0f} (typical) / "
            f"{sym}{totals['high']:,.0f} (comfortable)")
    if totals.get("local_mid") is not None:
        line += f", about {totals['local_mid']:,.0f} {totals['local_currency']} typical"
    if totals.get("excludes"):
        line += f"; not included: {', '.join(totals['excludes'])}"
    ans.summary = f"{ans.summary.rstrip()} {line}."


async def synthesize(ctx: RunContext, goal: str, results: list[BranchResult], instructions: str = "",
                     rates: dict[str, Any] | None = None) -> FinalAnswer:
    payload = [{"branch": r.branch_id, "goal": r.goal, "status": r.status, "final_url": r.final_url,
                "data": r.extracted} for r in results if not r.branch_id.startswith("fx_")]
    user = (f"User goal: {goal}\nExtra instructions: {instructions or 'none'}\n"
            f"Exchange rates found by the agent (multiply a price by to_usd[currency] to get USD): "
            f"{json.dumps(rates or {})}\n"
            f"Branch results (JSON; fields ending in _usd are already converted to USD in code):\n"
            f"{json.dumps(payload, ensure_ascii=False)[:14000]}")
    try:
        ans = await ctx.llm.chat_json(model=ctx.settings.llm_planner_model, system=load_prompt("synthesizer"),
                                      user=user, schema=FinalAnswer, purpose="synthesize", max_tokens=2000)
    except Exception as e:
        ans = FinalAnswer(summary=f"Could not write the final answer ({str(e)[:120]}). Raw results are below.",
                          notes=[json.dumps(payload, ensure_ascii=False)[:2000]])
    compute_totals(ans, rates)
    if not ans.sources:
        ans.sources = sorted({str(i.get("source_url")) for r in results for i in r.extracted
                              if isinstance(i, dict) and i.get("source_url")})
    return ans
