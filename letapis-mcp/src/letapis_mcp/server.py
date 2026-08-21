"""letapis MCP Server.

MCP server that proxies requests to letapis-core REST API.
Uses low-level Server API for dynamic tool registration.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx
import mcp.server.stdio
from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from letapis_mcp.client import letapisClient
from letapis_mcp.config import Config
from letapis_mcp.paths import PathHandler

# Global state (initialized on startup)
_client: letapisClient | None = None
_paths: PathHandler | None = None
_config: Config | None = None
_tools_cache: list[types.Tool] = []


# The key a client reads to keep one tool's description loaded while the rest of the
# server's surface is deferred. Set per tool, it works independently of the
# server-level `alwaysLoad` in the client's MCP config.
ALWAYS_LOAD_META: dict[str, Any] = {"anthropic/alwaysLoad": True}


#: Tools whose descriptions stay in the caller's window from the first second.
#:
#: The rest of the surface is deferred: the caller sees the names and fetches a
#: description when it decides to call one. That trade is only worth making if the
#: pinned few are the ones actually reached for, so the list comes from telemetry
#: rather than taste. Over the 14 days to 2026-08-20, across the domain's heads:
#:
#:     blast_radius     693 calls
#:     search           660
#:     list_folders      44
#:     ena_get_context   17
#:     everything else   single figures
#:
#: `search` and `blast_radius` are 95% of all calls to the server.
#:
#: The boundary of that measurement, which matters before anyone re-derives the
#: list: only heads with telemetry on are counted. Calls from codex heads and from
#: sessions without OTEL are not in it, so the tail is undercounted rather than
#: absent — a tool being low here is weaker evidence than a tool being high.
#:
#: `ena_get_context` is the third name, and it is NOT there on that count. Its 17
#: calls are stated above rather than hidden, and they argue against it. They are
#: not the reason, because they measure the wrong thing: the window they were
#: recorded in showed memory next to everything else, so they say how heads
#: BEHAVED, not whether recall is worth reaching for. A head cannot ask "did we
#: decide this before" until it knows the question is askable, and the description
#: is where it learns that. The owner decided on 2026-08-20 that recall belongs in
#: the window regardless of the count; whether the count then moves is the real
#: measurement, and the same query a week after this change is what answers it.
#:
#: Adding a name costs its description in every session of every head that mounts
#: this proxy, forever. The whole surface is 13 851 characters and `search` alone is
#: 1 873 of them, so this list is short on purpose. `ena_get_context` costs 59
#: characters (`Recall episodic memories (decisions, milestones, insights).`),
#: which is why a name this thin on calls can still be worth pinning — and why the
#: same argument does not carry over to a description ten times its size.
#:
#: One name from the memory group, not the group. The engine serves eight `ena_`
#: tools; the other seven write, correct, forget, audit, or read memory along one
#: narrow axis (a time window, the forgotten list), and a head reaches for those
#: knowing already what it wants. Only this one is how a head remembers at all, so
#: only this one has to be visible before the head thinks to look.
ALWAYS_LOADED: tuple[str, ...] = ("search", "blast_radius", "ena_get_context")


# Local tool definition for fetch_file (handled by letapis-mcp, not letapis-core)
FETCH_FILE_TOOL = types.Tool(
    name="fetch_file",
    description="""Fetch file from letapis-core and cache locally.

Use when Read tool fails on a path from search results.

Args:
    path: Remote file path

Returns:
    Local path to cached file
