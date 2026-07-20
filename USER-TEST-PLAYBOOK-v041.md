# USER TEST PLAYBOOK — CONSTRUCT v0.4.1

**Purpose:** Release-validation smoke test for CONSTRUCT v0.4.1, from a real user's
perspective, in a fresh workspace, using the shipped `construct` CLI and MCP server.

**Scope:** Happy-path verification that each headline capability *works end-to-end and
persists correctly* — not exhaustive QA. Each step states the exact command, the expected
result, and a pass criterion.

**Organisation:** by **capability**, not by delivery phase. Earlier playbooks numbered their
sections after the milestone phase that shipped each feature; that encoded a delivery history
which stopped mapping to anything a user cares about, and it is why the document drifted.

- **Milestone reference:** `.planning/MILESTONES.md`
- **Est. time:** ~25–35 min (≈20 min if you skip the credentialed sections)

## How to read this document

**Offline by default.** Every section runs against a plain checkout with **no credentials**,
unless its heading explicitly ends with `— requires ANTHROPIC_API_KEY`. Those marked sections
are opt-in extras, never gates on the core run. A release validator with nothing but a clone
of this repository can execute the entire unmarked path.

**Verdicts come from `--json`, not from exit codes.** Several capabilities *degrade by design*
— they complete a run with some steps unavailable and report that fact in their payload while
still exiting `0`. `curation run` does this deliberately, and `daily run` isolates a failing
child and carries on. **Never treat "exit code 0" as the pass criterion for a run command.**
Read the `status` field instead: `completed`, `degraded`, `skipped`, or `failed`. A step that
asserted on the exit code would report a degraded run as a passing release validation, which
is the worst possible outcome for a build signal.

**Keep `stdout` and `stderr` apart.** Degradation notices are written to `stderr` while the
`--json` payload goes to `stdout`. Piping `2>&1` into a JSON parser will corrupt the payload.
Redirect them separately, as the steps below do.

---

## 0. Prerequisites & setup

### 0.1 Tooling

| Requirement | Why | Check |
|-------------|-----|-------|
| Python ≥ 3.11 | Runtime | `python --version` |
| `construct` installed | CLI under test | `construct --version` |
| `ANTHROPIC_API_KEY` | Needed **only** by the two sections whose headings say so | `echo ${ANTHROPIC_API_KEY:+set}` |
| Ollama (optional) | `lightweight` provider tier; not required by this playbook | — |

If `construct` is not on your PATH, use the project venv. Activate it **once, here** — every
later section assumes an activated environment and writes bare `construct ...` commands:

```bash
cd /Users/mab/dev/mabstruct/construct
source .venv/bin/activate
construct --version
```

**Expected:** A version string is printed and the command exits 0.

**Pass:** A version prints. Do **not** assert a specific value: the packaged version string
currently begins `0.3.` and lags the milestone name. That mismatch is a known-open packaging
observation, not a failure of this playbook — see *Known-open observations* at the end.

> **LLM configuration note:** the authority for provider and gate configuration is
> `src/construct/llm/config.yaml`, which defines the `anthropic` / `openai` / `ollama`
> providers and the per-gate routing.
> The per-workspace `.construct/model-routing.yaml` is **deprecated and inert** — still
> scaffolded and still named by `construct status`, but nothing reads it for routing. Do not
> edit it expecting an effect.

### 0.2 Create a fresh smoke workspace

Do **not** test against `test-ws/` — those are committed fixtures and a smoke run would
mutate them. Use a throwaway directory outside the repository.

```bash
export INSTALL_ROOT="$HOME/construct-smoke"
export WS="$INSTALL_ROOT/ai-gateways"
rm -rf "$INSTALL_ROOT"
mkdir -p "$INSTALL_ROOT"
```

> A workspace lives *inside* an install root. Most commands take the workspace
> (`-w "$WS"`); the `views` commands take the install root (`--install-root "$INSTALL_ROOT"`),
> because the views generator discovers workspaces by scanning the install root's children.

`init` prompts interactively. Pipe the suggested answers so the run is reproducible:

```bash
printf 'ai-gateways\nAI Gateways\nAPI gateways in the age of AI\nrouting, auth, observability\npapers, vendor-docs\nllm proxy, semantic caching\n' | construct init "$WS"
```

