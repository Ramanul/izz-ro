#!/usr/bin/env bash
# Front-end audit loop: render -> serve output/ on localhost -> Lighthouse + pa11y.
# Structured output (JSON scores) you can compare before/after a slice. No external
# service, no rate limits, runs pre-deploy. See CLAUDE.md section 13.
#
#   bash tools/audit.sh                 # audit home + one article page
#   PORT=9000 bash tools/audit.sh       # custom port
#   CHROME_PATH=/path/to/chrome bash tools/audit.sh   # override browser binary
#   ARTICLE_PATH=/local/slug/ bash tools/audit.sh     # pin the article page (use for before/after)
#
# Tool versions + the article scored are written to .audit/versions.txt on every run: a
# Lighthouse or Chromium upgrade moves the numbers, so a score without them is not comparable.
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
  # Windows/Git-Bash: none of the above exist, so the script used to abort unless the caller
  # exported CHROME_PATH by hand. Only GOOGLE CHROME's default install locations are probed:
  # Chromium ships no official Windows installer, so its path depends on the packager and
  # there is nothing canonical to hard-code — a guessed path would be a fabricated one. For a
  # Chromium or Edge build on Windows, pass CHROME_PATH; that route is unchanged and works.
  if [ -z "$CHROME_PATH" ]; then
    for p in "/c/Program Files/Google/Chrome/Application/chrome.exe" \
             "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
             "$HOME/AppData/Local/Google/Chrome/Application/chrome.exe"; do
      if [ -x "$p" ]; then CHROME_PATH="$p"; break; fi
    done
  fi
fi
[ -z "$CHROME_PATH" ] && { echo "!! no browser found — set CHROME_PATH (Chrome, Chromium or Edge)"; exit 1; }
export CHROME_PATH
FLAGS="--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage"

echo ">> render-only"
( cd "$ROOT" && python -m generator.main --render-only >/dev/null )

echo ">> serve output/ on :$PORT"
python -m http.server "$PORT" --directory "$ROOT/output" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
until curl -s -o /dev/null "http://localhost:$PORT/"; do sleep 0.3; done

# Article page. `find | head -1` returns whatever the filesystem hands back first, so the
# page being scored changed between runs and the "article" number was not comparable across
# a slice — measured: two runs on the same commit scored two different articles, 87 vs 88.
# Sort makes the default deterministic for a given corpus; ARTICLE_PATH pins it outright,
# which is what you want when comparing before/after (content shifts between renders).
if [ -n "${ARTICLE_PATH:-}" ]; then
  ART="$ARTICLE_PATH"
else
  ART="$(cd "$ROOT/output" && find . -mindepth 3 -name index.html | LC_ALL=C sort | head -1 \
         | sed 's|^\.||;s|index.html$||')"
fi
echo ">> article page: ${ART:-none}${ARTICLE_PATH:+  (pinned via ARTICLE_PATH)}"

# `chrome.exe --version` on Windows forwards to an already-running instance and prints
# "Opening in existing browser session." — which is what versions.txt recorded, i.e. no
# version at all. Keep --version where it is correct (Linux/CI) and fall back to the
# executable's own file metadata. Not the Lighthouse report's hostUserAgent: Chrome
# reports a reduced UA there (150.0.0.0), so the build number is already lost.
chrome_version () {
  v="$("$CHROME_PATH" --version 2>/dev/null || true)"
  case "$v" in *[0-9].[0-9]*) printf '%s\n' "$v"; return;; esac
  if command -v powershell.exe >/dev/null 2>&1; then
    w="$(cygpath -w "$CHROME_PATH" 2>/dev/null || printf '%s' "$CHROME_PATH")"
    # A single quote in the path (C:\Users\O'Brien\...) would end PowerShell's literal
    # string early and silently degrade the version to '?'. Doubling is the escape a
    # single-quoted PowerShell string takes; -LiteralPath keeps [ ] from globbing.
    w="$(printf '%s' "$w" | sed "s/'/''/g")"
    v="$(powershell.exe -NoProfile -Command "(Get-Item -LiteralPath '$w').VersionInfo.ProductVersion" 2>/dev/null | tr -d '\r')"
    [ -n "$v" ] && { printf 'Chrome %s\n' "$v"; return; }
  fi
  printf '?\n'
}

