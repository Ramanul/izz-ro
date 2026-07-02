#!/usr/bin/env bash
# Front-end audit loop: render -> serve output/ on localhost -> Lighthouse + pa11y.
# Structured output (JSON scores) you can compare before/after a slice. No external
# service, no rate limits, runs pre-deploy. See CLAUDE.md section 13.
#
#   bash tools/audit.sh                 # audit home + one article page
#   PORT=9000 bash tools/audit.sh       # custom port
#   CHROME_PATH=/path/to/chrome bash tools/audit.sh   # override browser binary
#
# Requires (once): npm i -g lighthouse pa11y
set -eu   # no pipefail: `find | head` SIGPIPE is expected, not an error

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8848}"
OUT="${AUDIT_OUT:-$ROOT/.audit}"
mkdir -p "$OUT"

# Locate a Chromium/Chrome binary (pre-installed in CI/cloud, or system install).
if [ -z "${CHROME_PATH:-}" ]; then
  CHROME_PATH="$(ls -d /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | head -1 || true)"
  [ -z "$CHROME_PATH" ] && CHROME_PATH="$(command -v google-chrome chromium chromium-browser chrome 2>/dev/null | head -1 || true)"
fi
[ -z "$CHROME_PATH" ] && { echo "!! no Chrome/Chromium found — set CHROME_PATH"; exit 1; }
export CHROME_PATH
FLAGS="--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage"

echo ">> render-only"
( cd "$ROOT" && python -m generator.main --render-only >/dev/null )

echo ">> serve output/ on :$PORT"
python -m http.server "$PORT" --directory "$ROOT/output" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
until curl -s -o /dev/null "http://localhost:$PORT/"; do sleep 0.3; done

# Article page: first rendered article under any category.
ART="$(cd "$ROOT/output" && find . -mindepth 3 -name index.html | head -1 | sed 's|^\.||;s|index.html$||')"

lh () {  # $1=url  $2=label
  lighthouse "$1" --quiet --output=json --output-path="$OUT/lh-$2.json" \
    --only-categories=performance,accessibility,best-practices,seo \
    --chrome-flags="$FLAGS" --form-factor=mobile --screenEmulation.mobile >/dev/null
  node -e 'const r=require(process.argv[1]);console.log(process.argv[2].padEnd(10),
    Object.entries(r.categories).map(([k,v])=>k[0].toUpperCase()+k.slice(1,4)+" "+Math.round(v.score*100)).join("  "))' \
    "$OUT/lh-$2.json" "$2"
}

echo ">> Lighthouse (mobile)  [Perf / Acce / Best / Seo]"
lh "http://localhost:$PORT/" home
[ -n "$ART" ] && lh "http://localhost:$PORT$ART" article

echo ">> pa11y (WCAG2AA) home"
cat > "$OUT/pa11y.json" <<JSON
{ "chromeLaunchConfig": { "executablePath": "$CHROME_PATH", "args": ["--no-sandbox","--disable-dev-shm-usage"] } }
JSON
pa11y --config "$OUT/pa11y.json" --standard WCAG2AA --reporter csv \
  "http://localhost:$PORT/" > "$OUT/pa11y-home.csv" 2>/dev/null || true
ERRS=$(( $(wc -l < "$OUT/pa11y-home.csv") - 1 ))
echo "   WCAG2AA errors on home: ${ERRS} (detail: $OUT/pa11y-home.csv)"

echo ">> done. JSON reports in $OUT/"
