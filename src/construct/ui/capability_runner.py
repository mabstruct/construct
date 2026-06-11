"""Capability Runner panel per D-03 panel 3 and PRD §10.2.

Lists all registered capabilities from the capability registry, renders
dynamic form fields from Pydantic model JSON Schema, and invokes handlers
in-process through the registry per D-04.
"""
from __future__ import annotations

import json
import time
from typing import Any

import streamlit as st

from construct.capabilities.catalog import get_registry
from construct.capabilities.registry import CapabilityRecord


def _get_field_type(field_schema: dict) -> str:
    """Determine the Streamlit-friendly field type from a JSON Schema property."""
    schema_type = field_schema.get("type", "string")
    schema_format = field_schema.get("format", "")
    enum_values = field_schema.get("enum")
    one_of = field_schema.get("oneOf")

    if enum_values:
        return "enum"
    if one_of:
        # Check for optional fields with null: [{"type": "string"}, {"type": "null"}]
        types = [o.get("type") for o in one_of if o.get("type") != "null"]
        if types:
            return types[0]
        return "string"
    if schema_format == "path":
        return "path"
    if schema_type == "integer" or schema_type == "number":
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "array":
        return "array"
    return "string"


def _render_form_fields(schema: dict) -> dict[str, Any]:
    """Render Streamlit form fields dynamically from a JSON Schema.

    Maps Pydantic field types to Streamlit widgets:
      - str → st.text_input
      - int → st.number_input
      - bool → st.toggle
      - Path → st.text_input
      - list[str] → st.text_area (comma-separated)
      - enum → st.selectbox
    """
    inputs: dict[str, Any] = {}
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    if not properties:
        st.info("This capability requires no inputs.")
        return inputs

    st.caption("Fill in the inputs below:")
    st.divider()

    for field_name, field_schema in properties.items():
        field_type = _get_field_type(field_schema)
        title = field_schema.get("title", field_name)
        description = field_schema.get("description", "")
        label = f"{title}{' *' if field_name in required_fields else ''}"

        help_text = description or (f"Field: {field_name}")

        # Get default value
        default = field_schema.get("default")
        enum_values = field_schema.get("enum")

        if field_type == "boolean":
            inputs[field_name] = st.toggle(label, value=bool(default), help=help_text)

        elif field_type == "number":
            min_v = field_schema.get("minimum")
            max_v = field_schema.get("maximum")
            step = 1 if field_schema.get("type") == "integer" else 0.1
            int_val = int(default) if default is not None else 0
            inputs[field_name] = st.number_input(
                label, value=int_val, step=step,
                min_value=min_v, max_value=max_v,
                help=help_text,
            )

        elif field_type == "enum" and enum_values:
            default_idx = 0
            if default is not None and default in enum_values:
                default_idx = enum_values.index(default)
            inputs[field_name] = st.selectbox(
                label, options=enum_values, index=default_idx, help=help_text,
            )

        elif field_type == "array":
            default_str = ", ".join(default) if default else ""
            value = st.text_area(
                label, value=default_str,
                help=f"{help_text} (comma-separated)",
            )
            inputs[field_name] = [v.strip() for v in value.split(",") if v.strip()]

        else:
            # Default: text input for strings, paths, etc.
            str_default = str(default) if default is not None else ""
            if field_name == "question" or "question" in field_name.lower():
                inputs[field_name] = st.text_area(label, value=str_default, help=help_text)
            else:
                inputs[field_name] = st.text_input(label, value=str_default, help=help_text)

    return inputs


def _invoke_handler(cap: CapabilityRecord, inputs: dict) -> tuple[bool, Any, float]:
    """Invoke a capability handler with the provided inputs.

    All capability executions go through the capability registry per D-04.

    Returns:
        Tuple of (success, result_or_error, duration_seconds).
    """
    start = time.time()
    try:
        result = cap.handler(**inputs)
        elapsed = time.time() - start
        return True, result, elapsed
    except TypeError as exc:
        elapsed = time.time() - start
        return False, {
            "error": f"Handler signature mismatch: {exc}",
            "hint": "Some capability handlers require specific positional arguments "
                    "and cannot accept **kwargs from the form yet.",
        }, elapsed
    except Exception as exc:
        elapsed = time.time() - start
        return False, {"error": str(exc)}, elapsed


def _result_to_dict(result: Any) -> dict:
    """Convert an OperationResult or arbitrary result to a JSON-serializable dict."""
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if hasattr(result, "__dataclass_fields__"):
        # Dataclass serialization
        data = {}
        for field_name in result.__dataclass_fields__:
            val = getattr(result, field_name)
            if hasattr(val, "model_dump"):
                data[field_name] = val.model_dump(mode="json")
            elif isinstance(val, list):
                data[field_name] = [
                    v.model_dump(mode="json") if hasattr(v, "model_dump") else v
                    for v in val
                ]
            else:
                data[field_name] = val
        return data
    if isinstance(result, dict):
        return result
    return {"result": str(result)}


# ── Session state initialization ──
if "runner_results" not in st.session_state:
    st.session_state.runner_results = []


st.title("Capability Runner")
st.caption("Select a capability, fill in inputs, and run it. Results go through the capability registry per D-04.")

# ── Load registry ──
registry = get_registry()
capabilities = registry.list()

if not capabilities:
    st.error("No capabilities registered. Check the capability registry initialization.")
    st.stop()

# ── Capability selector ──
cap_options = {f"{c.id} — {c.description}": c for c in capabilities}
selected_label = st.selectbox(
    "Capability",
    options=list(cap_options.keys()),
    key="capability_selector",
)
cap = cap_options[selected_label]

# ── Input schema display ──
st.subheader(f"Inputs for: {cap.name}")

schema = cap.input_model.model_json_schema()

with st.expander("View JSON Schema", expanded=False):
    st.json(schema)

# ── Dynamic form ──
inputs = _render_form_fields(schema)

# ── Run button ──
if st.button("Run", type="primary", key="run_capability"):
    with st.spinner(f"Running {cap.id}..."):
        success, result, duration = _invoke_handler(cap, inputs)

    # Build result entry
    result_entry = {
        "capability_id": cap.id,
        "timestamp": time.time(),
        "success": success,
        "duration_s": round(duration, 3),
        "result_data": result,
    }

    # Store in session state (keep last 5)
    st.session_state.runner_results.insert(0, result_entry)
    st.session_state.runner_results = st.session_state.runner_results[:5]

    # ── Results display ──
    st.divider()
    st.subheader("Result")

    # Summary chips
    chip_col1, chip_col2, chip_col3 = st.columns(3)
    chip_col1.metric("Status", "✅ Success" if success else "❌ Failure")
    chip_col2.metric("Duration", f"{duration:.3f}s")

    result_dict = _result_to_dict(result)
    if isinstance(result_dict, dict):
        error_count = len(result_dict.get("errors", [])) if result_dict.get("errors") else 0
        chip_col3.metric("Errors", str(error_count))
    else:
        chip_col3.metric("Errors", "0")

    if success:
        st.code(json.dumps(result_dict, indent=2, default=str), language="json")
    else:
        st.error(result_dict.get("error", "Unknown error"))

# ── Last results (survive page nav) ──
if st.session_state.runner_results:
    with st.expander("Last 5 Results", expanded=False):
        for i, entry in enumerate(st.session_state.runner_results):
            st.caption(
                f"**{entry['capability_id']}** — "
                f"{'✅' if entry['success'] else '❌'} "
                f"{entry['duration_s']:.2f}s"
            )
            if st.button(f"Show result {i+1}", key=f"show_result_{i}"):
                st.json(entry["result_data"])
