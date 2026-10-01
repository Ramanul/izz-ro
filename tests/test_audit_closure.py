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
    log_slice = (ROOT / "tools/log_slice.py").read_text(encoding="utf-8")
    assert "izz-ro.pages.dev" not in claude
    assert "issue #83" not in claude
    assert "issue #83" not in log_slice
    assert "handoff/" in claude


# --- gazde retrase: matura, nu enumera ----------------------------------------------
#
# DE CE S-A SCHIMBAT (2026-09-14). Versiunea de dinainte verifica TREI fisiere pe nume —
# `CLAUDE.md`, `build.yml`, `harta-smoke.yml` — si era verde. In acelasi timp, alte trei
# fisiere foloseau gazda RETRASA ca fallback efectiv, nu ca pomenire:
#
#     .github/workflows/visual.yml:60      BASE_URL: ... || 'https://izz-ro.pages.dev'
#     .github/workflows/monitor.yml:42     ALT_ORIGIN: ... || 'https://izz-ro.pages.dev'
#     .github/workflows/harta-data.yml:150 ALT_ORIGIN: ... || 'https://izz-ro.pages.dev'
#
# Deci garda nu ratase o schimbare noua: ratase jumatate din suprafata de la inceput. Exact
# forma lui IZZ-0379 (o trimitere verificata din paisprezece) si a lui IZZ-0371, consemnat
# `propus` pe 2026-09-12 si inca neinchis doua zile mai tarziu. O lista de fisiere scrisa de
# mana ramane in urma repo-ului; o matura nu.
#
# DE CE MONITORUL NU A SEMNALAT-O. `monitor.yml` da `crit=1` doar cand CAD AMANDOUA originile.
# Cu primarul pe un nume mort si mirror-ul viu, iesea `::warning::` si jobul ramanea VERDE —
# 953 de rulari fara nicio alarma. O redundanta care acopera un nume mort arata identic cu una
# sanatoasa.
#
# INVARIANTUL: gazda retrasa poate aparea in PROZA (istoric, note, o negatie explicita), dar
# nu in COD. Linia de comentariu e proza; linia care poarta o valoare, nu.
GAZDE_RETRASE = ("izz-ro.pages.dev",)

SUPRAFATA_OPERATIONALA = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "tools/*.py",
    "tools/*.sh",
    "generator/*.py",
)


def _linii_de_cod_cu(text: str, ac: str) -> list[int]:
    """Numerele liniilor NECOMENTATE care contin `ac`.

    Comentariul se recunoaste pe primul caracter negol: `#` in YAML si in shell, `#` si in
    Python. Nu e un parser — si nu trebuie sa fie: un `#` la inceput de linie nu poate fi o
    valoare in niciuna dintre cele trei limbi maturate.
    """
    return [
        nr for nr, linie in enumerate(text.splitlines(), 1)
        if ac in linie and not linie.lstrip().startswith("#")
    ]


def test_nicio_gazda_retrasa_nu_e_folosita_ca_valoare():
    gasite = []
    for tipar in SUPRAFATA_OPERATIONALA:
        for cale in sorted(ROOT.glob(tipar)):
            text = cale.read_text(encoding="utf-8")
            for gazda in GAZDE_RETRASE:
                for nr in _linii_de_cod_cu(text, gazda):
                    gasite.append(f"{cale.relative_to(ROOT)}:{nr} -> {gazda}")
    assert not gasite, (
        "gazda RETRASA folosita ca valoare, nu doar pomenita:\n  " + "\n  ".join(gasite)
        + "\nFallback-ul corect e originea Worker. O pomenire in comentariu sau in proza e "
        "permisa; o valoare, nu."
    )


def test_garda_gazdelor_distinge_valoarea_de_comentariu(tmp_path, monkeypatch):
    """Proba in ambele directii: altfel garda ar fi ori oarba, ori de nefolosit."""
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "a.sh").write_text(
        "# fallback-ul vechi era izz-ro.pages.dev\nURL=https://exemplu.test\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)
    test_nicio_gazda_retrasa_nu_e_folosita_ca_valoare()  # comentariu: trece

    (tmp_path / "tools" / "b.sh").write_text(
        "URL=https://izz-ro.pages.dev\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="b.sh:1"):
        test_nicio_gazda_retrasa_nu_e_folosita_ca_valoare()


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
    # Poarta umana e COMUTATOR, nu starea permanenta: default false (flux neinghetat),
    # armabila din UI-ul GitHub (vars.IZZ_REQUIRE_HUMAN_GATE) fara atingere de cod.
    assert "IZZ_REQUIRE_HUMAN_GATE: ${{ vars.IZZ_REQUIRE_HUMAN_GATE || 'false' }}" in build


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


def test_protected_edit_guard_covers_bash_writes():
    settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    hook = (ROOT / ".claude/hooks/deny_protected_edits.py").read_text(encoding="utf-8")
    pre = settings["hooks"]["PreToolUse"][0]["matcher"]
    assert pre == "Edit|Write|Bash", f"PreToolUse matcher acopera doar {pre!r} — scrierile prin Bash ocolesc garda"
    assert "PROTECTED_TOKENS" in hook
    assert "def _bash_scrie_control_plane" in hook


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


def test_silence_detection_is_scheduled_and_alerts():
    tacere = (ROOT / ".github/workflows/detectie-tacere.yml").read_text(encoding="utf-8")
    assert "schedule:" in tacere
    assert "python tools/detectie_tacere.py" in tacere
    assert "issues: write" in tacere
    assert "if: failure()" in tacere
    tool = (ROOT / "tools/detectie_tacere.py").read_text(encoding="utf-8")
    for workflow in ("build.yml", "monitor.yml", "smoke.yml", "feedcheck.yml"):
        assert workflow in tool
    assert "data/articles.json" in tool
