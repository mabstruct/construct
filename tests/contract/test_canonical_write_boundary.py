"""GOV-04 — the canonical write boundary.

Canonical truth (knowledge cards and typed connections) is written by the apply
nodes that sit downstream of the review interrupt, and by nothing else.

This module holds the *category-level* form of that invariant. Phase 18 D-13
deleted ``src/construct/ui/gate_review.py``, a second canonical writer that built
its review queue from Streamlit session state with no run behind it. An invariant
phrased against that one file would go green the moment the file was deleted and
stay green while a third writer appeared somewhere else. So the invariant here is
phrased against the *category*: no module outside the apply nodes reaches a
canonical write function, enumerated by walking the source tree.
"""
from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "construct"
UI_DIR = SRC_ROOT / "ui"

# The Streamlit panels that survive D-13. Gate Review is gone; Dashboard and the
# Capability Runner stay (the runner dispatches capabilities through the seam —
# it is a legitimate surface, not a surface that forges a gate).
SURVIVING_PAGES = ("Dashboard", "Capability Runner")


class _RecordedPage:
    """Stand-in for ``st.Page`` that records the script it was pointed at.

    ``st.Page`` only half-initialises outside a Streamlit script run context, so
    reading ``page.title`` off a real one raises. Recording the constructor
    arguments keeps this an import-level check with no browser and no runtime.
    """

    def __init__(self, script, title=None, icon=None, **kwargs):
        self.script = script
        self.title = title


class _RecordedNavigation:
    """Stand-in for the object ``st.navigation`` returns; ``run()`` is a no-op."""

    def __init__(self, pages):
        self.pages = list(pages)

    def run(self):
        return None


def _load_navigation_pages(monkeypatch) -> list[_RecordedPage]:
    """Import the Streamlit application module and return its declared pages."""
    import streamlit as st

    captured: dict[str, _RecordedNavigation] = {}

    def _navigation(pages, **kwargs):
        nav = _RecordedNavigation(pages)
        captured["nav"] = nav
        return nav

    monkeypatch.setattr(st, "Page", _RecordedPage)
    monkeypatch.setattr(st, "navigation", _navigation)

    module = importlib.import_module("construct.ui.streamlit_app")
    importlib.reload(module)

    assert "nav" in captured, "streamlit_app.py never called st.navigation()"
    return captured["nav"].pages


def test_streamlit_navigation_matches_surviving_page_files(monkeypatch):
    """The app's page list holds exactly the surviving pages, each with a file.

    Deleting a page module without its navigation entry breaks application
    start-up (Pitfall 6); declaring a navigation entry without a backing file
    does the same. This asserts both directions at import time.
    """
    pages = _load_navigation_pages(monkeypatch)

    assert [page.title for page in pages] == list(SURVIVING_PAGES)

    for page in pages:
        script = UI_DIR / page.script
        assert script.is_file(), f"navigation entry {page.title!r} has no backing file: {script}"


# ═══════════════════════════════════════════════════════════════════════════════
# The category-level guard: exactly one canonical writer
# ═══════════════════════════════════════════════════════════════════════════════


def _knowledge_service_path() -> Path:
    """Absolute path of the module that defines the canonical write functions."""
    from construct.services import knowledge

    return Path(inspect.getsourcefile(knowledge)).resolve()


def canonical_write_functions() -> tuple[str, ...]:
    """Derive the canonical write set from the knowledge service's own source.

    A canonical write is a public function in ``construct.services.knowledge``
    whose body appends a *card* or *connection* event to the append-only audit
    trail — those two helpers exist precisely because a card or a connection was
    written to canonical truth. Deriving the names this way means the forbidden
    list cannot drift from the functions it names: a sixth canonical writer added
    to the service falls under the guard the day it appears, and renaming one
    keeps the guard pointed at the rename instead of at a stale string.
    """
    source = _knowledge_service_path().read_text(encoding="utf-8")
    tree = ast.parse(source)

    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
            continue
        calls = {
            child.func.id
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }
        if calls & {"append_card_event", "append_connection_event"}:
            names.append(node.name)
    return tuple(sorted(names))


def _direct_calls(source: str, path: Path, names: frozenset[str]) -> set[str]:
    """Return which canonical write functions this source *calls* directly.

    AST calls, not text matches: a docstring that names ``edit_card`` is prose,
    and ``handler=archive_card`` is a binding. Only ``edit_card(...)`` — bare or
    attribute-qualified — is a direct canonical write.
    """
    called: set[str] = set()
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in names:
            called.add(func.id)
        elif isinstance(func, ast.Attribute) and func.attr in names:
            called.add(func.attr)
    return called


def exemption_for(path: Path, source: str) -> str | None:
    """Return why a module may call canonical writes, or ``None`` if it may not.

    Three rules, each a *property* of the module rather than a name in a list.
    An allowlist of names is how a second writer survives as a documented
    exception (D-05); a property admits the modules that genuinely hold the
    responsibility and nothing else.
    """
    # Rule 1 — the definer. The module that defines the canonical write functions
    # necessarily contains their bodies and their recursive/internal use. Resolved
    # from the imported module object, so moving or renaming the file cannot leave
    # this rule pointing at nothing.
    if path.resolve() == _knowledge_service_path():
        return "definer: defines the canonical write functions"

    # Rule 2 — the apply-node modules. A module that both builds a LangGraph
    # StateGraph and raises a human-review interrupt() inside it is a gated
    # workflow graph: its write nodes are wired strictly downstream of that
    # interrupt, which is precisely the authorisation GOV-04 demands. Both halves
    # are required — an interrupt without a graph is not a review gate, and a
    # graph without an interrupt has no gate to be downstream of.
    if "StateGraph(" in source and "interrupt(" in source:
        return "apply-node graph: writes are downstream of a review interrupt"

    # Rule 3 — the binding tier. The capability catalog binds the write functions
    # to registry records; the only calls it makes to them are the keyword
    # marshalling pass-throughs inside those bindings. Binding a writer to a
    # registry record is not writing.
    if "CapabilityRecord(" in source:
        return "binding tier: binds write functions to registry records"

    return None


