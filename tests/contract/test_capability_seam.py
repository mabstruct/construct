"""Permanent contract guards for the GOV-01 capability invocation seam (D-05, D-06).

Two layers live here.

**Layer 1 — forbid cardinality (D-06).** The number of registry input models that
reject undeclared fields must *equal* the registry size. A capability registered
without ``extra="forbid"`` fails this the moment it lands. The registry size is
asserted separately, as one explicit integer a future capability must deliberately
bump.

The shape is the point. ``tests/contract/test_mcp_contracts.py:53-80`` asserts a
hand-typed set of capability names; that is the WR-01 anti-pattern, because a
membership assertion proves a capability is *listed* and never that nothing was
*added* unguarded. This file therefore asserts a relationship between two live
measurements and contains no name set used as an equality assertion.

**Layer 2 — model-to-handler binding audit (D-05, research Finding G3).**
``CapabilityRegistry.invoke`` dispatches ``handler(**model.model_dump())``, so a
declared field that is not a handler parameter is a ``TypeError`` at call time
rather than a documentation nit. Five capabilities were in exactly that state and
nobody noticed: they are five of the six capabilities not exposed over MCP, so
their models had never been used to construct a call. That correlation is the
strongest argument for D-05's refusal of an allowlist — the allowlist would have
been exactly these five.

**Known blind spot, stated rather than implied.** A handler declaring ``**kwargs``
accepts any field name, so the signature audit cannot prove such a shim actually
*marshals* what it accepts. The seam-invocation tests at the bottom of this file
cover the repaired capabilities where the signature audit goes blind.
"""
from __future__ import annotations

import ast
import inspect
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from construct.capabilities import catalog
from construct.capabilities.catalog import CardArchiveInput, get_registry
from construct.capabilities.errors import CapabilityInputError

FIXTURE_WS = Path(__file__).resolve().parents[2] / "test-ws" / "my-construct"

# A deliberate tripwire (not a name set): adding a capability must be a conscious
# edit here, which is what forces the author past the two guards below.
#
# 28 -> 29 in plan 18-03: ``views.validate_data`` joins the registry (D-02), so
# ``views validate`` stops being the last hand-written command group and becomes
# reachable from CLI and MCP by the one path every other capability uses. Bumping
# this integer is the intended act, not a workaround for it.
REGISTRY_SIZE = 29


def _forbids(model: type) -> bool:
    """Whether a model's resolved config rejects undeclared fields."""
    return (model.model_config or {}).get("extra") == "forbid"


def _capability_ids() -> list[str]:
    """Every registered capability, audited unconditionally.

    There is deliberately no exemption set here. The five capabilities whose
    models did not describe their handlers were repaired rather than excused —
    an exemption list would have grown into exactly the allowlist D-05 refused.
    """
    return [capability.id for capability in get_registry().list()]


# ---------------------------------------------------------------------------
# Layer 1 — forbid cardinality (D-06)
# ---------------------------------------------------------------------------


def test_registry_size_is_the_declared_tripwire() -> None:
    """One explicit integer, asserted on its own.

    The cardinality guard below compares two live measurements, so it stays true
    if the registry shrinks to zero. This test is what makes that comparison
    meaningful: a capability added or removed must bump this number consciously.
    """
    assert len(get_registry().list()) == REGISTRY_SIZE


def test_every_capability_input_model_forbids_undeclared_fields() -> None:
    """D-06 as a relationship, never as a name set.

    A model that forbids nothing turns the seam into a pass-through: it would
    validate types and then hand the handler whatever else the caller sent.
    """
    capabilities = get_registry().list()
    forbidding = [c for c in capabilities if _forbids(c.input_model)]

    open_models = sorted(
        f"{c.id} ({c.input_model.__name__}: "
        f"extra={(c.input_model.model_config or {}).get('extra')!r})"
        for c in capabilities
        if not _forbids(c.input_model)
    )
    assert len(forbidding) == len(capabilities), (
        "these capability input models accept undeclared fields at the seam: "
        f"{open_models}"
    )


