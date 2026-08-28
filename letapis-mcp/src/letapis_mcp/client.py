"""HTTP client for letapis-core REST API.

Uses dynamic routing from /api/v1/tools endpoint.
No hardcoded tool→endpoint mappings - everything comes from server.
"""

from __future__ import annotations

import re
import sys
from typing import Any

import httpx

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
# `reference_stats` named the stored-reference mechanism removed in Plan 36.1;
# `vector_search_nodes` is the kernel HANDLER's name — the tool has always been called
# `search`. Checked against the engine rather than from memory: `GET /api/v1/tools` on
# :3131 lists 49 tools and neither of those is among them `[проверено чтением, 26.08]`.
_RETRY_SAFE_TOOLS = frozenset(
    {
        "search",
        "blast_radius",
        "workspace_browse",
    }
)


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
        self._tool_routes: dict[str, tuple[str, str]] = {}  # name -> (method, endpoint)
        self.retry_safe_not_declared: tuple[str, ...] = ()
        """Names in `_RETRY_SAFE_TOOLS` the engine did not declare, filled by
        `_load_routes`. Empty is also the answer before any map has been built — see
        there for why an unbuilt map must not be read as «everything is dead»."""
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

    async def _load_routes(self) -> None:
        """Load tool routes from server, and check our own lists against them.

        The route map is built from `GET /api/v1/tools`, so at this moment every real
        tool name is in hand — which is the only moment `_RETRY_SAFE_TOOLS` can be
        judged at all. The proxy cannot import the kernel's registry (another tree) and
        its own tests stand up no engine, so «compare two lists inside the code» is not
        available here. Comparing OUR list against WHAT THE ENGINE ANSWERED is, and it
        costs one set difference on a call that already happened.

        Stage 58.33 found three dead names in that set by hand, one after another. A
        check that only a person performs is a check that runs when someone remembers.
        """
        try:
            result = await self.get_tools()
            tools = result.get("tools", [])

            for tool in tools:
                name = tool.get("name")
                method = tool.get("method", "POST")
                endpoint = tool.get("endpoint", "")
                if name and endpoint:
                    self._tool_routes[name] = (method, endpoint)

            # Judged only against a map that actually got built: an empty map means the
            # engine did not answer, and calling every name dead on that basis would
            # turn one outage into a page of false alarms.
            self.retry_safe_not_declared = (
                tuple(sorted(_RETRY_SAFE_TOOLS - set(self._tool_routes)))
                if self._tool_routes
                else ()
            )

            sys.stderr.write(
                f"[letapis-mcp] Loaded {len(self._tool_routes)} tool routes\n"
            )
            if self.retry_safe_not_declared:
                sys.stderr.write(
                    "[letapis-mcp] WARNING: named retry-safe but not declared by "
                    f"letapis-core: {', '.join(self.retry_safe_not_declared)}. "
                    "These names answer to nothing — a dead entry there reads as "
                    "«this tool exists and is safe to retry», and neither half is "
                    "true. Remove them from _RETRY_SAFE_TOOLS.\n"
                )
            sys.stderr.flush()
        except httpx.ConnectError:
            sys.stderr.write("[letapis-mcp] Error loading tool routes: connection refused\n")
            sys.stderr.flush()
            raise
        except Exception as e:
            sys.stderr.write(f"[letapis-mcp] Error loading tool routes: {e}\n")
            sys.stderr.flush()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool by name via REST API.

        Routes to appropriate endpoint based on tool schema from server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        # Load routes on first call
        if not self._tool_routes:
            await self._load_routes()

        if name not in self._tool_routes:
            if name in _RETRY_SAFE_TOOLS:
                # The proxy's own list disagrees with the engine, and this is the one
                # moment a person is looking straight at it. Said here rather than in
                # `letapis_status`, which is only ever listed while the engine is
                # DOWN — a fact that can only be learned from a live tool map cannot
                # be delivered by a tool that exists only when there is no map.
                return {
                    "error": f"Unknown tool: {name}",
                    "stale_proxy_list": "_RETRY_SAFE_TOOLS",
                    "message": (
                        f"'{name}' is named retry-safe by this proxy but letapis-core "
                        "does not declare it, so nothing answers to it. This is a "
                        "stale list in the proxy, not a missing engine feature — "
                        "remove the name from _RETRY_SAFE_TOOLS."
                    ),
                }
            return {"error": f"Unknown tool: {name}"}

        method, endpoint = self._tool_routes[name]

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
            except httpx.HTTPStatusError as e:
                # A live answer from core, not a stale socket — never recreate/retry.
                if e.response.status_code == 503:
                    # Expected warmup/not-ready state. letapis-core deps
                    # raise 503 while services initialize; keep the guidance
                    # in-band instead of relaying a bare HTTP error the agent
                    # reads as "this tool is broken".
                    return {
                        "status": "unavailable",
                        "message": (
                            f"letapis-core reports a service is not ready: {e.response.text}. "
                            "The server may be warming up — retry in a few seconds."
                        ),
                    }
                return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                # Stale/dead pool: a half-open keep-alive connection to a restarted
                # core hangs until timeout, and ConnectError means the connection
                # dropped. Recreate the pool so this (retry) and every future call
                # get a fresh connection — the fix for the manual-/mcp-reconnect
                # incident. Recreate is side-effect-free; only the retry is gated.
                await self._reset_pool()
                if isinstance(e, httpx.ConnectError):
                    # Routes may be stale after a reconnect — force a reload next call.
                    self._tool_routes.clear()
                if attempt + 1 < attempts:
                    continue
                # Out of retries (or a non-idempotent tool): let the MCP layer
                # shape it — long ops may still run server-side, and the pool is
                # now healthy for the next call.
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
            reveal: Hidden folders this call may read from (Stage 69.1). Left OUT of
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
