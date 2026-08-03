"""HTTP-07 — every durable run in a workspace is enumerable, from all three stores.

A run id is minted once and then lives only wherever the caller wrote it down.
``curation.inspect``, ``research.inspect``, ``daily.inspect`` and
``curation.review`` all take a ``run_id`` they cannot help a caller discover, so
a run whose id is lost is durable state nothing can reach. ``workflow.list``
(D-13) closes that, as a *registry capability* rather than as a browser-side
checkpoint reader — which is what makes CLI, MCP and HTTP gain run listing at the
same moment.

What this module is really guarding
-----------------------------------
**The three-store claim, and the specific way it would be broken.** Run state
lives in a curation checkpoint database, a research checkpoint database, and a
directory of daily JSON receipts. A daily run never pauses and writes no
checkpoint at all, so a listing built on the two checkpoint databases reports
*zero* daily runs while ``daily.inspect`` answers for them perfectly well — an
audit trail that answers confidently while a whole workflow type is invisible,
which is the failure HTTP-07 exists to prevent, reproduced inside its own fix.

A fixture that only ever ran curation is the documented way that gap survives
review. So ``runs_workspace`` below runs **one real run of each of the three
types**, offline, and the coverage test asserts three *distinct* workflow values
rather than "some entries came back".

**D-25, asserted rather than assumed.** Per-run status comes from the existing
inspect primitives, so listing costs one checkpoint deserialization per run. The
thing that must NOT happen is enumeration going through the checkpoint library's
own listing call, which yields one tuple per *checkpoint* — that would make
latency scale with run length instead of run count. ``test_enumeration_never_uses
_the_library_checkpoint_listing`` pins that by making the library call explode.

This module's own blind spot, stated rather than implied
--------------------------------------------------------
Enumeration reads a schema the pinned checkpoint library owns
(``checkpoints.thread_id``). Every test here builds its runs through the real run
entrypoints, so a library schema change would surface as an empty listing against
a workspace that demonstrably holds runs — a failure, not a silent zero. What no
test here covers is a *fourth* durable store added later: nothing mechanically
forces a new workflow type into ``CHECKPOINT_DATABASES``, and the same gap that
made daily invisible would reopen. That is a real residual risk and it is written
down rather than papered over.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from construct.llm.workflow_list import (
    CHECKPOINT_DATABASES,
    CURATION,
    DAILY,
    DAILY_RECEIPTS_DIRNAME,
    RESEARCH,
    RunSummary,
    list_workflow_runs,
)

#: The canonical source-of-truth artifacts a read-only listing may never touch.
_CANONICAL = ("cards", "refs", "connections.json", "search-seeds.json")


# ---------------------------------------------------------------------------
# Offline fixtures — real runs, no credentials, no network
# ---------------------------------------------------------------------------


def _new_workspace(root: Path, name: str) -> Path:
    """A real, discoverable CONSTRUCT workspace built by the real service.

    ``initialize_workspace`` rather than hand-written fixture files: a
    hand-assembled tree can satisfy the workspace check while being something the
    run modules would reject, and then these tests would assert against a shape
    the product never produces.
    """
    from construct.services.init import DomainInitInput, initialize_workspace

    workspace = root / name
    initialize_workspace(
        workspace,
        DomainInitInput(
            domain_id="test-domain",
            display_name="Test Domain",
            scope="A test domain for the workflow-listing contract tests.",
            taxonomy_seeds=["test-category"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["test research"],
        ),
    )
    return workspace


def _go_offline(monkeypatch) -> None:
    """Pin every provider seam shut, and make an escape an assertion failure.

    Two stubs and one tripwire, which together let the *real* run entrypoints
    execute end to end with no credential and no socket:

    * ``research_run._run_search`` returns no results, so retrieval is a no-op.
    * ``research_score.run_gate`` returns an empty gate output. It is called even
      for zero results, and stubbing it here is the same seam the Phase 10 run
      tests use.
    * ``factory.build_chat_model`` raises. Leaving the provider factory reachable
      would let a machine that happens to have ``ANTHROPIC_API_KEY`` set turn
      these into network tests that pass for the wrong reason — and pass
      *differently* in CI. The assertion is the point: it converts "we think this
      is offline" into "a provider call fails the test that made it".
    """
    from construct.llm import factory, research_run, research_score

    def _no_provider(*args, **kwargs):
        raise AssertionError("a provider call escaped the offline fixture")

    monkeypatch.setattr(research_run, "_run_search", lambda *a, **k: [])
    monkeypatch.setattr(
        research_score, "run_gate", lambda *a, **k: research_score.ResearchScoreGateOutput()
    )
    monkeypatch.setattr(factory, "build_chat_model", _no_provider)


@pytest.fixture(scope="module")
def runs_workspace(tmp_path_factory) -> Path:
    """One workspace holding runs in all three stores, plus an id collision.

    Built by two real calls:

    1. ``curation.run`` with the id ``shared-run``.
    2. ``daily.run`` with the id ``shared-run`` — which writes a daily receipt
       under that id and composes a curation child and a research child of its
       own.

    That yields four runs across the three stores, and the ``shared-run`` id
    deliberately names *two* of them (one curation run, one daily receipt).
    Making the collision real rather than synthetic matters: run ids are minted
    per workflow family, so a listing keyed on ``run_id`` alone would silently
    merge two live runs and make one unreachable — the same class of defect as
    not reading the receipts directory at all.

    Module-scoped because each run is genuine work; every test below reads it and
    none mutates it.
    """
    monkeypatch = pytest.MonkeyPatch()
    try:
        _go_offline(monkeypatch)
        workspace = _new_workspace(tmp_path_factory.mktemp("runs"), "demo")

        from construct.llm.curation_run import CurationRunInput, run_curation_run
        from construct.llm.daily_run import DailyRunInput, run_daily_run

        run_curation_run(
            CurationRunInput(workspace_path=str(workspace), run_id="shared-run")
        )
        run_daily_run(DailyRunInput(workspace_path=str(workspace), run_id="shared-run"))
        return workspace
    finally:
        monkeypatch.undo()


@pytest.fixture(scope="module")
def daily_only_workspace(tmp_path_factory) -> Path:
    """A workspace whose daily receipt id is NOT also a checkpoint thread id.

    Deliberately separate from ``runs_workspace``, whose whole point is that the
    ``shared-run`` id names both a curation run and a daily receipt. That makes it
    the wrong subject for the non-vacuity proof below: the claim there is "this
    entry could only have come from reading the receipts directory", and it needs
    a daily id no checkpoint database contains. ``daily.run`` names its composed
    children ``<id>-curation`` / ``<id>-research``, so the parent id itself is
    never a thread id.
    """
    monkeypatch = pytest.MonkeyPatch()
    try:
        _go_offline(monkeypatch)
        workspace = _new_workspace(tmp_path_factory.mktemp("daily"), "demo")

        from construct.llm.daily_run import DailyRunInput, run_daily_run

        run_daily_run(DailyRunInput(workspace_path=str(workspace), run_id="daily-only"))
        return workspace
    finally:
        monkeypatch.undo()


@pytest.fixture(scope="module")
def empty_workspace(tmp_path_factory) -> Path:
    """A real workspace that has never run anything."""
    return _new_workspace(tmp_path_factory.mktemp("empty"), "demo")


@pytest.fixture(scope="module")
def single_run_workspace(tmp_path_factory) -> Path:
    """A real workspace holding exactly one run."""
    monkeypatch = pytest.MonkeyPatch()
    try:
        _go_offline(monkeypatch)
        workspace = _new_workspace(tmp_path_factory.mktemp("single"), "demo")

        from construct.llm.curation_run import CurationRunInput, run_curation_run

        run_curation_run(
            CurationRunInput(workspace_path=str(workspace), run_id="only-run")
        )
        return workspace
    finally:
        monkeypatch.undo()


@pytest.fixture(scope="module")
def paused_workspace(tmp_path_factory) -> Path:
    """A real workspace whose single curation run is paused at its review gate.

    Two promotable cards plus a canned promotion verdict give the consolidated
    gate a non-empty queue, which is what makes ``curation.run`` interrupt. The
    L3 gates are driven through the ``build_chat_model`` seam the Phase 11 tests
    already use, so the pause is produced by the real graph rather than by
    writing a checkpoint by hand — a hand-written checkpoint would prove nothing
    about the status a real paused run reports.
    """
    from construct.llm import factory, research_run, research_score
    from construct.llm.curation_connect import ConnectionTypeDecision
    from construct.llm.curation_promote import PromotionDecision
    from construct.services.knowledge import create_card

    class _GateRoutingMock:
        """One ``build_chat_model`` seam driving both L3 gates in one run.

        ``curation.run`` fans out over the promotion gate and the
        connection-typing gate, and one canned object cannot satisfy both, so
        this dispatches on the requested structured-output model class. A local
        copy of the Phase 11 idiom rather than an import of a private test
        helper.
        """

        def __init__(self, promotion, connection) -> None:
            self._promotion = promotion
            self._connection = connection
            self._selected = None

        def with_structured_output(self, model_class, **kwargs):
            name = getattr(model_class, "__name__", "")
            self._selected = self._connection if "Connection" in name else self._promotion
            return self

        def invoke(self, messages):
            return self._selected

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(research_run, "_run_search", lambda *a, **k: [])
        monkeypatch.setattr(
            research_score,
            "run_gate",
            lambda *a, **k: research_score.ResearchScoreGateOutput(),
        )
        mock = _GateRoutingMock(
            PromotionDecision(
                card_id="_",
                decision="promote",
                target_lifecycle="growing",
                reasoning="gate reasoning",
                method="llm-judgment",
            ),
            ConnectionTypeDecision(
                from_card_id="_",
                to_card_id="_",
                connection_type="supports",
                reasoning="typed by the connection gate",
            ),
        )
        monkeypatch.setattr(
            factory, "build_chat_model", lambda cfg, *, temperature=0.2: mock
        )

        workspace = _new_workspace(tmp_path_factory.mktemp("paused"), "demo")
        for card_id, title in (("card-a", "Card A"), ("card-b", "Card B")):
            create_card(
                workspace,
                {
                    "id": card_id,
                    "title": title,
                    "epistemic_type": "finding",
                    "domains": ["test-domain"],
                    "content_categories": ["test-category"],
                    "confidence": 3,
                    "source_tier": 3,
                },
            )

        from construct.llm.curation_run import CurationRunInput, run_curation_run

        result = run_curation_run(
            CurationRunInput(workspace_path=str(workspace), run_id="paused-run")
        )
        assert result.status == "awaiting_review", (
            "fixture precondition: the run must actually pause, otherwise the "
            f"paused-run assertions below are vacuous (got {result.status})"
        )
        return workspace
    finally:
        monkeypatch.undo()


# ---------------------------------------------------------------------------
# The three-store claim
# ---------------------------------------------------------------------------


def test_all_three_stores_are_read(runs_workspace: Path) -> None:
    """One run of each type is listed, discriminated by three distinct workflows.

    Asserted as distinct *values*, not as "at least one entry": a listing that
    read only the checkpoint databases would still return entries, and a
    membership check on curation alone would pass while daily was invisible.
    """
    entries = list_workflow_runs(runs_workspace)
    workflows = {entry.workflow for entry in entries}
    assert workflows == {CURATION, RESEARCH, DAILY}, (
        "a durable store went unread — workflows present: "
        f"{sorted(workflows)}, entries: {[(e.workflow, e.run_id) for e in entries]}"
    )


def test_a_checkpoint_only_listing_could_not_have_produced_the_daily_entry(
    daily_only_workspace: Path,
) -> None:
    """The daily entry is provably NOT recoverable from either checkpoint database.

    This is the non-vacuity floor under the test above. Without it, a daily run
    id that *happened* to also be a checkpoint thread id would let a
    checkpoint-only implementation pass — it would have found the id, by
    coincidence, in a store that knows nothing about daily runs. Here the daily
    id is asserted absent from both databases' thread-id sets first, so its
    presence in the listing can only have come from reading the receipts
    directory.
    """
    import sqlite3

    entries = list_workflow_runs(daily_only_workspace)
    daily_ids = {entry.run_id for entry in entries if entry.workflow == DAILY}
    assert daily_ids == {"daily-only"}, entries

    thread_ids: set[str] = set()
    for filename in CHECKPOINT_DATABASES.values():
        database = daily_only_workspace / ".construct" / "workflow" / filename
        conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            thread_ids |= {
                row[0] for row in conn.execute("SELECT DISTINCT thread_id FROM checkpoints")
            }
        finally:
            conn.close()
    assert thread_ids, "fixture precondition: the checkpoint databases must hold runs"

    assert not (daily_ids & thread_ids), (
        "the daily run ids also exist as checkpoint threads, so this test can no "
        "longer distinguish a three-store listing from a checkpoint-only one"
    )


def test_the_daily_entry_carries_no_checkpoint_handle(runs_workspace: Path) -> None:
    """A daily run writes a receipt and never pauses, so it has no checkpoint.

    Recorded as an assertion because the tempting shortcut — giving every entry a
    checkpoint id — would quietly hand a caller a resume ETag for a run that
    cannot be resumed.
    """
    daily = [entry for entry in list_workflow_runs(runs_workspace) if entry.workflow == DAILY]
    assert daily
    assert all(entry.checkpoint_id is None for entry in daily)


def test_checkpointed_entries_carry_their_checkpoint_handle(runs_workspace: Path) -> None:
    checkpointed = [
        entry
        for entry in list_workflow_runs(runs_workspace)
        if entry.workflow in CHECKPOINT_DATABASES
    ]
    assert checkpointed
    assert all(entry.checkpoint_id for entry in checkpointed)


# ---------------------------------------------------------------------------
# Pause, empty, single, collision, ordering
# ---------------------------------------------------------------------------


def test_a_paused_run_reports_awaiting_review_and_its_queue_handle(
    paused_workspace: Path,
) -> None:
    """Truth 2: a run paused awaiting review says so, and names its queue.

    Both halves matter. The status alone tells a caller something is pending; the
    gate handle is what lets them go straight to ``curation.review`` instead of
    having to guess that the queue handle equals the run id.
    """
    entries = list_workflow_runs(paused_workspace)
    paused = [entry for entry in entries if entry.run_id == "paused-run"]
    assert len(paused) == 1, entries
    assert paused[0].workflow == CURATION
    assert paused[0].status == "awaiting_review"
    assert paused[0].gate_id == "paused-run"


def test_a_completed_run_carries_no_gate_handle(single_run_workspace: Path) -> None:
    """The gate handle discriminates. If every entry carried one, the assertion
    above would pass for a listing that never noticed the pause at all."""
    (entry,) = list_workflow_runs(single_run_workspace)
    assert entry.status != "awaiting_review"
    assert entry.gate_id is None


def test_an_empty_workspace_lists_nothing_and_is_not_an_error(
    empty_workspace: Path,
) -> None:
    """Truth 6, first half: no runs is an empty list, never an exception."""
    assert list_workflow_runs(empty_workspace) == []


def test_a_workspace_with_exactly_one_run_lists_exactly_one_entry(
    single_run_workspace: Path,
) -> None:
    """Truth 6, second half. The boundary above zero is where an off-by-one in
    the store-walking loop would show, and where an empty-list special case would
    have swallowed the only run."""
    entries = list_workflow_runs(single_run_workspace)
    assert len(entries) == 1
    assert entries[0].run_id == "only-run"
    assert entries[0].workflow == CURATION


def test_a_shared_run_id_across_workflows_is_two_entries(runs_workspace: Path) -> None:
    """Truth 7: ``run_id`` alone is not a key — ``(workflow, run_id)`` is.

    Merging these would report one run where two exist and make the other
    unreachable by exactly the mechanism this capability was written to fix.
    """
    shared = [
        entry for entry in list_workflow_runs(runs_workspace) if entry.run_id == "shared-run"
    ]
    assert len(shared) == 2, shared
    assert {entry.workflow for entry in shared} == {CURATION, DAILY}


def test_entries_are_ordered_by_workflow_then_run_id(runs_workspace: Path) -> None:
    """Truth 8: the order is specified, so a caller may rely on it."""
    entries = list_workflow_runs(runs_workspace)
    assert [(e.workflow, e.run_id) for e in entries] == sorted(
        (e.workflow, e.run_id) for e in entries
    )


def test_two_consecutive_calls_return_the_same_order(runs_workspace: Path) -> None:
    """Stability, asserted separately from sortedness.

    A listing whose store-walk order varied between calls could still be sorted
    each time and still shuffle equal-key entries, so sortedness alone does not
    imply reproducibility.
    """
    assert list_workflow_runs(runs_workspace) == list_workflow_runs(runs_workspace)


# ---------------------------------------------------------------------------
# The status filter
# ---------------------------------------------------------------------------


def test_a_status_filter_narrows_the_result(runs_workspace: Path) -> None:
    entries = list_workflow_runs(runs_workspace)
    statuses = {entry.status for entry in entries}
    assert statuses, "fixture precondition: the workspace holds runs"
    for status in statuses:
        filtered = list_workflow_runs(runs_workspace, status=status)
        assert filtered == [entry for entry in entries if entry.status == status]
        assert filtered, "a status measured from the listing must match something"


def test_an_unmatched_status_filter_is_an_empty_list_not_an_error(
    runs_workspace: Path,
) -> None:
    """"Nothing is awaiting review" is a legitimate answer to a legitimate
    question, so an unmatched filter is emptiness rather than failure."""
    assert list_workflow_runs(runs_workspace, status="no-such-status") == []


def test_the_unfiltered_listing_is_the_union_of_its_status_slices(
    runs_workspace: Path,
) -> None:
    """The filter partitions rather than drops. Without this, a filter that
    silently discarded an entry no slice claimed would pass every test above."""
    entries = list_workflow_runs(runs_workspace)
    sliced: list[RunSummary] = []
    for status in {entry.status for entry in entries}:
        sliced.extend(list_workflow_runs(runs_workspace, status=status))
    assert sorted((e.workflow, e.run_id) for e in sliced) == sorted(
        (e.workflow, e.run_id) for e in entries
    )


# ---------------------------------------------------------------------------
# Cost, disclosure, and the awkward filesystem states
# ---------------------------------------------------------------------------


def test_enumeration_never_uses_the_library_checkpoint_listing(
    runs_workspace: Path, monkeypatch
) -> None:
    """D-25's other half: the cheap primitive is a distinct-thread-id query.

    ``BaseCheckpointSaver.list`` deserializes every state blob and every pending
    write for every checkpoint, so using it would make listing latency scale with
    run *length* rather than run *count* — invisible on a fixture with short runs
    and very visible on a real workspace. Timing cannot assert that at this size,
    so the library call is made to explode instead: if enumeration reaches for
    it, this test fails immediately rather than a year later as a performance
    complaint.
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    def _explode(*args, **kwargs):
        raise AssertionError(
            "enumeration used the checkpoint library's listing call, which is "
            "O(checkpoints) rather than O(runs) (D-25)"
        )

    monkeypatch.setattr(SqliteSaver, "list", _explode)
    assert list_workflow_runs(runs_workspace)


