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

import inspect
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from construct.capabilities.catalog import CardArchiveInput, get_registry
from construct.capabilities.errors import CapabilityInputError

FIXTURE_WS = Path(__file__).resolve().parents[2] / "test-ws" / "my-construct"

# A deliberate tripwire (not a name set): adding a capability must be a conscious
# edit here, which is what forces the author past the two guards below.
REGISTRY_SIZE = 28

# Capabilities whose declared model does not describe their handler. Task 2 of
# plan 18-02 repairs all five and deletes this set together with its xfail marks.
_KNOWN_MISMATCHES = frozenset(
    {
        "knowledge.card.archive",
        "knowledge.connection.list",
        "knowledge.connection.remove",
        "workflow.status",
        "workspace.init",
    }
)


def _forbids(model: type) -> bool:
    """Whether a model's resolved config rejects undeclared fields."""
    return (model.model_config or {}).get("extra") == "forbid"


def _binding_params() -> list:
    params = []
    for capability in get_registry().list():
        marks = (
            [
                pytest.mark.xfail(
                    strict=True,
                    reason="18-02 Task 2 repairs this model-to-handler mismatch",
                )
            ]
            if capability.id in _KNOWN_MISMATCHES
            else []
        )
        params.append(pytest.param(capability.id, marks=marks))
    return params


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


@pytest.mark.parametrize("cap_id", _binding_params())
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


def test_the_positional_cli_call_paths_still_work(workspace: Path) -> None:
    """Research Finding G5's ordering constraint, pinned.

    ``cli.py`` still calls these handlers positionally; plan 18-03 normalizes
    those call sites onto the seam and only then may the positional branches go.
    Until it lands, retiring one breaks the CLI — so this test fails loudly if a
    branch is retired early.
    """
    from construct.services.knowledge import CardAuthor

    registry = get_registry()

    # knowledge.card.archive — cli.py: handler(workspace, card_id, author=...)
    assert registry.get("knowledge.card.archive").handler(
        workspace, "card-cmb-cold-spot", author=CardAuthor("curator")
    ).success

    # knowledge.connection.list — cli.py: handler(workspace, card_id=…, include_archived=…)
    assert registry.get("knowledge.connection.list").handler(
        workspace, card_id=None, include_archived=False
    ).success

    # knowledge.connection.remove — cli.py: handler(workspace, from_id, to_id, ctype)
    from construct.schemas.workspace import ConnectionType

    assert registry.get("knowledge.connection.remove").handler(
        workspace,
        "card-dark-energy-w0wa",
        "card-desi-bao-results",
        ConnectionType("supports"),
    ).success

    # workflow.status — cli.py: handler(workspace)
    assert registry.get("workflow.status").handler(workspace) is not None
