"""Contract tests for the optional Claude Code validator.

Cele doua teste de profiluri de agenti au fost sterse odata cu `generator/agents.py`
(2026-09-03): modulul era schelet declarativ, fara niciun apelant in productie, iar
testele erau singurul lucru care il tinea in viata. Rutarea AI reala e `CascadeProvider`
din `process.get_provider()`; validatorul de mai jos ramane, fiindca `main.py:20` chiar
il importa. Urma deciziei: `IZZ-0284`.
"""
from __future__ import annotations

import json

from generator.claude_orchestrator import ClaudeCodeValidator


def test_claude_validator_accepts_existing_absolute_executable(tmp_path, monkeypatch):
    executable = tmp_path / "claude.exe"
    executable.write_text("stub", encoding="utf-8")
    monkeypatch.setattr("generator.claude_orchestrator.shutil.which", lambda _: None)
    assert ClaudeCodeValidator(executable=str(executable)).available() is True


def test_claude_validator_degrades_safely_when_cli_is_missing(monkeypatch):
    validator = ClaudeCodeValidator(executable="definitely-not-installed-izz-claude")
    result = validator.validate_batch({"run_id": "test", "status": "success"})
    assert result.status == "unavailable"
    assert result.verdict == "defer"
    assert result.next_action == "deterministic_only"


def test_claude_validator_uses_read_only_contract(monkeypatch):
    calls = {}

    class Completed:
        returncode = 0
        stderr = ""
        stdout = json.dumps(
            {
                "structured_output": {
                    "verdict": "approve",
                    "issues": [],
                    "next_action": "publish_after_deterministic_guards",
                    "evidence": ["tests passed"],
                }
            }
        )

    monkeypatch.setattr("generator.claude_orchestrator.shutil.which", lambda _: "/usr/bin/claude")

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr("generator.claude_orchestrator.subprocess.run", fake_run)
    result = ClaudeCodeValidator(timeout_seconds=7).validate_batch({"run_id": "test"})

    assert result.accepted is True
    assert "--safe-mode" in calls["command"]
    assert "--system-prompt" in calls["command"]
    assert calls["command"][calls["command"].index("--permission-mode") + 1] == "dontAsk"
    assert "--allowed-tools" not in calls["command"]
    assert calls["kwargs"]["timeout"] == 7


def test_claude_validator_schema_is_closed():
    schema = ClaudeCodeValidator._schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"verdict", "issues", "next_action", "evidence"}
