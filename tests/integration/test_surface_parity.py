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

import pytest

from construct.capabilities.catalog import get_registry
from construct.mcp import server as mcp_server
from construct.mcp.server import create_server

REPO_ROOT = Path(__file__).resolve().parents[2]

# (capability_id, mcp_tool_name, payload builder, CLI argv builder)
PARITY_CASES: list[tuple[str, str, Callable[[Path], dict], Callable[[Path], list[str]]]] = [
    (
        "knowledge.card.list",
        "construct_list_cards",
        lambda ws: {"workspace": str(ws)},
        lambda ws: ["knowledge", "card", "list", "--workspace", str(ws), "--json"],
    ),
]

_CASE_IDS = [case[0] for case in PARITY_CASES]


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


def _card_workspace(tmp_path: Path) -> Path:
    """A scaffolded workspace holding two cards, built through the real services."""
    from construct.services.init import DomainInitInput, initialize_workspace
    from construct.services.knowledge import create_card

    ws = tmp_path / "workspace"
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


@pytest.mark.parametrize(
    ("cap_id", "tool_name", "build_payload", "build_argv"), PARITY_CASES, ids=_CASE_IDS
)
def test_success_parity_verdict_message_and_records(
    tmp_path: Path,
    cap_id: str,
    tool_name: str,
    build_payload: Callable[[Path], dict],
    build_argv: Callable[[Path], list[str]],
) -> None:
    """One payload, two real surfaces, one answer: same verdict, same message,
    same record key set."""
    ws = _card_workspace(tmp_path)

    cli = _cli(build_argv(ws))
    assert cli.returncode == 0, cli.stderr or cli.stdout
    cli_payload = json.loads(cli.stdout)

    mcp_payload = _mcp(tool_name, build_payload(ws))

    assert cli_payload["success"] == mcp_payload["success"] is True
    assert cli_payload["message"] == mcp_payload["message"]

    assert cli_payload["data"], "fixture produced no records to compare"
    assert len(cli_payload["data"]) == len(mcp_payload["data"])
    for cli_record, mcp_record in zip(cli_payload["data"], mcp_payload["data"]):
        assert set(cli_record.keys()) == set(mcp_record.keys())


# ── The MCP surface stays registry-generated ──────────────────────────────


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
