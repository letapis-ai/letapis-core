"""An engine failure leaves a line in the proxy's own log file, readable after the session is gone."""
from __future__ import annotations

import pytest

from tests.e2e.engine_double import (
    SEARCH,
    TOOLS,
    EngineDouble,
    Reply,
    after_startup,
    call,
    failing_on,
    healthy,
    proxy,
    write_config,
)

pytestmark = pytest.mark.asyncio


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


async def test_a_failed_tool_map_is_written_down(tmp_path, engine):
    double = engine(after_startup(TOOLS, Reply.text(500, "internal error")))
    async with proxy(write_config(tmp_path, double.url)) as session:
        await call(session, "search", {"query": "x"})
    lines = (tmp_path / "proxy.log").read_text().splitlines()
    assert any(f"engine={double.url}" in l and "code=500" in l for l in lines), lines


async def test_a_failed_call_is_written_down_with_its_tool(tmp_path, engine):
    double = engine(failing_on(SEARCH, Reply.text(401, "bad key")))
    async with proxy(write_config(tmp_path, double.url)) as session:
        await call(session, "search", {"query": "x"})
    lines = (tmp_path / "proxy.log").read_text().splitlines()
    assert any("call search" in l and "code=401" in l for l in lines), lines


async def test_a_healthy_session_writes_nothing(tmp_path, engine):
    double = engine(healthy)
    async with proxy(write_config(tmp_path, double.url)) as session:
        await call(session, "search", {"query": "x"})
    log = tmp_path / "proxy.log"
    assert not log.exists() or log.read_text() == "", log.read_text()
