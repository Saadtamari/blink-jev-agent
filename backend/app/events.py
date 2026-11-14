"""Per-run event bus: every event is stored (for replay) and fanned out to live subscribers."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .models import Event


class RunEvents:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: list[Event] = []
        self._subs: set[asyncio.Queue] = set()
        self.dir: Path = DATA_DIR / "runs" / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._file = (self.dir / "events.jsonl").open("a", encoding="utf-8")
        self.closed = False

    def emit(self, type: str, payload: dict[str, Any] | None = None, branch_id: str | None = None,
             agent: str = "blink") -> Event:
        ev = Event(run_id=self.run_id, type=type, payload=payload or {}, branch_id=branch_id, agent=agent)
        self.events.append(ev)
        line = ev.model_dump_json()
        try:
            self._file.write(line + "\n")
            self._file.flush()
        except ValueError:
            pass
        for q in list(self._subs):
            q.put_nowait(ev)
        return ev

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def close(self) -> None:
        self.closed = True
        for q in list(self._subs):
            q.put_nowait(None)
        try:
            self._file.close()
        except Exception:
            pass


def load_events(run_id: str) -> list[dict]:
    path = DATA_DIR / "runs" / run_id / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out