| Prompt | Answer |
|--------|--------|
| Domain slug | `ai-gateways` |
| Display name | `AI Gateways` |
| Scope/description | `API gateways in the age of AI` |
| Taxonomy seeds | `routing, auth, observability` |
| Source priorities | `papers, vendor-docs` |
| Research seeds | `llm proxy, semantic caching` |

**Expected:** `Initialized CONSTRUCT workspace at <path>`

**Pass:** Exit 0 and the workspace tree exists:

```bash
ls "$WS"
```

Expect exactly these entries: `cards`, `connections.json`, `digests`, `domains.yaml`,
`governance.yaml`, `log`, `publish`, `refs`, `search-seeds.json`, `WORKSPACE.md`.

> The domain id `ai-gateways` created here is referenced by every later step. Card ids are
> deterministic slugs derived from card titles, so the ids used below are reproducible and
> every command in this document can be copy-pasted verbatim.

### 0.3 Mark the install root

The `views` commands refuse to run against a directory that is not a CONSTRUCT installation,
so that an arbitrary path argument can never have a views tree scaffolded into it. The marker
is an `AGENTS.md` file at the install root:

```bash
printf '# CONSTRUCT smoke install root\n' > "$INSTALL_ROOT/AGENTS.md"
```

**Pass:** The file exists. Without it, the derived-data section fails with
`not a CONSTRUCT installation: missing AGENTS.md`.

---

## 1. Workspace contract & governance

**Capability:** Canonical workspace contract with pre-write validation, plus `validate` /
`status` introspection.

### 1.1 Validate a clean workspace

```bash
construct validate "$WS"
```

**Expected:** `Validation complete: 0 error(s), 0 warning(s)`

**Pass:** Exit 0, zero errors.

### 1.2 Inspect ownership categories

```bash
construct status "$WS"
```

**Expected:** Canonical / derived / support artifacts each marked `[present]` or `[missing]`.
`Support: inbox` reports `[missing]` in a fresh workspace, which is normal.

**Pass:** Every canonical artifact (`cards`, `refs`, `connections.json`, `domains.yaml`,
`governance.yaml`, `search-seeds.json`, `log/events.jsonl`) reports `present`.

> This listing names `.construct/model-routing.yaml`, which is **deprecated and inert** —
> scaffolded for backward compatibility only. See the note in §0.1.

### 1.3 Validation rejects corruption (negative test)

```bash
cp "$WS/domains.yaml" /tmp/domains.yaml.bak
echo 'not: [valid yaml' >> "$WS/domains.yaml"
construct validate "$WS"; echo "exit=$?"
```

**Expected:** At least one `ERROR ...` line; `exit=1`.

**Pass:** The gate refuses a corrupted canonical artifact. **Then restore:**

```bash
cp /tmp/domains.yaml.bak "$WS/domains.yaml"
construct validate "$WS"
```

**Pass:** Validation is clean again before you continue.

---

## 2. Governed knowledge operations

**Capability:** Card and connection CRUD behind validation gates, with event logging,
connection-preserving archive, and frontmatter-only enumeration.

### 2.1 Create two cards

Each command is a single line — do not wrap them:

```bash
construct knowledge card create -w "$WS" --title "Semantic caching cuts gateway latency" --type finding --domains ai-gateways --confidence 3 --source-tier 2 --summary "Caching embeddings at the gateway reduces repeat-LLM-call latency."
construct knowledge card create -w "$WS" --title "Token-based rate limiting" --type concept --domains ai-gateways --confidence 4 --source-tier 2 --summary "Rate limit on token budget rather than request count for LLM traffic."
```

**Expected:** A `✓ Card '<title>' created as <id>` line for each, yielding the ids
`semantic-caching-cuts-gateway-latency` and `token-based-rate-limiting`.

**Pass:** Both cards created with those exact slug ids.

> Valid `--type` values: `finding, claim, concept, method, paper, theme, gap, provocation,
> question, connection`. `--confidence` / `--source-tier` are 1–5.

### 2.2 Edit a card

```bash
construct knowledge card edit semantic-caching-cuts-gateway-latency -w "$WS" --confidence 4 --lifecycle growing
```

**Expected:** `✓ Card 'semantic-caching-cuts-gateway-latency' updated`

**Pass:** Exit 0 and the updated fields are reflected in §2.3's enumeration.

### 2.3 Enumerate cards (frontmatter only)

```bash
construct knowledge card list -w "$WS" --json
construct knowledge card list -w "$WS" --domain ai-gateways --json
```

