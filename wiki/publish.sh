#!/usr/bin/env bash
# Sync wiki/*.md to the GitHub wiki repo.
#
# Prerequisites (one-time):
#   1. Visit https://github.com/SquirmyWormy275/STRATHEX/wiki
#   2. Click "Create the first page" — any title, any content, save.
#
# Then run this script any time you want to publish wiki edits.

set -euo pipefail

REPO="SquirmyWormy275/STRATHEX"
WIKI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"

trap 'rm -rf "$TMP_DIR"' EXIT

echo "Cloning wiki repo..."
if ! git clone "https://github.com/${REPO}.wiki.git" "$TMP_DIR" 2>&1; then
    echo ""
    echo "ERROR: Wiki repo not initialized."
    echo "Go to https://github.com/${REPO}/wiki and click 'Create the first page' first."
    exit 1
fi

echo "Copying markdown pages..."
cp "${WIKI_DIR}"/*.md "$TMP_DIR/"
# Don't publish this README or the script itself.
rm -f "$TMP_DIR/README.md"

cd "$TMP_DIR"
git add -A

if git diff --cached --quiet; then
    echo "No changes to publish."
    exit 0
fi

git commit -m "Update wiki from STRATHEX/wiki/"
git push origin HEAD

echo ""
echo "Wiki published: https://github.com/${REPO}/wiki"
