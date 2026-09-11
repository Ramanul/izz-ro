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


# --- Bash: inchiderea bypass-ului de scriere prin comenzi (2026-09-05) ------------

def test_bash_redirect_spre_control_plane_e_respins():
    comenzi = [
        "echo 'x' > moderation.yaml",
        "cat fals.yaml >> data/articles.json",
        "echo '{}' | tee wrangler.jsonc",
        "sed -i 's/a/b/' moderation.yaml",
        "cp alfa.yaml data/articles.json",
        "rm data/feed_cache.json",
        "python -c \"import json; json.dump({}, open('data/articles.json','w'))\"",
        "python -c \"from pathlib import Path; Path('moderation.yaml').write_text('x')\"",
        "echo x > .github/workflows/build.yml",
    ]
    for comanda in comenzi:
        payload = {"tool_name": "Bash", "tool_input": {"command": comanda}}
        assert _run(payload) != 0, comanda


def test_bash_citiri_si_pipeline_continua_permise():
    permise = [
        "cat moderation.yaml",
        "python -m generator.main",
        "python -m generator.main --dry-run",
        "git add data/articles.json",
        "git diff data/articles.json | wc -l",
        "python tools/grounding_gate.py",
        "python -c \"import json; print(json.load(open('data/articles.json'))['meta'])\"",
    ]
    for comanda in permise:
        payload = {"tool_name": "Bash", "tool_input": {"command": comanda}}
        assert _run(payload) == 0, comanda


# --- Redirecturi care nu pot scrie un fisier cu nume (2026-09-11) -----------------
#
# Falsul pozitiv masurat: `2>&1` contine un `>`, deci orice CITIRE care mentiona o cale
# protejata era refuzata. Trei din primele sase comenzi ale sesiunii de audit, toate
# read-only. Testele de mai jos fixeaza si granita: garda ramane la fel de stricta pe
# scrierile reale, inclusiv cand ele stau langa un redirect inofensiv.

def test_bash_citire_cu_redirect_de_descriptor_e_permisa():
    permise = [
        "ls .github/workflows/ 2>&1",
        "cat moderation.yaml 2>&1 | head -5",
        "grep -n cron .github/workflows/build.yml 2>/dev/null",
        "sed -n '1,20p' .github/workflows/tests.yml 2>&1",
        "python -c \"print(1)\" >&2",
        "git diff data/articles.json &>/dev/null",
        "wc -l wrangler.jsonc 2>&-",
    ]
    for comanda in permise:
        payload = {"tool_name": "Bash", "tool_input": {"command": comanda}}
        assert _run(payload) == 0, comanda


def test_scrierea_reala_ramane_refuzata_langa_un_redirect_inofensiv():
    """Granita: stergerea redirectului inofensiv nu are voie sa deschida o ocolire."""
    comenzi = [
        "echo x >&2 > moderation.yaml",
        "echo x 2>/dev/null > data/articles.json",
        "sed -i 's/a/b/' moderation.yaml 2>&1",
        "cp alfa.yaml data/articles.json 2>/dev/null",
        "cat x > .github/workflows/build.yml 2>&1",
        "echo x >> wrangler.jsonc &>/dev/null",
    ]
    for comanda in comenzi:
        payload = {"tool_name": "Bash", "tool_input": {"command": comanda}}
        assert _run(payload) != 0, comanda


def test_dev_null_nu_e_prefix_pentru_alt_fisier():
    """`>/dev/nullx` e o scriere intr-un fisier oarecare, nu dispozitivul nul."""
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "echo x >/dev/nullx && cat moderation.yaml"},
    }
    assert _run(payload) != 0
