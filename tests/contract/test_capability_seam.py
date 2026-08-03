"""Permanent contract guards for the GOV-01 capability invocation seam (D-05, D-06).

Three layers live here.

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

**Layer 3 — workspace-id resolution over the whole registry (HTTP-03, D-11).**
``resolve_payload_workspace`` is a single code path with a 26-capability blast
radius, so the three parametrised families at the bottom of this file — coercion,
traversal, collision — assert **per capability**, never per field name.

That distinction is the whole reason they exist. A resolver test covering only
``workspace.status`` proves the ``path`` spelling works and says nothing about
the other three spellings; worse, it says nothing about the str/Path split,
because a single capability can only ever be on one side of it. 13 of the
workspace-scoped models declare a ``str`` field and 13 declare a ``Path``, and
the seam emits ``str(resolved)`` for all of them — pydantic coerces ``str ->
Path`` but not the reverse, so the direction is load-bearing and covering one
field name is the documented way it would have been missed (RESEARCH assumption
A2).

Each family is driven by ``WORKSPACE_FIELD``'s keys rather than by a hand-listed
table, for the same reason ``_capability_ids()`` carries no exemption set: a
table here would become one more guard a registration has to trip, and the one
nobody remembers.

**Known blind spot, stated rather than implied.** A handler declaring ``**kwargs``
accepts any field name, so the signature audit cannot prove such a shim actually
*marshals* what it accepts. The seam-invocation tests at the bottom of this file
cover the repaired capabilities where the signature audit goes blind.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import shutil
from pathlib import Path
from typing import Iterator

import pytest
from pydantic import ValidationError

from construct.capabilities import catalog
from construct.capabilities.catalog import CardArchiveInput, get_registry
from construct.capabilities.errors import CapabilityInputError
from construct.capabilities.workspaces import (
    CREATE_MODE_CAPABILITIES,
    INSTALL_ROOT_FIELD,
    WORKSPACE_FIELD,
    WORKSPACE_ID_KEY,
    resolve_payload_workspace,
    set_launch_install_root,
)

FIXTURE_WS = Path(__file__).resolve().parents[2] / "test-ws" / "my-construct"

# A deliberate tripwire (not a name set): adding a capability must be a conscious
# edit here, which is what forces the author past the two guards below.
#
# 28 -> 29 in plan 18-03: ``views.validate_data`` joins the registry (D-02), so
# ``views validate`` stops being the last hand-written command group and becomes
# reachable from CLI and MCP by the one path every other capability uses. Bumping
# this integer is the intended act, not a workaround for it.
#
# 29 -> 30 in plan 19-08: ``workflow.list`` joins the registry (D-13). Run
# enumeration is a capability rather than a CLI command precisely so CLI, MCP and
# HTTP gain it at the same moment — a browser-only run list would have been a
# reader for durable state the CLI could not see.
REGISTRY_SIZE = 30


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


def test_nested_multi_error_reason_does_not_depend_on_payload_key_order() -> None:
    """CR-05: the ordering guarantee must hold one nesting level down too.

    ``from_validation_error``'s docstring promises "a total order that does not
    depend on the payload", but ``_error_order_key`` read only ``loc[0]``. Every
    error under one declared field therefore tied on the same key and fell back to
    pydantic's own order — which for ``extra_forbidden`` is payload key insertion
    order. Reproduced against ``workspace.init``, whose ``domain`` is the phase's
    own example of a typed nested payload (T-18-13):

      {'root': …, 'domain': {…, 'zz': 1, 'aa': 2}}
        -> '… domain.zz: Unexpected …; domain.aa: Unexpected …'
      {'root': …, 'domain': {…, 'aa': 2, 'zz': 1}}
        -> '… domain.aa: Unexpected …; domain.zz: Unexpected …'

    Two callers sending the same logical payload, two different reason strings —
    the fork GOV-01 exists to close, surviving because
    ``test_multi_error_reason_does_not_depend_on_payload_key_order`` above only
    varies TOP-LEVEL keys.
    """
    base = {"domain_id": "d", "display_name": "D", "scope": "s",
            "taxonomy_seeds": ["t"], "source_priorities": ["p"], "research_seeds": ["r"]}

    forward = _reason_for(
        "workspace.init", {"root": ".", "domain": {**base, "zz_bogus": 1, "aa_bogus": 2}}
    )
    reversed_ = _reason_for(
        "workspace.init", {"root": ".", "domain": {**base, "aa_bogus": 2, "zz_bogus": 1}}
    )

    assert forward == reversed_, (
        "the seam's reason string changed with NESTED payload key insertion order: "
        f"{forward!r} != {reversed_!r}"
    )
    # Vacuity guard: both nested keys must actually be in the reason.
    assert "domain.aa_bogus" in forward and "domain.zz_bogus" in forward, forward
    # Undeclared nested keys sort by name, the same rule the top level uses.
    assert forward.index("domain.aa_bogus") < forward.index("domain.zz_bogus"), forward


def test_nested_declared_field_errors_follow_declaration_order() -> None:
    """Sorting on the whole ``loc`` must not sort nested *declared* fields by name.

    The tail is ranked by the sub-model's declaration index, not by the raw key,
    so a nested declared field reports in declaration order — the same rule the
    top level follows.

    ``domain_id`` / ``display_name`` is the discriminating pair: the sub-model
    declares ``domain_id`` first, but ``display_name`` sorts first
    alphabetically. A naive "sort by the whole loc tuple as strings" — the
    obvious way to fix CR-05 — passes the nesting test above and silently
    re-orders these two. This is the test that refuses it.
    """
    from construct.services.init import DomainInitInput

    order = list(DomainInitInput.__dataclass_fields__)
    assert order.index("domain_id") < order.index("display_name"), order
    assert "display_name" < "domain_id", "the pair no longer discriminates"

    reason = _reason_for("workspace.init", {
        "root": ".",
        # Both missing, and every key that IS sent is out of declaration order.
        "domain": {"research_seeds": ["r"], "source_priorities": ["p"],
                   "taxonomy_seeds": ["t"], "scope": "s"},
    })

    assert "domain.domain_id" in reason and "domain.display_name" in reason, reason
    assert reason.index("domain.domain_id") < reason.index("domain.display_name"), reason


def test_error_ordering_is_total_for_mixed_depths() -> None:
    """A top-level error and a nested one must not tie, whatever the payload order.

    ``list.sort`` is stable, so a tie falls back to pydantic's payload-ordered
    output — which is exactly how CR-05 hid. This pins that the key separates
    them by itself rather than by luck.
    """
    base = {"domain_id": "d", "display_name": "D", "scope": "s",
            "taxonomy_seeds": ["t"], "source_priorities": ["p"], "research_seeds": ["r"]}

    forward = _reason_for(
        "workspace.init",
        {"root": ".", "top_bogus": 1, "domain": {**base, "nested_bogus": 2}},
    )
    reversed_ = _reason_for(
        "workspace.init",
        {"domain": {**base, "nested_bogus": 2}, "top_bogus": 1, "root": "."},
    )

    assert forward == reversed_, f"{forward!r} != {reversed_!r}"
    assert "domain.nested_bogus" in forward and "top_bogus" in forward, forward


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


# ── T-18-34: the same control, on the field CR-04's fix did not reach ────────
#
# CR-04 guarded the six capabilities spelling the field `workspace`. The run
# family spells it `workspace_path`, took no guard, and opening a sqlite
# checkpointer materialises `<path>/.construct/workflow/<name>.sqlite` and every
# parent BEFORE the run can discover the workspace is not a workspace and fail.
#
# The security audit named three (curation.run / research.run / daily.run).
# Measuring found SEVEN — the `review` and `inspect` pairs create too, because
# "read-only" describes what `inspect` does to the WORKSPACE, not what opening a
# checkpointer does to the FILESYSTEM.
#
# So this test does not hard-code a list. Scoping a control to the instances
# someone happened to name is precisely the defect that produced T-18-34 from
# CR-04's fix, and a hand-typed list here would rebuild that trap for the next
# capability. It measures every registered capability that accepts a
# workspace-shaped path and asserts the property directly.

_WORKSPACE_FIELDS = ("workspace_path", "workspace", "install_root")


def _workspace_field(cap) -> str | None:
    """The workspace-shaped input field this capability declares, if any."""
    return next((f for f in _WORKSPACE_FIELDS if f in cap.input_model.model_fields), None)


def _minimal_payload(cap, field: str, value) -> dict:
    """`value` for the workspace field plus a stub for every other required one.

    The stubs only need to satisfy the model so dispatch reaches the handler —
    this test is about the filesystem, not about the handler's own semantics.
    """
    payload: dict = {field: value}
    for name, spec in cap.input_model.model_fields.items():
        if name == field or not spec.is_required():
            continue
        annotation = str(spec.annotation)
        payload[name] = "probe-id" if "str" in annotation else (1 if "int" in annotation else [])
    return payload


def _capabilities_taking_a_workspace_path() -> list:
    return [c for c in get_registry().list() if _workspace_field(c) is not None]


@pytest.mark.parametrize(
    "cap_id",
    sorted(c.id for c in _capabilities_taking_a_workspace_path()),
)
def test_no_capability_creates_anything_at_an_agent_supplied_non_workspace(
    tmp_path: Path, cap_id: str
) -> None:
    """T-18-34 / the property `workspace_error`'s docstring states.

    Reproduced before the fix, through the exact closure `mcp/server.py`
    registers::

        curation.run  workspace_path=/tmp/probe/a/b/inner
          -> created a, a/b, a/b/inner, a/b/inner/.construct,
             .construct/workflow, .construct/workflow/curation-run.sqlite

    The target is a nested path under a *sibling* of anything pre-existing, so
    the assertion is that nothing was created at all — not that a pre-existing
    directory stayed empty.
    """
    registry = get_registry()
    cap = registry.get(cap_id)
    field = _workspace_field(cap)
    outsider = tmp_path / "not-a-workspace" / "deeper" / "inner"
    assert not outsider.exists()

    try:
        registry.invoke(cap_id, _minimal_payload(cap, field, str(outsider)))
    except Exception:
        # A handler may still raise for its own reasons; the filesystem claim
        # below is the one this test makes.
        pass

    assert not outsider.exists(), (
        f"{cap_id} created {outsider} under an agent-supplied non-workspace path"
    )
    assert not outsider.parent.exists(), f"{cap_id} created {outsider.parent}"


def test_the_run_family_refusal_names_its_own_field_and_no_path(tmp_path: Path) -> None:
    """The refusal must point at `workspace_path`, not at `workspace`.

    `_workspace_refusal` hard-coded `field="workspace"`; reusing it verbatim for
    the run family would have told a caller to fix a field it never sent. The
    reason still carries no filesystem path (T-18-10 convention).
    """
    outsider = tmp_path / "not-a-workspace" / "inner"

    result = get_registry().invoke("curation.run", {"workspace_path": str(outsider)})

    assert result.success is False
    assert [e.field for e in result.errors] == ["workspace_path"]

    haystack = result.message + " ".join(e.reason for e in result.errors)
    for segment in (str(outsider), outsider.name, outsider.parent.name, str(tmp_path)):
        assert segment not in haystack, (
            f"the run-family refusal echoed a path segment {segment!r}: {haystack!r}"
        )


def test_a_real_workspace_still_reaches_the_run_family_runner(tmp_path: Path) -> None:
    """Default-deny is only correct if the door still opens.

    A real workspace must get PAST the boundary and fail (or succeed) on the
    runner's own terms — a guard that refuses everything would pass the test
    above while breaking the product.
    """
    from construct.services.init import DomainInitInput, initialize_workspace

    ws = tmp_path / "workspace"
    initialize_workspace(ws, DomainInitInput(
        domain_id="test-domain",
        display_name="Test Domain",
        scope="A domain for the run-family guard test.",
        taxonomy_seeds=["test-category"],
        source_priorities=["web"],
        research_seeds=["seed"],
    ))

    result = get_registry().invoke(
        "curation.inspect", {"workspace_path": str(ws), "run_id": "no-such-run"}
    )

    assert "refused the workspace" not in str(result.message), (
        "a real workspace was refused at the boundary instead of reaching the runner"
    )


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


# ---------------------------------------------------------------------------
# HTTP-03 — workspace-id addressing, classified over the WHOLE registry (D-11)
# ---------------------------------------------------------------------------
#
# ``resolve_payload_workspace`` is one code path with a 26-capability blast
# radius, so the guards below assert **per capability**, never per field name. A
# resolver test covering only ``workspace.status`` would prove the ``path``
# spelling works and say nothing about the other three spellings — and, worse,
# nothing about the str/Path split, since a single capability can only be on one
# side of it. That is the documented way RESEARCH assumption A2 ("emitting
# ``str(resolved)`` satisfies both the str-typed and the Path-typed models")
# would have been missed.
#
# The parametrisation is driven by ``WORKSPACE_FIELD``'s keys rather than by a
# hand-listed table, for the same reason ``_capability_ids()`` carries no
# exemption set: a table here would become the sixth guard a registration has to
# trip, and the one nobody remembers. A newly classified capability is audited
# the moment it is classified.


DOMAIN_SEED = {
    "domain_id": "seam-domain",
    "display_name": "Seam Domain",
    "scope": "A domain for the workspace-id resolution guards.",
    "taxonomy_seeds": ["seam-category"],
    "source_priorities": ["web"],
    "research_seeds": ["seed"],
}


@pytest.fixture
def launch_root(install_root: Path) -> Iterator[Path]:
    """The shared contract install root, installed as *launch* context (D-09).

    ``install_root`` (tests/contract/conftest.py) builds two real workspaces,
    ``demo`` and ``second-demo``. The launch root is process-level state, so it
    is cleared on teardown — otherwise one test's ``tmp_path`` stays the
    resolution root for the next, and a workspace-id assertion could pass
    against a tree the test never built.
    """
    set_launch_install_root(install_root)
    yield install_root
    set_launch_install_root(None)


def _tree_fingerprint(root: Path) -> list[tuple[str, str]]:
    """``(relative path, sha256 | '<dir>')`` for everything under ``root``.

    A status-code or exception-type assertion alone does not prove "rejected
    with no filesystem effect" — a rejection that first created a directory and
    then raised would satisfy it. Hashing file *content* as well as listing
    names is what makes the claim byte-level rather than name-level.
    """
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append((relative, "<dir>"))
        else:
            entries.append(
                (relative, hashlib.sha256(path.read_bytes()).hexdigest())
            )
    return entries


# ── The classification is exhaustive and unambiguous (RESEARCH A1) ────────


def test_the_classification_maps_cover_every_registered_capability() -> None:
    """A capability registered without a classification must fail a *test*.

    RESEARCH assumption A1's mitigation. The field maps are a snapshot of the
    registry as it stands today; without this guard a capability added next
    month would simply be unaddressable by id, and would announce that only as a
    request-time ``CapabilityInputError`` to whoever tried it first — the
    repudiation half of T-19-18.

    Asserted as a relationship between two live measurements, in the shape this
    file already uses. The message is built from the *unclassified* ids so the
    failure names the capability the author just added, rather than printing two
    29-element sets for them to diff by eye.
    """
    classified = set(WORKSPACE_FIELD) | set(INSTALL_ROOT_FIELD)
    registered = {capability.id for capability in get_registry().list()}

    unclassified = sorted(registered - classified)
    stale = sorted(classified - registered)

    assert classified == registered, (
        "these capabilities are registered but carry no workspace-id "
        f"classification: {unclassified}; add each to WORKSPACE_FIELD (scoped to "
        "one workspace) or to INSTALL_ROOT_FIELD (scoped to the install root). "
        f"These are classified but no longer registered: {stale}"
    )


def test_the_two_classification_maps_are_disjoint() -> None:
    """One scope per capability, or the resolver has two answers for one id.

    ``resolve_payload_workspace`` treats install-root scope and workspace scope
    as mutually exclusive branches — one injects launch context, the other
    resolves an id — so a capability in both maps would take whichever branch is
    written first and silently ignore the other classification.
    """
    both = sorted(set(WORKSPACE_FIELD) & set(INSTALL_ROOT_FIELD))
    assert not both, (
        "these capabilities are classified as BOTH workspace-scoped and "
        f"install-root-scoped: {both}"
    )


def test_create_mode_capabilities_are_themselves_classified() -> None:
    """The create-mode set names ids, so it can name one that does not exist.

    ``CREATE_MODE_CAPABILITIES`` is consulted as ``cap_id not in ...``, which is
    silently true for a typo — the capability would then be resolved in
    *existence-required* mode and refuse every id it was given.
    """
    unknown = sorted(CREATE_MODE_CAPABILITIES - set(WORKSPACE_FIELD))
    assert not unknown, (
        "these create-mode capabilities are not workspace-scoped (or are "
        f"misspelled): {unknown}"
    )


# ── workspace.init: the caller names a directory, never a location (D-11) ──


def test_workspace_init_by_id_creates_under_the_launch_install_root_only(
    tmp_path: Path, launch_root: Path
) -> None:
    """T-18-34 answered rather than deferred.

    The whole creation-mode argument in one assertion: the caller supplies a
    *name* and the seam supplies the *location*. So the test does not merely
    check that the expected directory appeared — it checks that **nothing else**
    appeared anywhere under ``tmp_path``, which is the claim that would fail if
    the id could steer the parent.
    """
    before = {path for path in tmp_path.rglob("*") if path.is_dir()}
    expected = launch_root / "brand-new"
    assert not expected.exists()

    get_registry().invoke(
        "workspace.init", {WORKSPACE_ID_KEY: "brand-new", "domain": dict(DOMAIN_SEED)}
    )

    assert expected.is_dir(), "workspace.init did not create the named workspace"

    created_outside = sorted(
        str(path)
        for path in {p for p in tmp_path.rglob("*") if p.is_dir()} - before
        if expected not in path.parents and path != expected
    )
    assert not created_outside, (
        "workspace.init created directories outside the id it was given: "
        f"{created_outside}"
    )


def test_a_workspace_created_by_id_is_immediately_addressable_by_id(
    launch_root: Path,
) -> None:
    """D-02's per-request scan is what makes creation and use compose.

    A launch-time cache would answer "no such workspace" for the workspace the
    previous request just created, until restart. Creating and then reading in
    two seam calls is the smallest test that would fail if the scan were cached.
    """
    registry = get_registry()
    registry.invoke(
        "workspace.init", {WORKSPACE_ID_KEY: "just-made", "domain": dict(DOMAIN_SEED)}
    )

    result = registry.invoke("workspace.validate", {WORKSPACE_ID_KEY: "just-made"})

    assert result is not None


def test_workspace_init_refuses_an_id_that_already_names_a_workspace(
    launch_root: Path,
) -> None:
    """The inverted gate. Same scan, read as a conflict instead of a match.

    Creation mode is the one place a resolver could be talked into writing over
    existing knowledge, so the refusal is asserted together with the tree being
    byte-identical afterwards — "raised" and "wrote nothing" are two claims.
    """
    before = _tree_fingerprint(launch_root)

    with pytest.raises(CapabilityInputError) as excinfo:
        get_registry().invoke(
            "workspace.init", {WORKSPACE_ID_KEY: "demo", "domain": dict(DOMAIN_SEED)}
        )

    assert "demo" in excinfo.value.reason
    assert _tree_fingerprint(launch_root) == before, (
        "the refused workspace.init still changed the install root"
    )


def test_workspace_init_refuses_an_id_naming_an_existing_non_workspace(
    launch_root: Path,
) -> None:
    """"Discoverable as a workspace" is narrower than "exists".

    An unrelated directory that happens to share the name passes the scan check.
    Resolving to it would hand ``initialize_workspace`` a tree it did not
    create, so existence — not workspace-ness — is the condition.
    """
    squatter = launch_root / "occupied"
    (squatter / "important").mkdir(parents=True)
    (squatter / "important" / "notes.txt").write_text("do not clobber", encoding="utf-8")
    before = _tree_fingerprint(squatter)

    with pytest.raises(CapabilityInputError) as excinfo:
        get_registry().invoke(
            "workspace.init", {WORKSPACE_ID_KEY: "occupied", "domain": dict(DOMAIN_SEED)}
        )

    assert "occupied" in excinfo.value.reason
    assert _tree_fingerprint(squatter) == before


def test_a_traversal_shaped_id_is_refused_in_creation_mode_too(
    launch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shape gate is unconditional — ``must_exist`` inverts gate 2 only.

    Creation mode is precisely where a dropped shape gate would be worst: a
    traversal-shaped id would name a directory the seam then *creates*. Spying on
    ``discover_workspaces`` proves the shape gate still runs first here, exactly
    as the read path proves it.
    """
    from construct.views.lib import discover as discover_module

    calls: list[Path] = []
    monkeypatch.setattr(
        discover_module, "discover_workspaces", lambda root: calls.append(Path(root)) or []
    )
    before = _tree_fingerprint(launch_root)

    with pytest.raises(CapabilityInputError):
        get_registry().invoke(
            "workspace.init",
            {WORKSPACE_ID_KEY: "../../etc", "domain": dict(DOMAIN_SEED)},
        )

    assert calls == [], "a traversal-shaped creation id reached the filesystem scan"
    assert _tree_fingerprint(launch_root) == before


