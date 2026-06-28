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


@pytest.mark.xfail(reason=_PENDING, strict=False)
def test_no_writes_before_approval(test_workspace, sample_search_results, scored_findings_batch, monkeypatch):
    """RSCH-03 / SC2: at ``awaiting_review`` NO refs/cards/digest/seed writes
    exist; writes appear only after ``Command(resume=approve)``."""
    from construct.llm import research_run  # noqa: F401

    raise AssertionError("no-writes-before-approval gate not implemented yet")


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
