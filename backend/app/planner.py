"""LLM planner: goal -> task graph of independent, parallel branches. Plans are cached per goal."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re

from .config import DATA_DIR
from .context import RunContext
from .models import TaskGraph
from .prompts import load_prompt

_CACHE = DATA_DIR / "plan_cache.json"


def _key(goal: str) -> str:
    # include the planner prompt + site list + model, so editing them invalidates old cached plans
    from .config import get_settings
    version = load_prompt("planner") + load_prompt("sites") + get_settings().llm_planner_model
    norm = " ".join(re.findall(r"\w+", goal.lower()))
    return hashlib.sha1((norm + "|" + version).encode()).hexdigest()[:16]


def _load_cache() -> dict:
    try:
        return json.loads(_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sanitize(graph: TaskGraph, max_branches: int) -> TaskGraph:
    graph.branches = graph.branches[:max_branches]
    seen = set()
    for b in graph.branches:
        b.id = re.sub(r"[^a-z0-9_]+", "_", b.id.lower()).strip("_") or "branch"
        while b.id in seen:
            b.id += "_2"
        seen.add(b.id)
        b.steps = b.steps[:8]
        for i, s in enumerate(b.steps):
            s.id = s.id or f"s{i + 1}"
    return graph


async def plan(ctx: RunContext, goal: str, use_cache: bool = True) -> TaskGraph:
    if ctx.settings.llm_provider == "offline":
        use_cache = False  # never mix scripted offline plans into the real cache
    cache = _load_cache() if use_cache else {}
    k = _key(goal)
    if use_cache and k in cache:
        g = TaskGraph.model_validate(cache[k])
        ctx.emit("log", {"plan_cache": "hit"})
        return g
    system = (load_prompt("planner")
              .replace("{today}", dt.date.today().isoformat())
              .replace("{sites}", load_prompt("sites")))
    graph = await ctx.llm.chat_json(model=ctx.settings.llm_planner_model, system=system, user=f"User goal: {goal}",
                                    schema=TaskGraph, purpose="plan", max_tokens=3000)
    graph = _sanitize(graph, ctx.settings.max_parallel_branches)
    graph.goal = goal
    if use_cache:
        cache[k] = graph.model_dump()
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return graph
