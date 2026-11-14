import pytest

from app import planner
from app.models import TaskGraph
from app.orchestrator import run_blink
from app.safety import is_sensitive_value, luhn_ok
from app.models import Step
from app.clients.jev_client import box_from_fractions
from app.imaging import fit_for_jev



def graph(base: str) -> dict:
    flights = {"id": "flights", "goal": "cheapest flight", "start_url": f"{base}/index.html", "steps": [
        {"id": "s1", "action": "type", "target": "Leaving from field", "value": "Cairo", "expect": "field shows 'Cairo'"},
        {"id": "s2", "action": "type", "target": "Going to field", "value": "Tokyo", "expect": "field shows 'Tokyo'"},
        {"id": "s3", "action": "click", "target": "Search flights button", "expect": "results to 'Tokyo'"},
        {"id": "s4", "action": "extract", "target": "the flight results with prices"}]}
    direct = {"id": "direct", "goal": "results via direct url",
              "start_url": f"{base}/results.html?from=Cairo&to=Osaka", "steps": [
                  {"id": "s1", "action": "extract", "target": "the flight results with prices"}]}
    return {"goal": "trip cost", "branches": [flights, direct], "synthesis_instructions": ""}


async def test_parallel_run_end_to_end(pool, make_ctx, fixture_url, monkeypatch):
    llm = {
        "plan": graph(fixture_url),
        "extract": {"items": [{"airline": "EgyptAir", "price": 612, "currency": "USD"}]},
        "synthesize": {"summary": "Flights from about $612.", "table": [
            {"category": "Flights", "mid": 612, "currency": "USD", "source_url": f"{fixture_url}/results.html"}]},
    }
    ctx = make_ctx(llm_responses=llm)
    monkeypatch.setattr(planner, "_CACHE", ctx.dir / "plan_cache.json")
    final = await run_blink(ctx, pool, "trip cost", use_plan_cache=False)
    assert final.table[0].mid == 612
    ends = [e for e in ctx.events.events if e.type == "branch_end"]
    assert {e.branch_id for e in ends} == {"flights", "direct"}
    # branches overlapped in time (parallel)
    starts = {e.branch_id: e.ts for e in ctx.events.events if e.type == "branch_start"}
    first_end = min(e.ts for e in ends)
    assert all(t < first_end for t in starts.values())
    assert ctx.llm.calls.count("plan") == 1 and "synthesize" in ctx.llm.calls


def test_planner_sanitize():
    g = TaskGraph.model_validate({"goal": "x", "branches": [
        {"id": "Flights Search", "goal": "a", "start_url": "https://a", "steps": []},
        {"id": "flights search", "goal": "b", "start_url": "https://b", "steps": []}] * 3})
    g = planner._sanitize(g, 4)
    assert len(g.branches) == 4 and len({b.id for b in g.branches}) == 4


def test_safety_rules():
    assert luhn_ok("4111111111111111")
    assert is_sensitive_value(Step(id="1", action="type", target="name", value="4111 1111 1111 1111"))
    assert is_sensitive_value(Step(id="1", action="type", target="Password field", value="hunter2"))
    assert not is_sensitive_value(Step(id="1", action="type", target="From field", value="Cairo"))


def test_box_fraction_conversion():
    b = box_from_fractions({"left": 0.5, "right": 0.6, "top": 0.1, "bottom": 0.2}, 1366, 900, 0.9)
    assert round(b.x) == 683 and round(b.w) == 137 and round(b.y) == 90 and round(b.h) == 90


def test_fit_for_jev_limits():
    from PIL import Image
    import io
    for size in ((1366, 900), (3000, 800), (200, 150)):
        buf = io.BytesIO()
        Image.new("RGB", size, "white").save(buf, format="PNG")
        data, fmt = fit_for_jev(buf.getvalue(), max_width=1280)
        w, h = Image.open(io.BytesIO(data)).size
        assert 280 <= w <= 1568 and 280 <= h <= 1568 and fmt == "jpeg"
