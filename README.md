# CONSTRUCT

Local-first, agent-powered personal knowledge system.

Current repo status: Phase 1 foundation is in progress. Right now the working CLI supports:

- `construct init <path>`
- `construct validate <path>`
- `construct status <path>`

## Requirements

- Python 3.11+

## Install

Create a virtual environment and install the package in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

If `python3` is not available, use your local Python 3.11+ executable instead.

## Quick Start

Initialize a new workspace:

```bash
construct init ~/my-construct-workspace
```

The CLI will prompt for the essential domain inputs:

- Domain slug
- Display name
- Scope/description
- Taxonomy seeds
- Source priorities
- Research seeds

Notes:

- taxonomy seeds become canonical `content_categories`, so they must be kebab-case
- the CLI now normalizes the domain slug to kebab-case automatically
- the CLI now normalizes spaces and punctuation for taxonomy seeds automatically
- example: `quantum gravity, string theory` becomes `quantum-gravity, string-theory`

Example session:

```text
$ construct init ~/my-construct-workspace
Domain slug (spaces will be normalized to kebab-case): climate policy
Display name: Climate Policy
Scope/description: Research on climate adaptation policy and implementation
Taxonomy seeds (comma-separated; spaces will be normalized to kebab-case): adaptation finance, loss and damage, national plans
Source priorities (comma-separated): peer-reviewed papers, policy briefs, institutional reports
Research seeds (comma-separated): climate adaptation policy, adaptation finance
Initialized CONSTRUCT workspace at /Users/you/my-construct-workspace
```

## What Gets Created

`construct init` currently creates the full workspace scaffold up front.

Canonical paths:

- `cards/`
- `domains.yaml`
- `domains/<domain-slug>/domain.yaml`
- `connections.json`
- `governance.yaml`
- `model-routing.yaml`
- `refs/`
- `workflows/`
- `log/events.jsonl`

Support paths:

- `inbox/`
- `digests/`
- `publish/`

Derived paths:

- `db/`
- `views/`

## Validate a Workspace

Run:

```bash
construct validate ~/my-construct-workspace
```

Behavior:

- hard structural problems are reported as `ERROR`
- softer issues are reported as `WARNING`
- the command exits non-zero only when errors are present

## Inspect Workspace Status

Run:

```bash
construct status ~/my-construct-workspace
```

This prints whether each known path is:

- `Canonical`
- `Support`
- `Derived`

and whether it is present or missing.

## Development

Run tests:

```bash
pytest -q
```

Targeted examples:

```bash
pytest tests/unit -q
pytest tests/integration/test_init_cli.py -q
```

## Notes

- `db/` and `views/` are rebuildable and non-canonical.
- Domain data currently uses per-domain folders plus a root `domains.yaml` registry.
- This README describes the code that exists now, not the full long-term product vision.
