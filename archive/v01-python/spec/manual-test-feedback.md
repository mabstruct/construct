# User Tests

## USERTEST 202606151700

USERTEST SCENARIO REPORT:

The user installed the workspace using ./setup-construct.sh into the directory /test-ws/semanticworld.

Workspace was scaffolded into named directory.

User started CLAUDE Code on the comand line.

User asked about the version of the instaled CONSTRUCT.

The answer within CLaude was: 
    This workspace is on CONSTRUCT 0.2.0 (per .construct/VERSION).

User expected the version v0.3 to be installed.

User asked for a comparison with current original code repo (which is on version v0.3).

Final answer from Claude Code was:
    The installed construct CLI resolves to /Users/mab/dev/mabstruct/construct/src/construct — so when skills shell out to
  the engine, they're hitting the v0.3 code with the capabilities registry, MCP server, and graph_status pipeline from your
  recent commits.

CLAUDE Code also mentions two possible gaps:
 1. MCP server not wired into the workspace. construct mcp exists in the CLI, but neither .claude/settings.json nor
  settings.local.json registers it as an MCP server — so agents in this workspace can't yet invoke the v0.3 engine as MCP
  tools. The capability ships in the code but isn't connected here.
  2. VERSION still reads 0.2.0 in both the impl source and the deployed copy. That's an un-bumped stamp — expected since
  v0.3 is mid-flight (you're on v03ph01-feature, phase 01) — but it means the version file won't tell you which version a
  workspace is on. (USER_GUIDE.md was also added to impl but isn't deployed per-workspace; minor, it's a doc not infra.)

  Bottom line: the workspace infrastructure and the engine it calls are the current v0.3-in-progress code, fully in sync
  with the impl source. The one functional gap if you want to exercise v0.3 specifically is the MCP server registration.




## USERTEST 202606151700

During a first triggered research cycle i got this after the web search tasks came back for ingestion:


A.
⏺The CLI expects the workspace path to be the domain directory itself (it looks for domains.yaml at the workspace root). I
  pointed -w . at the CONSTRUCT root, but the workspace is cosmology/. Let me correct that.


B.
The CLI ingest revealed a real problem. The construct ingest source command in v0.3.0 is not extracting content — it
  created a stub ref titled "Www.Desi.Lbl.Gov" (hostname, not the page title), with default relevance 0.5, source_tier 5,
  and empty findings/categories. And card creation is failing with a schema bug:

  Card validation failed: ... summary  Extra inputs are not permitted [type=extra_forbidden]

  So the CLI writes a thin ref and never produces a card. That defeats the purpose of the cycle. Let me inspect the card
  schema and validate tooling to confirm, before deciding how to proceed.


This was an analysis of Claude Code during Runtime (to be verified):
This is a genuine fork, and since you're the one building CONSTRUCT, it's your call rather than mine to assume.

  Here's the situation: the research itself worked great — I have rich, recent, well-sourced findings across all 5 clusters
  (DESI DR2 evolving dark energy at 4.2σ, the 2026 Hubble-tension status with sound-horizon-free H₀, the 2025 Cosmological
  Parameters review, the 2026 S₈-tension review, ACT's spectral-index tension with Planck, etc.). But the construct ingest
  source CLI that this skill is supposed to delegate to is broken in v0.3.0:

  - No extraction. It doesn't fetch the page — it sets the ref title to the hostname ("Www.Desi.Lbl.Gov"), relevance to a
  flat 0.5, source_tier to 5, and leaves findings/categories empty.
  - Card creation throws. Pydantic rejects the card with summary  Extra inputs are not permitted — so it produces zero seed
  cards.

  So the cycle can't be completed through the CLI as written. I can see two ways forward.

  Bug #2 — Card creation always fails (trivial fix, high impact)

  pipelines/ingestion.py:192 puts a "summary" key into card_data:
  card_data = { ..., "summary": f"Seed card from ingested {source_type}: {source_title}" }
  But _card_dict_to_markdown (services/knowledge.py:98-105) dumps the entire dict as YAML frontmatter and appends a fixed
  empty body. KnowledgeCard is extra="forbid" (schemas/card.py:93) and has no summary field → every ingest throws
  extra_forbidden. So no ingest has ever produced a card.
  - Fix: delete the "summary" line. One line. Cards then validate.
  - Caveat: the body template is hardcoded empty (knowledge.py:104), so even after the fix the ## Summary section stays
  blank — the summary text has nowhere to go. Populating it needs create_card/_card_dict_to_markdown to accept a body.
  That's a small enhancement, not required to unblock.

  Bug #1 — URL ingestion is a stub; no way to inject extracted metadata (design gap, larger)

  ingestion.py:99-139: the URL branch never fetches the page. It does:
  - title = hostname titlecased ("Www.Desi.Lbl.Gov") — and ref_id derives from the host, so every arxiv.org paper would
  collide into arxiv-org, arxiv-org-2…
  - relevance_score=0.5, source_tier=5, key_findings=[], content_categories=[], all hardcoded.

  The CLI also exposes no flags (--title, --relevance, --finding, --category, --tier, --year, --venue) to pass metadata in.
  So there's no path — automatic or agent-supplied — to get real metadata into a ref. Given CONSTRUCT's agent-driven
  design (extraction is my job; the CLI persists), the cleanest fix is (b): add optional metadata params so I pass the
  fields I already extracted from the web searches, rather than building a fetch+LLM-extract step into the CLI.

  My recommendation

  The research is done and high-quality — only the persistence layer is broken. I'd:
  1. Fix Bug #2 now (one line) — unblocks card creation.
  2. Fix Bug #1 via metadata flags — add optional --title/--relevance/--tier/--finding/--category/--year/--venue/--cluster
  to ingest source and derive ref_id from title, so the CLI faithfully records what I extract.
  3. Re-run the cycle through the fixed CLI — keeps the skill's delegation contract honest and seeds cosmology properly.
