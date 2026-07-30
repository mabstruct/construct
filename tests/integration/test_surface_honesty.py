"""GOV-05: a degraded or partially-applied run says so on EVERY surface (Plan 08).

The defect chain this file pins is a rendering defect, not a modelling one. The
result model was already honest — ``status`` carried ``degraded`` — and the CLI's
per-step renderer already printed it. Then the very next line of the same output
block printed ``✓ Curation run degraded.``: an unqualified success verdict
contradicting the honest status line one line above it. In the ``--json`` payload
and the MCP result the outcome was flattened away entirely, into a bare
``success: true`` that means only "the command ran".

Every assertion below therefore reads **rendered output** — the CLI's stdout, the
JSON payload it emitted, the dict the MCP serializer produced — never the result
model. A result-model assertion would have passed against the broken code, which
is precisely why D-16 asks for a table-driven cross-surface test instead.

The table has one row per surface. Phase 19's HTTP surface joins by adding a row
to ``SURFACES``, not by forking this file.

**D-15 is preserved by this plan, not changed by it.** The Phase 11 exit-code
contract holds: a degraded ``curation.run`` still exits 0 on purpose, because the
CLI uses the exit code to mean "the command ran", and GOV-05 governs what a
surface *reports*. ``test_degraded_curation_run_exits_zero`` is the regression
guard for that, and it was written and observed passing BEFORE any renderer here
was touched.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, NamedTuple

import pytest
from typer.testing import CliRunner

from construct.capabilities.catalog import get_registry
from construct.cli import app
from construct.llm import curation_run
from construct.mcp.server import _serialize_result
from tests.llm.conftest import create_test_workspace

runner = CliRunner()


# ── The surface table ───────────────────────────────────────────────────────


class Rendered(NamedTuple):
    """What one surface actually produced for one invocation.

    ``text`` is the surface's output as a reader/consumer sees it; ``payload`` is
    the structured form where the surface has one. ``exit_code`` is meaningful
    only for the CLI surfaces — the MCP surface has no process to exit.
    """

    text: str
    payload: Any
    exit_code: int


_CLI_ARGV: dict[str, Callable[[dict], list[str]]] = {
    "curation.run": lambda p: ["curation", "run", "--workspace", p["workspace_path"]],
    "curation.inspect": lambda p: [
        "curation", "inspect", "--workspace", p["workspace_path"], "--run-id", p["run_id"],
    ],
}


def _cli_human(cap: str, payload: dict) -> Rendered:
    """The real Typer CLI, human-readable output — what a person reads."""
    res = runner.invoke(app, _CLI_ARGV[cap](payload))
    return Rendered(text=res.stdout, payload=None, exit_code=res.exit_code)


def _cli_json(cap: str, payload: dict) -> Rendered:
    """The real Typer CLI, ``--json`` payload — what a script parses."""
    res = runner.invoke(app, [*_CLI_ARGV[cap](payload), "--json"])
    parsed = json.loads(res.stdout) if res.stdout.strip() else None
    return Rendered(text=res.stdout, payload=parsed, exit_code=res.exit_code)


def _mcp(cap: str, payload: dict) -> Rendered:
    """The real MCP dispatch path — the same handler the stdio tool wraps.

    ``mcp/server.py:_serialize_result`` is the exact function the generated tool
    calls, so anything that does not survive it does not reach an MCP client.
    """
    result = get_registry().invoke(cap, payload)
    serialized = _serialize_result(result)
    return Rendered(text=json.dumps(serialized, indent=2), payload=serialized, exit_code=0)


SURFACES: list[tuple[str, Callable[[str, dict], Rendered]]] = [
    ("cli-human", _cli_human),
    ("cli-json", _cli_json),
    ("mcp", _mcp),
]
SURFACE_IDS = [name for name, _ in SURFACES]


# ── Fixtures: a degraded run, an escalated run, an empty run ────────────────


def _injected_required_failure(state: dict) -> dict:
    """Replace a REQUIRED node's body with a reported failure.

    Same seam as ``test_run_status_degraded_on_step_failure``: the graph is built
    inside ``run_curation_run``, so the patched module global is the one the
    compiled graph captures. A required step reporting ``failed`` is what D-09's
    aggregate turns into a ``degraded`` run.
    """
    return {
        "steps": [{
            "step": "connection_maintenance",
            "status": "failed",
            "required": True,
            "findings": {"error": "injected failure"},
            "summary": "injected required-step failure",
            "reason": "injected",
        }]
    }


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """No provider key: the L3 gates degrade to zero proposals, deterministically."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def clean_workspace(tmp_path: Path, offline: None) -> Path:
    """A workspace whose curation run completes cleanly with an empty queue."""
    ws = tmp_path / "clean-ws"
    create_test_workspace(ws)
    return ws


