"""Offline LLM: scripted answers so the whole system (UI included) runs with no API key.

Enable with LLM_PROVIDER=offline and JEV_PROVIDER=mock. It plans against the local fixture
site served by the backend at /fixture, reads prices from the visible text, and builds a table.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Callable

from ..config import get_settings


def _fixture_plan(goal: str) -> dict:
    s = get_settings()
    base = f"http://{s.host}:{s.port}/fixture"
    search = {"id": "flights", "goal": "Find round-trip flights Cairo to Tokyo", "start_url": f"{base}/index.html",
              "steps": [
                  {"id": "s1", "action": "type", "target": "Leaving from field", "value": "Cairo", "expect": "field shows 'Cairo'"},
                  {"id": "s2", "action": "type", "target": "Going to field", "value": "Tokyo", "expect": "field shows 'Tokyo'"},
                  {"id": "s3", "action": "click", "target": "Search flights button", "expect": "flight results to 'Tokyo'"},
                  {"id": "s4", "action": "extract", "target": "the flight results with prices",
                   "extract_schema": {"airline": "string", "price": "number", "currency": "string"}}]}
    direct = {"id": "flights_direct", "goal": "Flights via a direct search URL (Osaka)",
              "start_url": f"{base}/results.html?from=Cairo&to=Osaka",
              "steps": [{"id": "s1", "action": "extract", "target": "the flight results with prices",
                         "extract_schema": {"airline": "string", "price": "number", "currency": "string"}}]}
    member = {"id": "member_deals", "goal": "Check member deals (hits a bot check)", "start_url": f"{base}/botcheck.html",
              "steps": [{"id": "s1", "action": "type", "target": "Leaving from field", "value": "Cairo",
                         "expect": "field shows 'Cairo'"},
                        {"id": "s2", "action": "extract", "target": "the search form"}]}
    checkout = {"id": "checkout", "goal": "Show that Blink stops before paying", "start_url": f"{base}/results.html?from=Cairo&to=Tokyo",
                "steps": [{"id": "s1", "action": "click", "target": "the 'Select' link of the first result", "expect": "checkout page"},
                          {"id": "s2", "action": "click", "target": "Pay now button"}]}
    return {"goal": goal, "branches": [search, direct, member, checkout], "synthesis_instructions": "offline demo"}


class OfflineLLM:
    def __init__(self, on_call: Callable[[dict], None] | None = None):
        self.on_call = on_call

    async def chat_json(self, *, model: str, system: str, user: Any, images=None, schema=None,
                        purpose: str = "llm", **kw) -> Any:
        t0 = time.time()
        await asyncio.sleep(0.4)
        text = user if isinstance(user, str) else str(user)
        if purpose == "plan":
            goal = text.replace("User goal:", "").strip()
            data: Any = _fixture_plan(goal)
        elif purpose == "extract":
            items = []
            for m in re.finditer(r"([A-Z][A-Za-z ]+?) · 1 stop · ([A-Za-z]+) → ([A-Za-z]+)[\s\S]*?\$(\d+)", text):
                items.append({"airline": m.group(1).strip(), "route": f"{m.group(2)}-{m.group(3)}",
                              "price": int(m.group(4)), "currency": "USD"})
            if not items:
                items = [{"price": int(p), "currency": "USD"} for p in re.findall(r"\$(\d{2,5})", text)[:5]]
            data = {"items": items[:5], "notes": "offline extraction"}
        elif purpose == "synthesize":
            prices = sorted(int(p) for p in re.findall(r'"price": (\d+)', text))
            row = {"category": "Flights (round trip)", "low": prices[0] if prices else None,
                   "mid": prices[len(prices) // 2] if prices else None, "high": prices[-1] if prices else None,
                   "currency": "USD", "note": f"{len(prices)} offers found (offline fixture site)"}
            data = {"summary": "Offline demo: flights from Cairo start around "
                               f"${prices[0] if prices else '?'} on the fixture site. Blink stopped before payment.",
                    "table": [row], "totals": {"low": row["low"], "mid": row["mid"], "high": row["high"], "currency": "USD"},
                    "notes": ["This is the offline demo on a local test site, not real prices."], "sources": []}
        elif purpose == "recovery":
            data = {"decision": "skip", "reason": "offline mode"}
        else:
            data = {"thought": "offline", "action": "done", "data": []}
        if self.on_call:
            self.on_call({"purpose": purpose, "model": "offline", "ms": int((time.time() - t0) * 1000), "cost": 0.0,
                          "input_tokens": 0, "output_tokens": 0})
        return schema.model_validate(data) if schema else data
