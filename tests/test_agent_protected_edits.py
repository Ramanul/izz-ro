from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude" / "hooks" / "deny-protected-edits.py"


def _run(payload: dict) -> int:
    return subprocess.run(
        ["python", str(SCRIPT), str(ROOT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    ).returncode


def test_protected_file_edit_is_denied():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "moderation.yaml"}}
    assert _run(payload) != 0


def test_regular_file_edit_is_allowed():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "generator/process.py"}}
    assert _run(payload) == 0


def test_missing_path_fails_closed():
    payload = {"tool_name": "Write", "tool_input": {}}
    assert _run(payload) != 0
