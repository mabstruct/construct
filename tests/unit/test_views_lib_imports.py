"""Unit tests guarding the views generator against skill-directory coupling (D-08, FIX-01)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

VENDORED_MODULES = [
    "build_id",
    "compute_stats",
    "discover",
    "envelope",
    "fingerprint",
    "frontmatter",
    "parse_articles",
    "parse_bridges",
    "parse_cards",
    "parse_connections",
    "parse_curation",
    "parse_digests",
    "parse_domains",
    "parse_events",
]

_SKILL_DIR_MARKER = "CONSTRUCT-CLAUDE-impl"


def _drop_views_modules() -> None:
    for name in list(sys.modules):
        if name == "construct.views.generate" or name.startswith("construct.views.lib"):
            del sys.modules[name]


def test_views_lib_imports_without_path_mutation() -> None:
    _drop_views_modules()
    before = list(sys.path)
    importlib.import_module("construct.views.generate")
    after = list(sys.path)
    assert before == after, (
        "importing construct.views.generate mutated the interpreter module search path"
    )


def test_views_lib_modules_all_importable() -> None:
    assert len(VENDORED_MODULES) == 14
    package = importlib.import_module("construct.views.lib")
    package_dir = Path(package.__file__).resolve().parent
    assert package_dir.name == "lib"
    assert package_dir.parent.name == "views"

    for name in VENDORED_MODULES:
        module = importlib.import_module(f"construct.views.lib.{name}")
        module_path = Path(module.__file__).resolve()
        assert module_path.parent == package_dir, f"{name} resolved outside the vendored package"
        assert _SKILL_DIR_MARKER not in str(module_path), f"{name} resolved to the skill directory"


def test_generate_module_declares_no_skill_directory_path() -> None:
    generate = importlib.import_module("construct.views.generate")
    source = Path(generate.__file__).read_text(encoding="utf-8")
    assert _SKILL_DIR_MARKER not in source
    code_lines = [line for line in source.splitlines() if not line.lstrip().startswith("#")]
    code = "\n".join(code_lines)
    assert "path.insert" not in code
    assert "path.append" not in code
