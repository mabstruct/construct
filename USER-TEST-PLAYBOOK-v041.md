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

<!-- gsd:write-continue -->
