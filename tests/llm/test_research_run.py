"""Wave 0 red suite for the durable ``research.run`` workflow (Phase 10).

Every test here is the Nyquist sampling point for one phase requirement and is
marked ``xfail(strict=False)`` until plans 02-05 turn it green. The production
module ``construct.llm.research_run`` does NOT exist yet, so it is imported
lazily INSIDE each test body — never at module top — so ``--collect-only``
succeeds while the suite stays red.

Requirement → test map (RESEARCH §Validation Architecture):
  RSCH-02 / SC1  → test_full_run_offline
  RSCH-03 / SC2  → test_no_writes_before_approval
  RSCH-03        → test_per_finding_decisions
  RSCH-04 / SC3  → test_cross_process_resume
  RSCH-04        → test_inspect_no_resume
  RSCH-05 / SC4  → test_idempotent_rerun
  RSCH-05        → test_partial_batch_resume_safe
  SC5            → test_run_result_fields
"""
from __future__ import annotations

import pytest

_PENDING = "implemented in plans 02-05"


@pytest.mark.xfail(reason=_PENDING, strict=False)
def test_full_run_offline(test_workspace, sample_search_results, scored_findings_batch, monkeypatch):
    """RSCH-02 / SC1: a full offline run composes search→dedup→score→review→
    ingest→digest→seeds→events and returns a result carrying the D-12 fields."""
    from construct.llm import research_run  # noqa: F401  (does not exist yet)

    raise AssertionError("research.run full-run composition not implemented yet")


def test_no_writes_before_approval(test_workspace, sample_search_results, scored_findings_batch, monkeypatch):
    """RSCH-03 / SC2: at ``awaiting_review`` NO refs/cards/digest/seed writes
    exist; writes appear only after ``Command(resume=approve)`` (Plan 04)."""
    from construct.llm import research_run
    from construct.llm import research_score

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    refs_dir = test_workspace / "refs"
    cards_dir = test_workspace / "cards"
    refs_before = set(refs_dir.glob("*.json")) if refs_dir.exists() else set()
    cards_before = set(cards_dir.glob("*.md"))
    seeds_before = (test_workspace / "search-seeds.json").read_text(encoding="utf-8")

    result = research_run.run_research_run(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-nowrite")
    )

    assert result.status == "awaiting_review"
    assert result.gate_queue, "pending per-finding batch must be surfaced"
    assert result.gate_id == "run-nowrite"

    refs_after = set(refs_dir.glob("*.json")) if refs_dir.exists() else set()
    cards_after = set(cards_dir.glob("*.md"))
    assert refs_after == refs_before, "no ref writes before approval"
    assert cards_after == cards_before, "no card writes before approval"
    assert (test_workspace / "search-seeds.json").read_text(encoding="utf-8") == seeds_before
    digests = test_workspace / "digests"
    assert not digests.exists() or not any(digests.rglob("*.md")), "no digest before approval"


@pytest.mark.xfail(reason=_PENDING, strict=False)
def test_per_finding_decisions(test_workspace, scored_findings_batch, monkeypatch):
    """RSCH-03: per-finding reject → finding not ingested and appended to the
    rejected ledger; ``approve-all`` / ``reject-all`` shortcuts honored."""
    from construct.llm import research_run  # noqa: F401

    raise AssertionError("per-finding decision routing not implemented yet")


@pytest.mark.xfail(reason=_PENDING, strict=False)
def test_cross_process_resume(test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch):
    """RSCH-04 / SC3: pause in one SqliteSaver/connection, close it, re-open a
    NEW SqliteSaver on the same DB file — ``get_state`` shows the pending batch
    and resume completes (mirrors ``test_workflow_runner`` r1/r2)."""
    from construct.llm import research_run  # noqa: F401

    saver1, conn1, db_path = sqlite_checkpointer()
    raise AssertionError("cross-process SqliteSaver resume not implemented yet")