def test_no_capability_widens_its_whole_model_for_free_form_input() -> None:
    """The escape hatch D-06 forbids: relaxing a whole model to carry free-form
    input. A capability that needs one declares a *typed field* for it."""
    widened = sorted(
        f"{c.id} ({c.input_model.__name__})"
        for c in get_registry().list()
        if (c.input_model.model_config or {}).get("extra") in {"allow", "ignore"}
    )
    assert not widened, (
        "a capability expressed an open payload by relaxing its whole model "
        f"instead of declaring a typed field: {widened}"
    )


def test_a_previously_unforbidden_write_model_rejects_an_undeclared_field() -> None:
    """The rejection contract, checked on a *write* capability's model.

    ``CardArchiveInput`` is one of the models this plan hardened, and archive is a
    write — the class of capability where an unexpected field is most dangerous.
    """
    with pytest.raises(ValidationError):
        CardArchiveInput(workspace=".", card_id="some-card", bogus=1)


# ---------------------------------------------------------------------------
# Layer 2 — model-to-handler binding audit (D-05, Finding G3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cap_id", _capability_ids())
def test_declared_fields_bind_to_the_handler(cap_id: str) -> None:
    """Every declared field must be a parameter the handler can receive.

    Uses ``Signature.bind`` rather than a name-subset check, so it catches both
    halves of a mismatch: a declared field the handler will not accept, and a
    required handler parameter no field supplies.
    """
    capability = get_registry().get(cap_id)
    signature = inspect.signature(capability.handler)

    if any(
        param.kind is inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    ):
        pytest.skip(f"{cap_id} handler declares **kwargs — it binds unconditionally")

    fields = {name: None for name in capability.input_model.model_fields}
    try:
        signature.bind(**fields)
    except TypeError as exc:  # pragma: no cover - failure path
        pytest.fail(
            f"{cap_id}: {capability.input_model.__name__} fields {sorted(fields)} "
            f"do not bind to handler{signature}: {exc}"
        )


# ---------------------------------------------------------------------------
# Determinism of the seam's multi-error reason (GOV-01 ordering edge)
# ---------------------------------------------------------------------------


def _reason_for(cap_id: str, payload: dict) -> str:
    registry = get_registry()
    with pytest.raises(CapabilityInputError) as excinfo:
        registry.invoke(cap_id, payload)
    return excinfo.value.reason


def test_multi_error_reason_is_byte_identical_across_invocations() -> None:
    """Two surfaces rendering the same rejection must render the same string, so
    the same payload rejected twice must produce one byte-identical reason."""
    payload = {"workspace": ".", "card_id": "some-card", "bogus": 1, "also_bogus": 2}

    first = _reason_for("knowledge.card.archive", dict(payload))
    second = _reason_for("knowledge.card.archive", dict(payload))

    assert first == second
    assert first.count(";") == 1, f"expected exactly two reported errors, got: {first}"


def test_multi_error_reason_does_not_depend_on_payload_key_order() -> None:
    """The ordering edge GOV-01 turns on.

    An MCP client and a CLI call site building the same logical payload need not
    insert its keys in the same order. Pydantic reports ``extra_forbidden`` errors
    in *payload* order, so without a total order imposed at the seam the two
    callers get different reason strings for an identical rejection — one contract
    forked into two messages.
    """
    base = {"workspace": ".", "card_id": "some-card"}
    forward = _reason_for(
        "knowledge.card.archive", {**base, "zz_bogus": 1, "aa_bogus": 2}
    )
    reversed_ = _reason_for(
        "knowledge.card.archive", {**base, "aa_bogus": 2, "zz_bogus": 1}
    )

    assert forward == reversed_, (
        "the seam's reason string changed with payload key insertion order: "
        f"{forward!r} != {reversed_!r}"
    )


def test_multi_error_reason_follows_model_field_declaration_order() -> None:
    """Declared-field failures are reported in the order the model declares them,
    not the order the caller happened to send them."""
    from construct.capabilities.catalog import CardCreateInput

    field_order = list(CardCreateInput.model_fields)
    assert field_order.index("confidence") < field_order.index("source_tier")

    reason = _reason_for(
        "knowledge.card.create",
        {
            "workspace": ".",
            "title": "T",
            "epistemic_type": "finding",
            "domains": ["d"],
            # Sent in the *reverse* of declaration order on purpose.
            "source_tier": 99,
            "confidence": 99,
        },
    )

    assert reason.index("confidence") < reason.index("source_tier"), reason


