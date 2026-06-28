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
_DEFERRED_STEPS = ("promotion_review", "process_inbox", "views_refresh_hook")

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
    """SC2: ``promotion_review``, ``process_inbox``, ``views_refresh_hook`` are
    present as ``skipped`` nodes with ``required=False`` and a "deferred to Phase
    12" reason — distinct from completed steps and from absent steps."""
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
        assert "deferred to Phase 12" in (step.get("reason") or "")


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
    flag and notes archiving is deferred to Phase 12 — but no card lifecycle is
    flipped to archived."""
    from construct.llm import curation_run
    from construct.storage.workspace import WorkspaceLoader

    _set_governance(curation_workspace, **{"decay.auto_archive_on_decay": True})

    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-autoarchive")
    )
    decay = _steps_by_name(run.steps)["decay_scan"]
    assert decay["findings"].get("auto_archive_on_decay") is True
    assert "deferred to Phase 12" in decay["summary"]

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
