"""Cablajul hook-urilor trebuie sa existe pe disc, nu doar in `.claude/settings.json`.

DE CE EXISTA (2026-09-06). `.claude/hooks/deny-protected-edits.sh` chema
`deny-protected-edits.py` (cratime), dar fisierul comis in repo e `deny_protected_edits.py`
(underscore, ca `reguli_l1.py`). `exec python3 <fisier inexistent>` iese cu 2, iar un hook
PreToolUse care iese cu 2 BLOCHEAZA unealta -- deci matcher-ul `Edit|Write|Bash` a refuzat
absolut orice comanda dintr-o sesiune de agent, nu doar scrierile pe caile protejate.
Masurat in aceeasi zi: patru apeluri consecutive (Bash, Write) au picat toate cu
"can't open file '.../deny-protected-edits.py'", deci sesiunea a ramas fara scriere locala.

DE CE N-A PRINS-O NIMIC. `tests.yml` ruleaza pytest, iar pytest nu cheama niciodata
hook-urile PreToolUse; `tests/test_reguli.py` chiar RULEAZA `session-start.sh`, dar numai pe
el. Defectul era vizibil doar dintr-o sesiune interactiva, adica exact acolo unde nu ruleaza
nicio garda. Stratul ales e tot `tests/`, din acelasi motiv ca in `test_reguli.py`: e singurul
care ruleaza pe ORICE masina, la fiecare PR.

CE NU ACOPERA, spus explicit: se verifica doar caile scrise LITERAL. Un nume construit la
rulare (`"$dir/$nume.py"`) nu se poate rezolva static, si nici faptul ca scriptul chemat face
ce pretinde. Garda asta raspunde la o singura intrebare: exista fisierul pe care il cheama?
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"

# Citarea unui fisier din .claude/hooks/, indiferent de prefix ($ROOT, $CLAUDE_PROJECT_DIR).
REFERINTA = re.compile(r"\.claude/hooks/([A-Za-z0-9._-]+\.(?:py|sh))")


def referinte(text: str) -> list[str]:
    """Numele de fisiere din `.claude/hooks/` citate literal in text."""
    return REFERINTA.findall(text)


def incalcari_cablaj(surse: dict[str, str], existente: set[str]) -> list[str]:
    """Referintele fara corespondent pe disc. Functie pura: intrarile sunt date, nu citite."""
    return [f"{nume} cheama {tinta}, care nu exista in .claude/hooks/"
            for nume, text in sorted(surse.items())
            for tinta in referinte(text)
            if tinta not in existente]


def _fisiere_din_hooks() -> set[str]:
    return {cale.name for cale in HOOKS.iterdir() if cale.is_file()}


def test_fiecare_wrapper_cheama_un_fisier_care_exista():
    surse = {cale.name: cale.read_text(encoding="utf-8") for cale in sorted(HOOKS.glob("*.sh"))}
    assert surse, "nu s-a gasit niciun wrapper .sh in .claude/hooks/"
    assert incalcari_cablaj(surse, _fisiere_din_hooks()) == []


def test_settings_json_nu_trimite_la_un_hook_inexistent():
    settings = (ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert incalcari_cablaj({"settings.json": settings}, _fisiere_din_hooks()) == []


def test_garda_prinde_numele_gresit():
    """Testul negativ: exact regresia din 2026-09-06 (cratime in loc de underscore)."""
    stricat = {"deny-protected-edits.sh":
               'exec "$c" "$ROOT/.claude/hooks/deny-protected-edits.py" "$ROOT"'}
    incalcari = incalcari_cablaj(stricat, {"deny_protected_edits.py"})
    assert len(incalcari) == 1
    assert "deny-protected-edits.py" in incalcari[0]
