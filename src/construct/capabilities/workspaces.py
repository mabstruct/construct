"""Workspace-id resolution for the capability seam — the GOV-01 / D-01 gate.

A capability's declared input takes a filesystem **path**. A browser must never
send one: HTTP-03's literal wording is that the trust boundary refuses
caller-supplied filesystem paths. So every surface sends a workspace **id** — a
directory name under the install root, which is the name the user already
recognises — and this module is the one place that turns an id into a path.

The resolution runs inside ``CapabilityRegistry.invoke`` (D-01), which means it
applies to CLI, MCP and HTTP alike. That distinction is load-bearing: the seam's
docstring forbids a strict/lenient flag, an allowlist argument, or any
per-surface exception, because a knob there would let one surface diverge from
another — the fork the seam exists to close. Uniform *behaviour* is not a knob.

**The install root is launch context, not an ``invoke()`` argument (D-09).**
``tests/integration/test_surface_parity.py::test_seam_has_no_leniency_knob``
pins ``invoke``'s parameters to exactly ``{self, cap_id, payload}``, so the
install root cannot ride in on the call. It is process-level launch state here
(``set_launch_install_root`` / ``launch_install_root``), defaulting to
``Path.cwd()`` **resolved at call time, never at import time** (WR-09: a module
constant would freeze whatever directory the importing process happened to be
standing in). ``construct serve``, the CLI and the MCP server all read the same
value, so this adds one shared behaviour rather than a per-surface setting.

The rejected alternative was resolving on the *adapter* side — the HTTP layer
turning ``workspace_id`` into a path before calling the seam. That was declined
because it puts the security-relevant gate in one surface only: CLI and MCP
would keep taking raw paths, and the id vocabulary would be an HTTP-only dialect
(HTTP-02 forbids exactly that).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from construct.capabilities.errors import CapabilityInputError
from construct.schemas.config import KEBAB_CASE_PATTERN


#: The shape a workspace id must have. Deliberately the *same* pattern
#: ``_validate_run_id`` enforces on run ids (``construct.schemas.config``) —
#: [a-z0-9] segments joined by single hyphens — so the project has one answer to
#: "what may a caller-supplied handle look like" rather than one per subsystem.
WORKSPACE_ID_PATTERN = KEBAB_CASE_PATTERN

#: ``cap_id -> the field name that capability's own input model declares`` for a
#: workspace-scoped capability.
#:
#: The names are **not uniform** and that is the measured reality, not an
#: oversight to normalise here: 13 capabilities spell it ``workspace_path``, 11
#: spell it ``workspace``, 2 spell it ``path`` and 1 spells it ``root``.
#: Renaming any of them would change a declared contract every existing CLI and
#: MCP caller already sends, so the map absorbs the difference instead.
#:
#: The map is exhaustive over the workspace-scoped half of the registry;
#: ``tests/contract/test_http_surface.py`` asserts
#: ``set(WORKSPACE_FIELD) | set(INSTALL_ROOT_FIELD)`` equals the registry's own
#: id set, so a capability added without a classification fails the suite rather
#: than silently becoming unaddressable by id.
WORKSPACE_FIELD: dict[str, str] = {
    # ── spelled ``workspace_path`` ──
    "ask.domain": "workspace_path",
    "bridge.detect": "workspace_path",
    "card.evaluate": "workspace_path",
    "curation.inspect": "workspace_path",
    "curation.review": "workspace_path",
    "curation.run": "workspace_path",
    "daily.inspect": "workspace_path",
    "daily.run": "workspace_path",
    "research.inspect": "workspace_path",
    "research.review": "workspace_path",
    "research.run": "workspace_path",
    "research.score": "workspace_path",
    "research.search": "workspace_path",
    # ── spelled ``workspace`` ──
    "graph.status": "workspace",
    "help.suggest": "workspace",
    "ingest.source": "workspace",
    "knowledge.card.archive": "workspace",
    "knowledge.card.create": "workspace",
    "knowledge.card.edit": "workspace",
    "knowledge.card.list": "workspace",
    "knowledge.connection.add": "workspace",
    "knowledge.connection.list": "workspace",
    "knowledge.connection.remove": "workspace",
    "workflow.list": "workspace",
    "workflow.status": "workspace",
    # ── spelled ``path`` ──
    "workspace.status": "path",
    "workspace.validate": "path",
    # ── spelled ``root`` ──
    "workspace.init": "root",
}

#: ``cap_id -> field name`` for the capabilities scoped to the **install root**
#: rather than to a single workspace. A different scope, not a rename:
#: ``discover_workspaces`` scans the *children* of its argument, so handing
#: either of these a single workspace discovers zero workspaces and silently
#: emits an empty build (the D-05 note on ``ViewsGenerateDataInput``).
INSTALL_ROOT_FIELD: dict[str, str] = {
    "views.generate_data": "install_root",
    "views.validate_data": "install_root",
}

#: Capabilities whose workspace argument names a directory that does **not**
#: exist yet, so the allowlist gate ("must be a discoverable workspace") cannot
#: apply to them — it is *inverted* into a conflict check instead (D-11).
#:
#: One member today. It is a set rather than an ``if cap_id == "workspace.init"``
#: because the rule is a property of the *capability class* ("names a directory
#: it is about to create"), and Phase 22's creation wizard is expected to add to
#: it. A hard-coded id would put the second member's behaviour in an ``or``.
CREATE_MODE_CAPABILITIES = frozenset({"workspace.init"})

#: Every payload key that carries a filesystem path, derived from the values of
#: both maps so it can never drift from them. Hand-listing these was the obvious
#: shortcut and the wrong one: a capability whose field spelling is added to
#: ``WORKSPACE_FIELD`` but forgotten here would be a path-shaped key the HTTP
#: trust boundary silently accepts (D-10).
PATH_SHAPED_KEYS: frozenset[str] = frozenset(WORKSPACE_FIELD.values()) | frozenset(
    INSTALL_ROOT_FIELD.values()
)

#: The payload key every surface uses to name a workspace by id.
WORKSPACE_ID_KEY = "workspace_id"


# ---------------------------------------------------------------------------
# Launch context (D-09)
# ---------------------------------------------------------------------------

_launch_install_root: Path | None = None


def set_launch_install_root(root: Path | str | None) -> None:
    """Record the install root this process was launched against.

    Called by ``create_app`` (and available to any other launcher). ``None``
    clears it, which restores the ``Path.cwd()`` default — the form the test
    suite uses to avoid leaking one test's root into the next.
    """
    global _launch_install_root
    _launch_install_root = None if root is None else Path(root)


def launch_install_root() -> Path:
    """The install root every surface resolves workspace ids against.

    Falls back to ``Path.cwd()`` **resolved here, at call time**. Declaring the
    default as a module constant would evaluate it at *import* time, so any
    process importing this module before changing directory — test runners,
    long-lived hosts, anything introspecting the CLI — would silently resolve
    against the wrong tree (WR-09, the idiom ``cli.py`` already follows for
    ``--install-root``).
    """
    if _launch_install_root is not None:
        return _launch_install_root
    return Path.cwd()


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def resolve_workspace_id(
    cap_id: str,
    value: Any,
    install_root: Path,
    *,
    must_exist: bool = True,
) -> Path:
    """Turn a caller-supplied workspace **id** into a workspace **path**.

    Two gates, and the order between them is the control, not a detail:

    1. **Shape.** ``value`` must match ``WORKSPACE_ID_PATTERN``.
    2. **Allowlist.** ``value`` must name one of
       ``discover_workspaces(install_root)``.

    The threat and the sink, stated the way ``_validate_run_id`` states them
    (T-19-03): ``value`` arrives from an untrusted HTTP body and is joined onto
    ``install_root``, so an unconstrained value such as ``"../../etc"`` would
    cross straight into the filesystem layer. Constraining it to kebab-case
    makes traversal inexpressible — ``/`` and ``.`` are outside the pattern —
    **before** any path is built.

    Gate 1 MUST run before gate 2 because gate 2 is itself filesystem contact:
    ``discover_workspaces`` calls ``install_root.iterdir()`` and ``_is_workspace``
    stats every child. Reversing them would let a traversal attempt drive a
    directory walk, and criterion 2 of this plan requires a traversal attempt to
    have **no** filesystem effect at all.

    Per D-02 the valid id set *is* that scan, recomputed per request rather than
    cached at launch: a workspace created during a session must be addressable
    immediately, and a cached set would answer "no such workspace" until restart.
    That property is what lets creation and use compose: a workspace created by
    ``workspace.init`` is addressable by the very next request, with no restart
    and no cache-invalidation step for a caller to forget.

    **``must_exist=False`` inverts gate 2 rather than dropping it (D-11).** The
    shape gate is unconditional either way; what changes is what membership in
    the scan *means*. For the create-mode capabilities
    (``CREATE_MODE_CAPABILITIES``) an id that already names a discoverable
    workspace is a **conflict**, not a match — so the same measurement that is an
    allowlist for every other capability reads as a denylist for these. The
    function then returns ``install_root / value`` without touching the
    filesystem beyond that scan; it creates nothing itself.

    This is the direct answer to **T-18-34** ("capabilities creating directories
    at agent-supplied paths"), not a deferral of it. A caller supplies a *name*
    and never a *location*: the parent is always ``install_root``, which is
    launch context no payload can move, and the shape gate has already made
    ``..`` and ``/`` inexpressible. The most an attacker-controlled
    ``workspace_id`` can achieve is a new directory as a direct child of the
    install root — which is what the product's own front door does anyway.

    A missing or non-directory ``install_root`` yields an empty scan rather than
    an ``OSError``: ``iterdir()`` on a missing directory raises, and letting that
    escape would turn a mis-configured launch root into an untyped crash on every
    surface instead of the seam's own typed error.
    """
    if not isinstance(value, str) or WORKSPACE_ID_PATTERN.fullmatch(value) is None:
        raise CapabilityInputError(
            cap_id,
            f"{WORKSPACE_ID_KEY} must be kebab-case ([a-z0-9] segments joined by "
            "single hyphens), e.g. 'my-construct' not '../../etc'",
        )

    root = Path(install_root)
    known = _discover(root)

    if must_exist:
        if value not in known:
            available = ", ".join(sorted(known)) or "<none>"
            raise CapabilityInputError(
                cap_id,
                f"{WORKSPACE_ID_KEY} names no workspace under the install root. "
                f"Known workspace ids: {available}",
            )
        return known[value]

    if value in known:
        raise CapabilityInputError(
            cap_id,
            f"{WORKSPACE_ID_KEY} '{value}' already names a workspace under the "
            "install root, and this capability creates a new one — choose an "
            "unused id",
        )

    target = root / value
    if target.exists():
        # "Discoverable as a workspace" is a *narrower* test than "exists": a
        # half-built tree, or an unrelated directory that happens to share the
        # name, passes the scan check and would then be written into. Refusing on
        # existence is what makes the claim ("requires that the directory does
        # NOT already exist") true rather than nearly true.
        raise CapabilityInputError(
            cap_id,
            f"{WORKSPACE_ID_KEY} '{value}' already exists under the install root "
            "but is not a CONSTRUCT workspace — this capability will not write "
            "into an existing directory; choose an unused id",
        )
    return target


def _discover(root: Path) -> dict[str, Path]:
    """``{directory name: path}`` for every discoverable workspace under ``root``.

    Deferred import, for the two reasons the repo defers an import. (a)
    ``construct.views`` pulls the whole views contract-model package in, and this
    module now sits on ``registry.py``'s import path — i.e. on every CLI startup.
    (b) The import happening at call time is what makes ``discover_workspaces``
    patchable at its *source* module, which is how the ordering proofs in
    ``tests/contract/test_http_surface.py`` and
    ``tests/contract/test_capability_seam.py`` show the shape gate runs first.

    The ``is_dir`` guard is inside this helper rather than at each call site so
    both modes inherit it: ``discover_workspaces`` calls ``iterdir()``
    unguarded, and a launch root that does not exist is a configuration mistake
    that should surface as the seam's typed error, not as a bare ``OSError``
    from three frames down.
    """
    from construct.views.lib.discover import discover_workspaces

    if not root.is_dir():
        return {}
    return {path.name: path for path in discover_workspaces(root)}


def resolve_payload_workspace(cap_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Rewrite ``workspace_id`` into the capability's own path field.

    Returns a **new** dict — the seam hands this straight to
    ``input_model.model_validate``, and mutating the caller's payload in place
    would make a rejected request observably different from an accepted one for
    anyone holding a reference to it.

    A payload without ``workspace_id`` is returned unchanged, so every existing
    CLI and MCP call site keeps working byte-for-byte. That is what makes D-01
    an *addition* to the seam rather than a migration of it.

    The resolved value is emitted as ``str(...)``, not as a ``Path``: 13 of the
    workspace-scoped models declare a ``str`` field and 13 declare a ``Path``,
    and pydantic coerces ``str -> Path`` but not the reverse. Emitting a
    ``Path`` would therefore validate for half the registry and fail for the
    other half. RESEARCH assumption A2 asserted that without measuring it; the
    coercion family in ``tests/contract/test_capability_seam.py`` measures it,
    once per workspace-scoped capability rather than once per field name.

    **Install-root-scoped capabilities take the root from launch context
    (D-11).** The two ``views.*`` capabilities are scoped to the install root,
    which is a *different scope* from a workspace, not a different spelling of
    one: ``discover_workspaces`` scans the children of its argument, so handing
    either of them a single workspace discovers nothing and silently emits an
    empty build. So ``workspace_id`` is **refused** for them rather than
    resolved, and when the payload omits ``install_root`` the seam supplies
    ``launch_install_root()``.

    Two things follow, and both are the point:

    * The install root is the authorization boundary itself. A caller that could
      choose it could read and write any tree on the machine, so over HTTP it is
      never caller-chosen — ``install_root`` is a ``PATH_SHAPED_KEYS`` entry and
      the envelope refuses it with 422 before dispatch (D-10). Injection is what
      makes the two capabilities reachable *at all* from a browser: an HTTP
      caller reaches them by sending nothing path-shaped.
    * The CLI's ``--install-root`` flag is unchanged. A payload that already
      carries the field is left exactly as it arrived, and the CLI always sends
      one — so this is a new behaviour for callers that omit the field, not a
      change of behaviour for callers that supply it.

    Like the rest of this module it is uniform seam behaviour rather than a
    per-surface exception (D-09/D-11): CLI, MCP and HTTP all get it, and
    ``invoke``'s signature is untouched.
    """
    payload = dict(payload)

    install_field = INSTALL_ROOT_FIELD.get(cap_id)
    if install_field is not None:
        if WORKSPACE_ID_KEY in payload:
            raise CapabilityInputError(
                cap_id,
                f"{WORKSPACE_ID_KEY} does not apply to this capability: it is "
                f"scoped to the install root (the directory *above* the "
                f"workspaces), not to one workspace. Omit "
                f"{WORKSPACE_ID_KEY} and the launch install root is used",
            )
        if install_field not in payload:
            payload[install_field] = str(launch_install_root())
        return payload

    if WORKSPACE_ID_KEY not in payload:
        return payload

    field = WORKSPACE_FIELD.get(cap_id)
    if field is None:
        raise CapabilityInputError(
            cap_id,
            f"capability is not workspace-scoped, so {WORKSPACE_ID_KEY} has "
            "nothing to resolve against",
        )

    if field in payload:
        raise CapabilityInputError(
            cap_id,
            f"{WORKSPACE_ID_KEY} cannot be combined with '{field}' — send one or "
            "the other, not both",
        )

    resolved = resolve_workspace_id(
        cap_id,
        payload[WORKSPACE_ID_KEY],
        launch_install_root(),
        must_exist=cap_id not in CREATE_MODE_CAPABILITIES,
    )

    rewritten = {key: item for key, item in payload.items() if key != WORKSPACE_ID_KEY}
    rewritten[field] = str(resolved)
    return rewritten
