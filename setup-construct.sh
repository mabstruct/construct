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

echo "Setting up CONSTRUCT at: $TARGET"

# Create target directory
mkdir -p "$TARGET"

# Copy agent infrastructure into .construct/
mkdir -p "$TARGET/.construct"
cp -r "$IMPL_DIR/agents"     "$TARGET/.construct/"
cp -r "$IMPL_DIR/skills"     "$TARGET/.construct/"
cp -r "$IMPL_DIR/workflows"  "$TARGET/.construct/"
cp -r "$IMPL_DIR/references" "$TARGET/.construct/"
cp -r "$IMPL_DIR/templates"  "$TARGET/.construct/"

# Copy the root AGENTS.md (Claude reads this first)
cp "$IMPL_DIR/AGENTS.md" "$TARGET/AGENTS.md"

echo ""
echo "Done. Structure:"
echo ""
echo "  $TARGET/"
echo "  ├── AGENTS.md              # Claude reads this"
echo "  └── .construct/            # Agent infrastructure"
echo "      ├── agents/"
echo "      ├── skills/"
echo "      ├── workflows/"
echo "      ├── references/"
echo "      └── templates/"
echo ""
echo "Next steps:"
echo "  1. Open $TARGET in Claude (Desktop, Code, or claude.ai project)"
echo "  2. Say: \"Initialize a workspace for cosmology\""
echo "  3. Claude creates cosmology/ as a subdirectory with cards, connections, etc."
