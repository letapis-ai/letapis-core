"""`reveal` travels from the tool the head calls to the engine's own route (69.1).

A folder can be marked hidden in the engine: it is indexed like any other and answers
nobody who did not name it in `reveal`. Seven of the eight surfaces that hand content out
are engine tools, so the parameter reaches them by being in the engine's own schema. The
eighth is not: `fetch_file` is declared HERE, in the proxy, and proxied to
`GET /api/v1/files/content` by hand — so a parameter this file does not know about
does not exist for the head that calls the tool.

The chain has three links and each is asked separately, because each fails silently on
its own: the schema (the head cannot even send it), the handler (it is read and dropped),
the client (it never reaches the query string). A single end-to-end probe would go red on
any of the three and say the same thing about all of them.

The last link is asked of the WIRE — the params handed to the HTTP call — rather than of
the arguments the client was given. `reveal` reaches the engine as a repeated query
parameter, and a list sent under the wrong shape is accepted by the client, rejected by
nothing, and quietly ignored by FastAPI.
"""
from __future__ import annotations

from typing import Any

import pytest

import letapis_mcp.server as srv
from letapis_mcp.client import letapisClient

HIDDEN_COPY = "/w/copy_a"
REMOTE = "/w/copy_a/notes.md"


@pytest.fixture(autouse=True)
def clean_state():
    srv._tools_cache.clear()
    yield
    srv._tools_cache.clear()


# ---------------------------------------------------------------------------
# 1. the head can send it
# ---------------------------------------------------------------------------


def test_the_tool_declares_reveal():
    """Declared here or nowhere: this tool's schema is not the engine's."""
    props = srv.FETCH_FILE_TOOL.inputSchema["properties"]

    assert "reveal" in props
    assert props["reveal"]["type"] == "array"
    assert props["reveal"]["items"]["type"] == "string"
    assert "reveal" not in srv.FETCH_FILE_TOOL.inputSchema["required"], (
        "a request without it must stay legal — that is the default the mark exists for"
    )


# ---------------------------------------------------------------------------
# 2. the handler reads it
# ---------------------------------------------------------------------------


