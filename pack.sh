#!/usr/bin/env bash
# pack.sh — bundle this plugin into a distributable zip.
#
# Usage:
#   ./pack.sh                    # writes dist/quali-claude-plugin-<version>.zip
#   ./pack.sh --output /tmp/x.zip
#   ./pack.sh --name custom-name
#
# The zip is structured so that extracting it yields a single top-level folder
# containing .claude-plugin/plugin.json — compatible with Claude Code's
# --plugin-dir flag, marketplace `source` paths, and any "upload zip" plugin
# install option that Claude Desktop may expose.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MANIFEST=".claude-plugin/plugin.json"
if [[ ! -f "$MANIFEST" ]]; then
  echo "error: $MANIFEST not found. Run pack.sh from the plugin root." >&2
  exit 1
fi

# Extract name + version from manifest (no jq dependency — use python3 stdlib).
PLUGIN_NAME=$(python3 -c "import json,sys;print(json.load(open('$MANIFEST'))['name'])")
PLUGIN_VERSION=$(python3 -c "import json,sys;print(json.load(open('$MANIFEST'))['version'])")

OUTPUT=""
OVERRIDE_NAME=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output|-o) OUTPUT="$2"; shift 2 ;;
    --name|-n)   OVERRIDE_NAME="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,15p' "$0"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

FOLDER_NAME="${OVERRIDE_NAME:-$PLUGIN_NAME}"
if [[ -z "$OUTPUT" ]]; then
  mkdir -p dist
  OUTPUT="$ROOT/dist/${FOLDER_NAME}-${PLUGIN_VERSION}.zip"
fi

# Stage in a temp dir so the zip has a clean top-level folder name regardless
# of the source directory name on the developer's machine.
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
STAGE_PLUGIN="$STAGE/$FOLDER_NAME"
mkdir -p "$STAGE_PLUGIN"

# Files to include. Track explicitly so the zip only contains plugin artifacts —
# never local dev files, secrets, or build output.
INCLUDE=(
  ".claude-plugin"
  ".mcp.json"
  "skills"
  "assets"
  "AGENTS.md"
  "README.md"
)

for item in "${INCLUDE[@]}"; do
  if [[ -e "$item" ]]; then
    # Use rsync if present (handles nested excludes cleanly), else cp -R.
    if command -v rsync >/dev/null 2>&1; then
      rsync -a \
        --exclude '.DS_Store' \
        --exclude '*.swp' \
        --exclude '.idea' \
        --exclude '__pycache__' \
        "$item" "$STAGE_PLUGIN/"
    else
      cp -R "$item" "$STAGE_PLUGIN/"
      find "$STAGE_PLUGIN" -name '.DS_Store' -delete 2>/dev/null || true
    fi
  fi
done

# Remove any file that looks like a secret leak before zipping.
if grep -rIEq '(eyJ[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|"[A-Za-z0-9_-]{40,}")' "$STAGE_PLUGIN" 2>/dev/null; then
  echo "warning: possible secret pattern detected in staged files." >&2
  echo "review the contents of $STAGE_PLUGIN before publishing." >&2
fi

# Build the zip. -X strips extra extended attributes for cleaner archives.
mkdir -p "$(dirname "$OUTPUT")"
rm -f "$OUTPUT"
(cd "$STAGE" && zip -rqX "$OUTPUT" "$FOLDER_NAME")

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "packed: $OUTPUT ($SIZE)"
echo
echo "next steps:"
echo "  • upload via Claude Desktop's plugin UI (Code tab → + → Plugins → Add plugin)"
echo "  • install via CLI: claude --plugin-dir $OUTPUT"
echo "  • share the zip with a teammate"
