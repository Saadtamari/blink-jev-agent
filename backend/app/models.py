from __future__ import annotations

import time
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Step(BaseModel):
    id: str
    action: Literal["goto", "click", "type", "select", "press", "scroll", "wait", "extract"]
    target: str | None = None  # what a human sees on screen: "departure city field"
    value: str | None = None  # text to type / option / key / url
    expect: str | None = None  # expected state after the step
    extract_schema: dict[str, Any] | None = None


class Branch(BaseModel):
    id: str
    goal: str
    start_url: str
    steps: list[Step]


class TaskGraph(BaseModel):
    goal: str
    branches: list[Branch]
    synthesis_instructions: str = ""
    home_currency: str | None = None  # e.g. "EGP" for a traveller from Cairo: totals are also shown in it


class PageState(str, Enum):
    LOADING = "loading"
    READY = "ready"
    RESULTS = "results"
    COOKIE_POPUP = "cookie_popup"
    MODAL = "modal"
    ERROR = "error"
    BOT_CHECK = "bot_check"
    LOGIN = "login"
    PAYMENT = "payment"


PAGE_STATE_CRITERIA: dict[str, str] = {
    "loading": "The page is blank or still loading (spinner, skeleton placeholders, empty white page).",
    "ready": "A normal web page is shown and can be used (forms, menus, content).",
    "results": "A list of search results, listings, offers or prices is shown.",
    "cookie_popup": "A cookie, consent or privacy banner or dialog is shown over the page.",
    "modal": "Another popup covers the page: newsletter, sign-up prompt, app download, location or language dialog.",
    "error": "An error page: not found, server error, 'something went wrong', access denied.",
    "bot_check": "A CAPTCHA or bot check: 'verify you are human', 'press and hold', puzzle, checkbox challenge.",
    "login": "The page requires signing in or creating an account before continuing.",
    "payment": "A checkout or payment page asking for card, billing or payment details.",
}

HANDOFF_STATES = {PageState.BOT_CHECK, PageState.LOGIN}


class Box(BaseModel):
    """Bounding box in real page (viewport) pixels."""

    x: float
    y: float
    w: float
    h: float
    confidence: float = 0.0

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


ResolvedBy = Literal["dom_fastpath", "site_memory", "jev", "llm_recovery", "none"]


class StepResult(BaseModel):
    step_id: str
    action: str
    target: str | None = None
    status: Literal["ok", "retried", "recovered", "handoff", "failed", "skipped", "blocked"]
    used: ResolvedBy = "none"
    confidence: float | None = None
    duration_ms: int = 0
    screenshot_before: str | None = None
    screenshot_after: str | None = None
    box: Box | None = None
    data: dict[str, Any] | None = None
    note: str | None = None


class BranchResult(BaseModel):
    branch_id: str
    goal: str = ""
    status: Literal["done", "partial", "failed", "waiting_user", "stopped"]
    steps: list[StepResult] = Field(default_factory=list)
    extracted: list[dict[str, Any]] = Field(default_factory=list)
    final_url: str | None = None
    duration_ms: int = 0


class CostRow(BaseModel):
    category: str
    low: float | None = None
    mid: float | None = None
    high: float | None = None
    currency: str = "USD"
    source_url: str | None = None
    note: str | None = None


class FinalAnswer(BaseModel):
    summary: str
    table: list[CostRow] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


EventType = Literal[
    "run_start", "plan", "plan_add", "branch_start", "step_start", "jev_call", "llm_call", "action",
    "step_end", "handoff", "handoff_resolved", "branch_end", "partial", "final",
    "metrics", "error", "screenshot", "run_end", "log",
]


class Event(BaseModel):
    run_id: str
    ts: float = Field(default_factory=time.time)
    type: EventType
    agent: Literal["blink", "baseline"] = "blink"
    branch_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RunRequest(BaseModel):
    goal: str
    mode: Literal["blink", "baseline", "race"] = "blink"
