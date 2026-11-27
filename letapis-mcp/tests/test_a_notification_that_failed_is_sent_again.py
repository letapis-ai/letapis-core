"""A surface counts as shown to the host only once the host was told; a notification that failed is sent again.

The session is a double that fails the way the input says. The client is a double that holds
the engine's full list, as after the engine came back.
"""
from __future__ import annotations

import asyncio

import pytest

import letapis_mcp.server as srv
from letapis_mcp.client import ToolList
from tests import handlers

ENGINE_TOOLS = [
    {"name": "search", "endpoint": "/api/v1/search", "description": "hybrid search",
     "inputSchema": {"type": "object"}},
]


class EngineBack:
    async def tool_list(self):
        return ToolList.from_answer({"tools": ENGINE_TOOLS})

    async def tool_list_now(self):
        return await self.tool_list()

    def kept_tool_list(self):
        return ToolList.from_answer({"tools": ENGINE_TOOLS})


class EngineDown:
    async def tool_list(self):
        raise ConnectionError("down")


class Session(handlers.Session):
    """Refuses the first `failures` notifications."""

    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures = failures
        self.attempts = 0
        self.told = asyncio.Event()

    async def send_tool_list_changed(self) -> None:
        self.attempts += 1
        if self.failures:
            self.failures -= 1
            raise RuntimeError("the write failed")
        await super().send_tool_list_changed()
        self.told.set()


async def host_shown_the_outage(monkeypatch, session: Session) -> None:
    monkeypatch.setattr(srv, "_client", EngineDown())
    monkeypatch.setattr(srv, "_session", session)
    monkeypatch.setattr(srv, "_shown", await srv.tool_surface(srv.get_client(), "http://x"))
    monkeypatch.setattr(srv, "_client", EngineBack())


@pytest.mark.asyncio
async def test_a_failed_notification_is_sent_again_on_the_next_ask(monkeypatch):
    session = Session(failures=1)
    await host_shown_the_outage(monkeypatch, session)

    with pytest.raises(RuntimeError):
        await srv.announce_if_changed()
    await srv.announce_if_changed()

    assert session.list_changed == 1, (session.attempts, session.list_changed)


@pytest.mark.asyncio
async def test_a_notification_that_went_out_is_not_sent_again(monkeypatch):
    session = Session(failures=0)
    await host_shown_the_outage(monkeypatch, session)

    await srv.announce_if_changed()
    await srv.announce_if_changed()

    assert session.list_changed == 1, session.list_changed


@pytest.mark.asyncio
async def test_the_watch_keeps_asking_until_the_host_was_told(monkeypatch):
    """The path the work exists for: a refused write must not leave the host without tools."""
    session = Session(failures=1)
    await host_shown_the_outage(monkeypatch, session)

    watch = asyncio.create_task(srv.watch_engine(0.01))
    try:
        await asyncio.wait_for(session.told.wait(), 3.0)
    finally:
        watch.cancel()

    assert session.list_changed == 1, (session.attempts, session.list_changed)
