"""Differential CLI-process vs MCP-dispatch parity harness (GOV-01, D-08).

Two surfaces reached the same capability handlers by two different, independently
written paths, and nothing asserted they agreed. ``input_model`` was computed into
a JSON Schema for MCP discovery and then thrown away, so ``CardListInput``'s
``extra="forbid()"`` never ran against a real payload (WR-02). GOV-01 closes that
by routing both surfaces through one validating seam, ``CapabilityRegistry.invoke``.

This harness is the proof. It drives the two surfaces *as they actually run* and
asserts they agree — rather than testing the seam once and assuming both callers
reach it.

Wave 1 status: the case table is seeded with a single row. Plan 03 converts the
remaining call sites and adds rows; the table is the extension point, so growing
coverage never means growing this file's logic.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from fastapi.testclient import TestClient

from construct.api import CAPABILITY_ROUTE
from construct.capabilities.catalog import get_registry
from construct.mcp import server as mcp_server
from construct.mcp.server import create_server

REPO_ROOT = Path(__file__).resolve().parents[2]


class ParityCase(NamedTuple):
    """One capability, described well enough to drive both real surfaces.

    ``build_env`` takes a *private* directory and returns the environment root the
    other two builders address. It is called once per arm, so each surface gets an
    identical but independent tree — which is what lets a **write** capability into
    the table at all. Sharing one tree would have the second arm collide with the
    first arm's write, and comparing "created" against "already exists" proves
    nothing about parity.

    ``read`` projects a surface's raw output onto the value being compared.
    Capabilities whose CLI prints ``_display_result``'s envelope share
    ``_envelope_view``; ``views validate`` prints its own report shape and brings
    its own reader. The projection lives in the row so the test body stays one
    equality assertion — adding a capability is a row, never new test logic.

    **The HTTP arm needs its own payload, not a reuse of ``build_payload``.**
    That is not an inconsistency to be smoothed over: the HTTP boundary refuses
    path-shaped keys outright (``PATH_SHAPED_KEYS``) and addresses a workspace by
    *id*, so the payload the other two arms send is one this surface is required
    to reject. ``build_http_payload`` therefore expresses the same request in the
    vocabulary HTTP actually speaks, and ``build_http_root`` names the install
    root the app is launched against — because an id is resolved against launch
    context (D-09) rather than carried in the request.
    """

    cap_id: str
    tool_name: str
    build_env: Callable[[Path], Path]
    build_payload: Callable[[Path], dict]
    build_argv: Callable[[Path], list[str]]
    read_cli: Callable[[str], object]
    read_mcp: Callable[[dict], object]
    build_http_root: Callable[[Path], Path]
    build_http_payload: Callable[[Path], dict]
    read_http: Callable[[dict], object]


def _envelope_view(payload: dict) -> dict:
    """The comparable core of an ``OperationResult`` rendered as JSON."""
    return {
        "success": payload["success"],
        "message": payload["message"],
        "errors": payload["errors"],
        "data": payload["data"],
    }


def _envelope_from_cli(stdout: str) -> dict:
    return _envelope_view(json.loads(stdout))


def _views_report(results: list[dict], all_passed: bool) -> dict:
    """The per-file verdict table, keyed by file so ordering is not the assertion."""
    return {
        "all_passed": all_passed,
        "files": {entry["file"]: entry["status"] for entry in results},
    }


def _views_view_from_cli(stdout: str) -> dict:
    payload = json.loads(stdout)
    return _views_report(payload["results"], payload["all_passed"])


def _views_view_from_mcp(payload: dict) -> dict:
    data = payload["data"]
    return _views_report(data["results"], data["all_passed"])


PARITY_CASES: list[ParityCase] = [
    # A read.
    ParityCase(
        cap_id="knowledge.card.list",
        tool_name="construct_list_cards",
        build_env=lambda root: _card_workspace(root),
        build_payload=lambda ws: {"workspace": str(ws)},
        build_argv=lambda ws: [
            "knowledge", "card", "list", "--workspace", str(ws), "--json",
        ],
        read_cli=_envelope_from_cli,
        read_mcp=_envelope_view,
        build_http_root=lambda ws: ws.parent,
        build_http_payload=lambda ws: {"workspace_id": ws.name},
        read_http=_envelope_view,
    ),
    # A write. D-08 permits trading fixture cost for breadth, and a table proving
    # only reads agree would leave the capabilities that *change* the workspace —
    # the ones where a surface fork actually costs the user something — unproven.
    ParityCase(
        cap_id="knowledge.card.create",
        tool_name="construct_create_card",
        build_env=lambda root: _card_workspace(root),
        build_payload=lambda ws: {
            "workspace": str(ws),
            "title": "Parity Card",
            "epistemic_type": "finding",
            "domains": ["test-domain"],
            "content_categories": ["test-category"],
            "confidence": 3,
            "source_tier": 3,
            "author": "construct",
            "summary": "Written through both surfaces to prove they agree.",
        },
        build_argv=lambda ws: [
            "knowledge", "card", "create",
            "--title", "Parity Card",
            "--type", "finding",
            "--domains", "test-domain",
            "--categories", "test-category",
            "--confidence", "3",
            "--source-tier", "3",
            "--author", "construct",
            "--summary", "Written through both surfaces to prove they agree.",
            "--workspace", str(ws),
            "--json",
        ],
        read_cli=_envelope_from_cli,
        read_mcp=_envelope_view,
        build_http_root=lambda ws: ws.parent,
        build_http_payload=lambda ws: {
            "workspace_id": ws.name,
            "title": "Parity Card",
            "epistemic_type": "finding",
            "domains": ["test-domain"],
            "content_categories": ["test-category"],
            "confidence": 3,
            "source_tier": 3,
            "author": "construct",
            "summary": "Written through both surfaces to prove they agree.",
        },
        read_http=_envelope_view,
    ),
    # The views capability D-02 registers in this plan.
    ParityCase(
        cap_id="views.validate_data",
        tool_name="construct_views_validate_data",
        build_env=lambda root: _generated_install_root(root),
        build_payload=lambda root: {"install_root": str(root)},
        build_argv=lambda root: [
            "views", "validate", "--install-root", str(root), "--json",
        ],
        read_cli=_views_view_from_cli,
        read_mcp=_views_view_from_mcp,
        # An install-root capability: the root is launch context, never caller
        # input, so the HTTP payload is empty and ``workspace_id`` is refused
        # outright (``INSTALL_ROOT_FIELD``). The empty payload here is the same
        # shape ``test_only_install_root_capabilities_run_on_an_empty_payload``
        # pins in the contract suite.
        build_http_root=lambda root: root,
        build_http_payload=lambda root: {},
        read_http=_views_view_from_mcp,
    ),
]

_CASE_IDS = [case.cap_id for case in PARITY_CASES]


# ── Surface drivers ───────────────────────────────────────────────────────


def _cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the real ``construct`` CLI in a real child process.

    ``typer.testing.CliRunner`` would share this pytest process, and with it the
    registry singleton cached in a module global (``catalog.py`` ``get_registry``).
    A shared registry cannot prove that an independently started process reaches
    the same verdict, which is the entire claim of a differential harness
    (RESEARCH Pitfall 5). It also cannot produce a real exit code.

    ``sys.executable`` is the interpreter running this suite, and ``PYTHONPATH``
    pins the child to *this* checkout's ``src``. A hardcoded ``.venv/bin/python``
    would import whatever tree that environment's editable install points at —
    inside a git worktree that is a different checkout, so the child would happily
    test code this test never touched.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "construct.cli", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )


def _mcp(tool_name: str, payload: dict) -> dict:
    """Invoke the closure ``create_server()`` actually registered with FastMCP.

    Calling ``cap.handler`` directly would skip the very wiring under test — the
    handler is reached through ``make_handler``'s closure, and that closure is
    where dispatch goes through the seam.
    """
    tool = create_server()._tool_manager.get_tool(tool_name)
    return json.loads(tool.fn(**payload))


def _http(cap_id: str, install_root: Path, payload: dict) -> tuple[int, dict]:
    """Drive the real ASGI app through a ``TestClient``, as a browser would.

    Built through ``create_app`` — the same factory ``construct serve`` hands
    uvicorn — so the request crosses the real middleware guard and the real
    dispatch route rather than calling a handler directly. The token and a
    loopback ``base_url`` are what make this a *passing* request; the guard's
    rejection paths are pinned in ``tests/contract/test_http_security.py``.

    ``set_launch_install_root`` is process-level state (D-09), so it is cleared
    on the way out: leaving it set would make the next arm resolve ids against
    a tree this test built, and an id assertion could then pass for the wrong
    reason.
    """
    from construct.api import TOKEN_HEADER
    from construct.api.app import create_app
    from construct.capabilities.workspaces import set_launch_install_root

    token = "parity-token-not-a-real-secret"
    app = create_app(install_root, token)
    try:
        with TestClient(app, base_url="http://127.0.0.1") as client:
            response = client.post(
                CAPABILITY_ROUTE.format(cap_id=cap_id),
                json={"payload": payload},
                headers={TOKEN_HEADER: token},
            )
        return response.status_code, response.json()
    finally:
        set_launch_install_root(None)


def _http_reason(body: dict) -> str:
    """The seam's reason with the HTTP surface's own framing stripped.

    Task 1 made every emitter on this surface return exactly ``{"detail": str}``
    (``api/errors.py``), and the capability-error arm puts ``str(exc)`` in it
    verbatim — the same string the CLI prints after ``ERROR `` and MCP returns
    as ``{"error": ...}``. So "strip the framing" is one key lookup, and the
    fact that it *is* only a key lookup is itself the HTTP-04 claim.
    """
    assert "detail" in body, f"expected the one error body, got: {body!r}"
    return body["detail"]


def _seam_in_fresh_process(cap_id: str, payload: dict) -> subprocess.CompletedProcess[str]:
    """Drive the seam directly in a real, freshly started process.

    Why this exists rather than a ``construct ... --bogus 1`` invocation: Typer's
    own option parser rejects an undeclared *flag* before the payload is ever
    built, so the real CLI cannot express a payload carrying an undeclared field.
    That is a genuine property of the CLI surface, pinned by
    ``test_cli_process_rejects_an_undeclared_flag_without_a_traceback`` below —
    not something to paper over.

    So seam-level reason parity is proven where it is actually decidable: the same
    payload crossing the same seam in an independent process versus through MCP
    dispatch. Rendering matches the CLI's real convention exactly
    (``typer.echo(f"ERROR {exc}")`` then exit 1), so "strip the CLI's framing"
    means the same thing here as it does in ``cli.py``.
    """
    script = (
        "import json, sys\n"
        "from construct.capabilities.catalog import get_registry\n"
        "from construct.capabilities.errors import CapabilityError\n"
        "cap_id, payload = json.loads(sys.argv[1])\n"
        "try:\n"
        "    result = get_registry().invoke(cap_id, payload)\n"
        "except CapabilityError as exc:\n"
        "    print(f'ERROR {exc}')\n"
        "    sys.exit(1)\n"
        "print(f'OK {result.success}')\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-c", script, json.dumps([cap_id, payload])],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )


def _cli_reason(completed: subprocess.CompletedProcess[str]) -> str:
    """The seam's reason with the CLI surface's own framing stripped."""
    text = (completed.stdout + completed.stderr).strip()
    assert text.startswith("ERROR "), f"unexpected CLI-side rendering: {text!r}"
    return text[len("ERROR ") :].strip()


def _mcp_reason(payload: dict) -> str:
    """The seam's reason with the MCP surface's own framing stripped."""
    assert "error" in payload, f"expected an error value, got: {payload!r}"
    return payload["error"]


def _generated_install_root(tmp_path: Path) -> Path:
    """A real CONSTRUCT install root carrying a real ``views/build/data/`` tree.

    Built by running the actual generator rather than by writing fixture JSON, so
    ``views validate`` is checked against bytes ``views generate`` really emits —
    the round-trip property VFIX-01 turns on. The ``AGENTS.md`` marker is what
    makes this a CONSTRUCT installation as far as ``install_root_error`` is
    concerned; without it the capability refuses the path before reading anything.
    """
    from construct.views.generate import generate

    root = tmp_path / "install"
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# CONSTRUCT parity install root\n", encoding="utf-8")

    _card_workspace(root, name="demo")

    report = generate(root)
    assert report.total_files_written, "the parity fixture generated no view data"
    return root


def _card_workspace(tmp_path: Path, name: str = "workspace") -> Path:
    """A scaffolded workspace holding two cards, built through the real services."""
    from construct.services.init import DomainInitInput, initialize_workspace
    from construct.services.knowledge import create_card

    ws = tmp_path / name
    initialize_workspace(
        ws,
        DomainInitInput(
            domain_id="test-domain",
            display_name="Test Domain",
            scope="A test domain for surface-parity tests.",
            taxonomy_seeds=["test-category"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["test research"],
        ),
    )
    for card_id, title in (("card-a", "Card A"), ("card-b", "Card B")):
        create_card(
            ws,
            {
                "id": card_id,
                "title": title,
                "epistemic_type": "finding",
                "domains": ["test-domain"],
                "content_categories": ["test-category"],
                "confidence": 3,
                "source_tier": 3,
            },
        )
    return ws


# ── The seam exists and carries the cross-phase signature ─────────────────


def test_seam_exists_with_the_cross_phase_signature() -> None:
    """Phase 19's generated HTTP adapter routes through this exact signature, so
    its shape is a cross-phase contract, not an implementation detail."""
    import inspect

    from construct.capabilities.registry import CapabilityRegistry

    signature = inspect.signature(CapabilityRegistry.invoke)
    assert list(signature.parameters) == ["self", "cap_id", "payload"]
    assert signature.return_annotation is not inspect.Signature.empty


def test_seam_has_no_leniency_knob() -> None:
    """D-05: a strict/lenient flag would let one surface diverge from another —
    the precise fork this seam exists to close. Its absence is load-bearing."""
    import inspect

    from construct.capabilities.registry import CapabilityRegistry

    parameters = set(inspect.signature(CapabilityRegistry.invoke).parameters)
    assert parameters == {"self", "cap_id", "payload"}


# ── Success parity across the two real surfaces ───────────────────────────


@pytest.mark.parametrize("case", PARITY_CASES, ids=_CASE_IDS)
def test_success_parity_across_all_three_real_surfaces(
    tmp_path: Path, case: ParityCase
) -> None:
    """One request, three real surfaces, one answer.

    Each arm gets its own identical environment, so a write capability is
    comparable: every surface acts on a fresh tree and must produce the same
    verdict, the same message, and the same data — not "one created it and the
    other found it already there".

    The HTTP arm addresses its workspace by id rather than by path, which is the
    whole point rather than a concession: if id resolution and path resolution
    could disagree, this is where it would show, because the projected answer
    would differ from the two arms that resolved a path.
    """
    cli_env = case.build_env(tmp_path / "cli-arm")
    mcp_env = case.build_env(tmp_path / "mcp-arm")
    http_env = case.build_env(tmp_path / "http-arm")

    cli = _cli(case.build_argv(cli_env))
    assert cli.returncode == 0, cli.stderr or cli.stdout

    mcp_payload = _mcp(case.tool_name, case.build_payload(mcp_env))

    status, http_body = _http(
        case.cap_id, case.build_http_root(http_env), case.build_http_payload(http_env)
    )
    assert status == 200, f"{case.cap_id} failed over HTTP: {status} {http_body!r}"

    cli_view = case.read_cli(cli.stdout)
    mcp_view = case.read_mcp(mcp_payload)
    http_view = case.read_http(http_body)

    assert cli_view == mcp_view, (
        f"{case.cap_id} answered differently on CLI vs MCP:\n"
        f"  CLI: {cli_view!r}\n  MCP: {mcp_view!r}"
    )
    assert cli_view == http_view, (
        f"{case.cap_id} answered differently on CLI vs HTTP:\n"
        f"  CLI: {cli_view!r}\n  HTTP: {http_view!r}"
    )
    assert cli_view, f"{case.cap_id} compared an empty projection — the assertion is vacuous"


@pytest.mark.parametrize("case", PARITY_CASES, ids=_CASE_IDS)
def test_undeclared_field_is_rejected_identically_on_both_surfaces(
    tmp_path: Path, case: ParityCase
) -> None:
    """The rejection contract, widened from one capability to the whole table.

    Plan 01 proved this on ``knowledge.card.list``. A contract proven on one
    capability is a contract proven on one capability — every row here is a
    payload an agent can send, and each must be refused with the same words
    whichever surface it arrives on.
    """
    env = case.build_env(tmp_path / "env")
    payload = {**case.build_payload(env), "bogus": 1}

    seam = _seam_in_fresh_process(case.cap_id, payload)
    assert seam.returncode != 0, seam.stdout

    mcp_payload = _mcp(case.tool_name, payload)

    assert _cli_reason(seam) == _mcp_reason(mcp_payload)
    assert "bogus" in _mcp_reason(mcp_payload)


def test_the_parity_table_covers_a_read_a_write_and_a_views_capability() -> None:
    """D-08's breadth requirement, asserted so it cannot silently narrow.

    Deliberately *not* an inventory check against the registry: that would prove a
    capability is listed and never that two surfaces behave the same. This asserts
    only that the differential table above — every row of which drives a real CLI
    process against real MCP dispatch — spans the three kinds.
    """
    covered = {case.cap_id for case in PARITY_CASES}

    assert {
        "knowledge.card.list",       # read
        "knowledge.card.create",     # write
        "views.validate_data",       # views
    } <= covered
    assert len(PARITY_CASES) >= 3


# ── The MCP surface stays registry-generated ──────────────────────────────


def _corrupt_one_data_file(root: Path) -> str:
    """Break exactly one generated data file so its contract model rejects it.

    A *populated* file rewritten to a shape its model forbids, rather than a
    deleted one: a missing file reports ``missing`` and never reaches the
    per-file error channel, which is the channel under test.
    """
    from construct.views.generate import BUILD_DATA_RELPATH

    data_dir = root / BUILD_DATA_RELPATH
    target = data_dir / "domains.json"
    assert target.is_file(), f"the parity fixture wrote no {target.name}"
    target.write_text(json.dumps({"domains": "not-a-list"}), encoding="utf-8")
    return str(target.relative_to(data_dir))


def test_failure_parity_puts_the_capability_s_errors_on_both_surfaces(
    tmp_path: Path,
) -> None:
    """CR-01: the failure case — the case GOV-01 is actually about — must agree too.

    Every row in ``PARITY_CASES`` compares a *successful* invocation, and the two
    rejection tests below compare failures raised by the seam *before* a handler
    runs. Neither reaches ``_serialize_result``, so nothing asserted that a
    capability which fails **with ``OperationResult.errors`` populated** renders
    its reasons over MCP at all.

    It did not. ``_serialize_result`` returned ``errors`` as a list of
    ``OperationError`` *dataclasses*; ``json.dumps`` then raised inside the
    handler's own ``try``, and every structured failure answered
    ``{"error": "Object of type OperationError is not JSON serializable"}`` —
    a bogus reason an agent cannot distinguish from an infrastructure fault.
    """
    cli_root = _generated_install_root(tmp_path / "cli-arm")
    mcp_root = _generated_install_root(tmp_path / "mcp-arm")
    broken = _corrupt_one_data_file(cli_root)
    assert _corrupt_one_data_file(mcp_root) == broken

    cli = _cli(["views", "validate", "--install-root", str(cli_root), "--json"])
    assert cli.returncode == 1, cli.stdout + cli.stderr

    mcp_payload = _mcp("construct_views_validate_data", {"install_root": str(mcp_root)})

    assert "error" not in mcp_payload, (
        "MCP answered with a surface-level error instead of the capability's "
        f"structured failure: {mcp_payload!r}"
    )
    assert mcp_payload["success"] is False

    # The per-file verdict tables agree.
    assert _views_view_from_cli(cli.stdout) == _views_view_from_mcp(mcp_payload)

    # And the reasons themselves cross the MCP boundary, field-by-field.
    cli_errors = {
        entry["file"]: entry["errors"]
        for entry in json.loads(cli.stdout)["results"]
        if entry["status"] == "fail"
    }
    mcp_errors = {err["field"]: err["reason"].split("; ") for err in mcp_payload["errors"]}
    assert cli_errors == mcp_errors
    assert broken in mcp_errors, f"the corrupted file is not in {mcp_errors!r}"


def test_mcp_server_names_no_capability() -> None:
    """Inserting the seam must not have bought parity with hand-wiring.

    ``mcp/server.py`` is 52 lines of registry-driven generation, and that is the
    structure Phase 19's HTTP adapter is generated from. If any capability id or
    tool name appears in its source, the generation claim is already false.
    """
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    registry = get_registry()
    for cap in registry.list():
        assert cap.id not in src, f"capability id leaked into mcp/server.py: {cap.id}"
        if cap.mcp_tool_name:
            assert cap.mcp_tool_name not in src, (
                f"tool name leaked into mcp/server.py: {cap.mcp_tool_name}"
            )


def test_mcp_dispatch_routes_through_the_seam() -> None:
    """The key link this plan asserts: MCP reaches handlers via ``invoke``, not
    via ``capability.handler``."""
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "invoke(" in src
    assert "capability.handler(" not in src


# ── The rejection contract: one reason, both dispatch paths ───────────────


def test_undeclared_field_reason_is_identical_across_dispatch_paths(tmp_path: Path) -> None:
    """The GOV-01 claim: one payload rejected for one reason, whichever surface asked.

    Before the seam, ``extra="forbid"`` was declared on ``CardListInput`` and never
    ran on a real MCP payload — the model was rendered to a JSON Schema for
    discovery and then discarded (WR-02). This is the assertion that it now runs.
    """
    ws = _card_workspace(tmp_path)
    payload = {"workspace": str(ws), "bogus": 1}

    cli = _seam_in_fresh_process("knowledge.card.list", payload)
    assert cli.returncode != 0, cli.stdout

    mcp_payload = _mcp("construct_list_cards", payload)

    assert _cli_reason(cli) == _mcp_reason(mcp_payload)
    assert "bogus" in _mcp_reason(mcp_payload)


def test_missing_required_field_reason_is_identical_across_dispatch_paths() -> None:
    """The empty-payload edge: one reason naming the missing field, on both arms."""
    cli = _seam_in_fresh_process("knowledge.card.list", {})
    assert cli.returncode != 0, cli.stdout

    mcp_payload = _mcp("construct_list_cards", {})

    assert _cli_reason(cli) == _mcp_reason(mcp_payload)
    assert "workspace" in _mcp_reason(mcp_payload)


def test_cli_process_rejects_an_undeclared_flag_without_a_traceback(tmp_path: Path) -> None:
    """The CLI surface rejects undeclared input non-zero and legibly.

    Note *where* it is rejected: Typer's option parser refuses ``--bogus`` before a
    payload exists, so this message is Click's, not the seam's. The CLI surface
    therefore has two layers of defence and its payload is seam-valid by
    construction, while an MCP payload is caller-controlled and only the seam
    stands in front of the handler. That asymmetry is why WR-02 was an MCP defect.
    """
    ws = _card_workspace(tmp_path)
    cli = _cli(["knowledge", "card", "list", "--workspace", str(ws), "--bogus", "1"])

    assert cli.returncode != 0
    combined = cli.stdout + cli.stderr
    assert "bogus" in combined
    assert "Traceback" not in combined


def test_a_rejected_payload_never_reaches_the_handler() -> None:
    """Validation is a gate, not a report: the handler must not run at all."""
    from pydantic import BaseModel, ConfigDict

    from construct.capabilities.errors import CapabilityInputError
    from construct.capabilities.registry import CapabilityRecord, CapabilityRegistry

    class GatedInput(BaseModel):
        model_config = ConfigDict(extra="forbid")

        name: str

    calls: list[dict] = []

    def handler(name: str) -> dict:
        calls.append({"name": name})
        return {"name": name}

    registry = CapabilityRegistry()
    registry.register(
        CapabilityRecord(
            id="test.gated",
            name="Gated",
            description="A capability used to prove the seam gates its handler.",
            input_model=GatedInput,
            output_model=GatedInput,
            handler=handler,
        )
    )

    with pytest.raises(CapabilityInputError):
        registry.invoke("test.gated", {"name": "ok", "bogus": 1})

    assert calls == [], "the handler ran despite an invalid payload"


def test_exact_fit_payload_is_accepted_and_one_extra_key_flips_it(tmp_path: Path) -> None:
    """The GOV-01 adjacency edge: exactly the declared field set passes; that same
    payload plus one undeclared key is rejected on both arms."""
    ws = _card_workspace(tmp_path)
    model = get_registry().get("knowledge.card.list").input_model
    exact = {"workspace": str(ws), "domain": None, "include_archived": False}
    assert set(exact) == set(model.model_fields), "payload is no longer an exact fit"

    assert _mcp("construct_list_cards", exact)["success"] is True
    accepted = _seam_in_fresh_process("knowledge.card.list", exact)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr

    adjacent = {**exact, "bogus": 1}
    rejected = _seam_in_fresh_process("knowledge.card.list", adjacent)
    assert rejected.returncode != 0
    assert _cli_reason(rejected) == _mcp_reason(_mcp("construct_list_cards", adjacent))


def test_exact_fit_is_reachable_through_the_real_cli(tmp_path: Path) -> None:
    """The declared field set is expressible as real CLI flags — the accept half of
    the adjacency edge, proven on the actual surface rather than at the seam."""
    ws = _card_workspace(tmp_path)
    cli = _cli(
        ["knowledge", "card", "list", "--workspace", str(ws), "--include-archived", "--json"]
    )
    assert cli.returncode == 0, cli.stderr or cli.stdout
    assert json.loads(cli.stdout)["success"] is True


def test_all_optional_model_accepts_an_empty_payload_and_uses_its_defaults() -> None:
    """The other empty-payload edge: strictness must not mean "always requires input".

    No capability in the catalog has an all-optional model today, so the seam's
    behaviour on that shape is proven against a purpose-built record in a local
    registry rather than by asserting something untrue about the real catalog.
    """
    from pydantic import BaseModel, ConfigDict

    from construct.capabilities.registry import CapabilityRecord, CapabilityRegistry

    class AllOptionalInput(BaseModel):
        model_config = ConfigDict(extra="forbid")

        limit: int = 7
        label: str = "default-label"

    def handler(limit: int, label: str) -> dict:
        return {"limit": limit, "label": label}

    registry = CapabilityRegistry()
    registry.register(
        CapabilityRecord(
            id="test.all_optional",
            name="All Optional",
            description="A capability whose input model has no required field.",
            input_model=AllOptionalInput,
            output_model=AllOptionalInput,
            handler=handler,
        )
    )

    assert registry.invoke("test.all_optional", {}) == {
        "limit": 7,
        "label": "default-label",
    }


def test_unknown_capability_raises_the_seam_s_typed_error() -> None:
    """The seam's other failure mode, converted from ``get``'s ``KeyError`` so a
    surface renders one string rather than a bare key repr."""
    from construct.capabilities.errors import CapabilityNotFoundError

    with pytest.raises(CapabilityNotFoundError) as excinfo:
        get_registry().invoke("no.such.capability", {})

    assert "no.such.capability" in str(excinfo.value)


def test_seam_reason_does_not_echo_the_submitted_payload_values(tmp_path: Path) -> None:
    """T-18-10: the reason is rendered straight back to an MCP client, so it names
    fields and constraints — never the caller's submitted values."""
    secret = "s3cr3t-value-not-for-echo"
    reason = _mcp_reason(_mcp("construct_list_cards", {"workspace": secret, "bogus": secret}))

    assert secret not in reason
    assert "bogus" in reason


