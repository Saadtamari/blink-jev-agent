"""Cost, call and timing counters for one agent run."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Metrics:
    started: float = field(default_factory=time.time)
    finished: float | None = None
    jev_calls: int = 0
    llm_calls: int = 0
    jev_cost: float = 0.0
    llm_cost: float = 0.0
    jev_ms: int = 0
    llm_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    steps: int = 0
    steps_by_path: dict[str, int] = field(default_factory=dict)
    handoffs: int = 0
    cache_hits: int = 0

    def add_jev(self, cost: float, ms: int, tin: int = 0, tout: int = 0) -> None:
        self.jev_calls += 1
        self.jev_cost += cost or 0.0
        self.jev_ms += ms
        self.input_tokens += tin
        self.output_tokens += tout

    def add_llm(self, cost: float, ms: int, tin: int = 0, tout: int = 0) -> None:
        self.llm_calls += 1
        self.llm_cost += cost or 0.0
        self.llm_ms += ms
        self.input_tokens += tin
        self.output_tokens += tout

    def add_step(self, used: str) -> None:
        self.steps += 1
        self.steps_by_path[used] = self.steps_by_path.get(used, 0) + 1

    @property
    def elapsed_s(self) -> float:
        return round((self.finished or time.time()) - self.started, 2)

    def snapshot(self) -> dict:
        return {
            "elapsed_s": self.elapsed_s,
            "jev_calls": self.jev_calls,
            "llm_calls": self.llm_calls,
            "jev_cost": round(self.jev_cost, 6),
            "llm_cost": round(self.llm_cost, 6),
            "total_cost": round(self.jev_cost + self.llm_cost, 6),
            "jev_ms": self.jev_ms,
            "llm_ms": self.llm_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "steps": self.steps,
            "steps_by_path": dict(self.steps_by_path),
            "handoffs": self.handoffs,
            "cache_hits": self.cache_hits,
        }
