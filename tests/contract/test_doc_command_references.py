"""FIX-04 — every documented ``construct ...`` invocation must resolve to a real command.

Phase verifications in v0.3/v0.4 tested the Python layer directly. Nothing ever
tested that a command string *written in a skill or workflow doc* resolves against
the shipped CLI. That blind spot let six broken invocation paths ship (V41-03 in
``.planning/milestones/v0.4-MILESTONE-AUDIT.md``): four skills invoking
``construct knowledge card list`` / ``knowledge ref list`` / ``views generate``,
plus two playbook steps invoking the ``workflow run`` / ``workflow resume``
commands deliberately removed in Phase 12 (D-10).

This is the doc-facing sibling of the ``test_mcp_no_hardcoded_*`` invariant: the
same "the surface must match the registry" idea, applied one layer further out.

Mechanism
---------
1. Introspect the live Typer app to build the set of valid command paths.
2. Scan skill/workflow/playbook docs for ``construct ...`` strings, looking ONLY
   inside code spans (fenced blocks and inline backticks) so prose like "construct
   a knowledge card" is never matched.
3. Assert each resolves to a known command path.

Known-broken references live in ``_KNOWN_BROKEN`` with their owning audit defect
ID. They are asserted to be *still broken* (xfail-style), so the moment a FIX
lands the entry must be deleted — the allowlist cannot silently rot. It should
only ever shrink.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import typer

from construct.cli import app

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPL = _REPO_ROOT / "CONSTRUCT-CLAUDE-impl"

# Docs whose command strings a user or agent is expected to execute verbatim.
_DOC_GLOBS = (
    (_IMPL / "claude" / "skills", "*/SKILL.md"),
    (_IMPL / "construct" / "workflows", "*.md"),
    (_REPO_ROOT, "USER-TEST-PLAYBOOK-v03.md"),
)

# Documents whose whole purpose is to carry executable invocations.
#
# Why a repo-wide total is not enough: ``test_docs_contain_invocations`` asserts a
# single aggregate floor across every scanned document. A document added to
# ``_DOC_GLOBS`` whose command strings the extractor happens to miss therefore
# passes ``test_documented_commands_resolve`` *trivially*, on an empty set, while
# the global total stays far above its floor — a false green produced by the very
# act of widening coverage. This named set closes that hole one level down: each
# listed document must individually yield at least one invocation.
#
# These paths are resolved directly against ``_REPO_ROOT``, NOT via
# ``_doc_files()``. The independence is deliberate and load-bearing: a document
# can be asserted non-vacuous before it is globbed, so this guard is able to fail
# for documents ``_DOC_GLOBS`` does not yet scan. It also means shrinking the scan
# surface cannot silence it.
_MUST_CARRY_INVOCATIONS: tuple[str, ...] = (
    "CONSTRUCT-CLAUDE-impl/USER_GUIDE.md",
    "CONSTRUCT-CLAUDE-impl/construct/references/commands.md",
    "USER-TEST-PLAYBOOK-v03.md",
)

# Tokens that end a command path — flags, placeholders, shell noise, prose.
_ARG_START = re.compile(r"^[-<{$\"'.,;:)\[/|]|^[A-Z]|\.\.\.")

# Code spans only: fenced blocks and inline backticks. Prose is never scanned.
_FENCED = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.DOTALL)
_INLINE = re.compile(r"`([^`\n]+)`")

# NOTE: [ \t]+ not \s+ — \s crosses newlines, which manufactures phantom commands
# from a line ending in "construct" followed by an unrelated next line.
_INVOCATION = re.compile(r"\bconstruct[ \t]+([a-z][\w \t-]*)")


# ---------------------------------------------------------------------------
# 1. The live command surface
# ---------------------------------------------------------------------------


def _command_paths(
    t_app: typer.Typer, prefix: tuple[str, ...] = ()
) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
    """Recursively collect (leaf commands, groups) from a Typer app.

    The distinction is load-bearing: trailing tokens after a *leaf* are positional
    arguments, so ``ingest source ./x`` resolves via the ``ingest source`` leaf.
    Trailing tokens after a *group* are a subcommand name — so ``workflow run``
    must NOT resolve just because the ``workflow`` group exists.
    """
    leaves: set[tuple[str, ...]] = set()
    groups: set[tuple[str, ...]] = set()
    for cmd in t_app.registered_commands:
        name = cmd.name or (cmd.callback.__name__.replace("_", "-") if cmd.callback else None)
        if name:
            leaves.add(prefix + (name,))
    for group in t_app.registered_groups:
        name = group.name or (group.typer_instance.info.name if group.typer_instance else None)
        if not name or group.typer_instance is None:
            continue
        sub = prefix + (name,)
        groups.add(sub)  # invocable on its own — prints help
        sub_leaves, sub_groups = _command_paths(group.typer_instance, sub)
        leaves |= sub_leaves
        groups |= sub_groups
    return leaves, groups


LEAF_COMMANDS, COMMAND_GROUPS = _command_paths(app)
VALID_PATHS = LEAF_COMMANDS | COMMAND_GROUPS


# ---------------------------------------------------------------------------
# 2. Extracting invocations from docs
# ---------------------------------------------------------------------------


def _code_spans(text: str) -> list[str]:
    spans = _FENCED.findall(text)
    # Strip fenced regions before scanning inline ticks so we don't double-count.
    spans += _INLINE.findall(_FENCED.sub("", text))
    return spans


def _invocations(text: str) -> set[tuple[str, ...]]:
    """Return the command path of every ``construct ...`` string in code spans."""
    found: set[tuple[str, ...]] = set()
    for span in _code_spans(text):
        for match in _INVOCATION.finditer(span):  # regex is newline-safe (see above)
            tokens: list[str] = []
            for token in match.group(1).split():
                if _ARG_START.match(token):
                    break
                tokens.append(token)
            if tokens:
                found.add(tuple(tokens))
    return found


def _resolves(path: tuple[str, ...]) -> bool:
    """A path resolves if it names a command/group, or extends a leaf with args."""
    if path in VALID_PATHS:
        return True
    # Trailing tokens are only legal as positional args to a leaf command.
    return any(path[:i] in LEAF_COMMANDS for i in range(len(path) - 1, 0, -1))


def _doc_files() -> list[Path]:
    files: list[Path] = []
    for root, pattern in _DOC_GLOBS:
        if root.is_dir():
            files.extend(sorted(root.glob(pattern)))
        elif (root / pattern).is_file():
            files.append(root / pattern)
    return files


def _documented() -> dict[Path, set[tuple[str, ...]]]:
    return {p: _invocations(p.read_text(encoding="utf-8")) for p in _doc_files()}


# ---------------------------------------------------------------------------
# 3. Known-broken allowlist — MUST only shrink
# ---------------------------------------------------------------------------

# Each entry is a command path that is documented but does not resolve, mapped to
# the audit defect that owns it. Delete an entry the moment its FIX lands; the
# test below fails if an entry starts resolving, so this cannot rot.
_KNOWN_BROKEN: dict[tuple[str, ...], str] = {
    ("knowledge", "card", "list"): "V41-03 / FIX-03 — no `list` on the card sub-app",
    ("knowledge", "ref", "list"): "V41-03 / FIX-03 — no `ref` sub-app exists",
    ("workflow", "run"): "V41-03 / FIX-03 — removed in Phase 12 (D-10)",
    ("workflow", "resume"): "V41-03 / FIX-03 — never existed",
}


def _is_known_broken(path: tuple[str, ...]) -> bool:
    """True if ``path`` or any prefix of it is an allowlisted broken command."""
    return any(path[:i] in _KNOWN_BROKEN for i in range(1, len(path) + 1))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_command_surface_is_discoverable() -> None:
    """Guard the introspection itself — if this breaks, every other test is vacuous."""
    assert ("research", "run") in VALID_PATHS
    assert ("curation", "run") in VALID_PATHS
    assert ("daily", "run") in VALID_PATHS
    assert ("views", "validate") in VALID_PATHS
    assert ("knowledge", "card", "create") in VALID_PATHS
    assert ("knowledge", "card", "list") in VALID_PATHS
    assert len(VALID_PATHS) > 25


def test_docs_contain_invocations() -> None:
    """Guard the extractor — a silent regex failure would make the suite vacuous."""
    documented = _documented()
    assert documented, "no documentation files found"
    total = sum(len(v) for v in documented.values())
    assert total > 10, f"extractor found only {total} invocations — regex likely broken"


@pytest.mark.parametrize(
    "rel",
    [pytest.param(rel, id=rel) for rel in _MUST_CARRY_INVOCATIONS],
)
def test_key_docs_are_not_vacuous(rel: str) -> None:
    """Each named document must individually carry at least one invocation.

    Complements ``test_docs_contain_invocations`` (which guards the extractor
    globally) by guarding per-document coverage — see ``_MUST_CARRY_INVOCATIONS``.
    """
    path = _REPO_ROOT / rel
    assert path.is_file(), (
        f"{rel} does not exist. A document named in _MUST_CARRY_INVOCATIONS that is "
        "renamed or deleted must fail loudly here, never vanish into a passing empty set."
    )
    found = _invocations(path.read_text(encoding="utf-8"))
    assert found, (
        f"{rel} yields zero extractable invocations — this document is expected to "
        "carry at least one executable `construct ...` invocation in a code span."
    )


@pytest.mark.parametrize(
    "doc_path",
    [pytest.param(p, id=f"{p.parent.name}/{p.name}") for p in _doc_files()],
)
def test_documented_commands_resolve(doc_path: Path) -> None:
    """Every ``construct ...`` string in this doc resolves, unless known-broken."""
    unresolved = {
        path
        for path in _invocations(doc_path.read_text(encoding="utf-8"))
        if not _resolves(path)
    }
    # An allowlisted path covers its own extensions: `workflow run curation-cycle`
    # is the same defect as `workflow run`, not a second one.
    unexpected = {p for p in unresolved if not _is_known_broken(p)}
    assert not unexpected, (
        f"{doc_path.relative_to(_REPO_ROOT)} documents commands that do not exist: "
        + ", ".join("construct " + " ".join(p) for p in sorted(unexpected))
    )


@pytest.mark.parametrize(
    ("path", "reason"),
    [pytest.param(p, r, id=" ".join(p)) for p, r in sorted(_KNOWN_BROKEN.items())],
)
def test_known_broken_entries_are_still_broken(path: tuple[str, ...], reason: str) -> None:
    """A fixed entry must be deleted from _KNOWN_BROKEN, not left to rot.

    This is what makes the allowlist trustworthy: it can only ever shrink.
    """
    assert not _resolves(path), (
        f"`construct {' '.join(path)}` now resolves ({reason}). "
        "Delete this entry from _KNOWN_BROKEN."
    )


# ---------------------------------------------------------------------------
# WR-07: documented `bash <...>/skills/<name>/run.sh` paths must exist
# ---------------------------------------------------------------------------

# The `_INVOCATION` regex above only matches strings beginning `construct `, so a
# skill doc naming a wrapper script under the wrong directory sailed past every
# check here. `construct-views-generate-data/SKILL.md` documented
# `.claude/skills/views-generate-data/run.sh` while the directory is
# `construct-views-generate-data/` — an agent following it got
# "No such file or directory", a failure the skill's own failure-mode table has no
# row for.
_SCRIPT_REF = re.compile(r"skills/([A-Za-z0-9_-]+)/([A-Za-z0-9_.-]+\.sh)\b")

_SKILLS_DIR = _IMPL / "claude" / "skills"


def test_documented_script_paths_exist() -> None:
    """Every `.../skills/<name>/<script>.sh` path in a skill doc resolves on disk."""
    missing: list[str] = []
    scanned = 0
    for doc_path in _doc_files():
        for span in _code_spans(doc_path.read_text(encoding="utf-8")):
            for skill_name, script in _SCRIPT_REF.findall(span):
                scanned += 1
                if not (_SKILLS_DIR / skill_name / script).is_file():
                    missing.append(f"{doc_path.name}: skills/{skill_name}/{script}")

    assert scanned, (
        "no documented skill script paths found — the extractor regex is likely broken"
    )
    assert not missing, "documented script paths that do not exist:\n" + "\n".join(
        sorted(set(missing))
    )