**Expected:** A `success` / `message` / `errors` / `data` envelope whose `data` is a list of
card frontmatter objects. Each carries `id`, `title`, `epistemic_type`, `confidence`,
`source_tier`, `domains`, `content_categories`, `lifecycle`, `created`, `last_verified`,
`sources`, `connects_to`, `tags`, `author`, `promoted_from`, `supersedes`. The card edited in
§2.2 shows `"confidence": 4` and `"lifecycle": "growing"`. Dates render as ISO-8601 strings.

**Pass — two distinct assertions:**

1. **No object carries a `body` key.** Enumeration returns frontmatter and never card prose;
   this is a contract, not an optimisation. Check it mechanically:

```bash
construct knowledge card list -w "$WS" --json | python -c "import json,sys; d=json.load(sys.stdin); assert not [k for c in d['data'] for k in c if k=='body'], 'body leaked'; print('no body keys:', len(d['data']), 'cards')"
```

2. The `--domain ai-gateways` filter returns the domain's cards, and the filter is
   case-sensitive — `--domain AI-Gateways` returns none.

### 2.4 Add a typed connection

```bash
construct knowledge connection add semantic-caching-cuts-gateway-latency token-based-rate-limiting -w "$WS" --type supports --note "Caching complements token budgeting"
```

**Expected:** `✓ Connection added: semantic-caching-cuts-gateway-latency -> token-based-rate-limiting (supports)`

**Pass:** Exit 0.

> Valid `--type` values: `supports, contradicts, extends, parallels, requires, enables,
> challenges, inspires, gap-for`.

### 2.5 List connections

```bash
construct knowledge connection list -w "$WS"
construct knowledge connection list -w "$WS" --card semantic-caching-cuts-gateway-latency
```

**Expected:** `✓ Found 1 connection(s)` from both — the `supports` edge.

**Pass:** The edge is present, and the card filter returns only edges touching that card.

### 2.6 Archive preserves connections

```bash
construct knowledge card archive token-based-rate-limiting -w "$WS"
construct knowledge connection list -w "$WS"
construct knowledge connection list -w "$WS" --include-archived
```

**Expected:** Archive succeeds. The plain listing now reports `0 connection(s)`, because one
endpoint is archived; `--include-archived` still reports `1 connection(s)`.

**Pass:** The edge is **hidden, not destroyed** — archival never deletes graph structure. The
same distinction holds for `construct knowledge card list --include-archived`, which still
returns the archived card.

### 2.7 The event log captured the operations

```bash
ls "$WS/log/"
wc -l < "$WS/log/events.jsonl"
```

**Expected:** `events.jsonl` exists and has grown since §0 — init, two creates, an edit, a
connection add, and an archive are all recorded.

**Pass:** The log exists and is non-empty.

---

## 3. Capability registry, CLI & MCP spine

**Capability:** One shared capability registry behind **both** the CLI and a stdio MCP server,
so a command registered once appears on both surfaces with no hand-wiring.

### 3.1 MCP server handshake and tool surface

MCP requires a real `initialize` handshake before `tools/list` — a bare one-shot `tools/list`
pipe is rejected with `-32602 Invalid request parameters`. Send the full sequence:

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}' '{"jsonrpc":"2.0","method":"notifications/initialized"}' '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | construct mcp 2>/dev/null | python -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    if msg.get('id') == 2:
        names = sorted(t['name'] for t in msg['result']['tools'])
        print('tools:', len(names))
        print('construct_list_cards present:', 'construct_list_cards' in names)
