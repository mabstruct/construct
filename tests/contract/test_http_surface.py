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

import os
import socket
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import typer
from fastapi.testclient import TestClient

from construct.api import (
    CAPABILITY_ROUTE,
    DEFAULT_API_PORT,
    TOKEN_FILE_RELPATH,
    TOKEN_HEADER,
)
from construct.api.app import DISCOVERY_ROUTE, _serialize_result, create_app
from construct.capabilities.catalog import get_registry
from construct.capabilities.registry import CapabilityRecord
from construct.capabilities.workspaces import (
    INSTALL_ROOT_FIELD,
    PATH_SHAPED_KEYS,
    WORKSPACE_FIELD,
    set_launch_install_root,
)

from tests.contract.conftest import API_TOKEN


def _url(cap_id: str) -> str:
    return CAPABILITY_ROUTE.format(cap_id=cap_id)


# ── The exposure ledger, read rather than trusted (D-18) ──────────────────
#
# ``src/construct/api/COVERAGE.md`` is a *machine-read* artifact: the coverage
# guard subtracts its exclusions table from the registry, so an exclusion added
# as prose does not quietly go undocumented — it fails the arithmetic. Located
# from the package's own ``__file__`` so a moved package moves the ledger with
# it, and parsed with string operations rather than a markdown library, because
# the file is written to a fixed shape declared in its own "How to read it"
# section.

COVERAGE_LEDGER = Path(
    sys.modules["construct.api.app"].__file__
).with_name("COVERAGE.md")

CAPABILITY_TABLE_HEADING = "Capability table"
EXCLUSIONS_HEADING = "Exclusions"
NON_CAPABILITY_ROUTES_HEADING = "Non-capability routes"


def _ledger_section(heading: str) -> list[str]:
    """The lines under ``## {heading}``, up to the next ``##``."""
    lines = COVERAGE_LEDGER.read_text(encoding="utf-8").splitlines()
    marker = f"## {heading}"
    assert marker in lines, (
        f"{COVERAGE_LEDGER.name} has no '{marker}' section — the guard reads the "
        "ledger by fixed headings, so renaming one silently detaches the test "
        "from the document it is supposed to constrain"
    )
    rest = lines[lines.index(marker) + 1 :]
    end = next(
        (index for index, line in enumerate(rest) if line.startswith("## ")),
        len(rest),
    )
    return rest[:end]


def _ledger_first_column(heading: str) -> list[str]:
    """The first cell of every data row of the pipe table under ``heading``.

    Malformed rows are **asserted on, never skipped**. A parser that skipped what
    it could not read would turn a typo into a silently missing row, which is the
    same failure as an undocumented exclusion — the thing this ledger exists to
    make impossible.
    """
    rows = [line for line in _ledger_section(heading) if line.lstrip().startswith("|")]
    assert len(rows) >= 2, (
        f"the '{heading}' section has no pipe table (found {len(rows)} table "
        "lines); the guard needs a header row and a separator row even when the "
        "table carries no data rows"
    )
    _header, separator, *data = rows
    assert set(separator.replace("|", "").strip()) <= set("-: "), (
        f"the second table line under '{heading}' is not a markdown separator: "
        f"{separator!r}"
    )

    values: list[str] = []
    for row in data:
        cell = row.strip().strip("|").split("|")[0].strip()
        assert cell.startswith("`") and cell.endswith("`") and len(cell) > 2, (
            f"first column of a '{heading}' row is not a backticked value: "
            f"{row!r}"
        )
        values.append(cell.strip("`"))
    return values


# ── D-06: the discovery endpoint ──────────────────────────────────────────


