"""Screenshot handling: resize for Jev limits, crop, encode."""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Any

from PIL import Image

JEV_MIN_SIDE = 280
JEV_MAX_SIDE = 1568


@dataclass
class Shot:
    """One screenshot. `raw` is the full-resolution PNG; `send` is what models receive."""

    raw: bytes
    width: int
    height: int
    send: bytes
    send_format: str  # "jpeg" | "png"
    url: str = ""
    path: str | None = None
    page: Any = field(default=None, repr=False)  # live Playwright page (used by mock/DOM helpers only)

    def data_uri(self) -> str:
        mime = "image/jpeg" if self.send_format == "jpeg" else "image/png"
        return f"data:{mime};base64,{base64.b64encode(self.send).decode()}"

    def b64(self) -> str:
        return base64.b64encode(self.send).decode()


def fit_for_jev(png: bytes, max_width: int = 1280, quality: int = 80) -> tuple[bytes, str]:
    """Resize/pad so every side is within Jev's 280..1568 px limits, encode as JPEG.

    Aspect ratio is preserved; boxes come back as fractions, so they map straight to
    the original screenshot as long as we never pad (padding only for tiny images).
    """
    img = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = img.size
    scale = min(1.0, max_width / w, JEV_MAX_SIDE / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    w, h = img.size
    if w < JEV_MIN_SIDE or h < JEV_MIN_SIDE:
        up = max(JEV_MIN_SIDE / w, JEV_MIN_SIDE / h)
        img = img.resize((int(w * up) + 1, int(h * up) + 1), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), "jpeg"


def crop(png: bytes, x: float, y: float, w: float, h: float, pad: int = 24,
         min_w: int = 320, min_h: int = 200) -> bytes:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    W, H = img.size
    cx, cy = x + w / 2, y + h / 2
    w2, h2 = max(w + 2 * pad, min_w) / 2, max(h + 2 * pad, min_h) / 2
    left, top = max(0, int(cx - w2)), max(0, int(cy - h2))
    right, bottom = min(W, int(cx + w2)), min(H, int(cy + h2))
    out = img.crop((left, top, right, bottom))
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def to_jpeg_b64(png: bytes, max_width: int = 1280) -> str:
    data, _ = fit_for_jev(png, max_width=max_width)
    return base64.b64encode(data).decode()
