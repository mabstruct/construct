"""Wave 0 RED guard for the API-04 skill migration (Phase 12).

Three Claude skills are being migrated from inline LLM search/judgment into thin
CLI delegators over the shipped ``construct research run`` / ``construct curation
run`` / ``construct card evaluate`` capabilities. Once migrated, none of them may
retain a web-fetch or a workspace-write tool in its ``allowed-tools`` frontmatter
line — the Python capabilities own those side effects, not the skill text.

This is a static frontmatter guard mirroring the ``Path(...).read_text()`` +
``assert "x" not in src`` pattern in ``test_curation_run_cli_mcp.py``. It reads
ONLY the ``allowed-tools:`` frontmatter line (not the prose body, which may
legitimately mention these tools) and asserts the forbidden tokens are absent.

Wave 0 status: RED for ``construct-research-cycle`` (still carries
``WebSearch, WebFetch``); the other two already delegate. The suite turns fully
GREEN when Plan 06 lands the migrated frontmatters.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# tests/contract/test_skill_migration.py → parents[2] == repo root.
_SKILLS_DIR = Path(__file__).resolve().parents[2] / "CONSTRUCT-CLAUDE-impl" / "claude" / "skills"

_MIGRATED_SKILLS = (
    "construct-research-cycle",
    "construct-curation-cycle",
    "construct-card-evaluate",
)

# Web-fetch tools and workspace-write tools must not survive in allowed-tools.
_FORBIDDEN_TOOLS = ("WebSearch", "WebFetch", "Write", "Edit")


def _allowed_tools_line(skill: str) -> str:
    """Return the ``allowed-tools:`` frontmatter line for a migrated skill."""
    path = _SKILLS_DIR / skill / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("allowed-tools:"):
            return line
    raise AssertionError(f"{skill}/SKILL.md has no allowed-tools frontmatter line")


@pytest.mark.parametrize("skill", _MIGRATED_SKILLS)
def test_skill_drops_forbidden_tools(skill: str) -> None:
    line = _allowed_tools_line(skill)
    for tool in _FORBIDDEN_TOOLS:
        assert tool not in line, f"{skill} still allows forbidden tool {tool!r} in: {line}"


@pytest.mark.parametrize("skill", _MIGRATED_SKILLS)
def test_skill_still_delegates_to_cli(skill: str) -> None:
    """The migrated skills stay thin CLI delegators: ``Bash(construct)`` remains in
    allowed-tools (they invoke the Python capabilities rather than doing the work
    inline)."""
    line = _allowed_tools_line(skill)
    assert "Bash(construct)" in line, f"{skill} must still delegate via Bash(construct): {line}"