# Versions decide the scores as much as the code does — record them next to the numbers.
{ echo "date:       $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "commit:     $(cd "$ROOT" && git rev-parse --short HEAD 2>/dev/null || echo '?')"
  echo "lighthouse: $(lighthouse --version 2>/dev/null || echo '?')"
  echo "pa11y:      $(pa11y --version 2>/dev/null || echo '?')"
  echo "chromium:   $(chrome_version)"
  echo "article:    ${ART:-none}"; } | tee "$OUT/versions.txt"

# A non-zero exit is tolerated ONLY if the report was written: on Windows chrome-launcher
# fails to delete its temp profile (EPERM) *after* a successful audit, and under `set -e`
# that aborted the whole script before pa11y ever ran — so the WCAG check silently never
# happened there. A missing or empty report stays a hard failure; stderr goes to a log
# instead of /dev/null so a real error is still readable.
lh () {  # $1=url  $2=label
  rm -f "$OUT/lh-$2.json"
  lighthouse "$1" --quiet --output=json --output-path="$OUT/lh-$2.json" \
    --only-categories=performance,accessibility,best-practices,seo \
    --chrome-flags="$FLAGS" --form-factor=mobile --screenEmulation.mobile \
    >/dev/null 2>"$OUT/lh-$2.stderr.log" || true
  [ -s "$OUT/lh-$2.json" ] || { echo "!! lighthouse wrote no report for $2 ($1) — see $OUT/lh-$2.stderr.log"; exit 1; }
  node -e 'const r=require(process.argv[1]);console.log(process.argv[2].padEnd(10),
    Object.entries(r.categories).map(([k,v])=>k[0].toUpperCase()+k.slice(1,4)+" "+Math.round(v.score*100)).join("  "))' \
    "$OUT/lh-$2.json" "$2"
}

echo ">> Lighthouse (mobile)  [Perf / Acce / Best / Seo]"
lh "http://localhost:$PORT/" home
[ -n "$ART" ] && lh "http://localhost:$PORT$ART" article

echo ">> pa11y (WCAG2AA) home"
# pa11y drives Chrome through puppeteer, i.e. node — which does not understand the MSYS
# path bash hands it ("Browser was not found at the configured executablePath
# /c/Program Files/..."). cygpath -m produces C:/Program Files/..., valid for node and
# safe inside JSON (forward slashes, nothing to escape). No-op off Windows.
CHROME_FOR_NODE="$(cygpath -m "$CHROME_PATH" 2>/dev/null || printf '%s' "$CHROME_PATH")"
cat > "$OUT/pa11y.json" <<JSON
{ "chromeLaunchConfig": { "executablePath": "$CHROME_FOR_NODE", "args": ["--no-sandbox","--disable-dev-shm-usage"] } }
JSON
pa11y --config "$OUT/pa11y.json" --standard WCAG2AA --reporter csv \
  "http://localhost:$PORT/" > "$OUT/pa11y-home.csv" 2>"$OUT/pa11y.stderr.log" || true
# An empty CSV means pa11y never ran: the old `wc -l - 1` turned that into "-1 errors",
# a fabricated number where a failure belonged. Zero errors still writes a header row.
[ -s "$OUT/pa11y-home.csv" ] || { echo "!! pa11y produced no output — see $OUT/pa11y.stderr.log"; exit 1; }
ERRS=$(( $(wc -l < "$OUT/pa11y-home.csv") - 1 ))
echo "   WCAG2AA errors on home: ${ERRS} (detail: $OUT/pa11y-home.csv)"

echo ">> done. JSON reports in $OUT/"
