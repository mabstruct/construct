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
from tests.search.conftest import overlay_mock_search_config

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
        # 18-03 / D-02: registration is what puts `views validate` on this
        # surface at all — it was CLI-only while its body lived in cli.py.
        "construct_views_validate_data",
        "construct_ingest_source",
        "construct_help_suggest",
        "construct_ask_domain",
        "construct_bridge_detect",
        "construct_research_search",
        "construct_research_score",
        "construct_research_run",
        "construct_research_review",
        "construct_research_inspect",
        "construct_curation_run",
        "construct_curation_inspect",
        "construct_curation_review",
        "construct_card_evaluate",
        "construct_daily_run",
        "construct_daily_inspect",
        "construct_list_cards",
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
    overlay_mock_search_config(dest)
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
        # D-05: this contract is install-root scoped, so the payload names the
        # workspace's *parent* — discover_workspaces scans children, and handing
        # it the workspace itself would discover nothing.
        "construct_views_generate_data": {"install_root": str(Path(ws).parent)},
        # 18-03 / D-02: same scoping and the same field spelling as its generate
        # sibling — the two views capabilities present one vocabulary.
        "construct_views_validate_data": {"install_root": str(Path(ws).parent)},
        "construct_ingest_source": {"workspace": ws, "source": "A contract-test note"},
        "construct_help_suggest": {"workspace": ws},
        "construct_ask_domain": {"workspace_path": ws, "domain_id": "cosmology", "question": "What is known?"},
        "construct_bridge_detect": {"workspace_path": ws},
        "construct_research_search": {
            "workspace_path": ws,
            "query": "contract test query",
        },
        "construct_research_score": {
            "workspace_path": ws,
            "results": [],
        },
        "construct_research_run": {"workspace_path": ws},
        "construct_research_review": {"workspace_path": ws, "run_id": "no-such-run"},
        "construct_research_inspect": {"workspace_path": ws, "run_id": "no-such-run"},
        "construct_curation_run": {"workspace_path": ws},
        "construct_curation_inspect": {"workspace_path": ws, "run_id": "no-such-run"},
        "construct_curation_review": {"workspace_path": ws, "run_id": "no-such-run"},
        "construct_card_evaluate": {"workspace_path": ws},
        "construct_daily_run": {"workspace_path": ws},
        "construct_daily_inspect": {"workspace_path": ws, "run_id": "no-such-run"},
        "construct_list_cards": {"workspace": ws},
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


def test_graph_status_is_keyword_only(workspace: str) -> None:
    """The inverse of what stood here, and the inversion is the point.

    This test used to be ``test_graph_status_accepts_positional_and_keyword`` and
    asserted that the handler bound *both* call forms, because ``services/help.py``
    invoked it positionally while MCP invoked it by keyword. That dual binding was
    an accommodation for one internal caller, and GOV-01 (plan 18-03) removed the
    caller: ``help.py`` now dispatches through ``registry.invoke``.

    So the accommodation is gone and a positional call is a ``TypeError``. Keeping
    the old assertion would have kept a second, unvalidated way into
    ``graph_status`` alive purely because a test demanded it.
    """
    cap = get_registry().get("graph.status")

    assert cap.handler(workspace=workspace).success

    with pytest.raises(TypeError):
        cap.handler(workspace)


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


# ---------------------------------------------------------------------------
# WR-10: the never-raise / never-leak property, which the TypeError gate misses
# ---------------------------------------------------------------------------

# ``test_every_mcp_handler_invokes_without_type_error`` catches TypeError and then
# swallows everything else. That blanket clause is why CR-02 shipped: the views
# handler raising FileNotFoundError straight through the MCP boundary passed the
# gate. Its narrow scope ("only signature mismatch") is defensible, but nothing
# asserted the property the sanitizer shims in catalog.py exist to provide.


def test_views_handler_returns_a_result_for_an_invalid_install_root(tmp_path: Path) -> None:
    """The views handler must report, not raise, on a path that is not an install root."""
    from construct.services.knowledge import OperationResult

    capability = get_registry().get_by_mcp_name("construct_views_generate_data")
    bogus = str(tmp_path / "does" / "not" / "exist")

    result = capability.handler(install_root=bogus)

    assert isinstance(result, OperationResult)
    assert result.success is False
    # Never echo the path back through the MCP error channel.
    assert bogus not in result.message
    assert all(bogus not in error.reason for error in result.errors)


def test_views_contract_payload_does_not_generate_into_the_fixture_tree(
    workspace: str,
) -> None:
    """The shim-signature gate must not have a full generation as a side effect.

    ``_payload_for`` hands ``construct_views_generate_data`` the workspace's parent
    as its install root. That parent is a tmp_path copy rather than the checked-in
    fixture, and since CR-03 it carries no AGENTS.md, so the handler refuses it
    before the generator can create anything. This pins both facts.
    """
    parent = Path(workspace).parent
    payload = _payload_for("construct_views_generate_data", workspace)
    assert payload["install_root"] == str(parent)

    get_registry().get_by_mcp_name("construct_views_generate_data").handler(**payload)

    assert not (parent / "views").exists(), (
        "a contract test performed a real build as a side effect"
    )


def _invalid_path_payload(tool_name: str, bogus: str) -> dict:
    """The advertised payload with every path-shaped field pointed at a bogus path."""
    return {
        key: (bogus if key in {"path", "workspace", "workspace_path", "install_root"} else value)
        for key, value in _payload_for(tool_name, bogus).items()
    }


def test_mcp_handlers_report_rather_than_raise_on_an_invalid_path(tmp_path: Path) -> None:
    """The never-raise property the sanitizer shims in catalog.py exist to provide.

    The TypeError gate above cannot see this: its ``except Exception: pass``
    swallows exactly the failures that reach an MCP client as raw exception text.
    That is why CR-02 shipped -- the views handler raising FileNotFoundError
    straight through the boundary passed that gate.

    Each handler gets its OWN bogus path. Sharing one would let an earlier
    write-capable handler create the directory and change what the later ones see,
    so the test would be asserting a property of the iteration order rather than of
    the handlers.
    """
    registry = get_registry()

    raised: dict[str, str] = {}
    for index, tool in enumerate(registry.list_mcp_tools()):
        name = tool["name"]
        bogus = str(tmp_path / f"not-a-workspace-{index}")
        try:
            registry.get_by_mcp_name(name).handler(**_invalid_path_payload(name, bogus))
        except Exception as exc:  # noqa: BLE001 — the property under test
            raised[name] = type(exc).__name__

    assert not raised, f"MCP handlers raised through the boundary: {raised}"