class _RecordingClient:
    """A client that fetches nothing and remembers what it was asked to fetch."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def fetch_file(self, path: str, reveal: list[str] | None = None) -> bytes:
        self.calls.append((path, reveal))
        return b"a recognisable string\n"


@pytest.fixture
def proxy(monkeypatch, tmp_path):
    """The proxy wired to a recording client and a cache nobody has written to yet."""
    from letapis_mcp.config import Config
    from letapis_mcp.paths import PathHandler

    config = Config()
    config.paths.fetch.cache_dir = tmp_path / "cache"
    client = _RecordingClient()
    monkeypatch.setattr(srv, "_client", client)
    monkeypatch.setattr(srv, "_paths", PathHandler(config))
    return client


@pytest.mark.asyncio
async def test_the_handler_carries_reveal_through(proxy):
    result = await srv._handle_fetch_file({"path": REMOTE, "reveal": [HIDDEN_COPY]})

    assert result["status"] == "success", result
    assert proxy.calls == [(REMOTE, [HIDDEN_COPY])]


@pytest.mark.asyncio
async def test_a_call_without_reveal_asks_for_nothing_extra(proxy):
    """The negative twin. `None`, not `[]`: an empty list is a caller saying «reveal
    these none», and the engine would have to tell that from silence for no reason."""
    await srv._handle_fetch_file({"path": "/w/base/notes.md"})

    assert proxy.calls == [("/w/base/notes.md", None)]


# ---------------------------------------------------------------------------
# 3. it reaches the query string
# ---------------------------------------------------------------------------


class _RecordingTransport:
    """Stands in for the HTTP client and keeps the params it was handed."""

    def __init__(self) -> None:
        self.params: Any = None

    async def get(self, url: str, params: dict[str, Any]) -> Any:
        self.params = params

        class _Response:
            content = b"a recognisable string\n"

            def raise_for_status(self) -> None:
                return None

        return _Response()


@pytest.mark.asyncio
async def test_the_client_puts_reveal_on_the_wire():
    client = letapisClient.__new__(letapisClient)
    transport = _RecordingTransport()
    client._client = transport

    await client.fetch_file(REMOTE, reveal=[HIDDEN_COPY])

    assert transport.params == {"path": REMOTE, "reveal": [HIDDEN_COPY]}


@pytest.mark.asyncio
async def test_the_wire_carries_no_reveal_key_when_none_was_asked_for():
    """The negative twin at the wire. A `reveal=None` in the params dict is sent by
    httpx as an empty value, and an empty `reveal` is not the same request as no
    `reveal` — the key must be absent, not present and blank."""
    client = letapisClient.__new__(letapisClient)
    transport = _RecordingTransport()
    client._client = transport

    await client.fetch_file("/w/base/notes.md")

    assert transport.params == {"path": "/w/base/notes.md"}


# ---------------------------------------------------------------------------
# 4. the cache is not a permission
# ---------------------------------------------------------------------------


class _GatedClient:
    """The engine, as far as this proxy can tell: serves a hidden path only when the
    call names the copy, and refuses it otherwise exactly as the route does."""

    def __init__(self, hidden_root: str) -> None:
        self.hidden_root = hidden_root
        self.calls: list[tuple[str, Any]] = []

    async def fetch_file(self, path: str, reveal: list[str] | None = None) -> bytes:
        self.calls.append((path, reveal))
        if path.startswith(self.hidden_root + "/") and self.hidden_root not in (reveal or []):
            raise RuntimeError("403: Path not within indexed folders")
        return b"a recognisable string\n"


@pytest.fixture
def gated(monkeypatch, tmp_path):
    from letapis_mcp.config import Config
    from letapis_mcp.paths import PathHandler

    config = Config()
    config.paths.fetch.cache_dir = tmp_path / "cache"
    client = _GatedClient(HIDDEN_COPY)
    monkeypatch.setattr(srv, "_client", client)
    monkeypatch.setattr(srv, "_paths", PathHandler(config))
    return client


@pytest.mark.asyncio
async def test_a_file_read_once_with_reveal_is_refused_without_it(gated):
    """Permission belongs to the request that is being answered, not to the one that
    came before it.

    The cache saved the answer to «may A read this», and every later caller inherited
    it. Nothing about that is visible from the outside: the second call returns the
    same bytes the first did, with `cached: true`, and the only thing missing is the
    question nobody asked.
    """
    opened = await srv._handle_fetch_file(
        {"path": REMOTE, "reveal": [HIDDEN_COPY]}
    )
    assert opened["status"] == "success", opened

    again = await srv._handle_fetch_file({"path": REMOTE})

    assert again["status"] == "error", again
    assert "local_path" not in again, "a path to the cached copy is the leak itself"
    assert gated.calls[-1] == (REMOTE, None), (
        "the second call must have ASKED the engine — a refusal decided here would be "
        "this proxy keeping a second copy of a rule that lives in the engine"
    )


@pytest.mark.asyncio
async def test_the_same_file_opens_again_for_a_call_that_names_the_copy(gated):
    """…and the refusal above is not the cache turning into a wall: the head working
    in the copy reads its own file as many times as it likes."""
    await srv._handle_fetch_file({"path": REMOTE, "reveal": [HIDDEN_COPY]})
    again = await srv._handle_fetch_file({"path": REMOTE, "reveal": [HIDDEN_COPY]})

    assert again["status"] == "success", again
    assert again["local_path"]


@pytest.mark.asyncio
async def test_an_ordinary_file_still_comes_back_from_the_cache(gated):
    """The negative half the fix must not break: a file nobody hid keeps answering, and
    keeps answering under the SAME local name, so an agent that fetched once and read
    that name goes on reading it.

    What the fix does give up is stated here rather than hidden: the second call goes
    to the engine too. It has to — this proxy cannot tell a hidden path from an
    ordinary one without keeping a second copy of a rule that lives in the engine — so
    the round trip is the price of asking the right party, and it is asserted rather
    than quietly tolerated.
    """
    plain = "/w/base/notes.md"

    first = await srv._handle_fetch_file({"path": plain})
    second = await srv._handle_fetch_file({"path": plain})

    assert first["status"] == second["status"] == "success"
    assert second["local_path"] == first["local_path"], (
        "the local name must be stable, or an agent's earlier Read stops working"
    )
    assert second["cached"] is True
    assert gated.calls == [(plain, None), (plain, None)], (
        "both calls asked the engine: the cache stopped standing in for permission"
    )
