#!/bin/bash
# PreToolUse guard: reject direct agent edits to critical control-plane/state files.
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    exec "$c" "$ROOT/.claude/hooks/deny-protected-edits.py" "$ROOT"
  fi
done
printf '%s\n' "DENY: Python is unavailable; protected edit cannot be authorized." >&2
exit 2
