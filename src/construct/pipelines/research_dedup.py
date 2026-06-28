"""Deterministic, offline idempotency primitives for research.run (RSCH-05).

Pure-Python building blocks consumed by the ``deduplicate`` and ``ingest_batch``
workflow nodes: URL normalization, deterministic ref-ID derivation, title
fuzzy near-dup detection, and rejected-findings ledger I/O.

These are intentionally stdlib-only and free of LangGraph so they remain
deterministic and offline-testable. The legacy collision suffixer in
``ingestion.py`` (appends ``-2``/``-3`` on collision) is the D-07 anti-pattern
this module replaces — it MUST NOT be used here, because its suffixes duplicate
findings on every rerun. ID stability comes from hashing the normalized URL
instead.
"""

from __future__ import annotations

from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys
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


# --- rejected-findings ledger (D-06) ---------------------------------------
#
# Lives at ``<workspace>/.construct/research/rejected.json`` — a verified
# non-SOT path (schemas/workspace.py allows ``.construct/**``), so it never
# trips ``validate_workspace`` and a corrupt/forged ledger cannot masquerade as
# a real ref under refs/. Reads are missing-file safe so the dedup node never
# crashes on a fresh workspace (T-10-05).

_EMPTY_LEDGER = {"version": 1, "rejected": []}


def rejected_ledger_path(workspace: Path) -> Path:
    """Return the rejected-ledger path: ``<workspace>/.construct/research/rejected.json``."""
    return Path(workspace) / ".construct" / "research" / "rejected.json"


def load_rejected_ledger(workspace: Path) -> dict:
    """Load the rejected ledger, returning an empty ledger if absent or unreadable.

    Never raises: a missing or malformed file yields ``{"version": 1,
    "rejected": []}`` so the dedup node degrades gracefully (T-10-05).
    """
    path = rejected_ledger_path(workspace)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "rejected": []}
    if not isinstance(data, dict) or not isinstance(data.get("rejected"), list):
        return {"version": 1, "rejected": []}
    data.setdefault("version", 1)
    return data


def append_rejected(
    workspace: Path,
    *,
    normalized_url: str,
    gate_id: str,
    title: str,
) -> None:
    """Append a rejected finding to the ledger and persist it.

    Each entry records the normalized URL, the originating ``gate_id``, the
    title, and a UTC ISO timestamp. Parent directories are created as needed;
    the ledger is written under ``.construct/research/`` and never inside the
    SOT trees (refs/cards/digests/log).
    """
    ledger = load_rejected_ledger(workspace)
    ledger["rejected"].append(
        {
            "normalized_url": normalized_url,
            "gate_id": gate_id,
            "title": title,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    path = rejected_ledger_path(workspace)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"WARNING: could not write rejected ledger to {path}: {exc}", file=sys.stderr)


def rejected_normalized_urls(ledger: dict) -> set[str]:
    """Return the set of normalized URLs in *ledger* for dedup filtering (D-06)."""
    return {
        entry["normalized_url"]
        for entry in ledger.get("rejected", [])
        if "normalized_url" in entry
    }
