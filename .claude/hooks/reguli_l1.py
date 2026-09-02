#!/usr/bin/env python3
"""L1 — regulile conditionate ajung in context cand atingi fisierul, nu la fiecare tura.

DE CE EXISTA. `CLAUDE.md` se incarca INTEGRAL la fiecare tura, deci fiecare octet se
plateste de fiecare data. Pe 2026-08-30 fisierul era la 24.532 din 24.576 de octeti:
44 liberi, adica urmatoarea regula scrisa acolo pica garda. Taierea, singura supapa de
pana acum, a pierdut deja 13 reguli tacut (2026-08-06) si a costat o sesiune intreaga de
arheologie pe git ca sa fie gasite (#226).

Regulile nu au insa aceeasi frecventa. §13 (front-end) conteaza doar cand atingi
`templates/`, `static/styles.css` sau `render.py` — restul turelor o platesti degeaba.
Stratul L1 o livreaza EXACT atunci, o data pe sesiune.

CE S-A MASURAT, nu presupus (2026-08-30, sesiune web):
  · `PostToolUse` chiar ruleaza intr-o sesiune cloud — deci F4 nu era blocat la contul A,
    cum spunea predarea din 08-29. `SessionStart` rula deja acolo; nimeni nu verificase.
  · Hook-ul se incarca LA CALD: adaugat la mijlocul sesiunii, a rulat la urmatoarea unealta.
  · `hookSpecificOutput.additionalContext` ajunge la model **fara** sa apara ca eroare si
    fara sa blocheze unealta. `IZZ-0254` prescria `exit 2` + `stderr`; merge si asa, dar
    incadreaza fiecare atingere de fisier ca esec. Mecanismul ales e cel curat.

DE CE NU se muta in `.claude/agents/`: masurat si respins in `IZZ-0252` — `description`-ul
unui agent e in promptul de sistem la FIECARE tura (economie zero), iar corpul se incarca
doar la spawn, care e o decizie a modelului: zero rulari in sapte saptamani. Regula mutata
acolo ar disparea, nu s-ar declansa.

SUPRA-DECLANSAREA E ACCEPTATA (decizie proprietar 2026-08-29): bratul `Bash` e potrivire de
subsir pe textul comenzii, deci `ls templates/` aprinde §13 desi e o citire. Asimetria decide:
~1 KB risipit o data e mic, masurabil si reversibil; un filtru strict care rateaza felia care
chiar schimba front-end-ul costa o regula neaplicata, invizibila pana face paguba.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# id -> (fisierul cu regula, caile care o aprind)
CATALOG: dict[str, tuple[str, tuple[str, ...]]] = {
    "13-frontend": (
        "13-frontend.md",
        ("templates/", "static/styles.css", "generator/render.py"),
    ),
    # §18 e a doua regula mutata in L1 (2026-09-02). Declansatorul ei pe cale e cel mai clar
    # dintre sectiunile ramase — de-aia ea si nu §17, a carei situatie tipica („nu s-a publicat
    # nimic de 4 ore") nu atinge niciun fisier, deci un hook pe cale ar rata exact cazul propriu.
    "18-imagini": (
        "18-imagini.md",
        ("tools/fetch_leadphotos.py", "tools/fetch_portraits.py",
         "generator/photojudge.py", "media/", "data/leadphotos.json", "data/portraits.json"),
    ),
}

CAMP_CALE = ("file_path", "notebook_path", "path")


def tinta(payload: dict) -> str:
    """Ce a atins unealta: o cale (Edit/Write) sau textul comenzii (Bash). '' daca nu stim."""
    intrare = payload.get("tool_input") or {}
    if not isinstance(intrare, dict):
        return ""
    for camp in CAMP_CALE:
        val = intrare.get(camp)
        if isinstance(val, str) and val:
            return val.replace("\\", "/")
    val = intrare.get("command")
    return val.replace("\\", "/") if isinstance(val, str) else ""


def reguli_aprinse(tinta_text: str, catalog: dict = CATALOG) -> list[str]:
    """Id-urile regulilor pe care textul le declanseaza. Ordinea e stabila (sortata)."""
    if not tinta_text:
        return []
    return sorted(rid for rid, (_, cai) in catalog.items()
                  if any(cale in tinta_text for cale in cai))


def _marcaj(sesiune: str, rid: str) -> Path:
    sigur = "".join(c for c in sesiune if c.isalnum() or c in "-_")[:64] or "fara-sesiune"
    return Path(tempfile.gettempdir()) / "izz-reguli-l1" / sigur / rid


def deja_livrata(sesiune: str, rid: str) -> bool:
    """O regula se livreaza O SINGURA DATA pe sesiune. A doua oara e doar cost."""
    m = _marcaj(sesiune, rid)
    if m.exists():
        return True
    m.parent.mkdir(parents=True, exist_ok=True)
    m.touch()
    return False


def text_regula(radacina: Path, rid: str, catalog: dict = CATALOG) -> str:
    fisier, _ = catalog[rid]
    return (radacina / ".claude" / "reguli" / fisier).read_text(encoding="utf-8").strip()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # un hook care moare nu are voie sa rupa sesiunea
    try:
        radacina = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
        sesiune = str(payload.get("session_id") or "")
        bucati = [text_regula(radacina, rid)
                  for rid in reguli_aprinse(tinta(payload))
                  if not deja_livrata(sesiune, rid)]
        if not bucati:
            return 0
        antet = ("REGULA CONDITIONATA, livrata fiindca tocmai ai atins un fisier care o "
                 "declanseaza (stratul L1, .claude/reguli/). Se aplica ACUM:\n\n")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": antet + "\n\n".join(bucati),
        }}, ensure_ascii=False))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
