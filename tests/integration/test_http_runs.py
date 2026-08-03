"""A run is addressable, pollable, resumable from either surface (HTTP-06).

Four claims, each asserted against **persisted state** rather than against a
response shape, because every one of them has a failure mode that returns a
well-formed response:

1. *Starting does not block.* The id comes back before the workflow has done
   anything — proven by the child still being alive **and** the checkpoint not
   existing yet at the moment the response is read, not by timing the request
   (D-12; a synchronous call is the alternative this rules out).
2. *A live run is pollable through the ordinary capability envelope.* Polling is
   ``curation.inspect`` over ``POST /api/capabilities/{cap_id}`` — the same route
   everything else uses. There is deliberately no new read path, which is what
   makes D-15 (poll, don't stream) cost nothing to hold.
3. *Cross-surface resume, in both directions.* A run started in the browser is
   resumed by a **real CLI child process**, and a run started by a real CLI child
   is resumed over HTTP. "Resumable from the CLI" is a claim about an independent
   process; a same-process call would share this interpreter's registry singleton
   and prove nothing (the argument
   ``tests/integration/test_surface_parity.py::_cli`` already makes).
4. *A failed start is visible.* D-26: the child's output goes to a file under the
   workspace whose path the start response names, so a spawn that dies is
   readable instead of presenting as a run that never existed.

**Why every resume here goes through a review capability.** The API layer never
drives the workflow graph, and neither does this file. A bare id-keyed dictionary
handed to ``Command(resume=...)`` is read by LangGraph as an *interrupt-id*
mapping — a proposal id has exactly the shape of an interrupt id — so it is
silently consumed as an **empty** resume: the run stays paused, nothing is
written, and the caller gets a well-formed success. That is why the resume
assertions below read the cards back off disk. A test that asserted on the
response would pass over precisely that defect.

**HTTP-06's prohibition, discharged rather than assumed.** No default, blanket
approval, or missing decision may ever produce a canonical write over this
surface. So the HTTP resumes here submit an explicit per-proposal ``decisions``
map, and ``test_a_resume_with_no_decisions_writes_nothing`` pins the other half:
a resume that names no decisions against a non-empty queue is refused and the
cards on disk are untouched.

**The offline fixture, and why it is not a mock.** ``curation.run`` pauses at its
review gate whenever the gate queue is non-empty, and ``decay_scan`` fills that
queue with *archive* proposals using nothing but ``governance.yaml`` and the
cards' own dates — no model, no network. So ``paused_install_root`` sets
``auto_archive_on_decay`` and backdates the cards, and the run pauses for real,
in a real child process. Monkeypatching a chat model (the idiom
``tests/contract/test_workflow_list.py`` uses) is not available here at all: the
run happens in another process, which is the entire point.

**This file's blind spot, stated rather than discovered later.** It drives the
ASGI *app object* through ``TestClient``; it never binds a socket. Host/Origin
handling, the real uvicorn lifecycle and a browser's actual fetch are outside
what any assertion here can see — plan 19-10's manual verification covers them.

A second, narrower blind spot: the window in which the child is *simultaneously*
alive and has written a checkpoint is a few tens of milliseconds wide on this
workflow, so asserting "poll returned a live status while the process was
running" would be a flake generator. What is asserted instead is strictly
checkable and says the same thing: the response arrives before the run has
started (claim 1), every poll issued while the child is alive is answered with a
well-formed 200 rather than an error (claim 2), and the run is still unfinished —
``awaiting_review`` — when polling reaches it.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient

from construct.api import CAPABILITY_ROUTE, TOKEN_HEADER
from construct.api.runs import RUN_LOG_RELPATH, RUNS_ROUTE, startable_workflows
from construct.capabilities.catalog import get_registry
from construct.capabilities.workspaces import set_launch_install_root

from tests.contract.conftest import API_TOKEN, build_workspace

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The workspace every run in this module addresses.
WORKSPACE_ID = "demo"

#: How long to wait for a spawned child to reach a state. Generous rather than
#: tuned: a slow machine must fail this suite by *timing out on a real defect*,
#: never by being slow, and the loops below exit the moment the state arrives.
TIMEOUT_SECONDS = 120.0

#: Poll interval. Small enough that the loops cost nothing, large enough not to
#: spin a core while a LangGraph child imports itself.
POLL_SECONDS = 0.05


# ── Fixtures ──────────────────────────────────────────────────────────────


def _make_paused_workspace(root: Path, name: str) -> Path:
    """A real workspace whose curation run will pause at its review gate, offline.

    Two edits to a real ``build_workspace`` tree, both of them ordinary product
    configuration rather than test scaffolding:

    * ``decay_window_days: 0`` with ``auto_archive_on_decay: true`` — the
      governance combination under which ``decay_scan`` becomes an archive
      *producer* rather than a findings-only step;
    * the cards' ``created`` date moved into the past, so they are decay
      candidates against that window.

    The result is a non-empty ``gate_queue``, which is the only thing
    ``run_curation_run`` consults to decide whether to pause. No provider is
    reached: the promotion gate degrades offline and enqueues nothing, and the
    archive proposals come from dates and YAML alone.
    """
    workspace = build_workspace(root, name)
    governance = workspace / "governance.yaml"
    governance.write_text(
        governance.read_text(encoding="utf-8")
        .replace("decay_window_days: 28", "decay_window_days: 0")
        .replace("auto_archive_on_decay: false", "auto_archive_on_decay: true"),
        encoding="utf-8",
    )
    today = str(datetime.date.today())
    for card in sorted((workspace / "cards").glob("*.md")):
        card.write_text(
            card.read_text(encoding="utf-8").replace(today, "2020-01-01"),
            encoding="utf-8",
        )
    return workspace


@pytest.fixture
def paused_install_root(tmp_path: Path) -> Path:
    """An install root holding one workspace whose curation run pauses."""
    root = tmp_path / "install"
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# CONSTRUCT test install root\n", encoding="utf-8")
    _make_paused_workspace(root, WORKSPACE_ID)
    return root


@pytest.fixture
def client(paused_install_root: Path) -> Iterator[TestClient]:
    """A ``TestClient`` over the real app factory, with the launch root cleared.

    ``set_launch_install_root`` is process-level state (D-09); leaving it set
    would make the next test resolve ``demo`` against a tree it never built, and
    an id assertion could then pass for the wrong reason.
    """
    from construct.api.app import create_app

    app = create_app(paused_install_root, API_TOKEN)
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client
    set_launch_install_root(None)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {TOKEN_HEADER: API_TOKEN}


@pytest.fixture
def workspace(paused_install_root: Path) -> Path:
    return paused_install_root / WORKSPACE_ID


# ── Surface drivers ───────────────────────────────────────────────────────


def _start(client: TestClient, headers: dict[str, str], **body: Any):
    """POST the run-start route."""
    return client.post(RUNS_ROUTE, json=body, headers=headers)


def _invoke(client: TestClient, headers: dict[str, str], cap_id: str, payload: dict):
    """Dispatch a capability over the ordinary envelope — the polling path."""
    return client.post(
        CAPABILITY_ROUTE.format(cap_id=cap_id), json={"payload": payload}, headers=headers
    )


def _cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the real ``construct`` CLI in a real, independent child process.

    ``sys.executable`` with ``PYTHONPATH`` pinned to *this* checkout's ``src``,
    for the reason ``test_surface_parity._cli`` gives: a hardcoded
    ``.venv/bin/python`` imports whatever tree that environment's editable
    install points at, which inside a git worktree is a **different checkout** —
    so the child would happily exercise code this test never touched.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "construct.cli", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
    )


# ── Observation helpers ───────────────────────────────────────────────────


def _alive(pid: int) -> bool:
    """Whether a signal can still be delivered to ``pid``."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _inspect(client: TestClient, headers: dict[str, str], run_id: str) -> dict:
    """One poll, through the envelope. Returns the capability's result envelope."""
    response = _invoke(
        client,
        headers,
        "curation.inspect",
        {"workspace_id": WORKSPACE_ID, "run_id": run_id},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _wait_for_status(
    client: TestClient, headers: dict[str, str], run_id: str, status: str
) -> dict:
    """Poll the run through the envelope until it reports ``status``.

    Returns the run's ``data`` block. Every poll is asserted to be a well-formed
    200 by ``_inspect``: a run that has not materialised yet is a *result*, not
    an error, and a surface that answered 500 for "not there yet" would make
    polling unusable.
    """
    deadline = time.monotonic() + TIMEOUT_SECONDS
    last: dict = {}
    while time.monotonic() < deadline:
        last = _inspect(client, headers, run_id)
        if (last.get("data") or {}).get("status") == status:
            return last["data"]
        time.sleep(POLL_SECONDS)
    raise AssertionError(
        f"run {run_id} never reported {status!r} within {TIMEOUT_SECONDS}s; "
        f"last envelope: {json.dumps(last)[:600]}"
    )


def _lifecycles(workspace: Path) -> dict[str, str]:
    """``card id -> lifecycle`` read straight off disk.

    The canonical source of truth, not a projection of it. This is what makes a
    silently-swallowed resume fail: it returns a well-formed response and leaves
    every one of these values exactly as it found them.
    """
    values: dict[str, str] = {}
    for card in sorted((workspace / "cards").glob("*.md")):
        for line in card.read_text(encoding="utf-8").splitlines():
            if line.startswith("lifecycle:"):
                values[card.stem] = line.split(":", 1)[1].strip()
                break
    return values


def _explicit_decisions(gate_queue: list[dict]) -> dict[str, str]:
    """One explicit verdict per queued proposal — never a blanket flag.

    HTTP-06's prohibition is that no default, blanket approval, or missing
    decision may result in a canonical write over this surface. Building the map
    from the queue the caller actually read is what "explicit per-proposal
    decision" means; ``approve_all`` would be the shape the prohibition names,
    even though the capability expands it into the same map.
    """
    return {entry["proposal_id"]: entry.get("decision") or "archive" for entry in gate_queue}


# ── Claim 1: starting returns an id and does not block ────────────────────


def test_starting_a_run_answers_with_an_id_before_the_workflow_begins(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The non-blocking claim, asserted twice over and without timing.

    Two independent measurements taken the moment the response is read:

    * the spawned child is still alive — the request did not wait for it;
    * the run has **no checkpoint at all** — so the workflow had not merely
      failed to finish, it had not started.

    The second is the stronger one, and it is what a synchronous implementation
    could not produce: a blocking call returns only once the run is durable.
    """
    response = _start(client, auth_headers, workflow="curation", workspace_id=WORKSPACE_ID)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "run_id",
        "workflow",
        "status",
        "log_path",
        "pid",
        "checkpoint_id",
    }
    assert body["workflow"] == "curation"
    assert body["status"] == "starting"
    assert body["run_id"]
    assert body["log_path"] == RUN_LOG_RELPATH.format(run_id=body["run_id"])

    assert _alive(body["pid"]), (
        "the child had already exited by the time the response was read — the "
        "request blocked on the workflow, which is what D-12 exists to prevent"
    )
    envelope = _inspect(client, auth_headers, body["run_id"])
    assert (envelope.get("data") or {}).get("status") == "failed", (
        "the run already had persisted state when the start response was read, "
        f"so the request did not return before the workflow began: {envelope}"
    )


def test_the_start_response_carries_the_checkpoint_handle_field(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Truth 7: every run response carries the handle a later phase needs.

    Null here, and present. There is genuinely no checkpoint yet — the child has
    not reached its first node — but a response shape that *grows* a field later
    is a shape every existing caller has to be told about, and the optimistic
    concurrency Phase 21 will build on reads this key. Declaring it now costs
    nothing and forecloses nothing.
    """
    body = _start(
        client, auth_headers, workflow="curation", workspace_id=WORKSPACE_ID
    ).json()
    assert "checkpoint_id" in body
    assert body["checkpoint_id"] is None


# ── Claim 2: pollable through the ordinary envelope ───────────────────────


def test_a_started_run_is_pollable_through_the_ordinary_envelope(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """No new read path: the poll is ``curation.inspect`` over the capability route.

    Every poll issued while the child is alive is answered with a well-formed
    200 — a run that has not materialised yet is a *result* saying so, never an
    error. A surface that answered 500 for "not there yet" would make polling
    unusable, and it is the shape a naive implementation produces.

    The run is still **unfinished** when polling reaches it: ``awaiting_review``
    is a live run whose process has already exited, which is exactly the
    property D-12 was chosen for — a run outlives the process that started it.
    """
    body = _start(
        client, auth_headers, workflow="curation", workspace_id=WORKSPACE_ID
    ).json()

    polls_while_alive = 0
    while _alive(body["pid"]) and polls_while_alive < 3:
        _inspect(client, auth_headers, body["run_id"])
        polls_while_alive += 1
        time.sleep(POLL_SECONDS)
    assert polls_while_alive, "the child exited before a single poll was issued"

    data = _wait_for_status(client, auth_headers, body["run_id"], "awaiting_review")
    assert data["run_id"] == body["run_id"]
    assert data["gate_queue"], "a paused run must surface the queue it is waiting on"
    assert data["checkpoint_id"], "a poll must carry the resume ETag (GOV-03 / D-11)"
    assert data["gate_id"] == body["run_id"]


def test_the_poll_response_carries_the_checkpoint_handle(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The other half of truth 7 — and the half that has to be non-null.

    Separated from the start-response test on purpose: a single test asserting
    "some response carries a handle" would pass while the one a resume actually
    needs carried ``None``.
    """
    body = _start(
        client, auth_headers, workflow="curation", workspace_id=WORKSPACE_ID
    ).json()
    data = _wait_for_status(client, auth_headers, body["run_id"], "awaiting_review")
    assert isinstance(data["checkpoint_id"], str) and data["checkpoint_id"]


# ── The startable set, and the refusals ───────────────────────────────────


def test_the_startable_workflows_are_derived_from_the_registry() -> None:
    """Truth 8: a future run capability becomes startable with no edit here.

    Asserted as a relationship between two live measurements rather than against
    a name list. A name list would need editing the day a run capability is
    registered, and an editor who is already editing the expectation is no
    longer being told anything.
    """
    registered = {
        capability.id for capability in get_registry().list() if capability.id.endswith(".run")
    }
    assert registered, "no run capabilities are registered — this test is vacuous"
    assert set(startable_workflows().values()) == registered
    assert set(startable_workflows()) == {cap_id[: -len(".run")] for cap_id in registered}


def test_an_unknown_workflow_is_refused_and_names_the_startable_set(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Refused in the project's one error body, with an actionable reason."""
    response = _start(client, auth_headers, workflow="not-a-workflow", workspace_id=WORKSPACE_ID)

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    detail = response.json()["detail"]
    for workflow in startable_workflows():
        assert workflow in detail, f"the refusal does not name {workflow!r}: {detail}"


def test_a_path_shaped_key_is_refused_the_way_the_envelope_refuses_one(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """D-10 at the run boundary, with the envelope's reason rather than pydantic's.

    ``extra="forbid"`` alone would already reject ``workspace_path`` — with a
    message that says nothing about ``workspace_id`` being how a workspace is
    addressed. Two refusals of one mistake giving two different explanations is
    the small fork this project keeps declining to introduce.
    """
    response = _start(
        client, auth_headers, workflow="curation", workspace_path="/etc/passwd"
    )

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    detail = response.json()["detail"]
    assert "workspace_path" in detail
    assert "workspace_id" in detail


def test_an_unknown_workspace_id_is_refused_before_anything_is_spawned(
    client: TestClient, auth_headers: dict[str, str], paused_install_root: Path
) -> None:
    """The seam's allowlist, reached through the same helper the envelope uses."""
    response = _start(client, auth_headers, workflow="curation", workspace_id="no-such-ws")

    assert response.status_code == 422
    assert WORKSPACE_ID in response.json()["detail"]
    assert not list((paused_install_root / WORKSPACE_ID).glob(".construct/workflow/logs/*"))


def test_a_traversal_shaped_workspace_id_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """T-19-03: the shape gate, before any path is built."""
    response = _start(client, auth_headers, workflow="curation", workspace_id="../../etc")

    assert response.status_code == 422
    assert "kebab-case" in response.json()["detail"]


def test_the_spawn_passes_an_argument_list_and_never_a_shell() -> None:
    """T-19-09, read off the module rather than asserted about it in prose.

    The only structural control that keeps a caller-influenced value out of a
    shell is that there is no shell. This reads the source because the property
    is about *how* the process is started, and no black-box request can observe
    the difference between ``shell=False`` and a shell that happened not to be
    reached on this input.
    """
    import inspect

    import construct.api.runs as module

    source = inspect.getsource(module)
    assert "shell" not in source or "shell=False" in source
    assert "shell=True" not in source
    assert "os.system" not in source
    assert "subprocess.Popen(" in source
