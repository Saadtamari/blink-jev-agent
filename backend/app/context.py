"""Everything one agent run needs, passed around explicitly."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .clients.jev_client import JevBase, make_jev
from .clients.llm_client import LLMClient
from .config import Settings, get_settings
from .events import RunEvents
from .metrics import Metrics
from .site_memory import SiteMemory


@dataclass
class RunContext:
    run_id: str
    events: RunEvents
    agent: str = "blink"  # "blink" | "baseline"
    settings: Settings = field(default_factory=get_settings)
    metrics: Metrics = field(default_factory=Metrics)
    llm: LLMClient | None = None
    jev: JevBase | None = None
    memory: SiteMemory | None = None
    use_dom_fastpath: bool = True
    use_site_memory: bool = True
    # handoff: branch_id -> asyncio.Event set when the user clicks Continue
    continue_events: dict[str, asyncio.Event] = field(default_factory=dict)
    cancelled: bool = False

    @property
    def dir(self) -> Path:
        return self.events.dir

    def emit(self, type: str, payload: dict[str, Any] | None = None, branch_id: str | None = None):
        return self.events.emit(type, payload, branch_id=branch_id, agent=self.agent)

    def emit_metrics(self) -> None:
        self.emit("metrics", self.metrics.snapshot())


def build_context(run_id: str, events: RunEvents, agent: str = "blink", jev_provider: str | None = None,
                  memory: SiteMemory | None = None) -> RunContext:
    ctx = RunContext(run_id=run_id, events=events, agent=agent)

    def on_llm(info: dict) -> None:
        ctx.metrics.add_llm(info.get("cost", 0), info.get("ms", 0), info.get("input_tokens", 0),
                            info.get("output_tokens", 0))
        ctx.emit("llm_call", info)
        ctx.emit_metrics()

    def on_jev(info: dict) -> None:
        ctx.metrics.add_jev(info.get("cost", 0), info.get("ms", 0), info.get("input_tokens", 0),
                            info.get("output_tokens", 0))
        ctx.emit("jev_call", info)
        ctx.emit_metrics()

    if ctx.settings.llm_provider == "offline":
        from .clients.offline_llm import OfflineLLM
        ctx.llm = OfflineLLM(on_call=on_llm)  # type: ignore[assignment]
    else:
        ctx.llm = LLMClient(on_call=on_llm)
    ctx.jev = make_jev(on_call=on_jev, provider=jev_provider, llm=ctx.llm)
    ctx.memory = memory
    return ctx
