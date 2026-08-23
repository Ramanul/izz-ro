#!/usr/bin/env bash
# Verifica pe LIVE ca izz.ro e servit prin lantul de redundanta documentat in
# infra/README-failover.md. Se ruleaza de pe o masina cu iesire la internet:
# sesiunile Claude Code pe web NU pot (proxy: CONNECT tunnel failed, 403).
#
# Un HTTP 200 nu dovedeste nimic — spune ca a raspuns cineva, nu CINE. Headerele
# x-izz-* si manifestul /build.json sunt discriminatorii reali.
#
#   bash infra/verifica-live.sh
set -u

DOMENIU="${DOMENIU:-https://izz.ro}"
PRIMAR="${PRIMAR:-https://izz-ro.andifreelancer2.workers.dev}"
CB="$(date +%s)"
esec=0

hdr() { printf '\n\033[1m%s\033[0m\n' "$1"; }
verdict() {  # verdict <ok|nok> <text>
  if [ "$1" = ok ]; then printf '  \033[32m✓\033[0m %s\n' "$2"
  else printf '  \033[31m✗\033[0m %s\n' "$2"; esec=1; fi
}

# Preflight: distinge "nu ajung la site" de "site-ul raspunde gresit". Fara asta,
# o retea blocata raporteaza "headerele lipsesc, ruta nu a prins" — exact genul de
# concluzie falsa pe care scriptul asta exista ca s-o previna.
hdr "0. Ajung la $DOMENIU?"
cod="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$DOMENIU/?cb=$CB" 2>&1)"
case "$cod" in
  [23]??) verdict ok "raspunde (HTTP $cod)" ;;
  *)
    verdict nok "NU pot ajunge la $DOMENIU (cod '$cod')"
    printf '\n  Asta NU inseamna ca ruta e gresita — inseamna ca de aici nu se vede.\n'
    printf '  Sesiunile Claude Code pe web sunt respinse de proxy (CONNECT tunnel failed, 403).\n'
    printf '  Ruleaza scriptul de pe masina ta, nu dintr-o sesiune remote.\n\n'
    exit 2 ;;
esac

hdr "1. Cine serveste izz.ro (header x-izz-origin)"
origini="$(curl -fsSI "$DOMENIU/?cb=$CB" 2>/dev/null | tr -d '\r' | grep -i '^x-izz-' || true)"
if [ -z "$origini" ]; then
  verdict nok "headerele x-izz-* LIPSESC — izz-failover nu e in lant (ruta nu a prins?)"
else
  echo "$origini" | sed 's/^/     /'
  case "$origini" in
    *"x-izz-origin: primary"*) verdict ok "servit de primar prin izz-failover" ;;
    *"x-izz-origin: mirror"*)  verdict nok "servit de MIRROR — primarul e cazut, investigheaza izz-ro" ;;
    *)                         verdict nok "x-izz-origin are o valoare neasteptata" ;;
  esac
fi

hdr "2. Cache la edge (a doua cerere pe acelasi asset trebuie sa dea HIT)"
curl -fsSI "$DOMENIU/static/styles.css" >/dev/null 2>&1
c2="$(curl -fsSI "$DOMENIU/static/styles.css" 2>/dev/null | tr -d '\r' | grep -i '^x-izz-cache' || true)"
if [ -n "$c2" ]; then
  echo "     $c2"
  case "$c2" in
    *HIT*)    verdict ok "Cache API activ" ;;
    *MISS*)   verdict nok "inca MISS — mai incearca odata; daca persista, cache-ul nu prinde" ;;
    *BYPASS*) verdict nok "BYPASS pe un asset static — nu ar trebui" ;;
  esac
else
  verdict nok "x-izz-cache lipseste pe /static/styles.css"
fi

hdr "3. Aceeasi versiune pe domeniu si pe primar (/build.json)"
cd_="$(curl -fsS "$DOMENIU/build.json?cb=$CB" 2>/dev/null || true)"
cp_="$(curl -fsS "$PRIMAR/build.json?cb=$CB"  2>/dev/null || true)"
sha() { printf '%s' "$1" | sed -n 's/.*"commit"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'; }
sd="$(sha "$cd_")"; sp="$(sha "$cp_")"
echo "     izz.ro : ${sd:-<fara raspuns>}"
echo "     primar : ${sp:-<fara raspuns>}"
if [ -z "$sd" ] || [ -z "$sp" ]; then
  verdict nok "una din origini nu a intors /build.json"
elif [ "$sd" = "local" ] || [ "$sp" = "local" ]; then
  verdict nok "commit='local' — build fara metadate de CI (sonda verde-pe-nimic)"
elif [ "$sd" = "$sp" ]; then
  verdict ok "acelasi commit pe ambele"
else
  verdict nok "COMMIT-URI DIFERITE — domeniul serveste alta versiune decat primarul"
fi

hdr "Rezultat"
if [ "$esec" -eq 0 ]; then
  printf '  \033[32mTOTUL VERDE\033[0m — lantul de redundanta e in functiune.\n\n'
else
  printf '  \033[31mCEVA NU E IN REGULA\033[0m — vezi ✗ de mai sus.\n\n'
fi
exit "$esec"
