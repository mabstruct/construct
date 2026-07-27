"""Wave 0 red suite for the deterministic ``curation.run`` workflow (Phase 11).

Every test pins one CUR-01 distinction and is the Nyquist sampling point that
must be able to FAIL if a step regresses to v0.3 placeholder behaviour. The
production module ``construct.llm.curation_run`` does NOT exist yet, so it is
imported lazily INSIDE each test body — never at module top — so
``--collect-only`` succeeds while the suite stays red on ImportError/AttributeError.

Sampling point → test map (RESEARCH §Validation Architecture):
  1. concrete counts/IDs present       → test_full_run_offline_real_findings
  2. degraded ≠ completed              → test_run_status_degraded_on_step_failure
  3. skipped-deferred nodes visible    → test_deferred_nodes_visible_skipped
  4. anti-placeholder guard            → test_steps_return_concrete_findings
  5. governance thresholds honored     → test_scans_use_governance_thresholds
  6. no canonical SOT writes           → test_no_canonical_writes
  6b. auto_archive reported not acted  → test_auto_archive_reported_not_acted
  RT-03 inspect reads, never re-runs   → test_inspect_no_rerun

The curation graph topology (spec §4.3) the integration test asserts on:
  integrity_check → decay_scan → orphan_scan → promotion_review(SKIP)
    → connection_maintenance → process_inbox(SKIP) → compile_report
    → views_refresh_hook(SKIP)
"""
from __future__ import annotations

from pathlib import Path

import yaml

# The five steps that must carry concrete findings (deferred nodes excluded).
_REAL_STEPS = (
    "integrity_check",
    "decay_scan",
    "orphan_scan",
    "connection_maintenance",
    "compile_report",
)
# Phase 12 turns ``promotion_review`` into a proposal PRODUCER and ``process_inbox``
# into the interrupt-only consolidated review gate (routed around on an empty
# queue), so neither is a deferred skip any longer. ``views_refresh_hook`` is the
# only node still deferred (its Phase-12 wiring lands in a later plan).
_DEFERRED_STEPS = ("views_refresh_hook",)

# Canonical source-of-truth artifacts D-06 protects. Derived ``log/`` and
# ``views/`` are intentionally EXCLUDED (Pitfall 1: bridge_detect writes there).
_CANONICAL = ("cards", "refs", "connections.json", "search-seeds.json")


# ── helpers ───────────────────────────────────────────────────────────────


def _steps_by_name(steps: list) -> dict:
    """Map a list of step dicts (or CurationStepResult) to {step_name: dict}."""
    out = {}
    for s in steps:
        s = s if isinstance(s, dict) else s.model_dump()
        out[s["step"]] = s
    return out


def _set_governance(ws: Path, **overrides) -> None:
    """Patch governance.yaml in place with the given decay/quality overrides."""
    path = ws / "governance.yaml"
    gov = yaml.safe_load(path.read_text(encoding="utf-8"))
    for dotted, value in overrides.items():
        section, key = dotted.split(".", 1)
        gov.setdefault(section, {})[key] = value
    path.write_text(yaml.safe_dump(gov, sort_keys=False), encoding="utf-8")


def _snapshot_canonical(ws: Path) -> dict:
    """Byte-snapshot every canonical SOT artifact (cards/refs trees + 2 files)."""
    snap: dict[str, bytes] = {}
    for name in _CANONICAL:
        target = ws / name
        if target.is_dir():
            for f in sorted(target.rglob("*")):
                if f.is_file():
                    snap[str(f.relative_to(ws))] = f.read_bytes()
        elif target.is_file():
            snap[name] = target.read_bytes()
    return snap


# ── 1. concrete findings across the full offline run ────────────────────────


def test_full_run_offline_real_findings(curation_workspace, sqlite_checkpointer):
    """CUR-01 / SC1: a full offline run produces real integrity + decay + orphan
    + connection-health + report findings — concrete counts/IDs, not bare
    success strings."""
    from construct.llm import curation_run

    saver, _conn, _db = sqlite_checkpointer()
    graph = curation_run.build_curation_run_graph(saver)
    cfg = {"configurable": {"thread_id": "cur-full"}}
    result = graph.invoke(
        curation_run._initial_state(
            curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-full")
        ),
        cfg,
    )

    steps = _steps_by_name(result["steps"])
    for name in _REAL_STEPS:
        assert name in steps, f"missing real step: {name}"
        findings = steps[name]["findings"]
        assert isinstance(findings, dict) and findings, f"{name} must carry concrete findings"

    # integrity_check exposes primitive counts (Pitfall 4 — no raw dataclass).
    integ = steps["integrity_check"]["findings"]
    for key in ("errors", "warnings", "ok"):
        assert key in integ, key

    # decay_scan: stale cards are candidates; fresh + archived are not.
    decay_ids = set(steps["decay_scan"]["findings"]["candidate_ids"])
    assert {"stale-orphan-card", "stale-connected-card"} <= decay_ids
    assert "fresh-card" not in decay_ids
    assert "stale-archived-card" not in decay_ids

    # orphan_scan: degree-0 stale card only; the connected stale card is NOT an
    # orphan and the fresh card is a connection target (degree > 0).
    orphan_ids = set(steps["orphan_scan"]["findings"]["candidate_ids"])
    assert "stale-orphan-card" in orphan_ids
    assert "stale-connected-card" not in orphan_ids
    assert "fresh-card" not in orphan_ids

    # compile_report rolls up graph_status counts.
    report = steps["compile_report"]["findings"]
    assert "cards" in report and "connections" in report


# ── 2. degraded vs completed discrimination ─────────────────────────────────


def test_run_status_degraded_on_step_failure(curation_workspace, monkeypatch):
    """SC2: a clean run is ``completed`` (NOT degraded despite the 3 deferred
    skips — Pitfall 5); a REQUIRED step reporting ``failed`` flips the run to
    ``degraded``."""
    from construct.llm import curation_run

    clean = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-clean")
    )
    assert clean.status == "completed"

    # Inject a required-step failure by replacing a real node body. The graph is
    # built inside run_curation_run, so the patched module global is captured.
    def _failed_connection(state):
        result = {
            "step": "connection_maintenance",
            "status": "failed",
            "required": True,
            "findings": {"error": "injected failure"},
            "summary": "injected required-step failure",
            "reason": "injected",
        }
        return {"steps": [result]}

    monkeypatch.setattr(curation_run, "connection_maintenance", _failed_connection)
    degraded = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-degraded")
    )
    assert degraded.status == "degraded"


