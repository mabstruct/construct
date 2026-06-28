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

from pathlib import Path

import pytest

_PENDING = "implemented in plans 02-05"


def test_full_run_offline(
    test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch
):
    """RSCH-02 / SC1: a full offline run composes search→dedup→score→review→
    ingest→digest→seeds→events: digest md + DigestRecord + last_queried + events."""
    import json

    from construct.llm import research_run
    from construct.llm import research_score
    from construct.views.models import DigestsFile
    from langgraph.types import Command

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    saver, conn, _db = sqlite_checkpointer()
    graph = research_run.build_research_run_graph(saver)
    cfg = {"configurable": {"thread_id": "run-full"}}
    graph.invoke(
        research_run._initial_state(
            research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-full")
        ),
        cfg,
    )
    snap = graph.get_state(cfg)
    defaults = [e["decision"] for e in snap.values["gate_queue"]]
    result = graph.invoke(Command(resume=defaults), cfg)

    assert result["status"] == "completed"

    # Refs written (arxiv ref+card, blog ref-only → 2 refs).
    assert any((test_workspace / "refs").glob("*.json"))

    # Digest markdown at digests/<id>.md.
    digest_path = Path(result["digest_path"])
    assert digest_path.exists()
    assert digest_path.parent == test_workspace / "digests"

    # DigestRecord appended to digests/digests.json.
    store_path = test_workspace / "digests" / "digests.json"
    assert store_path.exists()
    store = DigestsFile.model_validate_json(store_path.read_text(encoding="utf-8"))
    assert len(store.digests) == 1
    assert store.digests[0].id == "digest-run-full"

    # last_queried stamped on the queried clusters.
    seeds = json.loads((test_workspace / "search-seeds.json").read_text(encoding="utf-8"))
    queried = set(result.get("queried_clusters", []))
    stamped = [c for c in seeds["clusters"] if c["id"] in queried and c.get("last_queried")]
    assert stamped, "at least one queried cluster must have last_queried set"
    assert result["seed_update"] == "updated"

    # D-11 events appended to the audit log.
    events_log = (test_workspace / "log" / "events.jsonl").read_text(encoding="utf-8")
    for action in (
        "research_search_complete",
        "research_score_gate_complete",
        "gate_review_approved",
        "research_cycle_complete",
    ):
        assert action in events_log, action


def test_digest_degraded_notice(
    test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch
):
    """A degraded score-gate run surfaces a degraded notice in the digest markdown."""
    from construct.llm import research_run
    from construct.llm import research_score
    from langgraph.types import Command

    degraded = scored_findings_batch.model_copy(
        update={"retrieval": {**scored_findings_batch.retrieval, "degraded": True, "retried": 1, "errors": 1}}
    )
    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: degraded)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    saver, conn, _db = sqlite_checkpointer()
    graph = research_run.build_research_run_graph(saver)
    cfg = {"configurable": {"thread_id": "run-degraded"}}
    graph.invoke(
        research_run._initial_state(
            research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-degraded")
        ),
        cfg,
    )
    snap = graph.get_state(cfg)
    defaults = [e["decision"] for e in snap.values["gate_queue"]]
    result = graph.invoke(Command(resume=defaults), cfg)

    markdown = Path(result["digest_path"]).read_text(encoding="utf-8")
    assert "Degraded notice" in markdown


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


