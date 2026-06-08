# Phase 1: Contract Canon & Artifact Governance - Discussion Log

**Captured:** 2026-06-08

## Areas Selected

- Workspace shape
- Contract source
- Write gates
- Migration and fixtures
- Support artifacts

## Q&A Audit Trail

### Workspace shape
- **Question:** What should Phase 1 canonize as the official workspace layout?
- **Options shown:** Claude-native shape / Python shape / Hybrid transitional shape
- **Decision:** Claude-native shape.

### Contract source
- **Question:** When spec, templates, skills, and runtime code disagree, what should be authoritative?
- **Options shown:** Spec-template-catalog / Runtime-first / Split authority
- **Decision:** Spec-template-catalog.

### Write gates
- **Question:** How strict should source-of-truth writes be?
- **Options shown:** Hard pre-write blocking / Write then flag / Mixed by artifact
- **Decision:** Hard pre-write blocking.

### Migration and fixtures
- **Question:** What proof and compatibility bar should this phase lock in?
- **Options shown:** Explicit migration + real fixtures / Fixtures only / Migration only
- **Decision:** Explicit migration + real fixtures.

### Canonical fixture target
- **Question:** Which fixture set should be the canonical proof target for Phase 1 hardening?
- **Options shown:** `test-ws/` canonical / `tests/fixtures/v02/` canonical / Both first-class
- **Decision:** `test-ws/` canonical.

### Support artifacts
- **Question:** Should `digests/` and `publish/` be durable support artifacts or purely derived outputs?
- **Options shown:** Durable support artifacts / Purely derived outputs / Split treatment
- **Decision:** Purely derived outputs.

## Outcome Summary

- One canonical workspace shape: active Claude-native layout.
- One authoritative contract source: active spec + templates + artifact catalog.
- Hard pre-write gates for canonical artifacts.
- Explicit migration path required.
- `test-ws/` is the primary proof target.
- `digests/` and `publish/` are derived outputs, not canonical graph truth.