def test_the_discovery_endpoint_advertises_every_registered_capability(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Cardinality *and* identity, against a live registry read.

    Asserted as a relationship between two measurements rather than against a
    name list: a name list would need editing every time the registry grows, and
    an editor who is already editing the expectation is no longer being told
    anything by the test.
    """
    response = client.get(DISCOVERY_ROUTE, headers=auth_headers)

    assert response.status_code == 200, response.text
    advertised = response.json()["capabilities"]
    registered = get_registry().list()

    assert len(advertised) == len(registered), (
        "the discovery endpoint advertises a different number of capabilities "
        f"than the registry holds: {len(advertised)} vs {len(registered)}"
    )
    assert {entry["id"] for entry in advertised} == {cap.id for cap in registered}
    for entry in advertised:
        assert set(entry) == {"id", "name", "description", "input_schema"}
        assert entry["name"] and entry["description"]


def test_the_discovery_endpoint_is_not_the_mcp_projection(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The failure this endpoint was one line away from shipping.

    ``list_mcp_tools()`` skips every capability whose ``mcp_tool_name`` is
    ``None``. Iterating it would have produced a surface missing six real
    capabilities — and a membership test over what it *did* return would have
    passed, because every id present would have been correct. So the six are
    named here explicitly: they are the measurement that makes "iterate
    ``list()``" a decision rather than a coincidence.
    """
    registry = get_registry()
    unadvertised_over_mcp = {cap.id for cap in registry.list() if cap.mcp_tool_name is None}
    assert unadvertised_over_mcp, (
        "every capability now declares an MCP tool name, so this test no longer "
        "distinguishes list() from list_mcp_tools() — replace it rather than "
        "letting it pass vacuously"
    )

    response = client.get(DISCOVERY_ROUTE, headers=auth_headers)
    advertised = {entry["id"] for entry in response.json()["capabilities"]}

    missing = unadvertised_over_mcp - advertised
    assert not missing, (
        "these capabilities have no MCP tool name and are absent from the HTTP "
        f"discovery endpoint — it is iterating the MCP projection: {sorted(missing)}"
    )
    assert len(advertised) > len(registry.list_mcp_tools())


def test_the_advertised_schema_is_the_capabilitys_own_declared_model(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """GOV-01's schema-advertising half, recovered on HTTP (D-06 / Phase 18 D-21).

    Equality against ``model_json_schema()`` rather than a spot check on one
    field: the browser builds its form from this, so a schema that is *nearly*
    the declared one produces a form that silently omits a field.
    """
    response = client.get(DISCOVERY_ROUTE, headers=auth_headers)
    advertised = {entry["id"]: entry["input_schema"] for entry in response.json()["capabilities"]}

    wrong = [
        cap.id
        for cap in get_registry().list()
        if advertised[cap.id] != cap.input_model.model_json_schema()
    ]
    assert wrong == [], f"advertised schema differs from the declared model for: {wrong}"


def test_the_discovery_order_is_the_registrys_and_is_stable(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Id-sorted, and the same on the next call.

    Two claims because either alone is weak: a stable-but-arbitrary order would
    depend on import sequence, and a sorted-once order says nothing about the
    second poll a browser makes.
    """
    first = client.get(DISCOVERY_ROUTE, headers=auth_headers).json()["capabilities"]
    second = client.get(DISCOVERY_ROUTE, headers=auth_headers).json()["capabilities"]

    expected = [cap.id for cap in get_registry().list()]
    assert [entry["id"] for entry in first] == expected
    assert [entry["id"] for entry in second] == expected
    assert expected == sorted(expected)


def test_the_discovery_endpoint_never_answers_with_an_empty_list(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The vacuity floor. Every assertion above is a comparison against the
    registry, and all of them hold trivially if both sides are empty."""
    assert len(get_registry().list()) > 0
    body = client.get(DISCOVERY_ROUTE, headers=auth_headers).json()
    assert body["capabilities"], "the registry is non-empty but discovery returned nothing"


def test_the_discovery_endpoint_is_behind_the_same_trust_boundary(
    client: TestClient,
) -> None:
    """A ``GET`` is still a request. Discovery publishes the shape of every write
    capability this server exposes, so an unauthenticated reader would get a map
    of the surface for free."""
    assert client.get(DISCOVERY_ROUTE).status_code == 401


# ── D-18: the exposure ledger is a real, parseable document ───────────────


def test_the_ledger_has_one_row_per_registered_capability() -> None:
    """The ledger is only worth parsing if it is complete and unduplicated.

    Both directions are asserted, and the failure message names the offending
    ids — a diff that says "29 != 30" tells a future reader nothing about which
    capability they forgot.
    """
    listed = _ledger_first_column(CAPABILITY_TABLE_HEADING)
    registered = {cap.id for cap in get_registry().list()}

    duplicates = sorted({cap_id for cap_id in listed if listed.count(cap_id) > 1})
    assert duplicates == [], f"{COVERAGE_LEDGER.name} lists these twice: {duplicates}"
    assert set(listed) == registered, (
        f"{COVERAGE_LEDGER.name} is out of step with the registry — missing rows "
        f"for: {sorted(registered - set(listed))}; rows for unregistered "
        f"capabilities: {sorted(set(listed) - registered)}"
    )


def test_the_ledger_records_no_exclusions_today() -> None:
    """Zero rows is the current finding, asserted so it cannot drift silently.

    This test failing is not automatically a bug: it means somebody excluded a
    capability from the HTTP surface. What it forbids is doing so *without*
    anyone noticing, which is T-19-19.
    """
    assert _ledger_first_column(EXCLUSIONS_HEADING) == [], (
        "the exclusions table is no longer empty; a capability has been made "
        "unreachable over HTTP and this test is the notification"
    )


def test_every_non_dispatch_api_route_is_documented_in_the_ledger(
    install_root: Path,
) -> None:
    """D-20: no undocumented surface.

    Asserted as a subset in one direction only, and deliberately: the ledger may
    name a route *before* the plan that adds it (``POST /api/runs`` today), so
    requiring equality would fail on a correct forward reference. The direction
    that catches something is the other one — a route the app serves that the
    ledger has never heard of.
    """
    app = create_app(install_root, API_TOKEN)
    try:
        documented = {
            line.strip().strip("|").split("|")[0].strip().strip("`")
            for line in _ledger_section(NON_CAPABILITY_ROUTES_HEADING)
            if line.lstrip().startswith("|")
        }
        served = {
            f"{method} {route.path}"
            for route in app.routes
            if getattr(route, "path", "").startswith("/api")
            and "{cap_id}" not in getattr(route, "path", "")
            for method in getattr(route, "methods", set())
            if method not in {"HEAD", "OPTIONS"}
        }
    finally:
        set_launch_install_root(None)

    assert served <= documented, (
        "these non-capability routes are served but absent from "
        f"{COVERAGE_LEDGER.name}'s non-capability-routes table: "
        f"{sorted(served - documented)}"
    )


# ── HTTP-02: the coverage guard (T-19-19) ─────────────────────────────────
#
# Why this section is written the way it is, stated once so the shape below is
# read as a decision rather than as ceremony.
#
# Under D-05 there is a single static route with a path parameter, so "the
# server module was never hand-edited to add a capability" is true *by
# construction*. A guard that asserted it would prove nothing. The claim worth
# guarding is the one that can actually fail: **every registered capability is
# reachable**. Reachability is a runtime property — a capability can be
# registered, present in the id set, and still fail to resolve.
#
# So the guard asserts CARDINALITY, not membership. This project has been bitten
# twice by set-membership guards that passed over a subset (WR-01, and the
# ``list_mcp_tools`` trap the discovery endpoint above sidesteps). A membership
# assertion answers "is X listed?"; the question here is "is anything missing?",
# and only counting answers it.

#: The probe key. Declared by no capability, and not a path-shaped key — both
#: asserted below rather than assumed, because either being false would turn a
#: refusal into a *different* refusal and the probe would stop discriminating.
#:
#: Its 422 is produced by ``extra="forbid"``, which
#: ``tests/contract/test_capability_seam.py`` pins for the whole registry. That
#: is what makes this probe registry-derived rather than a hand-written payload
#: table: the payload works for every capability *because* of a guarded
#: property, not because somebody enumerated the fields.
PROBE_KEY = "__coverage_probe_undeclared_field__"


def _probe_response(client: TestClient, auth_headers: dict[str, str], cap_id: str):
    return client.post(
        _url(cap_id), json={"payload": {PROBE_KEY: "x"}}, headers=auth_headers
    )


def _classify(response, cap_id: str) -> str:
    """``"reached"``, ``"route-missing"``, or a description of neither.

    The discriminator, spelled out. A **404** means the id never resolved: the
    seam raised ``CapabilityNotFoundError`` before touching a model. A **422
    naming this capability** means the opposite — the record resolved, the
    declared model ran, and it rejected the probe key. So the two outcomes are
    distinguishable evidence rather than "some status code came back", which is
    the degenerate form this guard must not collapse into.

    The id is required to be *in the reason*, not merely in the request: a 422
    that did not name the capability would be the D-10 envelope gate firing
    ahead of dispatch, which is a refusal that says nothing about reachability.
    """
    if response.status_code == 404:
        return "route-missing"
    if response.status_code == 422 and cap_id in response.text:
        return "reached"
    return f"unclassified ({response.status_code}: {response.text[:120]})"


def _measure_reachability(
    client: TestClient, auth_headers: dict[str, str]
) -> tuple[set[str], dict[str, str]]:
    """``(reachable ids, {unreachable id: why})`` — both driven from the registry."""
    reachable: set[str] = set()
    unreachable: dict[str, str] = {}
    for capability in get_registry().list():
        verdict = _classify(
            _probe_response(client, auth_headers, capability.id), capability.id
        )
        if verdict == "reached":
            reachable.add(capability.id)
        else:
            unreachable[capability.id] = verdict
    return reachable, unreachable


def _assert_full_coverage(
    reachable: set[str], excluded: set[str], registered: set[str]
) -> None:
    """The assertion itself, factored out so the meta-test can run *this* code.

    A meta-test that re-implemented the assertion would prove its own copy
    fails, which is worth nothing. Three claims in this order, because each
    catches something the next cannot: cardinality catches a capability that is
    simply missing; disjointness catches one counted twice (documented as
    excluded *and* measured reachable, which would let a missing one hide behind
    an inflated total); the union catches a set that is the right size and the
    wrong contents.
    """
    assert len(reachable) + len(excluded) == len(registered), (
        "capability coverage does not add up — "
        f"{len(reachable)} reachable + {len(excluded)} documented exclusions "
        f"!= {len(registered)} registered. Unaccounted for: "
        f"{sorted(registered - reachable - excluded)}"
    )
    overlap = reachable & excluded
    assert not overlap, (
        "these capabilities are documented as excluded from the HTTP surface "
        f"and are reachable anyway — the ledger is wrong or the exclusion never "
        f"took effect: {sorted(overlap)}"
    )
    assert reachable | excluded == registered, (
        "the reachable and excluded sets do not exhaust the registry. Registered "
        f"but accounted for nowhere: {sorted(registered - (reachable | excluded))}; "
        f"accounted for but not registered: {sorted((reachable | excluded) - registered)}"
    )


def test_the_probe_key_discriminates_before_it_is_trusted() -> None:
    """The probe's two preconditions, asserted rather than assumed.

    If ``PROBE_KEY`` were declared by some capability, that capability's probe
    would succeed and run its handler. If it were path-shaped, the D-10 envelope
    gate would refuse it ahead of dispatch and every id — registered or not —
    would answer 422, collapsing the discriminator.
    """
    assert PROBE_KEY not in PATH_SHAPED_KEYS
    declaring = [
        capability.id
        for capability in get_registry().list()
        if PROBE_KEY in capability.input_model.model_fields
    ]
    assert declaring == [], f"the probe key is a declared field of: {declaring}"


def test_an_unregistered_id_is_route_missing_and_a_registered_one_is_not(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The explicit discriminator case.

    Without this, "every registered id returned something other than 404" would
    be satisfiable by a server that answered 422 to literally everything.
    ``does.not.exist`` is the control: it must be classified route-missing while
    a real id is classified reached, using the same classifier.
    """
    missing = client.post(
        _url("does.not.exist"), json={"payload": {PROBE_KEY: "x"}}, headers=auth_headers
    )
    assert missing.status_code == 404, missing.text
    assert _classify(missing, "does.not.exist") == "route-missing"

    live = get_registry().list()[0].id
    assert _classify(_probe_response(client, auth_headers, live), live) == "reached"


def test_every_registered_capability_is_reachable_over_http(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """HTTP-02's criterion 1, as a claim about all of them.

    The exclusions come from ``COVERAGE.md``'s parsed table, not from a set
    written in this file: an exclusion that lived here would be invisible to
    anybody reading the ledger, and one that lived only in the ledger's prose
    would be invisible to this test. Parsing is what keeps the two honest about
    each other (D-18).
    """
    reachable, unreachable = _measure_reachability(client, auth_headers)
    registered = {capability.id for capability in get_registry().list()}
    excluded = set(_ledger_first_column(EXCLUSIONS_HEADING))

    assert unreachable == {}, (
        "these registered capabilities are not reachable over HTTP: "
        f"{unreachable}"
    )
    _assert_full_coverage(reachable, excluded, registered)


def test_the_coverage_guard_fails_when_a_capability_is_unreachable() -> None:
    """The non-vacuity meta-test — the reason this file exists in this shape.

    A guard nobody has seen fail is a guard nobody knows works. That is not a
    general anxiety here: under a single-route surface the *naive* version of
    this guard is genuinely vacuous, so "it passes" carries no information until
    somebody demonstrates it can stop passing.

    Both failure arms are exercised, against the real ``_assert_full_coverage``:

    1. a capability measured unreachable and not documented as excluded — the
       cardinality arm, i.e. the regression this guard is for;
    2. a capability counted twice, reachable *and* excluded — the disjointness
       arm, which is how an unreachable capability could otherwise hide behind
       a total that still adds up.

    Each assertion also has to *name* the offending capability, because a
    coverage regression is read as a diff by somebody who did not write it.
    """
    registered = {capability.id for capability in get_registry().list()}
    victim = sorted(registered)[0]

    with pytest.raises(AssertionError) as cardinality_failure:
        _assert_full_coverage(registered - {victim}, set(), registered)
    assert victim in str(cardinality_failure.value)

    with pytest.raises(AssertionError) as disjointness_failure:
        _assert_full_coverage(registered, {victim}, registered)
    assert victim in str(disjointness_failure.value)


def test_the_guard_would_notice_a_capability_the_app_cannot_reach(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same non-vacuity claim, made end to end instead of on the assertion.

    The registry is presented as holding one capability the app cannot resolve,
    and the *measured* pipeline — probe, classify, count — is run against it.
    This is the arm that would catch a probe which had quietly stopped
    discriminating, which the pure-assertion meta-test above cannot see.
    """
    registry = get_registry()
    real = registry.list()
    phantom = CapabilityRecord(
        id="phantom.never.registered",
        name="Phantom",
        description="Registered in the listing only — the app cannot resolve it.",
        input_model=real[0].input_model,
        output_model=real[0].output_model,
        handler=real[0].handler,
    )
    monkeypatch.setattr(type(registry), "list", lambda self: [*real, phantom])

    reachable, unreachable = _measure_reachability(client, auth_headers)
    assert unreachable == {phantom.id: "route-missing"}

    with pytest.raises(AssertionError) as failure:
        _assert_full_coverage(
            reachable,
            set(_ledger_first_column(EXCLUSIONS_HEADING)),
            {capability.id for capability in registry.list()},
        )
    assert phantom.id in str(failure.value)


# ── Dispatch resolves a full id, never a prefix ───────────────────────────


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("curation.run", "curation.review"),
        ("knowledge.card.list", "knowledge.connection.list"),
    ],
)
def test_two_ids_sharing_a_prefix_route_to_different_capabilities(
    client: TestClient, auth_headers: dict[str, str], first: str, second: str
) -> None:
    """The path parameter matches a whole capability id.

    A prefix match would be silent and severe: ``curation.run`` is a *write*
    workflow and ``curation.review`` is not, so a caller asking for one and
    getting the other would be told nothing. The reason string names the
    capability that actually ran, which is what makes this assertable at all.
    """
    for target, other in ((first, second), (second, first)):
        response = _probe_response(client, auth_headers, target)
        assert response.status_code == 422, response.text
        detail = response.json()["detail"]
        assert target in detail
        assert other not in detail


# ── An empty payload reaches the seam, not a 500 ──────────────────────────


def _requires_a_field(cap_id: str) -> bool:
    model = get_registry().get(cap_id).input_model
    return any(field.is_required() for field in model.model_fields.values())


def test_no_capability_model_is_all_optional_today() -> None:
    """The measured property the parametrisation below depends on.

    Asserted separately so the dependency is visible: if a capability ever
    declares an all-optional model, ``{"payload": {}}`` would *run its handler*
    rather than being rejected, and the case below would silently change from
    "the seam validated" to "the workflow executed". This test is where that
    reader finds out.
    """
    all_optional = [
        capability.id
        for capability in get_registry().list()
        if not _requires_a_field(capability.id)
    ]
    assert all_optional == [], (
        "these capabilities now accept an empty payload, so the empty-payload "
        f"case must stop being parametrised over them: {all_optional}"
    )


@pytest.mark.parametrize(
    "cap_id",
    [
        capability.id
        for capability in get_registry().list()
        if _requires_a_field(capability.id)
    ],
)
def test_an_empty_payload_gets_the_capabilitys_own_reason_not_a_server_error(
    client: TestClient, auth_headers: dict[str, str], cap_id: str
) -> None:
    """``{}`` is a shape a browser form sends on its first render.

    The failure mode being excluded is a **500**: an adapter that assumed a
    non-empty payload would turn "you left a field blank" into "the server
    broke", and the caller would have no way to tell those apart. The reason
    must be the capability's own, so it names the capability and the missing
    field.
    """
    response = client.post(_url(cap_id), json={"payload": {}}, headers=auth_headers)

    assert response.status_code == 422, response.text
    assert cap_id in response.json()["detail"]


# ── D-10, server-side, for every capability (T-19-03 / T-19-17) ───────────


def _declared_path_field(cap_id: str) -> str:
    field = WORKSPACE_FIELD.get(cap_id) or INSTALL_ROOT_FIELD.get(cap_id)
    assert field is not None, f"{cap_id} has no declared path field to attack"
    return field


def _tree(root: Path) -> dict[str, int]:
    """Every path under ``root``, with file sizes. Directories carry ``-1``."""
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size if path.is_file() else -1)
        for path in sorted(root.rglob("*"))
    }


