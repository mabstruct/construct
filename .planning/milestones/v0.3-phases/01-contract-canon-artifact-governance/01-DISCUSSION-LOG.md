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

### Python runtime vs Claude-native skills (post-UAT)
- **Context:** During Phase 1 UAT, we tested `construct validate .` (Python CLI) against fixture workspaces. But CONSTRUCT's product is the Claude-native skills — that IS the current implementation. The Python runtime at `src/construct/` is a dormant parallel implementation from the v0.1 Python track.
- **Finding:** Testing through the Python runtime tests a dormant parallel implementation, not the product. The relationship is ambiguous: `src/construct/` is neither shared engine (skills don't call it) nor dead code (Phase 1 reconciled its schemas). This needs resolution in v0.3 planning: wire skills to call Python (making it the shared engine) or remove it.
- **Implication:** Future testing should test the skill path directly, or wire skills to the Python layer and test through that.

### Python runtime role (resolved 2026-06-09)
- **Question:** What is the Python runtime's role going forward?
- **Options shown:** Remove it / Wire skills to call it as shared engine / Hybrid (Python for deterministic work, skills for judgment)
- **Decision:** Hybrid via MCP. Python handles deterministic operations (card CRUD, ref management, connections, validation). Skills become thin wrappers that call Python through MCP tools. Claude remains the runtime for judgment, orchestration, and workflow.
- **Sequencing:** Phase 2 and 3 remain separate. Phase 2 builds the MCP server incrementally (starting with `workspace-validate` as proof) and adds knowledge ops handlers + MCP tools + thin skill wrappers. Phase 3 completes the capability registry and CLI parity.
- **Implication:** MCP infrastructure is built incrementally in Phase 2, not as a separate up-front project. Each new MCP tool proves the pattern before the next is added.

## Outcome Summary

- One canonical workspace shape: active Claude-native layout.
- One authoritative contract source: active spec + templates + artifact catalog.
- Hard pre-write gates for canonical artifacts.
- Explicit migration path required.
- `test-ws/` is the primary proof target.
- `digests/` and `publish/` are derived outputs, not canonical graph truth.
- Python runtime role (Phase 2+): deterministic engine via MCP; skills become thin MCP-calling wrappers.
- MCP server built incrementally in Phase 2 starting with `workspace-validate` proof.
