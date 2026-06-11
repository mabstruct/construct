"""Multi-level bridge detection pipeline: L1 structural, L2 category overlap, L3 semantic (LLM)."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from construct.services.knowledge import OperationError, OperationResult
from construct.storage.workspace import WorkspaceLoadError, WorkspaceLoader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# L1+L2 threshold — only candidates above this combined score proceed to L3
# Prevents O(N²) LLM calls per AI-SPEC §4b Pitfall 5
L3_THRESHOLD = 0.3

# Scoring weights per spec-v02-cross-domain-data.md §7
L1_WEIGHT = 0.30
L2_WEIGHT = 0.20
L3_WEIGHT = 0.50

# Max L3 candidates per run (cost guard)
MAX_L3_CANDIDATES = 50


# ---------------------------------------------------------------------------
# L3 structured output schema
# ---------------------------------------------------------------------------


class BridgeAssessmentOutput(BaseModel):
    """Structured output for L3 bridge assessment via LLM."""

    verdict: str = Field(description="Assessment: 'strong', 'possible', or 'reject'")
    reasoning: str = Field(description="One-sentence reasoning for the assessment")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def bridge_detect(workspace_path: str) -> OperationResult:
    """Run L1->L2->L3 bridge detection pipeline.

    Args:
        workspace_path: Path to CONSTRUCT workspace directory.

    Returns:
        OperationResult with data containing bridges, candidates, and scoring metadata.
    """
    try:
        root = Path(workspace_path)
        loader = WorkspaceLoader(root)

        # L1: Structural edges from connections.json
        l1_results = _l1_structural(loader)

        # L2: Category overlap across domains
        l2_results = _l2_category_overlap(loader)

        # Merge L1 + L2 into candidate list
        candidates = _merge_candidates(l1_results, l2_results, loader)

        # L3: Semantic assessment (only for candidates above threshold)
        l3_results = _l3_semantic(loader, candidates) if candidates else {}

        # Compute scores per spec
        bridges = _compute_all_scores(candidates, l3_results)

        # Persist to log/bridge-candidates.json and views/build/data/bridges.json
        _persist_candidates(root, bridges)

        total_confirmed = bridges["summary"]["totals"]["confirmed"]
        total_strong = bridges["summary"]["totals"]["strong_candidates"]

        return OperationResult(
            success=True,
            message=f"Bridge detection complete: {total_confirmed} confirmed, "
                    f"{total_strong} strong candidates",
            data=bridges,
        )
    except (WorkspaceLoadError, OSError) as exc:
        return OperationResult(
            success=False,
            message=str(exc),
            errors=[OperationError(reason=str(exc))],
        )


# ---------------------------------------------------------------------------
# L1: Structural bridge detection
# ---------------------------------------------------------------------------


def _l1_structural(loader: WorkspaceLoader) -> dict[str, Any]:
    """Detect cross-domain structural edges from connections.json.

    Loads connections and groups them by card-pair key. Returns only
    connections where the 'from' and 'to' cards belong to different domains.

    Returns:
        dict keyed by "{from_id}--{to_id}" with connection metadata.
    """
    # Pre-load all cards for domain lookups
    all_cards = loader.load_cards()
    card_domains: dict[str, set[str]] = {}
    for card in all_cards:
        card_id: str = card.get("id", "")
        domains: list[str] = card.get("domains", [])
        card_domains[card_id] = set(domains)

    connections = loader.load_connections()
    results: dict[str, Any] = {}

    for conn in connections.connections:
        from_id = conn.from_
        to_id = conn.to

        # Get domains for each endpoint
        from_domains = card_domains.get(from_id, set())
        to_domains = card_domains.get(to_id, set())

        # Cross-domain check: at least one domain differs
        if from_domains and to_domains and from_domains != to_domains:
            key = f"{from_id}--{to_id}"
            results[key] = {
                "from_id": from_id,
                "to_id": to_id,
                "from_domain": next(iter(from_domains)) if from_domains else "",
                "to_domain": next(iter(to_domains)) if to_domains else "",
                "connection_type": conn.type.value,
                "notes": conn.note or "",
            }

    return results


# ---------------------------------------------------------------------------
# L2: Category overlap detection
# ---------------------------------------------------------------------------


def _l2_category_overlap(loader: WorkspaceLoader) -> dict[str, Any]:
    """Detect shared content_categories across domain pairs.

    Groups cards by domain, then for each cross-domain pair computes
    the intersection of content_categories. Returns entries only for
    pairs that share at least one category.

    Returns:
        dict keyed by "{domain_a}--{domain_b}" with shared categories list.
    """
    all_cards = loader.load_cards()

    # Group cards by domain: domain -> list of cards
    domain_cards: dict[str, list[dict]] = {}
    for card in all_cards:
        card_domains: list[str] = card.get("domains", [])
        for domain in card_domains:
            if domain not in domain_cards:
                domain_cards[domain] = []
            domain_cards[domain].append(card)

    # Collect categories per domain
    domain_categories: dict[str, set[str]] = {}
    for domain, cards in domain_cards.items():
        cats: set[str] = set()
        for card in cards:
            for cat in card.get("content_categories", []):
                cats.add(cat)
        domain_categories[domain] = cats

    # Compute cross-domain overlaps
    results: dict[str, Any] = {}
    domain_list = sorted(domain_categories.keys())

    for i, domain_a in enumerate(domain_list):
        for domain_b in domain_list[i + 1 :]:
            shared = domain_categories[domain_a] & domain_categories[domain_b]
            if shared:
                key = f"{domain_a}--{domain_b}"
                results[key] = {
                    "domain_a": domain_a,
                    "domain_b": domain_b,
                    "shared_categories": sorted(shared),
                }

    return results


# ---------------------------------------------------------------------------
# Candidate merging
# ---------------------------------------------------------------------------


def _merge_candidates(
    l1_results: dict[str, Any],
    l2_results: dict[str, Any],
    loader: WorkspaceLoader,
) -> list[dict[str, Any]]:
    """Merge L1 and L2 results into a unified candidate list.

    L1 structural edges generate candidates directly. L2 category overlaps
    generate candidates by pairing all cards from matching domains.
    Each candidate gets a pre_score combining L1 and L2 signals.

    Returns:
        List of candidate dicts with from/to card info, signals, and pre_score.
    """
    all_cards = loader.load_cards()
    card_map: dict[str, dict] = {c.get("id", ""): c for c in all_cards}

    # Candidates from L1 structural edges
    candidates: list[dict[str, Any]] = []
    seen_pairs: set[str] = set()

    for key, l1_entry in l1_results.items():
        from_id = l1_entry["from_id"]
        to_id = l1_entry["to_id"]
        from_card = card_map.get(from_id, {})
        to_card = card_map.get(to_id, {})

        candidates.append({
            "pair_id": key,
            "from_card_id": from_id,
            "to_card_id": to_id,
            "from_domain": l1_entry["from_domain"],
            "to_domain": l1_entry["to_domain"],
            "from_title": from_card.get("title", ""),
            "to_title": to_card.get("title", ""),
            "l1_structural": True,
            "l2_shared_categories": [],
            "pre_score": L1_WEIGHT * 1.0 + L2_WEIGHT * 0.0,
        })
        seen_pairs.add(key)

    # Candidates from L2 category overlaps — pair all cards from matching domains
    for key, l2_entry in l2_results.items():
        domain_a = l2_entry["domain_a"]
        domain_b = l2_entry["domain_b"]
        shared_cats = l2_entry["shared_categories"]

        cards_a = [c for c in all_cards if domain_a in c.get("domains", [])]
        cards_b = [c for c in all_cards if domain_b in c.get("domains", [])]

        l2_score_val = min(1.0, len(shared_cats) / 3.0)

        for card_a in cards_a:
            for card_b in cards_b:
                pair_id_ab = f"{card_a['id']}--{card_b['id']}"
                pair_id_ba = f"{card_b['id']}--{card_a['id']}"

                if pair_id_ab in seen_pairs or pair_id_ba in seen_pairs:
                    continue

                pre = L1_WEIGHT * 0.0 + L2_WEIGHT * l2_score_val

                candidates.append({
                    "pair_id": pair_id_ab,
                    "from_card_id": card_a["id"],
                    "to_card_id": card_b["id"],
                    "from_domain": domain_a,
                    "to_domain": domain_b,
                    "from_title": card_a.get("title", ""),
                    "to_title": card_b.get("title", ""),
                    "l1_structural": False,
                    "l2_shared_categories": shared_cats,
                    "pre_score": round(pre, 2),
                })
                seen_pairs.add(pair_id_ab)

    return candidates


# ---------------------------------------------------------------------------
# L3: Semantic assessment (LLM)
# ---------------------------------------------------------------------------


def _l3_semantic(
    loader: WorkspaceLoader,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run bounded LLM assessment for promising candidates.

    Only candidates with pre_score >= L3_THRESHOLD proceed to the LLM.
    If ANTHROPIC_API_KEY is not set, L3 is skipped gracefully.
    Cost guard: max MAX_L3_CANDIDATES LLM calls per run.

    Args:
        loader: WorkspaceLoader for reading card content.
        candidates: List of merged candidates with pre_scores.

    Returns:
        dict keyed by pair_id with L3 verdict and reasoning, or empty dict if skipped.
    """
    # Filter to candidates above threshold
    qualifying = [c for c in candidates if c.get("pre_score", 0) >= L3_THRESHOLD]

    if not qualifying:
        logger.info("L3: No candidates above threshold %.1f", L3_THRESHOLD)
        return {}

    # Check API key availability
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("L3 skipped: ANTHROPIC_API_KEY not set")
        return {}

    # Cost guard
    if len(qualifying) > MAX_L3_CANDIDATES:
        logger.warning(
            "L3 skipped: %d candidates exceed max %d",
            len(qualifying),
            MAX_L3_CANDIDATES,
        )
        return {}

    # Pre-load all card bodies for excerpt extraction
    all_cards = loader.load_cards()
    card_map: dict[str, dict] = {c.get("id", ""): c for c in all_cards}

    # Build LLM
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError:
        logger.warning("L3 skipped: langchain_anthropic not installed")
        return {}

    llm = ChatAnthropic(
        model="claude-sonnet-haiku-4-20250514",
        temperature=0.0,
    )
    structured_llm = llm.with_structured_output(BridgeAssessmentOutput, method="json_schema")

    results: dict[str, Any] = {}

    for candidate in qualifying:
        pair_id = candidate["pair_id"]
        from_id = candidate["from_card_id"]
        to_id = candidate["to_card_id"]

        from_card = card_map.get(from_id, {})
        to_card = card_map.get(to_id, {})

        # Get up to 300 chars from each card's body
        from_excerpt = (from_card.get("body", "") or "")[:300]
        to_excerpt = (to_card.get("body", "") or "")[:300]

        system_msg = SystemMessage(
            content=(
                "You are a cross-domain bridge analyst. Assess whether two knowledge "
                "cards represent a genuine structural parallel across domains.\n\n"
                "Examples:\n"
                "- 'quantum decoherence' and 'consciousness/collapse' -> strong "
                "(shared observer-dependent structure)\n"
                "- 'neural correlates' and 'dark matter distribution' -> reject "
                "(different domains, no common mechanism)\n\n"
                "Respond with one of:\n"
                "- 'strong' — genuine structural parallel\n"
                "- 'possible' — interesting but uncertain\n"
                "- 'reject' — no meaningful connection"
            )
        )
        user_msg = HumanMessage(
            content=(
                f"Card 1: {from_card.get('title', 'Untitled')}\n"
                f"Domain: {candidate['from_domain']}\n"
                f"Excerpt: {from_excerpt}\n\n"
                f"Card 2: {to_card.get('title', 'Untitled')}\n"
                f"Domain: {candidate['to_domain']}\n"
                f"Excerpt: {to_excerpt}"
            )
        )

        try:
            result: BridgeAssessmentOutput = structured_llm.invoke([system_msg, user_msg])
            results[pair_id] = {
                "verdict": result.verdict,
                "reasoning": result.reasoning,
            }
        except Exception as exc:
            logger.warning("L3 assessment failed for %s: %s", pair_id, exc)
            results[pair_id] = {
                "verdict": "reject",
                "reasoning": f"LLM error: {exc}",
            }

    return results


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _compute_bridge_score(
    l1_structural: bool,
    l2_shared_categories: list[str],
    l3_candidate_strength: str | None,
) -> tuple[float, str]:
    """Compute final bridge score and band per spec-v02-cross-domain-data.md §7.

    Weights: L1=0.30, L2=0.20, L3=0.50

    Args:
        l1_structural: True if a direct cross-domain edge exists.
        l2_shared_categories: List of shared content categories.
        l3_candidate_strength: L3 verdict or None ('strong', 'possible', 'reject').

    Returns:
        Tuple of (score 0.0-1.0, band: 'strong'|'medium'|'weak').
    """
    l1_score = 1.0 if l1_structural else 0.0
    l2_score = min(1.0, len(l2_shared_categories) / 3.0) if l2_shared_categories else 0.0
    l3_map: dict[str, float] = {"strong": 1.0, "possible": 0.6}
    l3_score = l3_map.get(l3_candidate_strength, 0.0) if l3_candidate_strength else 0.0

    score = round((L1_WEIGHT * l1_score) + (L2_WEIGHT * l2_score) + (L3_WEIGHT * l3_score), 2)

    if l1_structural:
        band = "strong"
    elif score >= 0.70:
        band = "strong"
    elif score >= 0.45:
        band = "medium"
    else:
        band = "weak"

    return score, band


