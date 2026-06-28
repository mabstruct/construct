"""Deterministic, offline idempotency primitives for research.run (RSCH-05).

Pure-Python building blocks consumed by the ``deduplicate`` and ``ingest_batch``
workflow nodes: URL normalization, deterministic ref-ID derivation, title
fuzzy near-dup detection, and rejected-findings ledger I/O.

These are intentionally stdlib-only and free of LangGraph so they remain
deterministic and offline-testable. The legacy ``_deduplicate_ref_id()``
suffixer in ``ingestion.py`` (appends ``-2``/``-3`` on collision) is the D-07
anti-pattern this module replaces — it MUST NOT be used here, because its
suffixes duplicate findings on every rerun.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from construct.schemas.config import KEBAB_CASE_PATTERN

# Tracking / analytics query parameters stripped during normalization (D-05).
_TRACKING = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "spm",
}


def normalize_url(url: str) -> str:
    """Collapse a URL to one canonical form for dedup keying (D-05).

    Lowercases the host, drops the fragment, strips tracking params, sorts the
    remaining query keys, removes a trailing slash, and normalizes the scheme
    to ``https`` so ``http``/``https`` variants collapse together. Deterministic.
    """
    parts = urlsplit(url.strip())
    scheme = "https"
    host = parts.hostname.lower() if parts.hostname else ""
    if parts.port and not (parts.port == 443 or parts.port == 80):
        host = f"{host}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parts.query) if k.lower() not in _TRACKING)
    )
    return urlunsplit((scheme, host, path, query, ""))


def ref_id_for(normalized_url: str, title: str) -> str:
    """Derive a deterministic, kebab-valid ref ID from a normalized URL + title.

    The ID is a human-readable slug of the title plus a stable 8-char SHA-1 of
    the normalized URL, so the same URL always yields the same ID and distinct
    URLs sharing a title never collide. Falls back to ``ref`` when the title has
    no slug-able characters. Output always satisfies ``KEBAB_CASE_PATTERN``.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-") or "ref"
    digest = hashlib.sha1(normalized_url.encode("utf-8")).hexdigest()[:8]
    ref_id = f"{slug}-{digest}"
    assert KEBAB_CASE_PATTERN.fullmatch(ref_id) is not None, ref_id
    return ref_id


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, and sort tokens for order-insensitive compare."""
    tokens = re.sub(r"[^a-z0-9]+", " ", title.lower()).split()
    return " ".join(sorted(tokens))


def title_is_near_dup(
    candidate_title: str,
    existing_titles: Iterable[str],
    *,
    threshold: float = 0.90,
) -> bool:
    """True if *candidate_title* fuzzily matches any existing title (D-05).

    Comparison is case-, punctuation-, and word-order-insensitive: titles are
    token-normalized then compared with ``difflib.SequenceMatcher``. Returns
    True when the ratio meets *threshold* against any existing title.
    """
    candidate = _normalize_title(candidate_title)
    for existing in existing_titles:
        ratio = difflib.SequenceMatcher(None, candidate, _normalize_title(existing)).ratio()
        if ratio >= threshold:
            return True
    return False
