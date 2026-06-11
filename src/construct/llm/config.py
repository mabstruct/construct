"""LLM provider and gate configuration loader (YAML → Pydantic)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import ruamel.yaml
from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """LLM provider configuration."""
    model_config = {"extra": "forbid"}
    type: str = "langchain_anthropic"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    timeout_seconds: int = 60
    base_url: str | None = None


class GateConfig(BaseModel):
    """Single gate (e.g. ask.domain) configuration."""
    model_config = {"extra": "forbid"}
    provider: str = "anthropic"
    temperature: float = 0.2
    review_required: bool = True


class LlmConfig(BaseModel):
    """Top-level LLM configuration loaded from YAML."""
    model_config = {"extra": "forbid"}
    version: int = 1
    default_gate: str = "ask.domain"
    providers: dict[str, ProviderConfig] = Field(default_factory=lambda: {
        "anthropic": ProviderConfig(),
    })
    gates: dict[str, GateConfig] = Field(default_factory=lambda: {
        "ask.domain": GateConfig(),
    })


DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
_ENV_CONFIG_OVERRIDE = "CONSTRUCT_LLM_CONFIG"


def _load_yaml(path: Path) -> dict[str, Any]:
    yaml = ruamel.yaml.YAML(typ="safe")
    with open(path, encoding="utf-8") as f:
        data = yaml.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"LLM config is not a dict: {path}")
    return data


def load_llm_config(config_path: Path | None = None) -> LlmConfig:
    """Load LLM provider config from YAML.

    Resolution order:
    1. ``config_path`` argument (explicit override)
    2. ``CONSTRUCT_LLM_CONFIG`` environment variable
    3. ``src/construct/llm/config.yaml`` (default)
    """
    path = config_path
    if path is None:
        env_path = os.environ.get(_ENV_CONFIG_OVERRIDE)
        if env_path:
            path = Path(env_path)
    if path is None:
        path = DEFAULT_CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"GATE_PROVIDER_ERROR: LLM config not found at {path}. "
            f"Create src/construct/llm/config.yaml or set "
            f"{_ENV_CONFIG_OVERRIDE} environment variable."
        )

    data = _load_yaml(path)
    return LlmConfig(**data)