# ── 3. deferred nodes visible as skipped ────────────────────────────────────


def test_deferred_nodes_visible_skipped(curation_workspace):
    """SC2: an optional node that does not act is visible as an explicit ``skipped``
    step with ``required=False`` and a reason describing WHY — never absent, and never
    a fabricated status.

    Phase 15 (D-12) wired ``views_refresh_hook`` to the real refresh, so its reason is
    now the live gate outcome rather than the old "deferred to Phase 12" placeholder.
    The fixture's install root has no ``views/build/``, so the existence gate skips —
    and the reason must say so. Asserting the reason is *derived* is what keeps this a
    fake-success guard: a hardcoded reason of any vintage fails the second assertion.
    """
    from construct.llm import curation_run

    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-deferred")
    )
    steps = _steps_by_name(run.steps)
    for name in _DEFERRED_STEPS:
        assert name in steps, f"deferred node not visible: {name}"
        step = steps[name]
        assert step["status"] == "skipped"
        assert step["required"] is False
        reason = step.get("reason") or ""
        assert "views/build" in reason, f"{name} must report the real gate reason, got: {reason!r}"
        assert "deferred to Phase 12" not in reason


# ── 4. anti-placeholder guard ───────────────────────────────────────────────


def test_steps_return_concrete_findings(curation_workspace):
    """SC3 / CUR-01: no real step emits a "placeholder" message; every real
    step's findings dict is non-empty (kills the v0.3 fake-success regression)."""
    from construct.llm import curation_run

    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-concrete")
    )
    steps = _steps_by_name(run.steps)
    for name in _REAL_STEPS:
        step = steps[name]
        assert "placeholder" not in (step.get("summary") or "").lower()
        assert "placeholder" not in (step.get("reason") or "").lower()
        assert isinstance(step["findings"], dict) and step["findings"], f"{name} findings empty"


# ── 5. governance thresholds honored ────────────────────────────────────────


def test_scans_use_governance_thresholds(curation_workspace):
    """D-05: decay/orphan candidate sets change when governance thresholds change
    — proves the scans read ``governance.yaml`` rather than hardcoding."""
    from construct.llm import curation_run

    tight = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-tight")
    )
    tight_steps = _steps_by_name(tight.steps)
    tight_decay = set(tight_steps["decay_scan"]["findings"]["candidate_ids"])
    tight_orphan = set(tight_steps["orphan_scan"]["findings"]["candidate_ids"])
    assert tight_decay, "default decay window should surface stale candidates"
    assert tight_orphan, "default orphan tolerance should surface the orphan"

    # Widen both windows far beyond any card's age → candidate sets must shrink.
    _set_governance(
        curation_workspace,
        **{"decay.decay_window_days": 100000, "quality.orphan_tolerance_days": 100000},
    )
    loose = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-loose")
    )
    loose_steps = _steps_by_name(loose.steps)
    loose_decay = set(loose_steps["decay_scan"]["findings"]["candidate_ids"])
    loose_orphan = set(loose_steps["orphan_scan"]["findings"]["candidate_ids"])

    assert loose_decay != tight_decay
    assert loose_orphan != tight_orphan
    assert not loose_decay
    assert not loose_orphan


# ── 6. no canonical SOT writes ──────────────────────────────────────────────


def test_no_canonical_writes(curation_workspace):
    """D-06 / T-11-04: cards/refs/connections.json/search-seeds.json are
    byte-identical before and after a run. Derived ``log/`` and ``views/`` are
    deliberately NOT asserted on (bridge_detect writes there — Pitfall 1)."""
    from construct.llm import curation_run

    before = _snapshot_canonical(curation_workspace)
    curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-nowrite")
    )
    after = _snapshot_canonical(curation_workspace)
    assert after == before, "curation.run must not mutate canonical source-of-truth artifacts"


def test_auto_archive_reported_not_acted(curation_workspace):
    """D-06: with ``decay.auto_archive_on_decay: true`` the decay step REPORTS the
    flag and states that it archives nothing and that archival needs explicit
    operator approval at the review gate — and no card lifecycle is flipped to
    archived."""
    from construct.llm import curation_run
    from construct.storage.workspace import WorkspaceLoader

    _set_governance(curation_workspace, **{"decay.auto_archive_on_decay": True})

    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-autoarchive")
    )
    decay = _steps_by_name(run.steps)["decay_scan"]
    assert decay["findings"].get("auto_archive_on_decay") is True
    assert "archived only after explicit operator approval" in decay["summary"]

    # No previously-non-archived card may have flipped to archived.
    cards = {c["id"]: str(c["lifecycle"]) for c in WorkspaceLoader(curation_workspace).load_cards()}
    for cid in ("fresh-card", "stale-orphan-card", "stale-connected-card"):
        assert "archived" not in cards[cid], f"{cid} must not have been auto-archived"


# ── RT-03: inspect reads persisted state, never re-runs ─────────────────────


def test_inspect_no_rerun(curation_workspace):
    """RT-03: ``inspect_curation_run`` reads the persisted terminal state and does
    NOT re-execute nodes — same run_id/steps, no workspace mutation."""
    from construct.llm import curation_run

    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-inspect")
    )
    before = _snapshot_canonical(curation_workspace)

    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(workspace_path=str(curation_workspace), run_id="cur-inspect")
    )
    assert insp.run_id == run.run_id
    assert _steps_by_name(insp.steps).keys() == _steps_by_name(run.steps).keys()

    after = _snapshot_canonical(curation_workspace)
    assert after == before, "inspect must not mutate the workspace or re-run nodes"


# ═════════════════════════════════════════════════════════════════════════════
# Phase 12 Wave 0 — HITL interrupt/resume + reviewed-write integration tests
# ═════════════════════════════════════════════════════════════════════════════
#
# These mirror ``tests/llm/test_research_run.py`` by name and grafts the same
# interrupt-only-gate → single-resume → post-gate-write machine onto curation.
# The production surface they drive is created in Plans 03-04:
#   * ``CurationRunResult`` gains ``gate_queue`` + ``gate_id`` and an
#     ``awaiting_review`` status (Plan 03).
#   * ``review_curation_run`` / ``CurationReviewInput`` (Plan 04).
#   * The interrupt-only pause node + three post-gate apply-nodes (Plan 03-04).
# Every new test imports lazily INSIDE its body so this file still COLLECTS and
# the existing Phase-11 green tests above stay unaffected; the new tests go RED on
# the absent review runner / gate_queue field / awaiting_review status.