"
```

**Expected:** A non-empty tool list auto-registered from the capability registry, and the
server exits when stdin closes.

**Pass — two assertions:**

1. The tool list is non-empty.
2. `construct_list_cards` is present. This is the point of the shared registry: the card
   enumeration exercised at §2.3 through the CLI reaches the MCP surface **for free**, from
   one registry record, rather than being hand-wired into the server.

> Real agent clients speak the full handshake themselves. To register the server with a
> client, use `command: construct, args: ["mcp"]`.

---

## 4. Ingestion

**Capability:** `construct ingest source` turns a file, URL, or note into a ref (plus a seed
card) with metadata, routed to a domain.

### 4.1 Ingest a local note

```bash
construct ingest source "Gateways increasingly embed LLM routing logic." -w "$WS" --domain ai-gateways --title "Gateway LLM routing note" --tier 3 --finding "Routing logic is moving into the gateway layer" --category trend
```

**Expected:** `✓ Source ingested: ref 'gateway-llm-routing-note' + seed card created`

**Pass:** A new file appears under `"$WS/refs/"`.

### 4.2 Ingest a file

```bash
echo "Notes on semantic caching benchmarks." > /tmp/smoke-source.txt
construct ingest source /tmp/smoke-source.txt -w "$WS" --domain ai-gateways --tier 2
```

**Expected:** `✓ Source ingested: ref 'smoke-source' + seed card created`

**Pass:** Both refs are present:

```bash
ls "$WS/refs/"
```

> `ingest source` also accepts a URL or a `research:<query>` form. The `research:` form invokes
> the live web-research pipeline and is out of scope for an offline smoke test.

---

## 5. Guided workflow operability

**Capability:** State-aware next-step suggestions, plus durable multi-step runs that persist a
checkpoint, pause for human review, and can be inspected and resumed by run id.

> **Successor note.** Earlier playbooks tested this area with the `workflow run` and
> `workflow resume` subcommands. Both were **removed** in the v0.4 line; the generic workflow
> runner was replaced by named, durable capability runs. The steps below exercise the real
> successors — curation run / inspect / review here, and the research run / review pair in §8.
> The `workflow status` query survives read-only and is checked at §5.2.

### 5.1 Workspace-aware suggestion

```bash
construct help --suggest -w "$WS"
```

**Expected:** A suggestion naming the `ai-gateways` domain, plus a workspace-health line.

**Pass:** The output is a concrete, workspace-grounded suggestion naming the real domain — not
a generic help dump.

> **Known-open observation, not a failure:** the health line's `total_cards` /
> `total_connections` counters report `0` even when the workspace holds cards, while the
> nested `graph_status.cards.total` in the `--json` payload reports the true count. The
> suggestion aggregation reads a different source from the graph summary. Assert only that a
> domain-grounded suggestion is produced; do not assert on those two counters.

### 5.2 Workflow status is read-only and honest

```bash
construct workflow status -w "$WS"
```

**Expected:** `✓ No active workflow`

**Pass:** The command reports the absence of an active workflow rather than erroring. This is
the surviving half of the old `workflow` group.

### 5.3 Curation run (durable, degrades by design)

```bash
construct curation run -w "$WS" --json > /tmp/curation.json 2>/tmp/curation.err
```

**Expected:** Exit `0`. `stdout` carries the JSON envelope; `stderr` carries a degradation
notice such as `promotion_review: provider outage — no promotion proposals enqueued`, because
the LLM-backed promotion gate has no credential offline.

Read the verdict from the payload, never from the exit code:

```bash
python -c "
import json
d = json.load(open('/tmp/curation.json'))['data']
print('run status:', d['status'])
print('run_id:', d['run_id'])
for s in d['steps']:
    print('  %-24s %s (required=%s)' % (s['step'], s['status'], s.get('required')))
"
```

**Expected:** Run `status` is `completed`. The six required steps — `integrity_check`,
`decay_scan`, `orphan_scan`, `promotion_review`, `connection_maintenance`, `compile_report` —
each report `completed`; the optional `views_refresh_hook` reports `skipped`.

**Pass:** `status` is `completed` (or `degraded`, with a `stderr` notice explaining which
required step was unavailable). **A `failed` run status is the failure signal.**

> **Why this step reads a status field.** A degraded curation run exits `0` **on purpose** —
> failure surfaces in the status output, the JSON payload, and the event log, never in the
> exit code. A step asserting "exit 0 = passed" would silently green-light a degraded run.
> The run-level status aggregates the steps: any *required* step that is `failed` or `skipped`
> makes the run `degraded`.

### 5.4 Inspect a run by id (durable checkpoint round-trip)

```bash
construct curation inspect -w "$WS" --run-id "$(python -c "import json;print(json.load(open('/tmp/curation.json'))['data']['run_id'])")" --json
```

**Expected:** The same run is retrieved from its persisted checkpoint, reporting `success:
true` and the same `status` and step list as §5.3.

**Pass:** The run is retrievable by id after the process that created it has exited — this is
what "durable" means, and it is the capability that replaced the old resume wiring.

### 5.5 Review a completed run is idempotent

```bash
construct curation review -w "$WS" --run-id "$(python -c "import json;print(json.load(open('/tmp/curation.json'))['data']['run_id'])")" --approve-all --json
```

**Expected:** Exit `0` with `"message": "Curation run already complete (no re-review)."` and
`status: completed`, `gate_queue: []`.

**Pass:** The review entry point recognises an already-complete run and declines to re-apply
it, rather than double-writing. When a run *does* pause, this same command consumes its gate
queue — see §8.2 for the paused-gate path.

---

## 6. Daily cycle

**Capability:** A non-blocking daily maintenance cycle that runs research, curation, and graph
health as **isolated children** — a failing child degrades the parent rather than aborting it.

This is the flagship v0.4 capability. It runs credential-free: offline, the research child
fails on provider authentication while the others complete, which is precisely the isolation
behaviour worth validating.

### 6.1 Daily run

```bash
construct daily run -w "$WS" --json > /tmp/daily.json 2>/tmp/daily.err
```

```bash
python -c "
import json
d = json.load(open('/tmp/daily.json'))['data']
print('parent status:', d['status'])
print('run_id:', d['run_id'])
for c in d.get('children') or []:
    print('  child %-16s %s' % (c.get('capability'), c.get('status')))
