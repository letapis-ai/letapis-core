"""What the agent hears when a request to letapis-core did not produce a usable answer.

When the engine fails, the agent is told so, and only so: what went wrong lies with the
engine, and says nothing on whether the tool or the file it wanted exists. «Unknown tool»
and «your path is stale» are claims about tools and files; an agent that reads either one
acts on it with confidence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

BODY_LIMIT = 500

#: No answer, and the request never reached the engine: calling again cannot double anything.
UNSENT = frozenset({"refused", "not_connected"})


@dataclass(frozen=True)
class NoAnswer:
    """The request never got an HTTP answer."""

    kind: str
    """`refused` — nothing listens; `not_connected` — no connection in time; `timeout` —
    sent, no answer in time; `dropped` — sent, the connection broke before the answer."""
    error: str
    """The exception class, for the log."""
    detail: str


@dataclass(frozen=True)
class ErrorStatus:
    """The engine answered with an HTTP error status."""

    code: int
    body: str


@dataclass(frozen=True)
class Unusable:
    """The engine answered 200 with something the proxy cannot work with."""

    label: str
    """What was wrong, as a fixed word: `not-json`, `not-an-object`, `not-a-tool-list`,
    `empty-tool-list`."""
    detail: str = ""


Outcome = NoAnswer | ErrorStatus | Unusable


class EngineUnusable(Exception):
    """The engine answered 200 with something nothing can be routed by or read from."""

    def __init__(self, label: str, detail: str = "") -> None:
        super().__init__(f"{label}: {detail}" if detail else label)
        self.label = label
        self.detail = detail


def outcome_of(error: BaseException) -> Outcome | None:
    """The engine-side outcome an exception stands for; None when it is not the engine's."""
    if isinstance(error, httpx.HTTPStatusError):
        return ErrorStatus(error.response.status_code, error.response.text)
    if isinstance(error, httpx.ConnectError):
        return _no_answer("refused", error)
    if isinstance(error, (httpx.ConnectTimeout, httpx.PoolTimeout)):
        return _no_answer("not_connected", error)
    if isinstance(error, httpx.TimeoutException):
        return _no_answer("timeout", error)
    if isinstance(error, httpx.TransportError):
        return _no_answer("dropped", error)
    if isinstance(error, json.JSONDecodeError):
        return Unusable("not-json", str(error))
    if isinstance(error, EngineUnusable):
        return Unusable(error.label, error.detail)
    return None


def engine_failure(
    outcome: Outcome, *, url: str, asked_for: str, may_still_run: bool = False
) -> dict[str, Any]:
    """The answer the agent gets for `outcome` of the request for `asked_for`.

    `may_still_run` says the request could have started work the engine may still be
    doing — a mutation or a long operation the proxy does not repeat. If such a request
    reached the engine and its answer was lost, nobody knows whether the work began.
    """
    if isinstance(outcome, NoAnswer):
        if may_still_run and outcome.kind not in UNSENT:
            return {
                "status": "timeout" if outcome.kind == "timeout" else "dropped",
                "outcome": "unknown",
                "message": (
                    f"letapis-core received the request for {asked_for}, but its answer "
                    f"never arrived ({_said(outcome)}). The work may have started and may "
                    "still be going on, so do not call it again blindly: look at "
                    "get_indexing_progress, or read back whatever the call was meant to "
                    "change, and decide from what you see."
                ),
            }
        return {
            "status": "unavailable",
            "reason": outcome.kind,
            "message": (
                f"letapis-core at {url} gave no answer to the request for {asked_for} "
                f"({_said(outcome)}). That is all this says — nothing about whether "
                f"{asked_for} exists. Nothing was changed on the engine's side; call again "
                "in a moment, and if letapis-core stays silent, tell the user it needs to "
                "be started or checked."
            ),
        }
    if isinstance(outcome, ErrorStatus):
        body = outcome.body[:BODY_LIMIT]
        if outcome.code == 503:
            return {
                "status": "unavailable",
                "reason": "warming_up",
                "message": (
                    f"letapis-core reports a service is not ready: {body}. "
                    "The server may be warming up — retry in a few seconds."
                ),
            }
        return {
            "status": "engine_error",
            "code": outcome.code,
            "message": (
                f"letapis-core at {url} is up, but turned down the request for {asked_for} "
                f"with HTTP {outcome.code}: {body}. The cause sits on the engine's side and "
                "its own log names it; a 401 or a 403 usually means the proxy's api_key "
                f"does not match. Whether {asked_for} exists cannot be told from this — "
                "call again once the engine is put right."
            ),
        }
    detail = f": {outcome.detail[:BODY_LIMIT]}" if outcome.detail else ""
    return {
        "status": "engine_error",
        "message": (
            f"letapis-core at {url} answered the request for {asked_for}, but the answer "
            f"cannot be used ({outcome.label}{detail}). The engine is up and its answer is "
            "broken; its own log names the cause. Whether "
            f"{asked_for} exists cannot be told from this."
        ),
    }


def describe(outcome: Outcome) -> str:
    """The outcome in words, for the agent: it may quote what the engine said."""
    if isinstance(outcome, NoAnswer):
        return _said(outcome)
    if isinstance(outcome, ErrorStatus):
        return f"HTTP {outcome.code}: {outcome.body[:BODY_LIMIT]}"
    return f"{outcome.label}: {outcome.detail[:BODY_LIMIT]}" if outcome.detail else outcome.label


def log_fields(outcome: Outcome) -> str:
    """The outcome for the log on disk: its kind and code, and nothing the engine said."""
    if isinstance(outcome, NoAnswer):
        return f"kind={outcome.kind} error={outcome.error}"
    if isinstance(outcome, ErrorStatus):
        return f"kind=http code={outcome.code}"
    return f"kind=unusable what={outcome.label}"


def _no_answer(kind: str, error: BaseException) -> NoAnswer:
    return NoAnswer(kind, type(error).__name__, str(error) or type(error).__name__)


def _said(outcome: NoAnswer) -> str:
    words = {
        "refused": "connection refused",
        "not_connected": "could not connect in time",
        "timeout": "no answer in time",
        "dropped": "the connection broke before the answer",
    }[outcome.kind]
    return f"{words}: {outcome.detail}"
