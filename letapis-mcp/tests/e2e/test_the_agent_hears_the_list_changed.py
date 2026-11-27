"""The host hears `notifications/tools/list_changed` exactly when the surface it was shown is no longer the one the proxy would show.

Each probe starts the real proxy against a loopback engine and counts the notifications the
host receives. A ping after the last call is the fence: the proxy writes a notification
before the answer it belongs to, so once the ping is answered, every notification sent
before it has arrived.
"""
from __future__ import annotations

import copy

import pytest
from mcp import types

from tests.e2e.engine_double import (
    REGISTRY,
    SEARCH,
    TOOLS,
    Reply,
    call,
    healthy,
    listed,
    proxy,
    unused_url,
    write_config,
)

pytestmark = pytest.mark.asyncio

WITHOUT_SEARCH = {"tools": [t for t in REGISTRY["tools"] if t["name"] != "search"]}
UNAVAILABLE = Reply.json(503, {"detail": "warming up"})


@pytest.fixture
def engine():
    from tests.e2e.engine_double import EngineDouble

    doubles: list[EngineDouble] = []

    def start(script) -> EngineDouble:
        double = EngineDouble(script)
        double.start()
        doubles.append(double)
        return double

    yield start
    for double in doubles:
        double.stop()


class Host:
    """What the host is told unasked: the list-changed notifications, counted."""

    def __init__(self) -> None:
        self.list_changed = 0

    async def __call__(self, message) -> None:
        if isinstance(getattr(message, "root", message), types.ToolListChangedNotification):
            self.list_changed += 1

    async def heard(self, session) -> int:
        await session.send_ping()
        return self.list_changed


def serving(state: dict):
    """The engine lists `state["tools"]` and answers a call with `state["call"]`."""

    def script(request):
        if request.path == TOOLS:
            return state.get("tools_reply") or Reply.json(200, state["tools"])
        if request.path == SEARCH and state.get("call"):
            return state["call"]
        return healthy(request)

    return script


async def test_a_name_the_engine_starts_listing_is_announced_once(tmp_path, engine):
    state = {"tools": WITHOUT_SEARCH}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host) as session:
        state["tools"] = REGISTRY
        await call(session, "search", {"query": "x"})
        first = await host.heard(session)
        await call(session, "search", {"query": "x"})
        second = await host.heard(session)
        shown = await listed(session)
    assert (first, second) == (1, 1)
    assert "search" in shown, shown


async def test_a_changed_schema_is_announced(tmp_path, engine):
    """The host checks arguments against the schema it was shown, so a schema is part of the list."""
    state = {"tools": REGISTRY}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host) as session:
        changed = copy.deepcopy(REGISTRY)
        changed["tools"][0]["inputSchema"]["properties"]["limit"] = {"type": "integer"}
        state["tools"] = changed
        state["call"] = UNAVAILABLE
        await call(session, "search", {"query": "x"})
        state["call"] = None
        await call(session, "search", {"query": "x"})
        heard = await host.heard(session)
    assert heard == 1


async def test_the_same_list_loaded_again_is_not_announced(tmp_path, engine):
    state = {"tools": REGISTRY, "call": UNAVAILABLE}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host) as session:
        await call(session, "search", {"query": "x"})
        state["call"] = None
        payload = await call(session, "search", {"query": "x"})
        heard = await host.heard(session)
    assert payload.get("status") == "success", payload
    assert double.seen.count(TOOLS) >= 3, double.seen
    assert heard == 0


async def test_a_failure_is_not_announced(tmp_path, engine):
    """On a failure the host would re-read the outage surface and lose `search`; it keeps its list."""
    state = {"tools": REGISTRY, "call": UNAVAILABLE}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host) as session:
        state["tools_reply"] = UNAVAILABLE
        payload = await call(session, "search", {"query": "x"})
        heard = await host.heard(session)
    assert payload.get("status") == "unavailable", payload
    assert heard == 0


async def test_status_finds_the_engine_up_lists_its_tools_and_announces_them(tmp_path, engine):
    state = {"tools": REGISTRY, "tools_reply": UNAVAILABLE}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host) as session:
        before = await listed(session)
        state["tools_reply"] = None
        payload = await call(session, "letapis_status", {})
        heard = await host.heard(session)
        after = await listed(session)
    assert "letapis_status" in before and "search" not in before, before
    assert payload.get("status") == "success", payload
    assert heard == 1
    assert "search" in after and "letapis_status" not in after, after


async def test_status_with_the_engine_still_down_says_so_and_announces_nothing(tmp_path):
    host = Host()
    async with proxy(write_config(tmp_path, unused_url()), host) as session:
        payload = await call(session, "letapis_status", {})
        heard = await host.heard(session)
    assert payload.get("status") == "unavailable", payload
    assert heard == 0


async def test_status_reports_the_engine_as_it_is_now_not_as_it_was(tmp_path, engine):
    """The outage surface was built while the registry answered 503; the engine now answers 500."""
    state = {"tools": REGISTRY, "tools_reply": UNAVAILABLE}
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url)) as session:
        state["tools_reply"] = Reply.text(500, "internal error")
        payload = await call(session, "letapis_status", {})
    assert payload.get("status") != "success", payload
    assert "500" in payload.get("message", ""), payload


async def test_status_after_the_engine_went_down_says_it_is_down(tmp_path, engine):
    """The list was loaded while the engine was up; `letapis_status` reports the engine now."""
    state = {"tools": REGISTRY}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host) as session:
        state["tools_reply"] = UNAVAILABLE
        payload = await call(session, "letapis_status", {})
        heard = await host.heard(session)
    assert payload.get("status") == "unavailable", payload
    assert heard == 0


async def test_status_after_the_engine_changed_its_list_announces_the_new_one(tmp_path, engine):
    state = {"tools": REGISTRY}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host) as session:
        state["tools"] = WITHOUT_SEARCH
        payload = await call(session, "letapis_status", {})
        heard = await host.heard(session)
        shown = await listed(session)
    assert payload.get("status") == "success", payload
    assert heard == 1
    assert "search" not in shown, shown


async def test_status_with_the_engine_up_and_the_same_list_announces_nothing(tmp_path, engine):
    double = engine(serving({"tools": REGISTRY}))
    host = Host()
    async with proxy(write_config(tmp_path, double.url), host) as session:
        before = double.seen.count(TOOLS)
        payload = await call(session, "letapis_status", {})
        heard = await host.heard(session)
    assert payload.get("status") == "success", payload
    assert double.seen.count(TOOLS) == before + 1, double.seen
    assert heard == 0


async def test_the_outage_description_dates_what_it_says(tmp_path):
    """The host keeps the outage surface after the engine is back, so it must not say «is down» as of now."""
    async with proxy(write_config(tmp_path, unused_url())) as session:
        tools = {t.name: t for t in (await session.list_tools()).tools}
    description = tools["letapis_status"].description
    assert "when this tool list was made" in description, description
    assert "is UNAVAILABLE" not in description, description
