"""Jev (TypeSafe) adapter.

Jev answers *typed* questions about a screenshot with probabilities:
  - choice: which page state is this?           -> label + probability map
  - box:    where is <target>?                  -> bounding box (fractions) + confidence
  - noul:   is <statement> true?                -> probability of yes

Speed trick ("fused perception"): one request asks page state + target visible + target box
+ "did the previous action work?" together, so most steps cost ONE Jev call.

Real calls go to the OpenRouter Decisions API (POST /api/alpha/decisions, model typesafe/jev-1.14).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from ..config import get_settings
from ..imaging import Shot
from ..models import PAGE_STATE_CRITERIA, Box, PageState


class JevError(RuntimeError):
    pass


@dataclass
class Perception:
    state: PageState = PageState.READY
    state_probs: dict[str, float] = field(default_factory=dict)
    box: Box | None = None
    target: str | None = None
    target_visible: float | None = None  # P(target is visible)
    expect: str | None = None
    expect_met: float | None = None  # P(expected outcome happened)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def state_conf(self) -> float:
        return float(self.state_probs.get(self.state.value, 0.0))

    @property
    def locate_conf(self) -> float:
        """Combined confidence that the box is the real target.

        Measured on real Jev 1.14 (scripts/jev_box_probe.py): boxes hit the right element 8/8 times while
        Box confidence ranged 0.41-0.94, i.e. Box confidence reflects box tightness, not correctness.
        So the companion noul ("is <target> visible?") is the main signal; a very low Box confidence
        only lowers it.
        """
        if self.box is None:
            return 0.0
        vis = self.target_visible if self.target_visible is not None else 0.0
        bc = self.box.confidence or 0.0
        return round(vis if bc >= 0.3 else vis * 0.7, 3)


class JevBase:
    name = "jev"

    def __init__(self, on_call: Callable[[dict], None] | None = None):
        self.on_call = on_call

    # ---- to implement -------------------------------------------------------------
    async def ask(self, shot: Shot | None, context: str, questions: dict[str, dict],
                  purpose: str = "jev") -> dict[str, Any]:
        raise NotImplementedError

    # ---- high-level helpers ---------------------------------------------------------
    async def perceive(self, shot: Shot, context: str = "", target: str | None = None,
                       expect: str | None = None) -> Perception:
        qs: dict[str, dict] = {
            "page_state": {
                "type": "choice",
                "instructions": "Which best describes the state of the web page in the browser screenshot?",
                "criteria": PAGE_STATE_CRITERIA,
            }
        }
        if target:
            qs["target_visible"] = {
                "type": "noul",
                "instructions": f"Is this element visible in the browser screenshot: {target}?",
            }
            qs["target_box"] = {
                "type": "box",
                "instructions": f"In the browser screenshot, locate: {target}",
            }
        if expect:
            qs["expect_met"] = {
                "type": "noul",
                "instructions": f"Looking at the browser screenshot, is this true: {expect}?",
            }
        ans = await self.ask(shot, context, qs, purpose="perceive")
        return self._to_perception(ans, shot, target, expect)

    async def verify(self, shot: Shot, expectation: str, context: str = "") -> float:
        ans = await self.ask(shot, context, {"ok": {
            "type": "noul",
            "instructions": f"Looking at the browser screenshot, is this true: {expectation}?"}},
            purpose="verify")
        return _noul(ans.get("ok"))

    async def locate(self, shot: Shot, target: str, context: str = "") -> tuple[Box | None, float]:
        p = await self.perceive(shot, context, target=target)
        return p.box, p.locate_conf

    async def choose(self, shot: Shot, question: str, options: dict[str, str],
                     context: str = "") -> tuple[str, dict[str, float]]:
        ans = await self.ask(shot, context, {"c": {"type": "choice", "instructions": question,
                                                   "criteria": options}}, purpose="choose")
        a = ans.get("c") or {}
        return a.get("choice", ""), a.get("probabilities", {})

    # ---- parsing --------------------------------------------------------------------
    @staticmethod
    def _to_perception(ans: dict, shot: Shot, target: str | None, expect: str | None) -> Perception:
        p = Perception(target=target, expect=expect, raw=ans)
        st = ans.get("page_state") or {}
        if st.get("type") != "refusal":
            probs = {k: float(v) for k, v in (st.get("probabilities") or {}).items()}
            label = st.get("choice") or (max(probs, key=probs.get) if probs else "ready")
            try:
                p.state = PageState(label)
            except ValueError:
                p.state = PageState.READY
            p.state_probs = probs or {p.state.value: float(st.get("confidence") or 1.0)}
        if target:
            p.target_visible = _noul(ans.get("target_visible"))
            b = ans.get("target_box") or {}
            if b.get("type") != "refusal" and b.get("box"):
                p.box = box_from_fractions(b["box"], shot.width, shot.height,
                                           float(b.get("confidence") or 0.0))
        if expect:
            p.expect_met = _noul(ans.get("expect_met"))
        return p


def _noul(a: dict | None) -> float:
    if not a or a.get("type") == "refusal":
        return 0.0
    try:
        return float(a.get("noul", 0.0))
    except (TypeError, ValueError):
        return 0.0


def box_from_fractions(b: dict, width: int, height: int, confidence: float = 0.0) -> Box:
    left, right = float(b.get("left", 0)), float(b.get("right", 0))
    top, bottom = float(b.get("top", 0)), float(b.get("bottom", 0))
    left, right = sorted((max(0.0, min(1.0, left)), max(0.0, min(1.0, right))))
    top, bottom = sorted((max(0.0, min(1.0, top)), max(0.0, min(1.0, bottom))))
    return Box(x=left * width, y=top * height, w=(right - left) * width, h=(bottom - top) * height,
               confidence=confidence)


class RealJev(JevBase):
    """Jev through the OpenRouter Decisions API."""

    name = "jev"

    def __init__(self, on_call: Callable[[dict], None] | None = None, image_mode: str | None = None,
                 url: str | None = None, model: str | None = None):
        super().__init__(on_call)
        s = get_settings()
        self.url = url or s.jev_decisions_url
        self.model = model or s.jev_model
        self.image_mode = image_mode or s.jev_image_mode
        self.http = httpx.AsyncClient(timeout=60.0, headers={
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
            "X-Title": "Blink web agent",
        })

    def build_body(self, shot: Shot | None, context: str, questions: dict[str, dict]) -> dict:
        body: dict[str, Any] = {"model": self.model, "questions": questions}
        ctx = context or "A browser automation agent is looking at a web page."
        if shot is None:
            body["state"] = ctx
        elif self.image_mode == "assets":
            body["assets"] = {"screenshot": {"type": "image", "format": shot.send_format,
                                             "data_base64": shot.b64()}}
            body["state"] = {"task_context": ctx, "page_url": shot.url, "browser_screenshot": "screenshot"}
        else:
            body["state"] = [
                f"Task context: {ctx}",
                f"Page URL: {shot.url}",
                "Browser screenshot of the current viewport:",
                {"type": "image_url", "image_url": {"url": shot.data_uri()}},
            ]
        return body

    async def ask(self, shot: Shot | None, context: str, questions: dict[str, dict],
                  purpose: str = "jev") -> dict[str, Any]:
        body = self.build_body(shot, context, questions)
        t0 = time.time()
        last: Exception | None = None
        for attempt in range(3):
            try:
                r = await self.http.post(self.url, json=body)
            except httpx.HTTPError as e:
                last = e
                continue
            if r.status_code in (429, 502, 503, 524, 529) and attempt < 2:
                last = JevError(f"{r.status_code}: {r.text[:300]}")
                import asyncio
                await asyncio.sleep(0.8 * (attempt + 1))
                continue
            if r.status_code != 200:
                raise JevError(f"Jev {r.status_code}: {r.text[:500]}")
            data = r.json()
            ms = int((time.time() - t0) * 1000)
            usage = data.get("usage") or {}
            if self.on_call:
                self.on_call({"purpose": purpose, "model": data.get("model", self.model), "ms": ms,
                              "cost": float(usage.get("cost") or 0), "input_tokens": usage.get("input_tokens", 0),
                              "output_tokens": usage.get("output_tokens", 0),
                              "questions": list(questions), "answers": data.get("answers", {})})
            return data.get("answers") or {}
        raise JevError(f"Jev request failed: {last}")

    async def aclose(self) -> None:
        await self.http.aclose()


def make_jev(on_call: Callable[[dict], None] | None = None, provider: str | None = None, llm=None) -> JevBase:
    provider = provider or get_settings().jev_provider
    if provider == "mock":
        from .jev_mock import MockJev
        return MockJev(on_call)
    if provider == "llm_fallback":
        from .jev_llm_fallback import LLMFallbackJev
        return LLMFallbackJev(on_call, llm=llm)
    return RealJev(on_call)
