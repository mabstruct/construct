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

from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from construct.llm import factory
from construct.llm.config import GateConfig, ProviderConfig
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

    for card in loader.load_cards():
        for cat in card.get("content_categories", []) or []:
            categories.add(cat)

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