@pytest.mark.parametrize("cap_id", [capability.id for capability in get_registry().list()])
def test_no_capability_accepts_a_filesystem_path_over_http(
    client: TestClient,
    auth_headers: dict[str, str],
    install_root: Path,
    cap_id: str,
    tmp_path: Path,
) -> None:
    """The server-side half of D-10, asserted for **every** capability.

    "The HTTP client only ever sends ``workspace_id``" is not a property the
    adapter's own source can establish: under a single envelope the payload
    arrives verbatim from an untrusted caller (T-19-03), and ``install_root`` in
    particular would let a browser move the boundary the whole surface is scoped
    by (T-19-17). So the refusal is asserted per capability, using **that
    capability's own declared field name** derived from the maps — the realistic
    attack, and one that keeps working when a field is renamed.

    The tree is compared before and after because a status code alone would not
    catch a refusal that fired *after* the handler had already written. The
    target sits inside the install root so a capability that ran would leave
    evidence exactly where this looks.
    """
    payload = {_declared_path_field(cap_id): str(install_root / "attacker-supplied")}
    before = _tree(install_root)

    response = client.post(_url(cap_id), json={"payload": payload}, headers=auth_headers)

    assert response.status_code == 422, response.text
    assert _declared_path_field(cap_id) in response.json()["detail"]
    assert not (install_root / "attacker-supplied").exists()
    assert _tree(install_root) == before, (
        f"the install-root tree changed while refusing a path-shaped key for {cap_id}"
    )


