#!/bin/bash
# SessionStart hook — doua treburi, in ordinea asta:
#   1. INJECTEAZA MEMORIA dintre sesiuni in contextul sesiunii (local SI web).
#   2. Instaleaza dependentele pipeline-ului (doar web).
#
# Memoria si mandatul sunt derivate din fisierele canonice, nu duplicate aici. Astfel o
# schimbare de regula are o singura sursa de text si acest hook poate doar sa verifice
# ca sursa exista, nu sa pastreze o copie care poate imbatrani.
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

echo "================ MEMORIA PROIECTULUI (injectata automat) ================"
echo "Nu esti prima sesiune pe repo-ul asta. Ce urmeaza NU e context optional:"
echo "e ce stiu sesiunile dinaintea ta si tu nu. Citeste inainte sa propui orice."
echo

echo "---------------- MANDATUL (citeste inainte sa faci ceva) ----------------"
# CLAUDE.md este sursa unica de text pentru regula mandatului. Nu o copia aici: copierea
# creeaza drift silentios. Selectorul se opreste la urmatoarea sectiune de nivel 2.
MANDAT="$(awk '
  /^- \*\*Mandatul e ce a cerut proprietarul/ { on=1 }
  on { print }
  on && /^$/ { exit }
' "$ROOT/CLAUDE.md")"
if [ -z "$MANDAT" ]; then
  echo "!! ATENTIE: regula mandatului nu poate fi extrasa din CLAUDE.md; sesiunea nu poate continua in siguranta."
  exit 2
fi
printf '%s\n' "$MANDAT"
echo
echo "Si inainte sa declari ca nu poti face ceva: verifica UNEALTA, nu presupune (sect. 12a)."
echo "Lipsa unui binar nu dovedeste lipsa accesului — conectorii MCP sunt cale separata."
echo

if [ -f "$ROOT/specs/STATE.md" ]; then
  echo "---------------- specs/STATE.md (unde suntem) ----------------"
  cat "$ROOT/specs/STATE.md"
  echo
else
  echo "!! specs/STATE.md lipseste -- sursa unica de adevar pentru 'unde suntem' nu exista."
  echo
fi

if [ -f "$ROOT/specs/infrastructura.md" ]; then
  echo "---------------- fapte curente de infrastructura (nu le re-intreba) ----------------"
  grep -v '^>' "$ROOT/specs/infrastructura.md" | grep -v '^# ' | sed '/^$/d'
  echo
fi

if [ -f "$ROOT/specs/registru.tsv" ]; then
  echo "------- registru: ultimele decizii INCHISE (nu le redeschide orbeste) -------"
  awk -F'\t' 'NR>1 && ($5=="respins" || $5=="anulat" || $5=="abandonat" \
      || $5=="masurat-fals" || $5=="inchis-de-proprietar")' "$ROOT/specs/registru.tsv" \
    | tail -12 \
    | awk -F'\t' '{
        printf "%s  %s  %-20s %s\n", $1, $2, $5, substr($4,1,90)
        if ($5=="masurat-fals" && $8 != "") printf "        motiv: %s\n", substr($8,1,150)
      }' || true
  echo
  echo "(lista completa: python tools/registru.py find <subiect>)"
  echo
fi

echo "========================================================================"
echo

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

export SETUPTOOLS_USE_DISTUTILS=stdlib

if ! python -m pip install -q --ignore-installed PyYAML -r "$ROOT/requirements.txt" \
       pytest ruff pytest-randomly; then
  echo "!! ATENTIE: instalarea dependentelor a ESUAT. Pipeline-ul ('python -m generator.main')"
  echo "!! si suita de teste pot sa nu functioneze. Ruleaza manual si citeste eroarea:"
  echo "!!   python -m pip install --ignore-installed PyYAML -r requirements.txt pytest ruff pytest-randomly"
fi
