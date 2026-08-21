"""Three tools stay in the window, the other forty-seven arrive on demand.

The proxy marks a named few with ``_meta: {"anthropic/alwaysLoad": true}`` so the
client keeps their descriptions loaded once the SERVER-level `alwaysLoad` is off.

Every assertion here reads the mark the way the client will — through
``model_dump(by_alias=True, exclude_none=True)`` — and not by touching the
attribute, because the attribute existing is not the same as the field crossing
the wire under the name the client looks for.

The tool names are written out as literals rather than imported from
``srv.ALWAYS_LOADED``. A test that reads the same list it guards goes green together
with it: empty the constant and a constant-driven test simply stops checking
anything. `test_the_constant_holds_exactly_these_three` is the one place that compares
the two, so a deliberate change fails loudly there and nowhere else.
"""
from __future__ import annotations

import httpx
import pytest

import letapis_mcp.server as srv

ALWAYS_LOAD_KEY = "anthropic/alwaysLoad"

# The engine surface, trimmed to what these tests need: the three that must be
# marked plus three that must not be. `ena_add_episode` is there on purpose: the
# nearest neighbour of the pinned memory tool, so a build that pins the `ena_`
# prefix rather than the named tool fails here.
ENGINE_TOOLS = [
    {"name": "search", "description": "hybrid search", "inputSchema": {"type": "object"}},
    {"name": "blast_radius", "description": "callers of a symbol", "inputSchema": {"type": "object"}},
    {"name": "list_folders", "description": "watched folders", "inputSchema": {"type": "object"}},
    {"name": "ena_get_context", "description": "recall", "inputSchema": {"type": "object"}},
    {"name": "ena_add_episode", "description": "write an episode", "inputSchema": {"type": "object"}},
    {"name": "forget_document", "description": "hide a doc", "inputSchema": {"type": "object"}},
]


class FakeClientUp:
    def __init__(self, tools=None):
        self.tools = ENGINE_TOOLS if tools is None else tools

    async def get_tools(self):
        return {"tools": self.tools}

    async def call_tool(self, name, arguments):
        return {"status": "success"}


class FakeClientDown:
    async def get_tools(self):
        raise httpx.ConnectError("connection refused")


@pytest.fixture(autouse=True)
def clean_state():
    srv._tools_cache.clear()
    yield
    srv._tools_cache.clear()


def wire_meta(tool) -> dict | None:
    """The `_meta` the client receives, or None when the field is absent."""
    return tool.model_dump(by_alias=True, exclude_none=True).get("_meta")


# --- the two halves ------------------------------------------------------------


@pytest.mark.asyncio
async def test_named_tools_carry_the_mark(monkeypatch):
    """Positive half: every name in the list crosses the wire marked."""
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    tools = {t.name: t for t in await srv.list_tools()}

    for name in ("search", "blast_radius", "ena_get_context"):
        assert wire_meta(tools[name]) == {ALWAYS_LOAD_KEY: True}, (
            f"{name} must reach the client with {ALWAYS_LOAD_KEY}"
        )


@pytest.mark.asyncio
async def test_unnamed_tools_carry_no_meta_at_all(monkeypatch):
    """Negative half — the one that fails on code marking everything.

    The positive test above is green on a proxy that stamps the mark onto every
    tool it builds. This one is not: it requires the field to be ABSENT, not
    merely false, because a client reading `_meta` for the key would find it.
    """
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    tools = {t.name: t for t in await srv.list_tools()}

    for name in ("list_folders", "ena_add_episode", "forget_document"):
        assert wire_meta(tools[name]) is None, (
            f"{name} is not in the always-loaded list and must carry no _meta; "
            f"got {wire_meta(tools[name])!r}"
        )


@pytest.mark.asyncio
async def test_exactly_the_named_ones_are_marked(monkeypatch):
    """Counts, not spot checks: the marked set equals the named set."""
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    tools = await srv.list_tools()

    marked = {t.name for t in tools if wire_meta(t)}
    assert marked == {"search", "blast_radius", "ena_get_context"}


def test_the_constant_holds_exactly_these_three():
    """Guards the list itself, so emptying it cannot pass as 'nothing to check'.

    Without this, deleting a name would leave every test above green — they would
    simply stop asserting about it. This is also the test a deliberate change to
    the list is supposed to fail, so the change gets read rather than absorbed.
    """
    assert srv.ALWAYS_LOADED == ("search", "blast_radius", "ena_get_context")


# --- a name the engine does not serve ------------------------------------------


@pytest.mark.asyncio
async def test_a_name_the_engine_does_not_serve_is_reported(monkeypatch, capsys):
    """A renamed or removed tool must not drop out of the list in silence.

    Silence here is the dangerous outcome: the proxy would keep working, the
    caller would keep its window, and the tool meant to stay loaded would have
    quietly become deferred.
    """
    monkeypatch.setattr(srv, "ALWAYS_LOADED", ("search", "blast_radius", "no_such_tool"))
    monkeypatch.setattr(srv, "_client", FakeClientUp())

    await srv.list_tools()

    err = capsys.readouterr().err
    assert "no_such_tool" in err, f"the missing name must be named; stderr was: {err!r}"