def test_the_path_key_refusal_happens_before_dispatch_for_every_capability(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """"Refused" must mean "the seam was never entered", not "the answer was 422".

    The unchanged tree above shows no *write* happened; it cannot show that no
    handler ran, and a read handler that ran on a caller-supplied path would
    already be an information disclosure. So the seam is spied on and asserted
    zero-called across the whole registry.

    Written as one test over every capability rather than parametrised: the
    claim is about the set ("no capability dispatched"), and the install-root
    fixture is expensive enough that 29 rebuilds to make the same point would be
    paying for a nicer failure line.
    """
    calls: list[str] = []
    monkeypatch.setattr(
        type(get_registry()),
        "invoke",
        lambda self, cap_id, payload: calls.append(cap_id),
    )

    statuses = {}
    for capability in get_registry().list():
        payload = {_declared_path_field(capability.id): "/tmp/attacker-supplied"}
        statuses[capability.id] = client.post(
            _url(capability.id), json={"payload": payload}, headers=auth_headers
        ).status_code

    assert calls == [], f"a path-shaped payload reached the seam for: {sorted(set(calls))}"
    not_refused = {cap_id: code for cap_id, code in statuses.items() if code != 422}
    assert not_refused == {}, f"a path-shaped key was not refused with 422: {not_refused}"


# ── Concurrency (backstop strength — see the docstring) ───────────────────


def test_two_concurrent_invocations_each_return_their_own_result(
    client: TestClient, install_root: Path, auth_headers: dict[str, str]
) -> None:
    """Two capabilities in flight at once, each answered with its own result.

    The property under test is that ``install_root`` and ``token`` are bound
    **once** by ``create_app`` and never mutated per request — if either were
    stashed on the app and rewritten per call, two overlapping requests could
    answer each other's question.

    **Backstop strength, stated so a reader does not over-read a green run.**
    ``TestClient`` drives the ASGI app in-process; it does not exercise the
    deployed server's socket handling, its event loop under real load, or
    uvicorn's worker model. A pass here is evidence about the *app object*, not
    proof about the running server. It is worth having anyway — the failure it
    would catch is per-request mutable state, which lives in the app object.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            cap_id: pool.submit(
                client.post,
                _url(cap_id),
                json={"payload": {"workspace_id": "demo"}},
                headers=auth_headers,
            )
            for cap_id in ("workspace.status", "workflow.status")
        }
        bodies = {cap_id: future.result() for cap_id, future in futures.items()}

    for cap_id, response in bodies.items():
        assert response.status_code == 200, f"{cap_id}: {response.text}"

    expected_status = _serialize_result(
        get_registry().invoke("workspace.status", {"path": str(install_root / "demo")})
    )
    assert bodies["workspace.status"].json() == expected_status

    workflow_body = bodies["workflow.status"].json()
    assert "success" in workflow_body and "items" not in workflow_body, (
        "workflow.status came back with workspace.status's result shape — the "
        "two responses were crossed"
    )


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
    is what makes every capability reachable.

    The subject is **dispatch** routes — the ones carrying ``{cap_id}``. Plan
    19-05 added ``GET /api/capabilities``, which is not one: it advertises the
    registry rather than dispatching through it, and D-20 puts it in the
    ledger's non-capability-routes table for exactly this reason. Selecting on
    the path *prefix* instead would have made this guard count it, and the
    obvious repair — loosening the count to 2 — would have quietly readmitted
    per-capability routes one at a time.
    """
    app = create_app(install_root, API_TOKEN)
    try:
        dispatch_routes = [
            route for route in app.routes if "{cap_id}" in getattr(route, "path", "")
        ]
        assert len(dispatch_routes) == 1
        assert dispatch_routes[0].path == CAPABILITY_ROUTE
        assert set(dispatch_routes[0].methods) == {"POST"}

        # And no route names a capability id literally — the property a
        # generator would break, which the count above cannot see on its own.
        registered = {cap.id for cap in get_registry().list()}
        paths = {getattr(route, "path", "") for route in app.routes}
        named = sorted(
            cap_id for cap_id in registered if any(cap_id in path for path in paths)
        )
        assert named == [], f"the route table names capabilities directly: {named}"
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


# ── `serve` owns its failure modes (D-04, D-17, T-19-11) ──────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]


def _serve_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the real ``construct`` CLI in a real child process.

    Copied from ``tests/integration/test_surface_parity.py::_cli`` for its two
    load-bearing choices: ``sys.executable`` (not a hardcoded ``.venv/bin/python``,
    which inside a git worktree imports a *different* checkout than the one under
    test) and a ``PYTHONPATH`` pinned to this checkout's ``src``. A real process is
    also the only way to observe a real exit code, which is half of what this
    section asserts.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "construct.cli", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )


