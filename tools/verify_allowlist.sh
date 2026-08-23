#!/usr/bin/env bash
# verify_allowlist.sh — ce hosturi izz.ro pot fi atinse din mediul CURENT.
#
# De ce exista: CLAUDE.md §16.3 permite "confirmat pe live" doar dupa ce ai atins
# efectiv site-ul deployat, si cere sa citezi comanda cand nu poti. Raspunsul difera
# de la un mediu la altul (sandbox local vs. sesiune remote) SI se schimba in timp:
# pe 2026-08-21 izz.ro era respins de proxy din sesiunea remote, pe 2026-08-23
# raspunde 200 din aceeasi pozitie. Deci se masoara la fiecare sesiune, nu se
# presupune si nu se citeaza din memorie (§12a).
#
# Ce distinge, si asta e tot rostul lui:
#   - tunel CONNECT refuzat de gateway   -> nu ai iesit din mediu, allowlist
#   - raspuns venit de la ORIGINE        -> ai iesit; un 403 aici e Cloudflare/WAF,
#                                           NU allowlist (confuzia care a dus deja
#                                           la un diagnostic gresit)
#   - nume care nu se rezolva in DNS     -> gateway-ul da acelasi 403 ca la refuzul
#                                           de politica, deci NU e verdict de allowlist
#
#   bash tools/verify_allowlist.sh                          # lista implicita
#   bash tools/verify_allowlist.sh https://exemplu.ro/ ...  # hosturi date explicit
#   ALT_ORIGIN=https://x.workers.dev bash tools/verify_allowlist.sh
#   TIMEOUT=30 bash tools/verify_allowlist.sh
#
# Iesire: 0 = toate hosturile testate au raspuns de la origine
#         1 = cel putin unul e inaccesibil din mediul asta
set -u   # fara -e: check() intoarce 1 deliberat, si vrem sa testam TOATE hosturile

TIMEOUT="${TIMEOUT:-15}"
# Originea alternativa: acelasi nume ca variabila de repo citita de build/monitor/
# visual/harta-smoke/harta-data si de tools/verify_release.py. Implicit = Workerul.
ALT_ORIGIN="${ALT_ORIGIN:-https://izz-ro.andifreelancer2.workers.dev}"

esecuri=0

check() {
  local url="$1" host nume code rc err errfile
  host=${url#*://}; host=${host%%/*}
  # Numele pentru DNS nu e acelasi lucru cu hostul din URL: `exemplu.ro:8443` nu se
  # rezolva, si l-ar fi declarat inexistent. Portul se taie, IPv6 se descojeste.
  nume=$host
  case $nume in
    \[*\]*) nume=${nume%%\]*}; nume=${nume#\[} ;;
    *:*)    nume=${nume%:*} ;;
  esac

  errfile=$(mktemp)
  # `--`: fara el, un argument care incepe cu `-` ajunge OPTIUNE de curl, nu URL.
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" -- "$url" 2>"$errfile")
  rc=$?
  err=$(cat "$errfile"); rm -f "$errfile"

  if [ "$rc" -eq 0 ]; then
    case "$code" in
      2*|3*) printf '[OK]              %-42s HTTP %s (a raspuns originea)\n' "$host" "$code" ;;
      403)   printf '[ALLOWLIST OK]    %-42s HTTP 403 de la ORIGINE — tunel deschis, deci Cloudflare/WAF, NU allowlist\n' "$host" ;;
      *)     printf '[ALLOWLIST OK]    %-42s HTTP %s de la origine — tunel deschis; codul e al aplicatiei, nu al proxy-ului\n' "$host" "$code" ;;
    esac
    return 0
  fi

  if printf '%s' "$err" | grep -q 'CONNECT tunnel failed'; then
    # Gateway-ul raspunde 403 la CONNECT si pentru refuz de politica, SI pentru un
    # upstream inexistent — masurat 2026-08-23, un nume .invalid da exact acelasi
    # mesaj. DNS-ul le separa: daca numele se rezolva, refuzul e al politicii.
    # `getent` e din glibc si LIPSESTE pe macOS. Fara garda, exit 127 se citea ca
    # "nu se rezolva" si iesea un verdict FALS -- exact greseala pe care scriptul
    # exista ca s-o previna. Unealta lipsa trebuie sa dea "nu stiu", nu o concluzie.
    if ! command -v getent >/dev/null 2>&1; then
      printf '[NECUNOSCUT]      %-42s CONNECT refuzat, dar `getent` lipseste aici -> nu pot spune daca numele se rezolva\n' "$host"
    elif getent hosts "$nume" >/dev/null 2>&1; then
      printf '[BLOCAT DE PROXY] %-42s CONNECT refuzat, dar numele se rezolva in DNS -> nu e in allowlist\n' "$host"
    else
      printf '[NUME INEXISTENT] %-42s CONNECT refuzat SI numele nu se rezolva -> verifica scrierea; NU e verdict de allowlist\n' "$host"
    fi
    esecuri=$((esecuri + 1)); return 1
  fi

  printf '[EROARE RETEA]    %-42s curl rc=%s: %s\n' "$host" "$rc" "$err"
  esecuri=$((esecuri + 1)); return 1
}

echo "=== Test egress $(date -u +%FT%TZ) ==="
if [ "$#" -gt 0 ]; then
  for url in "$@"; do check "$url"; done
else
  check "$ALT_ORIGIN/"
  check https://izz.ro/
  check https://www.izz.ro/
fi

echo
echo "=== Esecuri recente raportate de proxy ==="
if [ -z "${HTTPS_PROXY:-}" ]; then
  echo "(HTTPS_PROXY nesetat — niciun proxy de interogat)"
else
  stare=$(curl -sS --max-time "$TIMEOUT" "$HTTPS_PROXY/__agentproxy/status" 2>/dev/null)
  if [ -z "$stare" ]; then
    echo "(endpointul de stare nu a raspuns)"
  elif command -v jq >/dev/null 2>&1; then
    printf '%s' "$stare" \
      | jq -r '.recentRelayFailures // [] | if length == 0 then "(niciunul)"
               else .[] | "\(.ts)  \(.host)  \(.kind): \(.detail)" end'
  else
    # fara jq: fragmentele ies nepereche, dar tot arata ce host a fost refuzat
    printf '%s' "$stare" | tr ',' '\n' | grep -E '"(kind|detail|host)"' || echo "(niciunul)"
  fi
fi

exit $(( esecuri > 0 ? 1 : 0 ))
