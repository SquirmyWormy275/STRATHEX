#!/usr/bin/env bash
# Compatibility wrapper; preview is the default. Pass --mode publish after merge.
set -euo pipefail
WIKI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "${WIKI_DIR}/../scripts/publish_wiki.py" "$@"