import inspect as _inspect

from pathlib import Path as _Path


class _GateRoutingMock:
    """A single ``build_chat_model`` seam that drives BOTH L3 gates in one run.

    ``curation.run`` fans out over the promotion gate (``PromotionDecision``) and
    the connection-typing gate (``ConnectionTypeDecision``). One canned object
    cannot satisfy both, so this mock dispatches on the requested structured-output
    model class name — returning the promotion verdict for the promotion gate and
    the connection verdict for the typing gate. Card/pair identity is filled from
    the input by the gate runner, so a single canned verdict per gate is enough.
    """

    def __init__(self, *, promotion, connection) -> None:
        self._promotion = promotion
        self._connection = connection
        self._selected = None

    def with_structured_output(self, model_class, **kwargs):
        name = getattr(model_class, "__name__", "")
        self._selected = self._connection if "Connection" in name else self._promotion
        return self

    def invoke(self, messages):
        return self._selected


def _install_gate_mocks(
    monkeypatch,
    *,
    promotion_decision: str = "promote",
    target_lifecycle: str | None = "growing",
    connection_type: str = "supports",
):
    """Patch ``factory.build_chat_model`` so both L3 gates run offline.

    Lazily imports the Plan-02 gate output models, so calling this before those
    modules exist raises ``ModuleNotFoundError`` — the RED signal for every test
    that seeds the consolidated gate queue.
    """
    from construct.llm.curation_promote import PromotionDecision
    from construct.llm.curation_connect import ConnectionTypeDecision
    from tests.llm.conftest import make_build_chat_model

    promotion = PromotionDecision(
        card_id="_",
        decision=promotion_decision,
        target_lifecycle=target_lifecycle,
        reasoning="gate reasoning",
        method="llm-judgment",
    )
    connection = ConnectionTypeDecision(
        from_card_id="_",
        to_card_id="_",
        connection_type=connection_type,
        reasoning="typed by the connection gate",
    )
    mock = _GateRoutingMock(promotion=promotion, connection=connection)
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model", make_build_chat_model(mock)
    )


def _card_lifecycles(ws: _Path) -> dict:
    from construct.storage.workspace import WorkspaceLoader

    return {c["id"]: str(c["lifecycle"]) for c in WorkspaceLoader(ws).load_cards()}


def _connection_keys(ws: _Path) -> set:
    import json

    path = ws / "connections.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(c["from"], c["to"], c["type"]) for c in data.get("connections", [])}


# ── CUR-03 spine: no canonical write before Command(resume=approve) ──────────


def test_no_writes_before_approval(curation_workspace, monkeypatch):
    """CUR-03 / spine: at ``awaiting_review`` NO card lifecycle change, NO new
    connection, NO archive exists; canonical writes appear only AFTER approval."""
    from construct.llm import curation_run

    _install_gate_mocks(monkeypatch, promotion_decision="promote", target_lifecycle="growing")

    lifecycles_before = _card_lifecycles(curation_workspace)
    connections_before = _connection_keys(curation_workspace)

    result = curation_run.run_curation_run(
        curation_run.CurationRunInput(
            workspace_path=str(curation_workspace), run_id="cur-nowrite"
        )
    )

    assert result.status == "awaiting_review"
    assert result.gate_queue, "the consolidated review queue must be surfaced"
    assert result.gate_id == "cur-nowrite"

    assert _card_lifecycles(curation_workspace) == lifecycles_before, "no lifecycle write before approval"
    assert _connection_keys(curation_workspace) == connections_before, "no connection write before approval"
    for cid, lc in lifecycles_before.items():
        assert not (lc != "archived" and _card_lifecycles(curation_workspace)[cid] == "archived"), cid


# ── reviewed promotion: approve writes lifecycle; reject does not ────────────


def test_reviewed_promotion_applied(curation_workspace, monkeypatch):
    """CUR-03: an APPROVED promotion advances the card lifecycle via edit_card; a
    REJECTED promotion leaves every candidate untouched."""
    from construct.llm import curation_run

    _install_gate_mocks(monkeypatch, promotion_decision="promote", target_lifecycle="growing")

    start = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-promote")
    )
    assert start.status == "awaiting_review"

    done = _review(curation_workspace, "cur-promote", approve_all=True)
    assert done.status == "completed"
    after_approve = _card_lifecycles(curation_workspace)
    # seed cards approved for promotion advance to their target lifecycle.
    assert after_approve["fresh-card"] == "growing"

    # ── reject path on the remaining candidates: no further lifecycle change ──
    before_reject = _card_lifecycles(curation_workspace)
    curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-reject")
    )
    _review(curation_workspace, "cur-reject", reject_all=True)
    assert _card_lifecycles(curation_workspace) == before_reject, "reject must not write lifecycle"


# ── reviewed connection: typed + written via add_connection; idempotent rerun ─


def test_reviewed_connection_idempotent(curation_workspace, monkeypatch):
    """CUR-03: an APPROVED connection is typed and persisted via add_connection;
    a rerun with the same decisions is idempotent ("Connection already exists" —
    knowledge.py:416-423), producing no duplicate edge."""
    from construct.llm import curation_run

    _install_gate_mocks(monkeypatch, connection_type="supports")

    curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-conn")
    )
    done = _review(curation_workspace, "cur-conn", approve_all=True)
    assert done.status == "completed"
    after_first = _connection_keys(curation_workspace)

    # Re-run + re-approve the same proposals → add_connection dedups, no growth.
    curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-conn-2")
    )
    _review(curation_workspace, "cur-conn-2", approve_all=True)
    after_second = _connection_keys(curation_workspace)
    assert after_second == after_first, "idempotent connection apply must not duplicate edges"
    # No duplicate (from,to,type) tuples ever appear.
    assert len(after_second) == len(set(after_second))


# ── reviewed archive: only when approved AND auto_archive_on_decay=true ──────


def test_reviewed_archive_applied(curation_workspace, monkeypatch):
    """CUR-03: a decay-candidate is archived ONLY when the archive proposal is
    approved AND ``decay.auto_archive_on_decay`` is true."""
    from construct.llm import curation_run

    _set_governance(curation_workspace, **{"decay.auto_archive_on_decay": True})
    _install_gate_mocks(monkeypatch, promotion_decision="hold", target_lifecycle=None)

    start = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-archive")
    )
    assert start.status == "awaiting_review"

    _review(curation_workspace, "cur-archive", approve_all=True)
    after = _card_lifecycles(curation_workspace)
    # A stale decay-candidate is archived once approved under the flag.
    assert after["stale-orphan-card"] == "archived"
    # The fresh card is never a decay candidate → never archived.
    assert after["fresh-card"] != "archived"