@pytest.mark.asyncio
async def test_nothing_is_reported_when_every_name_is_served(monkeypatch, capsys):
    """The negative half of the warning: it must not cry on a healthy set.

    Asserts on WARNING rather than on the phrase "always-loaded": the startup line
    carries that phrase legitimately, and a test matching it would be reporting on
    its own neighbour instead of on the warning.
    """
    monkeypatch.setattr(srv, "_client", FakeClientUp())

    await srv.list_tools()

    err = capsys.readouterr().err
    assert "WARNING" not in err, f"unexpected warning: {err!r}"


# --- the surfaces the mark must not leak into ----------------------------------


@pytest.mark.asyncio
async def test_the_mark_survives_the_cache(monkeypatch):
    """Second call is served from `_tools_cache`; the mark must still be there."""
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    await srv.list_tools()

    cached = {t.name: t for t in await srv.list_tools()}
    assert wire_meta(cached["search"]) == {ALWAYS_LOAD_KEY: True}
    assert wire_meta(cached["list_folders"]) is None


@pytest.mark.asyncio
async def test_the_outage_message_is_pinned(monkeypatch):
    """Engine down: `letapis_status` IS its description, so it must arrive loaded.

    A deferred one leaves the caller a bare name at the moment it is already
    confused, and one more call to learn why is how an agent gives up on the tool.
    """
    monkeypatch.setattr(srv, "_client", FakeClientDown())
    degraded = {t.name: t for t in await srv.list_tools()}

    assert set(degraded) == {"letapis_status", "fetch_file"}
    assert wire_meta(degraded["letapis_status"]) == {ALWAYS_LOAD_KEY: True}


@pytest.mark.asyncio
async def test_the_outage_message_is_pinned_even_when_the_list_is_empty(monkeypatch):
    """Negative half of the pinning above: it must NOT come from ALWAYS_LOADED.

    Whatever the list says — and it is edited by hand, so it can say nothing — the
    proxy still has to be able to report that the engine is down. A `letapis_status`
    fed from the list goes silent exactly when the list is trimmed.
    """
    monkeypatch.setattr(srv, "ALWAYS_LOADED", ())
    monkeypatch.setattr(srv, "_client", FakeClientDown())
    degraded = {t.name: t for t in await srv.list_tools()}

    assert wire_meta(degraded["letapis_status"]) == {ALWAYS_LOAD_KEY: True}


@pytest.mark.asyncio
@pytest.mark.parametrize("client", [FakeClientUp(), FakeClientDown()])
async def test_fetch_file_is_never_pinned(monkeypatch, client):
    """`fetch_file` stays deferred in both lists, and that is a decision.

    It is an ordinary tool, not a message about an outage: its description explains
    when to reach for it, which is read at the moment of reaching. 179 characters in
    every window forever against single-figure use is the wrong side of the trade.
    """
    monkeypatch.setattr(srv, "_client", client)
    tools = {t.name: t for t in await srv.list_tools()}

    assert wire_meta(tools["fetch_file"]) is None


# --- the list is read, not reimplemented ---------------------------------------


@pytest.mark.asyncio
async def test_an_empty_list_marks_nothing(monkeypatch):
    """Trimming the list to nothing must leave the surface unmarked."""
    monkeypatch.setattr(srv, "ALWAYS_LOADED", ())
    monkeypatch.setattr(srv, "_client", FakeClientUp())

    tools = await srv.list_tools()
    assert {t.name for t in tools if wire_meta(t)} == set()


@pytest.mark.asyncio
async def test_a_different_list_pins_a_different_tool(monkeypatch):
    """The list is data the build reads, not a rename of the same two names.

    A test fixed on ("search", "blast_radius") stays green on code that ignores
    ALWAYS_LOADED and hardcodes those two names in the build; this one does not.
    """
    monkeypatch.setattr(srv, "ALWAYS_LOADED", ("list_folders",))
    monkeypatch.setattr(srv, "_client", FakeClientUp())

    tools = await srv.list_tools()
    assert {t.name for t in tools if wire_meta(t)} == {"list_folders"}



# --- what the log says about what happened -------------------------------------


@pytest.mark.asyncio
async def test_the_startup_line_says_what_is_pinned(monkeypatch, capsys):
    """A count of tools does not say which of them stayed loaded.

    Two things decide that — the list here and the surface the engine serves — and
    both move without this file being read. The line is where the result is visible.
    """
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    await srv.list_tools()

    assert (
        "always-loaded: blast_radius, ena_get_context, search"
        in capsys.readouterr().err
    )


@pytest.mark.asyncio
async def test_the_startup_line_says_none_when_nothing_is_pinned(monkeypatch, capsys):
    """Negative half: 'none' is printed, rather than the line going quiet."""
    monkeypatch.setattr(srv, "ALWAYS_LOADED", ())
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    await srv.list_tools()

    assert "always-loaded: none" in capsys.readouterr().err