@pytest.mark.xfail(reason=_PENDING, strict=False)
def test_inspect_no_resume(test_workspace, sqlite_checkpointer, monkeypatch):
    """RSCH-04: ``research.inspect`` returns the pending batch via ``get_state``
    WITHOUT resuming the graph."""
    from construct.llm import research_run  # noqa: F401

    raise AssertionError("research.inspect (get_state, no resume) not implemented yet")


@pytest.mark.xfail(reason=_PENDING, strict=False)
def test_idempotent_rerun(test_workspace, sample_search_results, scored_findings_batch, monkeypatch):
    """RSCH-05 / SC4: rerunning the same inputs creates no duplicate refs
    (deterministic ID skip), rejected findings are not re-proposed (ledger), and
    normalized-URL + title-fuzzy dedup hold."""
    from construct.llm import research_run  # noqa: F401

    raise AssertionError("idempotent rerun / dedup not implemented yet")


@pytest.mark.xfail(reason=_PENDING, strict=False)
def test_partial_batch_resume_safe(test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch):
    """RSCH-05: a crash mid ``ingest_batch`` (interrupt after the first write)
    resumes and completes WITHOUT double-writing the already-ingested finding."""
    from construct.llm import research_run  # noqa: F401

    raise AssertionError("partial-batch resume safety not implemented yet")


@pytest.mark.xfail(reason=_PENDING, strict=False)
def test_run_result_fields(test_workspace, sample_search_results, scored_findings_batch, monkeypatch):
    """SC5: the run result exposes status, gate_ids, ref/card counts,
    digest_path, seed_update status, and an events list."""
    from construct.llm import research_run  # noqa: F401

    raise AssertionError("RunResult D-12 field surface not implemented yet")


# ─────────────────────────────────────────────────────────────────────────────
# Plan 03 Task 1 — state schema, in-module I/O models, pre-gate nodes (GREEN)
# ─────────────────────────────────────────────────────────────────────────────

import json


def _add_cluster(workspace, **cluster):
    seeds_path = workspace / "search-seeds.json"
    seeds = json.loads(seeds_path.read_text(encoding="utf-8"))
    seeds["clusters"].append(cluster)
    seeds_path.write_text(json.dumps(seeds, indent=2) + "\n", encoding="utf-8")


def _search_result_dict(url, title, *, tier=3, score=0.5):
    return {
        "title": title,
        "url": url,
        "snippet": "snippet",
        "source_tier": tier,
        "score": score,
        "provider_specific": {},
        "source_domain": None,
    }


def test_models_defined_in_module():
    """The I/O models live in research_run, NOT catalog.py (avoid circular import)."""
    from construct.llm import research_run

    for name in [
        "ResearchRunInput",
        "ReviewInput",
        "InspectInput",
        "RunResult",
        "GateQueueEntry",
        "ResearchRunState",
    ]:
        assert hasattr(research_run, name), f"missing model/type: {name}"
    # ResearchRunState must be a TypedDict (plain serializable channels).
    assert research_run.ResearchRunState.__class__.__name__ in {"_TypedDictMeta", "type"}


def test_models_state_holds_no_nonserializable_defaults():
    """A fresh state dict holds only plain serializable data (Pitfall 3)."""
    from construct.llm import research_run

    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path="/tmp/ws", run_id="run-x")
    )
    # Round-trips through JSON → proves no WorkspaceLoader / client / sqlite conn.
    json.dumps(state)


def test_build_queries_excludes_non_active(test_workspace):
    """Paused/exhausted clusters and empty-term reserved clusters are excluded."""
    from construct.llm import research_run

    _add_cluster(
        test_workspace,
        id="paused-topic",
        domain="test-domain",
        terms=["paused term"],
        weight=0.5,
        status="paused",
        last_queried=None,
    )
    _add_cluster(
        test_workspace,
        id="active-two",
        domain="test-domain",
        terms=["second active term"],
        weight=0.5,
        status="active",
        last_queried=None,
    )
    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-x")
    )
    state.update(research_run.load_config(state))
    out = research_run.build_queries(state)

    assert "paused-topic" not in out["queried_clusters"]
    # reserved empty-term ingest clusters never become queries
    assert "manual-ingest" not in out["queried_clusters"]
    assert "web-ingest" not in out["queried_clusters"]
    # active clusters with terms are queried
    assert "active-two" in out["queried_clusters"]
    assert "test-domain-seed" in out["queried_clusters"]
    assert len(out["queries"]) == len(out["queried_clusters"])


