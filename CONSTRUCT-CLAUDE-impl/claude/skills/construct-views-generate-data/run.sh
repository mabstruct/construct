#!/usr/bin/env bash
# views-generate-data wrapper.
#
# Thin wrapper over the CONSTRUCT CLI. The generator implementation lives in the
# Python layer (`construct.views.generate`), reached here through
# `construct views generate` (Phase 15, D-09). There is no skill-local Python
# runtime and no skill-local dependency bootstrap: the accepted cost of D-09 is
# that this skill is no longer standalone and requires an installed CONSTRUCT.
#
# Usage: run.sh <install-root>

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <install-root>" >&2
  echo "  <install-root> is the directory containing AGENTS.md and .construct/." >&2
  exit 2
fi

if ! command -v construct >/dev/null 2>&1; then
  echo "Error: the 'construct' executable is not on PATH." >&2
  echo "This skill wraps the CONSTRUCT CLI and requires an installed CONSTRUCT." >&2
  echo "Install the CONSTRUCT package (an editable install from the repository" >&2
  echo "root), or activate the environment it is installed into, and re-run." >&2
  exit 127
fi

exec construct views generate --install-root "$1"
