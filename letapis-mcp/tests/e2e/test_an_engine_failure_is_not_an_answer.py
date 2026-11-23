"""When the engine fails, the agent hears that the engine failed — never an answer about tools or content.

Each probe starts the real proxy process against a loopback engine and reads what the agent
reads. The input is the engine's behaviour on one request: no answer, a dropped connection,
an HTTP error, or a 200 that carries nothing usable. A failure read as «no such tool», as «your
path is stale», or as a bare error string is exactly what an agent acts on with false confidence.
"""
from __future__ import annotations

import json

import pytest

from tests.e2e.engine_double import (
    CONTENT,
    DROP,
    HANG,
    REGISTRY,
    SEARCH,
    TOOLS,
    EngineDouble,
    Reply,
    after_startup,
    call,
    failing_on,
    healthy,
    listed,
    proxy,
    unused_url,
    write_config,
)

pytestmark = pytest.mark.asyncio

ANSWER_SHAPED = ("re-run search", "Unknown tool", "stale_proxy_list")
LONG_PAGE = "e" * 500 + "TAIL" * 1000


def assert_engine_failure(payload: dict, *, status: set[str], code: int | None = None) -> None:
    text = json.dumps(payload)
    for claim in ANSWER_SHAPED:
        assert claim not in text, payload
    assert payload.get("status") in status, payload
    assert "letapis-core" in text, payload
    if code is not None:
        assert payload.get("code") == code, payload


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


TRANSPORT = [
    pytest.param(HANG, {"unavailable", "timeout"}, id="no-answer"),
    pytest.param(DROP, {"unavailable"}, id="dropped"),
]
HTTP = [
    pytest.param(Reply.text(500, "internal error"), 500, id="http-500"),
    pytest.param(Reply.text(401, "bad key"), 401, id="http-401"),
]
WARMING = Reply.text(503, "embedder not ready")


# --- startup ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(Reply.json(200, ["search"]), id="not-an-object"),
        pytest.param(Reply.text(200, "<html>not json</html>"), id="not-json"),
        pytest.param(Reply.text(500, "internal error"), id="http-500"),
    ],
)
async def test_the_proxy_comes_up_whatever_the_registry_answers(tmp_path, engine, answer):
    double = engine(failing_on(TOOLS, answer))
    async with proxy(write_config(tmp_path, double.url)) as session:
        tools = await listed(session)
    assert "letapis_status" in tools, tools


# --- the tool map, loaded on the first call (the engine was healthy at startup) ---------


async def test_engine_not_running_on_first_call(tmp_path):
    async with proxy(write_config(tmp_path, unused_url())) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"unavailable"})


@pytest.mark.parametrize("failure, status", TRANSPORT)
async def test_tool_map_transport_failure(tmp_path, engine, failure, status):
    double = engine(after_startup(TOOLS, failure))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status=status)


@pytest.mark.parametrize("failure, code", HTTP)
async def test_tool_map_http_error(tmp_path, engine, failure, code):
    double = engine(after_startup(TOOLS, failure))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"engine_error"}, code=code)


async def test_tool_map_while_warming_up(tmp_path, engine):
    double = engine(after_startup(TOOLS, WARMING))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"unavailable"})


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(Reply.text(200, "<html>not json</html>"), id="not-json"),
        pytest.param(Reply.json(200, ["search"]), id="not-an-object"),
        pytest.param(Reply.json(200, {}), id="no-tools-key"),
        pytest.param(Reply.json(200, {"tools": []}), id="empty"),
    ],
)
async def test_tool_map_nothing_routable(tmp_path, engine, answer):
    double = engine(after_startup(TOOLS, answer))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"engine_error"})


async def test_tool_map_error_page_is_cut(tmp_path, engine):
    double = engine(after_startup(TOOLS, Reply.text(500, LONG_PAGE)))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"engine_error"}, code=500)
    assert "TAIL" not in json.dumps(payload)


async def test_a_name_missing_from_a_loaded_map_is_an_unknown_tool(tmp_path, engine):
    double = engine(healthy)
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "no_such_tool", {})
    assert payload == {"error": "Unknown tool: no_such_tool"}


async def test_a_loaded_map_routes_the_call(tmp_path, engine):
    double = engine(healthy)
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert payload["status"] == "success"


# --- a stale connection under the tool map ---------------------------------------------


async def test_a_stale_connection_under_the_tool_map_is_an_engine_failure(tmp_path, engine):
    double = engine(healthy)
    async with proxy(write_config(tmp_path, double.url)) as session:
        double.go_stale()
        # A name the list lacks makes the proxy ask for the list again, over the stale pool.
        payload = await call(session, "no_such_tool", {})
    assert_engine_failure(payload, status={"unavailable", "timeout"})


