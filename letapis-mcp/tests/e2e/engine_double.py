"""A loopback stand-in for letapis-core, and the proxy started against it the way a host starts it.

The proxy is a real process speaking MCP over stdio; the only thing a probe chooses is what
the engine answers on the wire. Nothing in the proxy is replaced.
"""
from __future__ import annotations

import json
import socket
import sys
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TOOLS = "/api/v1/tools"
SEARCH = "/api/v1/search"
CONTENT = "/api/v1/files/content"
INDEX = "/api/v1/index_folder"

REGISTRY = {
    "tools": [
        {"name": "search", "method": "POST", "endpoint": SEARCH,
         "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}},
        {"name": "list_folders", "method": "GET", "endpoint": "/api/v1/folders",
         "inputSchema": {"type": "object"}},
        {"name": "index_folder", "method": "POST", "endpoint": INDEX,
         "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    ]
}
SEARCH_ANSWER = {"status": "success", "results": []}

#: Seconds the proxy waits for the engine; the probes' timeouts are this number, not a sleep.
PROXY_TIMEOUT = 0.5


@dataclass(frozen=True)
class Reply:
    """An HTTP answer the engine gives."""

    code: int
    body: bytes
    content_type: str = "application/json"

    @classmethod
    def json(cls, code: int, value: Any) -> Reply:
        return cls(code, json.dumps(value).encode())

    @classmethod
    def text(cls, code: int, value: str) -> Reply:
        return cls(code, value.encode(), "text/plain")


HANG = "hang"
"""The engine reads the request and never answers it."""

DROP = "drop"
"""The engine closes the connection without answering."""


@dataclass
class Request:
    path: str
    method: str
    fresh: bool
    """True when the connection was opened after the latest `EngineDouble.go_stale()`."""


Script = Callable[[Request], Any]


def healthy(request: Request) -> Any:
    if request.path == TOOLS:
        return Reply.json(200, REGISTRY)
    if request.path == CONTENT:
        return Reply(200, b"file body", "application/octet-stream")
    return Reply.json(200, SEARCH_ANSWER)


def after_startup(path: str, failure: Any) -> Script:
    """Healthy for the proxy's startup probe (the first registry request), then failing on `path`."""
    registry_requests = {"n": 0}

    def script(request: Request) -> Any:
        if request.path == TOOLS:
            registry_requests["n"] += 1
            if registry_requests["n"] == 1:
                return healthy(request)
        return failure if request.path == path else healthy(request)

    return script


def first_registry_request_fails(failure: Any) -> Script:
    """The proxy's startup probe gets `failure`; every later request is served."""
    registry_requests = {"n": 0}

    def script(request: Request) -> Any:
        if request.path == TOOLS:
            registry_requests["n"] += 1
            if registry_requests["n"] == 1:
                return failure
        return healthy(request)

    return script


def failing_on(path: str, failure: Any) -> Script:
    """An engine that answers `failure` on `path` and is healthy everywhere else."""

    def script(request: Request) -> Any:
        return failure if request.path == path else healthy(request)

    return script


@dataclass
class EngineDouble:
    script: Script
    seen: list[str] = field(default_factory=list)
    _generation: int = 0
    _release: threading.Event = field(default_factory=threading.Event)

    def go_stale(self) -> None:
        """From now on every connection opened before this moment hangs; new ones are served."""
        self._generation += 1

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> None:
        double = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def setup(self) -> None:
                super().setup()
                self.born = double._generation

            def log_message(self, format: str, *args: Any) -> None:
                pass

            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    self.rfile.read(length)
                path = self.path.split("?", 1)[0]
                double.seen.append(path)
                if self.born < double._generation:
                    double._release.wait()
                    self.close_connection = True
                    return
                action = double.script(Request(path, self.command, self.born == double._generation))
                if action == HANG:
                    double._release.wait()
                    self.close_connection = True
                    return
                if action == DROP:
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                self.send_response(action.code)
                self.send_header("Content-Type", action.content_type)
                self.send_header("Content-Length", str(len(action.body)))
                self.end_headers()
                self.wfile.write(action.body)

            do_GET = _serve
            do_POST = _serve
            do_PATCH = _serve
            do_DELETE = _serve

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self._release.set()
        self._server.shutdown()
        self._server.server_close()


def unused_url() -> str:
    """An address nothing listens on: the engine is not running."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def write_config(home: Path, url: str, clear_cache: bool = True) -> Path:
    cache = home / "cache"
    config = home / "config.yaml"
    config.write_text(
        "server:\n"
        f"  url: {url}\n"
        f"  timeout: {PROXY_TIMEOUT}\n"
        "paths:\n"
        "  fetch:\n"
        f"    cache_dir: {cache}\n"
        f"    clear_on_start: {'true' if clear_cache else 'false'}\n"
        "log:\n"
        f"  file: {home / 'proxy.log'}\n"
    )
    return config


@asynccontextmanager
async def proxy(config: Path):
    """The proxy as a host starts it: a process on stdio, initialized, tools listed once."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "letapis_mcp", "--config", str(config)],
        cwd=str(config.parent),
    )
    with open(config.parent / "proxy.stderr", "w") as errlog:
        async with stdio_client(params, errlog=errlog) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.list_tools()
                yield session


async def call(session: ClientSession, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """What the agent reads back from one tool call."""
    result = await session.call_tool(name, arguments)
    return json.loads(result.content[0].text)


async def listed(session: ClientSession) -> set[str]:
    return {tool.name for tool in (await session.list_tools()).tools}
