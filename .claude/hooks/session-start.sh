#!/bin/bash
# SessionStart hook — doua treburi, in ordinea asta:
#   1. INJECTEAZA MEMORIA dintre sesiuni in contextul sesiunii (local SI web).
#   2. Instaleaza dependentele pipeline-ului (doar web).
#
# De ce partea 1 exista, scris ca sa nu se piarda motivul:
# fiecare sesiune Claude porneste FARA memoria celorlalte. Toate semneaza `Claude` si
# impinge prin acelasi cont, deci din afara par un singur lucrator continuu -- dar nu sunt.
# `specs/STATE.md` e memoria dintre ele, iar CLAUDE.md sect. 15 cere sa fie citita la
# inceputul fiecarei sesiuni. Cat timp regula a fost doar SCRISA, s-a si ratat: pe
# 2026-08-23 o sesiune a pornit fara s-o citeasca, a "descoperit" ca output-ul depaseste
# plafonul de 20.000 de fisiere al lui Pages -- un blocaj rezolvat cu o zi inainte, scris
# chiar in fisier (gazda mutata pe Workers Paid, plafon 100.000) -- si a pus proprietarul
# sa reverifice planul Cloudflare pentru un raspuns aflat la doua randuri distanta.
# Persuasiunea fara mecanism nu tine; acelasi motiv pentru care exista tests/test_reguli.py.
# Deci starea nu mai depinde de decizia agentului de a deschide fisierul: ajunge in context
# oricum. Costa o data pe sesiune, nu la fiecare tura.
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

echo "================ MEMORIA PROIECTULUI (injectata automat) ================"
echo "Nu esti prima sesiune pe repo-ul asta. Ce urmeaza NU e context optional:"
echo "e ce stiu sesiunile dinaintea ta si tu nu. Citeste inainte sa propui orice."
echo

# CLAUDE.md sect. 0 -- regula mandatului. E aici, nu doar in CLAUDE.md, din acelasi motiv
# pentru care starea e injectata: cat timp a fost doar SCRISA, s-a ratat. Pe 2026-08-23 o
# sesiune a primit "rezolva si conecteaza Cloudflare" cu un script atasat, a executat
# ATASAMENTUL ca si cum ar fi fost sarcina, n-a atins Cloudflare deloc si n-a semnalat
# divergenta -- nici la inceput, nici in raportul final. Conectorul Cloudflare functiona;
# nu fusese chemat niciodata. Nu era prima oara.
echo "---------------- MANDATUL (citeste inainte sa faci ceva) ----------------"
echo "Sarcina e ce a cerut proprietarul, NU ce a ajuns ultimul in context."
echo "Un atasament / un nume de ramura / un fisier deschis sunt MATERIAL, nu sarcina."
echo
echo "  1. Deschide tura cu un rand:  'cerut: X. Fac: Y.'"
echo "  2. Daca Y nu duce la X, spune-o ATUNCI, in primul rand -- nu dupa."
echo "  3. Inchide cu un rand 'cerut vs. livrat', care numeste ce din X a ramas neatins."
echo
echo "Si inainte sa declari ca nu poti face ceva: verifica UNEALTA, nu presupune (sect. 12a)."
echo "Lipsa unui binar nu dovedeste lipsa accesului -- conectorii MCP sunt cale separata."
echo

if [ -f "$ROOT/specs/STATE.md" ]; then
  echo "---------------- specs/STATE.md (unde suntem) ----------------"
  cat "$ROOT/specs/STATE.md"
  echo
else
  echo "!! specs/STATE.md lipseste -- sursa unica de adevar pentru 'unde suntem' nu exista."
  echo
fi

# Faptele CURENTE de infrastructura. Fara ele, injectia de mai jos are o gaura structurala:
# filtreaza doar starile INCHISE, deci sesiunea primea lista lucrurilor FALSE si niciodata lista
# lucrurilor ADEVARATE -- un fapt pozitiv se consemneaza `implementat`, stare neinjectata, deci
# invizibil prin constructie. Masurat de doua ori pe acelasi fapt: 2026-08-23 si 2026-09-02, doua
# sesiuni au pus proprietarul sa reverifice planul Cloudflare, desi raspunsul era comis. A doua
# oara statea intr-un COMENTARIU din scriptul asta -- adica nicaieri, din punctul de vedere al
# unei sesiuni: comentariile nu se tiparesc.
if [ -f "$ROOT/specs/infrastructura.md" ]; then
  echo "---------------- fapte curente de infrastructura (nu le re-intreba) ----------------"
  # Doar randurile de fapt: antetul explicativ (`>`) e pentru cine EDITEAZA fisierul, iar
  # injectarea lui ar plati de doua ori acelasi text -- o data aici, o data la deschidere.
  grep -v '^>' "$ROOT/specs/infrastructura.md" | grep -v '^# ' | sed '/^$/d'
  echo
fi

