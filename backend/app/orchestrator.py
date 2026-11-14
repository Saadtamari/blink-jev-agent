"""Run manager: plans the goal, runs branches in parallel, synthesizes, and supports race / replay."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field

from . import planner
from .baseline.llm_only_agent import run_baseline
from .branch_runner import run_branch
from .browser import BrowserPool
from .config import DATA_DIR, get_settings
from .context import RunContext, build_context
from .events import RunEvents, load_events
from .models import BranchResult, FinalAnswer
from .site_memory import SiteMemory
from .synthesizer import synthesize


@dataclass
class Run:
    run_id: str
    goal: str
    mode: str
    events: RunEvents
    contexts: dict[str, RunContext] = field(default_factory=dict)
    finals: dict[str, dict] = field(default_factory=dict)
    status: str = "running"
    task: asyncio.Task | None = None
    started: float = field(default_factory=time.time)


async def run_blink(ctx: RunContext, pool: BrowserPool, goal: str, use_plan_cache: bool = True) -> FinalAnswer:
    t0 = time.time()
    graph = await planner.plan(ctx, goal, use_cache=use_plan_cache)
    ctx.emit("plan", {"graph": graph.model_dump(), "plan_ms": int((time.time() - t0) * 1000)})
    sem = asyncio.Semaphore(ctx.settings.max_parallel_branches)

    async def one(branch):
        async with sem:
            bctx = await pool.new_context()
            try:
                return await run_branch(ctx, bctx, branch)
            finally:
                await bctx.close()

    results: list[BranchResult] = await asyncio.gather(*(one(b) for b in graph.branches), return_exceptions=False)
    return await synthesize(ctx, goal, results, graph.synthesis_instructions)


class RunManager:
    def __init__(self):
        self.runs: dict[str, Run] = {}
        self.pool = BrowserPool()
        self.memory = SiteMemory()

    def get(self, run_id: str) -> Run | None:
        return self.runs.get(run_id)

    def start(self, goal: str, mode: str = "blink", jev_provider: str | None = None,
              use_plan_cache: bool = True, use_site_memory: bool = True) -> Run:
        run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        events = RunEvents(run_id)
        run = Run(run_id=run_id, goal=goal, mode=mode, events=events)
        self.runs[run_id] = run
        events.emit("run_start", {"goal": goal, "mode": mode, "config": get_settings().public()})
        run.task = asyncio.create_task(self._execute(run, jev_provider, use_plan_cache, use_site_memory))
        return run

    async def _agent(self, run: Run, agent: str, jev_provider: str | None, use_plan_cache: bool,
                     use_site_memory: bool) -> None:
        ctx = build_context(run.run_id, run.events, agent=agent, jev_provider=jev_provider,
                            memory=self.memory if use_site_memory else None)
        ctx.use_site_memory = use_site_memory
        run.contexts[agent] = ctx
        try:
            if agent == "blink":
                final = await run_blink(ctx, self.pool, run.goal, use_plan_cache)
            else:
                final = await run_baseline(ctx, self.pool, run.goal)
            ctx.metrics.finished = time.time()
            run.finals[agent] = {"answer": final.model_dump(), "metrics": ctx.metrics.snapshot()}
            ctx.emit("final", run.finals[agent])
        except Exception as e:
            ctx.metrics.finished = time.time()
            ctx.emit("error", {"where": agent, "error": str(e)[:500]})
            run.finals[agent] = {"answer": None, "metrics": ctx.metrics.snapshot(), "error": str(e)[:500]}

    async def _execute(self, run: Run, jev_provider, use_plan_cache, use_site_memory) -> None:
        agents = ["blink", "baseline"] if run.mode == "race" else [run.mode]
        try:
            await asyncio.gather(*(self._agent(run, a, jev_provider, use_plan_cache, use_site_memory)
                                   for a in agents))
            run.status = "done"
        except asyncio.CancelledError:
            run.status = "cancelled"
        finally:
            run.events.emit("run_end", {"status": run.status, "finals": run.finals})
            summary = {"run_id": run.run_id, "goal": run.goal, "mode": run.mode, "status": run.status,
                       "started": run.started, "finals": run.finals}
            (run.events.dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
            run.events.close()

    def continue_branch(self, run_id: str, branch_id: str) -> bool:
        run = self.runs.get(run_id)
        if not run:
            return False
        for ctx in run.contexts.values():
            ev = ctx.continue_events.get(branch_id)
            if ev:
                ev.set()
                return True
        return False

    def cancel(self, run_id: str) -> bool:
        run = self.runs.get(run_id)
        if not run:
            return False
        for ctx in run.contexts.values():
            ctx.cancelled = True
        return True

    # ---- demo mode: replay a saved run with its original timing --------------------
    def replay(self, source_run_id: str, speed: float = 1.0) -> Run | None:
        old = load_events(source_run_id)
        if not old:
            return None
        goal = next((e["payload"].get("goal", "") for e in old if e["type"] == "run_start"), "")
        mode = next((e["payload"].get("mode", "blink") for e in old if e["type"] == "run_start"), "blink")
        run_id = "replay-" + time.strftime("%H%M%S-") + uuid.uuid4().hex[:4]
        events = RunEvents(run_id)
        run = Run(run_id=run_id, goal=goal, mode=mode, events=events)
        self.runs[run_id] = run

        async def _go():
            t_prev = old[0]["ts"]
            for e in old:
                await asyncio.sleep(max(0.0, (e["ts"] - t_prev) / max(speed, 0.1)))
                t_prev = e["ts"]
                payload = dict(e.get("payload") or {})
                if e["type"] == "run_start":
                    payload["replay_of"] = source_run_id
                events.emit(e["type"], payload, branch_id=e.get("branch_id"), agent=e.get("agent", "blink"))
                if e["type"] == "final":
                    run.finals[e.get("agent", "blink")] = payload
            run.status = "done"
            events.close()

        run.task = asyncio.create_task(_go())
        return run


def list_saved_runs(limit: int = 50) -> list[dict]:
    out = []
    root = DATA_DIR / "runs"
    if not root.exists():
        return out
    for d in sorted(root.iterdir(), reverse=True):
        f = d / "summary.json"
        if f.exists():
            try:
                s = json.loads(f.read_text(encoding="utf-8"))
                out.append({k: s.get(k) for k in ("run_id", "goal", "mode", "status", "started")})
            except Exception:
                pass
        if len(out) >= limit:
            break
    return out