""",
    inputSchema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Remote file path"},
        },
        "required": ["path"],
    },
)


def get_client() -> letapisClient:
    """Get the HTTP client."""
    if _client is None:
        raise RuntimeError("Client not initialized")
    return _client


def get_paths() -> PathHandler:
    """Get the path handler."""
    if _paths is None:
        raise RuntimeError("Paths not initialized")
    return _paths


# Create low-level MCP server
server = Server("letapis")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools, fetched dynamically from letapis-core."""
    global _tools_cache

    # Return cached tools if available
    if _tools_cache:
        return _tools_cache

    # Fetch from letapis-core
    try:
        result = await get_client().get_tools()
        tools = result.get("tools", [])

        _tools_cache = [
            types.Tool(
                name=t["name"],
                description=t.get("description", ""),
                inputSchema=t.get("inputSchema", {"type": "object"}),
                # Passed through rather than derived here: destructiveness is the
                # engine's statement about its own tool, and a second opinion in
                # the proxy is one more place to drift. Absent upstream stays
                # absent — `None` keeps the field off the wire entirely, so a
                # client reading the key gets no answer instead of a false one.
                annotations=t.get("annotations"),
                # A fresh dict per tool: one shared mapping would let a client or a
                # later edit mutate every marked tool at once.
                _meta=dict(ALWAYS_LOAD_META) if t["name"] in ALWAYS_LOADED else None,
            )
            for t in tools
        ]

        # Add local-only tools (handled by letapis-mcp, not letapis-core)
        _tools_cache.append(FETCH_FILE_TOOL)

        # A pinned name the engine no longer serves is the quiet failure this
        # guards: the proxy keeps working, the caller keeps its window, and the tool
        # meant to stay loaded has become deferred with nobody told. Renames happen
        # engine-side, where this file is not read.
        served = {t["name"] for t in tools} | {FETCH_FILE_TOOL.name}
        unknown = [name for name in ALWAYS_LOADED if name not in served]
        if unknown:
            sys.stderr.write(
                f"[letapis-mcp] WARNING: always-loaded names not served by letapis-core: "
                f"{', '.join(unknown)} — they are deferred like everything else. "
                f"Renamed or removed upstream? Fix ALWAYS_LOADED in server.py\n"
            )

        # Say which names were actually pinned, not just how many tools loaded:
        # the pair (list, engine surface) is what decides it, and both move.
        pinned_note = ", ".join(sorted(set(ALWAYS_LOADED) & served)) or "none"
        sys.stderr.write(
            f"[letapis-mcp] Loaded {len(_tools_cache)} tools ({len(tools)} from letapis-core "
            f"+ 1 local), always-loaded: {pinned_note}\n"
        )
        sys.stderr.flush()

        return _tools_cache
    except Exception as e:
        sys.stderr.write(f"[letapis-mcp] Error fetching tools: {e}\n")
        sys.stderr.flush()
        url = _config.server.url if _config else "unknown"
        # Degraded surface is NOT cached: a session that starts before
        # letapis-core is up must recover on the next tools/list request
        # instead of being stuck with the probe tool forever.
        return [
            types.Tool(
                name="letapis_status",
                description=(
                    f"letapis-core is UNAVAILABLE at {url}. "
                    f"Error: {e}. "
                    "All letapis tools are offline. "
                    "Ask the user to check that letapis-core is running."
                ),
                inputSchema={"type": "object", "properties": {}},
                # Pinned unconditionally, and not via ALWAYS_LOADED: this tool
                # IS its description. The address and the error live nowhere else,
                # so a deferred one leaves the caller a bare name at the exact
                # moment it is already confused — and one more call to learn why is
                # how an agent decides letapis is not worth the trouble and leaves
                # for grep (the reason the whole surface is success-shaped, above).
                # It costs nothing while the engine is up: then this tool does not
                # exist. Frequency, which decides ALWAYS_LOADED, does not apply to a
                # message that only ever appears when something is wrong.
                _meta=dict(ALWAYS_LOAD_META),
            ),
            FETCH_FILE_TOOL,
        ]


