"""HTTP client for letapis-core REST API.

Uses dynamic routing from /api/v1/tools endpoint.
No hardcoded tool→endpoint mappings - everything comes from server.
"""

from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from typing import Any

import httpx

from letapis_mcp import journal
from letapis_mcp.answers import EngineUnusable, engine_failure, log_fields, outcome_of
from letapis_mcp.config import Config


# Tools whose result carries NO server-side side effect, so an automatic retry
# after a recreated (stale) pool cannot double-fire a mutation or a long
# background op. GET is idempotent by HTTP method; this set names the POST
# readers (search is the incident tool). Everything else still heals the pool on
# failure but is NOT retried — the caller gets guidance and its next call runs
# on the fresh pool.
#
# Every name here must be one the engine actually declares. Two were not, and a dead
# name in a set like this is worse than an absent one: it reads to everyone after as
# «this tool exists and is safe to retry», and neither half is true.
# `reference_stats` named a stored-reference mechanism the engine no longer has;
# `vector_search_nodes` is the kernel HANDLER's name — the tool has always been called
# `search`. Checked against the engine rather than from memory: `GET /api/v1/tools`
# lists neither of those.
_RETRY_SAFE_TOOLS = frozenset(
    {
        "search",
        "blast_radius",
        "workspace_browse",
    }
)


@dataclass(frozen=True)
class ToolList:
    """One answer of `GET /api/v1/tools`: what the agent is shown and what its calls route by.

    Both come from the same answer because two answers can differ, and then the agent is
    shown a tool its call cannot reach.
    """

    tools: tuple[dict[str, Any], ...]
    """The engine's definitions that can be called, in the engine's order, one per name."""
    routes: dict[str, tuple[str, str]]
    """name -> (method, endpoint), for exactly the definitions in `tools`."""

    @classmethod
    def from_answer(cls, answer: Any) -> ToolList:
        """The tool list in `answer`, or `EngineUnusable` when there is none to route by.

        A definition without a name or an endpoint cannot be called, so it is not shown
        either; a name served twice keeps its first definition for both.
        """
        tools = answer.get("tools") if isinstance(answer, dict) else None
        if not isinstance(tools, list) or not tools:
            raise EngineUnusable(
                "empty-tool-list" if tools == []
                else "not-an-object" if not isinstance(answer, dict)
                else "not-a-tool-list",
                "" if tools == [] else str(answer)[:200],
            )
        kept: dict[str, dict[str, Any]] = {}
        for t in tools:
            if isinstance(t, dict) and t.get("name") and t.get("endpoint"):
                kept.setdefault(t["name"], t)
        if not kept:
            raise EngineUnusable("empty-tool-list", "no tool carries a name and an endpoint")
        routes = {n: (t.get("method", "POST"), t["endpoint"]) for n, t in kept.items()}
        return cls(tuple(kept.values()), routes)

    def schema(self, name: str) -> dict[str, Any]:
        for tool in self.tools:
            if tool.get("name") == name:
                return tool.get("inputSchema") or {}
        return {}


def _coerce_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    """Arguments with numbers and booleans that arrived as strings turned into what `schema` declares.

    MCP transport may pass integers/numbers as strings; the REST API wants the type.
    """
    properties = schema.get("properties", {})
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


