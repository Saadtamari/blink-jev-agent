"""Playwright wrapper: one shared browser, one isolated context per branch."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .config import get_settings
from .imaging import Shot, fit_for_jev


class BrowserPool:
    def __init__(self, headless: bool | None = None):
        s = get_settings()
        self.headless = s.headless if headless is None else headless
        self.viewport = {"width": s.viewport_width, "height": s.viewport_height}
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._browser:
                return
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=self.headless,
                args=["--window-size=1400,1000"],
            )

    async def new_context(self, storage_state: str | None = None) -> BrowserContext:
        await self.start()
        assert self._browser
        ctx = await self._browser.new_context(viewport=self.viewport, locale="en-US",
                                              timezone_id="UTC", storage_state=storage_state)
        return ctx

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None


async def screenshot(page: Page, save_dir: Path | None = None, name: str | None = None,
                     max_width: int | None = None) -> Shot:
    s = get_settings()
    raw = await page.screenshot(type="png", full_page=False)
    vp = page.viewport_size or {"width": s.viewport_width, "height": s.viewport_height}
    send, fmt = fit_for_jev(raw, max_width=max_width or s.screenshot_max_width)
    path = None
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{name or int(time.time() * 1000)}.jpg"
        (save_dir / fname).write_bytes(send)
        path = str(save_dir / fname)
    return Shot(raw=raw, width=vp["width"], height=vp["height"], send=send, send_format=fmt,
                url=page.url, path=path, page=page)


async def wait_settled(page: Page, timeout_ms: int = 8000) -> None:
    """Wait for the page to be reasonably settled without hanging on long-polling sites."""
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    except Exception:
        pass
    try:
        await page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 2500))
    except Exception:
        pass


async def click_at(page: Page, x: float, y: float) -> None:
    await page.mouse.move(x, y)
    await page.mouse.click(x, y)


async def type_at(page: Page, x: float, y: float, text: str, clear: bool = True) -> None:
    await click_at(page, x, y)
    if clear:
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Delete")
    await page.keyboard.type(text, delay=15)


async def scroll(page: Page, direction: str = "down", amount: int = 700) -> None:
    dy = amount if direction != "up" else -amount
    await page.mouse.wheel(0, dy)
    await asyncio.sleep(0.4)
