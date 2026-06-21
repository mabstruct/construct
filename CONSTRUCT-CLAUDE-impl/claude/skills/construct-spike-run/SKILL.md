---
description: "Safely run external graph-analysis tools on isolated workspace copies. Supports Graphify-style and InfraNodus-style spikes. Use when user says 'spike graphify', 'run infranodus', 'tag analysis spike', or similar."
allowed-tools: Read, Write, Grep, Glob, Bash(construct spike *)
---

# Skill: Spike Run

**Trigger:** User wants to evaluate an external graph-analysis tool without risking canonical workspace data.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** `log/spike-results/{tool}-{timestamp}.json` with captured outputs.

---

## Prerequisites

The CONSTRUCT CLI must be available on `$PATH`:

```bash
construct --help
```

If the CLI is not installed, run `pip install -e .` from the CONSTRUCT project root.

---

## Procedure

### Step 0: Verify the Tool is Installed

Before running a spike, confirm the external tool is available:

```bash
which <tool-name>
```

If not installed, install it per the tool's documentation. For Graphify-style spikes, you need a tool that accepts a workspace path and outputs candidate/tags files. For InfraNodus-style spikes, you need a tool that accepts `--input <connections.json>` and produces a report.

### Step 1: List Available Spike Types

```
construct spike list
```

This shows all registered spike definitions with descriptions:

```
Available spike types:
  graphify: Graphify-style ingestion analysis — extract candidate tags and keywords from refs
  infranodus: InfraNodus-style graph exploration — analyze graph structure for insight patterns
```

### Step 2: Run the Spike

```
construct spike run <tool-name> --workspace <path> [--tool-path <path>] [--timeout <seconds>]
```

Examples:

```bash
# Run Graphify-style spike against the test workspace
construct spike run graphify --workspace test-ws/my-construct

# Run InfraNodus-style spike with explicit tool path
construct spike run infranodus --workspace test-ws/my-construct --tool-path /opt/infranodus/bin/analyze

# Run with extended timeout for large workspaces
construct spike run graphify --workspace test-ws/my-construct --timeout 600
```

**What happens under the hood:**

1. The spike runner validates the tool name against known spike definitions
2. A temporary copy of the workspace is created at a system temp directory
3. Only canonical files are copied (`cards/`, `refs/`, `connections.json`, `domains.yaml`); large derived directories (`views/build/`, `digests/`) are skipped
4. The external tool runs against the temp copy only — canonical data is never at risk
5. stdout, stderr, and expected output files are captured
6. Results are written to `log/spike-results/{tool}-{timestamp}.json`
7. The temp directory is cleaned up (even on failure)

### Step 3: Review Results

Results are at `log/spike-results/{tool}-{timestamp}.json`. The file contains:

```json
{
  "success": true,
  "tool_name": "graphify",
  "duration_seconds": 12.45,
  "outputs": {
    "candidates.json": "{ ... }",
    "tags.json": "{ ... }"
  },
  "stdout": "...",
  "stderr": "...",
  "error": null
}
```

To view results directly:

```bash
cat log/spike-results/graphify-*.json | python3 -m json.tool
```

### Step 4: Interpret Findings

Evaluate the spike output against the evaluation criteria for each spike type (see below). Document findings as cards, connections, or notes in the workspace — or defer as design input for future phases.

---

## Spike Types

### Graphify: Tag/Keyword Extraction Analysis (SPK-02)

**Purpose:** Evaluate whether Graphify-style ingestion analysis produces useful candidate tags and keywords from ref source material. This spike type exercises the exfiltration path: ref files → tags → candidates.

**How to run:**

1. `construct spike run graphify --workspace <path>`
2. Read output candidates from the captured `candidates.json` and `tags.json`
3. Compare against existing `search-seeds.json` vocabulary
4. Assess whether candidates are novel, relevant, and worth curating

**What to evaluate:**

| Factor | Question |
|--------|----------|
| **Precision** | What fraction of extracted tags are genuinely useful? |
| **Recall** | Are there obvious tags the tool missed? |
| **Novelty** | Do extracted tags overlap with existing search-seeds, or reveal new patterns? |
| **Signal-to-noise** | How much noise (irrelevant tags) does the tool produce? |

**Interpreting results:**

| Finding | Implication |
|---------|-------------|
| Strong, novel candidates | Route through tag pipeline for curation (Phase 6 tag-extraction pipeline) |
| Marginal or noisy results | Document as tuning opportunity — may need prompt/parameter adjustment |
| No useful output | Tool may not fit the ref structure; consider alternative tools or approaches |
| Output overlaps fully with existing seeds | Tool is redundant with current vocabulary; lower priority |

**Output:** This spike informs SPK-02/SPK-03 decisions about tag pipeline design. It does NOT modify the workspace.

### InfraNodus: Graph Exploration Analysis (SPK-04)

**Purpose:** Evaluate whether InfraNodus-style graph-guided exploration reveals insight patterns that could inform future UI and workflow design.

**Per D-09:** This is evaluated **via the spike framework only** — it is NOT built as a permanent feature in Phase 6. All findings feed into design input for v0.5 UI patterns.

**How to run:**

1. `construct spike run infranodus --workspace <path> --tool-path <path-to-infranodus>`
2. Read the graph structure report from the captured `report.json`
3. Identify structural patterns: clusters, bottlenecks, bridging nodes
4. Cross-reference with existing bridge detection pipeline results

**What to evaluate:**

| Factor | Question |
|--------|----------|
| **Structural insight** | Which graph metrics are most useful for insight discovery? |
| **UI applicability** | What UI patterns could expose these insights to the user? |
| **Bridge alignment** | How does this tool's findings compare with the existing L1/L2/L3 bridge pipeline? |
| **Novelty** | Does the tool reveal patterns the current system doesn't already surface? |

**Interpreting results:**

| Finding | Implication |
|---------|-------------|
| Useful structural patterns | Document as UI spec input for v0.5 — consider graph metrics dashboard |
| Redundant with bridge pipeline | Note as lower priority; current pipeline already covers this |
| Requires heavy external tooling | Document as deferred — may not justify integration cost |
| Reveals blind spots | Flag as high-value finding for v0.5 graph exploration design |

**Output:** Design input for v0.5 UI patterns and graph exploration workflows. No workspace modifications are made.

---

## Failure-mode Reference

| Trigger | Detection | User message |
|---------|-----------|-------------|
| Unknown spike tool | `construct spike list` shows available | `Unknown spike tool: '{name}'. Available: ...` |
| Tool not in PATH | `which <tool>` returns empty | `Tool '{name}' not found in PATH. Install it or pass --tool-path.` |
| Workspace not found | `--workspace` path doesn't exist | `Workspace not found: {path}` |
| Spike timed out | Tool exceeds --timeout (default 300s) | `Spike timed out after {timeout}s` |
| Tool fails | Non-zero exit code | `Tool exited with code {N}` with captured stderr |

In all failure cases, the temp workspace is cleaned up and no canonical data is affected.

---

## Validation

- [ ] External tool is installed and in PATH (or --tool-path is provided)
- [ ] `construct spike list` shows available spike types
- [ ] `construct spike run` completes against the target workspace
- [ ] Results file exists at `log/spike-results/{tool}-{timestamp}.json`
- [ ] Results contain `success`, `tool_name`, `outputs`, `stdout`, `stderr`
- [ ] Canonical workspace is unmodified after spike run (verify file contents)
- [ ] Temp workspace was cleaned up (check system temp for construct-spike-* dirs)
- [ ] Evaluation criteria applied per spike type and findings documented