# ── single consolidated gate: one gate_id, one resume covers all proposals ───


def test_single_consolidated_gate(curation_workspace, monkeypatch):
    """CUR-03: promotion + connection + archive proposals share ONE gate_id and are
    cleared by a SINGLE resume (not one gate per proposal type)."""
    from construct.llm import curation_run

    _set_governance(curation_workspace, **{"decay.auto_archive_on_decay": True})
    _install_gate_mocks(monkeypatch, promotion_decision="promote", target_lifecycle="growing")

    start = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-consolidated")
    )
    assert start.status == "awaiting_review"
    assert start.gate_id == "cur-consolidated"
    # The consolidated queue is a tagged union of proposal kinds.
    kinds = {entry.get("kind") for entry in start.gate_queue}
    assert kinds, "gate_queue must carry tagged proposal envelopes"
    assert kinds <= {"promotion", "connection", "archive", "escalate"}

    done = _review(curation_workspace, "cur-consolidated", approve_all=True)
    assert done.status == "completed"


# ── empty queue → completes without pausing (Pitfall 2) ─────────────────────


def test_empty_queue_no_pause(tmp_path, monkeypatch):
    """CUR-03: a run with nothing to review (no candidate cards/pairs) completes
    WITHOUT entering ``awaiting_review`` — an empty consolidated queue never pauses."""
    from construct.llm import curation_run
    from tests.llm.conftest import create_test_workspace

    ws = tmp_path / "empty-ws"
    create_test_workspace(ws)  # initializes a workspace with NO cards
    _install_gate_mocks(monkeypatch, promotion_decision="hold", target_lifecycle=None)

    result = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(ws), run_id="cur-empty")
    )
    assert result.status != "awaiting_review"
    assert result.status in ("completed", "degraded")
    # The queue field exists and is empty on a clean run.
    assert result.gate_queue == []


# ── CUR-05: no canonical write outside the post-gate apply nodes ─────────────


def test_no_unreviewed_writes(monkeypatch):
    """CUR-05: the pause node is interrupt-ONLY — it performs no canonical write
    and no event emission, so no write can originate before human approval. Every
    write therefore lives strictly downstream of the interrupt (mirrors
    research_run test_gate_review_is_interrupt_only)."""
    from construct.llm import curation_run

    gate_fn = getattr(curation_run, "gate_review", None) or getattr(
        curation_run, "process_inbox", None
    )
    assert gate_fn is not None, "an interrupt gate node must exist"
    src = _inspect.getsource(gate_fn)
    assert src.count("interrupt(") == 1, "the gate node must hold exactly one interrupt()"
    for forbidden in (
        "edit_card",
        "add_connection",
        "archive_card",
        "append_event",
        "write_text",
        ".write(",
    ):
        assert forbidden not in src, f"gate node must not perform {forbidden}"


# ── cross-process resume (fresh checkpointer over the same DB) ───────────────


def test_cross_process_resume(curation_workspace, sqlite_checkpointer, monkeypatch):
    """CUR-03: pause in one SqliteSaver/connection, close it, re-open a NEW
    SqliteSaver on the same DB file — ``get_state`` shows the pending consolidated
    queue and a single resume completes the run."""
    from construct.llm import curation_run
    from langgraph.types import Command

    _install_gate_mocks(monkeypatch, promotion_decision="promote", target_lifecycle="growing")

    cfg = {"configurable": {"thread_id": "cur-xproc"}}

    saver1, conn1, db_path = sqlite_checkpointer()
    graph1 = curation_run.build_curation_run_graph(saver1)
    res1 = graph1.invoke(
        curation_run._initial_state(
            curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-xproc")
        ),
        cfg,
    )
    assert "__interrupt__" in res1
    conn1.close()

    saver2, conn2, db_path2 = sqlite_checkpointer()
    assert db_path2 == db_path
    graph2 = curation_run.build_curation_run_graph(saver2)
    snap = graph2.get_state(cfg)
    assert snap.next == ("process_inbox",)
    assert snap.values.get("gate_queue"), "pending consolidated queue persisted across processes"

    # Phase 18 / GOV-02: the resume payload names each proposal by its opaque id.
    # It MUST cross Command(resume=…) inside _wrap_resume's envelope — a bare dict
    # is read by LangGraph as an interrupt-id mapping and silently discarded.
    decisions = {
        entry["proposal_id"]: entry.get("decision", "approve")
        for entry in snap.values["gate_queue"]
    }
    res2 = graph2.invoke(Command(resume=curation_run._wrap_resume(decisions)), cfg)
    assert graph2.get_state(cfg).next == ()
    assert res2["status"] == "completed"


# ── CUR-04: inspect reports awaiting_review + gate_queue, never resumes ──────


def test_inspect_pending_review(curation_workspace, monkeypatch):
    """CUR-04: ``inspect_curation_run`` reports ``awaiting_review`` and surfaces the
    pending consolidated queue WITHOUT resuming the graph (repeat inspect is
    stable; no canonical write)."""
    from construct.llm import curation_run

    _install_gate_mocks(monkeypatch, promotion_decision="promote", target_lifecycle="growing")

    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-pending")
    )
    assert run.status == "awaiting_review"

    before = _snapshot_canonical(curation_workspace)
    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(workspace_path=str(curation_workspace), run_id="cur-pending")
    )
    assert insp.status == "awaiting_review"
    assert insp.gate_queue, "inspect surfaces the pending consolidated queue"

    insp2 = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(workspace_path=str(curation_workspace), run_id="cur-pending")
    )
    assert insp2.status == "awaiting_review"
    assert _snapshot_canonical(curation_workspace) == before, "inspect must not mutate or resume"


# ── CUR-04: per-step + gate-review events emitted (spec §6.6) ────────────────


def test_curation_events_emitted(curation_workspace, monkeypatch):
    """CUR-04: a reviewed run appends per-step + gate-review events to the audit
    log (spec §6.6) — including a gate-review-approved event after resume."""
    from construct.llm import curation_run

    _install_gate_mocks(monkeypatch, promotion_decision="promote", target_lifecycle="growing")

    curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-events")
    )
    done = _review(curation_workspace, "cur-events", approve_all=True)
    assert done.status == "completed"

    events_log = (curation_workspace / "log" / "events.jsonl").read_text(encoding="utf-8")
    assert "gate_review_approved" in events_log
    assert "curation_cycle_complete" in events_log