def test_per_finding_decisions(
    test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch
):
    """RSCH-03: per-finding reject → finding not ingested and appended to the
    rejected ledger; approve (ref_only) → a ref is written, no card."""
    from construct.llm import research_run
    from construct.llm import research_score
    from construct.pipelines import research_dedup
    from langgraph.types import Command

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    saver, conn, _db = sqlite_checkpointer()
    graph = research_run.build_research_run_graph(saver)
    cfg = {"configurable": {"thread_id": "run-pf"}}
    state = research_run._initial_state(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-pf")
    )
    graph.invoke(state, cfg)  # pause at the gate
    snap = graph.get_state(cfg)
    assert snap.next == ("gate_review",)

    # Reject the arxiv finding, approve the blog as ref_only, skip the shop page.
    result = graph.invoke(Command(resume=["skip", "ref_only", "skip"]), cfg)
    assert result["status"] == "completed"

    refs_dir = test_workspace / "refs"
    ref_files = {p.stem for p in refs_dir.glob("*.json")} if refs_dir.exists() else set()
    # Blog (ref_only) ingested; arxiv (rejected) NOT ingested.
    assert any("blog" in r for r in ref_files), ref_files
    assert not any("loop-quantum" in r for r in ref_files), ref_files

    # No card written for a ref_only approval.
    cards_dir = test_workspace / "cards"
    new_cards = [p.stem for p in cards_dir.glob("*.md") if p.stem not in {"card-1", "card-2", "card-3"}]
    assert new_cards == [], new_cards

    # Rejected findings (arxiv + shop) are in the rejected ledger.
    ledger = research_dedup.load_rejected_ledger(test_workspace)
    rejected_urls = research_dedup.rejected_normalized_urls(ledger)
    assert research_dedup.normalize_url("https://arxiv.org/abs/2401.00001") in rejected_urls
    assert research_dedup.normalize_url("https://shop.test/widgets") in rejected_urls


def test_reject_all_and_approve_all(sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch, tmp_path):
    """Task 3 shortcut behaviour at the graph level: approve-all reproduces the
    LLM's recommended ingest set; reject-all writes no refs and ledgers all."""
    from construct.llm import research_run
    from construct.llm import research_score
    from construct.pipelines import research_dedup
    from langgraph.types import Command

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    # ── approve-all on a clean workspace ──
    ws_a = _make_workspace(tmp_path / "ws-approve")
    saver, conn, _db = sqlite_checkpointer()
    graph = research_run.build_research_run_graph(saver)
    cfg_a = {"configurable": {"thread_id": "run-aa"}}
    graph.invoke(
        research_run._initial_state(
            research_run.ResearchRunInput(workspace_path=str(ws_a), run_id="run-aa")
        ),
        cfg_a,
    )
    snap_a = graph.get_state(cfg_a)
    # approve-all == each finding's recommended ingest_action (the default decision)
    approve_all = [e["decision"] for e in snap_a.values["gate_queue"]]
    res_a = graph.invoke(Command(resume=approve_all), cfg_a)
    # recommended set: arxiv ref+card, blog ref-only, shop skip → 2 refs, 1 card
    assert sorted(res_a["refs_created"]) == sorted(res_a["refs_created"])
    assert len(res_a["refs_created"]) == 2
    assert len(res_a["cards_created"]) == 1

    # ── reject-all on a separate clean workspace ──
    ws_r = _make_workspace(tmp_path / "ws-reject")
    cfg_r = {"configurable": {"thread_id": "run-ra"}}
    graph.invoke(
        research_run._initial_state(
            research_run.ResearchRunInput(workspace_path=str(ws_r), run_id="run-ra")
        ),
        cfg_r,
    )
    snap_r = graph.get_state(cfg_r)
    reject_all = ["skip"] * len(snap_r.values["gate_queue"])
    res_r = graph.invoke(Command(resume=reject_all), cfg_r)
    assert res_r["refs_created"] == []
    assert res_r["cards_created"] == []
    refs_r = test_dir = (ws_r / "refs")
    assert not refs_r.exists() or not any(refs_r.glob("*.json"))
    ledger = research_dedup.load_rejected_ledger(ws_r)
    assert len(research_dedup.rejected_normalized_urls(ledger)) == 3


