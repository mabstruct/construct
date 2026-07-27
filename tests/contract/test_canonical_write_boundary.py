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

import importlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_DIR = REPO_ROOT / "src" / "construct" / "ui"

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