def test_build_queries_respects_max_papers_per_cycle(test_workspace):
    """The query list is capped at governance max_papers_per_cycle."""
    from construct.llm import research_run

    for i in range(4):
        _add_cluster(
            test_workspace,
            id=f"topic-{i}",
            domain="test-domain",
            terms=[f"term {i}"],
            weight=0.5,
            status="active",
            last_queried=None,
        )
    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-x")
    )
    state.update(research_run.load_config(state))
    state["max_papers_per_cycle"] = 2
    out = research_run.build_queries(state)
    assert len(out["queries"]) == 2


def test_deduplicate_filters_existing_refs_ledger_fuzzy_and_inbatch(test_workspace):
    """deduplicate drops refs/ URLs, ledger URLs, in-batch dups, and title fuzzy."""
    from construct.llm import research_run
    from construct.pipelines import research_dedup

    refs = test_workspace / "refs"
    refs.mkdir(exist_ok=True)
    existing_url = "https://arxiv.org/abs/2401.00001"
    (refs / "existing-ref.json").write_text(
        json.dumps(
            {
                "id": "existing-ref",
                "title": "Loop Quantum Gravity and the Big Bounce",
                "url": existing_url,
                "relevance_score": 0.9,
                "key_findings": [],
                "content_categories": [],
                "source_tier": 2,
                "extraction_status": "complete",
                "ingested_date": "2026-01-01",
                "domain": "test-domain",
                "search_cluster": "test-domain-seed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    research_dedup.append_rejected(
        test_workspace,
        normalized_url=research_dedup.normalize_url("https://shop.test/widgets"),
        gate_id="run-x",
        title="Unrelated marketing page",
    )

    candidates = [
        # normalized-URL + title-fuzzy dup of an existing ref (tracking param stripped)
        _search_result_dict(
            "https://arxiv.org/abs/2401.00001?utm_source=newsletter",
            "Loop Quantum Gravity and the Big Bounce",
            tier=2,
            score=0.9,
        ),
        # in the rejected ledger
        _search_result_dict("https://shop.test/widgets", "Unrelated marketing page", tier=5, score=0.1),
        # brand-new finding (kept)
        _search_result_dict("https://new.test/article", "A brand new finding", tier=3, score=0.6),
        # in-batch duplicate of the previous (dropped)
        _search_result_dict("https://new.test/article", "A brand new finding", tier=3, score=0.6),
    ]
    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-x")
    )
    state["search_results"] = candidates
    out = research_run.deduplicate(state)
    urls = [c["url"] for c in out["deduped"]]

    assert urls.count("https://new.test/article") == 1
    assert all("arxiv.org" not in u for u in urls)
    assert all("shop.test" not in u for u in urls)


def test_score_and_extract_catches_outage_before_gate(test_workspace, monkeypatch):
    """ResearchScoreOutageError is caught → status failed, no raise, no gate_queue."""
    from construct.llm import research_run
    from construct.llm import research_score

    def _boom(gate_id, input_data, *, config_path=None):
        raise research_score.ResearchScoreOutageError(
            "All scoring requests failed due to provider authentication error"
        )

    monkeypatch.setattr(research_score, "run_gate", _boom)

    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-x")
    )
    state["gate_id"] = "run-x"
    state["deduped"] = [_search_result_dict("https://arxiv.org/abs/2401.00001", "LQG")]

    out = research_run.score_and_extract(state)
    assert out["status"] == "failed"
    assert out["retrieval"]["total_outage"] is True
    assert out["gate_queue"] == []


