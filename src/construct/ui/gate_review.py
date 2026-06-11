"""Gate Review panel per D-03 panel 2 and PRD §10.3 + §8.6.

Two tabs:
  1. Ask.Domain Q&A Review — review pending ask.domain results with approve/reject
  2. Bridge Candidates Review — review bridge candidates with approve/reject

All capability executions go through the capability registry per D-04.
Gate review only approves/rejects — it doesn't edit workspace files outside the registry.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from construct.capabilities.catalog import get_registry


# ---------------------------------------------------------------------------
# Event logging helpers
# ---------------------------------------------------------------------------


def _log_gate_event(
    workspace: Path,
    action: str,
    gate_id: str,
    detail: str | None = None,
) -> None:
    """Append a gate review event to log/events.jsonl.

    Per PRD §8.6 gate review protocol:
      - Approve → log gate_review_approved event
      - Reject → log gate_review_rejected event
    """
    from construct.services.event_log import append_event
    from construct.schemas.config import EventAgent, EventResult

    result = EventResult.success if "approved" in action else EventResult.success
    append_event(
        workspace,
        EventAgent.construct,
        action,
        target=gate_id,
        detail=detail,
        result=result,
    )


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "gate_queue" not in st.session_state:
    st.session_state.gate_queue = []

if "reviewed_bridges" not in st.session_state:
    st.session_state.reviewed_bridges = set()


# ---------------------------------------------------------------------------
# Page title
# ---------------------------------------------------------------------------

st.title("Gate Review")
st.caption("Review pending ask.domain Q&A results and bridge candidates per PRD §10.3.")

# Get workspace path from session state (set by sidebar in streamlit_app.py)
workspace_path = st.session_state.get("workspace_path", "")
if not workspace_path:
    st.info("Set a workspace path in the sidebar to see gate review items.")
    st.stop()

workspace = Path(workspace_path).resolve()
if not workspace.exists():
    st.error(f"Workspace not found at: {workspace}")
    st.stop()

# ── Tabs ──
tab_qa, tab_bridges = st.tabs(["Ask.Domain Q&A", "Bridge Candidates"])


# ===========================================================================
# Tab 1: Ask.Domain Q&A Review
# ===========================================================================

with tab_qa:
    st.subheader("Pending Q&A Reviews")

    pending = [r for r in st.session_state.gate_queue if r.get("review_status") == "pending"]

    if not pending:
        st.info("No pending gate review items. Run ask.domain from the Capability Runner to create review items.")

        # Show completed items if any
        completed = [r for r in st.session_state.gate_queue if r.get("review_status") != "pending"]
        if completed:
            with st.expander("Previously Reviewed", expanded=False):
                for item in completed:
                    status = item.get("review_status", "unknown")
                    emoji = "✅" if status == "approved" else "❌" if status == "rejected" else "⏳"
                    st.caption(
                        f"{emoji} **{item.get('question', 'Unknown question')}** "
                        f"— {status}"
                    )

    for idx, item in enumerate(pending):
        st.divider()
        st.markdown(f"### Q: {item.get('question', 'Unknown question')}")

        # Answer
        answer = item.get("answer", "")
        if answer:
            st.markdown("**Answer:**")
            st.markdown(answer)
        else:
            st.warning("No answer generated.")

        # Citations
        citations = item.get("citations", [])
        if citations:
            st.markdown("**Citations:**")
            for c_idx, citation in enumerate(citations):
                title = citation.get("title", "Untitled")
                card_id = citation.get("card_id", "")
                snippet = citation.get("snippet", "")[:200]

                with st.expander(f"Citation: {title}"):
                    st.markdown(f"**Card ID:** `{card_id}`")
                    st.markdown(f"**Snippet:** {snippet}")
                    card_path = workspace / "cards" / f"{card_id}.md"
                    if card_path.exists():
                        st.markdown(f"**Path:** `{card_path}`")

        # Provider/model metadata
        gate_meta = item.get("gate", {})
        if gate_meta:
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            meta_col1.caption(f"**Model:** {gate_meta.get('model', 'N/A')}")
            meta_col2.caption(f"**Provider:** {gate_meta.get('provider', 'N/A')}")
            meta_col3.caption(f"**Confidence:** {item.get('confidence', 'N/A')}")

        # Approve / Reject buttons
        col_approve, col_reject = st.columns(2)

        approve_key = f"approve_qa_{idx}"
        reject_key = f"reject_qa_{idx}"

        if col_approve.button("✅ Approve", key=approve_key):
            st.session_state.gate_queue[idx]["review_status"] = "approved"
            _log_gate_event(
                workspace,
                "gate_review_approved",
                f"ask.domain:{item.get('question', 'unknown')[:50]}",
                detail=f"Approved answer for: {item.get('question', '')[:100]}",
            )
            st.rerun()

        if col_reject.button("❌ Reject", key=reject_key):
            st.session_state.gate_queue[idx]["review_status"] = "rejected"
            _log_gate_event(
                workspace,
                "gate_review_rejected",
                f"ask.domain:{item.get('question', 'unknown')[:50]}",
                detail=f"Rejected answer for: {item.get('question', '')[:100]}",
            )
            st.rerun()


# ===========================================================================
# Tab 2: Bridge Candidates Review
# ===========================================================================

with tab_bridges:
    st.subheader("Bridge Candidates")

    # Read bridge candidates from log/bridge-candidates.json
    bridges_path = workspace / "log" / "bridge-candidates.json"
    if not bridges_path.exists():
        st.info("No bridge candidates found. Run bridge.detect from the Capability Runner first.")
    else:
        try:
            bridge_data = json.loads(bridges_path.read_text(encoding="utf-8"))
            bridges = bridge_data.get("bridges", [])
        except (json.JSONDecodeError, OSError):
            st.error("Could not parse bridge-candidates.json.")
            bridges = []

        if not bridges:
            st.info("No bridge candidates available.")
        else:
            # Show summary counts
            summary = bridge_data.get("summary", {})
            totals = summary.get("totals", {})
            sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
            sum_col1.metric("Total Candidates", len(bridges))
            sum_col2.metric("Confirmed (L1)", totals.get("confirmed", 0))
            sum_col3.metric("Strong", totals.get("strong_candidates", 0))
            sum_col4.metric("Medium", totals.get("medium_candidates", 0))

            # Group by confidence band
            bands = {"strong": [], "medium": [], "weak": []}
            for bridge in bridges:
                band = bridge.get("band", "weak")
                if band in bands:
                    bands[band].append(bridge)
                else:
                    bands["weak"].append(bridge)

            # Display candidates grouped by band
            for band_name, band_label in [("strong", "Strong Candidates"), ("medium", "Medium Candidates"), ("weak", "Weak Candidates")]:
                band_items = bands[band_name]
                if not band_items:
                    continue

                with st.expander(f"{band_label} ({len(band_items)})", expanded=(band_name == "strong")):
                    for b_idx, bridge in enumerate(band_items):
                        from_card = bridge.get("from", {})
                        to_card = bridge.get("to", {})

                        candidate_key = f"{from_card.get('card_id', '')}--{to_card.get('card_id', '')}"
                        already_reviewed = candidate_key in st.session_state.reviewed_bridges

                        if already_reviewed:
                            st.caption(f"~~{from_card.get('title', '?')} → {to_card.get('title', '?')}~~ *(reviewed)*")
                            continue

                        bridge_col1, bridge_col2 = st.columns([3, 1])
                        with bridge_col1:
                            st.markdown(
                                f"**{from_card.get('title', '?')}** "
                                f"(`{from_card.get('domain', '?')}`) → "
                                f"**{to_card.get('title', '?')}** "
                                f"(`{to_card.get('domain', '?')}`)"
                            )
                            st.caption(
                                f"**Bridge type:** Structural={bridge.get('l1_structural', False)}, "
                                f"Score: {bridge.get('score', 0)}, "
                                f"L3: {bridge.get('l3_verdict', 'N/A')}"
                            )
                            if bridge.get("l3_reasoning"):
                                st.caption(f"**Rationale:** {bridge['l3_reasoning']}")
                            if bridge.get("l2_shared_categories"):
                                st.caption(f"**Shared categories:** {', '.join(bridge['l2_shared_categories'])}")

                        with bridge_col2:
                            approve_b_key = f"approve_bridge_{band_name}_{b_idx}"
                            reject_b_key = f"reject_bridge_{band_name}_{b_idx}"

                            if st.button("✅ Approve", key=approve_b_key):
                                # Invoke knowledge.connection.add via registry per D-04
                                try:
                                    from construct.schemas.workspace import ConnectionAuthor, ConnectionType

                                    registry = get_registry()
                                    conn_cap = registry.get("knowledge.connection.add")
                                    result = conn_cap.handler(
                                        workspace,
                                        from_card.get("card_id", ""),
                                        to_card.get("card_id", ""),
                                        ConnectionType.parallels,
                                        note=f"Bridge candidate approved from gate review. "
                                             f"Score: {bridge.get('score', 0)}",
                                        created_by=ConnectionAuthor.construct,
                                    )
                                    if result.success:
                                        st.success("Connection created!")
                                        st.session_state.reviewed_bridges.add(candidate_key)
                                        _log_gate_event(
                                            workspace,
                                            "bridge_approved",
                                            candidate_key,
                                            detail=f"Approved bridge: {from_card.get('card_id', '')} → {to_card.get('card_id', '')}",
                                        )
                                        st.rerun()
                                    else:
                                        st.error(f"Could not create connection: {result.message}")
                                except Exception as exc:
                                    st.error(f"Error creating connection: {exc}")

                            if st.button("❌ Reject", key=reject_b_key):
                                st.session_state.reviewed_bridges.add(candidate_key)
                                _log_gate_event(
                                    workspace,
                                    "bridge_rejected",
                                    candidate_key,
                                    detail=f"Rejected bridge: {from_card.get('card_id', '')} → {to_card.get('card_id', '')}",
                                )
                                st.rerun()

                        st.divider()
