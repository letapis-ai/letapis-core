"""Tests for path handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from letapis_mcp.config import Config, PathMapping, PathsConfig, FetchConfig
from letapis_mcp.paths import PathHandler


class TestPathMapping:
    """Test path mapping functionality."""

    def test_map_exact_prefix(self, tmp_path: Path) -> None:
        """Path with exact prefix should be mapped."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        (local_dir / "file.py").write_text("content")

        config = Config()
        config.paths.mapping = [PathMapping(remote="/remote", local=str(local_dir))]

        handler = PathHandler(config)
        result = handler.map_path("/remote/file.py")

        assert result == str(local_dir / "file.py")

    def test_map_nested_path(self, tmp_path: Path) -> None:
        """Nested paths should be mapped correctly."""
        local_dir = tmp_path / "local" / "nested"
        local_dir.mkdir(parents=True)
        (local_dir / "deep" / "file.py").mkdir(parents=True)
        (local_dir / "deep" / "file.py").rmdir()
        deep_dir = local_dir / "deep"
        deep_dir.mkdir(exist_ok=True)
        (deep_dir / "file.py").write_text("content")

        config = Config()
        config.paths.mapping = [PathMapping(remote="/workspace", local=str(local_dir))]

        handler = PathHandler(config)
        result = handler.map_path("/workspace/deep/file.py")

        assert result == str(deep_dir / "file.py")

    def test_map_no_match(self) -> None:
        """Non-matching path should return None."""
        config = Config()
        config.paths.mapping = [PathMapping(remote="/remote", local="/local")]

        handler = PathHandler(config)
        result = handler.map_path("/other/file.py")

        assert result is None

    def test_map_file_not_exists(self, tmp_path: Path) -> None:
        """Mapped path where file doesn't exist should return None."""
        config = Config()
        config.paths.mapping = [PathMapping(remote="/remote", local=str(tmp_path))]

        handler = PathHandler(config)
        result = handler.map_path("/remote/nonexistent.py")

        assert result is None

    def test_multiple_mappings_first_match(self, tmp_path: Path) -> None:
        """First matching mapping should be used."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "file.py").write_text("from dir1")

        config = Config()
        config.paths.mapping = [
            PathMapping(remote="/workspace", local=str(dir1)),
            PathMapping(remote="/workspace", local=str(dir2)),
        ]

        handler = PathHandler(config)
        result = handler.map_path("/workspace/file.py")

        assert result == str(dir1 / "file.py")


class TestPathCache:
    """Test file caching functionality."""

    def test_cache_path_structure(self, tmp_path: Path) -> None:
        """Cache path should mirror remote path structure."""
        config = Config()
        config.paths.fetch.cache_dir = tmp_path / "cache"

        handler = PathHandler(config)
        cache_path = handler.get_cache_path("/workspace/src/file.py")

        expected = tmp_path / "cache" / "workspace" / "src" / "file.py"
        assert cache_path == expected

    def test_save_to_cache(self, tmp_path: Path) -> None:
        """Save content to cache should create file."""
        config = Config()
        config.paths.fetch.cache_dir = tmp_path / "cache"

        handler = PathHandler(config)
        content = b"file content here"
        cache_path = handler.save_to_cache("/remote/file.py", content)

        assert cache_path.exists()
        assert cache_path.read_bytes() == content

    def test_init_cache_creates_dir(self, tmp_path: Path) -> None:
        """init_cache should create cache directory."""
        cache_dir = tmp_path / "new_cache"
        config = Config()
        config.paths.fetch.cache_dir = cache_dir
        config.paths.fetch.clear_on_start = False

        handler = PathHandler(config)
        handler.init_cache()

        assert cache_dir.exists()

    def test_init_cache_clears_on_start(self, tmp_path: Path) -> None:
        """init_cache with clear_on_start should remove existing files."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "old_file.txt").write_text("old content")

        config = Config()
        config.paths.fetch.cache_dir = cache_dir
        config.paths.fetch.clear_on_start = True

        handler = PathHandler(config)
        handler.init_cache()

        assert cache_dir.exists()
        assert not (cache_dir / "old_file.txt").exists()


class TestPathResolution:
    """Test resolve_path priority."""

    def test_resolve_uses_mapping_first(self, tmp_path: Path) -> None:
        """resolve_path should prefer mapping over cache."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        (local_dir / "file.py").write_text("local content")

        config = Config()
        config.paths.mapping = [PathMapping(remote="/remote", local=str(local_dir))]
        config.paths.fetch.cache_dir = tmp_path / "cache"

        handler = PathHandler(config)
        result = handler.resolve_path("/remote/file.py")

        assert result == str(local_dir / "file.py")

    def test_resolve_falls_back_to_cache(self, tmp_path: Path) -> None:
        """resolve_path should use cache if mapping doesn't match."""
        config = Config()
        config.paths.mapping = []
        config.paths.fetch.cache_dir = tmp_path / "cache"

        handler = PathHandler(config)
        handler.save_to_cache("/remote/file.py", b"cached")

        result = handler.resolve_path("/remote/file.py")

        assert result == str(tmp_path / "cache" / "remote" / "file.py")

    def test_resolve_returns_original_if_no_match(self) -> None:
        """resolve_path should return original path if nothing matches."""
        config = Config()
        config.paths.mapping = []

        handler = PathHandler(config)
        result = handler.resolve_path("/unknown/path/file.py")

        assert result == "/unknown/path/file.py"
