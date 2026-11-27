"""What the agent reads over the wire from the proxy: the tool list, the `initialize` answer, the outage surface, a call's answer.

Each probe starts the real proxy on stdio against a loopback engine and reads what a host reads.
Nothing here names an SDK class of the proxy, so the same probes hold on any SDK version.
"""
from __future__ import annotations

import json

import pytest

from tests.e2e.engine_double import (
    EngineDouble,
    Reply,
    call,
    proxy,
    unused_url,
    write_config,
)

pytestmark = pytest.mark.asyncio

DESTRUCTIVE = {"destructiveHint": True, "readOnlyHint": False, "idempotentHint": False}
INSTRUCTIONS = "letapis answers by MEANING over the corpus indexed here."
PINNED = {"search", "blast_radius", "ena_get_context"}

ENGINE_TOOLS = [
    {"name": "search", "method": "POST", "endpoint": "/api/v1/search", "description": "hybrid search",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}},
    {"name": "blast_radius", "method": "POST", "endpoint": "/api/v1/blast_radius", "description": "callers",
     "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}}}},
    {"name": "ena_get_context", "method": "POST", "endpoint": "/api/v1/ena_get_context", "description": "recall",
     "inputSchema": {"type": "object"}},
    {"name": "list_folders", "method": "GET", "endpoint": "/api/v1/folders", "description": "folders",
     "inputSchema": {"type": "object"}},
    {"name": "remove_folder", "method": "POST", "endpoint": "/api/v1/remove_folder", "description": "un-index",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
     "annotations": dict(DESTRUCTIVE)},
]
ENGINE_NAMES = {t["name"] for t in ENGINE_TOOLS}


@pytest.fixture
def engine():
    doubles: list[EngineDouble] = []

    def start(script) -> EngineDouble:
        double = EngineDouble(script)
        double.start()
        doubles.append(double)
        return double

    yield start
    for double in doubles:
        double.stop()


def serving(request):
    if request.path == "/api/v1/tools":
        return Reply.json(200, {"tools": ENGINE_TOOLS, "instructions": INSTRUCTIONS})
    if request.path == "/api/v1/search":
        return Reply.json(200, {"status": "success", "results": []})
    return Reply.json(200, {"status": "success"})


def is_error(result) -> bool:
    return bool(result.model_dump(by_alias=True).get("isError"))


def on_the_wire(tool) -> dict:
    """The tool as the client received it, absent fields absent."""
    return tool.model_dump(by_alias=True, exclude_none=True)


async def wire_tools(session) -> dict[str, dict]:
    return {t.name: on_the_wire(t) for t in (await session.list_tools()).tools}


async def test_the_agent_is_shown_the_engines_tools_and_the_proxys_own_fetch_file(tmp_path, engine):
    double = engine(serving)
    async with proxy(write_config(tmp_path, double.url)) as session:
        tools = await wire_tools(session)
    assert set(tools) == ENGINE_NAMES | {"fetch_file"}, set(tools)
    assert "letapis_status" not in tools
    assert tools["search"]["inputSchema"]["properties"] == {"query": {"type": "string"}}
    assert "reveal" in tools["fetch_file"]["inputSchema"]["properties"], tools["fetch_file"]


async def test_exactly_the_three_named_tools_ask_to_stay_loaded(tmp_path, engine):
    double = engine(serving)
    async with proxy(write_config(tmp_path, double.url)) as session:
        tools = await wire_tools(session)
    marked = {n for n, t in tools.items() if t.get("_meta") == {"anthropic/alwaysLoad": True}}
    carrying_any_meta = {n for n, t in tools.items() if "_meta" in t}
    assert marked == PINNED, marked
    assert carrying_any_meta == PINNED, carrying_any_meta


async def test_a_hint_the_engine_declares_reaches_the_agent_and_an_absent_one_stays_absent(tmp_path, engine):
    double = engine(serving)
    async with proxy(write_config(tmp_path, double.url)) as session:
        tools = await wire_tools(session)
    assert tools["remove_folder"]["annotations"] == DESTRUCTIVE, tools["remove_folder"]
    assert {n for n, t in tools.items() if "annotations" in t} == {"remove_folder"}


async def test_initialize_says_the_list_can_change_and_carries_the_engines_account(tmp_path, engine):
    double = engine(serving)
    async with proxy(write_config(tmp_path, double.url)) as session:
        init = session.initialize_answer
    wire = init.model_dump(by_alias=True, exclude_none=True)
    assert wire["capabilities"]["tools"]["listChanged"] is True, wire
    assert wire["instructions"] == INSTRUCTIONS, wire
    assert wire["serverInfo"]["name"] == "letapis", wire


async def test_a_call_returns_the_engines_body_as_one_text_block(tmp_path, engine):
    double = engine(serving)
    async with proxy(write_config(tmp_path, double.url)) as session:
        result = await session.call_tool("search", {"query": "x"})
    assert not is_error(result), result
    assert [c.type for c in result.content] == ["text"], result
    assert json.loads(result.content[0].text) == {"status": "success", "results": []}


async def test_with_the_engine_down_the_agent_is_shown_status_and_fetch_file_and_status_is_pinned(tmp_path):
    async with proxy(write_config(tmp_path, unused_url())) as session:
        tools = await wire_tools(session)
        init = session.initialize_answer
    assert set(tools) == {"letapis_status", "fetch_file"}, set(tools)
    assert tools["letapis_status"].get("_meta") == {"anthropic/alwaysLoad": True}
    assert "fetch_file" in tools and "_meta" not in tools["fetch_file"]
    assert init.model_dump(by_alias=True)["capabilities"]["tools"]["listChanged"] is True, init


async def test_with_the_engine_down_a_call_is_an_answer_and_not_an_error(tmp_path):
    """An expected state must not be `isError`: an early error teaches the agent to leave letapis."""
    async with proxy(write_config(tmp_path, unused_url())) as session:
        result = await session.call_tool("search", {"query": "x"})
        status = await call(session, "letapis_status", {})
    assert not is_error(result), result
    assert status.get("status") == "unavailable", status
    assert "letapis_status" in status.get("message", ""), status
