import functools
import http.server
import socketserver
import sys
import threading
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.browser import BrowserPool  # noqa: E402
from app.context import build_context  # noqa: E402
from app.events import RunEvents  # noqa: E402
from app.site_memory import SiteMemory  # noqa: E402

FIXTURE_DIR = Path(__file__).parent / "fixture_site"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="session")
def fixture_url():
    handler = functools.partial(_Quiet, directory=str(FIXTURE_DIR))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()


class FakeLLM:
    """Stands in for the LLM in tests: returns canned JSON per purpose."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    async def chat_json(self, *, model, system, user, images=None, schema=None, purpose="llm", **kw):
        self.calls.append(purpose)
        data = self.responses.get(purpose, {"items": []})
        if callable(data):
            data = data(user)
        return schema.model_validate(data) if schema else data


@pytest_asyncio.fixture
async def pool():
    p = BrowserPool(headless=True)
    await p.start()
    yield p
    await p.close()


@pytest.fixture
def make_ctx(tmp_path):
    def _make(**kw):
        run_id = "test_" + uuid.uuid4().hex[:8]
        ev = RunEvents(run_id)
        ctx = build_context(run_id, ev, jev_provider="mock", memory=SiteMemory(tmp_path / "mem.sqlite"))
        ctx.llm = FakeLLM(kw.pop("llm_responses", None))
        ctx.settings = ctx.settings.model_copy(update={"handoff_timeout_s": kw.pop("handoff_timeout_s", 20)})
        for k, v in kw.items():
            setattr(ctx, k, v)
        return ctx
    return _make
