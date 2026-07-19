"""Tests for the public LLM config path resolver (resolve_llm_config_path)."""
from __future__ import annotations

from pathlib import Path

import pytest

from construct.llm.config import (
    DEFAULT_CONFIG_PATH,
    LlmConfig,
    load_llm_config,
    resolve_llm_config_path,
)


class TestResolveLlmConfigPath:
    """The resolver implements the documented precedence: explicit argument,
    then the CONSTRUCT_LLM_CONFIG environment variable, then the packaged default."""

    def test_explicit_argument_beats_environment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An explicit config_path wins even when CONSTRUCT_LLM_CONFIG is set."""
        monkeypatch.setenv("CONSTRUCT_LLM_CONFIG", str(tmp_path / "env.yaml"))
        explicit = tmp_path / "explicit.yaml"

        resolved = resolve_llm_config_path(explicit)

        assert resolved == explicit

    def test_environment_beats_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """With no argument, CONSTRUCT_LLM_CONFIG overrides the packaged default."""
        env_path = tmp_path / "env.yaml"
        monkeypatch.setenv("CONSTRUCT_LLM_CONFIG", str(env_path))

        resolved = resolve_llm_config_path()

        assert resolved == env_path
        assert resolved != DEFAULT_CONFIG_PATH

    def test_default_when_nothing_supplied(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no argument and no environment override, the packaged default applies."""
        monkeypatch.delenv("CONSTRUCT_LLM_CONFIG", raising=False)

        resolved = resolve_llm_config_path()

        assert resolved == DEFAULT_CONFIG_PATH


class TestLoadLlmConfigDelegation:
    """load_llm_config resolves through the same code path, so the ops UI and the
    loader cannot diverge on which config file is effective."""

    def test_load_llm_config_delegates_to_resolver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_llm_config calls resolve_llm_config_path exactly once."""
        calls: list[Path | None] = []

        def _recording_resolver(config_path: Path | None = None) -> Path:
            calls.append(config_path)
            return DEFAULT_CONFIG_PATH

        monkeypatch.setattr(
            "construct.llm.config.resolve_llm_config_path", _recording_resolver
        )

        config = load_llm_config()

        assert len(calls) == 1
        assert isinstance(config, LlmConfig)
