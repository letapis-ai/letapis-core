"""What the agent sees listed and what its call is routed by come from one answer of the engine.

Each probe starts the real proxy against a loopback engine whose tool list changes over the
session: a list missing `search` for a while, a list missing it for good, a list that changes
after the agent has read it. The probe reads what the agent reads and counts the engine's
`GET /api/v1/tools` requests.
"""
from __future__ import annotations

import json

import pytest

from tests.e2e.engine_double import (
    REGISTRY,
    TOOLS,
    EngineDouble,
    Reply,
    Request,
    call,
    healthy,
    listed,
    proxy,
    write_config,
)

pytestmark = pytest.mark.asyncio

WITHOUT_SEARCH = {"tools": [t for t in REGISTRY["tools"] if t["name"] != "search"]}


@pytest.fixture
def engine():
    doubles: list[EngineDouble] = []

    def start(script) -> EngineDouble:
        double = EngineDouble(script)
        double.start()
        doubles.append(double)
        return double

    yield start
    for double in doubles:
        double.stop()


def serving(state: dict) -> object:
    """An engine whose tool list is `state["tools"]` at the moment of each request."""

    def script(request: Request):
        if request.path == TOOLS:
            return Reply.json(200, state["tools"])
        return healthy(request)

    return script


def registry_requests(double: EngineDouble) -> int:
    return double.seen.count(TOOLS)


async def test_search_comes_back_once_the_engine_lists_it_again(tmp_path, engine):
    state = {"tools": WITHOUT_SEARCH}
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url)) as session:
        await call(session, "search", {"query": "x"})
        state["tools"] = REGISTRY
        payload = await call(session, "search", {"query": "x"})
    assert payload.get("status") == "success", payload


async def test_a_tool_the_engine_never_lists_is_said_to_be_not_served(tmp_path, engine):
    double = engine(serving({"tools": WITHOUT_SEARCH}))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    text = json.dumps(payload)
    for claim in ("stale_proxy_list", "_RETRY_SAFE_TOOLS", "Unknown tool"):
        assert claim not in text, payload
    assert "letapis-core" in text and "search" in text, payload


async def test_a_name_in_no_list_asks_the_engine_once(tmp_path, engine):
    double = engine(healthy)
    async with proxy(write_config(tmp_path, double.url)) as session:
        await call(session, "search", {"query": "x"})
        before = registry_requests(double)
        payload = await call(session, "no_such_tool", {})
        asked = registry_requests(double) - before
    assert payload == {"error": "Unknown tool: no_such_tool"}
    assert asked == 1, double.seen


async def test_the_call_follows_the_list_the_agent_was_shown(tmp_path, engine):
    state = {"tools": REGISTRY}
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url)) as session:
        assert "search" in await listed(session)
        state["tools"] = WITHOUT_SEARCH
        payload = await call(session, "search", {"query": "x"})
    assert payload.get("status") == "success", payload
