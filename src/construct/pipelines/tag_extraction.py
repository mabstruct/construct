"""Tag/keyword extraction pipeline — extract candidates from refs, write reviewable results.

Per D-07:
  1. Extracts candidate tags/keywords from refs/*.json source material
  2. Writes candidates to log/tag-candidates.json
  3. On user approval via curation cycle → updates search-seeds.json

Per D-08: Tags are NEVER auto-accepted. All candidates start as "pending"
and require explicit approval through the curation review cycle.
"""
from __future__ import annotations

import json
import re
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TagCandidate:
    """A single candidate tag extracted from source material.

    All candidates start with status="pending" per D-08 — never auto-accepted.
    """

    id: str
    tag: str
    domain_id: str | None = None
    source_ref: str | None = None
    confidence: float = 0.0
    frequency: int = 1
    status: str = "pending"
    created_at: str = ""
    notes: str = ""


@dataclass
class TagExtractionResult:
    """Result of a single extract_candidates() run."""

    success: bool
    candidates: list[TagCandidate]
    total_candidates: int
    new_candidates: int
    existing_seeds_skipped: int
    error: str | None = None


# ---------------------------------------------------------------------------
# Stop words — common English words unlikely to be useful tags
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "we", "us", "our", "you", "your", "he", "she", "him", "her", "his",
    "not", "no", "nor", "so", "if", "then", "than", "just", "about",
    "above", "after", "again", "all", "also", "any", "because", "before",
    "between", "both", "each", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "too", "very", "into", "over", "under",
    "up", "out", "off", "down", "here", "there", "when", "where", "why",
    "how", "what", "which", "who", "whom", "while", "during", "through",
    "using", "based", "related", "regarding", "including", "within",
    "without", "across", "among", "along", "around", "toward", "via",
    "although", "however", "therefore", "thus", "hence", "further",
    "furthermore", "nevertheless", "nonetheless", "meanwhile", "moreover",
})