# ---------------------------------------------------------------------------
# The five repaired capabilities, driven through the seam end to end
#
# The signature audit above cannot see a ``**kwargs`` shim's marshalling, and
# ``Signature.bind`` proves a call is *constructible*, never that it *arrives*.
# These tests close both gaps for the five capabilities whose models did not
# describe their handlers — the five nobody had ever called by keyword.
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """A throwaway copy of the canonical fixture, so write capabilities cannot
    mutate the checked-in one."""
    destination = tmp_path / "my-construct"
    shutil.copytree(FIXTURE_WS, destination)
    return destination


def test_card_archive_reaches_its_service_through_the_seam(workspace: Path) -> None:
    result = get_registry().invoke(
        "knowledge.card.archive",
        {"workspace": workspace, "card_id": "card-cmb-cold-spot"},
    )

    assert result.success, result.message


def test_connection_list_reaches_its_service_through_the_seam(workspace: Path) -> None:
    result = get_registry().invoke(
        "knowledge.connection.list", {"workspace": workspace}
    )

    assert result.success, result.message


def test_connection_remove_reaches_its_service_through_the_seam(
    workspace: Path,
) -> None:
    result = get_registry().invoke(
        "knowledge.connection.remove",
        {
            "workspace": workspace,
            "from_id": "card-dark-energy-w0wa",
            "to_id": "card-desi-bao-results",
            "conn_type": "supports",
        },
    )

    assert result.success, result.message


def test_workflow_status_reaches_its_runner_through_the_seam(workspace: Path) -> None:
    result = get_registry().invoke("workflow.status", {"workspace": workspace})

    assert result is not None
    assert hasattr(result, "success")


def test_workflow_status_rejects_the_fields_its_handler_never_accepted() -> None:
    """``WorkflowRunInput`` declared ``workflow_name`` and ``start_step``, which
    the single-parameter runner lambda cannot receive. A contract that documents
    a call nobody can make is worse than no contract, so the fields are gone and
    sending one is now a rejection rather than a ``TypeError``."""
    with pytest.raises(CapabilityInputError):
        get_registry().invoke(
            "workflow.status", {"workspace": ".", "workflow_name": "workflow"}
        )


def test_workflow_status_declares_its_own_model() -> None:
    assert (
        get_registry().get("workflow.status").input_model.__name__
        == "WorkflowStatusInput"
    )


def test_workspace_init_reaches_its_service_with_a_typed_domain(
    tmp_path: Path,
) -> None:
    """T-18-13: the domain payload is a *typed* nested model, not an open dict,
    so ``DomainInitInput``'s own shape is enforced before any directory is made."""
    target = tmp_path / "fresh-workspace"

    get_registry().invoke(
        "workspace.init",
        {
            "root": target,
            "domain": {
                "domain_id": "quantum-gravity",
                "display_name": "Quantum Gravity",
                "scope": "Approaches to unifying gravity and quantum theory",
                "taxonomy_seeds": ["loop-quantum-gravity"],
                "source_priorities": ["peer-reviewed"],
                "research_seeds": ["spin foam models"],
            },
        },
    )

    assert (target / "cards").is_dir()
    assert (target / "domains.yaml").exists()


def test_workspace_init_rejects_a_malformed_domain_payload(tmp_path: Path) -> None:
    with pytest.raises(CapabilityInputError):
        get_registry().invoke(
            "workspace.init",
            {"root": tmp_path / "never-created", "domain": {"domain_id": "only-this"}},
        )


