# HOWTO: Verify Phase 18 — `ActivityList.jsx` renders live Python-emitted events

This is the **one** Phase 18 deliverable no automated check covers. Everything else in the phase —
including all five code-review blockers and the two-layer GOV-05 fix — was verified by live
reproduction against running code. This one could not be: there is no JS toolchain in the agent
environment and `T-18-SC` forbids installing one, so `ActivityList.jsx` was verified by source
review only and marked `human_judgment: true`.

**Time:** ~10 minutes, most of it `npm install`.
**Prerequisites:** Node ≥ 20 and npm. (Verified present on this machine: node v26.4.0, npm 11.17.0.)

---

## What you are actually testing

Plan 18-05 conformed the SPA's activity reader to D-17's canonical event shape.

Before the fix, `ActivityList.jsx` read five keys **no emitter in CONSTRUCT has ever produced** — a
legacy timestamp key, an actor key, a kind key, a nested what-was-acted-on object, and a skill key.
The nested object existed in no emitter at all. So every Python-emitted event rendered with a blank
agent and a blank action. That was a live defect *before* the contract work, not a regression from
it.

The component now destructures `ts` / `agent` / `action` / `target` / `detail` / `result`, which is
exactly what `views/lib/parse_events.py` canonicalises every log line into. Source review confirmed
the match. **This test confirms it at runtime.**

`result` is rendered, not merely read — an escalated action wrote nothing by design, and an activity
list that draws it identically to an applied change is the audit-trail-that-lies defect wearing a
browser. So the badge is part of the test, not decoration.

---

## Why you cannot just point this at `test-ws/my-construct`

Two traps, both of which will make a **working** component look broken. Both were hit while
preparing this guide.

### Trap 1 — `my-construct` is the wrong shape and produces no `events.json` at all

`views generate` expects an install root (marked by `AGENTS.md`) containing **workspace
subdirectories**. In `test-ws/my-construct`, the workspace *is* the root — `cards/`, `log/` and
friends sit directly under it. The generator finds zero workspaces and writes only install-root-level
files:

```
$ construct views generate --install-root <copy-of-my-construct>
Views data generation: build bce3f7fd, 5 files written, 0 validation errors, 0 content warnings

$ ls views/build/data
bridges.json  domains.json  articles.json  _build_meta.json  stats.json      # no events.json
```

No `events.json` → the dashboard has nothing to render. That is a fixture-shape problem, not a
component defect.

### Trap 2 — the correctly-shaped fixture has a legacy log that D-17 deliberately drops

`tests/fixtures/v02/single-domain-small` *is* a proper install root (`AGENTS.md` + a `cosmology/`
workspace). But its `cosmology/log/events.jsonl` is 30 lines of the **legacy** shape
(`event` / `timestamp` / `details`). D-17 refuses to fabricate the missing `agent` and `result`, so
all 30 lines are dropped with a warning naming file and line.

**Blank output from that fixture is correct behaviour**, and would be the single easiest way to
mis-report this test as a failure.

The recipe below combines the two: the *structure* of `single-domain-small` with a *canonical* log.

---

## Step 1 — Build the fixture

Run from the repo root. Everything happens in `/tmp`; your repo is not touched.

```bash
cd /Users/mab/dev/mabstruct/construct
export UAT=/tmp/uat-phase18
rm -rf "$UAT" && mkdir -p "$UAT"

# Structure: a real install root with a real workspace subdirectory.
cp -a tests/fixtures/v02/single-domain-small/. "$UAT/"

# Content: swap the legacy-shape log for a canonical one.
cp test-ws/my-construct/log/events.jsonl "$UAT/cosmology/log/events.jsonl"
```

Now append two events that exercise the badge paths. **The enums are strict** — `agent` must be one
of `construct | curator | researcher | human` and `result` one of `success | failure | escalated`.
Anything else is dropped with `cannot derive canonical event field(s)`, which is the reader
correctly refusing to guess:

```bash
cat >> "$UAT/cosmology/log/events.jsonl" <<'EOF'
{"ts": "2026-07-30T09:00:00Z", "agent": "curator", "action": "connection_review", "target": "card-hubble-tension", "detail": "Bridge to card-desi-bao-results needs a human call", "result": "escalated"}
{"ts": "2026-07-30T09:05:00Z", "agent": "researcher", "action": "ref_ingest", "target": "ref-riess-hubble-2024", "detail": "Fetch failed after 3 retries", "result": "failure"}
EOF
```

## Step 2 — Generate and validate the projection

```bash
.venv/bin/construct views generate --install-root "$UAT"
```

**Expect exactly this — `0 content warnings` is the signal that nothing was dropped:**

```
Views data generation: build 9de00480, 11 files written, 0 validation errors, 0 content warnings
```

> If you see `! warning (advisory): ... dropped: cannot derive canonical event field(s): agent`,
> a heredoc line has an `agent` or `result` value outside the enums above. Fix it before continuing —
> a dropped line will not appear in the UI and you would be testing the wrong thing.

