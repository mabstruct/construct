"""The one result/error boundary every invoke surface serializes through (HTTP-04).

CLI, MCP, and the HTTP adapter Phase 19 adds all render the same capability
return values. This module owns the two projections that must not fork between
them: a capability's return value onto a JSON-encodable dict
(:func:`serialize_result`), and an exception onto a reason string
(:func:`sanitize_exception`).

It deliberately imports nothing from ``construct.services`` or ``construct.mcp``
so every surface can import it without a cycle.

**Why the sanitizer is here and not at each call site.** M-4 measured 43 handlers
that build a message from a bound exception; 14 of them catch an OSError-family
exception, and ``str(OSError)`` embeds the absolute path
(``"[Errno 2] No such file or directory: '/Users/.../file.md'"``). Every one of
them reaches a serialized body. A boundary that reduces an exception without ever
reading its message closes that class in one place rather than 43 (T-18-10).

**What this module does not do.** It sanitizes what crosses the boundary; it does
not stop an upstream site from *producing* raw text into a result's ``message``
or ``errors``. That gap is held by the shrink-only baseline in
``tests/contract/test_result_boundary.py``. It also never sees the **success**
path's ``data`` — an absolute path written there by a capability that did not
raise is invisible to an exception sanitizer by construction (T-18-32), which is
why those two sites were fixed at the source instead (D-16, D-19).
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


class ResultSerializationError(TypeError):
    """A value reached the boundary that :func:`serialize_result` cannot project.

    Deliberately **not** a ``CapabilityError``. The seam's typed errors are
    rendered back to the caller as a reason string, and a serialization gap
    rendered that way would look like a normal refusal — the surface would answer
    politely and nobody would fix it. This is a bug in the boundary, so it is
    raised as its own type and left to surface loudly.

    ``TypeError`` is the base because the failure is exactly one: a value of an
    unprojectable *type*.
    """


# Path separators and the home shorthand. Nothing that is allowed through the
# sanitizer's detail channel legitimately contains one, so their presence is
# treated as evidence of a path rather than parsed as one.
_PATH_MARKERS = ("/", "\\", "~")

# A reason string is read by an agent and by a browser; an unbounded one is a
# denial-of-readability, not a leak, but it is still not a reason.
_MAX_DETAIL_CHARS = 120

_PRIMITIVES = (str, int, float, bool, type(None))


def serialize_result(result: Any) -> dict[str, Any]:
    """Project a capability's return value onto a JSON-encodable dict.

    The dataclass branch **recurses** (``asdict``), and that is the whole point.
    A one-level ``{f: getattr(result, f)}`` walk returned ``OperationResult`` with
    its ``errors`` list still holding ``OperationError`` dataclasses;
    ``json.dumps`` then raised inside the caller's own ``try`` and every
    structured failure answered ``{"error": "Object of type OperationError is not
    JSON serializable"}``. That dropped the entire error channel on the MCP
    surface — silently, with a well-formed JSON body — so an agent read a bogus
    reason and could not tell a validation failure from an infrastructure fault.
    The CLI rendered the same capability's reasons correctly, which is exactly
    the cross-surface fork GOV-01 exists to close (CR-01).

    There is deliberately **no stringifying fallback anywhere in this function**,
    and callers must keep ``json.dumps`` free of its ``default`` argument for the
    same reason: coercing an unexpected value with ``str()`` would put filesystem
    paths into a string rendered straight back to a client (T-18-10), so a value
    this function cannot project is a bug to fix here, not one to stringify at the
    boundary. That rule now covers the sequence branch too — it used to project
    items with ``str(item)``, which would have rendered a ``list[Path]`` as a list
    of absolute paths through the very branch that exists to keep them out.
    """
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)
    if isinstance(result, (list, tuple)):
        return {"items": [_project(item) for item in result]}
    raise ResultSerializationError(
        f"cannot project {type(result).__name__} onto a JSON-encodable body; "
        "give the capability a pydantic model or a dataclass return type, or add "
        "an explicit branch here — do not stringify it at the boundary"
    )


def _project(value: Any) -> Any:
    """Project one nested value, with the same no-stringifying rule."""
    if isinstance(value, _PRIMITIVES):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, (list, tuple)):
        return [_project(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _project(item) for key, item in value.items()}
    raise ResultSerializationError(
        f"cannot project a nested {type(value).__name__} onto a JSON-encodable body"
    )


def sanitize_exception(exc: BaseException) -> str:
    """Reduce an exception to a reason string that carries no environment.

    The rule is structural rather than filtering: **the exception's own message is
    never read.** Two measured facts make anything weaker unsafe.

    * ``str(OSError)`` embeds the absolute path — ``"[Errno 2] No such file or
      directory: '/Users/.../file.md'"`` (T-18-10, M-4). 14 of the 43 measured
      handlers catch an OSError-family exception, and every one of them reaches a
      serialized body.
    * ``str(pydantic.ValidationError)`` embeds ``input_value=`` — that is the
      *caller's own submitted payload* echoed back out (T-18-10), which is the
      same defect ``CapabilityInputError.from_validation_error`` already avoids by
      passing ``include_input=False`` / ``include_context=False``.

    So the output is the exception's class name, plus at most one bounded detail
    drawn from a single allow-listed attribute: ``OSError.strerror``, which CPython
    populates with the errno description alone (``"No such file or directory"``) and
    keeps the filename in a separate attribute this function never reads. A detail
    containing a path marker is dropped rather than trimmed — defence in depth for
    an ``OSError`` subclass that puts something else in ``strerror``.

    A ``Traceback`` marker cannot appear for the same structural reason: no branch
    formats the exception, and none formats ``__traceback__``.

    **Relationship to ``llm/curation_run.py:_sanitize_error``.** That helper takes
    the class name plus the message's *first line*, which is the right trade for
    the audit trail it feeds (T-11-02 / T-11-06) but is not sufficient here — the
    first line is exactly where ``str(OSError)`` puts the path. This function
    supersedes it for anything crossing to a caller; ``_sanitize_error`` is not to
    be reused at a result boundary.
    """
    name = type(exc).__name__
    detail = _safe_detail(exc)
    return f"{name}: {detail}" if detail else name


def _safe_detail(exc: BaseException) -> str | None:
    """The single allow-listed detail channel, or ``None``.

    Reads ``strerror`` and nothing else — never ``args``, never ``str(exc)``.
    """
    strerror = getattr(exc, "strerror", None)
    if not isinstance(strerror, str):
        return None
    lines = strerror.strip().splitlines()
    detail = lines[0].strip() if lines else ""
    if not detail:
        return None
    if any(marker in detail for marker in _PATH_MARKERS):
        return None
    return detail[:_MAX_DETAIL_CHARS]
