"""OpenRouter LLM wrapper: strict-JSON calls with vision, validated by Pydantic, with cost tracking."""
from __future__ import annotations

import base64
import json
import re
import time
from typing import Any, Callable, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from ..config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


def _extract_json(text: str) -> Any:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
        if start < 0:
            raise
        end = max(text.rfind("}"), text.rfind("]"))
        return json.loads(text[start:end + 1])


def image_part(img: bytes, fmt: str = "jpeg") -> dict:
    b64 = base64.b64encode(img).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/{fmt};base64,{b64}"}}


class LLMClient:
    def __init__(self, on_call: Callable[[dict], None] | None = None):
        s = get_settings()
        self.settings = s
        self.client = AsyncOpenAI(
            api_key=s.openrouter_api_key or "missing-key",
            base_url=s.openrouter_base_url,
            default_headers={"X-Title": "Blink web agent"},
            timeout=90.0,
        )
        self.on_call = on_call

    async def chat_json(self, *, model: str, system: str, user: str | list[dict],
                        images: list[bytes] | None = None, schema: type[T] | None = None,
                        purpose: str = "llm", max_tokens: int = 2500, temperature: float = 0.2) -> Any:
        content: list[dict] = []
        if isinstance(user, str):
            content.append({"type": "text", "text": user})
        else:
            content.extend(user)
        for img in images or []:
            content.append(image_part(img))
        messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": content}]

        last_err: str | None = None
        for attempt in range(2):
            if last_err:
                messages.append({"role": "user", "content":
                                 f"Your previous reply was invalid: {last_err}. Reply again with ONLY valid JSON."})
            t0 = time.time()
            try:
                resp = await self.client.chat.completions.create(
                    model=model, messages=messages, max_tokens=max_tokens, temperature=temperature,
                    response_format={"type": "json_object"},
                    extra_body={"usage": {"include": True}},
                )
            except Exception as e:  # network / provider error
                raise LLMError(f"{purpose}: {e}") from e
            ms = int((time.time() - t0) * 1000)
            usage = resp.usage
            cost = 0.0
            tin = tout = 0
            if usage is not None:
                tin, tout = usage.prompt_tokens or 0, usage.completion_tokens or 0
                extra = getattr(usage, "model_extra", None) or {}
                cost = float(extra.get("cost") or getattr(usage, "cost", 0) or 0)
            text = (resp.choices[0].message.content or "") if resp.choices else ""
            if self.on_call:
                self.on_call({"purpose": purpose, "model": model, "ms": ms, "cost": cost,
                              "input_tokens": tin, "output_tokens": tout, "attempt": attempt})
            try:
                data = _extract_json(text)
                if schema is not None:
                    return schema.model_validate(data)
                return data
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                last_err = str(e)[:600]
                messages.append({"role": "assistant", "content": text[:4000]})
        raise LLMError(f"{purpose}: invalid JSON after retry: {last_err}")
