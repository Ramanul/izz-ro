#!/usr/bin/env bash
# scripts/open_google_codespace.sh
# Script pentru Codespaces: salvează HTML-ul unei căutări Google într-un fișier.
# Usage:
#   ./scripts/open_google_codespace.sh "vreau sa lucrez direct in github"

set -euo pipefail

QUERY="${1:-vreau sa lucrez direct in github}"
ENC=$(python3 - <<PY
import urllib.parse,sys
print(urllib.parse.quote(sys.argv[1]))
PY
"$QUERY")
URL="https://www.google.com/search?q=${ENC}"
OUT="google_search_result.html"

# Preferăm Chromium headless (păstrează JS-urile necesare pentru Google).
if command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1; then
  CHROME=$(command -v chromium || command -v chromium-browser)
  echo "Folosing ${CHROME} --headless --no-sandbox --dump-dom '${URL}' > ${OUT}"
  "${CHROME}" --headless --no-sandbox --dump-dom "${URL}" > "${OUT}"
  echo "Salvat ${OUT}. Deschide-l cu Simple Browser (Ctrl+Shift+P → Simple Browser: Show) sau în editorul tău." 
  exit 0
fi

# Fallback: curl (pagina va fi posibil incompletă din cauza JS)
if command -v curl >/dev/null 2>&1; then
  echo "chromium absent; folosesc curl (HTML poate fi redus din cauza JS)"
  curl -L -A "Mozilla/5.0" "${URL}" -o "${OUT}"
  echo "Salvat ${OUT}"
  exit 0
fi

# Fallback 2: wget
if command -v wget >/dev/null 2>&1; then
  echo "chromium/curl absent; folosesc wget"
  wget -O "${OUT}" --user-agent="Mozilla/5.0" "${URL}"
  echo "Salvat ${OUT}"
  exit 0
fi

echo "Nici chromium, nici curl, nici wget nu sunt instalate. Rulează:
  sudo apt-get update && sudo apt-get install -y chromium curl wget"
exit 1
