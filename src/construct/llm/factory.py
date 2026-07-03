"""Model-agnostic LLM provider factory.

Single construction path that maps a ``ProviderConfig.type`` to a concrete
LangChain chat model. Both ``ask.domain`` and ``research.score`` build their
models through ``build_chat_model`` so provider selection lives in one place
(closes the spec-v04 line 546 hardcoded-``ChatAnthropic`` anti-pattern, D-01).

Optional vendors are lazy-imported inside their branch so a base install
(without the ``llm-openai`` extra) never crashes at import time — a missing
provider degrades to a clear ``GATE_PROVIDER_ERROR`` instead (D-02).
"""
from __future__ import annotations

from typing import Any

from construct.llm.config import ProviderConfig


def build_chat_model(cfg: ProviderConfig, *, temperature: float = 0.2) -> Any:
    """Map ``ProviderConfig.type`` to a constructed LangChain chat model.

    Args:
        cfg: Resolved provider configuration (type, model, max_tokens, ...).
        temperature: Sampling temperature threaded into the constructed model.

    Returns:
        A concrete LangChain chat model instance for ``cfg.type``.

    Raises:
        RuntimeError: With a ``GATE_PROVIDER_ERROR`` prefix when the provider's
            optional extra is not installed or the provider type is unknown.
            The message never contains API key values (T-09-06).
    """
    if cfg.type == "langchain_anthropic":
        from langchain_anthropic import ChatAnthropic

        # ChatAnthropic exposes `timeout` (alias of default_request_timeout) and
        # `base_url` (alias of anthropic_api_url). Thread both so a configured
        # self-hosted/proxy endpoint or request timeout is honoured (WR-02).
        kwargs: dict[str, Any] = dict(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            timeout=cfg.timeout_seconds,
            base_url=cfg.base_url,
        )
        # Newer models (e.g. Claude Sonnet 5) reject an explicit temperature;
        # omit it when the provider config opts out so we use the model default.
        if cfg.supports_temperature:
            kwargs["temperature"] = temperature
        return ChatAnthropic(**kwargs)

    if cfg.type == "langchain_openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "GATE_PROVIDER_ERROR: provider 'langchain_openai' requires the "
                "optional 'llm-openai' extra. Install: pip install 'construct[llm-openai]'"
            ) from exc

        # ChatOpenAI accepts `timeout` and `base_url` directly.
        oa_kwargs: dict[str, Any] = dict(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            timeout=cfg.timeout_seconds,
            base_url=cfg.base_url,
        )
        if cfg.supports_temperature:
            oa_kwargs["temperature"] = temperature
        return ChatOpenAI(**oa_kwargs)

    raise RuntimeError(f"GATE_PROVIDER_ERROR: unknown provider type '{cfg.type}'")
