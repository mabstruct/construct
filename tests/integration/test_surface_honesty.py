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
