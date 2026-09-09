"""Stage 106.1: what the engine says about itself reaches the client's
`initialize` answer, and a silent engine costs the session nothing.

`instructions` is the only prose that arrives before any tool does — a host
that defers tool schemas sends bare names, and this string still lands whole.
The proxy is the only place it can be put on the wire, and the only place it
can be dropped without anyone noticing: a missing field is not an error, and
the client shows a server with no instructions exactly as it shows a server
that sent none.

The negative half carries the weight. The proxy must start against a dead
engine — that is settled behaviour here, `_async_main` probes the backend and
refuses to exit on failure — so the code that reads this field runs on a path
where the engine may not answer at all. Reading it must not become the one
thing that turns a degraded start into no server at all.
"""

from __future__ import annotations

import httpx
import pytest

import letapis_mcp.server as srv

TEXT = "letapis answers by MEANING over the corpus indexed here."


class EngineWithAccount:
    async def get_tools(self):
        return {"tools": [], "instructions": TEXT}


class EngineWithoutAccount:
    """An older engine: it serves tools and has never heard of this field."""

    async def get_tools(self):
        return {"tools": []}


class EngineDown:
    async def get_tools(self):
        raise httpx.ConnectError("connection refused")


@pytest.mark.asyncio
async def test_the_account_the_engine_gives_is_the_one_that_travels():
    answer = await srv.probe_engine(EngineWithAccount())
    assert answer.get("instructions") == TEXT


@pytest.mark.asyncio
async def test_an_engine_that_says_nothing_yields_no_text():
    """Paired: absent upstream stays absent. An empty string would be a claim
    the engine did not make, and the client would render it as instructions."""
    answer = await srv.probe_engine(EngineWithoutAccount())
    assert answer.get("instructions") is None
    assert "tools" in answer, "the probe still has to report the tool list"


@pytest.mark.asyncio
async def test_a_dead_engine_costs_the_text_and_not_the_server():
    """Paired at the far end: the engine is unreachable. The probe must come
    back empty rather than raise — the proxy still has to come up."""
    assert await srv.probe_engine(EngineDown()) == {}


@pytest.mark.asyncio
async def test_the_field_reaches_the_initialization_options():
    """The wire form, not the attribute: the account is worth nothing until it
    is in the object the client is handed."""
    options = srv.build_initialization_options(TEXT)
    assert options.instructions == TEXT
    assert options.server_name == "letapis"


@pytest.mark.asyncio
async def test_no_account_leaves_the_options_valid():
    """Paired: the degraded start still produces options a client accepts."""
    options = srv.build_initialization_options(None)
    assert options.server_name == "letapis"
    assert not options.instructions
