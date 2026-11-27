"""The proxy's request handlers called the way the SDK calls them: with a context that carries the session."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from mcp import types

import letapis_mcp.server as srv


class Session:
    """What the handlers keep of the host's connection: it counts the notifications sent through it."""

    def __init__(self) -> None:
        self.list_changed = 0

    async def send_tool_list_changed(self) -> None:
        self.list_changed += 1


def context() -> Any:
    return SimpleNamespace(session=Session())


async def list_tools() -> list[types.Tool]:
    return (await srv.list_tools(context(), None)).tools


async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
    return await srv.call_tool(
        context(), types.CallToolRequestParams(name=name, arguments=arguments)
    )
