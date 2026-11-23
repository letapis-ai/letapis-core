"""Calls made at the same time are routed by one answer of the engine, and the agent sees only what it can call.

The host calls tools in parallel. Each probe starts the real proxy against a loopback engine
that holds its answer to `GET /api/v1/tools` until a signal request arrives, so loads that
start together overlap. The signal is `fetch_file`: the proxy sends it to the engine without
needing the tool list. Each held answer is a different version of the list, so the probe can
tell from the engine's side which answer a call was routed by.
"""
from __future__ import annotations

import asyncio
import threading

import pytest

from tests.e2e.engine_double import (
    CONTENT,
    REGISTRY,
    SEARCH,
    TOOLS,
    EngineDouble,
    Reply,
    Request,
    call,
    healthy,
    proxy,
    write_config,
)

pytestmark = pytest.mark.asyncio

PARALLEL = 4
HOLD_LIMIT = 5.0
"""Seconds a held list answer waits for the signal before it is given anyway."""
TIMEOUT = 10.0


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


def versioned(n: int) -> dict:
    """The registry with `search` served at an endpoint that names the answer it came from."""
    return {"tools": [
        dict(t, endpoint=f"{SEARCH}/v{n}") if t["name"] == "search" else t
        for t in REGISTRY["tools"]
    ]}


class HeldLists:
    """Once armed, every list request waits for the signal and gets the next version."""

    def __init__(self, before_armed) -> None:
        self.before_armed = before_armed
        self.armed = False
        self.asked = 0
        self.signal = threading.Event()
        self._lock = threading.Lock()

    def __call__(self, request: Request):
        if request.path == CONTENT:
            self.signal.set()
            return healthy(request)
        if request.path != TOOLS:
            return healthy(request)
        if not self.armed:
            return self.before_armed
        with self._lock:
            self.asked += 1
            n = self.asked
        self.signal.wait(HOLD_LIMIT)
        return Reply.json(200, versioned(n))


async def calls_with_signal(session, name: str) -> list[dict]:
    calls = [call(session, name, {"query": "x"}) for _ in range(PARALLEL)]
    results = await asyncio.gather(*calls, call(session, "fetch_file", {"path": "/w/a.md"}))
    return list(results[:PARALLEL])


def search_endpoints(double: EngineDouble) -> set[str]:
    return {path for path in double.seen if path.startswith(SEARCH + "/")}


async def test_parallel_calls_on_an_empty_list_wait_for_one_answer(tmp_path, engine):
    lists = HeldLists(before_armed=Reply.text(500, "starting"))
    double = engine(lists)
    async with proxy(write_config(tmp_path, double.url, timeout=TIMEOUT)) as session:
        lists.armed = True
        answers = await calls_with_signal(session, "search")
    assert all(a.get("status") == "success" for a in answers), answers
    assert lists.asked == 1, double.seen
    assert len(search_endpoints(double)) == 1, double.seen


async def test_parallel_misses_reload_the_list_once(tmp_path, engine):
    lists = HeldLists(before_armed=Reply.json(200, REGISTRY))
    double = engine(lists)
    async with proxy(write_config(tmp_path, double.url, timeout=TIMEOUT)) as session:
        lists.armed = True
        answers = await calls_with_signal(session, "no_such_tool")
    assert answers == [{"error": "Unknown tool: no_such_tool"}] * PARALLEL
    assert lists.asked == 1, double.seen


async def test_a_record_without_an_endpoint_is_not_shown(tmp_path, engine):
    ghost = {"name": "ghost", "method": "POST", "inputSchema": {"type": "object"}}
    registry = {"tools": REGISTRY["tools"] + [ghost]}

    def script(request: Request):
        return Reply.json(200, registry) if request.path == TOOLS else healthy(request)

    double = engine(script)
    async with proxy(write_config(tmp_path, double.url)) as session:
        names = [t.name for t in (await session.list_tools()).tools]
    assert "ghost" not in names
    assert "search" in names


async def test_a_name_served_twice_is_shown_once_and_called_where_shown(tmp_path, engine):
    first = {"name": "search", "method": "POST", "endpoint": f"{SEARCH}/first",
             "description": "first", "inputSchema": {"type": "object"}}
    second = dict(first, endpoint=f"{SEARCH}/second", description="second")
    registry = {"tools": [first, second]}

    def script(request: Request):
        return Reply.json(200, registry) if request.path == TOOLS else healthy(request)

    double = engine(script)
    async with proxy(write_config(tmp_path, double.url)) as session:
        shown = [t for t in (await session.list_tools()).tools if t.name == "search"]
        await call(session, "search", {"query": "x"})
    assert len(shown) == 1, shown
    assert search_endpoints(double) == {f"{SEARCH}/{shown[0].description}"}, double.seen
