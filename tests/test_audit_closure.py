from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_no_retired_origin_or_issue_channel_in_control_plane():
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    build = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    harta = (ROOT / ".github/workflows/harta-smoke.yml").read_text(encoding="utf-8")
    log_slice = (ROOT / "tools/log_slice.py").read_text(encoding="utf-8")
    assert "izz-ro.pages.dev" not in claude
    assert "izz-ro.pages.dev" not in build
    assert "izz-ro.pages.dev" not in harta
    assert "issue #83" not in claude
    assert "issue #83" not in log_slice
    assert "handoff/" in claude


def test_destructive_git_commands_are_denied_for_claude():
    settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    denied = set(settings["permissions"]["deny"])
    for pattern in (
        "Bash(git restore:*)",
        "Bash(git checkout --:*)",
        "Bash(git stash:*)",
        "Bash(git clean:*)",
        "Bash(git reset:*)",
    ):
        assert pattern in denied


def test_session_start_derives_mandate_from_canonical_contract():
    hook = (ROOT / ".claude/hooks/session-start.sh").read_text(encoding="utf-8")
    assert "awk" in hook
    assert "CLAUDE.md" in hook
    assert 'echo "  1. Deschide tura cu un rand' not in hook


def test_build_quality_and_human_gates_run_before_content_commit():
    build = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    grounding = build.index("name: Grounding gate")
    qa = build.index("name: QA check (blocking, inainte de commit)")
    commit = build.index("name: Comite starea")
    assert grounding < qa < commit
    assert 'IZZ_REQUIRE_HUMAN_GATE: "true"' in build


def test_production_deploy_uses_release_manifest_probe():
    deploy = (ROOT / ".github/workflows/deploy-worker.yml").read_text(encoding="utf-8")
    assert "tools/verify_release.py" in deploy
    assert "EXPECTED_COMMIT: ${{ github.sha }}" in deploy
    assert "workers.dev" in deploy
    assert "[ \"$code\" = \"200\" ]" not in deploy


def test_release_probe_points_to_workers_fallback():
    build = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    assert "izz-ro.andifreelancer2.workers.dev" in build


def test_feedcheck_is_scheduled_and_read_only():
    feedcheck = (ROOT / ".github/workflows/feedcheck.yml").read_text(encoding="utf-8")
    assert "schedule:" in feedcheck
    assert "contents: read" in feedcheck
    assert "permissions:\n  contents: write" not in feedcheck


def test_pr_checks_cover_all_surfaces():
    tests = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    pull_block = tests.split("  push:\n", 1)[0]
    assert "pull_request:" in pull_block
    assert "paths:" not in pull_block


def test_recovery_drill_is_non_destructive_by_default():
    recovery = (ROOT / ".github/workflows/recovery-drill.yml").read_text(encoding="utf-8")
    assert 'default: "check"' in recovery
    assert "if: inputs.action == 'rollback'" in recovery
    assert "wrangler@4.125.0 rollback" in recovery
    assert "python tools/arhiva.py --stats" in recovery


def test_protected_edit_guard_covers_deploy_control_plane():
    hook = (ROOT / ".claude/hooks/deny_protected_edits.py").read_text(encoding="utf-8")
    assert "wrangler.jsonc" in hook
    assert 'os.path.join(root, ".github", "workflows")' in hook
    assert "settings.json" in hook


def test_grounding_gate_blocks_deterministic_violation(tmp_path):
    report = tmp_path / "gate.jsonl"
    report.write_text(json.dumps({
        "blocking_issues": [{"cod": "citat_inventat", "detaliu": "quote"}],
        "advisory_issues": [],
    }) + "\n", encoding="utf-8")
    env = dict(os.environ)
    env["IZZ_RAPORT_COPIERE_GATE"] = str(report)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/grounding_gate.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "BLOCK" in proc.stdout


def test_grounding_gate_fails_closed_when_evidence_is_malformed(tmp_path):
    report = tmp_path / "gate.jsonl"
    report.write_text("[]\n", encoding="utf-8")
    env = dict(os.environ)
    env["IZZ_RAPORT_COPIERE_GATE"] = str(report)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/grounding_gate.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1


def test_grounding_report_writer_failure_is_not_silent(monkeypatch, tmp_path):
    from generator import raport_copiere

    gate = tmp_path / "gate.jsonl"
    monkeypatch.setenv("IZZ_RAPORT_COPIERE_GATE", str(gate))
    monkeypatch.setattr(
        raport_copiere,
        "suprapunere_sursa",
        lambda *_: type("Score", (), {"procent": 0, "max_cuvinte": 0, "fragment": ""})(),
    )
    monkeypatch.setattr(raport_copiere, "verifica", lambda *_: [])

    def fail_write(path, row):
        if path == gate:
            raise OSError("gate path read-only")
        return None

    monkeypatch.setattr(raport_copiere, "_scrie_jsonl", fail_write)
    with pytest.raises(OSError, match="gate path read-only"):
        raport_copiere.noteaza("B", "id", "Titlu", "Rezumat", "Sursa")
