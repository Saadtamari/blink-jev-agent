"""Mock Jev for offline development and tests.

It "looks" at the live page DOM instead of the pixels, but returns exactly the same
typed answers as the real adapter (Perception objects), so the rest of the system
can't tell the difference.
"""
from __future__ import annotations

import re
import time

from .. import dom_fastpath
from ..imaging import Shot
from ..models import PageState
from .jev_client import JevBase, Perception

_STATE_JS = r"""
() => {
  const forced = document.body && document.body.dataset.blinkState;
  if (forced) return forced;
  const vis = (el) => { if (!el) return false; const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
                        return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden'; };
  const txt = (document.body ? document.body.innerText : '').toLowerCase();
  if (/verify you are human|i'?m not a robot|press and hold|captcha/.test(txt)) return 'bot_check';
  if (/card number|cvv|billing address|pay now/.test(txt)) return 'payment';
  if (vis(document.querySelector('[data-blink=cookie], #cookie-banner, .cookie-banner'))) return 'cookie_popup';
  if (vis(document.querySelector('[data-blink=modal], .modal-overlay'))) return 'modal';
  if (/sign in to continue|log in to continue/.test(txt)) return 'login';
  if (/404|not found|something went wrong/.test(txt) && txt.length < 400) return 'error';
  if (document.querySelectorAll('.result, [data-blink=result]').length > 0) return 'results';
  if (!txt.trim()) return 'loading';
  return 'ready';
}
"""


class MockJev(JevBase):
    name = "mock"

    def _record(self, purpose: str, t0: float) -> None:
        if self.on_call:
            self.on_call({"purpose": purpose, "model": "mock-jev", "ms": int((time.time() - t0) * 1000),
                          "cost": 0.0, "input_tokens": 0, "output_tokens": 0})

    async def _page_state(self, page) -> PageState:
        try:
            label = await page.evaluate(_STATE_JS)
            return PageState(label)
        except Exception:
            return PageState.READY

    async def _expect(self, page, expect: str) -> float:
        try:
            hay = await page.evaluate(
                "() => (document.body.innerText + ' ' + [...document.querySelectorAll('input,textarea,select')]"
                ".map(e => e.value).join(' ') + ' ' + location.href).toLowerCase()")
        except Exception:
            return 0.0
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", expect)
        if quoted:
            return 0.95 if all(q.lower() in hay for q in quoted) else 0.1
        toks = dom_fastpath._tokens(expect)
        if not toks:
            return 0.5
        frac = sum(1 for t in toks if t in hay) / len(toks)
        return 0.9 if frac >= 0.6 else 0.2

    async def perceive(self, shot: Shot, context: str = "", target: str | None = None,
                       expect: str | None = None) -> Perception:
        t0 = time.time()
        page = shot.page
        p = Perception(target=target, expect=expect)
        if page is None:
            self._record("perceive", t0)
            return p
        p.state = await self._page_state(page)
        p.state_probs = {p.state.value: 0.97}
        if target:
            box, conf = await dom_fastpath.best_match(page, target)
            p.box = box
            p.target_visible = conf
        if expect:
            p.expect_met = await self._expect(page, expect)
        self._record("perceive", t0)
        return p

    async def verify(self, shot: Shot, expectation: str, context: str = "") -> float:
        t0 = time.time()
        v = await self._expect(shot.page, expectation) if shot.page else 0.0
        self._record("verify", t0)
        return v

    async def choose(self, shot: Shot, question: str, options: dict[str, str], context: str = ""):
        t0 = time.time()
        first = next(iter(options), "")
        self._record("choose", t0)
        return first, {k: (1.0 if k == first else 0.0) for k in options}

    async def ask(self, shot, context, questions, purpose="jev"):
        raise NotImplementedError("MockJev answers via perceive/verify/choose")
