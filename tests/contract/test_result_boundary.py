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

**The baseline's measured population, and how it reconciles with RESEARCH.**
The scan below was run against the tree as it stands, not copied from the
research. It finds **14 leaking handlers across 9 enclosing functions** in
``services/knowledge.py``. RESEARCH M-4 reports **13**, and the difference is
real rather than a discrepancy: M-4 classified handlers whose body contains
``str(<bound exception>)``, and one site interpolates the exception into an
f-string instead — ``_read_card_file`` re-raises
``OSError(f"Could not read cards/{card_id}.md: {exc}")``. It leaks identically
and a ``str(exc)``-shaped scan cannot see it, so this scan matches both forms and
the baseline carries the 14th.

**Why the 29 domain-error handlers are deliberately outside the baseline.**
M-4's other column — ``WorkspaceLoadError``, ``ArtifactValidationError``,
``PydanticValidationError``, ``ValueError`` — was classified *by exception type
rather than executed* (RESEARCH assumption A6). Two were probed live and did not
leak, because those paths raise domain errors carrying hand-written relative-path
messages. The remaining 27 are unproven in both directions: a ``WorkspaceLoadError``
whose message interpolates a path would leak and would not appear here. That
residue is accepted because the shared sanitizer covers them regardless — only
the baseline's *size* depends on the classification, never the boundary's
correctness.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
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

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "construct"
FIXTURE_WS = REPO_ROOT / "test-ws" / "my-construct"


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
    """M-4 counted this arm as a leak site of its own, and rightly.

    One bare ``str(exc)`` stood behind *every* capability, so an OSError escaping
    any handler put an absolute path into an MCP body.
    """
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


# ---------------------------------------------------------------------------
# The success path — where an exception-boundary sanitizer never looks (T-18-32)
# ---------------------------------------------------------------------------


# A POSIX absolute path of at least two segments, or a Windows drive prefix.
# Deliberately shape-based rather than "does the body contain *this* tmp_path":
# a body can carry somebody else's absolute path, and the tmp_path check would
# pass while criterion 3 failed.
_PATH_SHAPED = re.compile(r"(?:/[A-Za-z0-9._-]+){2,}|[A-Za-z]:[\\/]")


def _path_shaped_substrings(text: str) -> list[str]:
    return _PATH_SHAPED.findall(text)


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway copy of the canonical fixture, under an absolute temp path.

    ``ANTHROPIC_API_KEY`` is removed so ``bridge.detect``'s L3 gate skips rather
    than reaching the network: this is a boundary test, and a body's shape must
    not depend on whether the machine running it happens to be provisioned.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    dest = tmp_path / "my-construct"
    shutil.copytree(FIXTURE_WS, dest)
    return dest


def test_a_successful_graph_status_body_carries_no_absolute_path(
    workspace: Path,
) -> None:
    """Criterion 3 asserted against a **success**, which is the whole point.

    ``graph_status`` wrote ``str(root.resolve())`` into ``OperationResult.data``
    with no exception anywhere in the flow (T-18-32), so a criterion-3 test that
    only exercises failures — the documented way this leak survives — would have
    reported green throughout.
    """
    result = get_registry().invoke("graph.status", {"workspace": str(workspace)})

    assert result.success, result.message
    assert result.data["workspace"] == workspace.name

    body = json.dumps(serialize_result(result), indent=2)

    assert str(workspace) not in body
    assert str(workspace.parent) not in body
    assert _path_shaped_substrings(body) == []


def test_a_successful_bridge_detect_body_carries_no_absolute_path(
    workspace: Path,
) -> None:
    """The second instance of the same class, not recorded in RESEARCH.

    ``_persist_candidates`` set ``bridges["workspace"]`` on the dict it both
    writes to disk *and* returns as ``OperationResult.data``, so the path reached
    a serialized body by the same route.
    """
    result = get_registry().invoke("bridge.detect", {"workspace_path": str(workspace)})

    assert result.success, result.message
    assert result.data["workspace"] == workspace.name

    body = json.dumps(serialize_result(result), indent=2)

    assert str(workspace) not in body
    assert str(workspace.parent) not in body
    assert _path_shaped_substrings(body) == []