def test_score_and_extract_carries_degraded_and_builds_queue(
    test_workspace, scored_findings_batch, monkeypatch
):
    """Degraded signal is carried and gate_queue default decision = ingest_action."""
    from construct.llm import research_run
    from construct.llm import research_score

    degraded = scored_findings_batch.model_copy(
        update={
            "retrieval": {
                **scored_findings_batch.retrieval,
                "degraded": True,
                "retried": 1,
                "errors": 1,
            }
        }
    )
    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: degraded)

    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-x")
    )
    state["gate_id"] = "run-x"
    state["deduped"] = [_search_result_dict("https://arxiv.org/abs/2401.00001", "LQG")]

    out = research_run.score_and_extract(state)
    assert out["status"] != "failed"
    assert out["retrieval"]["degraded"] is True
    assert len(out["gate_queue"]) == 3
    # default decision mirrors the LLM's ingest_action (D-04)
    assert out["gate_queue"][0]["decision"] == "ref_and_card"
    assert out["gate_queue"][2]["decision"] == "skip"


# ─────────────────────────────────────────────────────────────────────────────
# Plan 03 Task 2 — interrupt gate, graph builder, checkpointer, run-start runner
# ─────────────────────────────────────────────────────────────────────────────

import inspect


def test_gate_review_is_interrupt_only():
    """T-10-07: the gate node body contains a single interrupt() and no writes."""
    from construct.llm import research_run

    src = inspect.getsource(research_run.gate_review)
    assert src.count("interrupt(") == 1
    for forbidden in (
        "_write_ref_file",
        "create_card",
        "append_event",
        "append_rejected",
        "write_text",
        ".write(",
    ):
        assert forbidden not in src, f"gate node must not perform {forbidden}"


def test_open_checkpointer_targets_construct(tmp_path):
    """Checkpointer DB lives at .construct/workflow/research-run.sqlite (D-02)."""
    from construct.llm import research_run
    from langgraph.checkpoint.sqlite import SqliteSaver

    saver, conn = research_run._open_checkpointer(tmp_path)
    try:
        db = tmp_path / ".construct" / "workflow" / "research-run.sqlite"
        assert db.exists()
        assert isinstance(saver, SqliteSaver)
    finally:
        conn.close()


def test_graph_pauses_at_gate_interrupt(
    test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch
):
    """build_research_run_graph compiles and pauses at the gate_review interrupt."""
    from construct.llm import research_run
    from construct.llm import research_score

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    saver, conn, _db = sqlite_checkpointer()
    graph = research_run.build_research_run_graph(saver)
    cfg = {"configurable": {"thread_id": "run-pause"}}
    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-pause")
    )
    result = graph.invoke(state, cfg)

    assert "__interrupt__" in result
    snap = graph.get_state(cfg)
    assert snap.next == ("gate_review",)
    assert snap.values.get("gate_queue"), "pending per-finding batch persisted"


def test_graph_outage_never_pauses(test_workspace, sqlite_checkpointer, monkeypatch):
    """A total outage routes to END (status failed) and never reaches the gate."""
    from construct.llm import research_run
    from construct.llm import research_score

    def _boom(*a, **k):
        raise research_score.ResearchScoreOutageError("authentication error (401)")

    monkeypatch.setattr(research_score, "run_gate", _boom)
    monkeypatch.setattr(
        research_run, "_run_search", lambda *a, **k: [_search_result_dict("https://x.test/a", "A")]
    )

    saver, conn, _db = sqlite_checkpointer()
    graph = research_run.build_research_run_graph(saver)
    cfg = {"configurable": {"thread_id": "run-outage"}}
    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-outage")
    )
    result = graph.invoke(state, cfg)

    assert "__interrupt__" not in result
    assert result["status"] == "failed"
    assert graph.get_state(cfg).next == ()


def test_skeleton_post_gate_nodes_perform_no_writes():
    """Plan 03 skeleton write nodes return no-write partial state (T-10-07)."""
    from construct.llm import research_run

    for node_name in ("ingest_batch", "compile_digest", "update_seeds_and_log"):
        node = getattr(research_run, node_name)
        src = inspect.getsource(node)
        for forbidden in ("_write_ref_file", "create_card", "append_event", "write_text"):
            assert forbidden not in src, f"{node_name} must not write in Plan 03"