# ---------------------------------------------------------------------------
# Layer 3 — one dispatch path in the repository (GOV-01, plan 18-03)
#
# Plan 18-02's ``test_the_positional_cli_call_paths_still_work`` stood here and
# pinned the *opposite* invariant: it held research Finding G5's ordering
# constraint open, asserting the positional branches still worked because
# ``cli.py`` still needed them. Plan 18-03 discharged that constraint by putting
# every ``cli.py`` command on the seam, so the branches were retired and the test
# it guarded was replaced by its inverse below. Retiring the branch and deleting
# the test that demanded it is one edit, not two.
# ---------------------------------------------------------------------------


def test_the_retired_positional_call_paths_are_gone(workspace: Path) -> None:
    """The inverse of the guard plan 18-02 left here.

    These four positional call forms were real ``cli.py`` call sites one plan ago.
    They must now be ``TypeError`` — not because a caller would be *wrong* to use
    them, but because a handler that still accepts one is a second way for a
    payload to reach a service without crossing ``input_model``.
    """
    from construct.schemas.workspace import ConnectionType
    from construct.services.knowledge import CardAuthor

    registry = get_registry()

    with pytest.raises(TypeError):
        registry.get("knowledge.card.archive").handler(
            workspace, "card-cmb-cold-spot", author=CardAuthor("curator")
        )

    with pytest.raises(TypeError):
        registry.get("knowledge.connection.list").handler(
            workspace, card_id=None, include_archived=False
        )

    with pytest.raises(TypeError):
        registry.get("knowledge.connection.remove").handler(
            workspace,
            "card-dark-energy-w0wa",
            "card-desi-bao-results",
            ConnectionType("supports"),
        )

    # graph.status — services/help.py:141 called this positionally, and the
    # record's handler was a lambda deliberately shaped to accept it (ING-05).
    with pytest.raises(TypeError):
        registry.get("graph.status").handler(workspace)


def test_graph_status_handler_is_keyword_only() -> None:
    """The one accommodation that existed for a *capability-to-capability* call.

    ``catalog.py`` documented the ``graph.status`` lambda as binding both call
    forms because ``services/help.py`` invoked it positionally. That caller is on
    the seam now, so the parameter is keyword-only and the accommodation is gone.
    """
    handler = get_registry().get("graph.status").handler
    parameters = inspect.signature(handler).parameters

    assert sorted(parameters) == ["workspace"]
    assert all(
        param.kind is inspect.Parameter.KEYWORD_ONLY for param in parameters.values()
    ), {name: param.kind for name, param in parameters.items()}


def test_no_dual_mode_positional_passthrough_branch_survives() -> None:
    """The nine ``if args: <passthrough>`` branches plan 18-02 enumerated are gone.

    Asserted on the source rather than by calling each handler, because the point
    is that the *branch* no longer exists to be re-entered — a runtime check would
    pass just as happily against a branch nothing currently reaches.

    Ten sibling handlers expressed the same intent as ``if args: raise TypeError``
    hand-rolled guards. Those are gone too, converted to ``**kwargs``-only
    signatures: identical behaviour, enforced by Python's own binding rather than
    by a line somebody has to remember to write.
    """
    source = Path(catalog.__file__).read_text(encoding="utf-8")

    assert "if args:" not in source, (
        "a positional-passthrough branch (or a hand-rolled positional guard) is "
        "back in catalog.py; the seam dispatches by keyword, so a positional "
        "branch can only serve a second, unvalidated caller"
    )


# ---------------------------------------------------------------------------
# The directory-scoped guard: no second path may appear
# ---------------------------------------------------------------------------

#: Everything under ``src/construct/`` is scanned except the capability package
#: itself, which is where reaching a handler is the *job* (``registry.invoke``
#: does it, and ``catalog.py`` binds the handlers in the first place).
_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "construct"
_CAPABILITIES_PACKAGE = _SRC_ROOT / "capabilities"


def _scanned_modules() -> list[Path]:
    """Every module under ``src/construct/`` outside the capabilities package.

    Scoped by *directory* rather than by a hand-typed file list, so a module
    added tomorrow is covered the day it appears rather than the day somebody
    remembers to add it here (WR-01).
    """
    return sorted(
        path
        for path in _SRC_ROOT.rglob("*.py")
        if _CAPABILITIES_PACKAGE not in path.parents
    )


