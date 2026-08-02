"""The Phase 19 tracer: one browser-shaped request, all the way through.

Requirements under test — HTTP-01 (a loopback HTTP surface exists),
HTTP-02 (it adds reach, never vocabulary), HTTP-03 (the boundary refuses
caller-supplied filesystem paths), HTTP-05 (the boundary refuses anything that
is not a token-bearing loopback request).

Decisions this file pins:

* **D-01 / D-09** — ``workspace_id`` is resolved inside
  ``CapabilityRegistry.invoke``, against a process-level install root, and
  ``invoke``'s signature is untouched. So the id vocabulary belongs to *every*
  surface, not to HTTP.
* **D-05** — one route, one envelope. The path parameter is the capability id,
  which is why no test here names a route per capability.
* **D-10** — path-shaped payload keys are refused server-side, because under a
  verbatim payload "the client only ever sends ``workspace_id``" is not a
  property the server can rely on.

The ordering claim is asserted, not assumed: a traversal-shaped id must be
refused with **no filesystem call**, so the shape gate is proven to run before
the allowlist gate by spying on ``discover_workspaces`` rather than by reading
the source.

**This file's blind spot, stated so nobody mistakes its coverage for more than
it is:** ``TestClient`` drives the ASGI app in-process and never opens a real
socket. It therefore proves what the app *does with* a ``Host`` header, and
proves nothing about what the operating system would route to the bound port.
The loopback bind address is asserted separately, as a constant, below — and a
constant is a weaker claim than a socket test, which is the honest state.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from construct.api import CAPABILITY_ROUTE, DEFAULT_API_PORT, TOKEN_HEADER
from construct.api.app import _serialize_result, create_app
from construct.capabilities.catalog import get_registry
from construct.capabilities.workspaces import (
    INSTALL_ROOT_FIELD,
    PATH_SHAPED_KEYS,
    WORKSPACE_FIELD,
    set_launch_install_root,
)

from tests.contract.conftest import API_TOKEN


def _url(cap_id: str) -> str:
    return CAPABILITY_ROUTE.format(cap_id=cap_id)


# ── The tracer: one request, end to end ───────────────────────────────────


def test_a_browser_shaped_request_reaches_a_real_capability_by_workspace_id(
    client: TestClient, install_root: Path, auth_headers: dict[str, str]
) -> None:
    """The whole architecture on one path.

    A POST carrying a workspace **id** crosses the trust boundary, is resolved
    inside the seam, reaches ``workspace.status``'s real handler, and comes back
    as the same body the other two surfaces get for the same workspace.

    The comparison is against ``_serialize_result`` of a direct seam call rather
    than against a hand-written expected body: a literal would only prove the
    route returns what this test's author *believed* the seam returns, which is
    exactly the cross-surface drift the phase exists to prevent.
    """
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "demo"}},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text

    expected = _serialize_result(
        get_registry().invoke("workspace.status", {"path": str(install_root / "demo")})
    )
    assert response.json() == expected
    assert expected["items"], "the fixture workspace reported no items — vacuous"


def test_the_shared_operation_result_envelope_survives_the_http_boundary(
    client: TestClient, install_root: Path, auth_headers: dict[str, str]
) -> None:
    """``success`` and ``data`` cross intact, on a capability that returns one.

    ``workspace.status`` returns a *list*, so the test above cannot make this
    claim. ``workflow.status`` returns an ``OperationResult`` and spells its
    workspace field ``workspace`` rather than ``path`` — so this covers the
    envelope and a second entry of the field map in one request.
    """
    response = client.post(
        _url("workflow.status"),
        json={"payload": {"workspace_id": "demo"}},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    direct = get_registry().invoke(
        "workflow.status", {"workspace": str(install_root / "demo")}
    )
    assert body["success"] == direct.success
    assert body["data"] == _serialize_result(direct)["data"]


# ── HTTP-05: the trust boundary ───────────────────────────────────────────


def test_a_request_without_a_token_is_refused_before_any_handler_runs(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """401, and the seam is never entered.

    A status-code assertion alone would not prove the second half. The seam is
    spied on, so "refused" means "the capability did not run" rather than "the
    response said 401".
    """
    calls: list[str] = []
    registry = get_registry()
    monkeypatch.setattr(
        type(registry),
        "invoke",
        lambda self, cap_id, payload: calls.append(cap_id),
    )

    response = client.post(
        _url("workspace.status"), json={"payload": {"workspace_id": "demo"}}
    )

    assert response.status_code == 401
    assert calls == [], "the seam ran despite a missing token"


def test_a_wrong_token_is_refused(client: TestClient) -> None:
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "demo"}},
        headers={TOKEN_HEADER: API_TOKEN + "-wrong"},
    )
    assert response.status_code == 401


def test_a_foreign_host_header_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """T-19-01, DNS rebinding: the socket cannot tell a rebound request apart
    from a local one, but the ``Host`` header can."""
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "demo"}},
        headers={**auth_headers, "Host": "evil.example.com"},
    )
    assert response.status_code == 400


def test_a_loopback_host_with_a_port_is_accepted(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The port is stripped, so a real browser's ``Host`` still passes.

    Without this, the rebinding guard would be "correct" and would also refuse
    every genuine request — the failure mode a status-code-only test of the
    rejection case cannot see.
    """
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "demo"}},
        headers={**auth_headers, "Host": f"127.0.0.1:{DEFAULT_API_PORT}"},
    )
    assert response.status_code == 200, response.text


