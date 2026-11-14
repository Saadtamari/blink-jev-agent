"""Start the Blink API.  Usage:  .venv/Scripts/python serve.py   (no auto-reload: Playwright needs
the Proactor event loop on Windows, which uvicorn's reloader would replace)."""
import asyncio
import sys

import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    s = get_settings()
    server = uvicorn.Server(uvicorn.Config("app.main:app", host=s.host, port=s.port, log_level="info"))
    asyncio.run(server.serve())
