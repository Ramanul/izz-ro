#!/bin/bash
# PreToolUse guard: reject direct agent edits to critical control-plane/state files.
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# Numele fisierului Python e cu UNDERSCORE (ca `reguli_l1.py`), wrapperul e cu cratime.
# Pana pe 2026-09-06 aici scria `deny-protected-edits.py`, care nu exista: `exec python3`
# pe un fisier inexistent iese cu 2, iar un PreToolUse care iese cu 2 BLOCHEAZA unealta --
# deci garda nu proteja caile protejate, ci refuza ORICE Edit/Write/Bash din sesiune.
# Garda trebuie sa cada inchis, dar cu un mesaj care spune CARE fisier lipseste.
GARDA="$ROOT/.claude/hooks/deny_protected_edits.py"
if [ ! -f "$GARDA" ]; then
  printf '%s\n' "DENY: guard script missing ($GARDA); protected edit cannot be authorized." >&2
  exit 2
fi

for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    exec "$c" "$GARDA" "$ROOT"
  fi
done
printf '%s\n' "DENY: Python is unavailable; protected edit cannot be authorized." >&2
exit 2
