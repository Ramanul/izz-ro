from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude" / "hooks" / "deny_protected_edits.py"


def _run(payload: dict) -> int:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(ROOT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
    ).returncode


def test_protected_file_edit_is_denied():
    for path in (
        "moderation.yaml",
        "data/articles.json",
        ".github/workflows/build.yml",
        ".github/workflows/tests.yml",
        "wrangler.jsonc",
        ".claude/settings.json",
    ):
        payload = {"tool_name": "Edit", "tool_input": {"file_path": path}}
        assert _run(payload) != 0, path


def test_regular_file_edit_is_allowed():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "generator/process.py"}}
    assert _run(payload) == 0


def test_missing_path_fails_closed():
    payload = {"tool_name": "Write", "tool_input": {}}
    assert _run(payload) != 0


def test_non_edit_tool_is_not_blocked_by_file_guard():
    payload = {"tool_name": "Read", "tool_input": {"file_path": "wrangler.jsonc"}}
    assert _run(payload) == 0


# --- Bash: inchiderea bypass-ului de scriere prin comenzi (2026-09-05) ------------

def test_bash_redirect_spre_control_plane_e_respins():
    comenzi = [
        "echo 'x' > moderation.yaml",
        "cat fals.yaml >> data/articles.json",
        "echo '{}' | tee wrangler.jsonc",
        "sed -i 's/a/b/' moderation.yaml",
        "cp alfa.yaml data/articles.json",
        "rm data/feed_cache.json",
        "python -c \"import json; json.dump({}, open('data/articles.json','w'))\"",
        "python -c \"from pathlib import Path; Path('moderation.yaml').write_text('x')\"",
        "echo x > .github/workflows/build.yml",
    ]
    for comanda in comenzi:
        payload = {"tool_name": "Bash", "tool_input": {"command": comanda}}
        assert _run(payload) != 0, comanda


def test_bash_citiri_si_pipeline_continua_permise():
    permise = [
        "cat moderation.yaml",
        "python -m generator.main",
        "python -m generator.main --dry-run",
        "git add data/articles.json",
        "git diff data/articles.json | wc -l",
        "python tools/grounding_gate.py",
        "python -c \"import json; print(json.load(open('data/articles.json'))['meta'])\"",
    ]
    for comanda in permise:
        payload = {"tool_name": "Bash", "tool_input": {"command": comanda}}
        assert _run(payload) == 0, comanda
