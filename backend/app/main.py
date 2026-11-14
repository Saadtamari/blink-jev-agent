"""Blink API: start runs, stream events over WebSocket, serve screenshots, benchmark results."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import BACKEND_DIR, DATA_DIR, get_settings
from .events import load_events
from .models import RunRequest
from .orchestrator import RunManager, list_saved_runs

manager: RunManager | None = None
DEMO_FILE = DATA_DIR / "demo_run.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global manager
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manager = RunManager()
    yield
    await manager.pool.close()


app = FastAPI(title="Blink", lifespan=lifespan)
s = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=[s.frontend_origin, "http://127.0.0.1:3000"],
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/fixture", StaticFiles(directory=BACKEND_DIR / "tests" / "fixture_site", html=True), name="fixture")


def _mgr() -> RunManager:
    assert manager is not None
    return manager


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/config")
async def config():
    cfg = get_settings().public()
    cfg["demo_run"] = json.loads(DEMO_FILE.read_text())["run_id"] if DEMO_FILE.exists() else None
    cfg["site_memory"] = _mgr().memory.stats()
    return cfg


class StartRun(RunRequest):
    jev_provider: str | None = None
    use_plan_cache: bool = True
    use_site_memory: bool = True


@app.post("/runs")
async def start_run(req: StartRun):
    if not req.goal.strip():
        raise HTTPException(400, "Enter a goal first.")
    m = _mgr()
    if get_settings().demo_mode and DEMO_FILE.exists():
        run = m.replay(json.loads(DEMO_FILE.read_text())["run_id"])
        if run:
            return {"run_id": run.run_id, "replay": True}
    run = m.start(req.goal, req.mode, jev_provider=req.jev_provider, use_plan_cache=req.use_plan_cache,
                  use_site_memory=req.use_site_memory)
    return {"run_id": run.run_id, "replay": False}


@app.get("/runs")
async def runs():
    return list_saved_runs()


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = _mgr().get(run_id)
    if run:
        return {"run_id": run.run_id, "goal": run.goal, "mode": run.mode, "status": run.status, "finals": run.finals}
    f = DATA_DIR / "runs" / run_id / "summary.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    raise HTTPException(404, "Run not found")


@app.get("/runs/{run_id}/events")
async def run_events(run_id: str):
    return load_events(run_id)


@app.post("/runs/{run_id}/branches/{branch_id}/continue")
async def continue_branch(run_id: str, branch_id: str):
    return {"ok": _mgr().continue_branch(run_id, branch_id)}


@app.post("/runs/{run_id}/cancel")
async def cancel(run_id: str):
    return {"ok": _mgr().cancel(run_id)}


class ReplayReq(BaseModel):
    speed: float = 1.0


@app.post("/runs/{run_id}/replay")
async def replay(run_id: str, req: ReplayReq):
    run = _mgr().replay(run_id, req.speed)
    if not run:
        raise HTTPException(404, "Run not found")
    return {"run_id": run.run_id}


@app.post("/runs/{run_id}/save_demo")
async def save_demo(run_id: str):
    if not (DATA_DIR / "runs" / run_id / "events.jsonl").exists():
        raise HTTPException(404, "Run not found")
    DEMO_FILE.write_text(json.dumps({"run_id": run_id}))
    return {"ok": True}


@app.get("/files")
async def files(path: str):
    p = Path(path).resolve()
    root = DATA_DIR.resolve()
    if root not in p.parents or not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p)


@app.get("/benchmark/results")
async def benchmark_results():
    f = DATA_DIR / "benchmark" / "results.json"
    if not f.exists():
        return {"tasks": [], "summary": None}
    return json.loads(f.read_text(encoding="utf-8"))


@app.websocket("/ws/runs/{run_id}")
async def ws_run(ws: WebSocket, run_id: str):
    await ws.accept()
    run = _mgr().get(run_id)
    try:
        if run is None:
            for e in load_events(run_id):
                await ws.send_text(json.dumps(e))
            await ws.close()
            return
        q = run.events.subscribe()
        for e in list(run.events.events):
            await ws.send_text(e.model_dump_json())
        if run.events.closed:
            await ws.close()
            return
        while True:
            ev = await q.get()
            if ev is None:
                break
            await ws.send_text(ev.model_dump_json())
        await ws.close()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if run is not None:
            try:
                run.events.unsubscribe(q)
            except Exception:
                pass