# ═════════════════════════════════════════════════════════════════════════════
# Phase 18 Plan 06 — GOV-02 / GOV-03: opaque proposal ids, id-keyed decisions,
# complete-coverage rejection, and the checkpoint-id ETag
# ═════════════════════════════════════════════════════════════════════════════
#
# The defect these pin: ``_resolve_decisions`` zipped the resume payload against
# the queue POSITIONALLY and, when the payload was short or absent, substituted
# each proposal's own recommended ``decision`` — a canonical write the user never
# approved. Every test below asserts zero writes by reading the WORKSPACE back,
# never by trusting a return value.

#: One PRE-Phase-18 queued proposal: the exact dict shape the old producers
#: persisted, carrying NO ``proposal_id``. Seeded into the initial state so the
#: ``operator.add`` reducer lands it in the checkpoint verbatim.
_LEGACY_PROPOSAL = {
    "kind": "archive",
    "decision": "archive",
    "payload": {"card_id": "stale-orphan-card"},
}


def _pause_legacy_run(ws: _Path, run_id: str = "cur-legacy") -> list:
    """Build a REAL paused sqlite checkpoint whose queue carries no proposal ids.

    Writes through the module's own ``_open_checkpointer`` (the same
    ``.construct/workflow/curation-run.sqlite`` the review/inspect entry points
    re-open), seeding ``gate_queue`` with ``_LEGACY_PROPOSAL`` before the graph
    runs. Offline the three producers enqueue nothing, so the persisted queue is
    exactly the legacy entry — a faithful pre-Phase-18 pause. Returns the queue as
    persisted (still id-less).
    """
    from construct.llm import curation_run

    saver, conn = curation_run._open_checkpointer(ws)
    try:
        graph = curation_run.build_curation_run_graph(saver)
        cfg = {"configurable": {"thread_id": run_id}}
        state = curation_run._initial_state(
            curation_run.CurationRunInput(workspace_path=str(ws), run_id=run_id)
        )
        state["gate_queue"] = [dict(_LEGACY_PROPOSAL)]
        graph.invoke(state, cfg)
        snap = graph.get_state(cfg)
        assert snap.next == ("process_inbox",), snap.next
        return list(snap.values["gate_queue"])
    finally:
        conn.close()


def _raw_snapshot(ws: _Path, run_id: str):
    """Read the persisted snapshot through a fresh checkpointer (no migration)."""
    from construct.llm import curation_run

    saver, conn = curation_run._open_checkpointer(ws)
    try:
        graph = curation_run.build_curation_run_graph(saver)
        return graph.get_state({"configurable": {"thread_id": run_id}})
    finally:
        conn.close()


def _review(ws: _Path, run_id: str, **kwargs):
    """Resume a paused run the way a real caller must: read the current ETag first.

    D-11 makes ``checkpoint_id`` a REQUIRED field on the review input, so every
    resume is a conditional request. Tests that are not themselves about
    staleness go through this helper; the GOV-03 tests below pass explicit
    (stale, near-miss, replayed) ids instead.
    """
    from construct.llm import curation_run

    return curation_run.review_curation_run(
        curation_run.CurationReviewInput(
            workspace_path=str(ws),
            run_id=run_id,
            checkpoint_id=curation_run._checkpoint_id(_raw_snapshot(ws, run_id)) or "",
            **kwargs,
        )
    )


# ── Task 1: an opaque id on every proposal, minted at enqueue ────────────────


def test_proposal_id_is_opaque_and_unique(curation_workspace):
    """GOV-02 / D-09: ``CurationProposal`` carries ``proposal_id``, minted at
    enqueue, and two TEXTUALLY IDENTICAL proposals receive different ids — the
    property a content hash could never provide."""
    from construct.llm import curation_run

    assert "proposal_id" in curation_run.CurationProposal.model_fields

    payload = {"card_id": "stale-orphan-card"}
    first = curation_run.CurationProposal(kind="archive", decision="archive", payload=dict(payload))
    second = curation_run.CurationProposal(kind="archive", decision="archive", payload=dict(payload))

    assert first.proposal_id and second.proposal_id
    assert first.proposal_id != second.proposal_id, "identical proposals must not share an id"
    # The chosen form: the FULL 32-character uuid4 hex — never truncated.
    assert len(first.proposal_id) == 32, first.proposal_id
    # Opaque: nothing about the queue, the run, or the payload is readable from it.
    assert "stale-orphan-card" not in first.proposal_id
    assert "archive" not in first.proposal_id


def test_proposal_id_rejects_non_opaque_values():
    """T-18-08: a caller-supplied id carrying a path separator, a parent-directory
    segment, or whitespace is rejected by the identifier guard, and the message
    carries an example of the correct form (AGENTS.md validator convention)."""
    import pytest
    from pydantic import ValidationError

    from construct.llm import curation_run

    for evil in ("../../../tmp/evil", "a/b", "has space", "UPPER", "", "trailing-"):
        with pytest.raises(ValidationError) as excinfo:
            curation_run.CurationProposal(kind="archive", proposal_id=evil)
        message = str(excinfo.value)
        assert "proposal_id" in message
        # An example of a VALID id must appear so the caller can self-correct.
        assert curation_run._PROPOSAL_ID_EXAMPLE in message, message

    # A real minted id passes the same guard unchanged.
    good = curation_run._new_proposal_id()
    assert curation_run.CurationProposal(kind="archive", proposal_id=good).proposal_id == good


def test_proposal_id_survives_pause_and_reload(curation_workspace, monkeypatch):
    """D-09: the id is persisted INTO the sqlite checkpoint — a reload through a
    fresh checkpointer/connection surfaces exactly the ids the pause produced."""
    from construct.llm import curation_run

    _install_gate_mocks(monkeypatch, promotion_decision="promote", target_lifecycle="growing")

    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(
            workspace_path=str(curation_workspace), run_id="cur-idpersist"
        )
    )
    assert run.status == "awaiting_review"
    paused_ids = [entry["proposal_id"] for entry in run.gate_queue]
    assert paused_ids and all(paused_ids), "every queued proposal must carry an id"
    assert len(set(paused_ids)) == len(paused_ids), "ids must be unique within the queue"

    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-idpersist"
        )
    )
    assert [entry["proposal_id"] for entry in insp.gate_queue] == paused_ids


