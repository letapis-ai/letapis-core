"""Stale keep-alive pool auto-recovery.

The incident this pins: after letapis-core restarted under the panel, the
persistent httpx.AsyncClient kept a half-open keep-alive connection in
httpcore's pool. It was neither is_closed() (no FIN/EOF received) nor
has_expired() (within keepalive_expiry), so every reuse wrote to a dead socket
and hung until the 60s read timeout — search timed out 3x until a manual /mcp
reconnect built a fresh pool.

The fix: on ConnectError / TimeoutException recreate the client (drop the
stale pool → fresh connections) and retry ONCE, but only for read-only tools —
a mutation / long background op (index_folder, deep_index) must never be
double-fired. Reproduced deterministically with a stateful
httpx.MockTransport handler (fail first, succeed second).
"""
from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from letapis_mcp.client import letapisClient


def _cfg():
    return SimpleNamespace(
        server=SimpleNamespace(url="http://test", api_key=None, timeout=5)
    )


async def _make_client(handler, routes):
    """Real letapisClient over a MockTransport (test seam) with preloaded routes."""
    c = letapisClient(_cfg(), transport=httpx.MockTransport(handler))
    await c.start()
    c._tool_routes = routes
    return c


@pytest.mark.asyncio
async def test_search_recovers_after_stale_timeout():
    """T1: a read tool that hits a stale ReadTimeout recreates the pool and
    retries, returning the recovered result — no manual reconnect."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("stale socket", request=request)
        return httpx.Response(200, json={"status": "success"})

    c = await _make_client(handler, {"search": ("POST", "/api/v1/search")})
    first_pool = c.client
    result = await c.call_tool("search", {"query": "x"})

    assert result == {"status": "success"}
    assert calls["n"] == 2  # retried once after recreate
    assert c.client is not first_pool  # stale pool dropped, fresh client
    await c.stop()


@pytest.mark.asyncio
async def test_index_folder_not_retried_on_timeout():
    """T2 (destructive): a long/mutating op that times out is NOT retried —
    the pool still heals, but the operation is never double-fired server-side."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("long op or stale", request=request)

    c = await _make_client(handler, {"index_folder": ("POST", "/api/v1/index_folder")})
    with pytest.raises(httpx.TimeoutException):
        await c.call_tool("index_folder", {"path": "/x"})

    assert calls["n"] == 1  # exactly one hit — no double index
    await c.stop()


@pytest.mark.asyncio
async def test_connect_error_recovers_and_clears_routes():
    """T3: ConnectError on a read tool recreates the pool, clears the route
    cache, and retries — handled consistently with TimeoutException."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, json={"ok": True})

    c = await _make_client(handler, {"search": ("POST", "/api/v1/search")})
    result = await c.call_tool("search", {"query": "x"})

    assert result == {"ok": True}
    assert calls["n"] == 2
    assert c._tool_routes == {}  # ConnectError invalidates the cached routes
    await c.stop()


@pytest.mark.asyncio
async def test_connect_error_mutation_not_retried():
    """T4: ConnectError on a mutation recreates + clears routes but does NOT retry."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("connection refused", request=request)

    c = await _make_client(handler, {"remove_folder": ("POST", "/api/v1/remove")})
    with pytest.raises(httpx.ConnectError):
        await c.call_tool("remove_folder", {"path": "/x"})

    assert calls["n"] == 1  # not retried
    assert c._tool_routes == {}
    await c.stop()


@pytest.mark.asyncio
async def test_normal_search_no_recreate():
    """T5: a healthy call succeeds on the first try — no recreate, no extra
    round-trip, latency-neutral."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"status": "ok"})

    c = await _make_client(handler, {"search": ("POST", "/api/v1/search")})
    first_pool = c.client
    result = await c.call_tool("search", {"query": "x"})

    assert result == {"status": "ok"}
    assert calls["n"] == 1
    assert c.client is first_pool  # untouched on success
    await c.stop()


@pytest.mark.asyncio
async def test_get_tool_retried_by_method():
    """T6: a GET tool is retry-safe by HTTP method (idempotent) even without being
    in the explicit set — recovers from a stale timeout."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("stale", request=request)
        return httpx.Response(200, json={"op": "done"})

    c = await _make_client(
        handler, {"get_operation": ("GET", "/api/v1/operations/{operation_id}")}
    )
    result = await c.call_tool("get_operation", {"operation_id": "abc"})

    assert result == {"op": "done"}
    assert calls["n"] == 2
    await c.stop()


@pytest.mark.asyncio
async def test_unlisted_mutation_not_retried():
    """T7: a POST tool not in the retry-safe set (a mutation) is not retried on a
    stale timeout — the idempotency boundary holds for unknown mutations."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("stale", request=request)

    c = await _make_client(handler, {"forget_document": ("POST", "/api/v1/forget")})
    with pytest.raises(httpx.TimeoutException):
        await c.call_tool("forget_document", {"path": "/x", "reason": "y"})

    assert calls["n"] == 1
    await c.stop()
