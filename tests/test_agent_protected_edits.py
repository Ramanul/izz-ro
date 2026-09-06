"""Ce blocheaza garda de control-plane -- comportamentul, nu doar cablajul.

Cablajul (exista fisierul pe care il cheama wrapperul?) e treaba lui `test_hooks_cablaj.py`,
scris dupa regresia `IZZ-0309`. Aici se verifica CE respinge garda, fiindca una cablata
corect si care nu blocheaza nimic arata identic din exterior: ambele trec, iar `STATE.md`
continua sa scrie ca scrierile Bash sunt pazite.

Masurat pe 2026-09-06 pe 14 tipare de scriere: patru treceau (`IZZ-0319`). Doua erau pe
traiectoria muncii normale a unui agent si s-au inchis -- `cd` in directorul parinte urmat de
redirect pe numele scurt, si modul append (`open(cale, 'a')`), pe care lista de moduri `'w'`
il rata. Doua cer expansiune de shell si RAMAN deschise prin design; sunt testate ca atare
mai jos, cu `xfail(strict=True)`, ca sa nu imbatraneasca documentatia in tacere.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


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
        # Numele scurt dupa `cd`: tokenul era calea cu prefix de director, deci scapa.
        "cd .claude && echo x > settings.json",
        "cd .github/workflows && sed -i 's/a/b/' build.yml",
        # Modul append strica un JSON de configurare la fel de bine ca o rescriere.
        "python -c \"open('.claude/settings.json','a').write('x')\"",
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


# --- limitele declarate ale garzii (2026-09-06) -----------------------------------

def _garda():
    """Modulul garzii, pentru verificarile care nu au nevoie de un subproces intreg."""
    spec = importlib.util.spec_from_file_location("deny_protected_edits", SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.mark.parametrize("comanda", [
    "echo x > .claude/sett\\ings.json",
    "echo x > .claude/sett*.json",
])
@pytest.mark.xfail(strict=True, reason="cere expansiune de shell; limita declarata a garzii")
def test_ocolirile_prin_expansiune_raman_deschise(comanda: str):
    """Backslash inserat in nume si glob trec, si asta e o decizie, nu o scapare.

    Garda e potrivire de subsir pe textul comenzii, nu parser de shell (vezi antetul din
    `deny_protected_edits.py`); modelul ei de amenintare e agentul care GRESESTE, nu cel
    care vrea sa treaca de ea -- acela are oricum forme nelimitate. `strict=True`: daca
    cineva chiar le inchide, testul da XPASS si obliga la actualizarea acestui text.
    """
    payload = {"tool_name": "Bash", "tool_input": {"command": comanda}}
    assert _run(payload) != 0


def test_niciun_token_nu_e_prins_doar_cu_prefix_de_director():
    """Invariantul din spatele bypass-ului `cd .claude`, nu inca un caz punctual.

    Pentru fiecare cale protejata, numele ei de baza trebuie sa fie el insusi prins; altfel
    un `cd` in directorul parinte deschide o poarta. `.github/workflows` e exceptia legitima:
    e un director, iar cazul lui e acoperit explicit in lista de mai sus.
    """
    garda = _garda()
    scapari = [token for token in garda.PROTECTED_TOKENS
               if "/" in token and not token.endswith("workflows")
               and garda._bash_scrie_control_plane(f"echo x > {token.rsplit('/', 1)[1]}") is None]
    assert scapari == [], f"tokeni prinsi doar cu prefix de director: {scapari}"