def _compute_all_scores(
    candidates: list[dict[str, Any]],
    l3_results: dict[str, Any],
) -> dict[str, Any]:
    """Compute final scores for all candidates and build output structure.

    Args:
        candidates: Merged candidate list with L1/L2 signals.
        l3_results: L3 assessment results keyed by pair_id.

    Returns:
        dict matching spec-v02-cross-domain-data.md §5 bridges.json contract.
    """
    bridge_entries: list[dict[str, Any]] = []

    for candidate in candidates:
        pair_id = candidate["pair_id"]
        l3_entry = l3_results.get(pair_id, {})
        l3_verdict = l3_entry.get("verdict") if l3_entry else None

        score, band = _compute_bridge_score(
            l1_structural=candidate["l1_structural"],
            l2_shared_categories=candidate["l2_shared_categories"],
            l3_candidate_strength=l3_verdict,
        )

        bridge_entry = {
            "from": {
                "card_id": candidate["from_card_id"],
                "domain": candidate["from_domain"],
                "title": candidate["from_title"],
            },
            "to": {
                "card_id": candidate["to_card_id"],
                "domain": candidate["to_domain"],
                "title": candidate["to_title"],
            },
            "score": score,
            "band": band,
            "l1_structural": candidate["l1_structural"],
            "l2_shared_categories": candidate["l2_shared_categories"],
            "l3_verdict": l3_verdict,
            "l3_reasoning": l3_entry.get("reasoning") if l3_entry else None,
        }
        bridge_entries.append(bridge_entry)

    # Compute summary totals
    confirmed = sum(1 for b in bridge_entries if b["l1_structural"])
    strong = sum(1 for b in bridge_entries if b["band"] == "strong")
    medium = sum(1 for b in bridge_entries if b["band"] == "medium")
    weak = sum(1 for b in bridge_entries if b["band"] == "weak")

    l3_skipped = not bool(l3_results) and bool(candidates)
    eligible_count = sum(
        1 for c in candidates if c.get("pre_score", 0) >= L3_THRESHOLD
    )

    result = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "workspace": "",
        "bridges": bridge_entries,
        "summary": {
            "totals": {
                "confirmed": confirmed,
                "strong_candidates": strong,
                "medium_candidates": medium,
                "weak_candidates": weak,
            },
            "l1_l2_only": l3_skipped,
            "l3_calls": len(l3_results),
            "l3_candidates_eligible": eligible_count,
            "l3_candidates_total": len(candidates),
        },
    }

    return result


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _persist_candidates(root: Path, bridges: dict) -> None:
    """Write bridge candidates to workspace log and views build directory.

    Writes to:
        - log/bridge-candidates.json (pipeline log)
        - views/build/data/bridges.json (derived data contract per D-06 #4)
    """
    # Set workspace path in the output
    bridges["workspace"] = str(root.resolve())

    serialized = json.dumps(bridges, indent=2, default=str) + "\n"

    # Write to pipeline log
    log_dir = root / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "bridge-candidates.json").write_text(serialized, encoding="utf-8")

    # Write to views build data (D-06 #4 — derived data contract)
    views_dir = root / "views" / "build" / "data"
    views_dir.mkdir(parents=True, exist_ok=True)
    (views_dir / "bridges.json").write_text(serialized, encoding="utf-8")
