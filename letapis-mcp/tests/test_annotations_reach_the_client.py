"""The destructive hint the engine declares reaches the client.

The engine states destructiveness as a FIELD (`annotations`) rather than as prose
in the description, because that is what a client can act on. The proxy sits
between: it rebuilds every tool as `types.Tool`, so a field it does not copy dies
here and `GET /api/v1/tools` is the last place it exists.

Assertions read the wire form — `model_dump(by_alias=True, exclude_none=True)` —
for the reason the neighbouring `_meta` tests give: an attribute that exists is
not the same as a field that crosses under the name the client reads.

The negative half is the one that matters. A proxy stamping every tool with the
hint passes the positive test and turns the whole surface into a warning nobody
reads.
"""
from __future__ import annotations

import pytest

import letapis_mcp.server as srv

DESTRUCTIVE_HINTS = {"destructiveHint": True, "readOnlyHint": False, "idempotentHint": False}

#: The engine surface trimmed to what this file needs: two tools that declare the
#: hint and two that must not carry it.
ENGINE_TOOLS = [
    {"name": "force_reindex", "description": "reindex from scratch",
     "inputSchema": {"type": "object"}, "annotations": dict(DESTRUCTIVE_HINTS)},
    {"name": "remove_folder", "description": "un-index a folder",
     "inputSchema": {"type": "object"}, "annotations": dict(DESTRUCTIVE_HINTS)},
    {"name": "search", "description": "hybrid search", "inputSchema": {"type": "object"}},
    {"name": "list_folders", "description": "watched folders", "inputSchema": {"type": "object"}},
]


class FakeClientUp:
    async def get_tools(self):
        return {"tools": ENGINE_TOOLS}

    async def call_tool(self, name, arguments):
        return {"status": "success"}


@pytest.fixture(autouse=True)
def clean_state():
    srv._tools_cache.clear()
    yield
    srv._tools_cache.clear()


def wire_annotations(tool) -> dict | None:
    """The `annotations` the client receives, or None when the field is absent."""
    return tool.model_dump(by_alias=True, exclude_none=True).get("annotations")


@pytest.mark.asyncio
async def test_a_declared_hint_crosses_the_proxy(monkeypatch):
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    tools = {t.name: t for t in await srv.list_tools()}

    for name in ("force_reindex", "remove_folder"):
        assert wire_annotations(tools[name]) == DESTRUCTIVE_HINTS, (
            f"{name}: the engine declared the hint and the client does not see it"
        )


@pytest.mark.asyncio
async def test_a_tool_without_the_field_carries_none(monkeypatch):
    """Absent, not false: a client reading the key would find an answer either way."""
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    tools = {t.name: t for t in await srv.list_tools()}

    for name in ("search", "list_folders"):
        assert wire_annotations(tools[name]) is None, (
            f"{name} declares nothing and must carry no annotations; "
            f"got {wire_annotations(tools[name])!r}"
        )


@pytest.mark.asyncio
async def test_exactly_the_declaring_tools_are_annotated(monkeypatch):
    """Counts rather than spot checks, so stamping everything fails here."""
    monkeypatch.setattr(srv, "_client", FakeClientUp())
    tools = await srv.list_tools()

    annotated = {t.name for t in tools if wire_annotations(t)}
    assert annotated == {"force_reindex", "remove_folder"}
