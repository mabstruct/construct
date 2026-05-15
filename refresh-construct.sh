#!/usr/bin/env bash
# Refresh an existing CONSTRUCT install with the latest skills/workflows/etc.
# from CONSTRUCT-CLAUDE-impl/. Additive: copies new files and updates existing
# ones, but does NOT delete files removed from source. Re-run safely any time.
#
# Usage:
#   ./refresh-construct.sh <target-directory>
#
# Example:
#   ./refresh-construct.sh ~/my-construct
#
# For fresh installs, use ./setup-construct.sh instead.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <target-directory>"
  echo "Example: $0 ~/my-construct"
  exit 1
fi

TARGET="$(cd "$(dirname "$1")" 2>/dev/null && pwd)/$(basename "$1")" || TARGET="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMPL_DIR="$SCRIPT_DIR/CONSTRUCT-CLAUDE-impl"

if [[ ! -d "$IMPL_DIR" ]]; then
  echo "Error: CONSTRUCT-CLAUDE-impl/ not found at $SCRIPT_DIR"
  exit 1
fi

if [[ ! -d "$TARGET" ]]; then
  echo "Error: target $TARGET does not exist. Use ./setup-construct.sh for fresh installs."
  exit 1
fi

if [[ ! -d "$TARGET/.construct" ]]; then
  echo "Error: $TARGET/.construct not found. Use ./setup-construct.sh for fresh installs."
  exit 1
fi

echo "Refreshing CONSTRUCT at: $TARGET"
echo "  Source: $IMPL_DIR"
echo ""

# Track what changed for the summary
ADDED_SKILLS=()
EXISTING_SKILLS_BEFORE=""
if [[ -d "$TARGET/.claude/skills" ]]; then
  EXISTING_SKILLS_BEFORE="$(ls "$TARGET/.claude/skills" 2>/dev/null || true)"
fi

# Refresh .claude/ (Claude Code native config)
mkdir -p "$TARGET/.claude/skills" "$TARGET/.claude/agents"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude 'node_modules' \
  "$IMPL_DIR/claude/skills/." "$TARGET/.claude/skills/"
echo "  ✓ refreshed .claude/skills/"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude 'node_modules' \
  "$IMPL_DIR/claude/agents/." "$TARGET/.claude/agents/"
echo "  ✓ refreshed .claude/agents/"
cp "$IMPL_DIR/claude/settings.json" "$TARGET/.claude/settings.json"
echo "  ✓ refreshed .claude/settings.json"

# Refresh .construct/ (reference library)
for sub in templates references workflows; do
  if [[ -d "$IMPL_DIR/construct/$sub" ]]; then
    mkdir -p "$TARGET/.construct/$sub"
    cp -R "$IMPL_DIR/construct/$sub/." "$TARGET/.construct/$sub/"
    echo "  ✓ refreshed .construct/$sub/"
  fi
done

# Detect newly added skills
if [[ -d "$TARGET/.claude/skills" ]]; then
  for skill in $(ls "$TARGET/.claude/skills"); do
    if ! grep -qx "$skill" <<< "$EXISTING_SKILLS_BEFORE"; then
      ADDED_SKILLS+=("$skill")
    fi
  done
fi

# Refresh VERSION marker (drives {{VERSION}} substitution in views-scaffold)
if [[ -f "$IMPL_DIR/VERSION" ]]; then
  cp "$IMPL_DIR/VERSION" "$TARGET/.construct/VERSION"
  echo "  ✓ .construct/VERSION = $(cat "$IMPL_DIR/VERSION")"
fi

# Refresh root files
cp "$IMPL_DIR/AGENTS.md" "$TARGET/AGENTS.md"
echo "  ✓ refreshed AGENTS.md"
cp "$IMPL_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
echo "  ✓ refreshed CLAUDE.md"

echo ""
if [[ ${#ADDED_SKILLS[@]} -gt 0 ]]; then
  echo "New skills since last refresh:"
  for s in "${ADDED_SKILLS[@]}"; do
    echo "  + $s"
  done
  echo ""
fi

echo "All available skills (invocable as /skill-name):"
ls "$TARGET/.claude/skills" | sed 's/^/  /'
echo ""

# v0.2 first-time guidance
if [[ -d "$TARGET/.claude/skills/construct-views-scaffold" && ! -d "$TARGET/views/src" ]]; then
  echo "v0.2 views skills are present but views/src/ does not exist yet."
  echo "First-time setup chain (in $TARGET):"
  echo ""
  echo "  Say to Claude (in this directory):"
  echo "    1. /construct-views-scaffold"
  echo "    2. /construct-views-build"
  echo "    3. /construct-views-generate-data"
  echo "    4. /construct-up"
  echo ""
  echo "Or invoke the chain manually — see CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md §3."
fi

echo "Done."
