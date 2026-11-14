"""Crop-then-read extraction: Jev boxes the region, the LLM reads only that crop (+ a short text snippet)."""
from __future__ import annotations

import json
from typing import Any

from playwright.async_api import Page

from .clients.jev_client import Perception
from .context import RunContext
from .imaging import Shot, crop
from .models import Step
from .prompts import load_prompt

_REGION_TEXT_JS = r"""
([x, y, w, h]) => {
  const out = new Set();
  const step = 24;
  for (let yy = y; yy < y + h; yy += step) {
    for (let xx = x; xx < x + w; xx += step) {
      const el = document.elementFromPoint(xx, yy);
      if (el && el.innerText) out.add(el.innerText.trim().slice(0, 200));
      if (out.size > 120) break;
    }
  }
  return [...out].join('\n').slice(0, 5000);
}
"""


async def _visible_text(page: Page, box) -> str:
    try:
        if box is not None:
            return await page.evaluate(_REGION_TEXT_JS, [box.x, box.y, box.w, box.h])
        return (await page.evaluate("() => document.body.innerText"))[:12000]
    except Exception:
        return ""


async def extract(ctx: RunContext, page: Page, shot: Shot, step: Step, p: Perception | None,
                  branch_goal: str) -> dict[str, Any]:
    target = step.target or "the main content with the information we need"
    box = None
    if p is not None and p.box is not None and p.target == target and p.locate_conf >= 0.5:
        box = p.box
    if box is not None:
        image = crop(shot.raw, box.x, box.y, box.w, box.h, pad=32, min_w=480, min_h=320)
        used = "jev_crop"
    else:
        image = shot.send
        used = "full_screenshot"
    region_text = await _visible_text(page, box) if box is not None else ""
    # long tables/lists continue below the fold: also give the LLM the page's text (cheap, no extra calls)
    page_text = await _visible_text(page, None)
    text = (region_text + "\n--- full page text ---\n" + page_text) if region_text else page_text
    schema = step.extract_schema or {"value": "string", "price": "number", "currency": "string"}
    user = (f"Branch goal: {branch_goal}\nWhat to extract: {target}\nPage URL: {page.url}\n"
            f"Fields per item (JSON schema-ish): {json.dumps(schema)}\n"
            f"Visible text near the region:\n---\n{text}\n---\nThe image shows the relevant region of the page.")
    data = await ctx.llm.chat_json(model=ctx.settings.llm_vision_model, system=load_prompt("extractor"), user=user,
                                   images=[image], purpose="extract", max_tokens=1200)
    if not isinstance(data, dict):
        data = {"items": data if isinstance(data, list) else []}
    data.setdefault("items", [])
    for it in data["items"]:
        if isinstance(it, dict):
            it.setdefault("source_url", page.url)
    data["region"] = used
    data["source_url"] = page.url
    return data