def test_a_foreign_origin_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """403 — the status the MCP specification names for an invalid ``Origin``."""
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "demo"}},
        headers={**auth_headers, "Origin": "http://evil.example.com"},
    )
    assert response.status_code == 403


def test_an_absent_origin_is_allowed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """``curl`` and the CLI send no ``Origin``. Requiring one would break every
    non-browser client for no gain — a browser always sends it cross-origin."""
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "demo"}},
        headers=auth_headers,
    )
    assert "origin" not in {key.lower() for key in auth_headers}
    assert response.status_code == 200, response.text


def test_no_cors_middleware_is_installed(install_root: Path) -> None:
    """T-19-02: permissive CORS would dismantle the property the token header's
    non-safelisted status buys — the preflight nothing answers."""
    app = create_app(install_root, API_TOKEN)
    try:
        installed = {middleware.cls.__name__ for middleware in app.user_middleware}
        assert "CORSMiddleware" not in installed
        assert "TrustedHostMiddleware" not in installed
        assert "LocalhostGuard" in installed
    finally:
        set_launch_install_root(None)


# ── HTTP-03: the id gate ──────────────────────────────────────────────────


def test_a_traversal_shaped_id_is_refused_with_no_filesystem_call(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ordering proof (T-19-03).

    ``discover_workspaces`` calls ``install_root.iterdir()`` and stats every
    child, so it is filesystem contact driven by caller-controlled input. The
    shape gate must run first, and *that* is what this asserts — a 422 alone
    would be produced by either ordering.
    """
    from construct.views.lib import discover as discover_module

    calls: list[Path] = []
    monkeypatch.setattr(
        discover_module,
        "discover_workspaces",
        lambda root: calls.append(Path(root)) or [],
    )

    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "../../etc"}},
        headers=auth_headers,
    )

    assert response.status_code == 422, response.text
    assert calls == [], "the traversal attempt reached the filesystem"


def test_an_unknown_workspace_id_is_refused_and_names_the_known_ids(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The allowlist gate. The reason names the ids so the caller can correct
    itself without a second round trip."""
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "no-such-workspace"}},
        headers=auth_headers,
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "demo" in detail and "second-demo" in detail


def test_a_path_shaped_key_beside_the_id_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """D-10: the trust boundary declines caller-supplied filesystem paths.

    Sent *alongside* a valid id, so the refusal cannot be mistaken for the
    "``workspace_id`` cannot be combined with its own field" seam error — this
    is HTTP's own gate, and it fires before dispatch.
    """
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "demo", "path": "/tmp"}},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "path" in response.json()["detail"]


