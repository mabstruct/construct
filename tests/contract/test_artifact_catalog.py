"""DOC-02 — ``artifact-catalog.md`` must match the live runtime surface.

The catalog is CONSTRUCT's single canonical inventory. Historically it was
entirely CONSTRUCT03-audit / Claude-config shaped (agents, skills, workflows)
with hand-typed counts ("Skills (23)"). It carried NO rows for the L2/L3 Python
runtime surface — the capability registry, the CLI command tree, or the MCP tool
list — and every hand-typed integer reset the rot clock on the next edit.

This guard is the doc-facing sibling of ``test_doc_command_references`` (FIX-04)
and of the ``test_mcp_no_hardcoded_*`` invariants: the same "the surface must
match the registry" idea, applied to the master inventory. It derives truth from
four *live* introspection sources and asserts the catalog documents each one:

1. the capability registry ids           -- ``get_registry().list()``
2. the MCP tool names                     -- ``get_registry().list_mcp_tools()``
3. the Typer leaf command tree            -- ``LEAF_COMMANDS`` (FIX-04 helper)
4. the ``construct-*`` skill directories  -- filesystem glob

Design contract
---------------
* Subset, not equality. Each assertion is ``introspected <= documented``: the
  catalog MAY carry extra narrative rows (the search spine, the LLM gates,
  CONSTRUCT03 audit columns) that no single registry enumerates. Exact equality
  is deliberately NOT required.
* Set membership, not row order. The catalog's row ordering is never asserted.
* Registry and Typer are TWO DISTINCT sources. Only 26 of 28 capabilities carry
  a ``cli_name``; ``views``/``spike``/``tag`` reach the CLI by an independent
  path, not through the registry (``catalog.py`` holdout note). So the Typer-leaf
  check does NOT require every leaf to map to a registry id.
* Vacuity is the real threat. A broken import or a renamed accessor that returns
  an empty set would make every ``<=`` assertion pass trivially — a false green
  that hides catalog rot. ``test_catalog_introspection_is_not_vacuous`` closes
  that hole loudly, mirroring ``test_command_surface_is_discoverable``.

Counts are never hand-typed here. The live figures (28 capabilities / 22 MCP
tools / 34 CLI leaves / 25 skills as of Phase 17) are derived at run time; this
module hardcodes none of them.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# The FIX-04 guard lives beside this file. Put its directory on the path so the
# reusable introspection helpers import by their bare module name (the layout
# gives ``tests/contract`` a package ``__init__``; this keeps the import robust
# regardless of pytest's rootdir handling). We IMPORT these helpers — we do not
# re-implement the Typer walk.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_doc_command_references import (  # noqa: E402  (path insert must precede)
    LEAF_COMMANDS,
    VALID_PATHS,
    _IMPL,
    _REPO_ROOT,
    _code_spans,
    _invocations,
)

from construct.capabilities.catalog import get_registry  # noqa: E402

_CATALOG = _REPO_ROOT / "CONSTRUCT-CLAUDE-spec" / "artifact-catalog.md"
_SKILLS_DIR = _IMPL / "claude" / "skills"


# ---------------------------------------------------------------------------
# Extracting the documented surface from the catalog
# ---------------------------------------------------------------------------

# Split a code span into candidate identifier tokens. Whitespace and markdown /
# table punctuation are separators; ``.`` ``_`` ``-`` are NOT — they are part of
# capability ids (``daily.run``), MCP tool names (``construct_daily_run``), and
# skill directory names (``construct-daily-cycle``) respectively.
_TOKEN_SPLIT = re.compile(r"[\s,|()<>\[\]{}`\"';:!?]+")


def _catalog_text() -> str:
    return _CATALOG.read_text(encoding="utf-8")


def _documented_tokens() -> set[str]:
    """Every identifier-shaped token that appears inside a catalog code span.

    Prose is never scanned — only fenced blocks and inline backticks — so a
    capability id must be written in a code span (a table cell in backticks) to
    count as documented, exactly as the FIX-04 extractor treats invocations.
    """
    tokens: set[str] = set()
    for span in _code_spans(_catalog_text()):
        for tok in _TOKEN_SPLIT.split(span):
            tok = tok.strip()
            if tok:
                tokens.add(tok)
    return tokens


def _documented_cli_paths() -> set[tuple[str, ...]]:
    """Every ``construct ...`` command path written in a catalog code span.

    Reuses the FIX-04 ``_invocations`` extractor so the two guards agree on what
    a documented CLI invocation is.
    """
    return _invocations(_catalog_text())


# ---------------------------------------------------------------------------
# Vacuity meta-guard — MUST run and MUST be able to fail loudly
# ---------------------------------------------------------------------------


def test_catalog_introspection_is_not_vacuous() -> None:
    """Guard the four introspection sources AND the doc extractor.

    Without this, a broken import or a renamed accessor returning an empty set
    would make every subset assertion below pass on the empty set — a false green
    that hides exactly the rot this guard exists to catch. Mirrors
    ``test_command_surface_is_discoverable`` in the FIX-04 module.
    """
    reg = get_registry()
    # Live sources are non-degenerate.
    assert len(reg.list()) > 25, "capability registry looks empty — introspection broke"
    assert len(reg.list_mcp_tools()) > 20, "MCP tool list looks empty — introspection broke"
    assert ("daily", "run") in VALID_PATHS, "Typer surface looks empty — introspection broke"
    assert (_SKILLS_DIR / "construct-daily-cycle").is_dir(), "skills glob anchor missing"

    # The doc extractor actually finds rows (a formatting change that blinds it
    # must fail here, not sail past every subset check on an empty documented set).
    tokens = _documented_tokens()
    assert len(tokens) > 20, "catalog code-span extractor found almost nothing — regex likely broke"
    assert "daily.run" in tokens, "extractor did not find a known capability id"
    assert "construct_daily_run" in tokens, "extractor did not find a known MCP tool name"
    assert "construct-daily-cycle" in tokens, "extractor did not find a known skill dir"
    assert ("daily", "run") in _documented_cli_paths(), "extractor did not find a known CLI path"


# ---------------------------------------------------------------------------
# The four subset assertions: introspected surface <= documented rows
# ---------------------------------------------------------------------------


def test_every_capability_id_has_a_catalog_row() -> None:
    """Every registered capability id (live 28) must appear as a catalog row."""
    documented = _documented_tokens()
    cap_ids = {cap.id for cap in get_registry().list()}
    missing = cap_ids - documented
    assert not missing, (
        "artifact-catalog.md is missing a runtime row for these capability ids: "
        + ", ".join(sorted(missing))
    )


def test_every_mcp_tool_has_a_catalog_row() -> None:
    """Every MCP tool name (live 22) must appear as a catalog row."""
    documented = _documented_tokens()
    mcp_names = {tool["name"] for tool in get_registry().list_mcp_tools()}
    missing = mcp_names - documented
    assert not missing, (
        "artifact-catalog.md is missing a runtime row for these MCP tool names: "
        + ", ".join(sorted(missing))
    )


def test_every_typer_leaf_is_represented() -> None:
    """Every Typer leaf command (live 34) must be documented as a CLI invocation.

    The registry (28 caps / 22 MCP tools) and the Typer app (34 leaves) are two
    DISTINCT sources: ``views``/``spike``/``tag`` reach the CLI by an independent
    path and carry no registry id. So this checks the leaf appears as a
    ``construct ...`` invocation in the catalog — it does NOT require a registry
    id for each leaf.
    """
    documented_cli = _documented_cli_paths()
    missing = LEAF_COMMANDS - documented_cli
    assert not missing, (
        "artifact-catalog.md does not document these CLI leaf commands: "
        + ", ".join("construct " + " ".join(p) for p in sorted(missing))
    )


def test_every_skill_dir_has_a_catalog_row() -> None:
    """Every ``construct-*`` skill directory (live 25) must have a catalog row.

    This is the check that catches the criterion-named missing ``construct-spike-run``
    row and the ``construct-daily-cycle`` row added in plan 17-02.
    """
    documented = _documented_tokens()
    skill_dirs = {p.name for p in _SKILLS_DIR.glob("construct-*") if p.is_dir()}
    missing = skill_dirs - documented
    assert not missing, (
        "artifact-catalog.md is missing a Skills-section row for these skill directories: "
        + ", ".join(sorted(missing))
    )