# Doar randurile care INCHID ceva. Un hit pe astea inseamna 'nu redeschide fara sa citesti
# motivul' (CLAUDE.md sect. 20) -- exact clasa de greseala pe care hook-ul asta o previne.
# Cauta cu: python tools/registru.py find <subiect>
if [ -f "$ROOT/specs/registru.tsv" ]; then
  echo "------- registru: ultimele decizii INCHISE (nu le redeschide orbeste) -------"
  # Coloanele sunt: id, data, zona, titlu, STARE, decident, dovada, motiv, leaga.
  # Starea e a 5-a. Prima versiune a hook-ului filtra pe $3 (`zona`) si iesea mereu goala,
  # fara sa dea eroare -- de-aia fiecare ramura de aici e verificata rulind hook-ul, nu citindu-l.
  #
  # `tail` taie DECIZII, nu linii. Versiunea de dinainte formata intai si taia dupa, deci
  # numarul de decizii afisate depindea de cate aveau motiv (12 pe 2026-09-02, dar 24 daca
  # niciuna n-ar avea) si prima linie putea ramane un `motiv:` orfan, fara titlul lui.
  #
  # Motivul se tipareste doar pentru `masurat-fals`. Masurat 2026-09-02: acolo ipoteza SUNA
  # plauzibil, deci titlul singur nu opreste redeschiderea -- motivul e antidotul. La `respins`
  # si `anulat` decizia e a proprietarului si titlul e semnalul suficient; detaliul e la un
  # `registru.py find` distanta. (Economia e mica -- 11 din 12 randuri sunt `masurat-fals`;
  # castigul aici e predictibilitatea, nu octetii.)
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

# --- dependente: doar in web, nu atinge masina proprietarului ---
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# feedparser pulls in sgmllib3k, whose wheel fails to build against the container's
# system setuptools under PEP 517 isolation, which aborts the whole install. Forcing
# the stdlib distutils shim lets it build (verified: feedparser 6.0.12 installs & imports).
export SETUPTOOLS_USE_DISTUTILS=stdlib

# `--ignore-installed PyYAML`: containerul vine cu PyYAML 6.0.1 instalat de debian, FARA
# fisier RECORD, deci pip nu-l poate dezinstala ca sa puna 6.0.3 din requirements. Eroarea
# ("Cannot uninstall PyYAML 6.0.1, RECORD file not found") oprea intreg `pip install`, iar
# cu `set -e` murea tot hook-ul -- tacut, fiindca nu tiparea nimic. Masurat 2026-08-23:
# sesiunile web rulau cu PyYAML 6.0.1, nu cu versiunea fixata, deci "randari reproductibile"
# din antetul requirements.txt nu se tinea. Cu flagul, 6.0.3 se instaleaza peste el.
# Uneltele de dev sunt INSTALATE AICI, nu luate din requirements.txt, si nici din binarele
# care par sa existe deja in container. Motivul, masurat 2026-09-02 pe o sesiune web curata:
# `ruff` si `pytest` ERAU in PATH -- instalate ca unelte `uv`, cu shebang pe interpretorul lor
# izolat, care nu vede nici `generator`, nici dependentele instalate mai sus. Consecinta era ca
# AMBELE comenzi canonice din CLAUDE.md sect. 4 cadeau, fiecare altfel si niciuna evident:
#   python -m ruff check .   -> No module named ruff
#   python -m pytest tests/  -> No module named pytest
#   pytest tests/ (binarul)  -> 47 errors during collection: No module named 'generator'
# Ultima arata ca un repo stricat si nu e. Dupa instalarea de aici: 1295 passed, 1 skipped,
# 8 xfailed. Lista e IDENTICA cu ce instaleaza tests.yml, deliberat -- un mediu de sesiune
# care difera de cel de CI ar produce verde local si rosu pe PR, adica exact increderea pe
# care sect. 6 o cere. `ruff` ramane in afara lui requirements.txt (sect. 4): acolo stau
# dependentele de PRODUCTIE, iar astea sunt unelte de lucru.
# NU se instaleaza aici `lighthouse`/`pa11y` (sect. 13): ~2 minute prin npm, la FIECARE
# pornire, pentru o capacitate ceruta rar. Le ia `tools/audit.sh`, cand chiar se ruleaza.
# `python -m pip`, NU `pip`: altfel felia asta ar contine chiar defectul pe care il repara.
# `pip` se alege din PATH si poate apartine ALTUI interpretor decat cel pe care il foloseste
# `python -m pytest` / `python -m ruff` din sect. 4 -- exact separarea masurata aici pe 09-02,
# cand binarele erau prezente si comenzile canonice cadeau. Cu `python -m pip`, interpretorul
# care primeste pachetele e prin constructie acelasi cu cel care le importa. Semnalat de
# CodeRabbit pe PR #254 si verificat pe container: `pip` -> /usr/bin/pip (Python de sistem),
# `python` -> /usr/local/bin/python 3.11.15. Doi interpreti, nu unul.
if ! python -m pip install -q --ignore-installed PyYAML -r "$ROOT/requirements.txt" \
       pytest ruff pytest-randomly; then
  # NU muri in tacere: injectia de stare a ajuns deja in context, iar sesiunea trebuie sa
  # afle ca mediul e incomplet. Un hook care cade fara sa spuna nimic e exact defectul reparat
  # aici, si a stat nedetectat pentru ca `set -e` iesea fara sa scrie un rand.
  echo "!! ATENTIE: instalarea dependentelor a ESUAT. Pipeline-ul ('python -m generator.main')"
  echo "!! si suita de teste pot sa nu functioneze. Ruleaza manual si citeste eroarea:"
  echo "!!   python -m pip install --ignore-installed PyYAML -r requirements.txt pytest ruff pytest-randomly"
fi