# ---------------------------------------------------------------------------
# The shrink-only baseline over the remaining source sites (D-16b, T-19-15)
# ---------------------------------------------------------------------------


OS_ERROR_FAMILY = frozenset(
    {
        "OSError",
        "IOError",
        "EnvironmentError",
        "FileNotFoundError",
        "FileExistsError",
        "PermissionError",
        "NotADirectoryError",
        "IsADirectoryError",
    }
)


def _caught_names(handler: ast.ExceptHandler) -> set[str]:
    """Every exception name a handler catches, tuple or single."""
    node = handler.type
    if node is None:
        return {"BaseException"}
    parts = node.elts if isinstance(node, ast.Tuple) else [node]
    names = set()
    for part in parts:
        if isinstance(part, ast.Name):
            names.add(part.id)
        elif isinstance(part, ast.Attribute):
            names.add(part.attr)
    return names


def _builds_message_from_bound_exception(handler: ast.ExceptHandler) -> bool:
    """Whether the handler turns its bound exception into text.

    Both forms count. ``str(exc)`` is the one M-4 scanned for; ``f"...{exc}"``
    is the one it could not see, and it leaks identically — CPython formats an
    interpolated exception with the same ``__str__``.
    """
    if not handler.name:
        return False
    for node in ast.walk(handler):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "str"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == handler.name
        ):
            return True
        if (
            isinstance(node, ast.FormattedValue)
            and isinstance(node.value, ast.Name)
            and node.value.id == handler.name
        ):
            return True
    return False


