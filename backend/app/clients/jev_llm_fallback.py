"""Backup "Jev" built on a vision LLM via OpenRouter.

Used only if the real Jev endpoint is unavailable. It answers the same typed questions
and returns answers in Jev's response format, so nothing else changes. The UI labels it.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from ..config import get_settings
from ..imaging import Shot
from .jev_client import JevBase
from .llm_client import LLMClient

_SYSTEM = """You imitate a typed decision model that looks at a browser screenshot.
Answer every question in the requested JSON format only.
- choice: {"type":"choice","choice":"<label>","probabilities":{"<label>":p,...}}  (probabilities sum to 1)
- noul:   {"type":"noul","noul":p}  where p = probability the statement is true
- box:    {"type":"box","box":{"left":f,"top":f,"right":f,"bottom":f},"confidence":p}
          coordinates are fractions (0..1) of the image width/height
Reply with {"answers": {"<question name>": <answer>, ...}}"""


class LLMFallbackJev(JevBase):
    name = "llm_fallback"

    def __init__(self, on_call: Callable[[dict], None] | None = None, llm: LLMClient | None = None):
        super().__init__(on_call)
        self.llm = llm or LLMClient()

    async def ask(self, shot: Shot | None, context: str, questions: dict[str, dict],
                  purpose: str = "jev") -> dict[str, Any]:
        user = (f"Context: {context or 'browser automation'}\nPage URL: {shot.url if shot else ''}\n"
                f"Questions:\n{json.dumps(questions, indent=1)}")
        data = await self.llm.chat_json(model=get_settings().llm_vision_model, system=_SYSTEM, user=user,
                                        images=[shot.send] if shot else None, purpose=f"jev_fallback:{purpose}",
                                        max_tokens=800, temperature=0.0)
        answers = data.get("answers", data) if isinstance(data, dict) else {}
        for k, q in questions.items():
            answers.setdefault(k, {"type": "refusal"})
            answers[k].setdefault("type", q["type"])
        return answers
