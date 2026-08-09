"""Tests for configuration loading."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from letapis_mcp.config import Config, PathMapping


class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_server_url(self) -> None:
        """Default server URL should be localhost:3131."""
        config = Config()
        assert config.server.url == "http://localhost:3131"

    def test_default_timeout(self) -> None:
        """Default timeout should be 60 seconds."""
        config = Config()
        assert config.server.timeout == 60

    def test_default_api_key_is_none(self) -> None:
        """API key should be None by default."""
        config = Config()
        assert config.server.api_key is None

    def test_default_fetch_disabled(self) -> None:
        """Fetch should be disabled by default."""
        config = Config()
        assert config.paths.fetch.enabled is False

    def test_default_cache_dir(self) -> None:
        """Default cache dir should be ~/.letapis_cache."""
        config = Config()
        assert config.paths.fetch.cache_dir == Path.home() / ".letapis_cache"


class TestConfigEnvOverrides:
    """Test environment variable overrides."""

    def test_server_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LETAPIS_SERVER_URL should override default."""
        monkeypatch.setenv("LETAPIS_SERVER_URL", "http://example.com:9000")
        config = Config.load()
        assert config.server.url == "http://example.com:9000"

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LETAPIS_API_KEY should set api_key."""
        monkeypatch.setenv("LETAPIS_API_KEY", "test-key-123")
        config = Config.load()
        assert config.server.api_key == "test-key-123"

    def test_timeout_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LETAPIS_TIMEOUT should override default."""
        monkeypatch.setenv("LETAPIS_TIMEOUT", "120")
        config = Config.load()
        assert config.server.timeout == 120

    def test_fetch_enabled_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LETAPIS_FETCH_ENABLED should enable fetch."""
        monkeypatch.setenv("LETAPIS_FETCH_ENABLED", "true")
        config = Config.load()
        assert config.paths.fetch.enabled is True

    def test_cache_dir_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LETAPIS_CACHE_DIR should override default."""
        monkeypatch.setenv("LETAPIS_CACHE_DIR", "/tmp/letapis-test-cache")
        config = Config.load()
        assert config.paths.fetch.cache_dir == Path("/tmp/letapis-test-cache")


class TestConfigYamlLoading:
    """Test YAML configuration file loading."""

    def test_load_from_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Load config from YAML file."""
        yaml_content = """
server:
  url: http://test-server:8000
  api_key: yaml-api-key
  timeout: 90

paths:
  mapping:
    - remote: /remote/path
      local: /local/path
  fetch:
    enabled: true
    cache_dir: /tmp/yaml-cache
    clear_on_start: false
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)
        monkeypatch.setenv("LETAPIS_CONFIG", str(config_file))

        config = Config.load()

        assert config.server.url == "http://test-server:8000"
        assert config.server.api_key == "yaml-api-key"
        assert config.server.timeout == 90
        assert len(config.paths.mapping) == 1
        assert config.paths.mapping[0].remote == "/remote/path"
        assert config.paths.mapping[0].local == "/local/path"
        assert config.paths.fetch.enabled is True
        assert config.paths.fetch.cache_dir == Path("/tmp/yaml-cache")
        assert config.paths.fetch.clear_on_start is False

    def test_env_overrides_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variables should override YAML values."""
        yaml_content = """
server:
  url: http://yaml-server:8000
  api_key: yaml-key
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)
        monkeypatch.setenv("LETAPIS_CONFIG", str(config_file))
        monkeypatch.setenv("LETAPIS_SERVER_URL", "http://env-server:9000")

        config = Config.load()

        # Env var should win
        assert config.server.url == "http://env-server:9000"
        # YAML should still apply for non-overridden values
        assert config.server.api_key == "yaml-key"


class TestConfigEnvExpansion:
    """Test ${VAR} expansion in YAML values."""

    def test_expand_env_in_api_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """${VAR} pattern in YAML should expand to env value."""
        yaml_content = """
server:
  url: http://test:8000
  api_key: ${TEST_API_KEY}
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)
        monkeypatch.setenv("LETAPIS_CONFIG", str(config_file))
        monkeypatch.setenv("TEST_API_KEY", "expanded-key-value")

        config = Config.load()

        assert config.server.api_key == "expanded-key-value"

    def test_expand_env_missing_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """${VAR} with missing env var should return None."""
        yaml_content = """
server:
  api_key: ${NONEXISTENT_VAR}
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)
        monkeypatch.setenv("LETAPIS_CONFIG", str(config_file))
        # Don't set NONEXISTENT_VAR

        config = Config.load()

        assert config.server.api_key is None
