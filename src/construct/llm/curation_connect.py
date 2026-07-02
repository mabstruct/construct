"""curation.connection_type L3 gate — connection-typing judgment core (Phase 12, D-05).

Turns one ``bridge_detect`` candidate pair into a governance-reviewable
``ConnectionTypeDecision`` (a typed edge proposal) via a structured-output LLM
call (through the Plan 01 provider factory). The input is a *candidate pair*
(bridge_detect.py:233-244), NOT an existing ``ConnectionRecord`` — untyped
edges cannot persist (``ConnectionRecord.type`` is a required enum), so this
gate PROPOSES a NEW typed connection; it never retypes an existing edge and
never writes to the SOT. The actual connection-add write is a Plan 04
post-gate node (T-12-03).

Structurally identical to :mod:`construct.llm.curation_promote`'s fan-out. The
provider-error sanitizer and the outage error class are imported from
``curation_promote`` to avoid duplication (security-load-bearing, T-12-04).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from construct.llm import factory
from construct.llm.config import GateConfig, ProviderConfig, load_llm_config
from construct.llm.curation_promote import (
    CardEvaluateOutageError,
    _is_provider_outage_cause,
    _safe_scoring_cause,
)
from construct.schemas.workspace import ConnectionType


# ── Structured LLM output / connection-typing contract (Discrepancy 2) ──


class ConnectionTypeDecision(BaseModel):
    """A typed-connection proposal for one bridge candidate pair.

    ``connection_type`` is a REQUIRED ``ConnectionType`` enum — there is no
    ``None`` option, because a null-typed edge cannot persist (Discrepancy 2).
    """

    model_config = {"extra": "forbid"}

    from_card_id: str
    to_card_id: str
    connection_type: ConnectionType
    reasoning: str


# ── Provider seam (routed through the shared Plan 01 factory monkeypatch) ──


def build_typing_llm(provider_cfg: ProviderConfig, gate_cfg: GateConfig) -> Any:
    """Construct the connection-typing chat model through the shared factory.

    Routed via ``factory.build_chat_model`` so the shared test monkeypatch on
    ``construct.llm.factory.build_chat_model`` covers this gate too.
    """
    return factory.build_chat_model(provider_cfg, temperature=gate_cfg.temperature)


# ── Prompt assembly ──


def _build_messages(candidate: dict) -> list:
    """Assemble system+user messages for one candidate pair's typing judgment.

    Untrusted card titles/categories are included only as data; the output is
    constrained to ``ConnectionTypeDecision`` (``extra="forbid"``), so a
    malicious title cannot add a write surface (T-12-03).
    """
    valid_types = ", ".join(ct.value for ct in ConnectionType)
    shared = ", ".join(candidate.get("l2_shared_categories") or [])
    system = SystemMessage(
        content=(
            "You are a knowledge-graph connection typer. Given a candidate pair "
            "of cards, choose the single best connection type describing how the "
            "FROM card relates to the TO card. Return a structured decision:\n"
            "- connection_type: one of " + valid_types + "\n"
            "- reasoning: a concise rationale for the chosen type\n\n"
            "You only PROPOSE a typed edge; a human review gate applies any write."
        )
    )
    user = HumanMessage(
        content=(
            f"From card id: {candidate.get('from_card_id')}\n"
            f"From title: {candidate.get('from_title')}\n"
            f"From domain: {candidate.get('from_domain')}\n"
            f"To card id: {candidate.get('to_card_id')}\n"
            f"To title: {candidate.get('to_title')}\n"
            f"To domain: {candidate.get('to_domain')}\n"
            f"Shared categories: {shared}\n"
        )
    )
    return [system, user]


# ── Single-candidate typing ──


def type_one(candidate: dict, *, llm: Any) -> ConnectionTypeDecision:
    """Type one bridge candidate pair into a ``ConnectionTypeDecision``.

    The LLM proposes the connection type; the gate deterministically stamps
    ``from_card_id``/``to_card_id`` from the input candidate (never trusting the
    model to identify which pair it typed). ``llm`` is supplied already-built so
    the call is offline-testable.
    """
    structured_llm = llm.with_structured_output(ConnectionTypeDecision, method="json_schema")
    messages = _build_messages(candidate)
    raw: ConnectionTypeDecision = structured_llm.invoke(messages)
    return raw.model_copy(
        update={
            "from_card_id": candidate.get("from_card_id"),
            "to_card_id": candidate.get("to_card_id"),
        }
    )


def _type_one_with_retry(
    candidate: dict, *, llm: Any
) -> tuple[ConnectionTypeDecision | None, int, BaseException | None]:
    """Type one candidate with a single retry; return (decision|None, retried, error).

    A still-failing candidate after one retry is DROPPED (returns ``None``) — no
    invalid connection is ever proposed.
    """
    retried = 0
    last_exc: BaseException | None = None
    for attempt in range(2):
        try:
            decision = type_one(candidate, llm=llm)
            return decision, retried, None
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                retried = 1
    return None, retried, last_exc


@dataclass
class TypeAllCounters:
    """Batch typing counters."""

    pairs_total: int = 0
    typed_ok: int = 0
    retried: int = 0
    errors: int = 0
    degraded: bool = False


@dataclass
class TypeAllResult:
    """Result of bounded fan-out typing over a candidate list."""

    decisions: list[ConnectionTypeDecision] = field(default_factory=list)
    counters: TypeAllCounters = field(default_factory=TypeAllCounters)
    total_outage: bool = False
    outage_message: str | None = None


def type_all(candidates: list[dict], *, llm: Any, cap: int) -> TypeAllResult:
    """Type a batch with bounded concurrency, per-item retry, and outage detection.

    Reuses the same retry + total-outage discrimination as ``card.evaluate``.
    ``typed_ok == 0 and provider_failures == len(items)`` promotes a silent
    all-failure into an explicit total outage. Still-failing candidates are
    dropped, never proposed as invalid connections.
    """
    if not candidates:
        return TypeAllResult(
            decisions=[],
            counters=TypeAllCounters(pairs_total=0),
        )

    ordered: list[ConnectionTypeDecision | None] = [None] * len(candidates)
    retried_total = 0
    errors = 0
    typed_ok = 0
    provider_failures = 0

    def _worker(index: int, candidate: dict):
        decision, item_retried, exc = _type_one_with_retry(candidate, llm=llm)
        return index, decision, item_retried, exc

    workers = max(1, min(cap, len(candidates)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_worker, idx, candidate)
            for idx, candidate in enumerate(candidates)
        ]
        for future in as_completed(futures):
            index, decision, item_retried, exc = future.result()
            ordered[index] = decision
            retried_total += item_retried
            if exc is not None:
                errors += 1
                if _is_provider_outage_cause(exc):
                    provider_failures += 1
            else:
                typed_ok += 1

    if typed_ok == 0 and provider_failures == len(candidates):
        return TypeAllResult(
            decisions=[],
            counters=TypeAllCounters(
                pairs_total=len(candidates),
                typed_ok=0,
                retried=retried_total,
                errors=errors,
                degraded=True,
            ),
            total_outage=True,
            outage_message=(
                "All connection typings failed due to provider authentication "
                "or configuration error"
            ),
        )

    decisions = [d for d in ordered if d is not None]
    return TypeAllResult(
        decisions=decisions,
        counters=TypeAllCounters(
            pairs_total=len(candidates),
            typed_ok=typed_ok,
            retried=retried_total,
            errors=errors,
            degraded=errors > 0,
        ),
    )


def run_gate(
    gate_id: str,
    candidates: list[dict],
    *,
    provider_override: str | None = None,
    config_path: Any = None,
) -> TypeAllResult:
    """Run the connection-typing gate: resolve config, fan out over candidates.

    Resolves gate config under id ``curation.connection_type`` so it does not
    fall back to the ``research.score`` provider/cap. This gate only PROPOSES
    typed edges; the actual connection-add write is a Plan 04 post-gate node.
    """
    config = load_llm_config(config_path)
    gate_cfg = config.gates.get(gate_id, config.gates.get("research.score"))
    if gate_cfg is None:
        raise RuntimeError(f"GATE_PROVIDER_ERROR: unknown gate '{gate_id}'")

    provider_key = provider_override or gate_cfg.provider
    provider_cfg = config.providers.get(provider_key, config.providers["anthropic"])
    llm = build_typing_llm(provider_cfg, gate_cfg)

    batch = type_all(candidates, llm=llm, cap=gate_cfg.concurrency_cap)

    if batch.total_outage:
        raise CardEvaluateOutageError(
            batch.outage_message
            or "Provider outage during curation.connection_type batch"
        )

    return batch
