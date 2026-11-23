"""A call the proxy does not repeat, whose answer never came back, may have started.

The agent is told the outcome is unknown and how to find out — never to repeat the call,
because repeating a mutation the engine already runs does the work twice.
"""
from __future__ import annotations

import json

import pytest

from tests.e2e.engine_double import (
    DROP,
    HANG,
    INDEX,
    EngineDouble,
    call,
    failing_on,
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


@pytest.mark.parametrize(
    "failure", [pytest.param(DROP, id="dropped"), pytest.param(HANG, id="no-answer")]
)
async def test_a_mutation_whose_answer_was_lost_is_not_to_be_repeated(tmp_path, engine, failure):
    double = engine(failing_on(INDEX, failure))
    async with proxy(write_config(tmp_path, double.url)) as session:
        payload = await call(session, "index_folder", {"path": "/w"})
    text = json.dumps(payload).lower()
    assert "retry" not in text, payload
    assert "get_indexing_progress" in text, payload
    assert double.seen.count(INDEX) == 1, double.seen
