#!/usr/bin/env python3
"""Sincronizeaza automat sectiunea ## Open din STATE.md cu istoricul git."""
import re
import subprocess
from pathlib import Path

def find_state_file() -> Path | None:
    # 1. Cauta in radacina sau locatii standard
    for p in [Path("STATE.md"), Path("specs/STATE.md"), Path("docs/STATE.md")]:
        if p.exists():
            return p
    # 2. Cauta recursiv in repo (excluzand directoarele ascunse)
    for p in Path(".").rglob("*.md"):
        if p.name.lower() == "state.md" and ".git" not in p.parts:
            return p
    return None

def get_merged_prs() -> set[str]:
    cmd = ["git", "log", "--merges", "--oneline", "-n", "300"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return set(re.findall(r"#(\d+)", res.stdout))

def reconcile():
    state_file = find_state_file()
    if not state_file:
        print("⚠️  STATE.md nu a fost gasit pe acest branch. Treci pe main sau pe branch-ul cu PR-ul.")
        return False

    content = state_file.read_text(encoding="utf-8")
    merged_prs = get_merged_prs()

    lines = content.splitlines()
    new_lines = []
    in_open = False
    modified = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Open"):
            in_open = True
            new_lines.append(line)
            continue
        elif stripped.startswith("## ") and in_open:
            in_open = False

        if in_open and stripped.startswith("- "):
            match = re.search(r"#(\d+)", line)
            if match:
                pr = match.group(1)
                if pr in merged_prs and "merged" not in line.lower():
                    line = f"{line.rstrip()} (merged)"
                    modified = True

        new_lines.append(line)

    if modified:
        state_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"✅ {state_file}: PR-urile merge-uite au primit adnotarea (merged).")
    else:
        print(f"ℹ️  {state_file} este deja sincronizat.")
    return modified

if __name__ == "__main__":
    reconcile()
