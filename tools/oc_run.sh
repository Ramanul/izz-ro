#!/usr/bin/env bash
# oc_run.sh — run one OpenCode task, falling through the free-route ladder.
#
# Why this exists: the Zen free tier is ~100 requests/day. When it is spent,
# `opencode run` just fails and delegation stops until the next day. This walks
# the ladder configured in opencode.json until a route actually completes.
#
#   tools/oc_run.sh "Read AGENTS.md, then execute specs/foo.md ..."
#   tools/oc_run.sh --title my-task --dir . "prompt"
#   tools/oc_run.sh --list                 # show which routes are eligible now
#   OC_ROUTES="google/gemini-3.1-flash-lite,ollama/qwen3-coder:30b" tools/oc_run.sh "prompt"
#
# Exit 0 = a route completed. Exit 1 = every eligible route failed.
# Exit 2 = usage error.
#
# It falls through only on INFRASTRUCTURE failure (non-zero exit, or an
# `Error:` line from opencode itself — auth, quota, rate limit, no credit).
# A route that runs and reports the task went badly is NOT retried: that is a
# task problem, and burning four more providers on it would just cost quota.

set -uo pipefail

DIR="."
TITLE=""
PROMPT=""
LIST_ONLY=0

# Ladder order = cheapest-and-already-working first, then key-gated, then local.
# Verified by running each one, 2026-08-02 (see .claude/commands/delegate-opencode.md).
DEFAULT_ROUTES="opencode/deepseek-v4-flash-free,\
opencode/laguna-s-2.1-free,\
opencode/north-mini-code-free,\
mistral/codestral-latest,\
google/gemini-3.1-flash-lite,\
openrouter-free/poolside/laguna-s-2.1:free"
# NOT in the default ladder: cerebras/* and groq/*. Keys were created and tested
# 2026-08-02; both fail for structural reasons, not bad keys:
#   groq     — key valid, but the free tier caps tokens-per-minute at 8k (gpt-oss-120b)
#              / 12k (llama-3.3-70b). opencode's system prompt alone is 32–46k tokens,
#              so EVERY agentic call is rejected as "Request too large". No model on the
#              free tier has a high enough TPM; only a paid Dev Tier would fix it.
#   cerebras — key valid (it lists models), but every chat call returns
#              "payment_required". Cerebras is moving the free tier to a credit-based
#              plan that needs a card on file (announced for 2026-08-17). Its free tier
#              also caps context at 8k, which would fail the same way as groq anyway.
# Left wired in opencode.json so they work immediately on a paid plan; re-add here
# with OC_ROUTES if that ever happens. Do not re-diagnose them as "bad key".
# NOT in the default ladder: ollama/*. Measured 2026-08-02 on this machine —
# GTX 1060 3GB VRAM / 16GB RAM. A 7B coder model (4.7GB) does not fit in 3GB of
# VRAM, so it runs half on CPU and is far too slow to drive an agentic loop with
# tool calls. Wired in opencode.json and reachable on purpose:
#   OC_ROUTES="ollama/qwen2.5-coder:7b" tools/oc_run.sh "..."
# after `ollama pull qwen2.5-coder:7b`. Treat it as an offline last resort for a
# tiny task, not as a replacement executor.

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)   DIR="${2:-}"; shift 2 ;;
    --title) TITLE="${2:-}"; shift 2 ;;
    --list)  LIST_ONLY=1; shift ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
    *) PROMPT="$1"; shift ;;
  esac
done

if [ "$LIST_ONLY" -eq 0 ] && [ -z "$PROMPT" ]; then
  echo "oc_run.sh: no prompt given. Try --help." >&2
  exit 2
fi

# Which env var each provider needs. Empty = opencode's own stored auth, or local.
key_var_for() {
  case "$1" in
    # NOT GEMINI_API_KEY. Measured 2026-08-02: the free tier allows 15 requests
    # per MINUTE, and generator/providers/gemini.py sits exactly on that ceiling
    # (GEMINI_THROTTLE=4.0 -> 4s x 15 = 60s). An unthrottled opencode call on the
    # same key during a pipeline run pushes production over the limit, and with a
    # single key gemini.py has no second key to fail over to -> failed run.
    # So opencode needs its OWN key, from a DIFFERENT Google account (a second key
    # on the same account shares the quota and fixes nothing).
    google/*)          echo GEMINI_API_KEY_OC ;;
    cerebras/*)        echo CEREBRAS_API_KEY ;;
    groq/*)            echo GROQ_API_KEY ;;
    openrouter-free/*) echo OPENROUTER_API_KEY ;;
    mistral/*)         echo MISTRAL_API_KEY ;;
    *)                 echo "" ;;
  esac
}

# A route is eligible if its key exists (dormant providers are skipped silently
# rather than burning a slow failing call) and, for ollama, the daemon answers.
eligible() {
  local route="$1" kv
  kv="$(key_var_for "$route")"
  if [ -n "$kv" ] && [ -z "${!kv:-}" ]; then
    echo "  skip $route — \$$kv not set"
    return 1
  fi
  if [ "${route#ollama/}" != "$route" ] \
     && ! curl -sf -m 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "  skip $route — no ollama daemon on :11434"
    return 1
  fi
  return 0
}

IFS=',' read -r -a ROUTES <<< "${OC_ROUTES:-$DEFAULT_ROUTES}"

if [ "$LIST_ONLY" -eq 1 ]; then
  echo "Eligible routes, in order:"
  for r in "${ROUTES[@]}"; do
    [ -z "$r" ] && continue
    if out="$(eligible "$r")"; then echo "  use  $r"; else echo "$out"; fi
  done
  exit 0
fi

strip_ansi() { sed -r 's/\x1b\[[0-9;]*[A-Za-z]//g'; }

attempted=0
for route in "${ROUTES[@]}"; do
  [ -z "$route" ] && continue
  if ! skipmsg="$(eligible "$route")"; then
    echo "$skipmsg" >&2
    continue
  fi

  attempted=$((attempted + 1))
  echo "==> oc_run: trying $route" >&2

  set +e
  if [ -n "$TITLE" ]; then
    raw="$(opencode run --dir "$DIR" --title "$TITLE" -m "$route" "$PROMPT" 2>&1)"
  else
    raw="$(opencode run --dir "$DIR" -m "$route" "$PROMPT" 2>&1)"
  fi
  rc=$?
  set -e

  clean="$(printf '%s\n' "$raw" | strip_ansi)"
  printf '%s\n' "$clean"

  # opencode reports provider-level trouble as a line starting with "Error:".
  if [ "$rc" -eq 0 ] && ! printf '%s\n' "$clean" | grep -qE '^[[:space:]]*Error:'; then
    echo "==> oc_run: completed on $route" >&2
    exit 0
  fi

  echo "==> oc_run: $route failed (exit $rc), falling through" >&2
done

if [ "$attempted" -eq 0 ]; then
  echo "==> oc_run: no eligible route. Run --list to see why." >&2
else
  echo "==> oc_run: all $attempted eligible routes failed." >&2
fi
exit 1