def test_cross_process_resume(
    test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch
):
    """RSCH-04 / SC3: pause in one SqliteSaver/connection, close it, re-open a
    NEW SqliteSaver on the same DB file — ``get_state`` shows the pending batch
    and resume completes (mirrors ``test_workflow_runner`` r1/r2)."""
    from construct.llm import research_run
    from construct.llm import research_score
    from langgraph.types import Command

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    cfg = {"configurable": {"thread_id": "run-xproc"}}

    # ── Process 1: start, pause at the gate, close the connection ──
    saver1, conn1, db_path = sqlite_checkpointer()
    graph1 = research_run.build_research_run_graph(saver1)
    res1 = graph1.invoke(
        research_run._initial_state(
            research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-xproc")
        ),
        cfg,
    )
    assert "__interrupt__" in res1
    conn1.close()

    # ── Process 2: NEW SqliteSaver on the SAME db file ──
    saver2, conn2, db_path2 = sqlite_checkpointer()
    assert db_path2 == db_path
    graph2 = research_run.build_research_run_graph(saver2)
    snap = graph2.get_state(cfg)
    assert snap.next == ("gate_review",)
    assert snap.values.get("gate_queue"), "pending per-finding batch persisted across processes"

    decisions = [e["decision"] for e in snap.values["gate_queue"]]
    res2 = graph2.invoke(Command(resume=decisions), cfg)
    assert graph2.get_state(cfg).next == ()
    assert res2["status"] == "completed"
    assert any((test_workspace / "refs").glob("*.json"))
    assert Path(res2["digest_path"]).exists()


def test_inspect_no_resume(
    test_workspace, sample_search_results, scored_findings_batch, monkeypatch
):
    """RSCH-04: ``research.inspect`` returns the pending batch via ``get_state``
    WITHOUT resuming the graph (state.next unchanged afterward)."""
    from construct.llm import research_run
    from construct.llm import research_score

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    run = research_run.run_research_run(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-inspect")
    )
    assert run.status == "awaiting_review"

    insp = research_run.inspect_research_run(
        research_run.InspectInput(workspace_path=str(test_workspace), run_id="run-inspect")
    )
    assert insp.status == "awaiting_review"
    assert insp.gate_queue, "inspect surfaces the pending per-finding batch"

    # Inspect must NOT advance the graph or write refs.
    refs_dir = test_workspace / "refs"
    assert not refs_dir.exists() or not any(refs_dir.glob("*.json"))
    insp2 = research_run.inspect_research_run(
        research_run.InspectInput(workspace_path=str(test_workspace), run_id="run-inspect")
    )
    assert insp2.status == "awaiting_review"


def test_run_result_fields(
    test_workspace, sample_search_results, scored_findings_batch, monkeypatch
):
    """SC5: the run result exposes status, gate_ids, ref/card counts,
    digest_path, seed_update status, and an events list."""
    from construct.llm import research_run
    from construct.llm import research_score

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    start = research_run.run_research_run(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-result")
    )
    assert start.status == "awaiting_review"
    assert start.gate_id == "run-result"
    assert start.gate_queue

    done = research_run.review_research_run(
        research_run.ReviewInput(
            workspace_path=str(test_workspace), run_id="run-result", approve_all=True
        )
    )
    # D-12 / SC5 surface.
    assert done.status == "completed"
    assert done.run_id == "run-result"
    assert done.gate_id == "run-result"
    assert done.refs_created, "ref count surfaced"
    assert done.cards_created, "card count surfaced"
    assert done.digest_path and Path(done.digest_path).exists()
    assert done.seed_update == "updated"
    assert "research_cycle_complete" in done.events


