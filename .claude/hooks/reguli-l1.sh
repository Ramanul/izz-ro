#!/usr/bin/env bash
# Stratul L1 al regimului de reguli: livreaza o regula CONDITIONATA exact cand
# sesiunea atinge fisierele ei, in loc s-o tina in `CLAUDE.md`, care se incarca la
# FIECARE tura. Spec: `specs/regim-reguli.md` sect. 4.3.
#
# De ce hook si nu agent, masurat in #227 (IZZ-0252): `description`-ul unui agent e
# injectat in promptul de sistem la fiecare tura -> economiseste ZERO; iar corpul lui
# se incarca doar la spawn, care e o decizie a modelului, nu un mecanism. O regula
# mutata acolo DISPARE. Hook-ul se aprinde mecanic, pe orice unealta.
#
# De ce `exit 2` si `stderr`, tot masurat (IZZ-0254): `exit 0` + `stdout` NU ajunge la
# model. Un hook care doar face `echo` pe succes e invizibil, deci regula nu soseste
# si n-ai cum sa observi — scriptul pare ca a rulat.
#
# DOAR `Edit|Write`, nu `Bash` — decizie REVIZUITA pe 2026-08-30, cu masuratoare.
# Intai am acceptat supra-declansarea pe Bash („~1 KB risipit bate o regula neaplicata").
# Apoi hook-ul s-a aprins pe propria mea sesiune la o comanda care doar SCRIA DESPRE
# `templates/` intr-un heredoc — nu atingea nimic. Doua costuri nemasurate initial:
# potrivirea de subsir pe textul comenzii da fals-pozitive dese, iar harness-ul prezinta
# `exit 2` drept „blocking error", deci zgomotul nu e doar context risipit, e si un
# semnal care poate fi citit gresit ca esec. Bratul Bash a fost scos.
# Ce se pierde, spus explicit: un `sed -i` pe `templates/` nu mai aprinde regula.
# Editarile de front-end trec prin Edit/Write in practica; cazul ramane cunoscut, nu ascuns.
#
# FAIL-SAFE: orice cale neasteptata iese 0. Un hook stricat n-are voie sa blocheze
# munca — asta ar fi mai rau decat regula pe care o transporta.
set -uo pipefail

RADACINA="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
REGULI="$RADACINA/.claude/reguli"
[ -d "$REGULI" ] || exit 0

intrare="$(cat 2>/dev/null || true)"
[ -n "$intrare" ] || exit 0

# `tool_input.file_path` pentru Edit/Write. Ramura `command` e pastrata in extractor
# fiindca e inofensiva si lasa bratul Bash sa fie reactivat dintr-un singur loc
# (matcher-ul din settings.json) daca vreodata se decide altfel.
tinta="$(printf '%s' "$intrare" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
print(ti.get("file_path") or ti.get("command") or "")
' 2>/dev/null || true)"
[ -n "$tinta" ] || exit 0

# harta regula -> declansator. Un rand per regula; a doua coloana e un ERE.
livrat=""
while IFS='|' read -r fisier tipar; do
  [ -n "${fisier:-}" ] || continue
  [ -f "$REGULI/$fisier" ] || continue
  if printf '%s' "$tinta" | grep -Eq "$tipar"; then
    livrat="$livrat$(cat "$REGULI/$fisier")"$'\n'
  fi
done <<'HARTA'
13-frontend.md|templates/|static/styles\.css|generator/render\.py
HARTA

[ -n "$livrat" ] || exit 0

printf '%s' "$livrat" >&2
exit 2