# ── views.*: install-root scope comes from launch context (D-11) ───────────


@pytest.mark.parametrize("cap_id", sorted(INSTALL_ROOT_FIELD))
def test_an_install_root_scoped_capability_takes_the_launch_root_when_absent(
    launch_root: Path, cap_id: str
) -> None:
    """The injection rule, asserted on the seam's own rewrite.

    ``install_root`` is a ``PATH_SHAPED_KEYS`` entry, so the HTTP envelope
    refuses it with 422 before dispatch (D-10). Without this injection the two
    views capabilities would be exposed and unreachable from a browser — a
    documented exclusion, which is exactly what D-07 says this phase must not
    have.
    """
    field = INSTALL_ROOT_FIELD[cap_id]

    assert resolve_payload_workspace(cap_id, {}) == {field: str(launch_root)}


@pytest.mark.parametrize("cap_id", sorted(INSTALL_ROOT_FIELD))
def test_an_explicit_install_root_is_left_exactly_as_it_arrived(cap_id: str) -> None:
    """The CLI's ``--install-root`` flag is unchanged by the injection.

    This is what makes injection an *addition* rather than a behaviour change:
    every existing CLI and MCP call site supplies the field, and a supplied
    field is never touched. Asserted with no launch root set, so a passing
    result cannot be an accident of the two values coinciding.
    """
    field = INSTALL_ROOT_FIELD[cap_id]
    supplied = {field: "/some/caller/chosen/root"}

    assert resolve_payload_workspace(cap_id, supplied) == supplied


