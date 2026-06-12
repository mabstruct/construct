"""CapabilityRecord model and CapabilityRegistry class."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic import BaseModel


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