def test_legacy_checkpoint_migrated_on_read(curation_workspace):
    """D-12 / T-18-25: a run paused BEFORE this phase loads rather than erroring —
    ids are injected at the raw-dictionary stage, so the forbid-extra model never
    sees an id-less proposal — and migration restores the QUEUE and no decision."""
    from construct.llm import curation_run

    persisted = _pause_legacy_run(curation_workspace)
    assert persisted, "the legacy fixture must persist a queue"
    assert all("proposal_id" not in entry for entry in persisted), persisted

    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-legacy"
        )
    )
    assert insp.status == "awaiting_review", insp.message
    migrated_ids = [entry["proposal_id"] for entry in insp.gate_queue]
    assert len(migrated_ids) == len(persisted)
    assert all(migrated_ids), "every migrated proposal must have an id"
    assert len(set(migrated_ids)) == len(migrated_ids)

    # Migration is STABLE: the id a reader is shown is the id a resume accepts.
    # (It must also be write-free — persisting it would advance the checkpoint
    # that D-11 uses as an ETag, making every subsequent resume stale.)
    again = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-legacy"
        )
    )
    assert [entry["proposal_id"] for entry in again.gate_queue] == migrated_ids

    # NO decision was carried over: the resume payload channel is still unset and
    # the migrated entry still carries only the gate's own recommendation.
    snap = _raw_snapshot(curation_workspace, "cur-legacy")
    assert snap.values.get("decisions") is None, "migration must never carry a decision"
    assert all("proposal_id" not in entry for entry in snap.values["gate_queue"]), (
        "migration must not write back into the checkpoint"
    )


def test_research_gate_entries_carry_the_same_shape():
    """GOV-02: both graphs carry ONE shape — the research queue entry gains the
    same opaque id, minted the same way, guarded by the same validator."""
    import pytest
    from pydantic import ValidationError

    from construct.llm import research_run

    assert "proposal_id" in research_run.GateQueueEntry.model_fields
    first = research_run.GateQueueEntry(finding={"url": None}, decision="skip")
    second = research_run.GateQueueEntry(finding={"url": None}, decision="skip")
    # Two findings with a NULL url — the exact case the old url-keyed mode could
    # not distinguish — still receive distinct ids.
    assert first.proposal_id != second.proposal_id
    assert len(first.proposal_id) == 32

    with pytest.raises(ValidationError):
        research_run.GateQueueEntry(finding={}, decision="skip", proposal_id="../evil")


# ── Task 2: decisions are keyed by id; an incomplete map writes NOTHING ──────


def _paused_queue(ws: _Path, run_id: str, monkeypatch) -> list:
    """Drive a run to ``awaiting_review`` and return its id-carrying queue."""
    from construct.llm import curation_run

    _set_governance(ws, **{"decay.auto_archive_on_decay": True})
    _install_gate_mocks(monkeypatch, promotion_decision="promote", target_lifecycle="growing")
    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(ws), run_id=run_id)
    )
    assert run.status == "awaiting_review", run.message
    assert run.gate_queue, "the fixture must queue at least two proposals"
    return list(run.gate_queue)


def _workspace_state(ws: _Path) -> tuple:
    """Every canonical surface a rejected resume must leave untouched."""
    return (_snapshot_canonical(ws), _card_lifecycles(ws), _connection_keys(ws))


def test_complete_decision_map_is_applied(curation_workspace, monkeypatch):
    """GOV-02: a map whose key set EXACTLY equals the queued id set is applied."""
    from construct.llm import curation_run

    queue = _paused_queue(curation_workspace, "cur-map-ok", monkeypatch)
    decisions = {entry["proposal_id"]: entry["decision"] for entry in queue}

    done = _review(curation_workspace, "cur-map-ok", decisions=decisions)
    assert done.status == "completed", done.message
    assert _card_lifecycles(curation_workspace)["fresh-card"] == "growing"


def test_incomplete_decision_map_rejected_in_full(curation_workspace, monkeypatch):
    """D-10 / T-18-03: a map omitting ANY queued id is rejected in full — zero
    canonical writes, the run still paused, and the response naming the uncovered
    id. This is the defect: the old code substituted the gate's own recommendation."""
    from construct.llm import curation_run

    queue = _paused_queue(curation_workspace, "cur-map-short", monkeypatch)
    assert len(queue) >= 2, queue
    uncovered = queue[0]["proposal_id"]
    decisions = {entry["proposal_id"]: entry["decision"] for entry in queue[1:]}

    before = _workspace_state(curation_workspace)
    rejected = _review(curation_workspace, "cur-map-short", decisions=decisions)

    assert rejected.status == "failed", rejected.message
    assert uncovered in rejected.message, rejected.message
    # T-18-10: the rejection names ids only — never a workspace path or card body.
    assert str(curation_workspace) not in rejected.message
    # Zero writes, asserted by reading the workspace back.
    assert _workspace_state(curation_workspace) == before

    # The run stays paused exactly where the user left it.
    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-map-short"
        )
    )
    assert insp.status == "awaiting_review"
    assert [e["proposal_id"] for e in insp.gate_queue] == [e["proposal_id"] for e in queue]


def test_unknown_decision_id_rejected_in_full(curation_workspace, monkeypatch):
    """GOV-02 adjacency: a key that is not in the queue is a clean rejection
    naming the unknown id — never a silently ignored extra."""
    from construct.llm import curation_run

    queue = _paused_queue(curation_workspace, "cur-map-extra", monkeypatch)
    stranger = curation_run._new_proposal_id()
    decisions = {entry["proposal_id"]: entry["decision"] for entry in queue}
    decisions[stranger] = "reject"

    before = _workspace_state(curation_workspace)
    rejected = _review(curation_workspace, "cur-map-extra", decisions=decisions)
    assert rejected.status == "failed", rejected.message
    assert stranger in rejected.message, rejected.message
    assert _workspace_state(curation_workspace) == before


def test_resume_with_no_decisions_is_rejected(curation_workspace, monkeypatch):
    """T-18-03 / the prohibition: a resume carrying NO decisions is rejected rather
    than defaulting to the gate's own recommendation. Nothing may be decided on
    the user's behalf."""
    from construct.llm import curation_run

    queue = _paused_queue(curation_workspace, "cur-map-none", monkeypatch)
    before = _workspace_state(curation_workspace)

    rejected = _review(curation_workspace, "cur-map-none")
    assert rejected.status == "failed", rejected.message
    for entry in queue:
        assert entry["proposal_id"] in rejected.message
    assert _workspace_state(curation_workspace) == before, "no recommendation may be applied"