class letapisClient:
    """HTTP client for communicating with letapis-core server via REST API.

    Fetches tool definitions (including endpoints) dynamically from server.
    """

    def __init__(
        self,
        config: Config,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._tool_list: ToolList | None = None
        self._loading: asyncio.Future[ToolList] | None = None
        """The load in flight, which every caller arriving meanwhile waits for."""
        self.retry_safe_not_declared: tuple[str, ...] = ()
        """Names in `_RETRY_SAFE_TOOLS` the engine did not declare, filled by
        `_load_tool_list`. Empty is also the answer before any list has been loaded — an
        unloaded list must not be read as «everything is dead»."""
        # Test seam: inject an httpx.MockTransport to simulate stale/dead sockets.
        # None in production → the default transport. Preserved across _reset_pool
        # so a recreated pool keeps the same (mock) transport in tests.
        self._transport = transport

    async def __aenter__(self) -> letapisClient:
        """Enter async context."""
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        """Exit async context."""
        await self.stop()

    async def start(self) -> None:
        """Start the HTTP client."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.server.api_key:
            headers["X-API-Key"] = self.config.server.api_key

        self._client = httpx.AsyncClient(
            base_url=self.config.server.url,
            headers=headers,
            timeout=self.config.server.timeout,
            transport=self._transport,
        )

    async def stop(self) -> None:
        """Stop the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _reset_pool(self) -> None:
        """Drop the current connection pool and open a fresh one.

        A keep-alive connection to a core that restarted / died without a clean
        FIN stays 'available' in httpcore's pool, and every reuse hangs until the
        read timeout (the stale-pool incident). ``aclose()`` closes the whole
        pool; a new client opens fresh connections. Side-effect-free — safe to
        call for any failed call; only the *retry* is gated on idempotency.
        """
        await self.stop()
        await self.start()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising if not started."""
        if self._client is None:
            raise RuntimeError("Client not started. Call start() first.")
        return self._client

    # =========================================================================
    # Tool Schema & Routing
    # =========================================================================

    async def get_tools(self) -> dict[str, Any]:
        """Get tool definitions from letapis-core.

        Returns:
            Dict with 'tools' key containing list of tool definitions.
            Each tool has: name, description, inputSchema, method, endpoint.
        """
        response = await self.client.get("/api/v1/tools")
        response.raise_for_status()
        return response.json()

    async def tool_list(self) -> ToolList:
        """The engine's tool list this proxy works from, loaded on first need.

        Transport and HTTP failures propagate, and so does an answer with nothing to
        route by: either way the engine failed, and nothing is kept, so the next need
        asks again.
        """
        if self._tool_list is not None:
            return self._tool_list
        return await self._load_once()

    async def reload_tool_list(self, stale: ToolList) -> ToolList:
        """A fresh tool list in place of `stale`, however many callers found it lacking.

        The kept list stays in place while the new one loads, so a caller arriving
        meanwhile still sees the list it would have missed on, and joins the same load.
        """
        if self._loading is None and self._tool_list is not None and self._tool_list is not stale:
            return self._tool_list
        return await self._load_once()

    async def tool_list_now(self) -> ToolList:
        """The engine's tool list asked of it now, kept in place of the held one.

        A load already in flight is joined rather than doubled: it was asked after the
        caller arrived. Failures propagate, as from `tool_list`.
        """
        return await self._load_once()

    def kept_tool_list(self) -> ToolList | None:
        """The tool list held now, without asking the engine; `None` when none is held."""
        return self._tool_list

    def forget_tool_list(self) -> None:
        """Drop the tool list; the next need loads a fresh one."""
        self._tool_list = None

    async def _load_once(self) -> ToolList:
        """The load in flight, or a new one: callers arriving together share one request."""
        if self._loading is None:
            self._loading = asyncio.ensure_future(self._load_and_keep())
        # Shielded: one caller cancelled must not cancel the load the others wait for.
        return await asyncio.shield(self._loading)

    async def _load_and_keep(self) -> ToolList:
        try:
            self._tool_list = await self._load_tool_list()
            return self._tool_list
        finally:
            self._loading = None

    async def _load_tool_list(self) -> ToolList:
        """One `GET /api/v1/tools`, and our own retry-safe names checked against it.

        This is the only moment every real tool name is in hand, so the only moment
        `_RETRY_SAFE_TOOLS` can be judged at all: the proxy cannot import the kernel's
        registry, and a check that only a person performs runs when someone remembers.
        """
        tool_list = ToolList.from_answer(await self.get_tools())

        self.retry_safe_not_declared = tuple(sorted(_RETRY_SAFE_TOOLS - set(tool_list.routes)))

        sys.stderr.write(
            f"[letapis-mcp] Loaded {len(tool_list.routes)} tool routes\n"
        )
        if self.retry_safe_not_declared:
            sys.stderr.write(
                "[letapis-mcp] WARNING: named retry-safe but not declared by "
                f"letapis-core: {', '.join(self.retry_safe_not_declared)}. "
                "Either this proxy's key does not reach them, or the names are dead — "
                "a dead entry there reads as «this tool exists and is safe to retry», "
                "and neither half is true. Then remove them from _RETRY_SAFE_TOOLS.\n"
            )
        sys.stderr.flush()
        return tool_list

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call the engine's tool `name`, routed by the same tool list the agent is shown.

        A name missing from that list asks the engine for a fresh one once: an earlier
        answer may have been incomplete, and the list is otherwise kept until the
        connection fails.
        """
        try:
            before = self._tool_list
            tool_list = await self.tool_list()
            # A list this call waited for is already fresh; only one it found kept is reloaded.
            if name not in tool_list.routes and tool_list is before:
                tool_list = await self.reload_tool_list(tool_list)
        except Exception as e:
            # Answered as a failure of the tool list: nothing was started, and the name
            # was never looked up.
            if (outcome := outcome_of(e)) is None:
                raise
            journal.record(self.config.server.url, "tool map", log_fields(outcome))
            return engine_failure(
                outcome, url=self.config.server.url, asked_for="its tool list"
            )

        if name not in tool_list.routes:
            if name in _RETRY_SAFE_TOOLS:
                # A name this proxy knows the engine has, missing from a list fetched just
                # now: the engine does not serve it to this proxy, and a key restricted to
                # some tools is the one way that happens.
                return {
                    "status": "not_served",
                    "message": (
                        f"letapis-core at {self.config.server.url} does not list '{name}' "
                        "among the tools it serves to this proxy, so the call was not made. "
                        "A key limited to some tools leaves the rest out; ask the user "
                        "which key this proxy uses and what it allows."
                    ),
                }
            return {"error": f"Unknown tool: {name}"}

        arguments = _coerce_arguments(tool_list.schema(name), arguments)
        method, endpoint = tool_list.routes[name]

        # Handle URL parameters (e.g., /api/v1/research/graphs/{scope_id}).
        # Substituted ONCE here: it pops from `arguments`, so it must not run
        # again on a retry (the params would already be gone).
        endpoint = self._substitute_url_params(endpoint, arguments)

        # Retry only pure reads: a recreated pool must never re-fire a mutation
        # or a long background op (index_folder, deep_index) — that would double
        # the work server-side. GET is idempotent by method; the explicit
        # set covers the POST readers (search — the incident tool).
        retry_safe = method == "GET" or name in _RETRY_SAFE_TOOLS
        attempts = 2 if retry_safe else 1

        for attempt in range(attempts):
            try:
                if method == "GET":
                    response = await self.client.get(endpoint, params=arguments or None)
                elif method == "POST":
                    response = await self.client.post(endpoint, json=arguments)
                elif method == "PATCH":
                    response = await self.client.patch(endpoint, json=arguments)
                elif method == "DELETE":
                    # Through `request`, because `client.delete()` takes no body at
                    # all: the old call dropped every argument that had not already
                    # been substituted into the URL, and dropped it silently — the
                    # answer came back successful with the narrowing gone. The branch
                    # is dead today (the engine declares no DELETE tool), so this is
                    # a trap being closed, not a symptom being treated: the first
                    # tool declared on this method would have lost its arguments with
                    # nowhere to learn it from.
                    response = await self.client.request(
                        "DELETE", endpoint, json=arguments
                    )
                else:
                    return {"error": f"Unsupported method: {method}"}

                response.raise_for_status()
                return response.json()
            except (httpx.HTTPStatusError, ValueError) as e:
                # A live answer from core, not a stale socket — never recreate/retry.
                outcome = outcome_of(e)
                if outcome is None:
                    return {"error": str(e)}
                journal.record(self.config.server.url, f"call {name}", log_fields(outcome))
                return engine_failure(
                    outcome, url=self.config.server.url, asked_for=f"'{name}'"
                )
            except httpx.TransportError as e:
                # Stale/dead pool: a half-open keep-alive connection to a restarted
                # core hangs until timeout or is dropped mid-request, and ConnectError
                # means nothing is listening. Recreate the pool so this (retry) and every
                # future call get a fresh connection — the fix for the manual-/mcp-reconnect
                # incident. Recreate is side-effect-free; only the retry is gated.
                await self._reset_pool()
                if isinstance(e, httpx.ConnectError):
                    # The tool list may be stale after a reconnect — reload on next need.
                    self.forget_tool_list()
                if attempt + 1 < attempts:
                    continue
                if retry_safe:
                    # A read retried on a fresh pool and still unanswered: nothing is
                    # running server-side, so the engine is simply not answering.
                    outcome = outcome_of(e)
                    journal.record(self.config.server.url, f"call {name}", log_fields(outcome))
                    return engine_failure(
                        outcome, url=self.config.server.url, asked_for=f"'{name}'"
                    )
                # A non-idempotent tool: let the MCP layer shape it — long ops may
                # still run server-side, and the pool is now healthy for the next call.
                raise
            except Exception as e:
                return {"error": str(e)}

    def _substitute_url_params(self, endpoint: str, arguments: dict[str, Any]) -> str:
        """Substitute {param} placeholders in endpoint with argument values.

        E.g., /api/v1/research/graphs/{scope_id} with arguments={"scope_id": "abc"}
        becomes /api/v1/research/graphs/abc

        Args:
            endpoint: URL template with {param} placeholders
            arguments: Arguments dict

        Returns:
            Endpoint with substituted values
        """
        # Find all {param} patterns
        pattern = r"\{(\w+)\}"

        def replace(match: re.Match) -> str:
            param_name = match.group(1)
            if param_name in arguments:
                value = arguments.pop(param_name)  # Remove from arguments
                return str(value)
            return match.group(0)  # Keep original if not found

        return re.sub(pattern, replace, endpoint)

    # =========================================================================
    # File Content (special case - returns bytes, not JSON)
    # =========================================================================

    async def fetch_file(self, path: str, reveal: list[str] | None = None) -> bytes:
        """Fetch file content from letapis-core.

        Args:
            path: Remote file path
            reveal: Hidden folders this call may read from. Left OUT of
                the query string when nothing was asked for, rather than sent empty:
                the route reads an absent parameter as «the originals» and would have
                to be taught to read a blank one the same way, in a second place.

        Returns:
            File content as bytes
        """
        params: dict[str, Any] = {"path": path}
        if reveal:
            params["reveal"] = reveal
        response = await self.client.get(
            "/api/v1/files/content",
            params=params,
        )
        response.raise_for_status()
        return response.content
