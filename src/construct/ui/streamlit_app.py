"""Local ops dashboard — run with: streamlit run src/construct/ui/streamlit_app.py

Per ADV-04 and D-03: Streamlit app with 3 panels:
  - Dashboard: graph health (card/connection/domain counts, recent events)
  - Capability Runner: list & execute capabilities from registry (dynamic form)
  - Gate Review: review ask.domain Q&A results and bridge candidates

All capability executions go through the capability registry per D-04.
No SOT writes from the UI.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="CONSTRUCT Ops", layout="wide")

# Sidebar config (per PRD §10 sidebar spec)
with st.sidebar:
    st.header("CONSTRUCT Ops")
    st.caption("Local ops dashboard — not a product UI")

    workspace_path = st.text_input("Workspace path", value="test-ws/my-construct", key="workspace_path_widget")
    install_root = st.text_input("Install root", value=".", key="install_root_widget")
    llm_config = st.text_input("LLM config path", value=".construct/model-routing.yaml", key="llm_config_widget")
    provider_override = st.selectbox("Provider override", ["", "anthropic", "openai", "ollama"], key="provider_override_widget")

    # Store in session state for page access
    st.session_state["workspace_path"] = workspace_path
    st.session_state["install_root"] = install_root
    st.session_state["llm_config"] = llm_config
    st.session_state["provider_override"] = provider_override

    st.divider()
    st.caption("All executions go through capability registry.")
    st.caption("No SOT writes.")

# Page routing (per PRD §10.1)
home = st.Page("dashboard.py", title="Dashboard", icon="📊")
runner = st.Page("capability_runner.py", title="Capability Runner", icon="⚡")
gates = st.Page("gate_review.py", title="Gate Review", icon="🔍")

pg = st.navigation([home, runner, gates])
pg.run()
