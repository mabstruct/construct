"""Tests for ask.domain LangGraph L2 gate."""
from __future__ import annotations

from pathlib import Path

import pytest

# Tests to be implemented in Plan 02:
# - test_ask_domain_structure: answer + citations returned
# - test_domain_filtering: cards outside domain excluded
# - test_citation_confidence: per-card confidence propagated
# - test_provider_config: config load + override
# - test_timeout: graceful LLM failure handling
# - test_empty_context: no cards → no LLM call


class TestAskDomainStructure:
    """Placeholder — implemented in Plan 02."""

    def test_import_ask_domain(self) -> None:
        """Verify the ask_domain module will be importable once created."""
        try:
            from construct.llm import ask_domain  # noqa: F811
            assert hasattr(ask_domain, "build_ask_domain_graph")
            assert hasattr(ask_domain, "run_gate")
        except ImportError:
            pytest.skip("ask_domain module not yet created — Plan 02")


class TestProviderConfig:
    """Configuration loading and override tests."""

    def test_provider_config_default_loads(self) -> None:
        """Default config loads without errors."""
        from construct.llm.config import load_llm_config, DEFAULT_CONFIG_PATH
        cfg = load_llm_config(DEFAULT_CONFIG_PATH)
        assert cfg.default_gate == "ask.domain"
        assert "anthropic" in cfg.providers
        assert cfg.gates["ask.domain"].provider == "anthropic"
        assert cfg.gates["ask.domain"].temperature == 0.2