_MIN_CONFIDENCE_THRESHOLD = 0.15


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_candidates(workspace: Path) -> TagExtractionResult:
    """Run the full tag extraction pipeline on a workspace.

    Steps:
      1. Read refs/*.json files
      2. Extract candidate phrases from each ref
      3. Normalize and score candidates by frequency
      4. Filter against existing search-seeds.json
      5. Diff against existing tag-candidates.json
      6. Write merged candidates to log/tag-candidates.json
      7. Return stats

    Args:
        workspace: Path to the CONSTRUCT workspace root.

    Returns:
        TagExtractionResult with candidate list and summary stats.
    """
    refs_dir = workspace / "refs"

    # Step 1: Validate refs directory exists
    if not refs_dir.is_dir():
        return TagExtractionResult(
            success=False,
            candidates=[],
            total_candidates=0,
            new_candidates=0,
            existing_seeds_skipped=0,
            error=f"No refs directory found at {refs_dir}",
        )

    # Step 2: Load existing seeds for dedup
    existing_seed_terms = load_search_seeds(workspace)

    # Step 3: Load existing tag candidates (for dedup)
    existing_candidates = load_existing_candidates(workspace)
    existing_tag_set: set[str] = {
        normalize_tag(c.get("tag", ""))
        for c in existing_candidates
        if c.get("status") in ("pending", "approved")
    }

    # Step 4: Read all ref files and extract phrases
    ref_files = sorted(refs_dir.glob("*.json"))
    all_phrases: list[tuple[str, str, str | None]] = []  # (normalized, original, domain_id)

    for ref_path in ref_files:
        phrases = _extract_phrases_from_ref(ref_path)
        if phrases is not None:
            all_phrases.extend(phrases)

    if not all_phrases:
        return TagExtractionResult(
            success=True,
            candidates=[],
            total_candidates=0,
            new_candidates=0,
            existing_seeds_skipped=0,
        )

    # Step 5: Aggregate by normalized tag
    tag_counter: Counter = Counter()
    tag_sources: dict[str, list[str]] = {}
    tag_domains: dict[str, set[str | None]] = {}

    for normalized, original, domain_id in all_phrases:
        tag_counter[normalized] += 1
        if normalized not in tag_sources:
            tag_sources[normalized] = []
        tag_sources[normalized].append(original)
        if normalized not in tag_domains:
            tag_domains[normalized] = set()
        tag_domains[normalized].add(domain_id)

    # Step 6: Build candidate list with scoring and filtering
    now_iso = datetime.now(timezone.utc).isoformat()
    candidates_by_tag: dict[str, TagCandidate] = {}
    existing_seeds_skipped = 0
    existing_candidates_skipped = 0

    for normalized_tag in sorted(tag_counter, key=tag_counter.get, reverse=True):
        freq = tag_counter[normalized_tag]
        sources = tag_sources.get(normalized_tag, [])
        domains = tag_domains.get(normalized_tag, set())

        # Confidence: simple heuristic based on frequency and phrase length
        confidence = _compute_confidence(normalized_tag, freq, len(ref_files))

        # Skip low-confidence tags
        if confidence < _MIN_CONFIDENCE_THRESHOLD:
            continue

        # Skip if it matches an existing seed
        if _matches_existing_seed(normalized_tag, existing_seed_terms):
            existing_seeds_skipped += 1
            continue

        # Skip if already in existing candidates
        if normalized_tag in existing_tag_set:
            existing_candidates_skipped += 1
            continue

        # Generate a stable ID from the tag + first domain
        domain_str = next(iter(domains)) if domains else None
        raw_domain = domain_str or "general"
        candidate_id = _generate_candidate_id(normalized_tag, raw_domain)

        # Best original form (use the most common original phrase)
        original_counter = Counter(sources)
        best_tag = original_counter.most_common(1)[0][0]

        candidate = TagCandidate(
            id=candidate_id,
            tag=best_tag,
            domain_id=domain_str,
            source_ref=",".join(
                sorted({s.rsplit("/", 1)[-1].replace(".json", "") for s in sources})
            ) if sources else None,
            confidence=round(confidence, 3),
            frequency=freq,
            status="pending",
            created_at=now_iso,
            notes=f"Extracted from {freq} ref(s)" if freq > 1 else "",
        )
        candidates_by_tag[normalized_tag] = candidate

    candidates = list(candidates_by_tag.values())
    total_candidates = len(candidates)

    # Step 7: Merge with existing candidates and write
    merged_candidates = list(existing_candidates)
    existing_ids = {c.get("id") for c in merged_candidates}
    for c in candidates:
        if c.id not in existing_ids:
            merged_candidates.append({
                "id": c.id,
                "tag": c.tag,
                "domain_id": c.domain_id,
                "source_ref": c.source_ref,
                "confidence": c.confidence,
                "frequency": c.frequency,
                "status": c.status,
                "created_at": c.created_at,
                "notes": c.notes,
            })
            existing_ids.add(c.id)

    new_count = len(candidates)
    merged_count = len(merged_candidates)

    # Step 8: Write merged file
    _write_candidates_file(workspace, merged_candidates, now_iso)

    return TagExtractionResult(
        success=True,
        candidates=candidates,
        total_candidates=new_count,
        new_candidates=new_count,
        existing_seeds_skipped=existing_seeds_skipped,
    )


# ---------------------------------------------------------------------------
# Phrase extraction helpers
# ---------------------------------------------------------------------------


