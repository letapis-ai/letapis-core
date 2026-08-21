"""Path handling utilities for letapis MCP.

Handles:
- Path mapping (remote -> local)
- File fetching and caching
"""

from __future__ import annotations

import shutil
from pathlib import Path

from letapis_mcp.config import Config


class PathHandler:
    """Handles path mapping and file fetching."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._cache_initialized = False

    def init_cache(self) -> None:
        """Initialize cache directory.

        Clears cache if clear_on_start is enabled.
        """
        if self._cache_initialized:
            return

        cache_dir = self.config.paths.fetch.cache_dir

        if self.config.paths.fetch.clear_on_start and cache_dir.exists():
            shutil.rmtree(cache_dir)

        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_initialized = True

    def map_path(self, remote_path: str) -> str | None:
        """Map remote path to local path using configured mappings.

        Args:
            remote_path: Path as returned by letapis-core

        Returns:
            Local path if mapping exists, None otherwise
        """
        for mapping in self.config.paths.mapping:
            if remote_path.startswith(mapping.remote):
                relative = remote_path[len(mapping.remote) :].lstrip("/")
                local = Path(mapping.local) / relative
                if local.exists():
                    return str(local)
        return None

    def get_cache_path(self, remote_path: str) -> Path:
        """Get cache path for a remote file.

        Args:
            remote_path: Remote file path

        Returns:
            Path where file would be cached
        """
        self.init_cache()
        # Remove leading slash and create cache path
        relative = remote_path.lstrip("/")
        return self.config.paths.fetch.cache_dir / relative

    def save_to_cache(self, remote_path: str, content: bytes) -> Path:
        """Save file content to cache.

        Args:
            remote_path: Remote file path
            content: File content

        Returns:
            Local cache path
        """
        cache_path = self.get_cache_path(remote_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(content)
        return cache_path

    def resolve_path(self, remote_path: str) -> str:
        """Resolve remote path to local path.

        Tries:
        1. Path mapping (if configured)
        2. Cache (if file was fetched)
        3. Returns original path (caller can try fetch_file)

        Args:
            remote_path: Path as returned by letapis-core

        Returns:
            Local path (mapped, cached, or original)
        """
        # Try mapping first
        if mapped := self.map_path(remote_path):
            return mapped

        cache_path = self.get_cache_path(remote_path)
        if cache_path.exists():
            return str(cache_path)

        # Return original - caller should use fetch_file if needed
        return remote_path
