"""HTTP-04's shared result/error boundary, pinned as a contract.

``src/construct/capabilities/results.py`` is the one place a capability's return
value becomes a JSON body and an exception becomes a reason string. CLI, MCP and
the HTTP adapter Phase 19 adds all render through it, so criterion 3 — *no raw
exception text and no filesystem path in any body* — is decidable here rather
than re-argued per surface.

**What the measurements say (M-4).** 43 handlers build a message from a bound
exception. 14 of them catch an OSError-family exception, and ``str(OSError)``
embeds the absolute path (``"[Errno 2] No such file or directory:
'/Users/.../file.md'"``) — T-18-10. ``str(pydantic.ValidationError)`` embeds
``input_value=``, i.e. the caller's own submitted payload. Every one of those
messages reaches a serialized body. ``sanitize_exception`` closes the class by
never reading the message at all.

**D-16 — three tracks, deliberately not folded into one.** (a) The shared
sanitizing boundary, asserted below. (b) The shrink-only baseline over the
remaining source sites, so they cannot regrow. (c) The **success-path** ``data``
leaks (T-18-32), which an exception-boundary sanitizer structurally cannot see —
``graph.status`` and ``bridge.detect`` wrote ``str(root.resolve())`` into a
result that never raised. Folding (c) into (a) is precisely how it gets quietly
missed, so it has its own assertions here, against a *successful* body.

**Blind spot, stated rather than implied.** The boundary assertions prove the
boundary sanitizes. They do not prove every upstream site stopped producing raw
text into ``OperationResult.message`` — a site can still write a path into a
message that the sanitizer never sees, because the sanitizer only sees
*exceptions*. ``PATH_LEAKING_EXCEPTION_HANDLERS`` below is what covers that, and
it covers it by cardinality, not by behaviour.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from construct.capabilities.catalog import get_registry
from construct.capabilities.results import (
    ResultSerializationError,
    sanitize_exception,
    serialize_result,
)
from construct.mcp.server import create_server
from construct.services.knowledge import OperationError, OperationResult


# ---------------------------------------------------------------------------
# serialize_result — the projection every surface shares
# ---------------------------------------------------------------------------


class _Projected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    when: date


def test_a_pydantic_model_is_projected_in_json_mode() -> None:
    """``mode="json"`` and not the default: a ``date`` must arrive JSON-ready.

    ``model_dump()`` would hand back a ``datetime.date`` object, and the only way
    to get that into a body is the stringifying fallback this module refuses to
    have.
    """
    projected = serialize_result(_Projected(name="alpha", when=date(2026, 1, 2)))

    assert projected == {"name": "alpha", "when": "2026-01-02"}
    json.dumps(projected)


def test_a_dataclass_recurses_so_nested_errors_are_projected() -> None:
    """CR-01: a one-level walk left ``OperationError`` dataclasses in ``errors``.

    ``json.dumps`` then raised inside the caller's own ``try`` and every
    structured failure answered ``{"error": "Object of type OperationError is not
    JSON serializable"}`` — the whole error channel dropped, with a well-formed
    body, on the MCP surface only.
    """
    result = OperationResult(
        success=False,
        message="refused",
        errors=[OperationError(field="title", reason="missing", suggestion="add one")],
    )

    projected = serialize_result(result)

    assert projected["errors"] == [
        {"field": "title", "reason": "missing", "suggestion": "add one"}
    ]


def test_a_real_operation_result_round_trips_without_a_stringifying_fallback() -> None:
    """``json.dumps`` is called exactly as the surfaces call it: no fallback arg."""
    result = OperationResult(
        success=False,
        message="refused",
        errors=[
            OperationError(field="_general", reason="one"),
            OperationError(field="domains", reason="two", suggestion="pick a domain"),
        ],
        data={"counts": {"cards": 3}},
        outcome="degraded",
    )

    body = json.loads(json.dumps(serialize_result(result), indent=2))

    assert body["outcome"] == "degraded"
    assert [entry["reason"] for entry in body["errors"]] == ["one", "two"]


def test_a_sequence_is_projected_item_by_item_and_never_stringified() -> None:
    """The items branch used to be ``str(item)``.

    That is a stringifying arm wearing a projection's name: a ``list[Path]`` would
    have been rendered as a list of absolute paths *through the very branch that
    exists to keep them out* (T-18-10).
    """
    projected = serialize_result(
        [OperationError(field="a", reason="one"), "plain", 3]
    )

    assert projected == {
        "items": [
            {"field": "a", "reason": "one", "suggestion": ""},
            "plain",
            3,
        ]
    }

    with pytest.raises(ResultSerializationError):
        serialize_result([Path("/etc/passwd")])


def test_an_unprojectable_value_raises_instead_of_being_stringified() -> None:
    """The whole point of removing the final arm.

    ``{"result": str(result)}`` answered *something* for any value at all, which
    meant a ``Path`` return type would have been a silent absolute path in a body
    rather than a bug anybody had to fix.
    """
    with pytest.raises(ResultSerializationError):
        serialize_result(Path("/Users/someone/private/workspace"))

    with pytest.raises(ResultSerializationError):
        serialize_result(object())


def test_the_serializer_carries_no_stringifying_fallback_in_its_source() -> None:
    """A structural assertion, because the behavioural ones can only sample.

    ``json.dumps``'s fallback argument is how a boundary quietly regains the
    ability to coerce anything at all; the surfaces must keep calling it without
    one, and this module must never grow one internally.
    """
    import inspect

    from construct.capabilities import results

    source = inspect.getsource(results)
    assert "default=" not in source
    assert "str(result)" not in source


# ---------------------------------------------------------------------------
# sanitize_exception — the reason string that carries no environment
# ---------------------------------------------------------------------------


ABSOLUTE_PATH = "/Users/someone/private/construct-workspace/cards/secret.md"


def test_an_os_error_reason_names_the_class_and_drops_the_path() -> None:
    """The measured leak: ``str(OSError)`` embeds the absolute path (T-18-10).

    The class name is the *errno subclass* CPython actually constructs
    (``OSError(2, ...)`` is a ``FileNotFoundError``), which is the more useful of
    the two names and is why the reason reports ``type(exc).__name__`` rather than
    the type the raiser wrote.
    """
    exc = OSError(2, "No such file or directory", ABSOLUTE_PATH)

    assert ABSOLUTE_PATH in str(exc), "fixture no longer reproduces the leak"

    reason = sanitize_exception(exc)

    assert reason == "FileNotFoundError: No such file or directory"
    assert ABSOLUTE_PATH not in reason
    assert "/" not in reason


def test_an_arbitrary_exception_reason_is_the_class_name_alone() -> None:
    """The message is never read, so a path anywhere in it cannot survive.

    A filter over ``str(exc)`` would have to be right about every message shape
    ever raised; not reading the message is right by construction.
    """
    exc = RuntimeError(f"could not open {ABSOLUTE_PATH} while resuming the run")

    reason = sanitize_exception(exc)

    assert reason == "RuntimeError"
    assert ABSOLUTE_PATH not in reason


def test_a_validation_error_reason_does_not_echo_the_submitted_payload() -> None:
    """``str(pydantic.ValidationError)`` embeds ``input_value=`` — the caller's own
    payload handed straight back out (T-18-10)."""
    secret = "/Users/someone/private/s3cret-token-value"
    try:
        _Projected.model_validate({"name": "alpha", "when": secret})
    except ValidationError as exc:
        raised = exc
    else:  # pragma: no cover - the fixture must fail validation
        pytest.fail("the fixture payload was accepted")

    assert secret in str(raised), "fixture no longer reproduces the echo"

    reason = sanitize_exception(raised)

    assert reason == "ValidationError"
    assert secret not in reason


def test_no_reason_carries_a_traceback_marker() -> None:
    """Structural, not filtered: no branch formats ``__traceback__``."""
    try:
        raise OSError(13, "Permission denied", ABSOLUTE_PATH)
    except OSError as exc:
        reason = sanitize_exception(exc)

    assert "Traceback" not in reason
    assert reason == "PermissionError: Permission denied"


def test_a_hostile_strerror_is_dropped_rather_than_trimmed() -> None:
    """Defence in depth for an ``OSError`` subclass that puts a path in ``strerror``.

    The allow-listed detail channel is CPython's errno description; anything
    carrying a path marker is discarded whole rather than edited into shape.
    """
    exc = OSError(2, f"could not read {ABSOLUTE_PATH}")

    assert sanitize_exception(exc) == "FileNotFoundError"


# ---------------------------------------------------------------------------
# The MCP surface's catch-all — the arm M-4 counted as the 14th leak site
# ---------------------------------------------------------------------------


def _mcp_tool(name: str):
    """The closure ``create_server()`` really registers with FastMCP.

    Calling ``cap.handler`` directly would skip the wiring under change — the
    generic exception arm lives in ``make_handler``'s closure, not in the handler.
    """
    return create_server()._tool_manager.get_tool(name)


def test_the_mcp_catch_all_no_longer_renders_raw_exception_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """M-4's 14th site: one bare ``str(exc)`` standing behind every capability."""
    record = get_registry().get("knowledge.card.list")

    def _raise(**_kwargs: object) -> object:
        raise OSError(2, "No such file or directory", ABSOLUTE_PATH)

    monkeypatch.setattr(record, "handler", _raise)

    body = json.loads(_mcp_tool("construct_list_cards").fn(workspace=str(tmp_path)))

    assert body["error"] == "FileNotFoundError: No such file or directory"
    assert ABSOLUTE_PATH not in body["error"]


def test_the_mcp_catch_all_drops_a_path_from_an_untyped_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The same arm, for an exception that is not OSError-shaped at all."""
    record = get_registry().get("knowledge.card.list")

    def _raise(**_kwargs: object) -> object:
        raise RuntimeError(f"index rebuild failed for {tmp_path}")

    monkeypatch.setattr(record, "handler", _raise)

    body = json.loads(_mcp_tool("construct_list_cards").fn(workspace=str(tmp_path)))

    assert body["error"] == "RuntimeError"
    assert str(tmp_path) not in body["error"]


def test_the_mcp_surface_still_renders_the_seams_typed_reason(tmp_path: Path) -> None:
    """GOV-01 parity is not collateral damage of the sanitizer.

    ``CapabilityInputError``'s reason is path-free by construction — it is built
    from field locations and pydantic constraint text with ``include_input`` and
    ``include_context`` off — so the typed arm keeps rendering its own message and
    the MCP reason stays identical to the CLI's.
    """
    body = json.loads(
        _mcp_tool("construct_list_cards").fn(workspace=str(tmp_path), bogus=1)
    )

    assert "bogus" in body["error"]
    assert "Invalid input for capability 'knowledge.card.list'" in body["error"]