def _extract_phrases_from_ref(
    ref_path: Path,
) -> list[tuple[str, str, str | None]] | None:
    """Extract candidate phrases from a single ref JSON file.

    Returns a list of (normalized_tag, original_tag, domain_id) tuples,
    or ``None`` if the file cannot be parsed.
    """
    try:
        data = json.loads(ref_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Skipping unparseable ref %s: %s", ref_path.name, exc)
        return None

    if not isinstance(data, dict):
        logger.warning("Skipping ref %s: not a JSON object", ref_path.name)
        return None

    domain_id: str | None = data.get("domain")

    # Collect text content from the ref
    texts: list[str] = []

    title = data.get("title", "")
    if title:
        texts.append(title)

    abstract = data.get("abstract", "")
    if abstract:
        texts.append(abstract)

    # Also check for notes/description fields
    notes = data.get("notes", "")
    if notes:
        texts.append(notes)

    key_findings = data.get("key_findings", [])
    if isinstance(key_findings, list):
        for finding in key_findings:
            if isinstance(finding, str):
                texts.append(finding)

    if not texts:
        return None

    combined = " ".join(texts)

    # Extract phrases using hybrid approach
    phrases = extract_phrases(combined)

    # Dedup phrases extracted from this ref
    seen: set[str] = set()
    result: list[tuple[str, str, str | None]] = []
    for phrase in phrases:
        normalized = normalize_tag(phrase)
        if normalized and normalized not in seen and len(normalized) >= 3:
            seen.add(normalized)
            result.append((normalized, phrase, domain_id))

    return result


def extract_phrases(text: str) -> list[str]:
    """Extract candidate noun phrases from text using regex heuristics.

    Per the agent's discretion (D-07 note): uses a hybrid regex-based
    approach — extracts capitalized multi-word phrases, adjective-noun
    patterns, and concept-level bigrams/trigrams. Designed to be
    upgradeable to LLM-assisted extraction when needed.

    Args:
        text: Source text to extract phrases from.

    Returns:
        List of candidate phrase strings (not normalized).
    """
    if not text or not text.strip():
        return []

    phrases: list[str] = []

    # Pattern 1: Multi-word capitalized phrases (proper nouns, named concepts)
    # e.g. "Large Scale Structure", "Dark Energy", "General Relativity"
    cap_phrases = re.findall(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
        text,
    )
    for phrase in cap_phrases:
        words = phrase.split()
        # Skip titles that look like start-of-sentence words (single caps)
        if len(words) >= 2:
            phrases.append(phrase)

    # Pattern 2: Adjective-noun pairs (e.g. "quantum gravity", "cosmic inflation")
    # Match sequences of: (adj|noun) + noun, 2-3 words
    adj_noun = re.findall(
        r"\b([a-z]+(?:\s+[a-z]+){1,2})\b",
        text.lower(),
    )
    for phrase in adj_noun:
        words = phrase.split()
        if len(words) >= 2:
            # Filter out phrases ending in common verbs or prepositions
            if words[-1] in _STOP_WORDS:
                continue
            # Filter out phrases where all words are stop words
            if all(w in _STOP_WORDS for w in words):
                continue
            # Only include if the phrase has substantive content words
            non_stop = [w for w in words if w not in _STOP_WORDS]
            if len(non_stop) >= 2 or (len(non_stop) == 1 and len(words) >= 2):
                phrases.append(phrase)

    # Pattern 3: "X of Y" constructions (e.g. "equation of state", "theory of mind")
    x_of_y = re.findall(
        r"\b([a-z]+(?:\s+of\s+[a-z]+)+)\b",
        text.lower(),
    )
    for phrase in x_of_y:
        words = phrase.split()
        non_stop = [w for w in words if w not in _STOP_WORDS and w != "of"]
        if len(non_stop) >= 2:
            phrases.append(phrase)

    # Pattern 4: Acronym expansions — e.g. "CMB (Cosmic Microwave Background)"
    acronym_expansions = re.findall(
        r"\(([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\)",
        text,
    )
    for phrase in acronym_expansions:
        words = phrase.split()
        if len(words) >= 2:
            phrases.append(phrase)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for phrase in phrases:
        key = phrase.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(phrase)

    return unique


def normalize_tag(text: str) -> str:
    """Normalize a tag for dedup: lowercase, strip, collapse whitespace.

    Args:
        text: Raw tag text to normalize.

    Returns:
        Normalized tag string.
    """
    normalized = text.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    return normalized.strip()


def _compute_confidence(tag: str, frequency: int, total_refs: int) -> float:
    """Compute a confidence score for a tag candidate.

    Factors:
      - Frequency relative to total refs (higher = more reliable)
      - Phrase length (longer phrases tend to be more specific)
      - Normalized tag substance (non-stop-word content)

    Returns a float 0.0–1.0.
    """
    # Frequency score: 0.0 to 0.5 based on how many refs mention this tag
    freq_ratio = frequency / max(total_refs, 1)
    freq_score = min(freq_ratio * 2, 0.5)

    # Length score: 0.0 to 0.3 based on phrase length
    word_count = len(tag.split())
    if word_count >= 5:
        length_score = 0.3
    elif word_count >= 3:
        length_score = 0.2
    elif word_count >= 2:
        length_score = 0.15
    else:
        length_score = 0.05

    # Substance score: 0.0 to 0.2 based on non-stop-word ratio
    words = tag.split()
    non_stop = sum(1 for w in words if w not in _STOP_WORDS)
    substance_ratio = non_stop / max(len(words), 1)
    substance_score = substance_ratio * 0.2

    return min(freq_score + length_score + substance_score, 1.0)


def _matches_existing_seed(tag: str, seed_terms: list[str]) -> bool:
    """Check if *tag* is already covered by an existing search seed.

    Performs case-insensitive substring matching: if the tag is a substring
    of any existing seed term (or vice versa), it's considered a match.

    Args:
        tag: Normalized tag to check.
        seed_terms: List of existing seed terms from search-seeds.json.

    Returns:
        True if the tag overlaps with an existing seed.
    """
    tag_lower = tag.lower()
    for term in seed_terms:
        term_lower = term.lower()
        if tag_lower == term_lower:
            return True
        # Tag is a substring of a longer seed term
        if len(tag_lower) >= 5 and tag_lower in term_lower:
            return True
        # Seed term is a substring of a longer tag
        if len(term_lower) >= 5 and term_lower in tag_lower:
            return True
    return False


def _generate_candidate_id(tag: str, domain: str) -> str:
    """Generate a stable tag candidate ID from tag and domain.

    Args:
        tag: Normalized tag text.
        domain: Domain ID string.

    Returns:
        A kebab-case ID like ``cosmology-dark-energy``.
    """
    slug = tag.lower().strip()
    slug = re.sub(r"[^a-z0-9\s]", " ", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = slug.strip("-")
    domain_slug = domain.lower().strip()
    domain_slug = re.sub(r"[^a-z0-9\s]", " ", domain_slug)
    domain_slug = re.sub(r"\s+", "-", domain_slug).strip("-")
    return f"{domain_slug}-{slug}" if domain_slug != "general" else slug


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------


def load_search_seeds(workspace: Path) -> list[str]:
    """Load existing search patterns from search-seeds.json.

    Args:
        workspace: Path to the workspace root.

    Returns:
        List of all search term strings from the clusters.
    """
    seeds_path = workspace / "search-seeds.json"
    if not seeds_path.is_file():
        return []

    try:
        data = json.loads(seeds_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not parse search-seeds.json — treating as empty")
        return []

    terms: list[str] = []
    for cluster in data.get("clusters", []):
        cluster_terms = cluster.get("terms", [])
        if isinstance(cluster_terms, list):
            terms.extend(cluster_terms)
        elif isinstance(cluster_terms, str):
            terms.append(cluster_terms)
    return terms


def load_existing_candidates(workspace: Path) -> list[dict]:
    """Load existing tag candidates from log/tag-candidates.json.

    Args:
        workspace: Path to the workspace root.

    Returns:
        List of existing candidate dicts (may be empty).
    """
    candidates_path = workspace / "log" / "tag-candidates.json"
    if not candidates_path.is_file():
        return []

    try:
        data = json.loads(candidates_path.read_text(encoding="utf-8"))
        return data.get("candidates", [])
    except (json.JSONDecodeError, OSError):
        logger.warning(
            "Corrupted tag-candidates.json — starting fresh. "
            "Previous candidates may be lost."
        )
        return []


def _write_candidates_file(
    workspace: Path,
    candidates: list[dict],
    generated_at: str,
) -> None:
    """Write tag candidates to log/tag-candidates.json using atomic write.

    Args:
        workspace: Path to the workspace root.
        candidates: List of candidate dicts to persist.
        generated_at: ISO timestamp for the file.
    """
    log_dir = workspace / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": generated_at,
        "total": len(candidates),
        "candidates": candidates,
    }

    target_path = workspace / "log" / "tag-candidates.json"
    tmp_path = target_path.with_suffix(".tmp")

    try:
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(target_path)
    except OSError as exc:
        logger.error("Failed to write tag-candidates.json: %s", exc)
        raise