@pytest.mark.parametrize("key", sorted(PATH_SHAPED_KEYS))
def test_every_path_shaped_key_is_refused_by_the_envelope(
    client: TestClient, auth_headers: dict[str, str], key: str
) -> None:
    """Parametrised over the derived set, so a spelling added to the field map
    is covered without editing this test."""
    response = client.post(
        _url("workspace.status"),
        json={"payload": {key: "/tmp"}},
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text


def test_a_bare_path_payload_is_still_reachable_off_the_http_surface(
    install_root: Path,
) -> None:
    """HTTP-02's other half, and the reason D-10 lives in the route rather than
    in the seam: the CLI and MCP still send a path, exactly as before. Moving
    the refusal into ``invoke`` would have broken 26 existing call sites."""
    result = get_registry().invoke(
        "workspace.status", {"path": str(install_root / "demo")}
    )
    assert result


# ── The field map is exhaustive ───────────────────────────────────────────


def test_the_field_maps_cover_every_registered_capability() -> None:
    """A capability added without a classification is a capability no surface
    can address by id. Asserted as a *relationship* between two live
    measurements, never as a name set, so it stays honest as the registry grows.
    """
    classified = set(WORKSPACE_FIELD) | set(INSTALL_ROOT_FIELD)
    registered = {capability.id for capability in get_registry().list()}

    assert classified == registered, (
        "these capabilities are unclassified in the workspace-id field maps: "
        f"{sorted(registered - classified)}; and these are classified but not "
        f"registered: {sorted(classified - registered)}"
    )


def test_the_declared_field_name_is_the_one_the_model_declares() -> None:
    """The map's whole job. A wrong spelling here would be caught only as a
    validation error at request time, on that one capability."""
    registry = get_registry()
    wrong = [
        cap_id
        for cap_id, field in {**WORKSPACE_FIELD, **INSTALL_ROOT_FIELD}.items()
        if field not in registry.get(cap_id).input_model.model_fields
    ]
    assert wrong == [], f"field map names an undeclared field for: {wrong}"


def test_path_shaped_keys_is_derived_from_the_maps() -> None:
    """Derived, never hand-listed (D-10): a hand-list is a second copy that can
    silently fall behind the first."""
    assert PATH_SHAPED_KEYS == set(WORKSPACE_FIELD.values()) | set(
        INSTALL_ROOT_FIELD.values()
    )


# ── The seam is untouched (D-09) ──────────────────────────────────────────


def test_the_seam_signature_is_unchanged_by_the_id_resolution() -> None:
    """D-01 added behaviour, not a knob. Duplicated from
    ``test_surface_parity.py`` on purpose — that file guards the property for
    Phase 18; this one records that Phase 19 knew about it and did not move it.
    """
    import inspect

    from construct.capabilities.registry import CapabilityRegistry

    assert set(inspect.signature(CapabilityRegistry.invoke).parameters) == {
        "self",
        "cap_id",
        "payload",
    }


def test_the_route_table_is_one_capability_route(install_root: Path) -> None:
    """D-05: no route generator, no loop over the registry. The path parameter
    is what makes every capability reachable."""
    app = create_app(install_root, API_TOKEN)
    try:
        capability_routes = [
            route
            for route in app.routes
            if getattr(route, "path", "").startswith("/api/capabilities")
        ]
        assert len(capability_routes) == 1
        assert capability_routes[0].path == CAPABILITY_ROUTE
        assert set(capability_routes[0].methods) == {"POST"}
    finally:
        set_launch_install_root(None)


def test_an_unknown_capability_id_is_a_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        _url("no.such.capability"), json={"payload": {}}, headers=auth_headers
    )
    assert response.status_code == 404
    assert "no.such.capability" in response.json()["detail"]


def test_an_undeclared_envelope_key_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """``extra="forbid"`` on the envelope: a top-level key beside ``payload``
    would otherwise be silently dropped, and the caller would never learn its
    request was not the one it thought it sent."""
    response = client.post(
        _url("workspace.status"),
        json={"payload": {"workspace_id": "demo"}, "smuggled": 1},
        headers=auth_headers,
    )
    assert response.status_code == 422
