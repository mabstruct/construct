"""Enumerate every durable workflow run in a workspace (HTTP-07, D-13, D-25).

A run id is handed out once, at run start, and after that it lives only in
whatever the caller wrote down. Every other run capability —
``curation.inspect``, ``research.inspect``, ``daily.inspect``,
``curation.review`` — takes a ``run_id`` it cannot help the caller discover. So a
run whose id is lost is durable state nothing can reach. This module is the
enumeration primitive that closes that gap, and ``workflow.list`` (D-13) is the
registry capability over it, which is what makes CLI, MCP and HTTP gain run
listing at the same moment rather than the browser gaining a private reader over
durable state.

**Three stores, not two.** Run state lives in three places and a listing that
reads two of them is the exact failure HTTP-07 exists to prevent — an audit trail
that answers confidently while a whole workflow type is invisible:

1. ``.construct/workflow/curation-run.sqlite`` — the curation checkpointer.
2. ``.construct/workflow/research-run.sqlite`` — the research checkpointer, a
   separate database file with the same schema.
3. ``.construct/workflow/daily/<run_id>.json`` — the daily receipts. A daily run
   persists a JSON receipt and **never** pauses, so it writes no checkpoint at
   all. A listing built only on the two checkpoint databases therefore reports
   zero daily runs while ``daily.inspect`` happily answers for them.

**A distinct-thread-id query, not the library's checkpoint listing.**
``BaseCheckpointSaver.list(None)`` does enumerate across threads, but it yields
one tuple *per checkpoint*, deserializing every state blob and every pending
write, ordered globally with no grouping. Listing latency would then scale with
run *length* rather than run *count*, so a workspace holding a few long runs
would make the endpoint visibly slow while telling the caller nothing extra. A
``SELECT DISTINCT thread_id`` against the ``checkpoints`` table the checkpointer's
own ``setup()`` creates is the cheap primitive, and the one this module uses.

**No fourth status vocabulary (D-13).** Per-run status comes from the existing
inspect primitive for that workflow type — ``inspect_curation_run``,
``inspect_research_run``, ``inspect_daily_run``. Three status vocabularies
already exist; re-deriving status here from raw checkpoint state would invent a
fourth that drifts from the three capabilities a caller then acts through.

**Cost is O(runs), and that is stated rather than discovered (D-25).** Each
inspect call deserializes one checkpoint, so a workspace with many runs costs one
deserialization per run. That is acceptable for a local single-user proof of
concept, and it is written down here so a future reader meets it as a known
property rather than as a surprise.

**Ordering is a contract.** Entries are sorted by workflow name, then run id.
Two consecutive calls return the same order. A caller may rely on that, and a
future change to it is a visible decision rather than a silent reshuffle.

**What an entry never carries.** Run ids, workflow names, statuses and the two
opaque handles — never a database path, never a receipt path (T-19-05). The
listing crosses the HTTP trust boundary, and the filesystem layout of a
workspace is not the caller's business.

**This module's own blind spot, stated rather than implied.** Enumeration reads
a schema the pinned checkpoint library owns (``checkpoints.thread_id``). If a
future library version renames either, this module finds nothing rather than
raising — which is why ``tests/contract/test_workflow_list.py`` builds one real
run of each of the three types and asserts three distinct workflow values. A
silent zero is what that test exists to turn into a failure.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from construct.llm.curation_run import (
    CHECKPOINT_BUSY_TIMEOUT_MS,
    CurationInspectInput,
    inspect_curation_run,
)
from construct.llm.daily_run import DailyInspectInput, inspect_daily_run
from construct.llm.research_run import InspectInput, inspect_research_run

#: The workflow names an entry's ``workflow`` field can carry. These are the
#: capability-family names a caller already knows (``curation.inspect``,
#: ``research.inspect``, ``daily.inspect``), not new vocabulary.
CURATION = "curation"
RESEARCH = "research"
DAILY = "daily"

#: ``workflow name -> checkpoint database filename`` under the workflow
#: directory. A map rather than two ``if`` branches because the enumeration is a
#: property of the *class* of store, and a fourth checkpointed workflow should be
#: one entry here rather than a third copy of the query.
CHECKPOINT_DATABASES: dict[str, str] = {
    CURATION: "curation-run.sqlite",
    RESEARCH: "research-run.sqlite",
}

#: Where the daily receipts live, relative to the workflow directory. Daily is
#: deliberately NOT in ``CHECKPOINT_DATABASES``: it is a different kind of store,
#: and collapsing the two would hide the very asymmetry this module exists for.
DAILY_RECEIPTS_DIRNAME = "daily"


class RunSummary(BaseModel):
    """One durable run, addressable by the inspect capability for its workflow.

    ``run_id`` + ``workflow`` together identify an entry: the two are a composite
    key, never ``run_id`` alone. Run ids are minted per workflow family, so a
    curation run and a daily receipt CAN share an id string, and merging them
    would make one of the two runs unreachable — the failure this whole module
    exists to prevent, reproduced one level down.

    ``checkpoint_id`` is the resume ETag (GOV-03 / D-11) where the workflow keeps
    checkpoints and ``None`` where it does not (daily). ``gate_id`` names the
    pending review queue and is populated only for a run that is actually paused,
    so a caller reading the listing can go straight to the review capability.

    No field carries a filesystem path (T-19-05).
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow: str
    status: str
    checkpoint_id: str | None = None
    gate_id: str | None = None


