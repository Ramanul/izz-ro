"""Optional local Claude Code orchestration and validation bridge.

This module never falls back to an API key implicitly.  It uses the locally
authenticated Claude Code CLI when available; otherwise it returns an explicit
unavailable result so the deterministic pipeline can continue or defer safely.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClaudeValidationResult:
    status: str
    verdict: str
    issues: tuple[str, ...] = ()
    next_action: str = ""
    evidence: tuple[str, ...] = ()
    raw: dict[str, Any] | None = None

    @property
    def accepted(self) -> bool:
        return self.status == "success" and self.verdict == "approve"


class ClaudeCodeValidator:
    """Run Claude Code locally as a bounded, read-only batch validator."""

    def __init__(
        self,
        executable: str | None = None,
        timeout_seconds: float | None = None,
        cwd: str | None = None,
    ) -> None:
        self.executable = executable or os.getenv("CLAUDE_CODE_BIN", "claude")
        self.timeout_seconds = timeout_seconds or float(os.getenv("CLAUDE_CODE_TIMEOUT", "120"))
        self.cwd = cwd

    def available(self) -> bool:
        # ``shutil.which`` can fail for an explicitly supplied absolute Windows
        # path even when the executable is present. Prefer an exact file check
        # for paths, then fall back to PATH lookup for bare command names.
        if Path(self.executable).is_file():
            return True
        return shutil.which(self.executable) is not None

    def validate_batch(self, manifest: dict[str, Any]) -> ClaudeValidationResult:
        """Validate a completed batch without granting edit, commit, or push tools."""
        if not self.available():
            return ClaudeValidationResult(
                status="unavailable",
                verdict="defer",
                next_action="deterministic_only",
                evidence=("Claude Code CLI indisponibil în mediul curent",),
            )

        prompt = self._prompt(manifest)
        schema = json.dumps(self._schema(), ensure_ascii=False, separators=(",", ":"))
        # The validator receives a self-contained manifest and needs no repository
        # access. ``--safe-mode`` keeps the user's Claude subscription login while
        # skipping CLAUDE.md, MCP servers, hooks, plugins, skills, auto-memory and
        # project settings. A small replacement prompt plus ``dontAsk`` makes this
        # a deterministic JSON-only validation call rather than a coding session.
        command = [
            self.executable,
            "--safe-mode",
            "--system-prompt",
            "Ești un validator JSON read-only. Analizezi exclusiv manifestul primit. "
            "Nu folosi instrumente, nu edita fișiere, nu cere secrete și nu explica "
            "în afara schemei JSON solicitate.",
            "--permission-mode",
            "dontAsk",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--json-schema",
            schema,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ClaudeValidationResult(
                status="timeout",
                verdict="defer",
                next_action="defer_batch",
                evidence=(f"Claude Code a depășit {self.timeout_seconds:.0f}s",),
            )
        except OSError as exc:
            return ClaudeValidationResult(
                status="error",
                verdict="defer",
                next_action="deterministic_only",
                evidence=(f"pornire Claude Code eșuată: {type(exc).__name__}",),
            )

        payload = self._parse_payload(completed.stdout)
        if completed.returncode != 0 or payload is None:
            detail = completed.stderr.strip() or completed.stdout.strip() or "fără detalii"
            return ClaudeValidationResult(
                status="error",
                verdict="defer",
                next_action="defer_batch",
                evidence=(detail[-500:],),
            )
        structured = payload.get("structured_output", payload)
        return ClaudeValidationResult(
            status="success",
            verdict=str(structured.get("verdict", "defer")).lower(),
            issues=tuple(str(item) for item in structured.get("issues", [])),
            next_action=str(structured.get("next_action", "")),
            evidence=tuple(str(item) for item in structured.get("evidence", [])),
            raw=payload,
        )

    @staticmethod
    def _prompt(manifest: dict[str, Any]) -> str:
        safe_manifest = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
        return (
            "Ești validatorul read-only al workflowului IZZ.ro. "
            "Analizează manifestul de batch de mai jos și aprobă numai dacă testele, "
            "guardurile și outputul sunt coerente. Nu edita, nu comite, nu face push și "
            "nu cere sau afișa secrete. Returnează exclusiv schema JSON cerută.\n\n"
            f"MANIFEST:\n{safe_manifest}"
        )

    @staticmethod
    def _schema() -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["approve", "defer"]},
                "issues": {"type": "array", "items": {"type": "string"}},
                "next_action": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["verdict", "issues", "next_action", "evidence"],
            "additionalProperties": False,
        }

    @staticmethod
    def _parse_payload(stdout: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
