"""Unit coverage for RSCH-05 idempotency primitives (research_dedup)."""

from __future__ import annotations

from pathlib import Path

from construct.schemas.config import KEBAB_CASE_PATTERN
from construct.pipelines.research_dedup import (
    append_rejected,
    load_rejected_ledger,
    normalize_url,
    ref_id_for,
    rejected_ledger_path,
    rejected_normalized_urls,
    title_is_near_dup,
)


# --- normalize_url ---------------------------------------------------------


def test_url_normalization_collapses_tracking_fragment_slash_scheme_case() -> None:
    a = normalize_url("http://Example.com/a/?utm_source=x&b=2#frag")
    b = normalize_url("https://example.com/a?b=2")
    assert a == b


def test_url_normalization_sorts_remaining_query_keys() -> None:
    assert normalize_url("https://example.com/p?b=2&a=1") == normalize_url(
        "https://example.com/p?a=1&b=2"
    )


def test_url_normalization_strips_all_known_tracking_params() -> None:
    noisy = (
        "https://example.com/p?utm_medium=m&gclid=g&fbclid=f&mc_cid=c"
        "&mc_eid=e&ref=r&ref_src=rs&spm=s&keep=1"
    )
    assert normalize_url(noisy) == "https://example.com/p?keep=1"


def test_url_normalization_root_path_preserved() -> None:
    assert normalize_url("http://Example.com/") == "https://example.com/"


# --- ref_id_for ------------------------------------------------------------


def test_ref_id_deterministic() -> None:
    u = normalize_url("https://example.com/deep-learning")
    t = "Deep Learning for X"
    assert ref_id_for(u, t) == ref_id_for(u, t)


def test_ref_id_is_kebab_valid() -> None:
    u = normalize_url("https://example.com/deep-learning")
    rid = ref_id_for(u, "Deep Learning for X!")
    assert KEBAB_CASE_PATTERN.fullmatch(rid) is not None


def test_ref_id_distinct_urls_same_title_do_not_collide() -> None:
    title = "Shared Title"
    a = ref_id_for(normalize_url("https://example.com/one"), title)
    b = ref_id_for(normalize_url("https://example.com/two"), title)
    assert a != b


def test_ref_id_empty_title_falls_back_to_ref_prefix() -> None:
    u = normalize_url("https://example.com/x")
    rid = ref_id_for(u, "  !!! ")
    assert rid.startswith("ref-")
    assert KEBAB_CASE_PATTERN.fullmatch(rid) is not None


# --- title_is_near_dup -----------------------------------------------------


def test_fuzzy_title_near_dup_true_above_threshold() -> None:
    assert title_is_near_dup(
        "Deep Learning for X", ["deep learning for x!"], threshold=0.9
    )


def test_fuzzy_title_word_order_and_punctuation_insensitive() -> None:
    assert title_is_near_dup("X for Deep Learning", ["Deep Learning for X"], threshold=0.9)


def test_fuzzy_title_below_threshold_is_false() -> None:
    assert not title_is_near_dup(
        "Quantum Gravity Review", ["Deep Learning for X"], threshold=0.9
    )


def test_fuzzy_title_empty_existing_is_false() -> None:
    assert not title_is_near_dup("anything", [], threshold=0.9)


# --- rejected ledger -------------------------------------------------------


def test_rejected_ledger_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_rejected_ledger(tmp_path) == {"version": 1, "rejected": []}


def test_rejected_append_and_reload_roundtrip(tmp_path: Path) -> None:
    url = normalize_url("https://example.com/rejected")
    append_rejected(tmp_path, normalized_url=url, gate_id="run-1", title="Some Title")
    urls = rejected_normalized_urls(load_rejected_ledger(tmp_path))
    assert url in urls


def test_rejected_entry_has_required_fields(tmp_path: Path) -> None:
    url = normalize_url("https://example.com/r")
    append_rejected(tmp_path, normalized_url=url, gate_id="run-9", title="T")
    ledger = load_rejected_ledger(tmp_path)
    entry = ledger["rejected"][0]
    assert entry["normalized_url"] == url
    assert entry["gate_id"] == "run-9"
    assert entry["title"] == "T"
    assert entry["rejected_at"].endswith("Z") or "+00:00" in entry["rejected_at"]


def test_rejected_ledger_path_under_construct_research(tmp_path: Path) -> None:
    p = rejected_ledger_path(tmp_path)
    assert p == tmp_path / ".construct" / "research" / "rejected.json"
    parts = set(p.parts)
    assert not ({"refs", "cards", "digests", "log"} & parts)


def test_rejected_append_is_cumulative(tmp_path: Path) -> None:
    append_rejected(
        tmp_path,
        normalized_url=normalize_url("https://example.com/a"),
        gate_id="run-1",
        title="A",
    )
    append_rejected(
        tmp_path,
        normalized_url=normalize_url("https://example.com/b"),
        gate_id="run-1",
        title="B",
    )
    urls = rejected_normalized_urls(load_rejected_ledger(tmp_path))
    assert urls == {
        normalize_url("https://example.com/a"),
        normalize_url("https://example.com/b"),
    }


def test_rejected_append_is_idempotent(tmp_path: Path) -> None:
    """WR-01/RSCH-05: re-appending the same normalized URL is a no-op, so a
    crash+resume that re-runs ingest never grows the ledger with duplicates."""
    url = normalize_url("https://example.com/a")
    append_rejected(tmp_path, normalized_url=url, gate_id="run-1", title="A")
    append_rejected(tmp_path, normalized_url=url, gate_id="run-1", title="A again")
    ledger = load_rejected_ledger(tmp_path)
    assert len(ledger["rejected"]) == 1
    assert rejected_normalized_urls(ledger) == {url}


def test_rejected_normalized_urls_returns_set() -> None:
    ledger = {"version": 1, "rejected": [{"normalized_url": "https://e.com/a"}]}
    result = rejected_normalized_urls(ledger)
    assert isinstance(result, set)
    assert result == {"https://e.com/a"}
