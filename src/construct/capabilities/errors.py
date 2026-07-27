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

from pydantic import ValidationError


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
        cls, cap_id: str, exc: ValidationError
    ) -> CapabilityInputError:
        """Build the seam's reason string from a pydantic ``ValidationError``.

        T-18-10: the reason is assembled from field locations and pydantic's own
        constraint messages only. ``include_input=False`` and
        ``include_context=False`` keep the caller's submitted values — which may
        be filesystem paths or other sensitive payload content — out of a string
        that is rendered straight back to an MCP client.

        Pydantic reports errors in a deterministic order for a given model and
        payload, so both surfaces build a byte-identical reason.
        """
        parts = [
            f"{'.'.join(str(item) for item in error['loc']) or '<root>'}: {error['msg']}"
            for error in exc.errors(
                include_url=False, include_input=False, include_context=False
            )
        ]
        return cls(cap_id, "; ".join(parts))