def unexempted_callers(root: Path) -> dict[str, set[str]]:
    """Walk ``root`` and return every non-exempt module that calls a canonical write.

    The scan set is produced by directory traversal, never by a hand-typed list of
    modules: a hand-typed list is a snapshot, and a module added tomorrow would be
    invisible to it — which is the exact failure mode this guard exists to prevent.
    """
    names = frozenset(canonical_write_functions())
    offenders: dict[str, set[str]] = {}

    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        called = _direct_calls(source, path, names)
        if not called:
            continue
        if exemption_for(path, source):
            continue
        offenders[path.relative_to(root).as_posix()] = called

    return offenders


# NOT a fourth exemption — an unresolved finding this guard surfaced on the day it
# was written, recorded so it stays named instead of silently allowlisted.
#
# ``pipelines/ingestion.py`` calls ``create_card`` directly from ``ingest_source``
# (:246). It is not an apply node and there is no review interrupt in front of it:
# the ``ingest.source`` capability creates a card as its declared product. That may
# well be correct behaviour, but it is not the invariant as GOV-04 states it, and
# deciding which of the two is wrong is a scope change, not an execution detail.
#
# The two assertions below treat this as a regression baseline that may only
# shrink: nothing new may join it, and an entry that stops being a real caller
# must be deleted from it rather than left to rot.
UNRESOLVED_DIRECT_CALLERS = {"pipelines/ingestion.py"}


def test_canonical_write_set_is_derived_from_the_service():
    """The derived forbidden list really covers the service's write functions."""
    derived = set(canonical_write_functions())

    assert {
        "create_card",
        "edit_card",
        "archive_card",
        "add_connection",
        "remove_connection",
    } <= derived, f"derivation lost a canonical writer: {sorted(derived)}"


def test_no_canonical_writer_outside_the_apply_nodes():
    """GOV-04: canonical truth is written by the apply nodes and by nothing else."""
    offenders = unexempted_callers(SRC_ROOT)

    new_writers = {mod: fns for mod, fns in offenders.items() if mod not in UNRESOLVED_DIRECT_CALLERS}
    assert not new_writers, (
        "canonical writes are reachable only from apply nodes downstream of the "
        f"review interrupt; these modules call them directly: {new_writers}"
    )

    stale = UNRESOLVED_DIRECT_CALLERS - set(offenders)
    assert not stale, (
        "these modules no longer call a canonical write function — delete them "
        f"from UNRESOLVED_DIRECT_CALLERS instead of leaving the baseline to rot: {sorted(stale)}"
    )


def test_guard_detects_a_planted_canonical_writer(tmp_path):
    """A guard that has never been observed failing is not known to be a guard.

    Plants three modules in a scratch tree and scans it with the same function the
    real guard uses: a surface that writes directly is caught, a surface that
    dispatches a registered capability through the seam is not, and a gated
    workflow graph is exempt by rule 2 rather than by its name.
    """
    (tmp_path / "rogue_surface.py").write_text(
        "from construct.services.knowledge import create_card\n"
        "def approve(workspace, card_data):\n"
        "    return create_card(workspace, card_data)\n",
        encoding="utf-8",
    )
    (tmp_path / "dispatching_surface.py").write_text(
        "def run(cap, **inputs):\n"
        "    return cap.handler(**inputs)\n",
        encoding="utf-8",
    )
    (tmp_path / "gated_graph.py").write_text(
        "from construct.services.knowledge import edit_card\n"
        "def gate(state):\n"
        "    return interrupt({'queue': state})\n"
        "def apply(state):\n"
        "    return edit_card(state['workspace'], state['card_id'], {})\n"
        "def build():\n"
        "    builder = StateGraph(dict)\n"
        "    return builder\n",
        encoding="utf-8",
    )

    offenders = unexempted_callers(tmp_path)

    # Red: the planted direct writer is caught.
    assert offenders == {"rogue_surface.py": {"create_card"}}

    # Green: removing the write makes the same scan pass again.
    (tmp_path / "rogue_surface.py").write_text(
        "def approve(workspace, card_data):\n"
        "    return None\n",
        encoding="utf-8",
    )
    assert unexempted_callers(tmp_path) == {}


def test_capability_dispatch_does_not_trip_the_guard():
    """Dispatching a registered capability is not calling a canonical writer.

    The Capability Runner survives D-13 precisely because it dispatches through
    the registry rather than reaching a write function; the guard must be able to
    tell the two apart, or it would fire on the surface it is meant to permit.
    """
    runner = UI_DIR / "capability_runner.py"
    source = runner.read_text(encoding="utf-8")

    assert "handler(" in source, "fixture drift: the runner no longer dispatches a capability"
    assert not _direct_calls(source, runner, frozenset(canonical_write_functions()))
    assert exemption_for(runner, source) is None, (
        "the runner must pass the guard on its own merits, not via an exemption"
    )