def test_no_entry_carries_a_filesystem_path(runs_workspace: Path) -> None:
    """T-19-05: the listing crosses the HTTP trust boundary.

    Run ids, workflow names, statuses and two opaque handles — never a database
    path and never a receipt path. Asserted over every string field of every
    entry so a field added later is covered without this test being edited.
    """
    workspace_text = str(runs_workspace)
    for entry in list_workflow_runs(runs_workspace):
        for name, value in entry.model_dump().items():
            if not isinstance(value, str):
                continue
            assert workspace_text not in value, f"{name} leaked the workspace path"
            assert "/" not in value, f"{name} looks like a path: {value!r}"
            assert ".sqlite" not in value and ".json" not in value, (
                f"{name} leaked a store filename: {value!r}"
            )


def _canonical_fingerprint(workspace: Path) -> dict[str, str]:
    """Name + content hash of every canonical source-of-truth file."""
    fingerprint: dict[str, str] = {}
    for relative in _CANONICAL:
        target = workspace / relative
        paths = sorted(target.rglob("*")) if target.is_dir() else [target]
        for path in paths:
            if path.is_file():
                fingerprint[str(path.relative_to(workspace))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    return fingerprint


def test_listing_writes_nothing_to_the_canonical_workspace(
    paused_workspace: Path,
) -> None:
    """Enumerating a *paused* run must not resume it.

    The paused workspace is the right subject: it is the one state where a
    listing that accidentally advanced the graph would apply real canonical
    writes. A byte-level fingerprint is used rather than an exception assertion,
    because "it did not raise" is also true of a listing that wrote.
    """
    before = _canonical_fingerprint(paused_workspace)
    entries = list_workflow_runs(paused_workspace)
    assert any(entry.status == "awaiting_review" for entry in entries)
    assert _canonical_fingerprint(paused_workspace) == before
    assert list_workflow_runs(paused_workspace) == entries


def test_a_database_without_a_checkpoints_table_lists_nothing(tmp_path: Path) -> None:
    """The state ``_open_checkpointer`` leaves behind on a miss.

    ``sqlite3.connect`` materialises the database file while ``setup()`` runs
    later, so *inspecting a run that does not exist* leaves an empty database on
    disk. Treating that as a corrupt store would make ``workflow.list`` fail on a
    workspace whose only sin is that somebody typed a wrong run id once.
    """
    workspace = _new_workspace(tmp_path, "demo")
    workflow_dir = workspace / ".construct" / "workflow"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    for filename in CHECKPOINT_DATABASES.values():
        (workflow_dir / filename).touch()

    assert list_workflow_runs(workspace) == []


def test_a_receipt_that_is_not_addressable_is_skipped_not_fatal(
    tmp_path: Path,
) -> None:
    """A file in the receipts directory whose stem is not a valid run id.

    Every inspect input kebab-validates ``run_id`` (T-11-01), so such a file
    names something no capability can be called with — listing it would hand the
    caller an entry they cannot act on. It must not take the whole listing down
    with it either, which is the half that matters: one stray file must not make
    every real run beside it unreachable.
    """
    monkeypatch = pytest.MonkeyPatch()
    try:
        _go_offline(monkeypatch)
        workspace = _new_workspace(tmp_path, "demo")

        from construct.llm.curation_run import CurationRunInput, run_curation_run
        from construct.llm.daily_run import DailyRunInput, run_daily_run

        run_daily_run(DailyRunInput(workspace_path=str(workspace), run_id="good-daily"))
        run_curation_run(
            CurationRunInput(workspace_path=str(workspace), run_id="good-curation")
        )
    finally:
        monkeypatch.undo()

    receipts = workspace / ".construct" / "workflow" / DAILY_RECEIPTS_DIRNAME
    (receipts / "Not A Run Id.json").write_text(json.dumps({}), encoding="utf-8")

    entries = list_workflow_runs(workspace)
    assert "good-daily" in {entry.run_id for entry in entries if entry.workflow == DAILY}
    assert "good-curation" in {
        entry.run_id for entry in entries if entry.workflow == CURATION
    }
    assert all(entry.run_id != "Not A Run Id" for entry in entries)


def test_a_missing_workspace_lists_nothing_rather_than_raising(tmp_path: Path) -> None:
    """A directory that does not exist has no stores, which is the same shape as
    a workspace that has never run anything. Raising an ``OSError`` here would
    escape as an unhandled 500 whose traceback carries a filesystem path."""
    assert list_workflow_runs(tmp_path / "no-such-workspace") == []
