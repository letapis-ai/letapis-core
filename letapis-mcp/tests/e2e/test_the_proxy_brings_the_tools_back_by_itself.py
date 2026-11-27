"""A session started while the engine is down gets the engine's tools without asking for them.

Each probe starts the real proxy on stdio against a loopback engine that answers 503 for a while.
The host never calls anything after the start. The engine's check period is an input the probe
gives the proxy by number (`LETAPIS_ENGINE_POLL_SECONDS`), and the host waits for the
notification as an event with a deadline given by number: no probe waits out the real period.
"""
from __future__ import annotations

import asyncio

import pytest
from mcp import types

from tests.e2e.engine_double import (
    REGISTRY,
    TOOLS,
    EngineDouble,
    Reply,
    healthy,
    listed,
    proxy,
    write_config,
)

pytestmark = pytest.mark.asyncio

POLL = {"LETAPIS_ENGINE_POLL_SECONDS": "0.05"}
DEADLINE = 3.0
"""Seconds the host waits for a notification that must come; sixty periods of the check."""
QUIET = 0.5
"""Seconds the host listens for a notification that must not come; ten periods of the check."""
UNAVAILABLE = Reply.json(503, {"detail": "warming up"})


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


class Host:
    """What the host is told unasked: list-changed notifications, counted, with an event to wait on."""

    def __init__(self) -> None:
        self.list_changed = 0
        self.heard_one = asyncio.Event()

    async def __call__(self, message) -> None:
        if isinstance(getattr(message, "root", message), types.ToolListChangedNotification):
            self.list_changed += 1
            self.heard_one.set()

    async def waits_for_one(self) -> bool:
        try:
            await asyncio.wait_for(self.heard_one.wait(), DEADLINE)
        except asyncio.TimeoutError:
            return False
        return True

    async def hears_none(self) -> bool:
        try:
            await asyncio.wait_for(self.heard_one.wait(), QUIET)
        except asyncio.TimeoutError:
            return True
        return False


def serving(state: dict):
    def script(request):
        if request.path == TOOLS and state.get("down"):
            return UNAVAILABLE
        return healthy(request)

    return script


async def test_the_engine_comes_up_and_the_host_is_told_without_calling_anything(tmp_path, engine):
    state = {"down": True}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host, env=POLL) as session:
        assert "search" not in await listed(session)
        state["down"] = False
        told = await host.waits_for_one()
        after = await listed(session) if told else set()
    assert told, "the engine came up, the host called nothing, and was never told"
    assert "search" in after and "letapis_status" not in after, after


async def test_one_engine_coming_up_is_one_notification(tmp_path, engine):
    state = {"down": True}
    host = Host()
    double = engine(serving(state))
    async with proxy(write_config(tmp_path, double.url), host, env=POLL) as session:
        state["down"] = False
        told = await host.waits_for_one()
        host.heard_one.clear()
        quiet_after = await host.hears_none()
        await session.send_ping()
    assert told, "never told"
    assert quiet_after and host.list_changed == 1, host.list_changed


async def test_an_engine_still_down_tells_the_host_nothing(tmp_path, engine):
    host = Host()
    double = engine(serving({"down": True}))
    async with proxy(write_config(tmp_path, double.url), host, env=POLL) as session:
        quiet = await host.hears_none()
        shown = await listed(session)
    assert quiet, host.list_changed
    assert "search" not in shown, shown


async def test_an_engine_that_was_up_from_the_start_tells_the_host_nothing(tmp_path, engine):
    """The paired half: the first list was the full one, so there is nothing to bring back."""
    host = Host()
    double = engine(serving({"down": False}))
    async with proxy(write_config(tmp_path, double.url), host, env=POLL) as session:
        quiet = await host.hears_none()
        shown = await listed(session)
    assert quiet, host.list_changed
    assert {t["name"] for t in REGISTRY["tools"]} <= shown, shown
