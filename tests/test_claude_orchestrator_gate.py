"""Tests for the optional Claude Code publication gate."""
from __future__ import annotations

import pytest

from generator import main
from generator.claude_orchestrator import ClaudeValidationResult


def _result(verdict="approve", status="success"):
    return ClaudeValidationResult(
        status=status,
        verdict=verdict,
        issues=() if verdict == "approve" else ("candidate invalid",),
        next_action="publish" if verdict == "approve" else "defer_batch",
        evidence=("test evidence",),
    )


def test_claude_gate_is_off_by_default(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_VALIDATE", raising=False)
    called = []
    monkeypatch.setattr(main.ClaudeCodeValidator, "validate_batch", lambda self, manifest: called.append(manifest))
    stats = {"new": 0}
    assert main._claude_validate(stats, []) is None
    assert called == []
    assert "claude_validation" not in stats


def test_claude_gate_report_mode_records_but_does_not_block(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_VALIDATE", "report")
    monkeypatch.setattr(main.ClaudeCodeValidator, "validate_batch", lambda self, manifest: _result("defer"))
    stats = {"new": 1}
    verdict = main._claude_validate(stats, [{"url": "https://example.test/a", "title": "A", "model": "B"}])
    assert verdict["verdict"] == "defer"
    assert stats["claude_validation"]["status"] == "success"


def test_claude_gate_required_blocks_non_approval(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_VALIDATE", "required")
    monkeypatch.setattr(main.ClaudeCodeValidator, "validate_batch", lambda self, manifest: _result("defer"))
    with pytest.raises(RuntimeError, match="publicarea a fost blocată"):
        main._claude_validate({"new": 1}, [])


def test_claude_gate_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_VALIDATE", "maybe")
    with pytest.raises(ValueError, match="off, report sau required"):
        main._claude_validate({}, [])
