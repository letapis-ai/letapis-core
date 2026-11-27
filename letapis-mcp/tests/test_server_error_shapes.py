"""Error-shape contract for the MCP proxy.

The lesson this pins: 1-2 `isError: true` early in a session and the
agent abandons the tool entirely. Every expected/recoverable condition
(letapis-core down, timeout, probe tool) must return a SUCCESS-shaped result
carrying guidance. The degraded tool list must never be cached — a session
started before letapis-core comes up must recover without a client restart.
"""
from __future__ import annotations

import httpx
import pytest

import letapis_mcp.server as srv
from tests import handlers
from letapis_mcp.client import ToolList


class FakeClientDown:
    async def tool_list(self):
        raise httpx.ConnectError("connection refused")

    async def tool_list_now(self):
        raise httpx.ConnectError("connection refused")

    async def call_tool(self, name, arguments):
        raise httpx.ConnectError("connection refused")

    def forget_tool_list(self):
        pass

    def kept_tool_list(self):
        return None


class FakeClientUp:
    def __init__(self):
        self.tools = [
            {"name": "search", "endpoint": "/api/v1/search", "description": "d", "inputSchema": {"type": "object"}}
        ]

    async def tool_list(self):
        return ToolList.from_answer({"tools": self.tools})

    async def call_tool(self, name, arguments):
        return {"status": "success"}


class FakeClientTimeout:
    async def call_tool(self, name, arguments):
        raise httpx.ReadTimeout("timed out")

    def kept_tool_list(self):
        return None


@pytest.mark.asyncio
async def test_list_tools_degraded_fallback_is_not_cached(monkeypatch):
    """F1: core down at first list_tools must NOT poison the cache forever."""
    monkeypatch.setattr(srv, "_client", FakeClientDown())
    degraded = await handlers.list_tools()
    names = {t.name for t in degraded}
    assert "letapis_status" in names
    assert "fetch_file" in names

    # core comes back up — the next list_tools must return the real surface
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    recovered = await handlers.list_tools()
    names = {t.name for t in recovered}
    assert "search" in names
    assert "letapis_status" not in names


@pytest.mark.asyncio
async def test_connect_error_on_call_is_success_shaped(monkeypatch):
    """F2: core down during a call → guidance, never isError."""
    monkeypatch.setattr(srv, "_client", FakeClientDown())
    result = await handlers.call_tool("search", {"query": "x"})
    assert not result.model_dump(by_alias=True).get("isError")
    text = result.content[0].text
    assert "unavailable" in text.lower()
    # guidance, not a bare error: tells the agent the path to recovery
    assert "retry" in text.lower() or "start" in text.lower()


@pytest.mark.asyncio
async def test_timeout_is_success_shaped_with_progress_hint(monkeypatch):
    """F2: timeout on long ops (index_folder/deep_index) is expected."""
    monkeypatch.setattr(srv, "_client", FakeClientTimeout())
    result = await handlers.call_tool("deep_index", {"path": "/x"})
    assert not result.model_dump(by_alias=True).get("isError")
    text = result.content[0].text
    assert "get_indexing_progress" in text


@pytest.mark.asyncio
async def test_generic_exception_is_success_shaped(monkeypatch):
    class FakeBoom:
        async def call_tool(self, name, arguments):
            raise ValueError("boom")

        def kept_tool_list(self):
            return None

    monkeypatch.setattr(srv, "_client", FakeBoom())
    result = await handlers.call_tool("search", {"query": "x"})
    assert not result.model_dump(by_alias=True).get("isError")
    assert "boom" in result.content[0].text


@pytest.mark.asyncio
async def test_letapis_status_probe_is_success_shaped(monkeypatch):
    monkeypatch.setattr(srv, "_config", None)
    monkeypatch.setattr(srv, "_client", FakeClientDown())
    result = await handlers.call_tool("letapis_status", {})
    assert not result.model_dump(by_alias=True).get("isError")
    assert "letapis-core" in result.content[0].text
    assert "connection refused" in result.content[0].text


@pytest.mark.asyncio
async def test_client_shapes_503_as_unavailable_guidance():
    """One choke point covers every letapis-core dep that 503s during warmup."""
    from types import SimpleNamespace

    from letapis_mcp.client import letapisClient

    cfg = SimpleNamespace(server=SimpleNamespace(url="http://test", api_key=None, timeout=5))
    c = letapisClient(cfg)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Search service not available")

    c._client = httpx.AsyncClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    c._tool_list = ToolList.from_answer(
        {"tools": [{"name": "search", "method": "POST", "endpoint": "/api/v1/search"}]}
    )

    result = await c.call_tool("search", {"query": "x"})
    assert result["status"] == "unavailable"
    assert "retry" in result["message"].lower()
