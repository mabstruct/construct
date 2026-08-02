"""HTTP-05 as a measured matrix — Host, Origin, token, and what they precede.

Every row of the trust boundary, asserted rather than assumed. The control set
is the MCP specification's own for a local HTTP server — validate ``Origin``,
answer **403** when it is present and invalid, bind loopback, authenticate even
locally — published after three independent DNS-rebinding advisories against MCP
SDKs: ``GHSA-w48q-cv73-mx4w`` (TypeScript SDK), ``CVE-2025-66416`` (Python SDK)
and ``GHSA-89vp-x53w-74fx`` (rmcp, missing ``Host`` validation). This file is
where that set stops being a claim in a docstring.

Decisions pinned here:

* **D-05** — one route, one JSON envelope. A drive-by *simple* request can only
  carry ``text/plain``, ``application/x-www-form-urlencoded`` or
  ``multipart/form-data``, and the content-type matrix below measures that none
  of them reaches a capability with a parsed payload.
* **D-21** — an absent ``Origin`` is allowed; a present-and-not-allowlisted one
  is refused with 403. ``curl``, the CLI and every scripted client send no
  ``Origin``; a browser always sends one cross-origin.
* **D-22** — the token travels in a non-CORS-safelisted header and **no CORS
  middleware is installed**, so a cross-origin caller must pass a preflight
  nothing answers. ``test_no_cors_middleware_is_installed`` is what stops a
  future convenience import from quietly removing that.
* **D-23** — Host, Origin and token are checked in one middleware, in that
  order, so all three refusals carry one body shape.

**This file's blind spot, stated so its coverage is not mistaken for more than
it is:** a test client sends no ``Origin`` header of its own. An Origin case that
does not set the header *explicitly* therefore proves nothing about Origin — it
merely re-runs the absent-Origin path. Every Origin assertion below sets the
header, and the absent case asserts that it is absent. Likewise ``TestClient``
never opens a socket, so this proves what the app does *with* a ``Host`` header
and nothing about what the operating system routes to the bound port.
"""
from __future__ import annotations

import hashlib
import secrets as secrets_module
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from construct.api import CAPABILITY_ROUTE, TOKEN_HEADER
from construct.api.app import create_app
from construct.api.middleware import (
    ALLOWED_HOSTS,
    ALLOWED_ORIGINS,
    allowed_origins,
)
from construct.capabilities.catalog import get_registry
from construct.capabilities.workspaces import set_launch_install_root

from tests.contract.conftest import API_TOKEN

#: A read capability, used for every case whose subject is the guard rather than
#: the effect. The write case lives in the ordering proof at the bottom.
READ_CAP = "workspace.status"

#: A port that is not ``DEFAULT_API_PORT``. The Origin allowlist is derived from
#: the launch port, and a matrix that only ever exercised the default port could
#: not tell a derived set apart from a hard-coded one.
LAUNCH_PORT = "9999"


def _url(cap_id: str) -> str:
    return CAPABILITY_ROUTE.format(cap_id=cap_id)


def _read_payload() -> dict:
    return {"payload": {"workspace_id": "demo"}}


def _spy_on_the_seam(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every capability id the seam is asked to invoke.

    "Refused" has to mean "the capability did not run", not "the response said
    401". A status code is the guard reporting on itself; this list is the seam
    reporting on the guard.
    """
    calls: list[str] = []
    monkeypatch.setattr(
        type(get_registry()),
        "invoke",
        lambda self, cap_id, payload: calls.append(cap_id),
    )
    return calls


# ── The Host check (T-19-01, DNS rebinding) ───────────────────────────────


def test_a_foreign_host_is_refused_with_400(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a rebind the browser still sends the attacker's hostname.

    The socket cannot tell a rebound request apart from a genuine local one —
    the ``Host`` header is the only place the difference survives.
    """
    calls = _spy_on_the_seam(monkeypatch)

    response = client.post(
        _url(READ_CAP),
        json=_read_payload(),
        headers={**auth_headers, "Host": "evil.example.com"},
    )

    assert response.status_code == 400
    assert calls == [], "the seam ran despite a foreign Host"


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        f"127.0.0.1:{LAUNCH_PORT}",
        "localhost",
        f"localhost:{LAUNCH_PORT}",
        "[::1]",
        f"[::1]:{LAUNCH_PORT}",
    ],
)
def test_every_loopback_host_spelling_is_accepted_with_or_without_a_port(
    client: TestClient, auth_headers: dict[str, str], host: str
) -> None:
    """The port is stripped before the comparison, and ``[::1]`` is a loopback.

    Without the accept half, the rebinding guard could be "correct" and also
    refuse every genuine request — the failure a rejection-only matrix cannot
    see. The bracketed IPv6 literal is here because stripping the port at the
    *first* colon would cut inside ``[::1]`` and turn the IPv6 loopback into a
    400 that looks like a security decision.
    """
    response = client.post(
        _url(READ_CAP), json=_read_payload(), headers={**auth_headers, "Host": host}
    )

    assert response.status_code == 200, response.text


