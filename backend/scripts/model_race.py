"""Time candidate LLMs on Blink's planner prompt (valid TaskGraph + latency + cost).

Usage (from backend/): .venv/Scripts/python scripts/model_race.py model1 model2 ...
"""
import asyncio
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.llm_client import LLMClient  # noqa: E402
from app.models import TaskGraph  # noqa: E402
from app.prompts import load_prompt  # noqa: E402

GOAL = "I want to go to Japan for 7 days in March from Cairo. How much will it cost?"


async def one(model: str):
    info = {}
    llm = LLMClient(on_call=lambda i: info.update(i))
    system = load_prompt("planner").replace("{today}", dt.date.today().isoformat()).replace("{sites}", load_prompt("sites"))
    try:
        g = await llm.chat_json(model=model, system=system, user=f"User goal: {GOAL}", schema=TaskGraph, purpose="plan",
                                max_tokens=3000)
        steps = sum(len(b.steps) for b in g.branches)
        print(f"{model:40} {info['ms']:6} ms  ${info['cost']:.4f}  branches={len(g.branches)} steps={steps} "
              f"urls={[b.start_url[:60] for b in g.branches]}")
    except Exception as e:
        print(f"{model:40} FAILED {str(e)[:200]}")


async def main():
    await asyncio.gather(*(one(m) for m in sys.argv[1:]))


asyncio.run(main())