def scan_path_leaking_handlers(path: Path) -> tuple[dict[str, int], int]:
    """``({"<module>::<function>": count}, handlers_examined)``.

    Keyed per **enclosing function**, never per module. A module-level key would
    let a second leaking handler land inside an already-listed file and change
    nothing the baseline can see — the count would hide behind the name.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    module = f"{path.parent.name}/{path.name}"
    offenders: dict[str, int] = {}
    examined = 0

    def walk(node: ast.AST, enclosing: str) -> None:
        nonlocal examined
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, child.name)
                continue
            if isinstance(child, ast.ExceptHandler):
                examined += 1
                if _caught_names(child) & OS_ERROR_FAMILY and (
                    _builds_message_from_bound_exception(child)
                ):
                    key = f"{module}::{enclosing}"
                    offenders[key] = offenders.get(key, 0) + 1
            walk(child, enclosing)

    walk(tree, "<module>")
    return offenders, examined


# NOT an allowlist — a regression baseline that may only shrink, in the
# ``UNRESOLVED_DIRECT_CALLERS`` shape this repo already uses (Phase 18 D-23).
#
# Each entry is a function in ``services/knowledge.py`` that catches an
# OSError-family exception and builds a message from it. ``str(OSError)`` embeds
# the absolute path, and every one of these messages lands in
# ``OperationResult.message`` or ``OperationError.reason`` — i.e. in a serialized
# body. The shared sanitizer does not reach them, because they never raise: they
# *return* the text.
#
# Fixing one means deleting its entry here. Leaving a fixed entry in place is a
# failure, not a courtesy.
PATH_LEAKING_EXCEPTION_HANDLERS = frozenset(
    {
        "services/knowledge.py::_read_card_file",
        "services/knowledge.py::_write_tag_candidates_file",
        "services/knowledge.py::add_connection",
        "services/knowledge.py::approve_tag_candidates",
        "services/knowledge.py::archive_card",
        "services/knowledge.py::create_card",
        "services/knowledge.py::edit_card",
        "services/knowledge.py::remove_connection",
        "services/knowledge.py::route_source_to_domain",
    }
)

#: Handlers, not functions. Four of the nine functions above carry more than one,
#: so a per-function baseline alone would let a tenth handler land inside
#: ``edit_card`` and change nothing the guard can see.
PATH_LEAKING_HANDLER_COUNT = 14

#: The scan must examine at least this many handlers to be believed. Measured 30
#: in ``services/knowledge.py``; the floor is set below that so ordinary edits do
#: not trip it, but far enough above zero that a scan which silently stops
#: finding anything fails instead of passing.
MINIMUM_HANDLERS_EXAMINED = 25


def test_no_new_path_leaking_exception_handler() -> None:
    """T-19-15: the leak sites may not regrow after the boundary lands."""
    offenders, _ = scan_path_leaking_handlers(SRC_ROOT / "services" / "knowledge.py")

    new = sorted(set(offenders) - PATH_LEAKING_EXCEPTION_HANDLERS)
    assert not new, (
        "these functions newly build a message from an OSError-family exception, "
        "which embeds the absolute path; route them through "
        "construct.capabilities.results.sanitize_exception instead of adding them "
        f"to the baseline: {new}"
    )


def test_no_stale_entry_in_the_path_leak_baseline() -> None:
    """The direction that forces the baseline down when a site is fixed."""
    offenders, _ = scan_path_leaking_handlers(SRC_ROOT / "services" / "knowledge.py")

    stale = sorted(PATH_LEAKING_EXCEPTION_HANDLERS - set(offenders))
    assert not stale, (
        "these functions no longer build a message from an OSError-family "
        "exception — delete them from PATH_LEAKING_EXCEPTION_HANDLERS instead of "
        f"leaving the baseline to rot: {stale}"
    )


def test_the_path_leak_handler_count_can_only_shrink() -> None:
    """The dimension a per-function baseline cannot see."""
    offenders, _ = scan_path_leaking_handlers(SRC_ROOT / "services" / "knowledge.py")
    measured = sum(offenders.values())

    assert measured == PATH_LEAKING_HANDLER_COUNT, (
        f"{measured} leaking handlers found, baseline says "
        f"{PATH_LEAKING_HANDLER_COUNT}. Fewer means a site was fixed — lower the "
        "number. More means one regrew inside a function already listed, which is "
        f"exactly what the per-function set cannot see: {dict(sorted(offenders.items()))}"
    )


def test_the_leak_scan_is_not_vacuous() -> None:
    """A guard that finds nothing passes for the wrong reason.

    Without this, a rename of ``ast.ExceptHandler`` handling — or a module that
    silently fails to parse into the shape the walk expects — would turn both
    assertions above into unconditional passes.
    """
    _, examined = scan_path_leaking_handlers(SRC_ROOT / "services" / "knowledge.py")

    assert examined >= MINIMUM_HANDLERS_EXAMINED, (
        f"the scan examined only {examined} exception handlers in "
        "services/knowledge.py; it is not looking at the module it claims to guard"
    )


def test_the_leak_scan_detects_a_planted_offender(tmp_path: Path) -> None:
    """A guard never observed failing is not known to be a guard.

    Plants a module in a scratch tree and scans it with the same function the real
    guard uses: a handler that stringifies its bound OSError is caught, one that
    stringifies a *domain* error is not (that is the A6 class, deliberately out of
    scope), and one that logs without touching the exception is not.
    """
    planted = tmp_path / "services" / "planted.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "def leaks():\n"
        "    try:\n"
        "        pass\n"
        "    except OSError as exc:\n"
        "        return str(exc)\n"
        "def interpolates():\n"
        "    try:\n"
        "        pass\n"
        "    except FileNotFoundError as exc:\n"
        "        return f'could not read: {exc}'\n"
        "def domain_error_is_out_of_scope():\n"
        "    try:\n"
        "        pass\n"
        "    except WorkspaceLoadError as exc:\n"
        "        return str(exc)\n"
        "def clean():\n"
        "    try:\n"
        "        pass\n"
        "    except OSError:\n"
        "        return 'could not read the card'\n",
        encoding="utf-8",
    )

    offenders, examined = scan_path_leaking_handlers(planted)

    assert set(offenders) == {
        "services/planted.py::leaks",
        "services/planted.py::interpolates",
    }
    assert examined == 4