@pytest.mark.parametrize("host", ["127.0.0.1:", "127.0.0.1:evil", "[::1", "[::1]junk"])
def test_a_malformed_host_authority_is_refused(
    client: TestClient, auth_headers: dict[str, str], host: str
) -> None:
    """A non-numeric port is not a request shape any real client produces.

    It matters because the port is what the Origin allowlist is derived from:
    accepting ``127.0.0.1:evil`` would put attacker-controlled text into that
    derived set for no reason at all.
    """
    response = client.post(
        _url(READ_CAP), json=_read_payload(), headers={**auth_headers, "Host": host}
    )

    assert response.status_code == 400


# ── The Origin check (T-19-12, D-21) ──────────────────────────────────────


def test_an_absent_origin_is_allowed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """D-21's non-browser half. ``curl``, the CLI and every scripted client send
    no ``Origin``; requiring one would break all of them for no gain, because a
    browser always sends it cross-origin."""
    assert "origin" not in {key.lower() for key in auth_headers}, (
        "the fixture headers already carry an Origin — this case proves nothing"
    )

    response = client.post(_url(READ_CAP), json=_read_payload(), headers=auth_headers)

    assert response.status_code == 200, response.text


@pytest.mark.parametrize("origin", sorted(ALLOWED_ORIGINS))
def test_the_servers_own_loopback_origin_is_allowed(
    client: TestClient, auth_headers: dict[str, str], origin: str
) -> None:
    """A same-machine page's ``Origin``, set explicitly — see this file's stated
    blind spot: without the explicit header this would be the absent case."""
    response = client.post(
        _url(READ_CAP), json=_read_payload(), headers={**auth_headers, "Origin": origin}
    )

    assert response.status_code == 200, response.text


