"""Typed errors raised by the capability invocation seam (GOV-01).

Every invoke surface — CLI, MCP, and the HTTP adapter Phase 19 generates — routes
through ``CapabilityRegistry.invoke``. These exceptions are what makes that seam's
failure modes *comparable* across surfaces: one payload rejected for one reason
produces one reason string, whichever surface asked.

They subclass ``Exception`` rather than ``ValueError`` on purpose. A ``ValueError``
subclass raised inside the seam can be swallowed by a pydantic field validator
further up the stack and re-emitted as a validation failure of some unrelated
field, which would fork the reason string per surface — the exact defect GOV-01
exists to close. This is a deliberate, documented exception to the
``ValueError``-subclass convention in AGENTS.md § Error Handling.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, get_args

from pydantic import BaseModel, ValidationError


class CapabilityError(Exception):
    """Base class for every error the capability invocation seam raises.

    Surfaces that want one ``except`` clause for the whole seam catch this;
    surfaces that render the two failure modes differently catch the subclasses.
    """


class CapabilityNotFoundError(CapabilityError):
    """Raised when a capability id is not present in the registry."""

    def __init__(self, cap_id: str, available: Sequence[str]) -> None:
        self.cap_id = cap_id
        self.available: tuple[str, ...] = tuple(available)
        super().__init__(
            f"Capability '{cap_id}' not found. Available: {', '.join(self.available)}"
        )


class CapabilityInputError(CapabilityError):
    """Raised when a payload fails its capability's declared input model."""

    def __init__(self, cap_id: str, reason: str) -> None:
        self.cap_id = cap_id
        self.reason = reason
        super().__init__(f"Invalid input for capability '{cap_id}': {reason}")

    @classmethod
    def from_validation_error(
        cls,
        cap_id: str,
        exc: ValidationError,
        model: type[BaseModel],
    ) -> CapabilityInputError:
        """Build the seam's reason string from a validation error.

        T-18-10: the reason is assembled from field locations and pydantic's own
        constraint messages only. Only ``loc`` and ``msg`` are ever read, and
        ``include_input=False`` / ``include_context=False`` are passed on top of
        that where the error object accepts them — so the caller's submitted
        values, which may be filesystem paths or other sensitive payload
        content, cannot reach a string that is rendered straight back to a
        client.

        ``model`` is the model the payload was validated against. It puts the
        errors into a **total order that does not depend on the payload**:
        declared fields first in model declaration order, then undeclared fields
        sorted by name. Pydantic is deterministic for a *given* payload, but it
        reports ``extra_forbidden`` errors in payload key-insertion order — so an
        MCP client and a CLI call site building the same logical payload with its
        keys in different orders would otherwise receive two different reason
        strings for one identical rejection. That is the contract fork GOV-01
        exists to close, so the ordering is imposed here rather than left to the
        caller's dict literal.

        **D-08 — ``model`` has no default, and that is the contract.** It was
        optional through Phase 18, which made the payload-independent ordering a
        *convention*: every caller that remembered to pass a model got it, and a
        caller that forgot got payload-ordered reasons back with no error, no
        warning, and no way to notice — the reasons are correct, merely ordered
        differently, so the fork only shows up as two surfaces disagreeing. A
        guarantee a caller can silently drop is not a guarantee. Phase 19's HTTP
        adapter is the caller that made the footgun real: it is a *second*
        independent call site building this reason for the same seam, which is
        exactly the shape that would have exercised the default. So the argument
        is required at the type level rather than protected by vigilance.

        The exception is typed as pydantic's ``ValidationError`` because that is
        what the seam raises against a capability's own model. FastAPI's
        ``RequestValidationError`` carries the same error dictionaries with a
        different ``errors()`` signature; :func:`_reported_errors` absorbs that
        difference so the HTTP adapter's envelope rejection is built here rather
        than formatted a second time somewhere else.
        """
        errors = _reported_errors(exc)
        errors.sort(key=_error_order_key(model))
        parts = [
            f"{'.'.join(str(item) for item in error['loc']) or '<root>'}: {error['msg']}"
            for error in errors
        ]
        return cls(cap_id, "; ".join(parts))


