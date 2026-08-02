"""The OQ-4 pin: both checkpointers declare WAL and their own busy timeout.

This module is the PIN, not the implementation. It exists because the
concurrency contract recorded as D-14 was previously in force by accident —
``SqliteSaver.setup()`` runs ``PRAGMA journal_mode=WAL`` as the first statement
of its own ``executescript``, and ``sqlite3.connect`` defaults to
``timeout=5.0`` i.e. a 5 000 ms busy timeout. Correct today, silently reversible
by a dependency bump, with no test that would notice.

A green run here means the PRAGMAs are OURS: ``curation_run._open_checkpointer``
and ``research_run._open_checkpointer`` set them on the connection themselves. If
a langgraph upgrade drops the library's own WAL pragma, or someone deletes the
``timeout=`` argument, these assertions fail instead of the guarantee reverting
quietly. ``busy_timeout`` is asserted for EXACT equality rather than a lower
bound on purpose — a silent downgrade to the stdlib's inherited 5 000 ms must be
a failure, and a ``>= 5000`` assertion would wave it through.

See ``CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md`` for
the contract, its stated limitation (no cross-process mutual exclusion), and the
ETag arbitration that stands in for one.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from construct.llm import curation_run, research_run


#: The two checkpointer modules, parametrised as one contract rather than two
#: special cases — adr-0004 governs them as a single artifact class, so a change
#: that lands on only one of them is drift, not a variant.
_CHECKPOINTERS = [
    pytest.param(curation_run, "curation-run.sqlite", id="curation"),
    pytest.param(research_run, "research-run.sqlite", id="research"),
]


@pytest.mark.parametrize("module, db_name", _CHECKPOINTERS)
def test_checkpointer_declares_wal_journal_mode(tmp_path: Path, module, db_name: str) -> None:
    """``PRAGMA journal_mode`` reads ``wal`` on a live checkpointer connection."""
    _saver, conn = module._open_checkpointer(tmp_path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()

    assert mode.lower() == "wal", f"{db_name}: expected WAL journaling, got {mode!r}"


@pytest.mark.parametrize("module, db_name", _CHECKPOINTERS)
def test_checkpointer_declares_the_d14_busy_timeout(tmp_path: Path, module, db_name: str) -> None:
    """``PRAGMA busy_timeout`` equals ``CHECKPOINT_BUSY_TIMEOUT_MS`` exactly.

    Exact equality, not a lower bound: the point of the assertion is to catch a
    silent downgrade back to ``sqlite3.connect``'s inherited 5 000 ms default.
    """
    _saver, conn = module._open_checkpointer(tmp_path)
    try:
        timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    finally:
        conn.close()

    assert timeout_ms == module.CHECKPOINT_BUSY_TIMEOUT_MS, (
        f"{db_name}: busy_timeout is {timeout_ms} ms, expected "
        f"{module.CHECKPOINT_BUSY_TIMEOUT_MS} ms (D-14)"
    )


def test_both_checkpointers_agree_on_the_timeout_value() -> None:
    """The two constants are one contract — 30 000 ms — not two independent knobs."""
    assert curation_run.CHECKPOINT_BUSY_TIMEOUT_MS == 30_000
    assert research_run.CHECKPOINT_BUSY_TIMEOUT_MS == curation_run.CHECKPOINT_BUSY_TIMEOUT_MS


@pytest.mark.parametrize("module, db_name", _CHECKPOINTERS)
def test_wal_persists_for_a_second_independent_connection(
    tmp_path: Path, module, db_name: str
) -> None:
    """A fresh ``sqlite3.connect`` on the same file also reports ``wal``.

    WAL is recorded in the database header, so the mode is a property of the
    FILE rather than of the connection that set it. This is what makes the
    contract meaningful across processes — a CLI resume opening the checkpoint a
    server-spawned run created inherits WAL without having to ask for it.
    """
    _saver, conn = module._open_checkpointer(tmp_path)
    try:
        db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    finally:
        conn.close()

    assert db_path.name == db_name

    second = sqlite3.connect(str(db_path))
    try:
        mode = second.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        second.close()

    assert mode.lower() == "wal", (
        f"{db_name}: a second connection saw {mode!r} — WAL is not persisted in the header"
    )


@pytest.mark.parametrize("module, db_name", _CHECKPOINTERS)
def test_checkpointer_introduces_no_lockfile(tmp_path: Path, module, db_name: str) -> None:
    """No lockfile and no cross-process mutex are created alongside the database.

    D-14 rejected both a server-held single-flight lock (its guarantee would be
    invisible to a CLI resume) and a lockfile (stale-lock recovery's failure mode
    is a permanently un-resumable run). This asserts the rejection held: the only
    files under ``.construct/workflow/`` are sqlite's own database and its WAL
    sidecars.
    """
    _saver, conn = module._open_checkpointer(tmp_path)
    try:
        conn.execute("PRAGMA journal_mode").fetchone()
    finally:
        conn.close()

    workflow_dir = tmp_path / ".construct" / "workflow"
    stem = db_name.removesuffix(".sqlite")
    allowed = {db_name, f"{db_name}-wal", f"{db_name}-shm", f"{db_name}-journal"}
    unexpected = [p.name for p in workflow_dir.iterdir() if p.name not in allowed]

    assert unexpected == [], f"{stem}: unexpected files beside the checkpoint DB: {unexpected}"
