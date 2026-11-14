"""DOM fast path: resolve obvious targets from the page's own elements with zero model calls.

We collect visible interactive elements (text, aria-label, placeholder, label, title, value)
and score them against the step's target description. Only a confident, unambiguous match
is used; otherwise we fall through to Jev.
"""
from __future__ import annotations

import re

from playwright.async_api import Page

from .models import Box

_COLLECT_JS = r"""
() => {
  const sel = 'a,button,input,select,textarea,summary,[role=button],[role=link],[role=combobox],[role=searchbox],[role=textbox],[role=tab],[role=option],[role=menuitem],[contenteditable=true]';
  const out = [];
  const vw = window.innerWidth, vh = window.innerHeight;
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    if (r.bottom < 0 || r.right < 0 || r.top > vh || r.left > vw) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) < 0.1) continue;
    const cx = Math.min(Math.max(r.left + r.width / 2, 0), vw - 1), cy = Math.min(Math.max(r.top + r.height / 2, 0), vh - 1);
    const top = document.elementFromPoint(cx, cy);
    const covered = top && top !== el && !el.contains(top) && !top.contains(el);
    let label = '';
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) label = l.innerText; }
    if (!label && el.closest('label')) label = el.closest('label').innerText;
    const tag = el.tagName.toLowerCase();
    out.push({
      tag, type: (el.getAttribute('type') || '').toLowerCase(), role: el.getAttribute('role') || '',
      text: (el.innerText || '').trim().slice(0, 120),
      aria: el.getAttribute('aria-label') || '', placeholder: el.getAttribute('placeholder') || '',
      title: el.getAttribute('title') || '', name: el.getAttribute('name') || '',
      value: (tag === 'input' && ['submit','button'].includes((el.type||''))) ? (el.value || '') : '',
      label: (label || '').trim().slice(0, 120), covered,
      x: r.left, y: r.top, w: r.width, h: r.height,
    });
  }
  return out;
}
"""

_STOP = {
    "the", "a", "an", "of", "to", "for", "in", "on", "at", "and", "or", "with", "this", "that",
    "field", "button", "input", "box", "link", "element", "area", "page", "text", "click", "icon",
    "dropdown", "form", "main",
}
_INPUT_WORDS = {"field", "input", "box", "textbox", "search box", "where", "type"}
_BUTTON_WORDS = {"button", "btn"}
_LINK_WORDS = {"link"}


def _tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in _STOP and len(t) > 1]


def score_element(target: str, el: dict) -> float:
    tt = _tokens(target)
    if not tt:
        return 0.0
    hay = " ".join(str(el.get(k, "")) for k in ("text", "aria", "placeholder", "title", "label", "value", "name"))
    ht = set(_tokens(hay))
    if not ht:
        return 0.0
    hit = sum(1 for t in tt if t in ht or any(h.startswith(t) or t.startswith(h) for h in ht if len(h) > 3))
    score = hit / len(tt)
    tl = target.lower()
    tag, typ, role = el.get("tag"), el.get("type"), el.get("role")
    is_input = tag in ("input", "textarea", "select") and typ not in ("submit", "button") or role in ("combobox", "searchbox", "textbox")
    is_button = tag == "button" or role == "button" or typ in ("submit", "button")
    is_link = tag == "a" or role == "link"
    if any(w in tl for w in _INPUT_WORDS) and is_input:
        score += 0.15
    if any(w in tl for w in _BUTTON_WORDS) and is_button:
        score += 0.15
    if any(w in tl for w in _LINK_WORDS) and is_link:
        score += 0.1
    if any(w in tl for w in _INPUT_WORDS) and not is_input and "button" not in tl:
        score -= 0.25
    # short, exact labels are more trustworthy than long paragraphs that happen to contain the words
    if len(hay) > 200:
        score -= 0.2
    if el.get("covered"):
        score -= 0.5
    return round(score, 3)


async def collect(page: Page) -> list[dict]:
    try:
        return await page.evaluate(_COLLECT_JS)
    except Exception:
        return []


async def resolve(page: Page, target: str, min_score: float = 0.9, margin: float = 0.25) -> Box | None:
    """Return a box only for a confident, unique match."""
    els = await collect(page)
    if not els:
        return None
    scored = sorted(((score_element(target, e), e) for e in els), key=lambda p: p[0], reverse=True)
    best_s, best = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0.0
    if best_s < min_score or best_s - second < margin:
        return None
    return Box(x=best["x"], y=best["y"], w=best["w"], h=best["h"], confidence=min(1.0, best_s))


async def best_match(page: Page, target: str) -> tuple[Box | None, float]:
    """Lenient best match (used by the mock Jev)."""
    els = await collect(page)
    if not els:
        return None, 0.0
    s, e = max(((score_element(target, e), e) for e in els), key=lambda p: p[0])
    if s <= 0:
        return None, 0.0
    return Box(x=e["x"], y=e["y"], w=e["w"], h=e["h"], confidence=min(1.0, s)), min(1.0, s)


async def element_text_at(page: Page, x: float, y: float) -> str:
    try:
        return await page.evaluate(
            """([x, y]) => { const el = document.elementFromPoint(x, y); if (!el) return '';
                const t = el.closest('a,button,input,select,textarea,label,[role]') || el;
                return [t.innerText, t.getAttribute('aria-label'), t.getAttribute('placeholder'),
                        t.getAttribute('title'), t.getAttribute('name'), t.value].filter(Boolean).join(' ').slice(0, 300); }""",
            [x, y])
    except Exception:
        return ""


def text_matches_target(text: str, target: str) -> float:
    tt = _tokens(target)
    if not tt or not text:
        return 0.0
    ht = set(_tokens(text))
    return sum(1 for t in tt if t in ht) / len(tt)
