"""Two different answers stop arriving as one (69.1, round 5 tail).

`resolve_path` fused «this engine path IS my path on disk» with «I downloaded this file
once», and returned a bare string either way. Nothing in the answer said which had
happened.

**That fusion is not a tidiness complaint — it is how the leak of round 3 survived
three review rounds.** While both answers looked identical, the argument «nothing enters
the cache without the engine granting a read» read as an argument about BOTH, and the
half it was false about was the half nobody could see.

The two facts differ in what a reader may conclude:

* a MAPPING says the head already has this tree on its own disk. It could open the file
  with no proxy at all, and the engine has no say in that;
* a CACHE hit says the proxy downloaded the file at some earlier moment, under a
  permission asked then and possibly not valid now. It is a snapshot, and it can be
  stale.

Told apart, they can be named. Fused, `local_path` meant «somewhere local» and a head
could not tell live source from an old download.
"""

from __future__ import annotations

from pathlib import Path

from letapis_mcp.config import Config, PathMapping
from letapis_mcp.paths import PathHandler


def _handler(tmp_path: Path, *, mapped: Path | None = None) -> PathHandler:
    config = Config()
    config.paths.mapping = (
        [PathMapping(remote="/remote", local=str(mapped))] if mapped else []
    )
    config.paths.fetch.cache_dir = tmp_path / "cache"
    return PathHandler(config)


class TestTheTwoAnswersAreAskedSeparately:
    def test_a_mapping_is_not_reported_by_the_cache_question(self, tmp_path: Path):
        """The negative half of the pair below, and the one that matters: if
        `cached_path` also answered for mappings, splitting them would have changed
        nothing — the caller would still be unable to tell the two apart."""
        local = tmp_path / "local"
        local.mkdir()
        (local / "file.py").write_text("live source")
        handler = _handler(tmp_path, mapped=local)

        assert handler.map_path("/remote/file.py") == str(local / "file.py")
        assert handler.cached_path("/remote/file.py") is None

    def test_a_cached_file_is_not_reported_by_the_mapping_question(self, tmp_path: Path):
        handler = _handler(tmp_path)
        handler.save_to_cache("/remote/file.py", b"a download")

        assert handler.map_path("/remote/file.py") is None
        assert handler.cached_path("/remote/file.py") == str(
            tmp_path / "cache" / "remote" / "file.py"
        )

    def test_neither_answers_for_a_path_it_has_never_seen(self, tmp_path: Path):
        handler = _handler(tmp_path)

        assert handler.map_path("/unknown/file.py") is None
        assert handler.cached_path("/unknown/file.py") is None

    def test_the_fused_answer_is_gone_rather_than_renamed(self, tmp_path: Path):
        """A name that says «names, not grants» is a promise the next reader may skip,
        and the fused answer would still not say WHICH fact answered. Removed instead:
        a door that is not there cannot be walked through by someone in a hurry."""
        assert not hasattr(_handler(tmp_path), "resolve_path"), (
            "the fused answer is still callable — it will be called"
        )


class TestTheSearchAnswerSaysWhichOne:
    @staticmethod
    def _transform(handler: PathHandler, path: str) -> dict:
        import letapis_mcp.server as srv

        srv._paths = handler
        return srv._transform_search_results({"results": [{"path": path}]})

    def test_a_mapped_hit_is_named_as_mapping(self, tmp_path: Path):
        local = tmp_path / "local"
        local.mkdir()
        (local / "file.py").write_text("live source")
        handler = _handler(tmp_path, mapped=local)

        item = self._transform(handler, "/remote/file.py")["results"][0]

        assert item["local_path"] == str(local / "file.py")
        assert item["local_path_source"] == "mapping"

    def test_a_cached_hit_is_named_as_cache(self, tmp_path: Path):
        """The half the whole round is about: a head reading `local_path` learns this is
        a copy downloaded earlier, not the tree it is working in."""
        handler = _handler(tmp_path)
        handler.save_to_cache("/remote/file.py", b"a download")

        item = self._transform(handler, "/remote/file.py")["results"][0]

        assert item["local_path_source"] == "cache"

    def test_a_hit_with_no_local_answer_is_left_alone(self, tmp_path: Path):
        """Neither key appears when neither question answered — an empty `local_path`
        would read as «there is a local copy and it is nowhere»."""
        item = self._transform(_handler(tmp_path), "/unknown/file.py")["results"][0]

        assert "local_path" not in item
        assert "local_path_source" not in item

    def test_the_search_answer_prefers_the_mapping(self, tmp_path: Path):
        """When both answer, the head's own tree wins — and the answer says so.

        This is the priority `resolve_path` used to hold, moved to where it is visible.
        It is the right way round: the mapping is the file as it is NOW on the head's
        disk, the cache is what the proxy downloaded at some earlier moment. Preferring
        the cache would hand a head a stale copy of a file it is editing.
        """
        local = tmp_path / "local"
        local.mkdir()
        (local / "file.py").write_text("live source")
        handler = _handler(tmp_path, mapped=local)
        handler.save_to_cache("/remote/file.py", b"an older download")

        item = self._transform(handler, "/remote/file.py")["results"][0]

        assert item["local_path"] == str(local / "file.py")
        assert item["local_path_source"] == "mapping"
