"""The single enumeration of which views data file is governed by which model.

``views/build/data/`` has two gates: ``views generate`` validates each payload
before writing it, and ``views validate`` validates the files on disk. Until this
module existed, each gate carried its own copy of the file→model map —
``generate.py``'s ``_FILE_MODEL_MAP`` / ``_PER_WS_FILES`` adapter tables and
``cli.py``'s hand-enumerated list inside the ``views validate`` command. Two
copies of one mapping is the same drift hazard the writer/validator divergence
already demonstrated at the *field* level: D-18 added contract models for
``<ws>/stats.json`` and ``<ws>/curation-history.json`` and had to remember to
edit both lists, and forgetting either one would have left a file gated on one
side and ungated on the other. Both consumers now read the tables below, so the
writer and the validator cannot enumerate different files.

**There is deliberately no adapter callable here.** The old tables carried one
per entry, mapping writer keys onto the model's field names — which is precisely
how ``views generate`` came to validate a projection it then discarded and write
something else. Plan 04 conformed the models to the writer (D-01), reducing every
adapter to the identity function; this module drops the concept rather than
keeping an identity callable around for a future edit to re-fork.

The two tables are separate because ``stats.json`` exists twice: once at the data
directory root (written by ``compute_stats.compute_global``) and once per
workspace (written by ``compute_stats.compute_workspace``). Same filename,
different writer, different shape, different contract. A global file is matched
on its exact relative path and a per-workspace file on a trailing
``/<filename>``, so neither can ever be validated against the other's model.

Files with no entry here — ``version.json``, ``_build_meta.json``,
``_generation-warnings.log`` — are build metadata rather than view data and are
deliberately ungated. Every *data* file the generator writes has an entry;
``tests/integration/test_views_generate.py`` asserts that mechanically rather
than trusting this sentence.
"""

from __future__ import annotations

from pydantic import BaseModel

from construct.views.models import (
    ArticlesFile,
    BridgesFile,
    CardsFile,
    ConnectionsFile,
    CurationHistoryFile,
    DigestsFile,
    DomainsFile,
    EventsFile,
    StatsFile,
    WorkspaceStatsFile,
)

#: Data files written once per build, at the root of ``views/build/data/``.
#: Keyed on the exact relative path.
GLOBAL_FILE_CONTRACTS: dict[str, type[BaseModel]] = {
    "bridges.json": BridgesFile,
    "domains.json": DomainsFile,
    "articles.json": ArticlesFile,
    "stats.json": StatsFile,
}

#: Data files written once per workspace, under ``views/build/data/<ws_id>/``.
#: Keyed on the filename, matched against the trailing segment of the relative
#: path. The first four were modelled from the start; ``stats.json`` and
#: ``curation-history.json`` are D-18's additions — the two files that were
#: previously written with no validation at all and never checked by
#: ``views validate`` either.
PER_WORKSPACE_FILE_CONTRACTS: dict[str, type[BaseModel]] = {
    "cards.json": CardsFile,
    "connections.json": ConnectionsFile,
    "digests.json": DigestsFile,
    "events.json": EventsFile,
    "stats.json": WorkspaceStatsFile,
    "curation-history.json": CurationHistoryFile,
}
