#!/bin/bash
# PostToolUse — livreaza regulile L1 (vezi .claude/hooks/reguli_l1.py pentru DE CE).
# Bash-ul e doar lansator: gaseste interpretorul si taca din gura daca nu-l gaseste.
# Containerul web are `python3`, masina proprietarului are `python` — de-aia amandoua.
set -uo pipefail   # deliberat FARA -e: un hook care moare nu are voie sa rupa sesiunea

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    exec "$c" "$ROOT/.claude/hooks/reguli_l1.py"
  fi
done
exit 0
