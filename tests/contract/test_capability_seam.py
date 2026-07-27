"""Permanent contract guards for the GOV-01 capability invocation seam (D-05, D-06).

Two layers live here.

**Layer 1 — forbid cardinality (D-06).** The number of registry input models that
reject undeclared fields must *equal* the registry size. A capability registered
without ``extra="forbid"`` fails this the moment it lands. The registry size is
asserted separately, as one explicit integer a future capability must deliberately
bump.

The shape is the point. ``tests/contract/test_mcp_contracts.py:53-80`` asserts a
hand-typed ``expected = {...}`` name set; that is the WR-01 anti-pattern, because a
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

import pytest
from pydantic import ValidationError

from construct.capabilities.catalog import CardArchiveInput, get_registry
from construct.capabilities.errors import CapabilityInputError

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
