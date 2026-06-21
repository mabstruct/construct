# CONSTRUCT v0.3 — Planning

## Purpose

**v0.3** delivered a **testable pipeline and API layer** — hardened capabilities, Python workflow runtime, strict contracts.

**Sequencing (updated 2026-06-21):** **v0.4** = agent workflows (LangGraph/LangChain); **v0.5** = UI-as-primary. See **[ADR-0003](../CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md)** Amendment B and **[spec-v04-agentworkflows.md](../CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md)**.

```text
v0.3  Layer 2–3   Python pipelines + CLI + MCP + contract tests  (shipped)
v0.4  Layer 2     LangGraph/LangChain workflows + model-agnostic search
v0.5  Layer 4     Browser UI-primary — views SPA / CoPilotKit (TBD)
      Layer 3+    HTTP for UI; localhost → cloud
```

**Invoke order:** CLI first → MCP (agentic) → HTTP (browser UI).

**LLM gates:** LangGraph subgraphs with provider config (not hand-rolled per-provider calls).

**UI path:** Streamlit spike in v0.3 informs **v0.5** choice (extend v0.2 views vs CoPilotKit).

---

## Master artifact inventory

All skills, agents, workflows, and the capability audit framework:

**[`CONSTRUCT-CLAUDE-spec/artifact-catalog.md`](../CONSTRUCT-CLAUDE-spec/artifact-catalog.md)**

Use it to:

- inventory every capability and classify steps as `PYTHON` vs LLM tier (L1/L2/L3)
- decide v0.3 pipeline implementation order (`PIPE` skills first)
- map future v0.5 UI affordances to v0.4 workflow capabilities

---

## Related inputs

| Document | Role |
|----------|------|
| [`adr-0003-v03-pipeline-v04-ui.md`](../CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md) | **Architecture decision** — layers, v0.3/v0.4 split, LLM tiers |
| [`artifact-catalog.md`](../CONSTRUCT-CLAUDE-spec/artifact-catalog.md) | Master inventory + audit matrix |
| [`commands.md`](../CONSTRUCT-CLAUDE-impl/construct/references/commands.md) | Current user command quick-ref |
| [`capabilities.md`](../CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md) | User-facing capability handbook |
| [`user-journeys.md`](../CONSTRUCT-CLAUDE-spec/user-journeys.md) | J1–J3 — API in v0.3/v0.4; UI in v0.5 |
| [`spec-v04-agentworkflows.md`](../CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md) | v0.4 baseline — LangGraph workflow migration |
| [`tranche-1-mvp.md`](tranche-1-mvp.md) | Approved v0.3 tranche 1 scope (historical) |
| [`prd-v02-live-views.md`](../CONSTRUCT-CLAUDE-spec/prd-v02-live-views.md) | v0.2 views — foundation for v0.5 UI shell |

---

## Working rules

1. When planning conflicts with `artifact-catalog.md` skill names or counts, **update the catalog first**.
2. **Workspace SOT unchanged** — pipelines read/write the same files Claude uses today.
3. **SKILL.md + catalog = spec**; **Python = PIPE**; **LangGraph = L2/L3 gates**; skills/agents call **MCP or CLI**.
4. Do not build **v0.5** UI until v0.4 workflow capabilities have contract tests.
5. **Streamlit spike** (localhost) validates browser UI patterns before **v0.5** commitment.

---

## Next steps (planning)

1. Review each skill in the artifact catalog — tag steps: `PYTHON` | `LLM-L1` | `LLM-L2` | `LLM-L3` | `USER-REVIEW`.
2. Draft **v0.3 PRD**: capability registry, CLI, MCP server, LangGraph gate protocol, Streamlit spike scope.
3. Define **v0.3 tranche 1** — see **[`tranche-1-mvp.md`](tranche-1-mvp.md)** (approved).
4. Produce per-skill migration notes: spec steps → Python module → CLI + MCP tool → test fixture.

*v0.5 PRD (UI shell, action model) follows once v0.4 agent workflows are stable.*

---

## GSD (implementation tracking)

**v0.3 GSD complete** — see [`.planning/`](../.planning/). **Next:** v0.4 agent workflows per [`spec-v04-agentworkflows.md`](../CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md).

---

## v0.4 / v0.5 planning (forward)

- **v0.4:** Agent workflows — [`spec-v04-agentworkflows.md`](../CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md); GSD `/gsd-new-milestone`
- **v0.5:** UI-primary shell, capability buttons, LLM modals, HTTP API — after v0.4 workflows ship
