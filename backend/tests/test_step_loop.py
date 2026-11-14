import asyncio

import pytest

from app.branch_runner import run_branch
from app.models import Branch, Step



def flight_branch(base: str) -> Branch:
    return Branch(id="flights", goal="Find the cheapest flight from Cairo to Tokyo", start_url=f"{base}/index.html",
                  steps=[
                      Step(id="s1", action="type", target="Leaving from field", value="Cairo", expect="field shows 'Cairo'"),
                      Step(id="s2", action="type", target="Going to field", value="Tokyo", expect="field shows 'Tokyo'"),
                      Step(id="s3", action="click", target="Search flights button", expect="results list of flights to 'Tokyo'"),
                      Step(id="s4", action="extract", target="the list of flight results with prices",
                           extract_schema={"airline": "string", "price": "number", "currency": "string"}),
                  ])


async def test_full_branch_with_cookie_banner(pool, make_ctx, fixture_url):
    llm = {"extract": {"items": [{"airline": "EgyptAir", "price": 612, "currency": "USD"}]}}
    ctx = make_ctx(llm_responses=llm)
    bctx = await pool.new_context()
    res = await run_branch(ctx, bctx, flight_branch(fixture_url))
    await bctx.close()
    statuses = [s.status for s in res.steps]
    assert statuses == ["ok", "ok", "ok", "ok"], [(s.status, s.note) for s in res.steps]
    assert res.extracted and res.extracted[0]["price"] == 612
    assert res.status == "done"
    kinds = [e.type for e in ctx.events.events]
    assert "action" in kinds and "branch_end" in kinds
    # the cookie banner was dismissed by rejecting (privacy first)
    dismiss = [e.payload for e in ctx.events.events if e.payload.get("action") == "dismiss_popup"]
    assert dismiss and dismiss[0]["how"] == "dom:reject"


async def test_jev_path_without_dom_fastpath(pool, make_ctx, fixture_url):
    llm = {"extract": {"items": [{"airline": "EgyptAir", "price": 612, "currency": "USD"}]}}
    ctx = make_ctx(llm_responses=llm, use_dom_fastpath=False, use_site_memory=False)
    bctx = await pool.new_context()
    res = await run_branch(ctx, bctx, flight_branch(fixture_url))
    await bctx.close()
    assert [s.used for s in res.steps[:3]] == ["jev", "jev", "jev"]
    assert all(s.status == "ok" for s in res.steps)


async def test_site_memory_used_on_second_run(pool, make_ctx, fixture_url):
    llm = {"extract": {"items": [{"price": 612}]}}
    ctx = make_ctx(llm_responses=llm, use_dom_fastpath=False)
    for _ in range(2):
        bctx = await pool.new_context()
        res = await run_branch(ctx, bctx, flight_branch(fixture_url))
        await bctx.close()
    assert res.steps[0].used == "site_memory"
    assert ctx.metrics.cache_hits >= 2


async def test_payment_page_hard_stop(pool, make_ctx, fixture_url):
    ctx = make_ctx()
    b = Branch(id="pay", goal="try to buy", start_url=f"{fixture_url}/checkout.html", steps=[
        Step(id="s1", action="type", target="Card number field", value="4111 1111 1111 1111"),
        Step(id="s2", action="click", target="Pay now button"),
    ])
    bctx = await pool.new_context()
    res = await run_branch(ctx, bctx, b)
    await bctx.close()
    assert res.status == "stopped"
    assert res.steps[0].status == "blocked"
    assert any(e.type == "handoff" and e.payload.get("kind") == "payment" for e in ctx.events.events)


async def test_payment_button_blocked_even_on_normal_page(pool, make_ctx, fixture_url):
    ctx = make_ctx()
    b = Branch(id="pay2", goal="x", start_url=f"{fixture_url}/results.html?from=Cairo&to=Tokyo", steps=[
        Step(id="s1", action="click", target="Book now button"),
    ])
    bctx = await pool.new_context()
    res = await run_branch(ctx, bctx, b)
    await bctx.close()
    assert res.steps[0].status == "blocked" and res.status == "stopped"


async def test_bot_check_hands_off_to_user_and_resumes(pool, make_ctx, fixture_url):
    ctx = make_ctx(handoff_timeout_s=30)
    b = Branch(id="bot", goal="get to the search page", start_url=f"{fixture_url}/botcheck.html", steps=[
        Step(id="s1", action="type", target="Leaving from field", value="Cairo", expect="field shows 'Cairo'"),
    ])
    bctx = await pool.new_context()
    task = asyncio.create_task(run_branch(ctx, bctx, b))
    # wait until Blink asks for help, then act as the user: solve the check ourselves
    for _ in range(100):
        if any(e.type == "handoff" for e in ctx.events.events):
            break
        await asyncio.sleep(0.1)
    assert any(e.type == "handoff" and e.payload["kind"] == "bot_check" for e in ctx.events.events)
    page = bctx.pages[0]
    await page.click("#human", no_wait_after=True)  # the human solves it
    ctx.continue_events["bot"].set()  # and presses Continue (Blink may also auto-resume first)
    res = await asyncio.wait_for(task, 30)
    await bctx.close()
    assert any(e.type == "handoff_resolved" and e.payload["resolved"] for e in ctx.events.events)
    assert res.steps[0].status == "ok"


async def test_recovery_retarget(pool, make_ctx, fixture_url):
    # target described badly -> mock Jev can't find it -> LLM recovery retargets
    llm = {"recovery": {"decision": "retarget", "target": "Going to field", "reason": "use the visible label"}}
    ctx = make_ctx(llm_responses=llm, use_dom_fastpath=False, use_site_memory=False)
    b = Branch(id="rec", goal="type destination", start_url=f"{fixture_url}/index.html", steps=[
        Step(id="s1", action="type", target="zzqx widget", value="Tokyo", expect="field shows 'Tokyo'"),
    ])
    bctx = await pool.new_context()
    res = await run_branch(ctx, bctx, b)
    await bctx.close()
    assert res.steps[0].status == "recovered"
    assert res.steps[0].used == "llm_recovery"
    assert "recovery" in ctx.llm.calls
