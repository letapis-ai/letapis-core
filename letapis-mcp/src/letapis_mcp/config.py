"""Configuration management for letapis MCP.

Supports:
- Environment variables (LETAPIS_SERVER_URL, LETAPIS_API_KEY, etc.)
- Config file (YAML)
- Default values
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PathMapping:
    """Maps remote paths to local paths."""

    remote: str
    local: str


@dataclass
class FetchConfig:
    """Configuration for file fetching."""

    enabled: bool = False
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".letapis_cache")
    clear_on_start: bool = True


@dataclass
class ServerConfig:
    """Configuration for letapis-core server connection."""

    url: str = "http://localhost:3131"
    api_key: str | None = None
    timeout: int = 60


@dataclass
class PathsConfig:
    """Configuration for path handling."""

    mapping: list[PathMapping] = field(default_factory=list)
    fetch: FetchConfig = field(default_factory=FetchConfig)


@dataclass
class Config:
    """Main configuration for letapis MCP."""

    server: ServerConfig = field(default_factory=ServerConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    @classmethod
    def load(cls, config_path: str | None = None) -> Config:
        """Load configuration from environment and config file.

        Args:
            config_path: Explicit path to config file (highest priority).

        Priority (highest to lowest):
        1. Explicit config_path argument
        2. LETAPIS_CONFIG environment variable
        3. Default locations
        4. Environment variable overrides (always applied)
        5. Default values
        """
        config = cls()

        path_to_load: Path | None = None

        if config_path:
            # Explicit argument has highest priority
            path_to_load = Path(config_path)
        elif env_path := os.environ.get("LETAPIS_CONFIG"):
            path_to_load = Path(env_path)
        else:
            # Check default locations
            default_paths = [
                Path.home() / ".config" / "letapis-mcp" / "config.yaml",
                Path.home() / ".config" / "letapis-mcp" / "config.yml",
                Path.cwd() / ".letapis-mcp.yaml",
                Path.cwd() / ".letapis-mcp.yml",
            ]
            for path in default_paths:
                if path.exists():
                    path_to_load = path
                    break

        if path_to_load and path_to_load.exists():
            config = cls._load_from_file(path_to_load)

        config = cls._apply_env_overrides(config)

        return config

    @classmethod
    def _load_from_file(cls, path: Path) -> Config:
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> Config:
        """Create Config from dictionary."""
        config = cls()

        # Server config
        if "server" in data:
            server_data = data["server"]
            config.server.url = server_data.get("url", config.server.url)
            config.server.api_key = cls._expand_env(
                server_data.get("api_key", config.server.api_key)
            )
            config.server.timeout = server_data.get("timeout", config.server.timeout)

        # Paths config
        if "paths" in data:
            paths_data = data["paths"]

            # Path mapping
            if "mapping" in paths_data:
                config.paths.mapping = [
                    PathMapping(remote=m["remote"], local=m["local"])
                    for m in paths_data["mapping"]
                ]

            # Fetch config
            if "fetch" in paths_data:
                fetch_data = paths_data["fetch"]
                config.paths.fetch.enabled = fetch_data.get(
                    "enabled", config.paths.fetch.enabled
                )
                if "cache_dir" in fetch_data:
                    config.paths.fetch.cache_dir = Path(
                        os.path.expanduser(fetch_data["cache_dir"])
                    )
                config.paths.fetch.clear_on_start = fetch_data.get(
                    "clear_on_start", config.paths.fetch.clear_on_start
                )

        return config

    @classmethod
    def _apply_env_overrides(cls, config: Config) -> Config:
        """Apply environment variable overrides."""
        if url := os.environ.get("LETAPIS_SERVER_URL"):
            config.server.url = url

        if api_key := os.environ.get("LETAPIS_API_KEY"):
            config.server.api_key = api_key

        if timeout := os.environ.get("LETAPIS_TIMEOUT"):
            config.server.timeout = int(timeout)

        if cache_dir := os.environ.get("LETAPIS_CACHE_DIR"):
            config.paths.fetch.cache_dir = Path(os.path.expanduser(cache_dir))

        if os.environ.get("LETAPIS_FETCH_ENABLED", "").lower() in ("true", "1", "yes"):
            config.paths.fetch.enabled = True

        return config

    @staticmethod
    def _expand_env(value: str | None) -> str | None:
        """Expand ${VAR} patterns in string values."""
        if value is None:
            return None

        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var)

        return value