def _reported_errors(exc: Any) -> list[dict[str, Any]]:
    """The error entries of a pydantic or FastAPI validation error.

    Pydantic's ``ValidationError.errors`` takes the three suppression keywords;
    FastAPI's ``RequestValidationError.errors`` takes none, because it is a
    plain ``Sequence`` holder rather than a pydantic object. The keywords are
    passed when they are accepted and their absence is not a disclosure either
    way: the reason is built from ``loc`` and ``msg`` alone, so an ``input`` or
    ``ctx`` key left in the dictionary is never read. The keywords stay as
    defence in depth — a future formatter that reached for another key would
    find nothing sensitive there on the path that can supply them.
    """
    try:
        return list(
            exc.errors(include_url=False, include_input=False, include_context=False)
        )
    except TypeError:
        return [dict(error) for error in exc.errors()]


def _field_order(container: Any) -> dict[str, int]:
    """``{field_name: declaration_index}`` for a pydantic model or a dataclass.

    Both shapes appear in one ``loc`` path: ``WorkspaceInitInput`` is a
    ``BaseModel`` whose ``domain`` field is the ``DomainInitInput`` *dataclass*
    (T-18-13), so a key that understood only ``model_fields`` would lose the
    ordering exactly where the phase's own nested-payload example uses it.
    """
    fields = getattr(container, "model_fields", None)
    if fields is None:
        fields = getattr(container, "__dataclass_fields__", None)
    if not fields:
        return {}
    return {name: index for index, name in enumerate(fields)}


def _unwrap_annotation(annotation: Any) -> Any:
    """Yield ``annotation`` and every type argument nested inside it.

    ``domain: DomainInitInput | None`` and ``items: list[Thing]`` both hide the
    container one level in; walking the arguments finds it without the caller
    having to enumerate every typing construct.
    """
    yield annotation
    for arg in get_args(annotation):
        yield from _unwrap_annotation(arg)


def _child_container(container: Any, name: str) -> Any:
    """The model/dataclass declared at ``container.name``, or ``None``."""
    annotation: Any = None
    fields = getattr(container, "model_fields", None)
    if fields is not None and name in fields:
        annotation = fields[name].annotation
    else:
        dataclass_fields = getattr(container, "__dataclass_fields__", None)
        if dataclass_fields is not None and name in dataclass_fields:
            # ``from __future__ import annotations`` leaves this a *string* on a
            # dataclass. Unresolvable here, and deliberately not resolved: the
            # level simply falls back to name ordering, which is still
            # payload-independent.
            annotation = dataclass_fields[name].type

    for candidate in _unwrap_annotation(annotation):
        if _field_order(candidate):
            return candidate
    return None


def _error_order_key(model: type[BaseModel]):
    """A payload-independent sort key over a ``ValidationError``'s entries.

    The rule, applied at **every level of the ``loc`` path** rather than only its
    head: declared fields sort first, in the order their container declares them;
    undeclared fields sort after, by name. ``list.sort`` is stable, so anything
    the key genuinely ties (two errors on one field) keeps pydantic's own order.

    Reading only ``loc[0]`` was the CR-05 defect. Every error under one declared
    field tied on ``(0, index, "")`` and fell through to pydantic's order — which
    for ``extra_forbidden`` is *payload key insertion order*. So two callers
    submitting the same logical payload with a nested dict's keys in different
    orders received two different reason strings, which is precisely the contract
    fork the docstring above claims to close:

      {'root': …, 'domain': {…, 'zz': 1, 'aa': 2}}
        -> '… domain.zz: Unexpected …; domain.aa: Unexpected …'
      {'root': …, 'domain': {…, 'aa': 2, 'zz': 1}}
        -> '… domain.aa: Unexpected …; domain.zz: Unexpected …'

    Sorting on the whole ``loc`` as plain strings would fix that arm and quietly
    break another: nested *declared* fields would come out alphabetically instead
    of in declaration order. Hence the per-level rank rather than the raw key.

    The key is a tuple of same-shaped ``(kind, index, name)`` triples, so keys of
    different depths compare element-wise and then by length — a prefix sorts
    before what extends it, and a top-level error can never tie with a nested one.
    """

    def key(error: dict[str, Any]) -> tuple[tuple[int, int, str], ...]:
        ranks: list[tuple[int, int, str]] = []
        container: Any = model
        for item in error.get("loc") or ():
            if isinstance(item, int):
                # A sequence index: already a declaration-independent position.
                # The element type is not resolved, so anything below it falls
                # back to name ordering.
                ranks.append((0, item, ""))
                container = None
                continue
            name = str(item)
            order = _field_order(container)
            if name in order:
                ranks.append((0, order[name], ""))
                container = _child_container(container, name)
            else:
                ranks.append((1, 0, name))
                container = None
        return tuple(ranks)

    return key