"
```

**Expected offline:** parent `status` is `degraded`, with children
`research.run -> failed`, `curation.run -> completed`, `graph.status -> completed`.
`stderr` explains the research failure as a provider authentication outage.

**Pass — and read this carefully:** the parent aggregate must be `degraded`, and the two
non-LLM children must be `completed`. **The process exits `0` here even though a child
failed.** That is the entire reason this section asserts on `status` and per-child state: an
exit-code assertion would report this degraded cycle as a clean pass. With
`ANTHROPIC_API_KEY` set, the research child reaches `completed` or `awaiting_review` and the
parent aggregates to `completed`.

### 6.2 Daily inspect

```bash
construct daily inspect -w "$WS" --run-id "$(python -c "import json;print(json.load(open('/tmp/daily.json'))['data']['run_id'])")" --json
```

**Expected:** The persisted daily receipt is returned with the same parent status and child
breakdown.

**Pass:** The cycle is retrievable by id. A missing receipt resolves to `status: failed` with
`No such daily run.` — so a `failed` here means the receipt did not persist.

---

## 7. Card evaluation

**Capability:** The L3 promotion gate that evaluates cards for lifecycle advancement.

This step stays in the core offline path deliberately: without a credential the capability
**degrades with structured reporting** rather than crashing, and that reporting is itself
worth validating.

### 7.1 Card evaluate degrades cleanly without a credential

```bash
construct card evaluate -w "$WS" --json > /tmp/evaluate.json 2>/dev/null
```

```bash
python -c "
import json
d = json.load(open('/tmp/evaluate.json'))
print('success:', d['success'])
print('message:', d['message'])
print('data:', d['data'])
"
```

**Expected offline:** `success: false` with
`"All card evaluations failed due to provider authentication or configuration error"` and
`data` carrying `{"degraded": true, "total_outage": true}`.

**Pass:** The outage is reported as **structured data** — `degraded` and `total_outage` flags
— rather than an unhandled traceback. With `ANTHROPIC_API_KEY` set, the command returns real
per-card evaluations and `total_outage` is absent or `false`.

---

## 8. Research

**Capability:** Provider-backed search, scoring, and a durable run that pauses at a human
review gate before anything is written to the workspace.

### 8.1 Search (offline)

```bash
construct research search -w "$WS" --query "semantic caching" --max-results 3
```

**Expected:** `✓ Search complete (N results)`

**Pass:** The search path returns a result set and exits 0 without a credential.

### 8.2 Durable run → human review → resume — requires `ANTHROPIC_API_KEY`

> **Skip this subsection if you have no key.** Scoring is an LLM gate: offline, `research run`
> reports `status: failed` with a total scoring outage on `stderr` and never reaches the review
> gate, so the pause/resume path cannot be exercised. That offline failure is expected and is
> not a defect.

```bash
construct research run -w "$WS" --json > /tmp/research.json 2>/tmp/research.err
```

```bash
python -c "
import json
d = json.load(open('/tmp/research.json'))['data']
print('status:', d['status'])
print('run_id:', d['run_id'])
print('gate queue size:', len(d.get('gate_queue') or []))
"
```

**Expected:** `status` is `awaiting_review` with a non-empty `gate_queue` — the run has
**paused and persisted** rather than writing findings straight into the workspace.

**Pass:** The run pauses at the gate. Nothing is written to `refs/` or `cards/` yet.

Then resume it through the review gate, supplying the run id from above:

```bash
construct research review -w "$WS" --run-id "<RUN_ID>" --approve-all --json
construct research inspect -w "$WS" --run-id "<RUN_ID>" --json
```

**Expected:** `review` consumes the queue, applies the approved ingest actions, and reports
`status: completed` with populated `refs_created` / `cards_created`. `inspect` then returns
the same completed run from its checkpoint.

**Pass:** The paused run resumes **from its persisted checkpoint** and completes without
re-running the steps that already succeeded. This durable pause/resume is the architecture
that replaced the removed generic workflow runner. Use `--reject-all` or a
`--decisions-file` instead of `--approve-all` to exercise per-finding decisions.

---

## 9. Grounded synthesis & graph reasoning — requires `ANTHROPIC_API_KEY`

**Capability:** Bounded, citation-backed Q&A over a domain's cards (`ask domain`) and
cross-domain bridge detection (`bridge detect`).

### 9.1 Grounded domain Q&A — requires `ANTHROPIC_API_KEY`

```bash
construct ask domain -w "$WS" --domain ai-gateways --question "How can a gateway reduce LLM latency and control cost?"
```

**Expected:** A synthesized answer that **cites the cards** created in §2, with a confidence
score; it hedges or declines when grounding is weak. Offline it exits 1 with
`✗ No answer could be generated from available cards.`

**Pass:** The answer references real card ids/titles (grounded, not invented) and includes
citations and a confidence score.

### 9.2 Bridge detection (runs offline)

```bash
construct bridge detect -w "$WS"
cat "$WS/log/bridge-candidates.json"
```

**Expected:** `✓ Bridge detection complete: 0 confirmed, 0 strong candidates` and
`log/bridge-candidates.json` is written.

**Pass:** The candidates file is written and is valid JSON. A single-domain smoke workspace
legitimately yields **0** cross-domain bridges — that is still a pass, because the deliverable
is the pipeline and its artifact, not a non-empty result. The L1/L2 layers run offline; the L3
enrichment layer needs `ANTHROPIC_API_KEY` and is skipped without one.

---

## 10. Derived data & views

**Capability:** A views generator that writes per-install-root view data, and a Pydantic
schema gate that validates it.

### 10.1 Generate views data

```bash
construct views generate --install-root "$INSTALL_ROOT" --json
```

**Expected:** `success: true` with a `build_id`, a non-zero `total_files_written`, an empty
`validation_errors` list, and possibly `warnings` naming cards that are missing optional
fields.

**Pass:** Files are written and `validation_errors` is empty. Warnings about seed cards
missing `lifecycle` are expected — ingested seed cards do not carry every field.

### 10.2 Validate view data contracts

```bash
construct views validate --install-root "$INSTALL_ROOT" --json
```

**Expected:** A `results` list with one entry per view file, each `pass` or `fail`, plus an
`all_passed` flag.

**Pass — read the caveat before recording a verdict.** `views validate` does **not** currently
accept every file `views generate` writes: a fresh install root typically shows several files
failing with Pydantic `extra_forbidden` errors on fields the generator emits (for example
`stats.json`, and the per-workspace `cards.json`, `connections.json`, `events.json`). This is
a **known-open contract question recorded by the previous milestone**, not a new defect — the
generator and the schema have drifted apart and reconciling them is tracked separately. A
validator hitting it should recognise it and move on.

What *is* a defect here: the command failing to run, returning malformed JSON, or reporting a
failure whose error text is something other than a schema mismatch on generator-written
fields. The schema gate itself must never pass malformed data.

### 10.3 Streamlit ops dashboard (manual / interactive)

```bash
streamlit run src/construct/ui/streamlit_app.py
```

Then in the browser sidebar set **Workspace path** to your `$WS` and check the three panels:

| Panel | Expected |
|-------|----------|
| Dashboard | Card / connection / domain counts and recent events for `$WS` |
| Capability Runner | Lists registry capabilities; can execute one via a generated form |
| Gate Review | Shows Q&A results and bridge candidates for review |

**Pass:** All three panels load, counts match what you created, and a capability run from the
Runner succeeds. **No source-of-truth writes from the UI** — it goes through the registry only.

---

## 11. Governed spikes & tag extraction

**Capability:** Isolated, governed external-tool spikes, plus hybrid tag extraction where
candidates are **never auto-accepted**.

### 11.1 List spikes

```bash
construct spike list
```

**Expected:** Registered spike types — `graphify` and `infranodus` — with descriptions.

**Pass:** Non-empty list.

> `construct spike run <tool-name>` copies the workspace to an isolated directory and invokes
> an external binary. Skip the run itself unless that binary is installed; `spike list` is
> sufficient for a smoke test.

### 11.2 Extract tag candidates

```bash
construct tag extract -w "$WS"
construct tag list -w "$WS" --status pending
```

**Expected:** Candidates extracted from `refs/` and written to `log/tag-candidates.json`;
`list` shows them as **pending**.

**Pass:** Candidates exist and every one is `pending` — nothing is auto-approved.

### 11.3 Approve a candidate (human-gated)

```bash
construct tag approve ai-gateways-gateway-llm-routing -w "$WS"
construct tag list -w "$WS" --status approved
```

**Expected:** `✓ Approved 1 tag candidate(s), added 1 search cluster(s).` and the approved
candidate appears with `status: approved`.

**Pass:** Only the explicitly named id moves to `approved` and reaches `search-seeds.json`;
every un-approved candidate stays `pending`. Approval is explicit and isolated.

---

## 12. Cross-cutting: machine-readable output

Every data command supports `--json` / `-j` for agent and UI consumption.

### 12.1 The JSON envelope is the verdict surface

```bash
construct knowledge connection list -w "$WS" --json
construct knowledge card list -w "$WS" --json
construct views validate --install-root "$INSTALL_ROOT" --json
```

**Pass:** Output is well-formed JSON suitable for programmatic use.

**The rule this playbook applies throughout:** for any command that can degrade — `curation
run`, `research run`, `daily run`, `card evaluate` — **the `--json` payload is the verdict and
the process exit code is not.** These commands exit `0` while reporting real degradation,
because degradation is an expected operating mode rather than a crash. Read `status`
(`completed` / `degraded` / `failed` / `awaiting_review`) or the explicit `degraded` flag.
Anything asserting on `$?` alone will report a degraded system as healthy.

Remember also that degradation notices go to `stderr` while the payload goes to `stdout`;
never pipe `2>&1` into a JSON parser.

---

## 13. Teardown

```bash
rm -rf "$INSTALL_ROOT" /tmp/smoke-source.txt /tmp/curation.json /tmp/curation.err /tmp/daily.json /tmp/daily.err /tmp/evaluate.json /tmp/research.json /tmp/research.err /tmp/domains.yaml.bak
```

---

## Results summary

Record outcomes as you go:

| § | Capability | Result | Notes |
|---|------------|--------|-------|
| 0 | Prerequisites, smoke workspace & install-root marker | ☐ pass / ☐ fail | |
| 1 | Workspace contract & governance | ☐ / ☐ | |
| 2 | Governed knowledge operations (CRUD, enumerate, archive, events) | ☐ / ☐ | |
| 3 | Capability registry, CLI & MCP spine | ☐ / ☐ | |
| 4 | Ingestion | ☐ / ☐ | |
| 5 | Guided workflow operability (curation run / inspect / review) | ☐ / ☐ | |
| 6 | Daily cycle | ☐ / ☐ | |
| 7 | Card evaluation | ☐ / ☐ | |
| 8.1 | Research search | ☐ / ☐ | |
| 8.2 | Research durable run → review → resume | ☐ / ☐ / ☐ skipped (no key) | |
| 9 | Grounded synthesis & graph reasoning | ☐ / ☐ / ☐ skipped (no key) | |
| 10 | Derived data & views | ☐ / ☐ | |
| 11 | Governed spikes & tag extraction | ☐ / ☐ | |
| 12 | Machine-readable output | ☐ / ☐ | |

## Known-open observations (not failures)

These are recorded so a validator recognises them instead of filing them as new defects:

1. **Packaged version string lags the milestone.** `construct --version` reports a `0.3.`
   prefix while this playbook validates v0.4.1.
2. **`help --suggest` health counters read `0`** for cards and connections even in a populated
   workspace, while the same payload's `graph_status` reports the true totals (§5.1).
3. **`views validate` rejects fields `views generate` writes** — a schema/generator drift
   carried over from the previous milestone (§10.2).
4. **Offline LLM gates report total outages.** `research run`, `card evaluate`, and the
   research child of `daily run` all degrade without `ANTHROPIC_API_KEY`. Each reports the
   outage as structured data; none crashes.
