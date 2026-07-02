"""card.evaluate L3 gate — card promotion judgment core (Phase 12, CUR-02).

Turns one non-mature knowledge card into a governance-reviewable
``PromotionDecision`` (promote / hold / escalate) via a structured-output LLM
call (through the Plan 01 provider factory). Unlike ``research.score`` there is
no relevance-band ceiling-clamp — promotion has no numeric band; the *human
review gate* (Plans 03-04) is the write constraint. This module only PROPOSES;
it never writes to the workspace SOT (T-12-03).

Symbol-for-symbol sibling of ``construct.llm.research_score``:
``score_one`` → :func:`evaluate_one`, ``_score_one_with_retry`` →
:func:`_evaluate_one_with_retry`, ``score_all`` → :func:`evaluate_all`, plus
:func:`run_gate`, the outage error class, and the verbatim provider-error
sanitizer (security-load-bearing, T-12-04 / WR-06 — never echo raw provider
text).

Models are defined IN this module (not ``catalog.py``) to avoid the
circular-import hazard between the capability catalog and the gate runner.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from construct.llm import factory
from construct.llm.config import GateConfig, ProviderConfig, load_llm_config
from construct.schemas.card import Lifecycle
from construct.storage.workspace import WorkspaceLoader


# ── Structured LLM output / promotion contract (spec §6.4) ──


class PromotionDecision(BaseModel):
    """A governance-reviewable promotion proposal for one card.

    Used both as the ``with_structured_output`` target (the LLM's raw proposal)
    and as the decision returned by :func:`evaluate_one`. ``target_lifecycle``
    is constrained to the two promotion bands (``seed→growing`` and
    ``growing→mature``); ``archived`` is a SEPARATE decay write type, never a
    promotion target (Discrepancy 1) — ``seedling`` does not exist.
    """

    model_config = {"extra": "forbid"}

    card_id: str
    decision: Literal["promote", "hold", "escalate"]
    target_lifecycle: Literal["growing", "mature"] | None = None
    reasoning: str
    method: Literal["rule-based", "llm-judgment"] = "llm-judgment"


# ── Gate I/O models (defined here to avoid circular import with catalog.py) ──


class GateMetadata(BaseModel):
    """Metadata about the gate invocation (L3 tier for card.evaluate)."""

    model_config = {"extra": "forbid"}
    gate_id: str
    tier: str = "L3"
    review_required: bool = True
    review_status: str = "pending"
    provider: str = ""
    model: str = ""


class CardEvaluateInput(BaseModel):
    """Input for the card.evaluate gate.

    ``workspace_path`` is required so the non-mature cards can be loaded
    read-only. This is the thin capability-input model that Plan 05's
    ``card.evaluate`` shim constructs and hands to :func:`run_gate`; it must
    exist and be importable so that plan does not reference an undefined class.
    """

    model_config = {"extra": "forbid"}
    workspace_path: str
    provider_override: str | None = None


class CardEvaluateGateOutput(BaseModel):
    """Canonical card.evaluate result: decisions + gate metadata + retrieval."""

    model_config = {"extra": "forbid"}
    decisions: list[PromotionDecision] = Field(default_factory=list)
    gate: GateMetadata = Field(default_factory=lambda: GateMetadata(gate_id="card.evaluate"))
    retrieval: dict = Field(default_factory=dict)


# ── Provider seam (routed through the shared Plan 01 factory monkeypatch) ──


def build_scoring_llm(provider_cfg: ProviderConfig, gate_cfg: GateConfig) -> Any:
    """Construct the evaluation chat model through the shared Plan 01 factory.

    Routed via ``factory.build_chat_model`` so the shared test monkeypatch on
    ``construct.llm.factory.build_chat_model`` covers this gate too.
    """
    return factory.build_chat_model(provider_cfg, temperature=gate_cfg.temperature)


# ── Candidate pre-filter (D-02) ──


def _lifecycle_value(card: dict) -> str | None:
    """Normalize a card's lifecycle to its string value (enum or str tolerant)."""
    lifecycle = card.get("lifecycle")
    return getattr(lifecycle, "value", lifecycle)


def is_promotion_candidate(card: dict) -> bool:
    """A card is a promotion candidate iff it is not mature and not archived (D-02).

    ``mature`` has nowhere left to be promoted; ``archived`` is out of scope for
    promotion entirely. Applied deterministically BEFORE the LLM fan-out,
    mirroring the archived-exclusion guard at ``curation_run.py:317``.
    """
    value = _lifecycle_value(card)
    return value not in (Lifecycle.mature.value, Lifecycle.archived.value)


# ── Prompt assembly ──


def _build_messages(card: dict) -> list:
    """Assemble system+user messages for one card's promotion judgment.

    Untrusted card body/title content is included only as data; the output is
    constrained to ``PromotionDecision`` (``extra="forbid"``), so a malicious
    card body cannot escalate privilege or add a write surface (T-12-03).
    """
    system = SystemMessage(
        content=(
            "You are a knowledge-curation assistant. Judge whether ONE card is "
            "ready to advance its lifecycle band. Return a structured decision:\n"
            "- decision: promote | hold | escalate\n"
            "- target_lifecycle: growing | mature | null (only when promoting; "
            "seed→growing or growing→mature only; never archived)\n"
            "- reasoning: a concise rationale\n"
            "- method: llm-judgment\n\n"
            "Promote only when the card is well-supported and coherent for its "
            "next band. Hold when it is not yet ready. Escalate when the card is "
            "ambiguous or needs human judgment. You only PROPOSE; a human review "
            "gate applies any write."
        )
    )
    user = HumanMessage(
        content=(
            f"Card id: {card.get('id')}\n"
            f"Title: {card.get('title')}\n"
            f"Current lifecycle: {_lifecycle_value(card)}\n"
            f"Confidence: {card.get('confidence')}\n"
            f"Source tier: {card.get('source_tier')}\n"
            f"Content categories: {', '.join(card.get('content_categories') or [])}\n"
            f"Body:\n{card.get('body')}\n"
        )
    )
    return [system, user]


# ── Single-card evaluation ──


def evaluate_one(card: dict, *, llm: Any) -> PromotionDecision:
    """Evaluate one card into a ``PromotionDecision``.

    The LLM proposes the decision; the gate deterministically stamps
    ``card_id`` from the input card (never trusting the model to identify which
    card it judged). ``llm`` is supplied already-built so the call is
    offline-testable; :func:`run_gate` constructs it via
    :func:`build_scoring_llm`.
    """
    structured_llm = llm.with_structured_output(PromotionDecision, method="json_schema")
    messages = _build_messages(card)
    raw: PromotionDecision = structured_llm.invoke(messages)
    return raw.model_copy(update={"card_id": card.get("id")})


# ── Error sanitization + outage discrimination (T-12-04, WR-06) ──


class CardEvaluateOutageError(Exception):
    """Total provider/auth outage — every item failed on a provider-level cause."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.safe_message = message


# Auth-phrase markers are specific enough that bare substring containment is
# acceptable. Numeric HTTP codes are matched with word boundaries instead (see
# below) so a "401"/"403" embedded in a token count or a scraped page echoed
# into the message does not trip a false provider outage (WR-06).
_PROVIDER_OUTAGE_PHRASES = (
    "authentication",
    "auth failed",
    "api key",
    "api_key",
    "unauthorized",
)
_PROVIDER_OUTAGE_CODES = ("401", "403")
# Known provider auth/permission exception class names (matched across the MRO
# so vendor subclasses are covered without importing optional SDKs).
_AUTH_ERROR_TYPE_NAMES = frozenset(
    {
        "AuthenticationError",
        "PermissionDeniedError",
        "PermissionError",
    }
)
_CODE_BOUNDARY_PATTERN = re.compile(
    r"\b(" + "|".join(_PROVIDER_OUTAGE_CODES) + r")\b"
)


def _is_provider_outage_cause(exc: BaseException) -> bool:
    """Classify whether an exception indicates provider/auth/config failure.

    Prefer unambiguous signals: the explicit ``GATE_PROVIDER_ERROR`` prefix the
    factory/gate raise, the exception *type* for known auth/permission errors,
    word-boundary auth phrases, and word-boundary numeric HTTP codes. Bare
    substring containment of codes like ``401``/``403`` is deliberately avoided
    so a non-provider failure whose message merely mentions one of those tokens
    is not misclassified as a provider auth outage (WR-06).
    """
    text = str(exc)
    if "GATE_PROVIDER_ERROR" in text:
        return True

    for klass in type(exc).__mro__:
        if klass.__name__ in _AUTH_ERROR_TYPE_NAMES:
            return True

    lowered = text.lower()
    if any(phrase in lowered for phrase in _PROVIDER_OUTAGE_PHRASES):
        return True
    return bool(_CODE_BOUNDARY_PATTERN.search(lowered))


def _safe_scoring_cause(exc: BaseException) -> str:
    """Return a key-safe cause string — never echo raw provider exception text."""
    name = exc.__class__.__name__
    if _is_provider_outage_cause(exc):
        return f"{name}: provider authentication or configuration error"
    return f"{name}: evaluation failed"


def _escalate_decision_for_failure(card: dict, safe_cause: str) -> PromotionDecision:
    """Build a rule-based ESCALATE when per-card evaluation fails after retry (D-03).

    A still-failing card never silently drops and never fabricates an
    llm-judgment verdict — it becomes a human-reviewable escalation carrying a
    pre-sanitized safe cause.
    """
    return PromotionDecision(
        card_id=card.get("id"),
        decision="escalate",
        target_lifecycle=None,
        reasoning=f"card_evaluation_failed: {safe_cause}",
        method="rule-based",
    )


def _evaluate_one_with_retry(
    card: dict, *, llm: Any
) -> tuple[PromotionDecision, int, BaseException | None]:
    """Evaluate one card with a single retry; return (decision, retried, error)."""
    retried = 0
    last_exc: BaseException | None = None
    for attempt in range(2):
        try:
            decision = evaluate_one(card, llm=llm)
            return decision, retried, None
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                retried = 1
    assert last_exc is not None
    return (
        _escalate_decision_for_failure(card, _safe_scoring_cause(last_exc)),
        retried,
        last_exc,
    )


@dataclass
class EvaluateAllCounters:
    """Batch evaluation counters echoed in retrieval (D-03)."""

    cards_total: int = 0
    evaluated_ok: int = 0
    retried: int = 0
    errors: int = 0
    degraded: bool = False


@dataclass
class EvaluateAllResult:
    """Result of bounded fan-out evaluation over a card list."""

    decisions: list[PromotionDecision] = field(default_factory=list)
    counters: EvaluateAllCounters = field(default_factory=EvaluateAllCounters)
    total_outage: bool = False
    outage_message: str | None = None


def evaluate_all(cards: list[dict], *, llm: Any, cap: int) -> EvaluateAllResult:
    """Evaluate a batch with bounded concurrency, per-card retry, and outage detection.

    Applies the D-02 candidate pre-filter (skip mature + archived) BEFORE the
    fan-out. ``scored_ok == 0 and provider_failures == len(items)`` promotes a
    silent all-failure into an explicit total outage rather than an all-escalate
    "success" (mirrors ``research_score.score_all``).
    """
    items = [card for card in cards if is_promotion_candidate(card)]
    if not items:
        return EvaluateAllResult(
            decisions=[],
            counters=EvaluateAllCounters(cards_total=0),
        )

    ordered: list[PromotionDecision | None] = [None] * len(items)
    retried_total = 0
    errors = 0
    evaluated_ok = 0
    provider_failures = 0

    def _worker(index: int, card: dict) -> tuple[int, PromotionDecision, int, BaseException | None]:
        decision, item_retried, exc = _evaluate_one_with_retry(card, llm=llm)
        return index, decision, item_retried, exc

    workers = max(1, min(cap, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_worker, idx, card)
            for idx, card in enumerate(items)
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
                evaluated_ok += 1

    if evaluated_ok == 0 and provider_failures == len(items):
        return EvaluateAllResult(
            decisions=[],
            counters=EvaluateAllCounters(
                cards_total=len(items),
                evaluated_ok=0,
                retried=retried_total,
                errors=errors,
                degraded=True,
            ),
            total_outage=True,
            outage_message=(
                "All card evaluations failed due to provider authentication "
                "or configuration error"
            ),
        )

    decisions = [d for d in ordered if d is not None]
    return EvaluateAllResult(
        decisions=decisions,
        counters=EvaluateAllCounters(
            cards_total=len(items),
            evaluated_ok=evaluated_ok,
            retried=retried_total,
            errors=errors,
            degraded=errors > 0,
        ),
    )


def run_gate(
    gate_id: str,
    input_data: CardEvaluateInput,
    *,
    config_path: Any = None,
) -> CardEvaluateGateOutput:
    """Run the card.evaluate gate: resolve config, load cards, fan out, assemble output."""
    config = load_llm_config(config_path)
    gate_cfg = config.gates.get(gate_id, config.gates.get("research.score"))
    if gate_cfg is None:
        raise RuntimeError(f"GATE_PROVIDER_ERROR: unknown gate '{gate_id}'")

    provider_key = input_data.provider_override or gate_cfg.provider
    provider_cfg = config.providers.get(provider_key, config.providers["anthropic"])

    cards = WorkspaceLoader(input_data.workspace_path).load_cards()
    llm = build_scoring_llm(provider_cfg, gate_cfg)

    batch = evaluate_all(cards, llm=llm, cap=gate_cfg.concurrency_cap)

    if batch.total_outage:
        raise CardEvaluateOutageError(
            batch.outage_message
            or "Provider outage during card.evaluate batch"
        )

    return CardEvaluateGateOutput(
        decisions=batch.decisions,
        gate=GateMetadata(gate_id=gate_id, provider=provider_key, model=provider_cfg.model),
        retrieval={
            "cards_total": batch.counters.cards_total,
            "evaluated_ok": batch.counters.evaluated_ok,
            "retried": batch.counters.retried,
            "errors": batch.counters.errors,
            "degraded": batch.counters.degraded,
        },
    )
