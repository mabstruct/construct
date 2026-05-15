#!/usr/bin/env bash
# debounced per-card views hook wrapper.
#
# Usage: debounced-hook.sh <install-root> [source]

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <install-root> [source]" >&2
  exit 2
fi

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="$1"
SOURCE="${2:-direct-card}"

if python3 -c "import yaml" >/dev/null 2>&1; then
  exec python3 "$SKILL_DIR/debounced_hook.py" "$INSTALL_ROOT" "$SOURCE"
fi

VENV="$SKILL_DIR/.venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Bootstrapping skill venv at $VENV (one-time setup)..." >&2
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$SKILL_DIR/requirements.txt"
fi

if ! "$VENV/bin/python" -c "import yaml" >/dev/null 2>&1; then
  echo "Error: skill venv at $VENV does not have PyYAML. Investigate." >&2
  echo "Try: rm -rf $VENV  and re-run." >&2
  exit 1
fi

exec "$VENV/bin/python" "$SKILL_DIR/debounced_hook.py" "$INSTALL_ROOT" "$SOURCE"