"""Gărzi de referință: o trimitere din fișierele de workflow nu are voie să ducă în gol.

DE CE EXISTĂ. Pe 2026-08-30 `.claude/agents/frontend-auditor.md` trimitea la
`CLAUDE.md §13 ("Current scores")` — un șir cu ZERO apariții în tot repo-ul. Baseline-ul se
mutase în `specs/masuratori-frontend.md` pe 2026-08-06. Fix-ul F1 din 2026-08-29 (`bf971776`)
a corectat `.claude/commands/audit.md` și a ratat fișierul de agent, fiindcă nimeni nu putea
vedea diferența fără să caute manual. Un agent care urmează instrucțiunea aia caută o secțiune
inexistentă și fie inventează un baseline, fie raportează fără delta — și niciuna nu se vede.

Testele astea sunt ieftine (citesc fișiere text) și prind clasa întreagă, nu incidentul.
"""
from __future__ import annotations

import re
from pathlib import Path

RADACINA = Path(__file__).resolve().parents[1]

SUFIXE = {".md", ".sh", ".py", ".json", ".toml"}


def _fisiere(*radacini: str) -> list[Path]:
    out: list[Path] = []
    for r in radacini:
        d = RADACINA / r
        if d.is_dir():
            out += [p for p in d.rglob("*") if p.is_file() and p.suffix in SUFIXE]
    return sorted(out)


# Fișierele care spun unei sesiuni ce să facă. O trimitere ruptă aici costă o felie.
FISIERE_WORKFLOW = _fisiere(".claude") + [
    RADACINA / n for n in ("CLAUDE.md", "AGENTS.md", "REVIEW.md", "REGULI-SINTEZA.md")
]

# Copiile portate pe alt CLI (#234). Aceleași trimiteri, aceeași cerință să rezolve — dar
# garda de fosile de mai jos NU le include: `.codex/README.md` discută deliberat fosila
# „Current scores" ca să spună de ce a fost reparată.
FISIERE_PORTATE = _fisiere(".codex", ".agents")

# Căi care trăiesc în repo-ul de workspace (`claude-desktop-workspace`), nu aici. CLAUDE.md §14
# le marchează explicit „din workspace" / „de acolo".
CAI_DIN_WORKSPACE = {"handoff/PROTOCOL.md", "handoff/to-A", "izz/specs/STATE.md"}


def _sectiuni_din_claude_md() -> set[str]:
    text = (RADACINA / "CLAUDE.md").read_text(encoding="utf-8")
    return set(re.findall(r"^## (\d+)\.", text, re.M)) | set(re.findall(r"^### (\d+[a-z])\.", text, re.M))


def _sectiuni_arhivate() -> set[str]:
    """Secțiuni scoase din CLAUDE.md dar păstrate în arhivă — o trimitere la ele e validă.

    Nu e o listă de excepții scrisă de mână: se citește din arhiva reală, deci dacă cineva
    șterge `## §9` de acolo, trimiterea din CLAUDE.md redevine ruptă și testul o spune.
    """
    arhiva = RADACINA / "specs" / "istoric-operational.md"
    if not arhiva.exists():
        return set()
    return set(re.findall(r"^## §(\d+[a-z]?)", arhiva.read_text(encoding="utf-8"), re.M))


def test_toate_trimiterile_de_sectiune_rezolva():
    """`§N` citat oriunde în workflow trebuie să existe ca secțiune în CLAUDE.md."""
    sectiuni = _sectiuni_din_claude_md() | _sectiuni_arhivate()
    rupte = []
    for p in FISIERE_WORKFLOW + FISIERE_PORTATE:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"§\s?(\d+(?:\.\d+)?[a-z]?)", text):
            ref = m.group(1)
            # §5.4 se validează pe §5; §12a pe §12a apoi pe §12.
            candidati = {ref, re.match(r"\d+[a-z]?", ref).group(), re.match(r"\d+", ref).group()}
            if not (candidati & sectiuni):
                rupte.append(f"{p.relative_to(RADACINA)}:{text[:m.start()].count(chr(10)) + 1} → §{ref}")
    assert not rupte, "Trimiteri § inexistente în CLAUDE.md și nearhivate:\n  " + "\n  ".join(rupte)


def test_caile_citate_exista():
    """Orice cale din repo citată între backtick-uri trebuie să existe pe disc."""
    tipar = re.compile(
        r"`([A-Za-z0-9_./-]*(?:specs|tools|generator|templates|static|content|data|infra|tests|"
        r"\.claude|\.github|handoff|sessions|notes)/[A-Za-z0-9_./-]+)`"
    )
    lipsa = []
    for p in FISIERE_WORKFLOW + FISIERE_PORTATE:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in tipar.finditer(text):
            ref = m.group(1).rstrip("/.,)")
            if ref in CAI_DIN_WORKSPACE or any(c in ref for c in "*<>"):
                continue
            if not (RADACINA / ref).exists():
                lipsa.append(f"{p.relative_to(RADACINA)}:{text[:m.start()].count(chr(10)) + 1} → {ref}")
    assert not lipsa, "Căi citate care nu există:\n  " + "\n  ".join(lipsa)


def test_indicatorul_de_baseline_e_adevarat():
    """Fosila care a motivat fișierul ăsta: baseline-ul front-end nu mai e în CLAUDE.md."""
    claude_md = (RADACINA / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Current scores" not in claude_md, (
        "'Current scores' a reapărut în CLAUDE.md — dacă baseline-ul chiar s-a mutat înapoi, "
        "actualizează și trimiterile din .claude/, apoi testul ăsta."
    )
    fosile = [
        str(p.relative_to(RADACINA))
        for p in FISIERE_WORKFLOW
        if p.exists() and "Current scores" in p.read_text(encoding="utf-8", errors="replace")
    ]
    assert not fosile, (
        "Fișiere care trimit încă la secțiunea 'Current scores', inexistentă: " + ", ".join(fosile)
    )
    masuratori = RADACINA / "specs" / "masuratori-frontend.md"
    assert masuratori.exists(), "specs/masuratori-frontend.md lipsește — trimiterile spre el sunt rupte"
    assert re.search(r"^## Baseline", masuratori.read_text(encoding="utf-8"), re.M), (
        "Secțiunea '## Baseline' a dispărut din specs/masuratori-frontend.md, dar .claude/ trimite la ea"
    )
