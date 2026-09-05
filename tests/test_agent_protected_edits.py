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