def _workflow_dir(workspace: Path | str) -> Path:
    return Path(workspace) / ".construct" / "workflow"


def _distinct_thread_ids(database: Path) -> list[str]:
    """Every distinct ``thread_id`` in a checkpointer database, or ``[]``.

    Opened read-only through a ``file:...?mode=ro`` URI with the run modules'
    own busy timeout, so enumeration can never write to, create, or recover a
    database another process is mid-run on.

    Two absences are answered with an empty list rather than an exception,
    because both are ordinary states of a healthy workspace and neither is the
    caller's mistake:

    * **The file does not exist.** A workspace that has never run this workflow
      has no database. Raising here would make ``workflow.list`` fail on a fresh
      workspace, and truth 6 says an empty workspace lists empty.
    * **The file exists but holds no ``checkpoints`` table.** ``_open_checkpointer``
      materialises the database file on ``sqlite3.connect`` while ``setup()`` runs
      later, so *inspecting a nonexistent run* leaves a zero-byte database behind.
      That file means "no runs", not "corrupt store".
    """
    if not database.is_file():
        return []
    try:
        conn = sqlite3.connect(
            f"file:{database}?mode=ro",
            uri=True,
            check_same_thread=False,
            timeout=CHECKPOINT_BUSY_TIMEOUT_MS / 1000,
        )
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute("SELECT DISTINCT thread_id FROM checkpoints").fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    return [row[0] for row in rows if isinstance(row[0], str) and row[0]]


def _curation_summary(workspace: str, run_id: str) -> RunSummary:
    result = inspect_curation_run(
        CurationInspectInput(workspace_path=workspace, run_id=run_id)
    )
    return RunSummary(
        run_id=run_id,
        workflow=CURATION,
        status=result.status,
        checkpoint_id=result.checkpoint_id,
        gate_id=result.gate_id,
    )


def _research_summary(workspace: str, run_id: str) -> RunSummary:
    result = inspect_research_run(InspectInput(workspace_path=workspace, run_id=run_id))
    return RunSummary(
        run_id=run_id,
        workflow=RESEARCH,
        status=result.status,
        checkpoint_id=result.checkpoint_id,
        gate_id=result.gate_id if result.status == "awaiting_review" else None,
    )


def _daily_summary(workspace: str, run_id: str) -> RunSummary:
    result = inspect_daily_run(DailyInspectInput(workspace_path=workspace, run_id=run_id))
    return RunSummary(run_id=run_id, workflow=DAILY, status=result.status)


#: ``workflow name -> the inspect adapter that turns one id into one summary``.
_SUMMARY_FOR = {
    CURATION: _curation_summary,
    RESEARCH: _research_summary,
    DAILY: _daily_summary,
}


def _summarise(workspace: str, workflow: str, run_id: str) -> RunSummary | None:
    """One run's summary, or ``None`` when the id is not addressable.

    Every inspect input kebab-validates ``run_id`` (T-11-01), because the id
    becomes a LangGraph thread id and steers a path. An id that fails that
    validator names something no inspect capability can be called with, so
    listing it would produce an entry a caller cannot act on. Skipping it is the
    honest answer; it is also the answer that keeps a hand-dropped file in the
    receipts directory from breaking enumeration for every real run beside it.
    """
    try:
        return _SUMMARY_FOR[workflow](workspace, run_id)
    except ValidationError:
        return None


def _daily_run_ids(workflow_dir: Path) -> list[str]:
    """Run ids from the daily receipts directory, derived from the file stem.

    Globbed rather than read: the receipt's *name* is the id, and
    ``inspect_daily_run`` is what parses the contents. A directory that does not
    exist yields no ids — a workspace that has never run a daily cycle is not an
    error.
    """
    receipts = workflow_dir / DAILY_RECEIPTS_DIRNAME
    if not receipts.is_dir():
        return []
    return [path.stem for path in receipts.glob("*.json") if path.is_file()]


def list_workflow_runs(
    workspace: Path | str, status: str | None = None
) -> list[RunSummary]:
    """Every durable run in ``workspace``, across all three stores.

    Reads the curation checkpoint database, the research checkpoint database and
    the daily receipts directory — see the module docstring for why all three are
    mandatory and why a distinct-thread-id query is used instead of the
    checkpoint library's own listing call.

    ``status`` narrows the result to entries whose status matches exactly. A
    filter that matches nothing returns an empty list; it is not an error,
    because "no run is currently awaiting review" is a legitimate answer to a
    legitimate question.

    Returns entries sorted by workflow name, then run id — a stable, specified
    order two consecutive calls reproduce.

    Cost is one checkpoint deserialization per checkpointed run (D-25).
    """
    workspace_path = str(workspace)
    workflow_dir = _workflow_dir(workspace)

    discovered: list[tuple[str, str]] = []
    for workflow, filename in CHECKPOINT_DATABASES.items():
        for run_id in _distinct_thread_ids(workflow_dir / filename):
            discovered.append((workflow, run_id))
    for run_id in _daily_run_ids(workflow_dir):
        discovered.append((DAILY, run_id))

    summaries: list[RunSummary] = []
    for workflow, run_id in discovered:
        summary = _summarise(workspace_path, workflow, run_id)
        if summary is not None:
            summaries.append(summary)

    if status is not None:
        summaries = [entry for entry in summaries if entry.status == status]

    return sorted(summaries, key=lambda entry: (entry.workflow, entry.run_id))
