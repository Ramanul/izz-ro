"""Contract tests for agent roles and the optional Claude Code validator."""
from __future__ import annotations

import json

from generator.agents import get_agent, list_agents, validate_profiles
from generator.claude_orchestrator import ClaudeCodeValidator


def test_all_agent_profiles_have_bounded_contracts():
    assert validate_profiles() == []
    assert "claude_orchestrator" in list_agents()
    assert "gemini_editor" in list_agents()
    assert "mistral_verifier" in list_agents()
    assert "groq_triage" in list_agents()
    assert get_agent("claude_orchestrator").allowed_tools


def test_unknown_agent_fails_loudly():
    try:
        get_agent("unbounded-agent")
    except ValueError as exc:
        assert "agent necunoscut" in str(exc)
    else:
        raise AssertionError("unknown agent must not be silently accepted")


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
    assert "--allowed-tools" in calls["command"]
    allowed = calls["command"][calls["command"].index("--allowed-tools") + 1]
    assert "Edit" not in allowed
    assert "git push" not in allowed
    assert calls["kwargs"]["timeout"] == 7


def test_claude_validator_schema_is_closed():
    schema = ClaudeCodeValidator._schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"verdict", "issues", "next_action", "evidence"}
