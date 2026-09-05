from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_contract_has_no_retired_origin_or_issue_channel():
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    build = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    log_slice = (ROOT / "tools/log_slice.py").read_text(encoding="utf-8")
    assert "izz-ro.pages.dev" not in claude
    assert "izz-ro.pages.dev" not in build
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
    assert 'awk' in hook
    assert 'CLAUDE.md' in hook
    assert "echo \"  1. Deschide tura cu un rand" not in hook


def test_build_quality_gate_runs_before_content_commit():
    build = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    qa = build.index("name: QA check (blocking, inainte de commit)")
    commit = build.index("name: Comite starea")
    grounding = build.index("name: Grounding gate")
    assert grounding < qa < commit


def test_release_probe_points_to_workers_fallback():
    build = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    assert "izz-ro.andifreelancer2.workers.dev" in build


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
