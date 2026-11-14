"""Currency normalization as an agent feature.

Websites often show prices in the visitor's local currency. Instead of trusting the LLM to
convert (or worse, relabel), Blink opens an exchange-rate page in its own tab (executed by Jev,
like any branch), reads the rate, and converts prices in code.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from .config import DATA_DIR
from .models import Branch, BranchResult, Step

# Wise covers every currency (x-rates has no JOD, Google search shows a bot check to automation)
FX_URL = "https://wise.com/us/currency-converter/{fl}-to-{tl}-rate?amount=1"
PRICE_KEYS = ("price", "price_per_night", "average_cost", "cost", "amount", "total", "value", "price_low", "price_high")
_ISO = re.compile(r"^[A-Z]{3}$")


_CACHE = DATA_DIR / "fx_cache.json"
CACHE_TTL_S = 6 * 3600


def cached_rate(frm: str, to: str) -> float | None:
    try:
        d = json.loads(_CACHE.read_text(encoding="utf-8")).get(f"{frm}->{to}")
    except Exception:
        return None
    if d and time.time() - d["ts"] < CACHE_TTL_S:
        return float(d["rate"])
    return None


def save_rate(frm: str, to: str, rate: float) -> None:
    try:
        data = json.loads(_CACHE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    data[f"{frm}->{to}"] = {"rate": rate, "ts": time.time()}
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE.write_text(json.dumps(data), encoding="utf-8")


def fx_branch(frm: str, to: str) -> Branch:
    return Branch(id=f"fx_{frm}_{to}".lower(), goal=f"Exchange rate from {frm} to {to}",
                  start_url=FX_URL.format(fl=frm.lower(), tl=to.lower()),
                  steps=[Step(id="s1", action="extract",
                              target=f"the conversion result showing how much 1 {frm} is in {to}",
                              extract_schema={"from": "string", "to": "string", "rate": "number"})])


def currencies_in(items: list[dict[str, Any]]) -> set[str]:
    out = set()
    for it in items:
        if isinstance(it, dict):
            c = str(it.get("currency") or "").upper().strip()
            if _ISO.match(c):
                out.add(c)
    return out


def rate_from(result: BranchResult) -> float | None:
    for it in result.extracted:
        if not isinstance(it, dict):
            continue
        for k in ("rate", "value", "price", "amount"):
            try:
                v = float(str(it.get(k)).replace(",", ""))
            except (TypeError, ValueError):
                continue
            if v > 0:
                return v
    return None


def convert_items(results: list[BranchResult], to_usd: dict[str, float]) -> None:
    """Add <key>_usd fields next to every price in a non-USD currency we have a rate for."""
    for r in results:
        for it in r.extracted:
            if not isinstance(it, dict):
                continue
            cur = str(it.get("currency") or "").upper()
            rate = to_usd.get(cur)
            if not rate or cur == "USD":
                continue
            for k in list(it.keys()):
                if k in PRICE_KEYS or k.startswith("price"):
                    try:
                        v = float(str(it[k]).replace(",", ""))
                    except (TypeError, ValueError):
                        continue
                    it[f"{k}_usd"] = round(v * rate, 2)
            it["fx_rate_to_usd"] = rate
