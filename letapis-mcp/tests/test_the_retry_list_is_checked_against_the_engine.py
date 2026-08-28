"""The proxy's own list of retry-safe tools is judged against what the engine answered.

Stage 58.33 found three names in `_RETRY_SAFE_TOOLS` that answer to nothing —
`reference_stats` (a mechanism removed in Plan 36.1), `vector_search_nodes` (the kernel
HANDLER's name; the tool has always been `search`), and before them `build_refs` on the
settings surface, which is the same disease one floor up. All three were found by a
person looking. A check only a person performs runs when someone remembers.

**Why not «compare two lists in the code».** The proxy cannot import the kernel's
registry — it is another tree and another package — and these tests stand up no engine.
That is the wall the first attempt hit.

**What is available instead.** The proxy already asks the engine for every tool name at
startup, to build `tool -> (method, endpoint)`. At that moment the true set is in hand,
so the comparison is ours-against-theirs and it costs one set difference on a call that
was going to happen anyway.

And the map is DATA, so this needs no engine either: hand `get_tools` an answer with the
name missing and see what the proxy says; hand it a complete one and require silence.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from letapis_mcp.client import _RETRY_SAFE_TOOLS, letapisClient


def _cfg():
    return SimpleNamespace(
        server=SimpleNamespace(url="http://test", api_key=None, timeout=5)
    )


def _registry(names: list[str]) -> httpx.MockTransport:
    """An engine whose tool registry declares exactly `names`."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "tools": [
                {"name": n, "method": "POST", "endpoint": f"/api/v1/{n}"}
                for n in names
            ]
        })

    return httpx.MockTransport(handler)


async def _loaded(names: list[str]) -> letapisClient:
    client = letapisClient(_cfg(), transport=_registry(names))
    await client.start()
    await client._load_routes()
    return client


@pytest.mark.asyncio
async def test_a_name_the_engine_does_not_declare_is_named(capsys):
    """The whole set minus one — and the one is reported, by name."""
    victim = "search"
    served = sorted(_RETRY_SAFE_TOOLS - {victim}) + ["list_folders"]

    client = await _loaded(served)

    assert client.retry_safe_not_declared == (victim,)
    assert victim in capsys.readouterr().err, (
        "the dead name never reached the log — the only place a person sees it at "
        "the moment it becomes knowable"
    )


@pytest.mark.asyncio
async def test_a_list_that_agrees_with_the_engine_says_nothing(capsys):
    """The other half, and without it the first is satisfied by a proxy that calls
    every name dead. A warning that fires always is read once and skipped for good."""
    client = await _loaded(sorted(_RETRY_SAFE_TOOLS) + ["list_folders"])

    assert client.retry_safe_not_declared == ()
    assert "WARNING" not in capsys.readouterr().err


@pytest.mark.asyncio
async def test_an_engine_that_answered_nothing_is_not_read_as_every_name_dead(capsys):
    """An outage is one fault, not a page of them.

    With no map built, the difference against an empty set is the whole list — so the
    naive check turns «letapis-core is down» into «every tool you named is dead», which
    is false and, worse, indistinguishable from the true report it imitates.
    """
    client = letapisClient(_cfg(), transport=_registry([]))
    await client.start()
    await client._load_routes()

    assert client.retry_safe_not_declared == ()
    assert "WARNING" not in capsys.readouterr().err


@pytest.mark.asyncio
async def test_calling_a_stale_name_says_the_proxy_is_stale_not_the_engine():
    """The askable half, delivered where a person is already looking.

    Not in `letapis_status`: that tool is only ever listed while the engine is DOWN, and
    a fact learned from a live tool map cannot be carried by a tool that exists only
    when there is no map.
    """
    victim = "search"
    client = await _loaded(sorted(_RETRY_SAFE_TOOLS - {victim}))

    answer = await client.call_tool(victim, {})

    assert answer["stale_proxy_list"] == "_RETRY_SAFE_TOOLS"
    assert victim in answer["message"]
    assert "proxy" in answer["message"].lower()


@pytest.mark.asyncio
async def test_an_ordinary_unknown_tool_is_not_blamed_on_the_proxy_list():
    """The negative twin: a name nobody ever claimed was retry-safe gets the plain
    answer. Blaming the proxy's list for every unknown name would send the next reader
    to edit a list the name was never in."""
    client = await _loaded(sorted(_RETRY_SAFE_TOOLS))

    answer = await client.call_tool("zzz_never_existed", {})

    assert answer["error"] == "Unknown tool: zzz_never_existed"
    assert "stale_proxy_list" not in answer


def test_the_list_names_only_tools_this_proxy_could_reach():
    """A cheap standing check on the shape of the set itself.

    It cannot say whether a name is live — that needs the engine — but it can say the
    set has not grown a non-name, which is how `vector_search_nodes` (a handler, not a
    tool) got in.
    """
    assert all(n and n.islower() and " " not in n for n in _RETRY_SAFE_TOOLS)
    assert "handle_" not in " ".join(_RETRY_SAFE_TOOLS)
