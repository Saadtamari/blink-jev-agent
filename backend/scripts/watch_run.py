"""Start a run through the API and print a compact live log until it ends.

Usage (from backend/): .venv/Scripts/python scripts/watch_run.py "goal text" [blink|race|baseline]
"""
import asyncio
import json
import sys

import httpx
import websockets

API = "http://127.0.0.1:8000"


async def main(goal: str, mode: str):
    r = httpx.post(f"{API}/runs", json={"goal": goal, "mode": mode}, timeout=30)
    run_id = r.json()["run_id"]
    print("run", run_id, flush=True)
    async with websockets.connect(f"ws://127.0.0.1:8000/ws/runs/{run_id}", max_size=None) as ws:
        t0 = None
        async for msg in ws:
            e = json.loads(msg)
            t0 = t0 or e["ts"]
            t = f"{e['ts'] - t0:6.1f}s {e['agent'][:5]:5} {str(e.get('branch_id') or ''):14}"
            p = e["payload"]
            ty = e["type"]
            if ty == "plan":
                for b in p["graph"]["branches"]:
                    print(f"{t} PLAN {b['id']}: {b['start_url']}  steps={[s['action'] + ':' + str(s.get('target') or s.get('value'))[:40] for s in b['steps']]}")
            elif ty == "step_end":
                s = p["result"]
                print(f"{t} STEP {s['action']:8} {s['status']:9} {s.get('used')} conf={s.get('confidence')} {s.get('note') or ''} {str(s.get('target') or '')[:50]}")
            elif ty == "log" and "perception" in p:
                pp = p["perception"]
                print(f"{t}   page={pp['state']}({pp['state_conf']}) locate={pp['locate_conf']} target={str(pp.get('target'))[:40]}")
            elif ty == "log" and "recovery" in p:
                print(f"{t}   RECOVERY {p['recovery']}")
            elif ty in ("handoff", "handoff_resolved", "error", "branch_end"):
                print(f"{t} {ty.upper()} {json.dumps(p)[:300]}")
            elif ty == "action" and p.get("action") == "dismiss_popup":
                print(f"{t}   popup dismissed via {p.get('how')}")
            elif ty == "final":
                print(f"{t} FINAL {json.dumps(p, indent=1)[:4000]}")
            elif ty == "run_end":
                print(f"{t} END {p['status']}")
    print("run", run_id)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "blink"))
