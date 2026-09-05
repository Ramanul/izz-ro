from __future__ import annotations

import json
import os
import sys


def main() -> int:
    root = os.path.abspath(sys.argv[1])
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("DENY: PreToolUse input invalid; protected edit cannot be authorized.", file=sys.stderr)
        return 2

    tool_name = str(payload.get("tool_name") or payload.get("name") or "")
    if tool_name not in {"Edit", "Write"}:
        return 0

    inputs = payload.get("tool_input") or payload.get("input") or {}
    path = inputs.get("file_path") or inputs.get("path") or ""
    if not isinstance(path, str) or not path.strip():
        print("DENY: protected edit has no resolvable file path.", file=sys.stderr)
        return 2

    candidate = os.path.abspath(os.path.join(root, path) if not os.path.isabs(path) else path)
    workflows = os.path.abspath(os.path.join(root, ".github", "workflows")) + os.sep
    protected_exact = {
        os.path.abspath(os.path.join(root, "moderation.yaml")),
        os.path.abspath(os.path.join(root, "data", "articles.json")),
        os.path.abspath(os.path.join(root, "data", "feed_cache.json")),
        os.path.abspath(os.path.join(root, "wrangler.jsonc")),
        os.path.abspath(os.path.join(root, ".claude", "settings.json")),
    }
    protected = candidate in protected_exact or candidate.startswith(workflows)
    if protected:
        print(
            "DENY: direct agent edit blocked for protected control-plane file: "
            f"{os.path.relpath(candidate, root)}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