Confirm the round-trip that criterion 1 is about — the validator accepting what the generator wrote:

```bash
.venv/bin/construct views validate --install-root "$UAT"
```

Every line should be `✓`, including `✓ cosmology/events.json`.

Sanity-check the data the component will receive:

```bash
.venv/bin/python -c "
import json; d=json.load(open('$UAT/views/build/data/cosmology/events.json'))
ev=d['data']['events']
print(len(ev),'events; results:', sorted({e['result'] for e in ev}))
"
```

**Expect:** `13 events; results: ['escalated', 'failure', 'success']`

## Step 3 — Build the SPA

The scaffold template is not pre-installed; copy it into the install root's `views/src/`:

```bash
mkdir -p "$UAT/views/src"
cp -a CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/. "$UAT/views/src/"

# The template ships a placeholder version; npm rejects it.
sed -i '' 's/{{VERSION}}/0.5.0-dev/' "$UAT/views/src/package.json"

cd "$UAT/views/src"
npm install          # a few minutes on first run
npm run build        # vite writes to ../build, alongside the data/ dir from Step 2
```

`vite.config.js` sets `outDir: '../build'` with `emptyOutDir: false` — that second flag is why the
build does **not** wipe the `data/` directory the generator just wrote. If you ever see an empty
dashboard with a 404 on `/data/...`, that flag is the first thing to check.

## Step 4 — Serve and open

```bash
npm run serve        # serves ../build on http://localhost:3000
```

Open **<http://localhost:3000/cosmology>** — the route is `/:workspace`, so the workspace id is the
path segment. Landing on `/` gives you the workspace list instead of the dashboard.

---

## Step 5 — What to look for

The activity list is on the workspace dashboard, showing the **10 most recent** events
(`WorkspaceDashboard.jsx:106` slices to 10). The two events you appended are the newest, so they sort
to the top.

Each row is `<time> <agent> <action> <target — detail> [badge]`.

### ✅ Pass looks like

| Column | Expectation |
|---|---|
| **time** | A relative time (`3d ago`) or an ISO date — never blank |
| **agent** | `curator`, `researcher`, `construct` — **never `—` and never blank** |
| **action** | `connection review`, `ref ingest`, `create card` — underscores rendered as spaces |
| **target — detail** | The card/ref id, an em-dash, then the free-text detail |
| **badge** | An **amber `ESCALATED`** badge on the top row, a **rose `FAILURE`** badge on the second |

Rows with `result: success` correctly show **no badge** — success is the overwhelming majority and
needs no decoration. Absence of a badge on those rows is right, not a missing feature.

### ❌ Fail looks like

- **Agent column shows `—` or is blank on every row.** This is the exact pre-fix defect: the reader
  is looking for keys the Python emitter never writes.
- **Action column blank** while time and target populate — a partial key mismatch.
- **No amber badge on the escalated row.** An escalated action wrote nothing; drawing it identically
  to an applied change is the defect this rendering exists to prevent.
- **"No recent activity."** with 13 events in `events.json` — the component received an empty array.

### Not a failure

- Only 10 of 13 events shown — `slice(0, 10)` is by design.
- No badge on `success` rows — by design.
- Cosmetic spacing/colour differences — out of scope for this test.

---

## Step 6 — Report the result

Back in the Claude session:

- **Passes** → type `pass`. Phase 18 is marked complete and the roadmap advances.
- **Doesn't** → describe what you saw in plain language ("agent column is empty on every row"). No
  severity rating needed — it is inferred, then diagnosed by a debug agent, turned into a verified
  fix plan, and executed via `/gsd-execute-phase 18 --gaps-only`.

Cleanup when done:

```bash
rm -rf /tmp/uat-phase18
```

---

## Appendix — if you would rather not build the SPA

The component is 90 lines of pure rendering with no state or effects. If a full toolchain run is not
worth it, the honest fallback is to confirm the **contract** the component depends on, and record
that the runtime check was skipped rather than passed:

```bash
# The keys the component destructures, straight from the generated file:
.venv/bin/python -c "
import json; d=json.load(open('$UAT/views/build/data/cosmology/events.json'))
print(sorted(d['data']['events'][0].keys()))
"
# Expect: ['action', 'agent', 'detail', 'result', 'target', 'ts']

grep -o "e\.\(ts\|agent\|action\|target\|detail\|result\)" \
  CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/src/components/ActivityList.jsx \
  | sort -u
```

If those two sets match, the defect class is closed at the data level. **This is what was already
done during the phase** — it is why the item is `human_judgment: true` rather than verified. Repeating
it adds no new evidence, so if you take this path, reply `skip` rather than `pass`, and the phase
stays honest about what was and was not observed.

---

*Phase 18: Contract & Governance Foundations — 8/8 plans, 5/5 success criteria verified,
774 passed / 18 skipped / 0 failed. This is the last open item.*
