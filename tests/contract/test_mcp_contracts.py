"""Contract tests for MCP server tool definitions.

Two layers of contract coverage live here:

1. **Schema-shape tests** assert the advertised MCP tool definitions exist and
   expose the right JSON-Schema surface. These never invoke a handler — which is
   precisely the CI blind spot that let RT-03 (handlers raising TypeError on their
   own advertised kwargs) ship undetected.

2. **Handler-invocation tests** (D-08.1) close that blind spot: every MCP tool
   handler is invoked with schema-shaped kwargs and must NOT raise TypeError.
   This is the structural mechanism preventing RT-03 recurrence — if Task 1's
   adapter shims are reverted, these tests fail with a TypeError-driven assertion.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from construct.capabilities.catalog import get_registry

FIXTURE_WS = Path(__file__).resolve().parents[2] / "test-ws" / "my-construct"


# ---------------------------------------------------------------------------
# Schema-shape tests (existing — preserved)
# ---------------------------------------------------------------------------


def test_mcp_tools_match_registry() -> None:
    registry = get_registry()
    mcp_tools = registry.list_mcp_tools()
    assert len(mcp_tools) >= 4
    for tool in mcp_tools:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
        assert "properties" in tool["input_schema"]


def test_mcp_tool_construct_validate_schema() -> None:
    registry = get_registry()
    mcp_tools = registry.list_mcp_tools()
    validate_tool = next(t for t in mcp_tools if t["name"] == "construct_validate")
    schema = validate_tool["input_schema"]
    assert "path" in schema["properties"]
    assert schema["properties"]["path"]["type"] == "string"


def test_mcp_tool_count() -> None:
    registry = get_registry()
    mcp_tools = registry.list_mcp_tools()
    tool_names = {t["name"] for t in mcp_tools}
    expected = {
        "construct_validate",
        "construct_create_card",
        "construct_edit_card",
        "construct_add_connection",
        "construct_graph_status",
        "construct_views_generate_data",
        "construct_workflow_run",
        "construct_ingest_source",
        "construct_help_suggest",
        "construct_ask_domain",
        "construct_bridge_detect",
    }
    assert tool_names == expected


# ---------------------------------------------------------------------------
# Handler-invocation tests (D-08.1 — RT-03 / ING-05 regression gate)
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path: Path) -> str:
    """A throwaway copy of the canonical fixture so write tools cannot mutate it."""
    dest = tmp_path / "my-construct"
    shutil.copytree(FIXTURE_WS, dest)
    return str(dest)


def _payload_for(tool_name: str, ws: str) -> dict:
    """A representative valid kwargs payload (advertised schema fields) per tool."""
    payloads: dict[str, dict] = {
        "construct_validate": {"path": ws},
        "construct_create_card": {
            "workspace": ws,
            "title": "Contract Test Card",
            "epistemic_type": "finding",
            "domains": ["cosmology"],
            "confidence": 3,
            "source_tier": 4,
            "summary": "Contract summary.",
        },
        "construct_edit_card": {
            "card_id": "contract-test-card",
            "workspace": ws,
            "title": "Contract Test Card Edited",
            "summary": "Edited contract summary.",
        },
        "construct_add_connection": {
            "from_id": "contract-test-card",
            "to_id": "contract-test-card",
            "conn_type": "supports",
            "workspace": ws,
        },
        "construct_graph_status": {"workspace": ws},
        "construct_views_generate_data": {"workspace": ws},
        "construct_workflow_run": {"workspace": ws},
        "construct_ingest_source": {"workspace": ws, "source": "A contract-test note"},
        "construct_help_suggest": {"workspace": ws},
        "construct_ask_domain": {"workspace_path": ws, "domain_id": "cosmology", "question": "What is known?"},
        "construct_bridge_detect": {"workspace_path": ws},
    }
    return payloads[tool_name]


def test_every_mcp_handler_invokes_without_type_error(workspace: str) -> None:
    """Invoking each MCP tool handler with its advertised schema fields must not
    raise TypeError. This is the gate that would have caught RT-03."""
    registry = get_registry()
    for tool in registry.list_mcp_tools():
        capability = registry.get_by_mcp_name(tool["name"])
        payload = _payload_for(tool["name"], workspace)
        try:
            capability.handler(**payload)
        except TypeError as exc:  # pragma: no cover - failure path
            pytest.fail(
                f"MCP tool '{tool['name']}' raised TypeError on its advertised "
                f"schema fields {sorted(payload)}: {exc}"
            )
        except Exception:
            # Non-TypeError runtime outcomes (e.g. ask.domain needing an LLM
            # provider, or a validation-failure result) are out of scope: this
            # gate asserts ONLY that the shim layer accepts the advertised
            # schema fields without a signature mismatch (TypeError).
            pass


@pytest.mark.parametrize(
    "tool_name",
    [
        "construct_validate",
        "construct_create_card",
        "construct_edit_card",
        "construct_add_connection",
        "construct_ingest_source",
    ],
)
def test_previously_broken_tools_return_result(tool_name: str, workspace: str) -> None:
    """The five RT-03 tools must each return a result object (not raise TypeError)."""
    registry = get_registry()
    capability = registry.get_by_mcp_name(tool_name)
    # create the card the edit/connection payloads reference, so they exercise the
    # success path rather than a missing-card validation failure.
    create = registry.get_by_mcp_name("construct_create_card")
    create.handler(**_payload_for("construct_create_card", workspace))

    result = capability.handler(**_payload_for(tool_name, workspace))
    assert result is not None
    assert not isinstance(result, TypeError)
    # OperationResult exposes 'success'; ValidationReport exposes 'ok'.
    assert hasattr(result, "success") or hasattr(result, "ok")


def test_graph_status_returns_health_report(workspace: str) -> None:
    """ING-05: graph.status returns the real cards/connections/domains report."""
    registry = get_registry()
    cap = registry.get_by_mcp_name("construct_graph_status")
    result = cap.handler(workspace=workspace)
    assert result.success, result.message
    assert {"cards", "connections", "domains"}.issubset(result.data.keys())


def test_graph_status_accepts_positional_and_keyword(workspace: str) -> None:
    """help.py calls graph.status positionally; MCP calls it by keyword."""
    cap = get_registry().get("graph.status")
    assert cap.handler(workspace).success
    assert cap.handler(workspace=workspace).success


def test_help_suggest_surfaces_graph_health(workspace: str) -> None:
    """ING-05: help.suggest surfaces graph health. The 'graph_status' key is
    populated ONLY when graph.status succeeds, so its presence machine-proves the
    swallow at help.py:124-130 is fixed."""
    cap = get_registry().get("help.suggest")
    result = cap.handler(workspace)
    assert result.success, result.message
    assert "graph_status" in result.data, (
        "help.suggest did not surface graph_status — graph.status result was swallowed"
    )