def _free_port() -> int:
    """A port nothing is listening on right now.

    ``serve``'s pre-flight probe really binds, so a test that let it use
    ``DEFAULT_API_PORT`` would fail on any machine already running the server —
    an environment-dependent red that says nothing about the code. The declared
    default is asserted separately, by reading the option rather than by
    occupying the port.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _serve_in_process(monkeypatch: pytest.MonkeyPatch, args: list[str]):
    """Invoke ``construct serve`` with ``uvicorn.run`` stubbed out.

    ``serve``'s last statement blocks until the process is killed, so everything
    it does *before* that — the probe, the token file, the printed lines — is
    unobservable in a child process that has to be reaped. Stubbing the one
    blocking call is what makes those assertions deterministic instead of a
    poll-and-hope loop. The port-collision case below still uses a real child
    process, because an exit code cannot be faked in-process.

    Returns ``(result, captured_uvicorn_kwargs)``.
    """
    import uvicorn
    from typer.testing import CliRunner

    from construct import cli as cli_module

    captured: dict[str, object] = {}

    def fake_run(app, **kwargs):
        captured["app"] = app
        captured.update(kwargs)

    monkeypatch.setattr(uvicorn, "run", fake_run)
    result = CliRunner().invoke(cli_module.app, ["serve", *args])
    return result, captured


def test_the_bind_address_is_the_loopback_constant(
    monkeypatch: pytest.MonkeyPatch, install_root: Path
) -> None:
    """T-19-11 asserted rather than assumed.

    Three claims, because any one alone is weak: the constant is the loopback
    literal, ``uvicorn.run`` is actually handed *that constant*, and no wildcard
    address appears anywhere in ``cli.py``. A wildcard bind would put every
    capability — including the write ones — on the local network.
    """
    from construct import cli as cli_module

    assert cli_module.LOOPBACK_HOST == "127.0.0.1"

    port = _free_port()
    result, captured = _serve_in_process(
        monkeypatch, ["--install-root", str(install_root), "--port", str(port)]
    )
    assert result.exit_code == 0, result.output
    assert captured["host"] == cli_module.LOOPBACK_HOST
    assert captured["port"] == port

    source = Path(cli_module.__file__).read_text(encoding="utf-8")
    for wildcard in ('"0.0.0.0"', "'0.0.0.0'", '"::"', "'::'"):
        assert wildcard not in source, f"cli.py names a wildcard bind address: {wildcard}"


def test_the_declared_port_default_is_the_fixed_bookmarkable_one() -> None:
    """D-04: fixed, not ephemeral — the URL has to be bookmarkable and stable
    enough for a playbook to name a literal address. Read off the option rather
    than proven by binding it, so the assertion does not depend on 8787 being
    free on the machine running the suite."""
    from construct import cli as cli_module

    command = typer.main.get_command(cli_module.app).commands["serve"]
    port_option = next(p for p in command.params if p.name == "port")
    assert port_option.default == DEFAULT_API_PORT
    assert DEFAULT_API_PORT == 8787


def test_a_busy_port_exits_one_with_actionable_guidance(tmp_path: Path) -> None:
    """D-04's planner obligation: a collision produces guidance, not a traceback.

    Run in a real child process because the assertion *is* the exit code. uvicorn
    0.50.0+ raises ``SystemExit(3)`` for any startup failure, and 3 is a code no
    other CONSTRUCT command emits — so this test failing with 3 means the
    pre-flight probe was removed and the command stopped owning its own failure.
    """
    from construct import cli as cli_module

    holder = socket.socket()
    holder.bind((cli_module.LOOPBACK_HOST, 0))
    holder.listen(1)
    port = holder.getsockname()[1]
    try:
        completed = _serve_cli(
            ["serve", "--port", str(port), "--install-root", str(tmp_path)]
        )
    finally:
        holder.close()

    combined = completed.stdout + completed.stderr
    assert completed.returncode == 1, f"exit {completed.returncode}: {combined}"
    assert str(port) in combined
    assert "--port" in combined
    assert "Traceback" not in combined


def test_the_launch_token_reaches_a_0600_file_and_stdout(
    monkeypatch: pytest.MonkeyPatch, install_root: Path
) -> None:
    """D-17 / T-19-08: stdout and a ``0600`` file, and the two agree.

    The mode is asserted, not the write: a token file anyone on the machine can
    read is the same disclosure as no token at all, and the process umask decides
    the creation mode — so the explicit ``chmod`` is the control and this is what
    proves it ran.
    """
    result, _ = _serve_in_process(
        monkeypatch,
        ["--install-root", str(install_root), "--port", str(_free_port())],
    )
    assert result.exit_code == 0, result.output

    token_file = install_root / TOKEN_FILE_RELPATH
    assert token_file.is_file()
    assert stat.S_IMODE(token_file.stat().st_mode) == 0o600

    printed = [
        line.split("Token:", 1)[1].strip()
        for line in result.output.splitlines()
        if line.startswith("Token:")
    ]
    assert printed == [token_file.read_text(encoding="utf-8")]
    assert printed[0], "an empty token was issued"


def test_the_token_never_appears_in_a_url(
    monkeypatch: pytest.MonkeyPatch, install_root: Path
) -> None:
    """T-19-08's other half. A query-string token lands in shell history, access
    logs and the ``Referer`` — so the printed URL must not carry it."""
    result, _ = _serve_in_process(
        monkeypatch,
        ["--install-root", str(install_root), "--port", str(_free_port())],
    )
    token = (install_root / TOKEN_FILE_RELPATH).read_text(encoding="utf-8")

    urls = [line for line in result.output.splitlines() if "http://" in line]
    assert urls, "serve printed no URL"
    for line in urls:
        assert token not in line
        assert "?" not in line