@pytest.mark.parametrize("cap_id", sorted(INSTALL_ROOT_FIELD))
def test_an_install_root_scoped_capability_refuses_a_workspace_id(
    launch_root: Path, cap_id: str
) -> None:
    """A different scope, not a different spelling.

    ``discover_workspaces`` scans the *children* of its argument, so resolving an
    id here would hand these capabilities a single workspace and silently emit an
    empty build. Refusing is the honest answer; and since the install root is the
    authorization boundary itself, it is never caller-chosen over HTTP either.
    """
    with pytest.raises(CapabilityInputError) as excinfo:
        get_registry().invoke(cap_id, {WORKSPACE_ID_KEY: "demo"})

    assert "install root" in excinfo.value.reason


def test_views_validate_data_reaches_the_launch_root_with_an_empty_payload(
    launch_root: Path,
) -> None:
    """End to end, and distinguishable from the explicit-value case below.

    The launch root carries the ``AGENTS.md`` marker, so it passes
    ``install_root_error`` and the handler gets as far as looking for views data.
    "Found nothing to validate" is therefore proof it read *this* root — a bare
    ``success is False`` would be produced by either outcome.
    """
    result = get_registry().invoke("views.validate_data", {})

    assert "found nothing to validate" in result.message


def test_views_validate_data_still_honours_a_supplied_install_root(
    tmp_path: Path, launch_root: Path
) -> None:
    """The other arm of the same pair, chosen to be *distinguishable*.

    The supplied root deliberately lacks the ``AGENTS.md`` marker, so it is
    refused by the install-root guard — an outcome the launch root cannot
    produce. Asserting "success is False" for both would have passed even if the
    supplied value had been overwritten by the injection.
    """
    stranger = tmp_path / "not-an-install"
    stranger.mkdir()

    result = get_registry().invoke("views.validate_data", {"install_root": str(stranger)})

    assert "refused the install root" in result.message