# ── A1: what MCP *advertises* is still not the model's schema ─────────────


def test_advertised_mcp_schema_is_not_yet_the_model_schema() -> None:
    """Records the measured limit of GOV-01 on this pinned FastMCP (assumption A1).

    ``FastMCP.add_tool`` exposes no input-schema override, so the advertised schema
    is inferred from ``make_handler``'s generic ``**kwargs`` signature and describes
    a single ``kwargs`` property. Enforcement is closed — the seam validates every
    payload — but *discovery* is not: a client reading the advertised schema cannot
    see the real field set.

    This test pins the gap so it cannot be quietly forgotten. When a FastMCP upgrade
    makes it fail, that is the signal to pass ``entry["input_schema"]`` through in
    ``create_server()`` and delete this test.
    """
    import inspect

    from mcp.server.fastmcp import FastMCP

    add_tool_params = set(inspect.signature(FastMCP.add_tool).parameters)
    assert not add_tool_params & {"input_schema", "inputSchema", "schema", "parameters"}

    advertised = create_server()._tool_manager.get_tool("construct_list_cards").parameters
    model_schema = get_registry().get("knowledge.card.list").input_model.model_json_schema()

    assert advertised != model_schema
    assert set(advertised["properties"]) == {"kwargs"}
    assert set(model_schema["properties"]) == {"workspace", "domain", "include_archived"}
