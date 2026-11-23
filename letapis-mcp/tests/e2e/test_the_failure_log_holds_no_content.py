"""The failure log on disk names what failed and how, and carries nothing the engine said.

The agent gets the engine's error text in the tool answer; the file outlives the session,
and an error body can carry corpus text or a key.
"""
from __future__ import annotations

import pytest

from tests.e2e.engine_double import (
    CONTENT,
    SEARCH,
    TOOLS,
    EngineDouble,
    Reply,
    after_startup,
    call,
    failing_on,
    first_registry_request_fails,
    healthy,
    listed,
    proxy,
    write_config,
)

pytestmark = pytest.mark.asyncio

BODY_MARKER = "BODY-MARKER-7f3a"
ARGUMENT_MARKER = "ARGUMENT-MARKER-91c2"


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


@pytest.mark.parametrize(
    "script, tool, arguments, entry",
    [
        pytest.param(
            after_startup(TOOLS, Reply.text(500, BODY_MARKER)), "search",
            {"query": ARGUMENT_MARKER}, "tool map", id="tool-map",
        ),
        pytest.param(
            failing_on(SEARCH, Reply.text(500, BODY_MARKER)), "search",
            {"query": ARGUMENT_MARKER}, "call search", id="call",
        ),
        pytest.param(
            failing_on(CONTENT, Reply.text(500, BODY_MARKER)), "fetch_file",
            {"path": f"/w/{ARGUMENT_MARKER}.md"}, "fetch_file", id="fetch-file",
        ),
    ],
)
async def test_an_engine_error_is_logged_by_code_and_without_its_body(
    tmp_path, engine, script, tool, arguments, entry
):
    double = engine(script)
    async with proxy(write_config(tmp_path, double.url)) as session:
        await call(session, tool, arguments)
    log = (tmp_path / "proxy.log").read_text()
    assert BODY_MARKER not in log, log
    assert ARGUMENT_MARKER not in log, log
    assert any(entry in l and "500" in l for l in log.splitlines()), log


async def test_an_unusable_tool_list_is_logged_without_what_it_held(tmp_path, engine):
    double = engine(after_startup(TOOLS, Reply.json(200, [BODY_MARKER])))
    async with proxy(write_config(tmp_path, double.url)) as session:
        await call(session, "search", {"query": "x"})
    log = (tmp_path / "proxy.log").read_text()
    assert BODY_MARKER not in log, log
    assert "tool map" in log, log


async def test_a_failed_startup_probe_is_logged_with_its_cause(tmp_path, engine):
    double = engine(first_registry_request_fails(Reply.text(500, BODY_MARKER)))
    async with proxy(write_config(tmp_path, double.url)) as session:
        tools = await listed(session)
    log = (tmp_path / "proxy.log").read_text()
    assert "search" in tools, tools
    assert any("startup" in l and "500" in l for l in log.splitlines()), log
    assert BODY_MARKER not in log, log
