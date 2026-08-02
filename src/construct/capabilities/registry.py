"""CapabilityRecord model and CapabilityRegistry class."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic import BaseModel, ValidationError

from construct.capabilities.errors import (
    CapabilityInputError,
    CapabilityNotFoundError,
)
from construct.capabilities.workspaces import resolve_payload_workspace


InputModel = type[BaseModel]
OutputModel = type[BaseModel]


@dataclass
class CapabilityRecord:
    id: str
    name: str
    description: str
    input_model: InputModel
    output_model: OutputModel
    handler: Callable[..., Any]
    cli_name: Optional[str] = None
    mcp_tool_name: Optional[str] = None


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityRecord] = {}

    def register(self, record: CapabilityRecord) -> None:
        if record.id in self._capabilities:
            raise ValueError(f"Capability '{record.id}' is already registered")
        self._capabilities[record.id] = record

    def get(self, cap_id: str) -> CapabilityRecord:
        if cap_id not in self._capabilities:
            available = ", ".join(sorted(self._capabilities))
            raise KeyError(f"Capability '{cap_id}' not found. Available: {available}")
        return self._capabilities[cap_id]

    def invoke(self, cap_id: str, payload: dict[str, Any]) -> Any:
        """Resolve, validate, then run a capability — the one seam all surfaces share.

        This is the GOV-01 contract. Three steps, in this order, with no surface
        allowed to skip any of them:

        1. resolve the record (``get``), converting its ``KeyError`` to a typed error;
        2. validate ``payload`` against the capability's declared ``input_model``;
        3. call the handler with the *validated* model's fields.

        Step 2 is what was missing. ``input_model`` was computed into a JSON Schema
        for MCP discovery and then discarded, so ``extra="forbid"`` never ran on any
        real payload (WR-02). Routing every surface through here is what makes a
        model's declared contract actually enforced rather than merely advertised.

        There is deliberately no strict/lenient flag, no allowlist argument, and no
        per-surface exception (D-05): a knob here would let one surface diverge from
        another, which is the fork this seam exists to prevent.

        Step 1.5 is D-01's ``workspace_id`` resolution, inserted between the
        record lookup and the model validation. It is **behaviour applied
        uniformly to every surface**, not a knob: ``invoke``'s signature is
        untouched (``test_seam_has_no_leniency_knob`` pins it to
        ``{self, cap_id, payload}``), the install root it resolves against is
        process-level launch context every surface shares (D-09), and a payload
        carrying no ``workspace_id`` passes through byte-for-byte. Placing it
        here rather than in the HTTP adapter is the whole point: a browser must
        not be the only caller that can address a workspace by id, and an
        adapter-side resolver would make the id an HTTP-only dialect — the
        cross-surface vocabulary fork HTTP-02 forbids.
        """
        try:
            cap = self.get(cap_id)
        except KeyError as exc:
            raise CapabilityNotFoundError(cap_id, sorted(self._capabilities)) from exc

        payload = resolve_payload_workspace(cap_id, payload)

        try:
            model = cap.input_model.model_validate(payload)
        except ValidationError as exc:
            # The model is handed over so the reason string can be ordered by
            # field declaration rather than by payload key insertion — otherwise
            # two surfaces sending the same logical payload with keys in
            # different orders receive two different reasons for one rejection.
            raise CapabilityInputError.from_validation_error(
                cap_id, exc, cap.input_model
            ) from exc

        return cap.handler(**model.model_dump())

    def list(self) -> list[CapabilityRecord]:
        return sorted(self._capabilities.values(), key=lambda c: c.id)

    def list_by_cli(self, cli_name: str) -> list[CapabilityRecord]:
        return [c for c in self._capabilities.values() if c.cli_name == cli_name]

    def get_by_mcp_name(self, name: str) -> CapabilityRecord:
        for cap in self._capabilities.values():
            if cap.mcp_tool_name == name:
                return cap
        available = ", ".join(sorted(c.mcp_tool_name for c in self._capabilities.values() if c.mcp_tool_name))
        raise KeyError(f"MCP tool '{name}' not found. Available: {available}")

    def list_mcp_tools(self) -> list[dict]:
        tools: list[dict] = []
        for cap in self._capabilities.values():
            if cap.mcp_tool_name is None:
                continue
            tools.append({
                "name": cap.mcp_tool_name,
                "description": cap.description,
                "input_schema": cap.input_model.model_json_schema(),
            })
        return tools

    def __len__(self) -> int:
        return len(self._capabilities)
