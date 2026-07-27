---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-07-27T12:31:55.567Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 18 | deviation | src/construct/pipelines/ingestion.py | 246 | GOV-04: ingest_source calls create_card directly outside any apply node; recorded as UNRESOLVED_DIRECT_CALLERS baseline in tests/contract/test_canonical_write_boundary.py, not exempted | open |  | 2026-07-27T12:31:55.567Z |  |

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
  }
]
````