# ---------------------------------------------------------------------------
# The three resolver families — per capability, never per field name
# ---------------------------------------------------------------------------

#: The required fields ``_minimal_payload`` cannot stub, and only those.
#:
#: Its heuristic reads ``str(annotation)`` for the substring ``"str"``, which is
#: right for the 20-odd plain ``str`` fields and wrong for exactly three:
#: ``list[str]`` and ``DomainInitInput`` both contain ``"str"`` as a substring
#: (the latter via *con-str-uct*), and ``ResearchSearchInput`` enforces a
#: one-of-three rule no per-field stub can satisfy.
#:
#: Enumerated rather than generalised. Teaching ``_minimal_payload`` to build
#: valid values for arbitrary annotations would make it a second, weaker copy of
#: pydantic; three named exceptions stay readable and fail loudly if a model
#: changes underneath them.
_COERCION_OVERRIDES: dict[str, dict] = {
    "knowledge.card.create": {"domains": ["seam-domain"]},
    "research.search": {"query": "a probe query"},
    "workspace.init": {"domain": dict(DOMAIN_SEED)},
}


def _workspace_scoped_ids() -> list[str]:
    """Every workspace-scoped capability, from the map itself.

    No exemption set, deliberately — see this module's docstring. Classifying a
    capability is what enrols it in all three families.
    """
    return sorted(WORKSPACE_FIELD)


