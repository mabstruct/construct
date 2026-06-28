"""Unit coverage for RSCH-05 idempotency primitives (research_dedup)."""

from __future__ import annotations

from construct.schemas.config import KEBAB_CASE_PATTERN
from construct.pipelines.research_dedup import (
    normalize_url,
    ref_id_for,
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
