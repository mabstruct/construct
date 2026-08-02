"""The ASGI app: one route, the whole capability registry (HTTP-01, D-05).

The structural claim ``mcp/server.py`` already proves for the MCP surface, made
again here in a different shape. There is **no route generator and no loop over
the registry**: a single ``POST /api/capabilities/{cap_id}`` is what makes every
capability reachable, because the path parameter *is* the capability id. A
capability added to the catalog is reachable over HTTP the moment it is
registered, with no edit to this file — the same property
``test_mcp_server_names_no_capability`` pins on the MCP side.

The route body does no validation of its own beyond the D-10 key refusal below.
Validation is the seam's job (GOV-01): ``get_registry().invoke(cap_id, payload)``
resolves the record, resolves ``workspace_id`` (D-01), validates against the
capability's declared ``extra="forbid"`` model, and only then dispatches. An
adapter that re-checked anything the seam checks would be a second contract that
can drift from the first — the fork the seam exists to close (HTTP-02).

**D-10 — the envelope refuses path-shaped payload keys, server-side.** Under
D-05 the payload arrives from the client verbatim, so "the adapter can only ever
emit ``workspace_id``" is not a property a client can hold. Any key in
``PATH_SHAPED_KEYS`` is refused with 422 before dispatch. This is HTTP's trust
boundary declining caller-supplied filesystem paths — HTTP-03's literal wording
— and it is *not* the rejected adapter-side-resolution alternative: resolution
still happens only inside the seam.

Known limits, deliberately left to later plans in this phase rather than
half-solved here:

* ``_serialize_result`` is duplicated from ``mcp/server.py`` for now. Plan 19-03
  moves the one copy to a shared module and has both surfaces import it; copying
  it into a third place instead would be the drift this phase is about.
* The route catches only the two typed seam errors. Anything else propagates
  rather than being stringified into a body — plan 19-07 installs the sanitizing
  exception handler, and ``str(exc)`` in the meantime is exactly the unguarded
  path leak (T-18-10) that would have to be unpicked afterwards.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from construct.api import CAPABILITY_ROUTE
from construct.api.middleware import LocalhostGuard
from construct.capabilities.catalog import get_registry
from construct.capabilities.errors import (
    CapabilityInputError,
    CapabilityNotFoundError,
)
from construct.capabilities.workspaces import (
    PATH_SHAPED_KEYS,
    set_launch_install_root,
)


class Envelope(BaseModel):
    """The one request body shape (D-05).

    ``extra="forbid"``, like every model in this project: an envelope that
    accepted unknown top-level keys would let a caller smuggle fields past the
    single declared ``payload``, and the seam would never see them.

    ``payload`` defaults to an empty dict so a capability whose model is
    all-optional is callable with ``{}`` — the seam already accepts that shape
    (``test_all_optional_model_accepts_an_empty_payload_and_uses_its_defaults``).
    """

    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any] = Field(default_factory=dict)


def _serialize_result(result: Any) -> dict:
    """Project a capability's return value onto a JSON-encodable dict.

    A copy of ``mcp/server.py::_serialize_result``, carrying its reasoning
    unchanged so the two surfaces answer in one shape: the dataclass branch
    **recurses** (``asdict``), because a one-level walk left ``OperationResult``
    holding ``OperationError`` dataclasses and dropped the whole error channel at
    the boundary (CR-01). And no ``str()`` fallback is applied to an unexpected
    value on the way out — coercing one would put filesystem paths into a body
    rendered straight back to a browser (T-18-10), so a value this cannot project
    is a bug to fix here rather than one to stringify at the boundary.

    Plan 19-03 moves this to a shared module and deletes both copies.
    """
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)
    if isinstance(result, (list, tuple)):
        return {"items": [str(item) for item in result]}
    return {"result": str(result)}


def create_app(install_root: Path, token: str) -> FastAPI:
    """Build the ASGI app for one launch.

    ``install_root`` and ``token`` are **per-launch state**, which is why this is
    a factory and why ``cli.py`` hands uvicorn the returned instance rather than
    an import string: an import string makes uvicorn re-import the module in a
    fresh interpreter, where neither value exists.
    """
    set_launch_install_root(install_root)

    app = FastAPI(
        title="CONSTRUCT",
        description=(
            "Loopback HTTP surface over the capability registry. Every route "
            "dispatches through CapabilityRegistry.invoke — the same seam the "
            "CLI and MCP surfaces use."
        ),
    )
    app.add_middleware(LocalhostGuard, token=token, allowed_origins=_allowed_origins())

    @app.post(CAPABILITY_ROUTE)
    async def invoke_capability(cap_id: str, envelope: Envelope) -> dict:
        """Dispatch one capability. The path parameter is the capability id."""
        offending = sorted(set(envelope.payload) & PATH_SHAPED_KEYS)
        if offending:
            raise HTTPException(
                status_code=422,
                detail=(
                    "path-shaped payload keys are refused at the HTTP boundary: "
                    f"{', '.join(offending)} — address a workspace by id with "
                    "'workspace_id' instead"
                ),
            )

        try:
            result = get_registry().invoke(cap_id, envelope.payload)
        except CapabilityNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CapabilityInputError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return _serialize_result(result)

    return app


def _allowed_origins() -> frozenset[str]:
    """The origins a browser page may carry when calling this server.

    A closed set of loopback literals, and deliberately a small one. Phase 21
    serves the UI from this very origin, and a same-origin ``fetch`` sends no
    ``Origin`` header at all — so the set is consulted almost only by requests
    that are already suspect.

    Note what it does **not** contain: a port. ``http://localhost:5173`` (a Vite
    dev server) is refused today. That is the honest current state rather than a
    wildcard nobody would notice; widening it is a visible edit, which is the
    property worth keeping for a check whose failure mode is silent.
    """
    return frozenset(
        f"http://{host}" for host in ("127.0.0.1", "localhost", "[::1]")
    )
