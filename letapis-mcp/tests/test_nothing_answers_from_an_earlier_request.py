"""Nothing this proxy remembers may decide what a later call is allowed to see (69.1).

The engine decides who may read what, per request. This process sits in front of it and
keeps things between calls — that is what a proxy is for — and every one of those things
is a chance to answer the current call out of an earlier one. It happened once already:
a file fetched by a call that named a hidden copy was handed to the next call that named
nothing, from the cache, without the engine being asked at all. The leak was invisible
from the outside — same bytes, same shape, `cached: true` — and the only thing missing
from the second answer was the question nobody put.

So the state is enumerated here rather than in prose, and every name has to carry a
reason. The polarity is the point, and it is the one `NOT_PROCESSING_FIELDS` uses in the
engine: a global added to the proxy tomorrow fails this file by existing, and gets in
only by someone writing down what it holds and why holding it is safe. The list of what
is DANGEROUS would have been the other choice, and it is the list that gets forgotten.
"""
from __future__ import annotations

import inspect

import letapis_mcp.client as cli
import letapis_mcp.server as srv

#: Module state the proxy keeps between calls, and why each one cannot decide a
#: permission. Reviewed at Stage 69.1; a name here is a promise, not a description.
REVIEWED_SERVER_STATE = {
    # The HTTP client and the configuration: one connection pool and one settings
    # object. They say WHERE the engine is, never what a caller may read from it.
    "_client": "where the engine is",
    "_config": "settings read at startup",
    # The path handler owns the fetch cache. It no longer answers `fetch_file` — a
    # cached file is one the engine handed to ONE earlier request, and the permission
    # went with that request, not with the bytes. What it still answers is a MAPPING,
    # which is this head's own configuration about a tree already on its own disk.
    "_paths": "mapping (local tree) + a cache that is no longer a permission",
    # The engine's tool surface: names, schemas, descriptions. The same for every
    # caller by construction — the engine does not vary it per request — so a stale
    # copy can be wrong about the ENGINE and never about who may see a folder. Its
    # own staleness is guarded separately (`test_always_loaded_tools`).
    "_tools_cache": "the engine's tool surface, identical for every caller",
}

#: The same, one layer down. `_tool_routes` maps a tool name to the method and endpoint
#: it is called at — routing, not authorisation — and is dropped whenever the connection
#: proves stale (`test_connection_resilience`).
REVIEWED_CLIENT_STATE = {
    "config": "settings",
    "_client": "connection pool",
    "_tool_routes": "name -> (method, endpoint); routing, never permission",
    "_transport": "test seam for the pool",
    "retry_safe_not_declared": (
        "names this proxy calls retry-safe that the engine did not declare (58.33). "
        "A finding about the PROXY's own configuration, recomputed every time the "
        "route map is rebuilt. It gates nothing: no call consults it to decide "
        "whether to run, to retry, or what to return, so it cannot make a later "
        "request see anything an earlier one could not. It says a name answers to "
        "nothing — a statement about this proxy, never a permission about a caller."
    ),
}


def _module_state(module) -> set[str]:
    """Names the module keeps that are neither functions, classes, nor imports."""
    return {
        name
        for name, value in vars(module).items()
        if name.startswith("_")
        and not name.startswith("__")
        and not callable(value)
        and not isinstance(value, type)
        and not inspect.ismodule(value)
    }


def test_every_thing_the_server_keeps_has_been_reviewed():
    unreviewed = _module_state(srv) - set(REVIEWED_SERVER_STATE)

    assert not unreviewed, (
        f"new state kept between calls: {sorted(unreviewed)}. Say what it holds and why "
        "it cannot decide what a later call may see — or do not keep it."
    )


def _client_state() -> set[str]:
    """What one connection keeps, read off the assignments in its constructor."""
    src = inspect.getsource(cli.letapisClient.__init__)
    return {
        # The annotation travels with the name on an assignment like
        # `self._client: httpx.AsyncClient | None = None`, so it is cut off here —
        # otherwise the reviewed list would have to spell types it does not care about,
        # and a type change would read as new state.
        line.split("=")[0].strip().removeprefix("self.").split(":")[0].strip()
        for line in src.splitlines()
        if line.strip().startswith("self.")
    }


def test_every_thing_the_client_keeps_has_been_reviewed():
    unreviewed = _client_state() - set(REVIEWED_CLIENT_STATE)

    assert not unreviewed, (
        f"new per-connection state: {sorted(unreviewed)}. Same question as above."
    )


def test_the_server_list_is_not_a_list_of_things_that_stopped_existing():
    """The negative twin. A whitelist rots the other way too: a name left here after
    the state it described was removed makes the file look watchful while watching
    nothing, and the next reader trusts it."""
    assert set(REVIEWED_SERVER_STATE) <= _module_state(srv), (
        f"reviewed names the server no longer keeps: "
        f"{sorted(set(REVIEWED_SERVER_STATE) - _module_state(srv))}"
    )


def test_the_client_list_is_not_a_list_of_things_that_stopped_existing():
    """The same twin for the other list, and its absence was the point.

    One list had the reverse check and the other did not, so half this file could rot
    into a guard over nothing while the file as a whole read as watched. A pairing that
    holds in one place and not the other is worse than none: it is the reason nobody
    looks again.
    """
    assert set(REVIEWED_CLIENT_STATE) <= _client_state(), (
        f"reviewed names the client no longer keeps: "
        f"{sorted(set(REVIEWED_CLIENT_STATE) - _client_state())}"
    )