def test_idempotent_rerun(
    test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch
):
    """RSCH-05 / SC4: rerunning the same inputs creates no duplicate refs
    (deterministic ID skip), and no ``-2``/``-3`` suffixed collision IDs appear."""
    from construct.llm import research_run
    from construct.llm import research_score
    from langgraph.types import Command

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    saver, conn, _db = sqlite_checkpointer()
    graph = research_run.build_research_run_graph(saver)

    def _run(thread_id):
        cfg = {"configurable": {"thread_id": thread_id}}
        graph.invoke(
            research_run._initial_state(
                research_run.ResearchRunInput(
                    workspace_path=str(test_workspace), run_id=thread_id
                )
            ),
            cfg,
        )
        snap = graph.get_state(cfg)
        defaults = [e["decision"] for e in snap.values["gate_queue"]]
        return graph.invoke(Command(resume=defaults), cfg)

    res1 = _run("run-idem-1")
    refs_dir = test_workspace / "refs"
    refs_after_1 = {p.name for p in refs_dir.glob("*.json")}

    res2 = _run("run-idem-2")
    refs_after_2 = {p.name for p in refs_dir.glob("*.json")}

    # No new ref files on the second identical run (deterministic ID + skip).
    assert refs_after_2 == refs_after_1
    # Second run skipped what the first created.
    assert res2["refs_created"] == []
    assert res2["skipped_existing"]
    # No collision-suffixed IDs (the D-07 anti-pattern).
    import re

    assert not any(re.search(r"-\d+\.json$", name) for name in refs_after_2), refs_after_2


def test_partial_batch_resume_safe(
    test_workspace, sample_search_results, scored_findings_batch, sqlite_checkpointer, monkeypatch
):
    """RSCH-05: a hard crash mid ``ingest_batch`` (after the first ref write)
    resumes and completes WITHOUT double-writing the already-ingested ref."""
    from construct.llm import research_run
    from construct.llm import research_score
    from construct.pipelines import ingestion
    from langgraph.types import Command

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    saver, conn, _db = sqlite_checkpointer()
    graph = research_run.build_research_run_graph(saver)
    cfg = {"configurable": {"thread_id": "run-partial"}}
    graph.invoke(
        research_run._initial_state(
            research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-partial")
        ),
        cfg,
    )

    class _SimulatedCrash(BaseException):
        """Escapes the per-finding ``except Exception`` to mimic a hard crash."""

    real_write = ingestion._write_ref_file
    calls = {"n": 0}

    def crashing_write(root, ref_id, ref):
        calls["n"] += 1
        if calls["n"] >= 2:  # first ref written, crash before the second
            raise _SimulatedCrash("simulated mid-batch crash")
        return real_write(root, ref_id, ref)

    monkeypatch.setattr(ingestion, "_write_ref_file", crashing_write)

    # Resume → ingest_batch starts, writes the first ref, then crashes hard.
    with pytest.raises(BaseException):
        graph.invoke(Command(resume=["ref_and_card", "ref_only", "skip"]), cfg)

    refs_dir = test_workspace / "refs"
    after_crash = {p.name for p in refs_dir.glob("*.json")}
    assert len(after_crash) == 1, after_crash  # exactly one ref survived the crash

    # Restore the real writer and resume the pending node.
    monkeypatch.setattr(ingestion, "_write_ref_file", real_write)
    result = graph.invoke(None, cfg)
    assert result["status"] == "completed"

    after_resume = {p.name for p in refs_dir.glob("*.json")}
    # First ref not double-written; batch completed (arxiv ref + blog ref = 2).
    assert len(after_resume) == 2, after_resume
    assert after_crash.issubset(after_resume)


# ─────────────────────────────────────────────────────────────────────────────
# Plan 03 Task 1 — state schema, in-module I/O models, pre-gate nodes (GREEN)
# ─────────────────────────────────────────────────────────────────────────────

import json


def _add_cluster(workspace, **cluster):
    seeds_path = workspace / "search-seeds.json"
    seeds = json.loads(seeds_path.read_text(encoding="utf-8"))
    seeds["clusters"].append(cluster)
    seeds_path.write_text(json.dumps(seeds, indent=2) + "\n", encoding="utf-8")