def test_a_foreign_origin_is_refused_with_403_before_the_seam(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """403 — the status the MCP specification names for a present, invalid
    ``Origin``, and the seam is never entered."""
    calls = _spy_on_the_seam(monkeypatch)

    response = client.post(
        _url(READ_CAP),
        json=_read_payload(),
        headers={**auth_headers, "Origin": "http://evil.example.com"},
    )

    assert response.status_code == 403
    assert calls == [], "the seam ran despite a foreign Origin"


def test_the_origin_allowlist_follows_the_launch_port(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The reason ``ALLOWED_ORIGINS`` is derived rather than hard-coded.

    A page served by this very server on ``--port 9999`` sends
    ``Origin: http://127.0.0.1:9999``. A hard-coded portless allowlist would
    refuse it, so every browser request against a non-default port would be
    foreign — a break whose symptom is "the UI stopped working" and whose cause
    looks like a security control doing its job.

    The negative half is what makes it a check rather than a widening: a
    *different* loopback port (a Vite dev server on 5173) is still refused.
    """
    same_port = client.post(
        _url(READ_CAP),
        json=_read_payload(),
        headers={
            **auth_headers,
            "Host": f"127.0.0.1:{LAUNCH_PORT}",
            "Origin": f"http://127.0.0.1:{LAUNCH_PORT}",
        },
    )
    assert same_port.status_code == 200, same_port.text

    other_port = client.post(
        _url(READ_CAP),
        json=_read_payload(),
        headers={
            **auth_headers,
            "Host": f"127.0.0.1:{LAUNCH_PORT}",
            "Origin": "http://127.0.0.1:5173",
        },
    )
    assert other_port.status_code == 403


def test_the_derived_origin_set_covers_every_allowed_host_spelling() -> None:
    """The derivation itself, so it cannot drift from ``ALLOWED_HOSTS``.

    A hostname added to the host allowlist and forgotten in the origin
    allowlist is a hole whose failure mode is silence, which is why this asserts
    the derivation rather than a literal set.
    """
    assert allowed_origins() == frozenset(f"http://{host}" for host in ALLOWED_HOSTS)
    assert allowed_origins(LAUNCH_PORT) == frozenset(
        f"http://{host}:{LAUNCH_PORT}" for host in ALLOWED_HOSTS
    )
    assert ALLOWED_ORIGINS == allowed_origins()


# ── The token check (T-19-07, T-19-08) ────────────────────────────────────


def test_a_missing_token_is_refused_before_the_seam(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _spy_on_the_seam(monkeypatch)

    response = client.post(_url(READ_CAP), json=_read_payload())

    assert response.status_code == 401
    assert calls == [], "the seam ran despite a missing token"


def test_a_token_differing_in_one_character_is_refused(client: TestClient) -> None:
    """One character, not a wholly different string.

    A wrong-token case built from an obviously different value would still pass
    against a comparison that only checked the length, or the first byte.
    """
    wrong = API_TOKEN[:-1] + ("x" if API_TOKEN[-1] != "x" else "y")
    assert wrong != API_TOKEN and len(wrong) == len(API_TOKEN)

    response = client.post(
        _url(READ_CAP), json=_read_payload(), headers={TOKEN_HEADER: wrong}
    )

    assert response.status_code == 401


def test_the_correct_token_is_accepted(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The positive control for the two cases above."""
    response = client.post(_url(READ_CAP), json=_read_payload(), headers=auth_headers)

    assert response.status_code == 200, response.text


def test_the_token_comparison_is_constant_time_and_on_bytes(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """``secrets.compare_digest``, never ``==``.

    ``==`` short-circuits on the first differing byte and leaks the token prefix
    through timing. Timing cannot be asserted directly in a unit test, so the
    *call* is asserted instead — and with it the operand type, because
    ``compare_digest`` raises ``TypeError`` on a ``str`` carrying a non-ASCII
    code point and header values reach the guard latin-1 decoded.
    """
    observed: list[tuple[object, object]] = []
    real = secrets_module.compare_digest

    def recording(left, right):
        observed.append((left, right))
        return real(left, right)

    monkeypatch.setattr(secrets_module, "compare_digest", recording)

    response = client.post(_url(READ_CAP), json=_read_payload(), headers=auth_headers)

    assert response.status_code == 200, response.text
    assert observed, "the token was compared without secrets.compare_digest"
    left, right = observed[-1]
    assert isinstance(left, bytes) and isinstance(right, bytes), (
        "compare_digest was handed str operands — a non-ASCII header value would "
        "then raise TypeError and turn the 401 into a 500"
    )


def test_a_non_ascii_token_is_refused_rather_than_crashing(client: TestClient) -> None:
    """One high byte must not convert the authentication check into a 500.

    An authentication check that can be crashed is an authentication check that
    can be probed. Starlette decodes header values as latin-1, so this is a
    reachable input, not a hypothetical one.
    """
    response = client.post(
        _url(READ_CAP),
        json=_read_payload(),
        headers={TOKEN_HEADER.encode("ascii"): "café".encode("latin-1")},
    )

    assert response.status_code == 401


# ── The ordering of the three checks (D-23) ───────────────────────────────


def test_the_checks_run_in_the_order_host_origin_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A request that fails all three is answered by the *first* failure.

    Order is not cosmetic. Answering a tokenless request with 403 would tell an
    unauthenticated caller which of its headers the server disliked, and the
    Host check has to come first because it is the one that decides whether this
    is a rebound request at all.
    """
    calls = _spy_on_the_seam(monkeypatch)
    bad_everything = {
        "Host": "evil.example.com",
        "Origin": "http://evil.example.com",
    }

    all_three = client.post(_url(READ_CAP), json=_read_payload(), headers=bad_everything)
    assert all_three.status_code == 400

    origin_and_token = client.post(
        _url(READ_CAP),
        json=_read_payload(),
        headers={"Origin": "http://evil.example.com"},
    )
    assert origin_and_token.status_code == 403

    token_only = client.post(_url(READ_CAP), json=_read_payload())
    assert token_only.status_code == 401

    assert calls == [], "the seam ran despite a refusal"


def test_every_refusal_carries_the_same_body_shape(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """One rendering for all three (D-23).

    This is the concrete content of the "``TrustedHostMiddleware`` would give us
    two shapes" objection: it only means something if this side actually matches
    FastAPI's own ``{"detail": ...}``. It is also what lets plan 19-07 swap one
    function rather than three.
    """
    responses = [
        client.post(
            _url(READ_CAP),
            json=_read_payload(),
            headers={**auth_headers, "Host": "evil.example.com"},
        ),
        client.post(
            _url(READ_CAP),
            json=_read_payload(),
            headers={**auth_headers, "Origin": "http://evil.example.com"},
        ),
        client.post(_url(READ_CAP), json=_read_payload()),
    ]

    assert [response.status_code for response in responses] == [400, 403, 401]
    for response in responses:
        body = response.json()
        assert set(body) == {"detail"}
        assert isinstance(body["detail"], str) and body["detail"]
        assert "evil.example.com" not in body["detail"], (
            "the refusal echoed attacker-controlled text back into the body"
        )


# ── No CORS, and the drive-by content types (D-22, D-05) ──────────────────


def test_no_cors_middleware_is_installed(install_root: Path) -> None:
    """T-19-02. The property the single-route shape was chosen for.

    Permissive CORS is the one edit to this surface that looks like a
    convenience and is a vulnerability: it would answer the preflight that
    ``X-Construct-Token``'s non-safelisted status forces, make the token header
    usable cross-origin, and demote ``Origin`` validation from defence in depth
    to the sole remaining check.
    """
    app = create_app(install_root, API_TOKEN)
    try:
        installed = {middleware.cls.__name__ for middleware in app.user_middleware}
        assert "CORSMiddleware" not in installed
        assert "TrustedHostMiddleware" not in installed
        assert "LocalhostGuard" in installed
    finally:
        set_launch_install_root(None)


def test_a_cross_origin_preflight_is_answered_by_nothing(client: TestClient) -> None:
    """The other half of D-22, from the request side rather than the stack side.

    A browser sends this ``OPTIONS`` before it will let a page use
    ``X-Construct-Token`` cross-origin. No ``Access-Control-Allow-Origin`` comes
    back, so the browser never sends the real request.
    """
    response = client.options(
        _url(READ_CAP),
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": TOKEN_HEADER,
        },
    )

    assert "access-control-allow-origin" not in {
        key.lower() for key in response.headers
    }
    assert response.status_code == 403


@pytest.mark.parametrize(
    "content_type",
    [
        "text/plain",
        "application/x-www-form-urlencoded",
        "multipart/form-data; boundary=x",
        None,
    ],
    ids=["text-plain", "form-urlencoded", "multipart", "no-content-type"],
)
def test_a_drive_by_content_type_never_reaches_a_capability(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    content_type: str | None,
) -> None:
    """The measured basis for D-05's security rationale.

    The three content types a cross-origin *simple* request may carry are the
    first three rows; the fourth is a ``fetch`` of a typeless ``Blob``, which
    sends no ``Content-Type`` at all and is also a simple request. None of them
    reaches a capability with a parsed payload.

    Measured against **FastAPI 0.141.1**, where the typeless row holds because
    ``strict_content_type`` defaults to ``True``. That is a framework default
    rather than something this project enforces — which is exactly why it is
    pinned here: were it turned off, or were the dependency floor to slip below
    the release that introduced it, a typeless JSON body would be parsed and
    dispatched, and nothing else in the codebase would notice.
    """
    calls = _spy_on_the_seam(monkeypatch)
    headers = dict(auth_headers)
    if content_type is not None:
        headers["Content-Type"] = content_type

    response = client.post(
        _url(READ_CAP), content=b'{"payload": {"workspace_id": "demo"}}', headers=headers
    )

    assert response.status_code == 422, response.text
    assert calls == [], f"a {content_type or 'typeless'} body reached a capability"


def test_a_json_content_type_is_the_positive_control(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same bytes, with ``application/json``, do reach the capability.

    Without this the matrix above would pass against a payload that could never
    have been dispatched for an unrelated reason.
    """
    calls = _spy_on_the_seam(monkeypatch)

    client.post(
        _url(READ_CAP),
        content=b'{"payload": {"workspace_id": "demo"}}',
        headers={**auth_headers, "Content-Type": "application/json"},
    )

    assert calls == [READ_CAP]


# ── Concurrency: the token is minted once per process ─────────────────────


def test_concurrent_good_tokens_all_pass_while_a_bad_one_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Interleaving cannot change the outcome, because nothing rotates.

    The launch token is minted once per process and never rotated mid-run, and
    the guard holds it as instance state on a middleware built once by
    ``create_app``. So there is no window in which a good token is briefly wrong
    or a bad one briefly right — which is the property this asserts, rather than
    hoping a race simply did not happen to fire.
    """
    def send(headers: dict[str, str]) -> int:
        return client.post(_url(READ_CAP), json=_read_payload(), headers=headers).status_code

    good = [auth_headers] * 10
    bad = {TOKEN_HEADER: API_TOKEN + "-wrong"}

    with ThreadPoolExecutor(max_workers=11) as pool:
        futures = [pool.submit(send, headers) for headers in good]
        refused = pool.submit(send, bad)
        statuses = [future.result() for future in futures]

    assert statuses == [200] * 10
    assert refused.result() == 401


# ── The claim a status code cannot make ───────────────────────────────────
#
# Criterion 4's wording is "refused **before it reaches a capability**". A status
# code is the guard reporting on itself: a guard that returned 403 *after*
# dispatching would satisfy every assertion above. The answer below is the
# workspace tree itself — hashed before and after each refused request, with a
# positive control proving the payload would otherwise have written.


def _tree_hashes(root: Path) -> dict[str, str]:
    """Every file under ``root`` as ``relative path -> content hash``.

    Paths *and* contents, because either alone misses half the question: a
    mapping of paths only would not see a card being edited, and a set of
    hashes only would not see a file being renamed or removed.
    """
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _card_payload(title: str) -> dict:
    """A payload that is valid for ``knowledge.card.create`` in every respect.

    The entire force of the rejection cases is that this request *would* have
    written something had it reached dispatch — so it addresses the workspace by
    id (``workspace`` is path-shaped and refused at the boundary by D-10) and
    fills every required field of ``CardCreateInput``.
    """
    return {
        "payload": {
            "workspace_id": "demo",
            "title": title,
            "epistemic_type": "finding",
            "domains": ["test-domain"],
            "content_categories": ["test-category"],
            "confidence": 3,
            "source_tier": 3,
        }
    }


WRITE_CAP = "knowledge.card.create"


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        ({"Origin": "http://evil.example.com"}, 403),
        ({}, 401),
        ({"Host": "evil.example.com"}, 400),
    ],
    ids=["foreign-origin", "no-token", "foreign-host"],
)
def test_a_refused_write_leaves_the_tree_byte_identical(
    client: TestClient,
    install_root: Path,
    auth_headers: dict[str, str],
    headers: dict[str, str],
    expected_status: int,
) -> None:
    """The ordering proof, expressed as bytes on disk rather than as a status."""
    request_headers = dict(headers)
    if expected_status != 401:
        request_headers.update(auth_headers)

    before = _tree_hashes(install_root)
    response = client.post(
        _url(WRITE_CAP), json=_card_payload("Refused Card"), headers=request_headers
    )
    after = _tree_hashes(install_root)

    assert response.status_code == expected_status
    assert after == before, "a refused request changed the workspace"


def test_the_same_payload_with_correct_headers_does_change_the_tree(
    client: TestClient, install_root: Path, auth_headers: dict[str, str]
) -> None:
    """The positive control the three cases above are worthless without.

    A payload that was invalid for some unrelated reason would leave the tree
    identical under every rejection case *and* under an accepted one, and all
    three would still pass — the same vacuity this phase's coverage guard
    exists to catch. So the identical payload, with correct ``Host``, no
    ``Origin`` and the right token, must write.
    """
    before = _tree_hashes(install_root)
    response = client.post(
        _url(WRITE_CAP), json=_card_payload("Accepted Card"), headers=auth_headers
    )
    after = _tree_hashes(install_root)

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True, response.text
    assert after != before, "the control payload wrote nothing — the proof is vacuous"
    assert set(after) - set(before), "the control payload created no new file"