def test_legacy_positional_payload_is_rejected(curation_workspace, monkeypatch):
    """D-10 and D-12 are one contract: a MIGRATED queue still demands a complete
    id-keyed map, so no legacy positional payload can ever be applied to it.

    Rejected at BOTH layers: the input model no longer admits a list at all, and a
    list smuggled straight into graph state (past every surface) still resolves to
    zero decisions and is refused by the coverage check rather than being zipped
    against the queue."""
    import pytest
    from pydantic import ValidationError

    from construct.llm import curation_run

    queue = _paused_queue(curation_workspace, "cur-map-pos", monkeypatch)
    before = _workspace_state(curation_workspace)

    # Layer 1 — the trust boundary refuses the shape outright.
    with pytest.raises(ValidationError):
        curation_run.CurationReviewInput(
            workspace_path=str(curation_workspace), run_id="cur-map-pos",
            decisions=["approve", "approve", "approve"],
        )

    # Layer 2 — even past the boundary, a positional list is never applied.
    smuggled = {
        "run_id": "cur-map-pos",
        "gate_queue": queue,
        "decisions": ["approve"] * len(queue),
    }
    with pytest.raises(curation_run.IncompleteDecisionMap) as excinfo:
        curation_run._resolve_decisions(smuggled)
    assert excinfo.value.missing == sorted(e["proposal_id"] for e in queue)

    assert _workspace_state(curation_workspace) == before


def test_migrated_queue_requires_a_complete_map(curation_workspace):
    """D-12: a run paused before this phase keeps its pending work AND still
    requires an explicit, complete decision in the new shape."""
    from construct.llm import curation_run

    _pause_legacy_run(curation_workspace, run_id="cur-legacy-resume")
    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-legacy-resume"
        )
    )
    migrated_id = insp.gate_queue[0]["proposal_id"]

    before = _workspace_state(curation_workspace)
    rejected = _review(curation_workspace, "cur-legacy-resume")
    assert rejected.status == "failed", rejected.message
    assert migrated_id in rejected.message
    assert _workspace_state(curation_workspace) == before

    # The migrated id is the one a resume accepts — the pending work is not lost.
    done = _review(curation_workspace, "cur-legacy-resume", decisions={migrated_id: "archive"})
    assert done.status in ("completed", "degraded"), done.message
    assert _card_lifecycles(curation_workspace)["stale-orphan-card"] == "archived"


def test_blanket_flags_expand_into_a_complete_map(curation_workspace, monkeypatch, tmp_path):
    """T-18-24: approve-all / reject-all still work, by EXPANDING into a complete
    map over the queued ids — satisfying the coverage check rather than bypassing
    it. A bypass would be a second path to a write."""
    import shutil

    from construct.llm import curation_run

    queue = _paused_queue(curation_workspace, "cur-approve-all", monkeypatch)
    ids = {entry["proposal_id"] for entry in queue}
    for flag in ("approve_all", "reject_all"):
        expanded = curation_run._build_resume_decisions(
            curation_run.CurationReviewInput(
                workspace_path=str(curation_workspace), run_id="cur-approve-all",
                checkpoint_id="unused-here", **{flag: True},
            ),
            queue,
        )
        assert expanded.keys() == ids, f"{flag} must expand to a COMPLETE map"

    done = _review(curation_workspace, "cur-approve-all", approve_all=True)
    assert done.status == "completed", done.message
    assert _card_lifecycles(curation_workspace)["fresh-card"] == "growing"

    # reject-all on an identical, untouched copy writes nothing at all.
    ws_r = tmp_path / "curation-workspace-reject"
    shutil.copytree(tmp_path / "curation-workspace", ws_r)
    shutil.rmtree(ws_r / ".construct", ignore_errors=True)
    _paused_queue(ws_r, "cur-reject-all", monkeypatch)
    before = _workspace_state(ws_r)
    rejected = _review(ws_r, "cur-reject-all", reject_all=True)
    assert rejected.status == "completed", rejected.message
    assert _workspace_state(ws_r) == before, "reject-all must write nothing"


def test_decision_key_order_does_not_change_the_outcome(curation_workspace, monkeypatch, tmp_path):
    """GOV-02 ordering edge: the SAME decisions submitted in two different key
    orders, against two identical fresh runs, produce identical canonical writes
    and an identical event sequence. The outcome no longer depends on payload
    order — which is precisely what the positional zip made it depend on."""
    import shutil

    from construct.llm import curation_run

    ws_b = tmp_path / "curation-workspace-order-b"
    shutil.copytree(tmp_path / "curation-workspace", ws_b)

    queue_a = _paused_queue(curation_workspace, "cur-order-a", monkeypatch)
    queue_b = _paused_queue(ws_b, "cur-order-b", monkeypatch)
    assert [e["kind"] for e in queue_a] == [e["kind"] for e in queue_b], "runs must be identical"

    forward = {e["proposal_id"]: e["decision"] for e in queue_a}
    reverse = {e["proposal_id"]: e["decision"] for e in reversed(queue_b)}
    assert list(reverse) != [q["proposal_id"] for q in queue_b] or len(queue_b) == 1

    done_a = _review(curation_workspace, "cur-order-a", decisions=forward)
    done_b = _review(ws_b, "cur-order-b", decisions=reverse)

    assert done_a.status == done_b.status == "completed"
    assert done_a.events == done_b.events, "event sequence must not depend on key order"
    assert _card_lifecycles(curation_workspace) == _card_lifecycles(ws_b)
    assert _connection_keys(curation_workspace) == _connection_keys(ws_b)


def test_empty_queue_with_empty_map_resolves_cleanly():
    """GOV-02 empty edge: an empty queue with an empty map is not an error — it
    resolves to zero decisions and therefore zero writes."""
    from construct.llm import curation_run

    state = {"run_id": "cur-empty", "gate_queue": [], "decisions": {}}
    assert curation_run._resolve_decisions(state) == []
    assert curation_run._queue_and_decisions(state) == []


