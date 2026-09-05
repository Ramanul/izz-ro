from __future__ import annotations

import json
import os
import sys

# Subșiruri care identifică un fișier de control-plane într-o comandă oarecare.
# Match gros din construcție: e o gardă de conținut, nu un parser de shell —
# falsul blocant (comandă care doar menționează calea + un indicator de scriere)
# costă o decizie umană, falsul permis costă un fișier de control rescris.
PROTECTED_TOKENS = (
    "moderation.yaml",
    "articles.json",
    "feed_cache.json",
    "wrangler.jsonc",
    ".claude/settings.json",
    ".github/workflows",
)

# Indicatori de scriere în comenzi Bash: redirecturi, tee, editare in-place, ștergere,
# mutare/copiere, și descrieri de mod 'w' pentru uneltele python (open/write_text).
SCRITORI = (
    ">", ">>", "tee ", "sed -i", " rm ", " mv ", " cp ", "truncate ", " dd ",
    "'w'", '"w"', "write_text", "unlink(", "rmtree", "shutil",
)


def _bash_scrie_control_plane(command: str) -> str | None:
    """Tokenul protejat găsit într-o comandă cu indicator de scriere, sau None."""
    turnat = f" {command} "
    if not any(token in turnat for token in PROTECTED_TOKENS):
        return None
    gasit = next((token for token in PROTECTED_TOKENS if token in turnat), None)
    if any(indicator in turnat for indicator in SCRITORI):
        return gasit
    return None


def main() -> int:
    root = os.path.abspath(sys.argv[1])
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("DENY: PreToolUse input invalid; protected edit cannot be authorized.", file=sys.stderr)
        return 2

    tool_name = str(payload.get("tool_name") or payload.get("name") or "")
    if tool_name not in {"Edit", "Write", "Bash"}:
        return 0

    inputs = payload.get("tool_input") or payload.get("input") or {}

    if tool_name == "Bash":
        command = inputs.get("command") or ""
        if not isinstance(command, str) or not command.strip():
            print("DENY: Bash without resolvable command cannot be authorized.", file=sys.stderr)
            return 2
        token = _bash_scrie_control_plane(command)
        if token:
            print(
                "DENY: Bash command writing to protected control-plane path "
                f"({token}). Use an explicit, reviewed change instead.",
                file=sys.stderr,
            )
            return 2
        return 0

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
