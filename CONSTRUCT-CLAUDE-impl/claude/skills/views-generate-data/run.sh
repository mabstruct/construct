#!/usr/bin/env bash
# views-generate-data wrapper.
#
# Picks the right Python interpreter:
#   1. If system python3 has PyYAML → use it directly.
#   2. Otherwise, ensure a per-skill venv exists at .venv/ alongside this
#      script with PyYAML installed, and use that.
#
# This avoids the user fighting macOS PEP-668 "externally-managed-environment"
# errors when running `pip install pyyaml` against system Python.
#
# Usage: run.sh <install-root>

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <install-root>" >&2
  exit 2
fi

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="$1"

# 1. Fast path: system python3 has yaml
if python3 -c "import yaml" >/dev/null 2>&1; then
  exec python3 "$SKILL_DIR/generate.py" "$INSTALL_ROOT"
fi

# 2. Slow path: bootstrap a per-skill venv (one-time, ~5s)
VENV="$SKILL_DIR/.venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Bootstrapping skill venv at $VENV (one-time setup)..." >&2
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$SKILL_DIR/requirements.txt"
fi

# Sanity: venv should now have yaml
if ! "$VENV/bin/python" -c "import yaml" >/dev/null 2>&1; then
  echo "Error: skill venv at $VENV does not have PyYAML. Investigate." >&2
  echo "Try: rm -rf $VENV  and re-run." >&2
  exit 1
fi

exec "$VENV/bin/python" "$SKILL_DIR/generate.py" "$INSTALL_ROOT"
