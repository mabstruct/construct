"""One error body for every HTTP emitter (HTTP-04).

RESEARCH measured that **four** different default error bodies can leave this
surface, only one of which the route writes:

1. a request-validation rejection — the envelope failed its own model;
2. an unknown-route rejection — the framework's ``404``;
3. a pre-dispatch guard rejection — ``LocalhostGuard`` answers *before* the app,
   so no exception handler can reach it;
4. an unexpected exception raised while a capability ran.

"No third fork" (HTTP-02) is a claim about the whole vocabulary a caller meets,
so it means overriding all four. This module owns the one body builder they
share; ``middleware.py`` imports it for the third, and ``app.py`` installs the
handlers for the other two and renders the fourth itself.

**The body is exactly ``{"detail": <str>}``.** That is FastAPI's own
``HTTPException`` shape, chosen so that a body this project did not write —
the framework's ``404``, for instance — is already the project's shape rather
than a second one to be noticed later. ``tests/contract/test_http_security.py``
asserts the key *set*, so a second top-level key added here is a failing test
rather than a silent fork; anything a body needs to say goes into the reason.

**T-19-16 — the documented handler for (1) is a disclosure.** FastAPI's own
example returns ``exc.body`` (the caller's raw request body) and ``exc.errors()``
(whose entries carry pydantic's echoed ``input``). That is precisely the class
``CapabilityInputError.from_validation_error`` already suppresses for the seam.
So the validation handler here calls *that* builder rather than formatting
pydantic's error list itself — which is what makes the cross-surface reason
contract hold by construction rather than by whoever next edits this file
remembering it.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import Response

from construct.capabilities.errors import (
    CapabilityError,
    CapabilityInputError,
    CapabilityNotFoundError,
)


#: The HTTP status each of the seam's typed errors carries (D-24).
#:
#: Keyed by exact type, and looked up by exact type. A ``CapabilityError``
#: subclass that is not listed gets **500**, not a guessed 4xx: a 4xx tells the
#: caller their request was wrong, and this map has no basis for saying that
#: about an error class it has never been told about. Adding a seam error type
#: is therefore a deliberate two-line change rather than an inherited status.
#:
#: Note what is *absent*: any entry for a capability that ran and reported
#: failure. That is not a seam error at all — see ``app.py``'s D-24 comment.
STATUS_FOR_SEAM_ERROR: dict[type[CapabilityError], int] = {
    CapabilityNotFoundError: 404,
    CapabilityInputError: 422,
}

#: Stands in for the capability id when a request failed validation before it
#: named one. It is only ever handed to ``CapabilityInputError``'s constructor
#: to satisfy it; the placeholder never reaches a response body, because the
#: handler emits ``error.reason`` rather than ``str(error)`` in that case.
_NO_CAPABILITY = "<no capability>"


def error_body(reason: str, cap_id: str | None = None) -> dict[str, str]:
    """The one error body. Every emitter on this surface returns this.

    ``cap_id`` is folded into the reason rather than carried as a second key,
    because the body shape is the thing being unified: a key that appears on
    some refusals and not others is a fork wearing a smaller hat, and a caller
    parsing it would have to branch. The seam's own reasons already name the
    capability, so they pass ``cap_id=None``; the arm that supplies it is the
    unexpected-exception path, whose sanitized reason is a bare class name and
    would otherwise not say what was being asked for.

    ``reason`` names the *check* or the *class*, never a submitted value — the
    rule the seam's reason strings and ``sanitize_exception`` both already
    follow (T-18-10). This function cannot enforce that; it is stated here
    because this is where every reason on this surface passes through.
    """
    detail = reason if cap_id is None else f"Capability '{cap_id}': {reason}"
    return {"detail": detail}


def status_for_seam_error(exc: CapabilityError) -> int | None:
    """The status for a typed seam error, or ``None`` if it has none declared.

    ``None`` means "this is not a refusal this surface knows how to express",
    and the caller renders it as an unexpected exception — sanitized, at 500.
    """
    return STATUS_FOR_SEAM_ERROR.get(type(exc))


def install_error_handlers(app: FastAPI, envelope_model: type[BaseModel]) -> None:
    """Override the two emitters the framework owns.

    ``envelope_model`` is the model the request body is validated against, and
    it has no default for the same reason ``from_validation_error``'s ``model``
    has none (D-08): it is what makes the reason's field ordering independent of
    the caller's key order, and a defaultable correctness argument is one a
    caller drops without being told. It is passed in rather than imported so
    this module stays free of a cycle back into ``app.py``.
    """

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> Response:
        """The envelope was malformed. Answer 422 in the project's own words.

        **The reason is built by the seam's builder, never here (T-19-16).**
        FastAPI's documented handler for this exception returns ``exc.body`` and
        ``exc.errors()``: the first is the caller's raw submitted body and the
        second carries pydantic's echoed ``input`` value for every failing
        field. Both are the disclosure class
        ``CapabilityInputError.from_validation_error`` exists to suppress, and
        it is already the source of the reason a rejected *payload* produces on
        all three surfaces. Reusing it here is what makes the envelope rejection
        and the payload rejection the same kind of sentence — and, more to the
        point, makes a future edit that reintroduces the echo have to walk past
        a function whose whole job is to not do that.
        """
        cap_id = request.path_params.get("cap_id")
        error = CapabilityInputError.from_validation_error(
            cap_id or _NO_CAPABILITY, exc, envelope_model
        )
        detail = str(error) if cap_id else error.reason
        return JSONResponse(status_code=422, content=error_body(detail))

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> Response:
        """Every ``HTTPException``, including the router's own unknown-route 404.

        The framework's default handler already emits ``{"detail": ...}``, so
        this override changes no body today. It is installed anyway because
        "the default happens to match" is not the same claim as "this surface
        emits one shape" — the first stops being true when a dependency changes
        its default, silently, in a body nobody re-reads.
        """
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(detail),
            headers=getattr(exc, "headers", None),
        )
