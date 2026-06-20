#!/usr/bin/env bash
# Assemble a self-contained CONSTRUCT workspace directory.
#
# Usage:
#   ./setup-construct.sh <target-directory>
#
# Example:
#   ./setup-construct.sh ~/my-construct
#   # Then open ~/my-construct in Claude and say "Initialize cosmology"

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

if [[ -d "$TARGET/.construct" ]]; then
  echo "Error: $TARGET/.construct already exists. Remove it first or choose a different directory."
  exit 1
fi

if [[ -d "$TARGET/.claude" ]]; then
  echo "Error: $TARGET/.claude already exists. Remove it first or choose a different directory."
  exit 1
fi

echo "Setting up CONSTRUCT at: $TARGET"

# Create target directory
mkdir -p "$TARGET"

# Deploy root files
cp "$IMPL_DIR/AGENTS.md" "$TARGET/AGENTS.md"
cp "$IMPL_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
cp "$IMPL_DIR/USER_GUIDE.md" "$TARGET/USER_GUIDE.md"

# Register the CONSTRUCT MCP server (project-scoped, committed with the workspace).
# Claude Code prompts to approve it on first load.
cp "$IMPL_DIR/.mcp.json" "$TARGET/.mcp.json"

# Deploy .claude/ (Claude Code native configuration)
mkdir -p "$TARGET/.claude"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude 'node_modules' \
  "$IMPL_DIR/claude/skills" "$TARGET/.claude/"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude 'node_modules' \
  "$IMPL_DIR/claude/agents" "$TARGET/.claude/"
cp "$IMPL_DIR/claude/settings.json" "$TARGET/.claude/settings.json"

# Deploy .construct/ (reference library)
mkdir -p "$TARGET/.construct"
cp -r "$IMPL_DIR/construct/templates"  "$TARGET/.construct/"
cp -r "$IMPL_DIR/construct/references" "$TARGET/.construct/"
cp -r "$IMPL_DIR/construct/workflows"  "$TARGET/.construct/"

# Stamp VERSION marker from the installed engine (release + build stamp).
VERSION="$(python -c 'from construct import __version__; print(__version__)')"
if [[ -z "$VERSION" ]]; then
  echo "Error: could not read version from construct package"
  exit 1
fi
printf '%s\n' "$VERSION" > "$TARGET/.construct/VERSION"

echo ""
echo "Done. Structure:"
echo ""
echo "  $TARGET/"
echo "  ├── AGENTS.md              # Operating mode definition"
echo "  ├── CLAUDE.md              # Claude Code entry point (imports AGENTS.md)"
echo "  ├── USER_GUIDE.md          # End-user guide"
echo "  ├── .mcp.json              # CONSTRUCT MCP server (approve on first load)"
echo "  ├── .claude/               # Claude Code native config"
echo "  │   ├── settings.json      # Permission pre-approvals"
echo "  │   ├── skills/            # Invocable as /skill-name"
echo "  │   └── agents/            # Curator + Researcher subagents"
echo "  └── .construct/            # Reference library"
echo "      ├── templates/"
echo "      ├── references/"
echo "      └── workflows/"
echo ""
echo "Next steps:"
echo "  1. Open $TARGET in Claude Code"
echo "  2. Say: \"Initialize a workspace for cosmology\""
echo "  3. Claude creates cosmology/ as a subdirectory with cards, connections, etc."
echo "  4. Use /construct-help for context-aware suggestions"
