---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-07-30T17:20:59.136Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 18 | deviation | src/construct/pipelines/ingestion.py | 246 | GOV-04: ingest_source calls create_card directly outside any apply node; recorded as UNRESOLVED_DIRECT_CALLERS baseline in tests/contract/test_canonical_write_boundary.py, not exempted | open |  | 2026-07-27T12:31:55.567Z |  |
| 2 | 18 | deviation | src/construct/llm/research_run.py | 919 | research_run.update_seeds_and_log emits gate_review_approved from the decision, not from the write: ingest_batch tracks skipped_existing for refs/cards that already existed, so an idempotent re-run records approvals for ingests that did not happen (T-18-06 class, research graph). Curation is fixed and invariant-tested by 18-08; research is out of that plan's declared files. | open |  | 2026-07-30T17:20:59.136Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "18",
    "file": "src/construct/pipelines/ingestion.py",
    "line": 246,
    "description": "GOV-04: ingest_source calls create_card directly outside any apply node; recorded as UNRESOLVED_DIRECT_CALLERS baseline in tests/contract/test_canonical_write_boundary.py, not exempted",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-07-27T12:31:55.567Z",
    "resolved_at": null
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "18",
    "file": "src/construct/llm/research_run.py",
    "line": 919,
    "description": "research_run.update_seeds_and_log emits gate_review_approved from the decision, not from the write: ingest_batch tracks skipped_existing for refs/cards that already existed, so an idempotent re-run records approvals for ingests that did not happen (T-18-06 class, research graph). Curation is fixed and invariant-tested by 18-08; research is out of that plan's declared files.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-07-30T17:20:59.136Z",
    "resolved_at": null
  }
]
````