async def test_the_call_after_a_stale_tool_map_gets_the_map(tmp_path, engine):
    double = engine(healthy)
    async with proxy(write_config(tmp_path, double.url)) as session:
        double.go_stale()
        await call(session, "search", {"query": "x"})
        payload = await call(session, "search", {"query": "x"})
    assert payload["status"] == "success", payload


# --- the call itself, with the map loaded ----------------------------------------------


@pytest.mark.parametrize("failure, status", TRANSPORT)
async def test_call_transport_failure(tmp_path, engine, failure, status):
    double = engine(failing_on(SEARCH, failure))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status=status)


@pytest.mark.parametrize("failure, code", HTTP)
async def test_call_http_error(tmp_path, engine, failure, code):
    double = engine(failing_on(SEARCH, failure))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"engine_error"}, code=code)


async def test_call_while_warming_up(tmp_path, engine):
    double = engine(failing_on(SEARCH, WARMING))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"unavailable"})


async def test_call_answer_that_is_not_json(tmp_path, engine):
    double = engine(failing_on(SEARCH, Reply.text(200, "<html>not json</html>")))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"engine_error"})


async def test_call_error_page_is_cut(tmp_path, engine):
    double = engine(failing_on(SEARCH, Reply.text(500, LONG_PAGE)))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "search", {"query": "x"})
    assert_engine_failure(payload, status={"engine_error"}, code=500)
    assert "TAIL" not in json.dumps(payload)


# --- fetch_file --------------------------------------------------------------------------


async def test_fetch_file_engine_not_running(tmp_path):
    async with proxy(write_config(tmp_path, unused_url())) as session:
        payload = await call(session, "fetch_file", {"path": "/w/a.md"})
    assert_engine_failure(payload, status={"unavailable"})


@pytest.mark.parametrize("failure, status", TRANSPORT)
async def test_fetch_file_transport_failure(tmp_path, engine, failure, status):
    double = engine(failing_on(CONTENT, failure))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "fetch_file", {"path": "/w/a.md"})
    assert_engine_failure(payload, status=status)


@pytest.mark.parametrize("failure, code", HTTP)
async def test_fetch_file_http_error(tmp_path, engine, failure, code):
    double = engine(failing_on(CONTENT, failure))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "fetch_file", {"path": "/w/a.md"})
    assert_engine_failure(payload, status={"engine_error"}, code=code)


async def test_fetch_file_while_warming_up(tmp_path, engine):
    double = engine(failing_on(CONTENT, WARMING))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "fetch_file", {"path": "/w/a.md"})
    assert_engine_failure(payload, status={"unavailable"})


async def test_fetch_file_error_page_is_cut(tmp_path, engine):
    double = engine(failing_on(CONTENT, Reply.text(500, LONG_PAGE)))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "fetch_file", {"path": "/w/a.md"})
    assert_engine_failure(payload, status={"engine_error"}, code=500)
    assert "TAIL" not in json.dumps(payload)


async def test_fetch_file_missing_path_keeps_the_path_hint(tmp_path, engine):
    double = engine(failing_on(CONTENT, Reply.json(404, {"detail": "no such file: /w/a.md"})))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "fetch_file", {"path": "/w/a.md"})
    assert payload["status"] == "error", payload
    assert "re-run search" in payload["hint"], payload


async def test_fetch_file_local_cache_failure_is_not_blamed_on_the_path(tmp_path, engine):
    """The engine answered; the proxy could not write its copy — that is not a stale path."""
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "w").write_text("a file where the cache needs a folder")
    double = engine(healthy)
    async with proxy(write_config(tmp_path, double.url, clear_cache=False)) as session:
        payload = await call(session, "fetch_file", {"path": "/w/a.md"})
    assert payload.get("status") != "success", payload
    assert "re-run search" not in json.dumps(payload), payload


async def test_fetch_file_delivers_the_file(tmp_path, engine):
    double = engine(healthy)
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "fetch_file", {"path": "/w/a.md"})
    assert payload["status"] == "success", payload


# --- the tool list the host shows the agent --------------------------------------------


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(Reply.json(200, {"tools": []}), id="empty"),
        pytest.param(Reply.json(200, {}), id="no-tools-key"),
        pytest.param(Reply.text(500, "internal error"), id="http-500"),
    ],
)
async def test_an_unusable_registry_lists_the_outage_and_recovers(tmp_path, engine, answer):
    state = {"down": True}

    def script(request):
        if request.path == TOOLS and state["down"]:
            return answer
        return healthy(request)

    double = engine(script)
    async with proxy(write_config(tmp_path, double.url)) as session:
        during = await listed(session)
        state["down"] = False
        after = await listed(session)
    assert "letapis_status" in during, during
    assert {t["name"] for t in REGISTRY["tools"]} <= after, after
    assert "letapis_status" not in after, after
