"""Site memory: remember where targets were on each site so repeat runs skip model calls.

Key: (domain, normalized target, viewport). A remembered box is always verified after acting;
a failed verify deletes the entry.
"""
from __future__ import annotations

import re
import sqlite3
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from .config import DATA_DIR
from .models import Box


def _norm(target: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", target.lower()))


def domain_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


class SiteMemory:
    def __init__(self, path: Path | None = None):
        self.path = path or (DATA_DIR / "site_memory.sqlite")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS memory (domain TEXT, path TEXT, target TEXT, vw INT, vh INT,"
            " x REAL, y REAL, w REAL, h REAL, hits INT DEFAULT 0, updated REAL,"
            " PRIMARY KEY (domain, path, target, vw, vh))")
        self._db.commit()

    @staticmethod
    def _path_key(url: str) -> str:
        try:
            p = urlparse(url).path or "/"
        except Exception:
            p = "/"
        return re.sub(r"\d+", "#", p)[:120]

    def lookup(self, url: str, target: str, vw: int, vh: int) -> Box | None:
        with self._lock:
            row = self._db.execute(
                "SELECT x,y,w,h FROM memory WHERE domain=? AND path=? AND target=? AND vw=? AND vh=?",
                (domain_of(url), self._path_key(url), _norm(target), vw, vh)).fetchone()
            if not row:
                return None
            self._db.execute(
                "UPDATE memory SET hits=hits+1 WHERE domain=? AND path=? AND target=? AND vw=? AND vh=?",
                (domain_of(url), self._path_key(url), _norm(target), vw, vh))
            self._db.commit()
        return Box(x=row[0], y=row[1], w=row[2], h=row[3], confidence=0.9)

    def save(self, url: str, target: str, vw: int, vh: int, box: Box) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO memory (domain,path,target,vw,vh,x,y,w,h,hits,updated)"
                " VALUES (?,?,?,?,?,?,?,?,?,COALESCE((SELECT hits FROM memory WHERE domain=? AND path=?"
                " AND target=? AND vw=? AND vh=?),0),?)",
                (domain_of(url), self._path_key(url), _norm(target), vw, vh, box.x, box.y, box.w, box.h,
                 domain_of(url), self._path_key(url), _norm(target), vw, vh, time.time()))
            self._db.commit()

    def forget(self, url: str, target: str, vw: int, vh: int) -> None:
        with self._lock:
            self._db.execute("DELETE FROM memory WHERE domain=? AND path=? AND target=? AND vw=? AND vh=?",
                             (domain_of(url), self._path_key(url), _norm(target), vw, vh))
            self._db.commit()

    def stats(self) -> dict:
        with self._lock:
            n, hits = self._db.execute("SELECT COUNT(*), COALESCE(SUM(hits),0) FROM memory").fetchone()
        return {"entries": n, "hits": hits}

    def clear(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM memory")
            self._db.commit()