def test_research_url_keyed_decision_mode_is_gone():
    """GOV-02: ``research_run`` keyed decisions on a finding ``url`` — content-
    derived, nullable, not unique. The branch is REMOVED, not kept as a compatible
    alternative; leaving it would be the parity fork this requirement closes."""
    import inspect as _i

    import pytest

    from construct.llm import curation_run, research_run

    src = _i.getsource(research_run._resolve_decisions)
    assert "by_url" not in src, src
    assert "url" not in src, src

    # A url-keyed payload is now an unknown-key rejection, never a silent apply.
    state = {
        "run_id": "run-url",
        "gate_queue": [{"proposal_id": "a" * 32, "finding": {"url": "u"}, "decision": "skip"}],
        "decisions": [{"url": "u", "decision": "ref_only"}],
    }
    with pytest.raises(curation_run.IncompleteDecisionMap):
        research_run._resolve_decisions(state)


# ── Task 3: the checkpoint id as an ETag (GOV-03 / D-11) ────────────────────


def test_inspect_returns_the_checkpoint_id_etag(curation_workspace, monkeypatch):
    """D-11: inspecting a paused run returns the queue TOGETHER WITH the run's
    current checkpoint id, and that id is stable across repeated reads and across
    a second, independent connection to the same checkpoint database."""
    from construct.llm import curation_run

    _paused_queue(curation_workspace, "cur-etag", monkeypatch)

    first = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-etag"
        )
    )
    assert first.status == "awaiting_review"
    assert first.checkpoint_id, "the queue must be returned with its ETag"
    assert first.gate_queue

    second = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-etag"
        )
    )
    assert second.checkpoint_id == first.checkpoint_id, "stable across repeated reads"

    # A separate connection to the same DB reads the same id (cross-process).
    snap = _raw_snapshot(curation_workspace, "cur-etag")
    assert curation_run._checkpoint_id(snap) == first.checkpoint_id


def test_resume_with_current_etag_proceeds(curation_workspace, monkeypatch):
    """D-11: a resume carrying the run's current checkpoint id proceeds normally."""
    from construct.llm import curation_run

    _paused_queue(curation_workspace, "cur-etag-ok", monkeypatch)
    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-ok"
        )
    )

    done = curation_run.review_curation_run(
        curation_run.CurationReviewInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-ok",
            checkpoint_id=insp.checkpoint_id, approve_all=True,
        )
    )
    assert done.status == "completed", done.message
    assert _card_lifecycles(curation_workspace)["fresh-card"] == "growing"


def test_stale_etag_rejected_with_zero_writes(curation_workspace, monkeypatch):
    """GOV-03 boundary edge: a checkpoint id differing by a SINGLE character is
    rejected, nothing is written, and the run stays paused."""
    from construct.llm import curation_run

    _paused_queue(curation_workspace, "cur-etag-stale", monkeypatch)
    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-stale"
        )
    )
    current = insp.checkpoint_id
    tampered = current[:-1] + ("0" if current[-1] != "0" else "1")
    assert tampered != current and len(tampered) == len(current)

    before = _workspace_state(curation_workspace)
    rejected = curation_run.review_curation_run(
        curation_run.CurationReviewInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-stale",
            checkpoint_id=tampered, approve_all=True,
        )
    )
    assert rejected.status == "failed", rejected.message
    assert tampered in rejected.message and current in rejected.message
    assert _workspace_state(curation_workspace) == before

    after = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-stale"
        )
    )
    assert after.status == "awaiting_review"
    assert after.checkpoint_id == current, "a rejected resume must not advance the run"


def test_etag_comparison_is_exact_string_equality(curation_workspace, monkeypatch):
    """GOV-03 precision edge: no trimming, no case folding, no prefix matching.
    Each near-miss below is rejected, and each rejection writes nothing."""
    from construct.llm import curation_run

    _paused_queue(curation_workspace, "cur-etag-exact", monkeypatch)
    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-exact"
        )
    )
    current = insp.checkpoint_id
    near_misses = [
        f" {current}",
        f"{current} ",
        f"\t{current}\n",
        current.upper(),
        current[:-4],
        f"{current}0",
    ]

    before = _workspace_state(curation_workspace)
    for candidate in near_misses:
        if candidate == current:  # pragma: no cover - defensive
            continue
        rejected = curation_run.review_curation_run(
            curation_run.CurationReviewInput(
                workspace_path=str(curation_workspace), run_id="cur-etag-exact",
                checkpoint_id=candidate, approve_all=True,
            )
        )
        assert rejected.status == "failed", f"{candidate!r} must be rejected"
        assert _workspace_state(curation_workspace) == before, candidate


def test_replayed_resume_is_rejected_as_stale_etag(curation_workspace, monkeypatch):
    """GOV-03 idempotency edge — the sharpest of them: replaying a SUCCESSFUL
    resume (the same complete map, the same checkpoint id) is rejected, because
    the first resume advanced the checkpoint. This is what actually protects a
    user from a double-submitted review."""
    from construct.llm import curation_run

    queue = _paused_queue(curation_workspace, "cur-etag-replay", monkeypatch)
    insp = curation_run.inspect_curation_run(
        curation_run.CurationInspectInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-replay"
        )
    )
    decisions = {entry["proposal_id"]: entry["decision"] for entry in insp.gate_queue}
    assert len(decisions) == len(queue)

    first = curation_run.review_curation_run(
        curation_run.CurationReviewInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-replay",
            checkpoint_id=insp.checkpoint_id, decisions=decisions,
        )
    )
    assert first.status == "completed", first.message

    after_first = _workspace_state(curation_workspace)
    replay = curation_run.review_curation_run(
        curation_run.CurationReviewInput(
            workspace_path=str(curation_workspace), run_id="cur-etag-replay",
            checkpoint_id=insp.checkpoint_id, decisions=decisions,
        )
    )
    assert replay.status == "failed", replay.message
    assert "checkpoint" in replay.message.lower()
    assert _workspace_state(curation_workspace) == after_first, "a replay must write nothing"


def test_concurrency_configuration_stays_phase_19s(curation_workspace):
    """T-18-26: the checkpoint concurrency contract (write-ahead logging, busy
    timeouts, locking) is Phase 19's (OQ-4). The ETag stops cross-process
    MISAPPLICATION; it does not claim to survive lock contention, and this phase
    must not quietly start claiming otherwise."""
    from pathlib import Path as _P

    from construct.llm import curation_run, research_run

    for module in (curation_run, research_run):
        src = _P(module.__file__).read_text(encoding="utf-8")
        for forbidden in ("busy_timeout", "journal_mode"):
            assert forbidden not in src, f"{module.__name__} must not configure {forbidden}"
        assert "WAL" not in src, f"{module.__name__} must not configure WAL"
