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

    def cached_path(self, remote_path: str) -> str | None:
        """This file's earlier DOWNLOAD, if the proxy holds one — never a mapping.

        The other half of what `resolve_path` used to answer in one breath. The two are
        different facts and license different conclusions:

        * a mapping says the head already holds this tree on its own disk — it could
          open the file with no proxy at all, and the engine has no say in that;
        * a cache hit says the proxy downloaded the file at some earlier moment, under a
          permission asked THEN. It is a snapshot, and it may be stale.

        Fused, both arrived as a bare string and nothing said which. That is how
        «nothing enters the cache without the engine granting a read» came to be read as
        an argument about both — and the half it was false about was the half nobody
        could see. The leak of round 3 lived behind that sentence for three review
        rounds.

        `resolve_path` is not renamed but GONE. A name promising «this only names, it
        does not grant» is a promise the next reader may skip, and a fused answer would
        still not say WHICH fact answered — which is the defect itself, not its label. A
        door that is not there cannot be walked through by somebody in a hurry.
        """
        cache_path = self.get_cache_path(remote_path)
        return str(cache_path) if cache_path.exists() else None
