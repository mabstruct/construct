# HOWTO: Verify Phase 19 — a real browser reaches the running server

This is the **one** Phase 19 deliverable no automated check covers, and it is the last open item in
the phase (`19-10-PLAN.md`, wave 5, `autonomous: false`). Everything else — all 9 executed plans —
is green: `1124 passed, 18 skipped`.

**Time:** ~15 minutes. No installs; everything below uses the existing `.venv`.
**Prerequisites:** any Chrome/Firefox/Safari on this machine, and a terminal.

---

## What you are actually testing

Every HTTP test in Phase 19 drives the FastAPI application object through a `TestClient`. That is
the right tool for the contract, and it is structurally blind to exactly two things:

1. **Whether a real socket is bound to loopback and reachable from a separate browser process.**
   Criterion 1 of the phase says "a user starts the server with one command and reaches every
   registry capability *from a browser*". A `TestClient` never opens a socket. A green suite with
   nobody having opened a browser is the shape of a self-report that contradicts the criterion it
   claims.
2. **Whether an operator can actually get the per-launch token into that browser.** The research
   raised this as an open question and it was resolved by preference (stdout + a `0600` file), not
   by measurement. Phase 21 owns token delivery for the served app and needs your verdict.

There is a third thing a test client cannot see, and it is the interesting one. `middleware.py`
states its own blind spot: *"a test client sends no `Origin` of its own"*. The design's CSRF story
(assumption **A3**) is that `X-Construct-Token` is **not** a CORS-safelisted header, so a
cross-origin page carrying it gets preflighted and blocked — and no `CORSMiddleware` is installed to
answer that preflight. **Only a real browser enforces CORS.** `curl` will happily send anything.
Step 6 is where A3 is genuinely tested for the first time.

---

## Step 0 — Deal with the server that is already running

**Read this before starting anything.** There is a `construct serve` process from **Aug 3** still
holding the default port:

```bash
lsof -i :8787 -n -P
# COMMAND   PID USER   FD   TYPE            DEVICE SIZE/OFF NODE NAME
# Python  57684  mab    6u  IPv4 0xa231411c94a8734      0t0  TCP 127.0.0.1:8787 (LISTEN)
```

It is two days stale and predates the wave-4 commits, so it is *not* running the code you want to
verify. Kill it:

```bash
kill 57684        # substitute the PID from your own lsof output
```

If you leave it and start a second server on another port, you hit a real gotcha — see the box under
Step 1.

Confirm the port is free:

```bash
lsof -i :8787 -n -P || echo "8787 free"
```

### Verified: the busy-port path works

Worth 10 seconds, because it is D-04's whole reason for existing. With the old server still running,
`serve` refuses **before** uvicorn is handed control, so you get guidance instead of a
`SystemExit(3)` and a stack trace:

```
ERROR: port 8787 on 127.0.0.1 is already in use. Retry with a different port, e.g.
`construct serve --port 8788`, or find the process holding it with `lsof -i :8787`.
```

That is the actual observed output. Exit code 1.

---

## Step 1 — Start the server

Run from the repo root. `test-ws` is used as the install root because it already holds real
workspaces; the repo root does not.

```bash
cd /Users/mab/dev/mabstruct/construct
.venv/bin/python -m construct.cli serve --install-root test-ws
```

**Expect exactly this shape** (your token will differ — it is minted per launch):

```
CONSTRUCT API listening on http://127.0.0.1:8788
Token: YdC1Tus7tySWEP7Esaz3yAs_UnymLbBc9FOsEPgQRwE
Token file: test-ws/.construct/api-token
INFO:     Started server process [4847]
INFO:     Uvicorn running on http://127.0.0.1:8788 (Press CTRL+C to quit)
```

✅ **Check the URL is `127.0.0.1`, not `0.0.0.0`.** That single character is the difference between a
local tool and an open server. The automated suite asserts the constant; this asserts the
deployment.

> ### ⚠️ Gotcha: two servers, one token file
>
> The token file path is `{install_root}/.construct/api-token` — it does **not** vary by port. So a
> second `construct serve --port 8788 --install-root test-ws` **overwrites the token file of the
> server already running on 8787**. The first server keeps working (it holds its token in memory),
> but the on-disk copy now authenticates against the *second* server only.
>
> This matters beyond this test: **Phase 21 reads that file.** A served app would authenticate
> against whichever server launched last, regardless of which one it is talking to. Worth recording
> as a Phase 21 input — it is not covered by any test.

Leave this terminal running. Open a second one for the rest.

## Step 2 — The token file is owner-only and matches

```bash
cd /Users/mab/dev/mabstruct/construct
ls -l test-ws/.construct/api-token
cat test-ws/.construct/api-token
```

**Expect:**

```
-rw-------@ 1 mab  staff  43 Aug  5 18:47 test-ws/.construct/api-token
```

✅ Mode is `-rw-------` (0600, owner read/write only). ✅ The contents match the `Token:` line from
Step 1 exactly.

