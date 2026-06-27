"""Tests for the model-agnostic LLM provider factory (build_chat_model)."""
from __future__ import annotations

import pytest

from construct.llm.config import ProviderConfig
from construct.llm.factory import build_chat_model


class TestAnthropicBranch:
    """type='langchain_anthropic' returns a configured ChatAnthropic."""

    def test_builds_anthropic_with_config_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returned model reflects config model/max_tokens and the passed temperature."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
        cfg = ProviderConfig(
            type="langchain_anthropic",
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
        )

        model = build_chat_model(cfg, temperature=0.2)

        from langchain_anthropic import ChatAnthropic

        assert isinstance(model, ChatAnthropic)
        assert model.model == "claude-sonnet-4-20250514"
        assert model.max_tokens == 4096
        assert model.temperature == 0.2

    def test_temperature_kwarg_is_threaded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-default temperature kwarg flows into the constructed model."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
        cfg = ProviderConfig(type="langchain_anthropic", model="claude-sonnet-4-20250514")

        model = build_chat_model(cfg, temperature=0.7)

        assert model.temperature == 0.7


class TestOpenAIMissingExtra:
    """type='langchain_openai' without the optional extra installed degrades cleanly."""

    def test_missing_openai_extra_raises_gate_provider_error(self) -> None:
        """langchain_openai absence raises GATE_PROVIDER_ERROR naming the llm-openai extra."""
        # langchain_openai is intentionally NOT installed in the offline venv.
        cfg = ProviderConfig(type="langchain_openai", model="gpt-4o")

        with pytest.raises(RuntimeError) as exc_info:
            build_chat_model(cfg)

        message = str(exc_info.value)
        assert message.startswith("GATE_PROVIDER_ERROR")
        assert "llm-openai" in message


class TestUnknownProvider:
    """Unknown/out-of-scope provider types raise a clear error."""

    def test_unknown_type_raises_gate_provider_error(self) -> None:
        """A bogus provider type raises GATE_PROVIDER_ERROR naming the type."""
        cfg = ProviderConfig(type="bogus-provider")

        with pytest.raises(RuntimeError) as exc_info:
            build_chat_model(cfg)

        message = str(exc_info.value)
        assert message.startswith("GATE_PROVIDER_ERROR")
        assert "bogus-provider" in message

    def test_out_of_scope_ollama_raises_gate_provider_error(self) -> None:
        """langchain_ollama is out of scope (D-02) and raises the unknown-provider error."""
        cfg = ProviderConfig(type="langchain_ollama")

        with pytest.raises(RuntimeError) as exc_info:
            build_chat_model(cfg)

        message = str(exc_info.value)
        assert message.startswith("GATE_PROVIDER_ERROR")
        assert "langchain_ollama" in message