def _imports_the_capability_package(tree: ast.Module) -> bool:
    """Whether a module can obtain a ``CapabilityRecord`` at all.

    Checked on the parsed import statements, including the function-scoped ones —
    ``services/help.py`` imports ``get_registry`` inside ``suggest()`` because a
    module-level import would be circular, and a guard that only read the top of
    the file would miss the very call site this phase converted.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("construct.capabilities"):
                return True
        elif isinstance(node, ast.Import):
            if any(alias.name.startswith("construct.capabilities") for alias in node.names):
                return True
    return False


def _direct_handler_calls(tree: ast.Module) -> list[int]:
    """Line numbers of ``<something>.handler(...)`` *calls* in a parsed module.

    Parsed rather than grepped, and this is not fussiness. A regex over source
    lines matches the phrase inside a comment or a docstring, so documenting the
    anti-pattern — which ``services/help.py`` and ``ui/capability_runner.py`` both
    now do, to record what they used to do and why they stopped — would trip the
    guard. A guard that punishes writing down its own rationale gets deleted.
    """
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "handler"
    ]


def test_the_guard_scans_a_plausible_number_of_modules() -> None:
    """Non-vacuity: a glob that silently matched nothing would make the guard
    below pass forever. The three files converted by plans 18-01 and 18-03 are
    named explicitly, because they are exactly where a regression lands."""
    scanned = _scanned_modules()

    assert len(scanned) > 20, f"the directory scan found only {len(scanned)} modules"
    names = {path.relative_to(_SRC_ROOT).as_posix() for path in scanned}
    assert {"cli.py", "ui/capability_runner.py", "services/help.py"} <= names
    assert not any(name.startswith("capabilities/") for name in names)


def test_every_registry_aware_module_is_covered_by_the_guard() -> None:
    """The guard's scope, asserted rather than assumed.

    ``test_no_registry_aware_module_calls_a_handler_directly`` only inspects
    modules that can actually obtain a ``CapabilityRecord``. That narrowing is
    load-bearing and therefore checked here: every module this phase converted
    must be inside the scope, and the scope must not have quietly collapsed to a
    handful of files.
    """
    covered = {
        path.relative_to(_SRC_ROOT).as_posix()
        for path in _scanned_modules()
        if _imports_the_capability_package(ast.parse(path.read_text(encoding="utf-8")))
    }

    assert {"cli.py", "services/help.py", "ui/capability_runner.py", "mcp/server.py"} <= covered, (
        f"a converted module fell out of the guard's scope; covered: {sorted(covered)}"
    )


def test_workflow_runner_is_not_a_capability_caller() -> None:
    """Research assumption A2, resolved by reading the code rather than assuming.

    ``pipelines/workflow_runner.py:201`` calls ``step.handler(**kwargs)``, which
    looks like the pattern this phase is retiring. It is not. ``WorkflowStep`` is
    a local dataclass with its own ``handler`` / ``handler_kwargs`` pair — a field
    ``CapabilityRecord`` does not have — and the module cannot reach the registry
    at all. Two different abstractions that happen to share an attribute name.

    So it is out of scope, and this test is why that is a finding rather than an
    exemption: the reason it is skipped is *derived and asserted*, not written
    into an allowlist. The day ``workflow_runner`` imports the capability package,
    this test fails and it joins the guard.
    """
    from construct.pipelines.workflow_runner import WorkflowStep
    from construct.capabilities.registry import CapabilityRecord

    path = _SRC_ROOT / "pipelines" / "workflow_runner.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    assert _direct_handler_calls(tree), "the A2 call site vanished; re-resolve A2"
    assert not _imports_the_capability_package(tree)

    step_fields = set(WorkflowStep.__dataclass_fields__)
    assert {"handler", "handler_kwargs"} <= step_fields
    assert not hasattr(CapabilityRecord, "handler_kwargs")


# ---------------------------------------------------------------------------
# views.validate_data — the last hand-written command group joins the registry
# ---------------------------------------------------------------------------


def test_views_validate_data_is_registered_on_both_surfaces() -> None:
    """D-02: registration is what makes ``views validate`` reachable by the one
    path, and what makes Phase 19's generated HTTP adapter inherit it without a
    code change. Both names are asserted because a record with no
    ``mcp_tool_name`` is registered but not reachable."""
    capability = get_registry().get("views.validate_data")

    assert capability.cli_name
    assert capability.mcp_tool_name
    assert capability.input_model.__name__ == "ViewsValidateInput"


def test_views_validate_data_shares_the_generate_side_vocabulary() -> None:
    """The two views capabilities must not name the same thing two ways.

    ``views.generate_data`` declares ``install_root``; a validate model declaring
    ``root`` or ``path`` would make one group speak two dialects at the boundary
    an agent reads.
    """
    registry = get_registry()
    generate_fields = set(registry.get("views.generate_data").input_model.model_fields)
    validate_fields = set(registry.get("views.validate_data").input_model.model_fields)

    assert generate_fields == validate_fields == {"install_root"}


def test_views_validate_data_refuses_a_non_install_root_without_naming_a_path(
    tmp_path: Path,
) -> None:
    """T-18-07 / T-18-10, together.

    Registration is what makes ``install_root`` *agent-supplied* over MCP and, in
    Phase 19, over HTTP — so the marker-file guard stops being an internal
    convenience and becomes a boundary control. It must run before any file is
    read, and its reason must not echo a filesystem path back to the caller.
    """
    outsider = tmp_path / "not-a-construct-install"
    (outsider / "views" / "build" / "data").mkdir(parents=True)
    (outsider / "views" / "build" / "data" / "domains.json").write_text(
        "this is not json and must never be read", encoding="utf-8"
    )

    result = get_registry().invoke("views.validate_data", {"install_root": outsider})

    assert result.success is False
    # The file above is malformed on purpose: if the guard ran late, the report
    # would carry a parse failure for it instead of an install-root refusal.
    assert "domains.json" not in result.message
    assert not (result.data or {}).get("results")

    haystack = result.message + " ".join(e.reason for e in result.errors)
    for segment in (str(outsider), outsider.name, str(tmp_path)):
        assert segment not in haystack, (
            f"the rejection reason echoed a filesystem path segment {segment!r}: "
            f"{haystack!r}"
        )


def test_views_validate_data_refuses_a_path_that_is_not_a_directory(
    tmp_path: Path,
) -> None:
    """The other half of the guard, which ``install_root_error`` reports first."""
    a_file = tmp_path / "AGENTS.md"
    a_file.write_text("# not a directory\n", encoding="utf-8")

    result = get_registry().invoke("views.validate_data", {"install_root": a_file})

    assert result.success is False
    assert str(a_file) not in result.message


# ── The workspace marker guard on the write capabilities (CR-04) ──────────

#: Every registered capability that writes into an agent-supplied ``workspace``,
#: with a schema-shaped payload for each. Enumerated rather than discovered so a
#: new write capability has to be added here deliberately — the guard cannot go
#: quiet by a capability simply not being found.
_WRITE_CAPABILITIES: dict[str, dict] = {
    "knowledge.card.create": {
        "title": "Guarded", "epistemic_type": "finding", "domains": ["d"],
        "confidence": 3, "source_tier": 3,
    },
    "knowledge.card.edit": {"card_id": "guarded", "title": "Renamed"},
    "knowledge.card.archive": {"card_id": "guarded"},
    "knowledge.connection.add": {
        "from_id": "a", "to_id": "b", "conn_type": "supports",
    },
    "knowledge.connection.remove": {
        "from_id": "a", "to_id": "b", "conn_type": "supports",
    },
    "ingest.source": {"source": "a note the guard must never persist"},
}


@pytest.mark.parametrize("cap_id", sorted(_WRITE_CAPABILITIES))
def test_write_capabilities_refuse_a_workspace_that_carries_no_marker(
    tmp_path: Path, cap_id: str
) -> None:
    """CR-04: the boundary control the views capabilities got, on the write side.

    ``views.generate_data`` / ``views.validate_data`` gained ``install_root_error``
    precisely because registration is what makes a path *agent-supplied* over MCP.
    The MCP-exposed **write** capabilities — ``construct_create_card``,
    ``construct_edit_card``, ``construct_add_connection``,
    ``construct_ingest_source`` — took no such guard, and ``Path`` accepts any
    absolute or ``../``-relative value. Verified before the fix:
    ``knowledge.card.create`` against
    ``/tmp/definitely-not-a-workspace-9x8/secret-dir`` returned
    ``success=True, "Card 't' created as t"`` after creating ``cards/`` and
    ``log/`` and writing into both — an MCP primitive for creating directories
    and writing attacker-influenced markdown/JSONL anywhere the process can write,
    with a success receipt.

    The path is a *sibling* of ``tmp_path`` rather than ``tmp_path`` itself, so
    the assertion is that nothing was created at all, not that a pre-existing
    directory stayed empty.
    """
    outsider = tmp_path / "not-a-construct-workspace" / "secret-dir"
    assert not outsider.exists()

    result = get_registry().invoke(cap_id, {"workspace": outsider, **_WRITE_CAPABILITIES[cap_id]})

    assert result.success is False, f"{cap_id} accepted a non-workspace path"
    assert not outsider.exists(), f"{cap_id} created {outsider} before refusing"

    # T-18-10, the ``install_root_error`` convention: the reason names no path.
    haystack = result.message + " ".join(e.reason for e in result.errors)
    for segment in (str(outsider), outsider.name, outsider.parent.name, str(tmp_path)):
        assert segment not in haystack, (
            f"{cap_id}'s refusal echoed a filesystem path segment {segment!r}: {haystack!r}"
        )


@pytest.mark.parametrize("cap_id", sorted(_WRITE_CAPABILITIES))
def test_write_capabilities_refuse_a_workspace_that_is_not_a_directory(
    tmp_path: Path, cap_id: str
) -> None:
    """The other half of the guard, which ``workspace_error`` reports first."""
    a_file = tmp_path / "domains.yaml"
    a_file.write_text("domains: []\n", encoding="utf-8")

    result = get_registry().invoke(cap_id, {"workspace": a_file, **_WRITE_CAPABILITIES[cap_id]})

    assert result.success is False
    assert str(a_file) not in result.message


def test_a_real_workspace_still_passes_the_write_guard(tmp_path: Path) -> None:
    """Default-deny is only correct if the door still opens for a real workspace."""
    from construct.services.init import DomainInitInput, initialize_workspace

    ws = tmp_path / "workspace"
    initialize_workspace(ws, DomainInitInput(
        domain_id="test-domain",
        display_name="Test Domain",
        scope="A domain for the write-guard test.",
        taxonomy_seeds=["test-category"],
        source_priorities=["web"],
        research_seeds=["seed"],
    ))

    result = get_registry().invoke("knowledge.card.create", {
        "workspace": ws, **_WRITE_CAPABILITIES["knowledge.card.create"],
    })

    assert result.success is True, result.message
    assert (ws / "cards" / "guarded.md").is_file()


def test_no_registry_aware_module_calls_a_handler_directly() -> None:
    """GOV-01's structural claim: exactly one path from a payload to a handler.

    Every surface — CLI, MCP, the Streamlit form, and one capability calling
    another — now dispatches through ``registry.invoke``, which validates against
    the declared ``input_model`` first. A module that reaches ``cap.handler(...)``
    instead has built a second path, and a second path is a payload that never met
    the contract.

    There is deliberately **no allowlist** (D-05). If a caller genuinely needs
    direct access, that is a design conversation, not an entry in a set here — an
    exemption list is how the five never-keyword-called capabilities plan 18-02
    repaired stayed broken for as long as they did.
    """
    offenders: list[str] = []
    for path in _scanned_modules():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        if not _imports_the_capability_package(tree):
            continue
        lines = source.splitlines()
        for lineno in _direct_handler_calls(tree):
            offenders.append(
                f"{path.relative_to(_SRC_ROOT).as_posix()}:{lineno}: "
                f"{lines[lineno - 1].strip()}"
            )

    assert not offenders, (
        "these modules reach a capability handler directly instead of dispatching "
        "through registry.invoke:\n  " + "\n  ".join(offenders)
    )