The `chmod` happens *after* the write, deliberately — the file is created under the process umask,
so a permissive umask would leave it world-readable for the window in between. `-rw-r--r--` here is
a **fail**.

---

## Step 3 — Get a browser console onto the server's origin

**This is the part that is not obvious, and getting it wrong will make a working server look
broken.**

You cannot test this by typing the URL into the address bar: a browser navigation cannot carry the
`X-Construct-Token` header, so every navigation is a 401. And you cannot open the console on some
random page and fetch — that page is a **foreign origin**, and the request will be blocked (which is
Step 6's test, not this one).

The trick: **navigate to the server's own URL first.** You will get a 401 JSON body — that is
correct and expected — but the page now *has the server's origin*, so console fetches from it are
same-origin.

1. In your browser, open **<http://127.0.0.1:8788>** (use your port from Step 1).
2. You should see exactly:

   ```json
   {"detail":"missing or invalid token"}
   ```

   HTTP 401, `content-type: application/json`. **This is a pass, not a failure.** It proves the guard
   runs before anything else, on every path, including one that does not exist.

3. Open developer tools (`Cmd-Option-J` in Chrome, `Cmd-Option-K` in Firefox) → **Console**.
4. Paste your token in, once:

   ```js
   const T = "YdC1Tus7tySWEP7Esaz3yAs_UnymLbBc9FOsEPgQRwE";  // ← your token from Step 1
   const call = (p, body) => fetch(p, {
     method: body ? "POST" : "GET",
     headers: {"X-Construct-Token": T, "Content-Type": "application/json"},
     body: body ? JSON.stringify(body) : undefined,
   }).then(async r => ({status: r.status, body: await r.json()}));
   ```

> **How did that paste feel?** Note it now while it is fresh — Step 8 asks for the verdict, and the
> answer is genuinely the point of this checkpoint, not a formality.

## Step 4 — A real browser reaches every capability

```js
await call("/api/capabilities").then(r => r.body.capabilities.length)
```

**Expect `30`.**

The number is the test. A membership check would pass on a 23-capability surface — that is the
WR-01 failure mode this phase was built around, and it is why the discovery endpoint iterates
`registry.list()` rather than the MCP projection (which drops the 6 capabilities whose
`mcp_tool_name` is `None`). Confirm it against the registry itself in your terminal:

```bash
.venv/bin/python -c "
from construct.capabilities.catalog import get_registry
print(len(get_registry().list()))"
```

Both must say **30**. If discovery says 23 or 24, that is a real failure.

Check a schema is actually published — this is the half of GOV-01 that Phase 18's D-21 had to
concede upstream, recovered here:

```js
await call("/api/capabilities").then(r =>
  Object.keys(r.body.capabilities.find(c => c.id === "workspace.status").input_schema.properties))
```

**Expect** a non-empty property list. An empty or missing `input_schema` is a fail — Phase 21 builds
its forms from these.

## Step 5 — Invoke a capability, then have it refused

Now with the token:

```js
await call("/api/capabilities/workspace.status", {payload: {workspace_id: "my-construct"}})
```

**Expect** `status: 200` and a body whose `items` list every canonical/derived path with an `exists`
flag. Known workspace ids under `test-ws` are `my-construct`, `ping-eon`, `smoke202606201640`.

Now without the token — same request, header dropped:

```js
await fetch("/api/capabilities/workspace.status", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({payload: {workspace_id: "my-construct"}}),
}).then(async r => ({status: r.status, body: await r.json()}))
```

**Expect** `status: 401`, `{"detail": "missing or invalid token"}` — **refused, not answered**. The
capability must not have run.

## Step 6 — The cross-origin refusal (assumption A3 — browser-only)

**This step cannot be done with `curl` and is the single most valuable thing in this document.**
`curl` does not implement CORS; only a browser does.

1. Open a **new tab** on any ordinary website — `https://example.com` is fine.
2. Open its console and run (substituting your port and token):

   ```js
   fetch("http://127.0.0.1:8788/api/capabilities", {
     headers: {"X-Construct-Token": "YdC1Tus7...your token..."}
   }).then(r => r.json()).then(console.log).catch(e => console.log("BLOCKED:", e.message))
   ```

**Expect the request to be BLOCKED by the browser**, with a CORS error in the console along the
lines of *"has been blocked by CORS policy: Response to preflight request doesn't pass access
control check"* — and, critically, **no successful response body**.

✅ **Pass:** the fetch fails. The browser preflighted it (because `X-Construct-Token` is not
CORS-safelisted), no `CORSMiddleware` answered, so the real request was never sent. This is the
drive-by CSRF threat (T-19-02) refused as deployed.

❌ **Fail:** you get a capability list back. That would mean a CORS middleware crept into the stack —
the one edit to this surface that looks like a convenience and is a vulnerability.

Also check the **Network** tab: the preflight `OPTIONS` should show no
`access-control-allow-origin` response header.

## Step 7 — The refusals that need no browser (optional, ~1 min)

These are already covered by the automated suite; run them only if you want to see the trust boundary
answer with your own eyes. From a terminal, with the server still running:

```bash
cd /Users/mab/dev/mabstruct/construct
T=$(cat test-ws/.construct/api-token)
B=http://127.0.0.1:8788

# Traversal in the workspace id — shape gate, before any filesystem contact
curl -s -X POST -H "X-Construct-Token: $T" -H "Content-Type: application/json" \
  -d '{"payload":{"workspace_id":"../../etc"}}' $B/api/capabilities/workspace.status

# A path-shaped key at all
curl -s -X POST -H "X-Construct-Token: $T" -H "Content-Type: application/json" \
  -d '{"payload":{"workspace_path":"/etc"}}' $B/api/capabilities/workspace.status

# A foreign Host (DNS-rebinding shape) — a browser cannot forge this, curl can
curl -s -H "X-Construct-Token: $T" -H "Host: evil.example" $B/api/capabilities
```

**Verified actual output:**

```
422  {"detail":"Invalid input for capability 'workspace.status': workspace_id must be kebab-case
      ([a-z0-9] segments joined by single hyphens), e.g. 'my-construct' not '../../etc'"}

422  {"detail":"path-shaped payload keys are refused at the HTTP boundary: workspace_path —
      address a workspace by id with 'workspace_id' instead"}

400  {"detail":"invalid host"}
```

Note what the reasons do **not** contain: no stack trace, no absolute path, and no echo of the
rejected `Host` value back into the body.

## Step 8 — Record the token-delivery verdict

This is a UX judgement and the answer is the deliverable. Phase 21 has to decide whether stdout plus
a `0600` file is enough for the served app, or whether it needs something else (a server-rendered
`index.html` carrying the token was deliberately declined in Phase 19 — it would have pulled Phase
21's static serving forward).

Answer these in a sentence each:

- How many steps did it take to get the token from your terminal into the browser console?
- Did you ever feel tempted to put the token in the URL? (If yes, that is important — a query-string
  token lands in shell history, access logs, and the `Referer` sent to any third party.)
- Did the token end up anywhere durable you did not intend — shell history, a scratch file, a
  password manager, a Slack message to yourself?
- With `--port 8788` in play, was it clear *which* server the token file belonged to?

Then check your own shell history for a leak:

```bash
history | grep -c "X-Construct-Token"   # the curl lines from Step 7 will show; that is expected
history | grep "8788.*token="           # expect NO matches — a token in a URL would be the failure
```

---

## Pass / fail summary

| # | Check | Pass |
|---|---|---|
| 1 | Printed URL is loopback | `http://127.0.0.1:PORT`, never `0.0.0.0` |
| 2 | Token file mode | `-rw-------`, contents match stdout |
| 3 | Browser navigation to the server | 401 JSON — the guard runs before everything |
| 4 | Discovery from a real browser | **30** capabilities, with `input_schema` populated |
| 5 | Capability call with token | 200, real result body |
| 6 | Same call without token | 401, refused before the capability runs |
| 7 | Cross-origin fetch with token | **Blocked by the browser** — no body returned |
| 8 | Token-delivery verdict | Written down for Phase 21 |

**Not a failure:**

- The 401 JSON page when you navigate to the server — that is Step 3 working.
- `workflow.list` returning `{"runs": []}` — `test-ws/my-construct` has no runs; the capability ran
  fine and reported honestly.
- A capability returning `success: false` with a 200 status. D-24: *the command ran* and *how it
  went* are different questions, and mapping a reported failure onto a 4xx would re-fork the
  contract the CLI's exit code already encodes.

---

## ⚠️ One finding from the dry run — read before you sign off

While verifying the commands in this document I hit a genuine defect that no test catches.

**`help.suggest` returns an absolute filesystem path in its success body.**

```js
await call("/api/capabilities/help.suggest", {payload: {workspace_id: "my-construct"}})
```

returns, inside `data`:

```json
"workspace": "/Users/mab/dev/mabstruct/construct/test-ws/my-construct"
```

Source: `src/construct/services/help.py:188` — `"workspace": str(root)`.

This is **exactly** the T-18-32 success-path leak shape that plan 19-03 fixed for `graph.status` and
`bridge.detect` — a path written into a result that never raised, which the exception sanitizer
structurally cannot see. It is a third instance that was missed.

It is uncaught because the two success-path assertions in
`tests/contract/test_result_boundary.py` name those two capabilities individually
(`test_a_successful_graph_status_body_carries_no_absolute_path`,
`test_a_successful_bridge_detect_body_carries_no_absolute_path`). There is no sweep over the success
bodies of all 30.

Against criterion 3 — *"no raw exception text or filesystem paths in the body"* — this is a
violation. I have **not** fixed it; it is your call whether it blocks the phase, gets a follow-up
plan, or lands in `deferred-items.md`. The structural fix (a generic success-body sweep, rather than
a third named test) is the one that would have caught it.