def _addressable_id(cap_id: str, index: int) -> str:
    """The workspace id to address ``cap_id`` with.

    ``demo`` for the ordinary case. Create-mode capabilities need an id that
    resolves to *nothing*, and a distinct one per case so two parametrisations
    cannot collide with each other's directory.
    """
    if cap_id in CREATE_MODE_CAPABILITIES:
        return f"fresh-workspace-{index}"
    return "demo"


def _id_payload(cap, cap_id: str, workspace_id: str) -> dict:
    """``_minimal_payload``'s stubs, addressed by id instead of by path."""
    payload = _minimal_payload(cap, WORKSPACE_FIELD[cap_id], workspace_id)
    payload.pop(WORKSPACE_FIELD[cap_id])
    payload[WORKSPACE_ID_KEY] = workspace_id
    payload.update(_COERCION_OVERRIDES.get(cap_id, {}))
    return payload


# ── Family 1: coercion (RESEARCH assumption A2) ───────────────────────────


@pytest.mark.parametrize("cap_id", _workspace_scoped_ids())
def test_a_workspace_id_validates_and_arrives_as_the_declared_type(
    launch_root: Path, monkeypatch: pytest.MonkeyPatch, cap_id: str
) -> None:
    """The resolved value reaches the handler in the field, and the type, the
    model declares.

    **This asserts at the validation boundary, not at the handler's outcome, and
    that is deliberate — do not "strengthen" it into a credential-dependent
    test.** Several of these capabilities cannot run without an ``ANTHROPIC_API_KEY``
    or network access (``ask.domain``, the ``research`` family), and others open
    a sqlite checkpointer and execute a real workflow. Asserting on their
    *results* would make this suite need credentials, a network, and seconds per
    case to prove a property that is fully decided before the handler is
    entered: a model that validated is the property under test.

    So the handler is replaced by a spy, which is the *observation point* rather
    than a bypass — record lookup, id resolution and ``model_validate`` all run
    for real, and the spy sees exactly what ``handler(**model.model_dump())``
    would have been called with. That is a stronger claim than "it did not
    raise": it names the field the value landed in and the type it arrived as,
    which is the half a type-blind assertion would miss.

    ``tests/contract/test_http_surface.py`` and the create-then-read case above
    invoke real handlers by id, so the door is separately proven to open.
    """
    registry = get_registry()
    cap = registry.get(cap_id)
    field = WORKSPACE_FIELD[cap_id]
    declared = cap.input_model.model_fields[field].annotation
    workspace_id = _addressable_id(cap_id, 0)

    received: dict = {}
    monkeypatch.setattr(cap, "handler", lambda **kwargs: received.update(kwargs))

    registry.invoke(cap_id, _id_payload(cap, cap_id, workspace_id))

    assert field in received, (
        f"{cap_id}: the resolved workspace never reached the handler's {field!r}"
    )
    value = received[field]
    # ``isinstance`` rather than ``type(...) is``: pydantic resolves ``Path`` to
    # the platform's concrete ``PosixPath``/``WindowsPath``, which an identity
    # check would reject on every Path-declared capability. It still catches the
    # split in both directions — ``str`` and ``Path`` are unrelated types, so a
    # value on the wrong side fails whichever side the model declares.
    assert isinstance(value, declared), (
        f"{cap_id}: {field} arrived as {type(value).__name__}, but the model "
        f"declares {declared}. The seam emits str(resolved); pydantic coerces "
        f"str -> Path but not the reverse."
    )
    assert Path(value) == launch_root / workspace_id, (
        f"{cap_id}: {field} resolved to {value!r}, not to the addressed workspace"
    )


