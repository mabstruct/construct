"""Dashboard — Graph Health panel per D-03 panel 1.

Reads workspace files directly for graph health stats:
  - Total cards, total connections, total domains
  - Card counts by domain
  - Connection counts by type
  - Recent events from log/events.jsonl

No capability invocations for simple stats — all readings go through
file I/O to the workspace SOT.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from construct.schemas.card import parse_card_markdown
from construct.schemas.config import DomainsRegistry
from construct.schemas.workspace import ConnectionsFile


def _read_events_log(workspace: Path, limit: int = 20) -> list[dict]:
    """Read the last N events from log/events.jsonl."""
    events_path = workspace / "log" / "events.jsonl"
    if not events_path.exists():
        return []
    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    events = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events[::-1]  # Most recent first


def _read_domains(workspace: Path) -> DomainsRegistry | None:
    """Load domains.yaml, returning None if not found."""
    from ruamel.yaml import YAML

    domains_path = workspace / "domains.yaml"
    if not domains_path.exists():
        return None
    try:
        yaml = YAML(typ="safe")
        data = yaml.load(domains_path.read_text(encoding="utf-8"))
        return DomainsRegistry(**data)
    except Exception:
        return None


def _read_connections(workspace: Path) -> ConnectionsFile | None:
    """Load connections.json, returning None if not found."""
    conn_path = workspace / "connections.json"
    if not conn_path.exists():
        return None
    try:
        data = json.loads(conn_path.read_text(encoding="utf-8"))
        return ConnectionsFile(**data)
    except Exception:
        return None


def _count_cards_by_domain(workspace: Path) -> dict[str, int]:
    """Count cards by domain from cards/*.md files."""
    cards_dir = workspace / "cards"
    if not cards_dir.exists():
        return {}
    domain_counts: dict[str, int] = {}
    for card_path in sorted(cards_dir.glob("*.md")):
        try:
            markdown = card_path.read_text(encoding="utf-8")
            card, _ = parse_card_markdown(markdown, source_path=card_path)
            for domain in card.domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        except Exception:
            domain_counts["_unparseable"] = domain_counts.get("_unparseable", 0) + 1
    return domain_counts


st.title("Dashboard — Graph Health")

# Get workspace path from session state (set by sidebar in streamlit_app.py)
workspace_path = st.session_state.get("workspace_path", "")
if not workspace_path:
    st.info("Set a workspace path in the sidebar to see graph health.")
    st.stop()

workspace = Path(workspace_path).resolve()
if not workspace.exists() or not (workspace / "cards").exists():
    st.error(f"Workspace not found at: {workspace}")
    st.stop()

# ── Key metrics row ──
col1, col2, col3 = st.columns(3)

# Count cards
cards_dir = workspace / "cards"
total_cards = len(list(cards_dir.glob("*.md"))) if cards_dir.exists() else 0
col1.metric("Total Cards", total_cards)

# Count connections
connections_file = _read_connections(workspace)
total_connections = len(connections_file.connections) if connections_file else 0
col2.metric("Total Connections", total_connections)

# Count domains
domains_file = _read_domains(workspace)
total_domains = len(domains_file.domains) if domains_file else 0
col3.metric("Total Domains", total_domains)

# ── Cards by domain ──
st.subheader("Cards by Domain")
domain_counts = _count_cards_by_domain(workspace)
if domain_counts:
    domain_data = [{"Domain": d, "Count": c} for d, c in sorted(domain_counts.items(), key=lambda x: -x[1])]
    st.dataframe(domain_data, use_container_width=True)
else:
    st.caption("No cards found.")

# ── Connections by type ──
st.subheader("Connections by Type")
if connections_file and connections_file.connections:
    type_counts: dict[str, int] = {}
    for conn in connections_file.connections:
        type_counts[conn.type.value] = type_counts.get(conn.type.value, 0) + 1
    conn_data = [{"Type": t, "Count": c} for t, c in sorted(type_counts.items(), key=lambda x: -x[1])]
    st.dataframe(conn_data, use_container_width=True)
else:
    st.caption("No connections found.")

# ── Recent events ──
st.subheader("Recent Events")
events = _read_events_log(workspace)
if events:
    event_data = [
        {
            "Timestamp": e.get("ts", ""),
            "Action": e.get("action", ""),
            "Agent": e.get("agent", ""),
            "Target": e.get("target", ""),
            "Result": e.get("result", ""),
        }
        for e in events
    ]
    st.dataframe(event_data, use_container_width=True)
else:
    st.caption("No events found in log/events.jsonl.")
