"""What the agent is told for each way a request to the engine can fail, checked on the function."""
from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from letapis_mcp.answers import (
    EngineUnusable,
    ErrorStatus,
    NoAnswer,
    Unusable,
    engine_failure,
    log_fields,
    outcome_of,
)
from letapis_mcp.client import letapisClient

URL = "http://engine"
ANSWER_SHAPED = ("re-run search", "Unknown tool", "stale_proxy_list")


def answer(outcome, **kw) -> dict:
    return engine_failure(outcome, url=URL, asked_for="'search'", **kw)


def says_nothing_about_tools_or_content(payload: dict) -> bool:
    text = json.dumps(payload)
    return "letapis-core" in text and not any(c in text for c in ANSWER_SHAPED)


# --- no answer --------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["refused", "not_connected", "timeout", "dropped"])
def test_no_answer_is_unavailable_with_its_reason(kind):
    payload = answer(NoAnswer(kind, "SomeError", "detail"))
    assert payload["status"] == "unavailable"
    assert payload["reason"] == kind
    assert says_nothing_about_tools_or_content(payload)


@pytest.mark.parametrize("kind", ["timeout", "dropped"])
def test_a_lost_answer_to_work_that_may_have_started_is_an_unknown_outcome(kind):
    payload = answer(NoAnswer(kind, "SomeError", "detail"), may_still_run=True)
    assert payload["status"] == kind
    assert payload["outcome"] == "unknown"
    assert "get_indexing_progress" in payload["message"]
    assert "retry" not in payload["message"].lower()


@pytest.mark.parametrize("kind", ["refused", "not_connected"])
def test_a_request_that_never_reached_the_engine_can_be_sent_again(kind):
    payload = answer(NoAnswer(kind, "SomeError", "detail"), may_still_run=True)
    assert payload["status"] == "unavailable"
    assert "call again" in payload["message"]


# --- an HTTP error ----------------------------------------------------------------------


@pytest.mark.parametrize("code", [400, 401, 403, 404, 422, 500, 502])
def test_an_error_status_is_an_engine_error_with_its_code(code):
    payload = answer(ErrorStatus(code, "boom"))
    assert payload["status"] == "engine_error"
    assert payload["code"] == code
    assert says_nothing_about_tools_or_content(payload)


def test_503_is_the_engine_warming_up():
    payload = answer(ErrorStatus(503, "embedder not ready"))
    assert payload["status"] == "unavailable"
    assert "warming up" in payload["message"]


def test_an_error_page_reaches_the_agent_cut():
    payload = answer(ErrorStatus(500, "e" * 500 + "TAIL"))
    assert "e" * 500 in payload["message"]
    assert "TAIL" not in payload["message"]


def test_a_short_error_page_reaches_the_agent_whole():
    payload = answer(ErrorStatus(500, "short reason"))
    assert "short reason" in payload["message"]


# --- a 200 nothing can use --------------------------------------------------------------


def test_an_unusable_answer_is_an_engine_error_without_a_code():
    payload = answer(Unusable("empty-tool-list"))
    assert payload["status"] == "engine_error"
    assert "code" not in payload
    assert "empty-tool-list" in payload["message"]
    assert says_nothing_about_tools_or_content(payload)


def test_an_unusable_answer_is_cut_too():
    payload = answer(Unusable("not-a-tool-list", "x" * 500 + "TAIL"))
    assert "TAIL" not in payload["message"]


# --- which outcome an exception stands for ----------------------------------------------

REQUEST = httpx.Request("GET", "http://engine/api/v1/tools")


@pytest.mark.parametrize(
    "error, kind",
    [
        (httpx.ConnectError("refused", request=REQUEST), "refused"),
        (httpx.ConnectTimeout("slow", request=REQUEST), "not_connected"),
        (httpx.PoolTimeout("slow", request=REQUEST), "not_connected"),
        (httpx.ReadTimeout("slow", request=REQUEST), "timeout"),
        (httpx.WriteTimeout("slow", request=REQUEST), "timeout"),
        (httpx.RemoteProtocolError("gone", request=REQUEST), "dropped"),
        (httpx.ReadError("gone", request=REQUEST), "dropped"),
    ],
)
def test_a_transport_error_is_no_answer(error, kind):
    assert outcome_of(error) == NoAnswer(kind, type(error).__name__, str(error))


def test_an_http_status_error_is_an_error_status():
    response = httpx.Response(401, text="bad key", request=REQUEST)
    error = httpx.HTTPStatusError("401", request=REQUEST, response=response)
    assert outcome_of(error) == ErrorStatus(401, "bad key")


def test_an_answer_that_is_not_json_is_unusable():
    try:
        json.loads("<html>")
    except json.JSONDecodeError as error:
        assert isinstance(outcome_of(error), Unusable)


def test_an_unusable_registry_is_unusable():
    assert outcome_of(EngineUnusable("empty-tool-list")) == Unusable("empty-tool-list")


@pytest.mark.parametrize("error", [RuntimeError("client not started"), KeyError("x"), ValueError("x")])
def test_an_error_of_the_proxy_itself_is_not_the_engines(error):
    assert outcome_of(error) is None


# --- the client answers a failed tool map as a failure of the tool list ------------------


async def _client_over(handler) -> letapisClient:
    cfg = SimpleNamespace(server=SimpleNamespace(url=URL, api_key=None, timeout=5))
    client = letapisClient(cfg, transport=httpx.MockTransport(handler))
    await client.start()
    return client


@pytest.mark.asyncio
async def test_a_tool_map_that_timed_out_is_unavailable_not_still_running():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    client = await _client_over(handler)
    payload = await client.call_tool("deep_index", {})
    await client.stop()
    assert payload["status"] == "unavailable", payload
    assert "get_indexing_progress" not in payload["message"]
    assert "tool list" in payload["message"]


@pytest.mark.asyncio
async def test_a_loaded_tool_map_still_answers_unknown_names_plainly():
    def handler(request):
        return httpx.Response(200, json={"tools": [
            {"name": "search", "method": "POST", "endpoint": "/api/v1/search"}
        ]})

    client = await _client_over(handler)
    payload = await client.call_tool("zzz_never_existed", {})
    await client.stop()
    assert payload == {"error": "Unknown tool: zzz_never_existed"}


# --- what the log on disk is given ------------------------------------------------------


@pytest.mark.parametrize(
    "outcome, expected",
    [
        (NoAnswer("dropped", "RemoteProtocolError", "BODY"), "kind=dropped error=RemoteProtocolError"),
        (ErrorStatus(500, "BODY"), "kind=http code=500"),
        (Unusable("not-a-tool-list", "BODY"), "kind=unusable what=not-a-tool-list"),
    ],
)
def test_the_log_gets_the_kind_and_code_and_not_what_the_engine_said(outcome, expected):
    assert log_fields(outcome) == expected