def _make_workspace(path):
    """Build a fresh minimal CONSTRUCT workspace (mirrors conftest.create_test_workspace)."""
    from construct.services.init import DomainInitInput, initialize_workspace

    domain = DomainInitInput(
        domain_id="test-domain",
        display_name="Test Domain",
        scope="Test domain.",
        taxonomy_seeds=["test-category"],
        source_priorities=["peer-reviewed papers"],
        research_seeds=["test research"],
    )
    initialize_workspace(path, domain)
    return path


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


# NOTE: the Plan 03 ``test_skeleton_post_gate_nodes_perform_no_writes`` test was
# removed in Plan 04 — the post-gate nodes are now fully implemented (they DO
# write, but only downstream of the gate interrupt). The enduring invariant
# (NO writes before approval) is covered by ``test_no_writes_before_approval``.


# ── Security + robustness regressions (post-verification gap closure) ──────


def test_run_id_rejects_path_traversal():
    """CR-01: a non-kebab ``run_id`` (path traversal) is rejected at the trust
    boundary on every input model, so it can never reach the digest file path."""
    import pytest as _pytest
    from pydantic import ValidationError

    from construct.llm import research_run

    evil = "../../../../tmp/evil"
    with _pytest.raises(ValidationError):
        research_run.ResearchRunInput(workspace_path="/ws", run_id=evil)
    with _pytest.raises(ValidationError):
        research_run.ReviewInput(workspace_path="/ws", run_id=evil)
    with _pytest.raises(ValidationError):
        research_run.InspectInput(workspace_path="/ws", run_id=evil)

    # The run-start default (run_id=None) stays valid.
    assert research_run.ResearchRunInput(workspace_path="/ws").run_id is None


def test_generated_run_id_is_kebab_safe():
    """CR-01: the auto-generated handle satisfies the same kebab invariant the
    validator enforces, so re-validation inside ``run_research_run`` never trips."""
    from construct.llm import research_run
    from construct.schemas.config import KEBAB_CASE_PATTERN

    rid = research_run._new_run_id()
    assert KEBAB_CASE_PATTERN.fullmatch(rid) is not None, rid
    # And it round-trips through the validated input model.
    assert research_run.ResearchRunInput(workspace_path="/ws", run_id=rid).run_id == rid


def test_inspect_nonexistent_run_reports_failed(tmp_path):
    """WR-03: inspecting a run that does not exist returns ``status='failed'`` so
    the catalog shim maps it to ``success=False`` (not a misleading success)."""
    from construct.llm import research_run

    insp = research_run.inspect_research_run(
        research_run.InspectInput(workspace_path=str(tmp_path), run_id="run-nope")
    )
    assert insp.status == "failed"


def test_review_does_not_resume_completed_run(
    test_workspace, sample_search_results, scored_findings_batch, monkeypatch
):
    """WR-05: re-reviewing an already-completed run is a no-op — it must NOT
    re-execute the post-gate write nodes (no duplicate events / re-stamped seeds)."""
    from construct.llm import research_run
    from construct.llm import research_score

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    research_run.run_research_run(
        research_run.ResearchRunInput(workspace_path=str(test_workspace), run_id="run-twice")
    )
    first = research_run.review_research_run(
        research_run.ReviewInput(
            workspace_path=str(test_workspace), run_id="run-twice", approve_all=True
        )
    )
    assert first.status == "completed"
    first_events = list(first.events)

    # Second review of the now-completed run must not re-run the write nodes.
    second = research_run.review_research_run(
        research_run.ReviewInput(
            workspace_path=str(test_workspace), run_id="run-twice", approve_all=True
        )
    )
    assert second.status == "completed"
    assert second.events == first_events, "completed run must not re-emit events"


def test_review_nonexistent_run_reports_failed(tmp_path):
    """WR-05: reviewing a run_id with no paused state returns failed, not a resume."""
    from construct.llm import research_run

    res = research_run.review_research_run(
        research_run.ReviewInput(workspace_path=str(tmp_path), run_id="run-ghost", approve_all=True)
    )
    assert res.status == "failed"