@pytest.fixture
def degraded_workspace(tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A workspace whose curation run is forced ``degraded`` by a required-step failure."""
    ws = tmp_path / "degraded-ws"
    create_test_workspace(ws)
    monkeypatch.setattr(curation_run, "connection_maintenance", _injected_required_failure)
    return ws


# ── The D-15 exit-code regression guard ─────────────────────────────────────
#
# Written and observed PASSING before any renderer in this plan was touched, so
# the guard exists before the code that could break it. GOV-05 changes what the
# surfaces report; it must not move a single exit code.


def test_degraded_curation_run_exits_zero(degraded_workspace: Path) -> None:
    """D-15 / the Phase 11 contract: a degraded run still exits 0, on purpose.

    The exit code means "the command ran". Reporting the degradation honestly is
    GOV-05's job; re-opening WR-04 sideways inside a repair phase is what
    recording D-15 was meant to prevent.
    """
    human = _cli_human("curation.run", {"workspace_path": str(degraded_workspace)})
    assert "degraded" in human.text, "the fixture did not actually produce a degraded run"
    assert human.exit_code == 0, human.text


def test_degraded_curation_run_json_exits_zero(degraded_workspace: Path) -> None:
    """The same contract on the ``--json`` surface: a degraded run exits 0."""
    payload = _cli_json("curation.run", {"workspace_path": str(degraded_workspace)})
    assert payload.payload["data"]["status"] == "degraded"
    assert payload.exit_code == 0, payload.text
    assert payload.payload["success"] is True, (
        "the success flag drives the exit code and means 'the command ran'; "
        "decoupling the reported outcome from it must not move it"
    )


def test_completed_curation_run_exits_zero(clean_workspace: Path) -> None:
    """The unchanged half of the contract: a clean run exits 0 too."""
    human = _cli_human("curation.run", {"workspace_path": str(clean_workspace)})
    assert "completed" in human.text
    assert human.exit_code == 0, human.text


# ── The completed-run output snapshot ───────────────────────────────────────

#: Captured from the REAL CLI on this plan's base commit, BEFORE the renderer
#: change, and masked only where the content is environment-derived (the run id,
#: each step's own summary, the event list). Everything the RENDERER decides —
#: which lines exist, their order, their prefixes, and the terminal verdict's
#: glyph and wording — is literal here. Adding an unconditional bucket line or
#: changing the verdict glyph on a clean run breaks this test, which is the
#: point: a completed run's human output must come through this plan untouched.
_COMPLETED_HUMAN_BEFORE = """\
status: completed
run_id: <run-id>
  - integrity_check: completed — <summary>
  - decay_scan: completed — <summary>
  - orphan_scan: completed — <summary>
  - promotion_review: completed — <summary>
  - connection_maintenance: completed — <summary>
  - compile_report: completed — <summary>
  - views_refresh_hook: skipped — <summary>
events: <events>
✓ Curation run completed.
"""


def _mask(text: str) -> str:
    """Mask the environment-derived fragments, keeping every renderer decision."""
    masked = re.sub(r"cur-\d{8}-\d{6}-[0-9a-f]+", "<run-id>", text)
    masked = re.sub(r"(?m)^(  - [a-z_]+: [a-z]+) — .*$", r"\1 — <summary>", masked)
    masked = re.sub(r"(?m)^events: .*$", "events: <events>", masked)
    return masked


def test_completed_run_human_output_is_unchanged(clean_workspace: Path) -> None:
    """A completed run renders exactly what it rendered before this plan."""
    human = _cli_human("curation.run", {"workspace_path": str(clean_workspace)})

    assert _mask(human.text) == _COMPLETED_HUMAN_BEFORE


# ── GOV-05: a degraded run reads as degraded on all three surfaces ──────────


@pytest.mark.parametrize("name,render", SURFACES, ids=SURFACE_IDS)
def test_degraded_reads_as_degraded_on_every_surface(
    name: str, render: Callable[[str, dict], Rendered], degraded_workspace: Path
) -> None:
    """The outcome reaches every surface, not just the result model.

    On the CLI's human output the word must appear in what a person reads; on the
    structured surfaces it must appear as a first-class ``outcome`` field on the
    envelope, not merely buried in ``data.status`` — a caller reading the envelope
    to decide "did this go well?" sees only ``success``, which means "the command
    ran" and is deliberately true for a degraded run.
    """
    out = render("curation.run", {"workspace_path": str(degraded_workspace)})

    assert "degraded" in out.text
    if out.payload is not None:
        assert out.payload["outcome"] == "degraded", (
            f"{name}: the reported outcome must ride on the envelope, decoupled "
            "from the success flag that drives the exit code"
        )


def test_degraded_human_output_has_no_unqualified_success_verdict(
    degraded_workspace: Path,
) -> None:
    """The prohibition, stated exactly: no surface may pair an honest status line
    with a contradicting verdict in the same output block.

    Before this plan the output read::

        status: degraded
        ...
        ✓ Curation run degraded.

    — an honest status line and an unqualified success glyph, four lines apart.
    """
    human = _cli_human("curation.run", {"workspace_path": str(degraded_workspace)})

    assert "status: degraded" in human.text, "the honest status line must survive"
    verdict = human.text.strip().splitlines()[-1]
    assert not verdict.startswith("✓"), (
        f"degraded run rendered an unqualified success verdict: {verdict!r}"
    )
    assert "degraded" in verdict, f"the verdict must carry the outcome: {verdict!r}"


def test_completed_run_still_renders_a_clean_success_verdict(clean_workspace: Path) -> None:
    """The qualification is driven by the outcome, not applied to everything: a
    genuinely completed run keeps its unqualified ✓."""
    human = _cli_human("curation.run", {"workspace_path": str(clean_workspace)})

    assert human.text.strip().splitlines()[-1] == "✓ Curation run completed."


# ── GOV-05: escalated items surface as flagged, in queue order, everywhere ──


_ESCALATED_ORDER = ["stale-connected-card", "fresh-card", "stale-orphan-card"]


@pytest.fixture
def escalated_run(tmp_path: Path, offline: None) -> tuple:
    """A REAL reviewed run carrying three escalated items and one applied item.

    Built by pausing a run whose consolidated queue is exactly the proposals
    under test and resuming it through the real review entry point — so the
    escalated bucket on the persisted state is one an actual reviewed run
    produced, not a hand-written state dict. Returns ``(workspace, run_id)``;
    the surfaces then read it back through ``curation.inspect``.
    """
    from tests.llm.conftest import write_card

    ws = tmp_path / "escalated-ws"
    create_test_workspace(ws)
    for card_id in (*_ESCALATED_ORDER, "applied-card"):
        write_card(ws, card_id, body=f"Fixture card {card_id}.")

    run_id = "cur-escalated-fixture"
    proposals = [
        curation_run.CurationProposal(
            kind="escalate", decision="escalate", payload={"card_id": card_id}
        )
        for card_id in _ESCALATED_ORDER
    ]
    proposals.append(
        curation_run.CurationProposal(
            kind="promotion", decision="promote",
            payload={"card_id": "applied-card", "target_lifecycle": "growing"},
        )
    )

    saver, conn = curation_run._open_checkpointer(ws)
    try:
        graph = curation_run.build_curation_run_graph(saver)
        cfg = {"configurable": {"thread_id": run_id}}
        state = curation_run._initial_state(
            curation_run.CurationRunInput(workspace_path=str(ws), run_id=run_id)
        )
        state["gate_queue"] = [p.model_dump(mode="json") for p in proposals]
        graph.invoke(state, cfg)
        snap = graph.get_state(cfg)
        assert snap.next == ("process_inbox",), snap.next
        queue = list(snap.values["gate_queue"])
        checkpoint = curation_run._checkpoint_id(snap)
    finally:
        conn.close()

    done = curation_run.review_curation_run(
        curation_run.CurationReviewInput(
            workspace_path=str(ws),
            run_id=run_id,
            checkpoint_id=checkpoint or "",
            decisions={entry["proposal_id"]: "approve" for entry in queue},
        )
    )
    assert done.status == "completed", done.message
    assert done.escalated == _ESCALATED_ORDER
    assert done.applied == ["applied-card"]
    return ws, run_id


@pytest.mark.parametrize("name,render", SURFACES, ids=SURFACE_IDS)
def test_escalated_bucket_appears_in_queue_order_on_every_surface(
    name: str, render: Callable[[str, dict], Rendered], escalated_run: tuple
) -> None:
    """GOV-05 ordering edge: the same items, in the same order, on every surface.

    A reader comparing the CLI to the JSON to an MCP client must not have to
    wonder which ordering is authoritative.
    """
    ws, run_id = escalated_run
    out = render("curation.inspect", {"workspace_path": str(ws), "run_id": run_id})

    positions = [out.text.index(card_id) for card_id in _ESCALATED_ORDER]
    assert positions == sorted(positions), (
        f"{name}: escalated items are not in queue order: {out.text}"
    )
    if out.payload is not None:
        assert out.payload["data"]["escalated"] == _ESCALATED_ORDER


@pytest.mark.parametrize("name,render", SURFACES, ids=SURFACE_IDS)
def test_applied_and_escalated_are_two_counts_never_their_sum(
    name: str, render: Callable[[str, dict], Rendered], escalated_run: tuple
) -> None:
    """GOV-05 adjacency edge: 1 applied and 3 escalated, and no surface prints 4.

    Folding them into one number is the exact failure mode D-16 names: an
    escalated item wrote nothing, so counting it alongside something that did is
    a claim about the knowledge base that is not true.
    """
    ws, run_id = escalated_run
    out = render("curation.inspect", {"workspace_path": str(ws), "run_id": run_id})

    if out.payload is not None:
        data = out.payload["data"]
        assert len(data["applied"]) == 1
        assert len(data["escalated"]) == 3
        for field, value in data.items():
            if isinstance(value, list) and field not in ("steps", "events", "gate_queue"):
                assert len(value) != 4, f"{name}: {field} holds the sum of applied and escalated"
    else:
        assert "4" not in re.sub(r"cur-[\w-]+", "", out.text), (
            f"{name}: a count of 4 — the sum of 1 applied and 3 escalated — reached "
            f"the human output:\n{out.text}"
        )


def test_escalated_bucket_is_labelled_for_its_real_effect(escalated_run: tuple) -> None:
    """A reader must be told escalation wrote nothing — the label is the whole
    point of D-16's relabelling clause."""
    ws, run_id = escalated_run
    human = _cli_human("curation.inspect", {"workspace_path": str(ws), "run_id": run_id})

    assert "escalated" in human.text
    assert curation_run.ESCALATED_LABEL in human.text, (
        f"the escalated bucket must be named for its real effect:\n{human.text}"
    )


# ── GOV-05 empty edge: a run with nothing to do claims nothing ─────────────


@pytest.mark.parametrize("name,render", SURFACES, ids=SURFACE_IDS)
def test_empty_run_reports_zero_applied_and_zero_escalated(
    name: str, render: Callable[[str, dict], Rendered], clean_workspace: Path
) -> None:
    """A run with zero proposals completes, applies nothing, escalates nothing,
    and emits no degraded warning — the honest empty case, which must not be
    dressed up as an accomplishment."""
    out = render("curation.run", {"workspace_path": str(clean_workspace)})

    assert "degraded" not in out.text
    if out.payload is not None:
        assert out.payload["data"]["status"] == "completed"
        assert out.payload["data"]["applied"] == []
        assert out.payload["data"]["escalated"] == []
        assert out.payload["outcome"] == "completed"