@pytest.mark.parametrize(
    "cap_id, payload",
    [
        ("knowledge.card.list", {}),
        ("curation.inspect", {"run_id": "no-such-run"}),
    ],
)
def test_a_real_handler_runs_when_addressed_by_id(
    launch_root: Path, cap_id: str, payload: dict
) -> None:
    """Default-deny is only correct if the door still opens — on both sides of
    the str/Path split, with no handler patched.

    ``knowledge.card.list`` declares ``workspace: Path``; ``curation.inspect``
    declares ``workspace_path: str``. Neither needs a credential or a network,
    so one case from each side of the split can be asserted for real, which is
    what keeps the spy-based family above honest.
    """
    result = get_registry().invoke(cap_id, {WORKSPACE_ID_KEY: "demo", **payload})

    assert result is not None
    haystack = str(getattr(result, "message", "") or "")
    assert "refused the workspace" not in haystack, (
        f"{cap_id}: an id-addressed real workspace was refused at the boundary"
    )


# ── Family 2: traversal (T-19-03) ─────────────────────────────────────────


@pytest.mark.parametrize("cap_id", _workspace_scoped_ids())
def test_a_traversal_shaped_workspace_id_touches_nothing(
    launch_root: Path, monkeypatch: pytest.MonkeyPatch, cap_id: str
) -> None:
    """Criterion 2, on every workspace-scoped capability: *rejected with no
    filesystem effect*.

    Two claims, because an exception type alone proves neither. The spy on
    ``discover_workspaces`` proves the shape gate ran **first** — a 422 would be
    produced by either gate ordering, but only one ordering leaves the directory
    walk unexecuted. The before/after fingerprint hashes file content as well as
    listing names, so a rejection that created something and then raised would
    fail here even though it "rejected".
    """
    from construct.views.lib import discover as discover_module

    calls: list[Path] = []
    monkeypatch.setattr(
        discover_module, "discover_workspaces", lambda root: calls.append(Path(root)) or []
    )
    before = _tree_fingerprint(launch_root)

    with pytest.raises(CapabilityInputError) as excinfo:
        get_registry().invoke(cap_id, {WORKSPACE_ID_KEY: "../../etc"})

    reason = excinfo.value.reason
    assert "kebab-case" in reason, f"{cap_id}: the reason does not state the shape rule"
    assert "my-construct" in reason, (
        f"{cap_id}: the reason states a rule but carries no example of a valid id"
    )
    assert calls == [], f"{cap_id}: the traversal attempt reached the filesystem scan"
    assert _tree_fingerprint(launch_root) == before, (
        f"{cap_id}: the traversal attempt changed the install root"
    )


# ── Family 3: collision ───────────────────────────────────────────────────


@pytest.mark.parametrize("cap_id", _workspace_scoped_ids())
def test_a_workspace_id_beside_the_capabilitys_own_field_is_refused(
    launch_root: Path, cap_id: str
) -> None:
    """Two ways of naming one workspace must not silently prefer one.

    Preferring either would make the *other* key a value the caller believes it
    sent and the system ignored — the class of defect that is only ever found in
    production. The reason names the conflicting field, because the field
    spelling differs per capability and a caller cannot otherwise tell which of
    the two keys to drop.
    """
    field = WORKSPACE_FIELD[cap_id]

    with pytest.raises(CapabilityInputError) as excinfo:
        get_registry().invoke(
            cap_id, {WORKSPACE_ID_KEY: "demo", field: str(launch_root / "demo")}
        )

    assert field in excinfo.value.reason, (
        f"{cap_id}: the refusal does not name the conflicting field {field!r}, so "
        f"the caller cannot tell which key to drop: {excinfo.value.reason!r}"
    )
