"""Static guard: migrated Claude skills must stay thin CLI delegators.

Four Claude skills have been (or are being) migrated from inline LLM
search/judgment into thin CLI delegators over the shipped ``construct research
run`` / ``construct curation run`` / ``construct card evaluate`` / ``construct
ask domain`` capabilities. None of them may retain a web-fetch or a
workspace-write tool in its ``allowed-tools`` frontmatter — the Python
capabilities own those side effects, not the skill text.

This is a static frontmatter guard mirroring the ``Path(...).read_text()`` +
``assert "x" not in src`` pattern in ``test_curation_run_cli_mcp.py``. It reads
ONLY the ``allowed-tools:`` frontmatter declaration (not the prose body, which
may legitimately mention these tools) and asserts the forbidden tokens are
absent.

Two frontmatter dialects exist in the tree and both must be read, or the guard
goes vacuous: inline (``allowed-tools: A, B, C``) and list style
(``allowed-tools:`` followed by indented ``- `` lines). A parser that reads only
the first line returns a bare ``allowed-tools:`` for the list dialect, which
makes every ``tool not in text`` assertion pass unconditionally — a false green.
``test_allowed_tools_text_is_not_vacuous`` is the meta-guard that closes this.

Current scope: the three Phase 12 skills plus ``construct-synthesis``, added by
Phase 16 DEC-01. Status: RED for ``construct-synthesis``, which still carries
``WebSearch`` / ``WebFetch``; those grants are removed in Plan 16-04, at which
point the suite turns fully GREEN.
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
    "construct-synthesis",
)

# Web-fetch tools and workspace-write tools must not survive in allowed-tools.
_FORBIDDEN_TOOLS = ("WebSearch", "WebFetch", "Write", "Edit")


def _allowed_tools_text(skill: str) -> str:
    """Return the full ``allowed-tools:`` frontmatter declaration for a skill.

    Handles both dialects present in the tree. After locating the
    ``allowed-tools:`` line, subsequent YAML list items (lines whose stripped form
    starts with ``- ``) are consumed and joined with newlines; scanning stops at
    the first line that is neither.

    For the inline dialect the next line is the closing ``---``, which is not a
    list item, so the returned text is the single line — byte-identical to the
    original single-line behaviour. A line-oriented scan is deliberate: it keeps
    this guard free of a YAML dependency.
    """
    path = _SKILLS_DIR / skill / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.strip().startswith("allowed-tools:"):
            continue
        collected = [line]
        for continuation in lines[index + 1 :]:
            if not continuation.strip().startswith("- "):
                break
            collected.append(continuation)
        return "\n".join(collected)
    raise AssertionError(f"{skill}/SKILL.md has no allowed-tools frontmatter line")


@pytest.mark.parametrize("skill", _MIGRATED_SKILLS)
def test_allowed_tools_text_is_not_vacuous(skill: str) -> None:
    """Meta-guard: the parser must return an actual tool declaration.

    A parser returning a bare ``allowed-tools:`` (as the single-line reader did
    for the list dialect) makes every ``tool not in text`` assertion below pass
    unconditionally. Every guard in this suite carries a meta-guard asserting it
    is still looking at something.
    """
    text = _allowed_tools_text(skill)
    _, _, declared = text.partition(":")
    assert declared.strip(), (
        f"{skill} yields an empty allowed-tools declaration ({text!r}) — the "
        "frontmatter parser is not reading the tool grants, so every forbidden-tool "
        "assertion for this skill is vacuous."
    )


@pytest.mark.parametrize("skill", _MIGRATED_SKILLS)
def test_skill_drops_forbidden_tools(skill: str) -> None:
    text = _allowed_tools_text(skill)
    for tool in _FORBIDDEN_TOOLS:
        assert tool not in text, f"{skill} still allows forbidden tool {tool!r} in: {text}"


@pytest.mark.parametrize("skill", _MIGRATED_SKILLS)
def test_skill_still_delegates_to_cli(skill: str) -> None:
    """The migrated skills stay thin CLI delegators: ``Bash(construct)`` remains in
    allowed-tools (they invoke the Python capabilities rather than doing the work
    inline)."""
    text = _allowed_tools_text(skill)
    assert "Bash(construct)" in text, f"{skill} must still delegate via Bash(construct): {text}"
