from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _run(root: Path, payload: dict) -> int:
    script = root / ".claude" / "hooks" / "deny-protected-edits.py"
    return subprocess.run(
        ["python", str(script), str(root)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    ).returncode


def test_protected_file_edit_is_denied(tmp_path):
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "moderation.yaml"}}
    assert _run(Path(tmp_path), payload) != 0


def test_regular_file_edit_is_allowed(tmp_path):
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "generator/process.py"}}
    assert _run(Path(tmp_path), payload) == 0


def test_missing_path_fails_closed(tmp_path):
    payload = {"tool_name": "Write", "tool_input": {}}
    assert _run(Path(tmp_path), payload) != 0
