"""The proxy carries arguments on EVERY method, not just the two in daily use.

Stage `68.9`, decision `D68-18`. The class "a declared parameter never arrives" is
guarded on two seams inside the engine — schema→route and schema→handler. The third
seam belongs to this package and nobody watched it: `POST` goes out with
`json=arguments`, `GET` with `params=arguments`, and `DELETE` went as
`self.client.delete(endpoint)` — no body, no params. Everything not already
substituted into the URL vanished silently.

**The branch is dead today, and that is precisely why the probe exists.** The engine's
live map on 27.08: 49 tools, 39 `POST`, 10 `GET`, no `DELETE` at all
`[checked: GET /api/v1/tools on :3131]`. What is being fixed is a trap, not a symptom:
the first tool declared on a losing method would have dropped its arguments with
nowhere to learn it from.

**The declaration here is invented, and that is a boundary of the stage.** No real
tool is given `DELETE` for the sake of a test: the engine's live surface is not
touched to make a probe pass. The route map is injected straight into the client, so
this probe knows nothing about which methods the engine declares — and must not. Its
claim is about the PROXY: arguments go out on the wire whatever the method.

What is asked is the WIRE — what was handed to the HTTP call — not the arguments the
client was given. An argument accepted by the client and never put into the request is
rejected by nothing and lost silently; that is exactly how `DELETE` lived.
"""

from __future__ import annotations

from typing import Any

import pytest

from letapis_mcp.client import letapisClient

ARGS = {"scope_id": "sc-1", "reason": "obsolete"}


class _RecordingTransport:
    """Stands in for the HTTP client and keeps method and everything handed to it.

    Each method records its own call whole — body and params together — so the probe
    can tell "went as a body" from "went as a query string" from "did not go at all".
    A double whose method silently returns a response and records nothing would
    reproduce the defect: the call happened, the arguments are gone, and from the
    outside it looks like success.
    """

    def __init__(self) -> None:
        self.seen: list[tuple[str, dict[str, Any]]] = []

    def _record(self, method: str, url: str, **kw: Any):
        self.seen.append((method, {"url": url, **kw}))

        class _Response:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, Any]:
                return {"status": "success"}

        return _Response()

    async def get(self, url, **kw):
        return self._record("GET", url, **kw)

    async def post(self, url, **kw):
        return self._record("POST", url, **kw)

    async def patch(self, url, **kw):
        return self._record("PATCH", url, **kw)

    async def delete(self, url, **kw):
        return self._record("DELETE", url, **kw)

    async def request(self, method, url, **kw):
        return self._record(method, url, **kw)


def _client_on(method: str) -> tuple[letapisClient, _RecordingTransport]:
    """A client holding ONE invented tool on the named method.

    The route map is set by hand rather than loaded: the live engine declares no such
    tool, and must not be made to.
    """
    client = letapisClient.__new__(letapisClient)
    transport = _RecordingTransport()
    client._client = transport
    client._tool_routes = {"pretend_tool": (method, "/api/v1/pretend")}
    return client, transport


def _delivered(payload: dict[str, Any]) -> dict[str, Any]:
    """The arguments as they went onto the wire — as a body or as a query string.

    Which of the two depends on the method and is not what this probe is about: the
    question is WHETHER they arrived, not by which of the two legitimate routes.
    """
    return payload.get("json") or payload.get("params") or {}


# --- a method that carries: the half that was already correct ----------------


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["POST", "GET", "PATCH"])
async def test_a_working_method_carries_the_arguments(method):
    """The three methods in daily use carry arguments — and did so before this work.

    The probe is not here for their sake: without it the claim "arguments arrive"
    would rest on `DELETE` alone, and a change breaking `POST` would pass unnoticed.
    """
    client, transport = _client_on(method)

    await client.call_tool("pretend_tool", dict(ARGS))

    assert len(transport.seen) == 1
    sent_method, payload = transport.seen[0]
    assert sent_method == method
    assert _delivered(payload) == ARGS


# --- the method that used to lose them ---------------------------------------


@pytest.mark.asyncio
async def test_delete_carries_its_arguments_too():
    """What the work is for: arguments go out on `DELETE` as well.

    Before the fix the call went as `client.delete(endpoint)` — no body, no params —
    and `scope_id` with `reason` vanished while the answer came back successful.
    """
    client, transport = _client_on("DELETE")

    await client.call_tool("pretend_tool", dict(ARGS))

    assert len(transport.seen) == 1
    sent_method, payload = transport.seen[0]
    assert sent_method == "DELETE"
    assert _delivered(payload) == ARGS, (
        "посредник вызвал DELETE и не приложил доводы — они потеряны молча"
    )


# --- paired halves ------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["POST", "GET", "PATCH", "DELETE"])
async def test_a_call_without_arguments_invents_none(method):
    """No arguments sent — the proxy does not invent any.

    Without this half the first probe would go green on a client that supplies
    arguments of its own: "the arguments arrived" is true of the WRONG ones too.
    """
    client, transport = _client_on(method)

    await client.call_tool("pretend_tool", {})

    _sent_method, payload = transport.seen[0]
    assert _delivered(payload) == {}


@pytest.mark.asyncio
async def test_a_url_parameter_is_not_sent_twice():
    """An argument that went into the URL is not repeated on the wire.

    `_substitute_url_params` pops it from the dict; had the `DELETE` fix attached the
    original arguments rather than what remained, `scope_id` would travel both in the
    path and in the body — a different request from the one the caller asked for.
    """
    client, transport = _client_on("DELETE")
    client._tool_routes = {"pretend_tool": ("DELETE", "/api/v1/graphs/{scope_id}")}

    await client.call_tool("pretend_tool", dict(ARGS))

    _method, payload = transport.seen[0]
    assert payload["url"] == "/api/v1/graphs/sc-1"
    assert _delivered(payload) == {"reason": "obsolete"}
