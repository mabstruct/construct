# CONSTRUCT v0.3 — Planning

## Purpose

**v0.3** delivers a **testable pipeline and API layer** — hardened capabilities, Python workflow runtime, strict contracts — so **v0.4** can build UI-as-primary on proven foundations.

This is not the UI milestone. v0.4 owns the shell (buttons, wizards, modals). See **[ADR-0003](../CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md)** for the full layered architecture decision.

```text
v0.3  Layer 2–3   Python pipelines + CLI + MCP + contract tests
      Layer 0     Skill specs — Claude/agents invoke via MCP tools
      Spikes      LangGraph (L2/L3 gates) + Streamlit (localhost ops UI)
v0.4  Layer 4     Browser UI-primary — views SPA / CoPilotKit (TBD after spike)
      Layer 3+    HTTP for UI; localhost → cloud
```

**Invoke order:** CLI first → MCP (agentic) → HTTP (browser UI).

**LLM gates:** LangGraph subgraphs with provider config (not hand-rolled per-provider calls).

**UI path:** Streamlit spike in v0.3 informs v0.4 choice (extend v0.2 views vs CoPilotKit).

---

## Master artifact inventory

All skills, agents, workflows, and the capability audit framework:

**[`CONSTRUCT-CLAUDE-spec/artifact-catalog.md`](../CONSTRUCT-CLAUDE-spec/artifact-catalog.md)**

Use it to:

- inventory every capability and classify steps as `PYTHON` vs LLM tier (L1/L2/L3)
- decide v0.3 pipeline implementation order (`PIPE` skills first)
- map future v0.4 UI affordances to v0.3 API commands

---

## Related inputs

| Document | Role |
|----------|------|
| [`adr-0003-v03-pipeline-v04-ui.md`](../CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md) | **Architecture decision** — layers, v0.3/v0.4 split, LLM tiers |
| [`artifact-catalog.md`](../CONSTRUCT-CLAUDE-spec/artifact-catalog.md) | Master inventory + audit matrix |
| [`commands.md`](../CONSTRUCT-CLAUDE-impl/construct/references/commands.md) | Current user command quick-ref |
| [`capabilities.md`](../CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md) | User-facing capability handbook |
| [`user-journeys.md`](../CONSTRUCT-CLAUDE-spec/user-journeys.md) | J1–J3 — re-map to API in v0.3, UI in v0.4 |
| [`tranche-1-mvp.md`](tranche-1-mvp.md) | **Approved** v0.3 tranche 1 scope — registry, CLI, MCP stdio, L2 LangGraph, Streamlit, workflow skeleton |
| [`prd-v02-live-views.md`](../CONSTRUCT-CLAUDE-spec/prd-v02-live-views.md) | v0.2 views — foundation for v0.4 UI shell |

---

## Working rules

1. When planning conflicts with `artifact-catalog.md` skill names or counts, **update the catalog first**.
2. **Workspace SOT unchanged** — pipelines read/write the same files Claude uses today.
3. **SKILL.md + catalog = spec**; **Python = PIPE**; **LangGraph = L2/L3 gates**; skills/agents call **MCP or CLI**.
4. Do not build v0.4 UI until tranche 1 CLI + MCP capabilities have contract tests.
5. **Streamlit spike** (localhost) validates browser UI patterns before v0.4 commitment.

---

## Next steps (planning)

1. Review each skill in the artifact catalog — tag steps: `PYTHON` | `LLM-L1` | `LLM-L2` | `LLM-L3` | `USER-REVIEW`.
2. Draft **v0.3 PRD**: capability registry, CLI, MCP server, LangGraph gate protocol, Streamlit spike scope.
3. Define **v0.3 tranche 1** — see **[`tranche-1-mvp.md`](tranche-1-mvp.md)** (approved).
4. Produce per-skill migration notes: spec steps → Python module → CLI + MCP tool → test fixture.

*v0.4 PRD (UI shell, action model) follows once v0.3 tranche 1 is stable.*

---

## GSD (implementation tracking)

**No active `.planning/` directory.** Python v0.1 GSD archived at [`archive/v01-python/gsd/`](../archive/v01-python/gsd/).

When v0.3 moves from planning to **implementation**, initialize fresh GSD from the v0.3 PRD and artifact catalog. Do not resume the archived Python GSD run.

---

## v0.4 planning

Create `CONSTRUCT-CLAUDE-v04-planning/` when v0.3 pipeline tranche 1 ships. v0.4 scope: UI-primary shell, capability buttons, LLM modals — all calling v0.3 API.