def _coerce_arguments(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Coerce argument types based on tool's inputSchema.

    MCP transport may pass integers/numbers as strings.
    This converts them to proper types before sending to REST API.
    """
    for tool in _tools_cache:
        if tool.name == name:
            properties = tool.inputSchema.get("properties", {})
            break
    else:
        return arguments

    coerced = {}
    for key, value in arguments.items():
        if key in properties:
            prop_type = properties[key].get("type")
            try:
                if prop_type == "integer" and isinstance(value, str):
                    value = int(value)
                elif prop_type == "number" and isinstance(value, str):
                    value = float(value)
                elif prop_type == "boolean" and isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
            except (ValueError, TypeError):
                pass
        coerced[key] = value
    return coerced


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
    """Handle tool calls by proxying to letapis-core REST API."""

    # Status probe tool (returned when letapis-core is down).
    # Success-shaped: an expected/recoverable state must not be
    # isError — early isError teaches the agent to abandon letapis entirely.
    if name == "letapis_status":
        return _to_call_result(_core_unavailable_result())

    # Special handling for fetch_file (needs local path handling)
    if name == "fetch_file":
        try:
            result = await _handle_fetch_file(arguments)
            return _to_call_result(result)
        except httpx.ConnectError:
            _tools_cache.clear()
            return _to_call_result(_core_unavailable_result())

    # Coerce types before proxying
    arguments = _coerce_arguments(name, arguments)

    # Proxy to letapis-core
    try:
        result = await get_client().call_tool(name, arguments)

        # Transform search results to add local paths
        if name in ("search", "vector_search_nodes"):
            result = _transform_search_results(result)

        return _to_call_result(result)

    except httpx.ConnectError:
        _tools_cache.clear()
        return _to_call_result(_core_unavailable_result())
    except httpx.TimeoutException as e:
        return _to_call_result({
            "status": "timeout",
            "message": (
                f"letapis-core did not answer in time for '{name}': {e}. "
                "Long operations (index_folder, deep_index, force_reindex) may still be "
                "running server-side — check get_indexing_progress before retrying."
            ),
        })
    except Exception as e:
        return _to_call_result({
            "status": "error",
            "message": (
                f"Unexpected proxy error calling letapis-core for '{name}': {e}. "
                "Retry once; if it persists, report it to the user instead of "
                "falling back to manual search."
            ),
        })


def _core_unavailable_result() -> dict[str, Any]:
    """Success-shaped guidance for the expected 'letapis-core is down' state."""
    url = _config.server.url if _config else "unknown"
    return {
        "status": "unavailable",
        "message": (
            f"letapis-core is not reachable at {url} (connection refused). "
            "This is recoverable: ask the user to start letapis-core, then retry "
            "the original call — the tool list refreshes automatically."
        ),
    }


async def _handle_fetch_file(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle fetch_file tool - fetch from letapis-core and cache locally."""
    path = arguments.get("path", "")
    if not path:
        return {"status": "error", "error": "Path required"}

    paths = get_paths()

    # Check if already cached or mapped
    local_path = paths.resolve_path(path)
    if local_path != path:
        return {
            "status": "success",
            "local_path": local_path,
            "cached": True,
        }

    # Fetch from server
    try:
        content = await get_client().fetch_file(path)
        cache_path = paths.save_to_cache(path, content)
        return {
            "status": "success",
            "local_path": str(cache_path),
            "size": len(content),
            "cached": True,
        }
    except httpx.ConnectError:
        raise
    except Exception as e:
        # Actionable guidance: the path usually comes from a
        # search result — a miss means it's stale or mistyped, not that the
        # tool is broken. Steer the agent back to search, not to grep.
        return {
            "status": "error",
            "error": str(e),
            "path": path,
            "hint": (
                "Could not fetch this path. It should come verbatim from a "
                "letapis search result — re-run search to get a current path, or "
                "check list_folders that the file is indexed."
            ),
        }


def _to_call_result(result: dict[str, Any]) -> types.CallToolResult:
    """Convert dict result to CallToolResult."""
    text = json.dumps(result, indent=2, ensure_ascii=False)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
    )


def _transform_search_results(result: dict[str, Any]) -> dict[str, Any]:
    """Transform search results, mapping paths to local where possible.

    Works with both compact (path only) and verbose (path + absolute_path) formats.
    Adds local_path only when it differs from path (i.e., mapping found).
    """
    paths = get_paths()
    if "results" in result:
        for item in result["results"]:
            # Compact uses "path", verbose also has "absolute_path"
            path = item.get("absolute_path") or item.get("path")
            if path:
                local = paths.resolve_path(path)
                if local != path:
                    item["local_path"] = local
    return result


# =============================================================================
# Entry Point
# =============================================================================


async def _async_main(config_path: str | None = None) -> None:
    """Async initialization and run."""
    global _client, _paths, _config, _tools_cache

    # Load config
    _config = Config.load(config_path=config_path)

    # Initialize path handler
    _paths = PathHandler(_config)
    _paths.init_cache()

    # Initialize HTTP client
    _client = letapisClient(_config)
    await _client.start()

    # Probe the backend for a friendly startup log, but NEVER exit on failure:
    # a session that starts before letapis-core must still get the MCP
    # server — list_tools serves the degraded letapis_status surface and
    # recovers automatically once the backend comes up. Exiting here left the
    # session with no letapis server at all, unrecoverable without a restart.
    try:
        result = await _client.get_tools()
        tool_count = len(result.get("tools", []))
        sys.stderr.write(
            f"[letapis-mcp] Backend OK: {_config.server.url} ({tool_count} tools)\n"
        )
    except Exception as e:
        sys.stderr.write(
            f"[letapis-mcp] WARNING: Backend unreachable at {_config.server.url}: {e}. "
            "Starting anyway — tools will load when letapis-core comes up.\n"
        )
    sys.stderr.flush()

    # Clear tools cache to force reload
    _tools_cache = []

    try:
        # Run MCP server with stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="letapis",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    finally:
        await _client.stop()


def main() -> None:
    """Run the MCP server."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="letapis MCP Server")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to config file (YAML). Overrides LETAPIS_CONFIG env var.",
    )
    args = parser.parse_args()

    # Log startup
    sys.stderr.write("[letapis-mcp] Starting with dynamic tool schema...\n")
    sys.stderr.flush()

    asyncio.run(_async_main(config_path=args.config))


if __name__ == "__main__":
    main()
