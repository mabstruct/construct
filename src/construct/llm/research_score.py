"""research.score L3 gate — single-result scoring core (Plan 02).

Turns one normalized Phase-8 ``SearchResult`` into a governance-aware
``ScoredFinding`` via a structured-output LLM call (through the Plan 01
provider factory), then deterministically ceiling-clamps the LLM's
``ingest_action`` against governance bands so the model can only ever be *more*
conservative than governance allows (D-05). Governance thresholds are echoed
into the gate's retrieval block so they are provable offline (D-06), and the
workspace taxonomy is loaded read-only and soft-injected into the prompt
(D-11/D-12).

Hard boundary: this gate is read-only. It never writes to the workspace SOT
(T-09-05) — taxonomy/governance loads use ``WorkspaceLoader`` reads only.

Models are defined IN this module (not ``catalog.py``) to avoid the
circular-import hazard between the capability catalog and the gate runner.

The bounded fan-out, per-item retry/skip (D-08), total-outage promotion
(D-09), and the ``run_gate`` runner are intentionally deferred to Plan 03 —
this module exposes the seams those layers compose: ``score_one``, the
governance/taxonomy loaders, ``build_scoring_llm``, and ``build_gate_output``.
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
from construct.search.models import SearchResult
from construct.storage.workspace import WorkspaceLoader

IngestAction = Literal["skip", "ref_only", "ref_and_card"]


# ── Structured LLM output / finding contract ──


class ScoredFinding(BaseModel):
    """A governance-aware scoring proposal for one search result.

    Used both as the ``with_structured_output`` target (the LLM's raw proposal)
    and as the post-clamp finding returned by ``score_one``. The deterministic
    clamp may only ratchet ``ingest_action`` toward conservatism.
    """

    model_config = {"extra": "forbid"}

    url: str
    title: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_tier: int = Field(ge=1, le=5)
    ingest_action: IngestAction
    key_findings: list[str] = Field(default_factory=list, max_length=5)
    content_categories: list[str] = Field(default_factory=list)
    reasoning: str


# ── Gate I/O models (defined here to avoid circular import with catalog.py) ──


class GateMetadata(BaseModel):
    """Metadata about the gate invocation (L3 tier for research.score)."""

    model_config = {"extra": "forbid"}
    gate_id: str
    tier: str = "L3"
    review_required: bool = True
    review_status: str = "pending"
    provider: str = ""
    model: str = ""


class ResearchScoreInput(BaseModel):
    """Input for the research.score gate.

    ``workspace_path`` is required (D-12) so taxonomy/governance can be loaded
    read-only. ``results`` is the flattened ``SearchResult`` payload (D-10);
    the batches→flat flattening helper lands in Plan 04.
    """

    model_config = {"extra": "forbid"}
    workspace_path: str
    results: list[SearchResult] = Field(default_factory=list)
    provider_override: str | None = None


class ResearchScoreGateOutput(BaseModel):
    """Canonical research.score result: findings + gate metadata + retrieval."""

    model_config = {"extra": "forbid"}
    findings: list[ScoredFinding] = Field(default_factory=list)
    gate: GateMetadata = Field(default_factory=lambda: GateMetadata(gate_id="research.score"))
    retrieval: dict = Field(default_factory=dict)


# ── Governance thresholds (D-05/D-06) ──


@dataclass(frozen=True)
class GovernanceThresholds:
    """The governance bands the clamp enforces and the gate echoes (D-06)."""

    relevance_threshold: float
    card_creation_threshold: float
    max_papers_per_cycle: int


def load_governance_thresholds(workspace_path: str) -> GovernanceThresholds:
    """Read governance.yaml research thresholds (read-only, D-12)."""
    research = WorkspaceLoader(workspace_path).load_governance().research
    return GovernanceThresholds(
        relevance_threshold=research.relevance_threshold,
        card_creation_threshold=research.card_creation_threshold,
        max_papers_per_cycle=research.max_papers_per_cycle,
    )


def retrieval_echo(thresholds: GovernanceThresholds) -> dict:
    """Echo governance thresholds so success criterion 3 is provable offline (D-06)."""
    return {
        "relevance_threshold": thresholds.relevance_threshold,
        "card_creation_threshold": thresholds.card_creation_threshold,
        "max_papers_per_cycle": thresholds.max_papers_per_cycle,
    }


# ── Taxonomy soft-steering (D-11/D-12) ──


def load_taxonomy_categories(workspace_path: str) -> list[str]:
    """Load workspace taxonomy categories read-only for soft prompt steering (D-11).

    Combines domain ``content_categories`` from the registry with categories on
    existing cards. Read-only — the gate never writes to the workspace.
    """
    loader = WorkspaceLoader(workspace_path)

    categories: set[str] = set()
    try:
        registry = loader.load_domains_registry()
        for entry in registry.domains.values():
            categories.update(entry.content_categories)
    except Exception:
        pass

    # Taxonomy is "soft steering" (D-11): a card-store load failure should
    # degrade to no extra categories, not abort the whole gate run with an
    # exception that escapes the shim. Guard symmetrically with the registry
    # load above (WR-05).
    try:
        for card in loader.load_cards():
            for cat in card.get("content_categories", []) or []:
                categories.add(cat)
    except Exception:
        pass

    return sorted(categories)


# ── Ceiling-clamp (D-05) — deterministic, one-way ratchet toward conservatism ──


def clamp_action(
    llm_action: str,
    score: float,
    relevance: float,
    card_create: float,
) -> IngestAction:
    """Ceiling-clamp the LLM's ingest_action against governance bands (D-05).

    The LLM may only ever be *more* conservative than governance permits; the
    clamp never promotes a more permissive action.
    """
    if score < relevance:
        return "skip"
    if score < card_create:
        return "ref_only" if llm_action != "skip" else "skip"
    return llm_action  # ref_and_card permitted; LLM may still be more conservative


# ── Provider seam (consumed by the Plan 03 runner) ──


def build_scoring_llm(provider_cfg: ProviderConfig, gate_cfg: GateConfig) -> Any:
    """Construct the scoring chat model through the shared Plan 01 factory.

    Routed via ``factory.build_chat_model`` so the shared test monkeypatch on
    ``construct.llm.factory.build_chat_model`` covers this gate too.
    """
    return factory.build_chat_model(provider_cfg, temperature=gate_cfg.temperature)


# ── Prompt assembly ──


def _build_messages(
    result: SearchResult,
    *,
    thresholds: GovernanceThresholds,
    taxonomy_categories: list[str],
) -> list:
    """Assemble system+user messages: inject thresholds (D-06) + taxonomy (D-11).

    Untrusted snippet/url content is included only as data; the output is
    constrained to ``ScoredFinding`` and the deterministic clamp governs the
    final action, so a malicious snippet cannot escalate ingest_action (T-09-02).
    """
    taxonomy_block = (
        ", ".join(taxonomy_categories) if taxonomy_categories else "(none on record)"
    )
    system = SystemMessage(
        content=(
            "You are a research source-scoring assistant. Score ONE search result "
            "into a structured finding with relevance_score (0-1), source_tier (1-5, "
            "your own judgement of source quality from the URL + content), an "
            "ingest_action (skip | ref_only | ref_and_card), up to 5 key_findings "
            "(only for non-skip results), content_categories, and reasoning.\n\n"
            "Governance thresholds (advisory — the system enforces them deterministically):\n"
            f"- relevance_threshold: {thresholds.relevance_threshold} "
            "(below this → skip)\n"
            f"- card_creation_threshold: {thresholds.card_creation_threshold} "
            "(below this → at most ref_only)\n"
            f"- max_papers_per_cycle: {thresholds.max_papers_per_cycle}\n\n"
            "Workspace taxonomy categories — PREFER these when they fit, but you may "
            "propose new kebab-case categories when nothing fits:\n"
            f"{taxonomy_block}\n"
        )
    )
    user = HumanMessage(
        content=(
            f"Title: {result.title}\n"
            f"URL: {result.url}\n"
            f"Provider source_tier: {result.source_tier}\n"
            f"Provider score: {result.score}\n"
            f"Snippet:\n{result.snippet}\n"
        )
    )
    return [system, user]


# ── Single-result scoring (D-05 clamp + D-14 key_findings) ──


def score_one(
    result: SearchResult,
    *,
    llm: Any,
    thresholds: GovernanceThresholds,
    taxonomy_categories: list[str],
) -> ScoredFinding:
    """Score one search result into a governance-clamped ``ScoredFinding``.

    The LLM proposes the raw finding (relevance, tier, action, key_findings);
    Python then ceiling-clamps the action (D-05). When the final action is
    ``skip``, key_findings are cleared and the clamp rationale is appended to
    reasoning (D-14 / Pitfall 5).

    ``llm`` is supplied already-built so the call is offline-testable; the
    Plan 03 runner constructs it via :func:`build_scoring_llm`.
    """
    structured_llm = llm.with_structured_output(ScoredFinding, method="json_schema")
    messages = _build_messages(
        result, thresholds=thresholds, taxonomy_categories=taxonomy_categories
    )
    raw: ScoredFinding = structured_llm.invoke(messages)

    final_action = clamp_action(
        raw.ingest_action,
        raw.relevance_score,
        thresholds.relevance_threshold,
        thresholds.card_creation_threshold,
    )

    key_findings = raw.key_findings
    reasoning = raw.reasoning
    if final_action == "skip":
        key_findings = []
        if raw.ingest_action != "skip":
            reasoning = (
                f"{reasoning} [clamped to skip: relevance_score "
                f"{raw.relevance_score} < relevance_threshold "
                f"{thresholds.relevance_threshold}]"
            )

    return raw.model_copy(
        update={
            "ingest_action": final_action,
            "key_findings": key_findings,
            "reasoning": reasoning,
        }
    )


# ── Output assembly (echoes thresholds — D-06) ──


def build_gate_output(
    findings: list[ScoredFinding],
    *,
    gate_id: str,
    provider: str,
    model: str,
    thresholds: GovernanceThresholds,
    extra_retrieval: dict | None = None,
) -> ResearchScoreGateOutput:
    """Assemble the gate output with the governance thresholds echoed (D-06)."""
    retrieval = retrieval_echo(thresholds)
    if extra_retrieval:
        retrieval.update(extra_retrieval)
    return ResearchScoreGateOutput(
        findings=findings,
        gate=GateMetadata(gate_id=gate_id, provider=provider, model=model),
        retrieval=retrieval,
    )


# ── Error sanitization + outage discrimination (D-08/D-09, T-09-03) ──


class ResearchScoreOutageError(Exception):
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
    return f"{name}: scoring failed"


def _skip_finding_for_failure(result: SearchResult, safe_cause: str) -> ScoredFinding:
    """Build a skip finding when per-item scoring fails after retry (D-08)."""
    return ScoredFinding(
        url=result.url,
        title=result.title,
        relevance_score=0.0,
        source_tier=result.source_tier,
        ingest_action="skip",
        key_findings=[],
        content_categories=[],
        reasoning=f"scoring_failed: {safe_cause}",
    )


def _score_one_with_retry(
    result: SearchResult,
    *,
    llm: Any,
    thresholds: GovernanceThresholds,
    taxonomy_categories: list[str],
) -> tuple[ScoredFinding, int, BaseException | None]:
    """Score one result with a single retry; return (finding, retried_count, error)."""
    retried = 0
    last_exc: BaseException | None = None
    for attempt in range(2):
        try:
            finding = score_one(
                result,
                llm=llm,
                thresholds=thresholds,
                taxonomy_categories=taxonomy_categories,
            )
            return finding, retried, None
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                retried = 1
    assert last_exc is not None
    return (
        _skip_finding_for_failure(result, _safe_scoring_cause(last_exc)),
        retried,
        last_exc,
    )


@dataclass
class ScoreAllCounters:
    """Batch scoring counters echoed in retrieval (D-06 + D-08)."""

    results_total: int = 0
    scored_ok: int = 0
    retried: int = 0
    errors: int = 0
    degraded: bool = False


@dataclass
class ScoreAllResult:
    """Result of bounded fan-out scoring over a result list."""

    findings: list[ScoredFinding] = field(default_factory=list)
    counters: ScoreAllCounters = field(default_factory=ScoreAllCounters)
    total_outage: bool = False
    outage_message: str | None = None


def score_all(
    results: list[SearchResult],
    *,
    llm: Any,
    thresholds: GovernanceThresholds,
    taxonomy_categories: list[str],
    cap: int,
) -> ScoreAllResult:
    """Score a batch with bounded concurrency, per-item retry, and outage detection."""
    if not results:
        return ScoreAllResult(
            findings=[],
            counters=ScoreAllCounters(results_total=0),
        )

    ordered: list[ScoredFinding | None] = [None] * len(results)
    retried_total = 0
    errors = 0
    scored_ok = 0
    provider_failures = 0

    def _worker(index: int, result: SearchResult) -> tuple[int, ScoredFinding, int, BaseException | None]:
        finding, item_retried, exc = _score_one_with_retry(
            result,
            llm=llm,
            thresholds=thresholds,
            taxonomy_categories=taxonomy_categories,
        )
        return index, finding, item_retried, exc

    workers = max(1, min(cap, len(results)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_worker, idx, result)
            for idx, result in enumerate(results)
        ]
        for future in as_completed(futures):
            index, finding, item_retried, exc = future.result()
            ordered[index] = finding
            retried_total += item_retried
            if exc is not None:
                errors += 1
                if _is_provider_outage_cause(exc):
                    provider_failures += 1
            else:
                scored_ok += 1

    if scored_ok == 0 and provider_failures == len(results):
        return ScoreAllResult(
            findings=[],
            counters=ScoreAllCounters(
                results_total=len(results),
                scored_ok=0,
                retried=retried_total,
                errors=errors,
                degraded=True,
            ),
            total_outage=True,
            outage_message=(
                "All scoring requests failed due to provider authentication "
                "or configuration error"
            ),
        )

    findings = [f for f in ordered if f is not None]
    return ScoreAllResult(
        findings=findings,
        counters=ScoreAllCounters(
            results_total=len(results),
            scored_ok=scored_ok,
            retried=retried_total,
            errors=errors,
            degraded=errors > 0,
        ),
    )


def run_gate(
    gate_id: str,
    input_data: ResearchScoreInput,
    *,
    config_path: Any = None,
) -> ResearchScoreGateOutput:
    """Run the research.score gate: resolve config, fan out, assemble output."""
    config = load_llm_config(config_path)
    gate_cfg = config.gates.get(gate_id, config.gates.get("research.score"))
    if gate_cfg is None:
        raise RuntimeError(f"GATE_PROVIDER_ERROR: unknown gate '{gate_id}'")

    provider_key = input_data.provider_override or gate_cfg.provider
    provider_cfg = config.providers.get(provider_key, config.providers["anthropic"])

    thresholds = load_governance_thresholds(input_data.workspace_path)
    taxonomy_categories = load_taxonomy_categories(input_data.workspace_path)
    llm = build_scoring_llm(provider_cfg, gate_cfg)

    batch = score_all(
        input_data.results,
        llm=llm,
        thresholds=thresholds,
        taxonomy_categories=taxonomy_categories,
        cap=gate_cfg.concurrency_cap,
    )

    if batch.total_outage:
        raise ResearchScoreOutageError(
            batch.outage_message
            or "Provider outage during research.score batch"
        )

    extra_retrieval = {
        "results_total": batch.counters.results_total,
        "scored_ok": batch.counters.scored_ok,
        "retried": batch.counters.retried,
        "errors": batch.counters.errors,
        "degraded": batch.counters.degraded,
    }

    return build_gate_output(
        batch.findings,
        gate_id=gate_id,
        provider=provider_key,
        model=provider_cfg.model,
        thresholds=thresholds,
        extra_retrieval=extra_retrieval,
    )
