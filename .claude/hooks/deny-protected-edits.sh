#!/bin/bash
# PreToolUse guard: reject direct agent edits to critical control-plane/state files.
# Claude Code supplies the hook input as JSON on stdin. We intentionally fail CLOSED
# when the path cannot be parsed: an unknown edit is not permission to touch protected files.
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
python3 - "$ROOT" <<'PY'
import json
import os
import sys

root = os.path.abspath(sys.argv[1])
raw = sys.stdin.read()
try:
    payload = json.loads(raw)
except Exception:
    print("DENY: PreToolUse input invalid; protected edit cannot be authorized.", file=sys.stderr)
    raise SystemExit(2)

# Claude Code hook payloads have varied slightly across releases. Accept a small,
# explicit set of fields and refuse when an Edit/Write operation has no target path.
tool_name = str(payload.get("tool_name") or payload.get("name") or "")
if tool_name not in {"Edit", "Write"}:
    raise SystemExit(0)
inputs = payload.get("tool_input") or payload.get("input") or {}
path = inputs.get("file_path") or inputs.get("path") or ""
if not isinstance(path, str) or not path.strip():
    print("DENY: protected edit has no resolvable file path.", file=sys.stderr)
    raise SystemExit(2)

candidate = os.path.abspath(os.path.join(root, path) if not os.path.isabs(path) else path)
protected = {
    os.path.abspath(os.path.join(root, "moderation.yaml")),
    os.path.abspath(os.path.join(root, "data", "articles.json")),
    os.path.abspath(os.path.join(root, "data", "feed_cache.json")),
    os.path.abspath(os.path.join(root, ".github", "workflows", "build.yml")),
}
if candidate in protected:
    print(f"DENY: direct agent edit blocked for protected file: {os.path.relpath(candidate, root)}", file=sys.stderr)
    raise SystemExit(2)

raise SystemExit(0)
PY
