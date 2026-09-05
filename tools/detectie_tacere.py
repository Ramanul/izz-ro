#!/usr/bin/env python3
"""Detecția tăcerii: verifică că mecanismele-cheie chiar rulează (PLAN UNIFICAT #10).

Un cron care moare tăcut arată identic, din afară, cu un sistem sănătos — uptime-ul
poate fi verde pe un site înghețat. Unelta asta nu măsoară site-ul public (asta fac
monitor/smoke), ci CABLAJUL: ultimul commit de conținut și ultima rulare a fiecărui
workflow programat. Orice depășire de plafon = tăcere.

Ieșiri: 0 = totul viu; 1 = tăcere detectată (detalii în stdout + alerta.md);
2 = nu am putut verifica (fail-closed: tăcerea detectorului e tot tăcere).
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# (workflow, plafon_ore): cât maxim poate tăcea un mecanism viu.
# build.yml (pipeline): cron orar, poartă de cadență ~2h => 4h fără nicio rulare = mort.
# monitor.yml: */10 min => 1h. smoke.yml: orar => 2h. feedcheck.yml: zilnic => 26h.
MECANISME = [
    ("build.yml", 4),
    ("monitor.yml", 1),
    ("smoke.yml", 2),
    ("feedcheck.yml", 26),
]
PLAFON_CONTINUT_ORE = 6  # cadența de conținut e ~2h; 6h fără commit de conținut = înghețat


def _gh(*args: str) -> str:
    rezultat = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if rezultat.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} a eșuat: {rezultat.stderr.strip()[:200]}")
    return rezultat.stdout


def _varsta_ore(iso: str, acum: datetime) -> float:
    moment = datetime.fromisoformat(iso.strip().replace("Z", "+00:00"))
    return (acum - moment).total_seconds() / 3600.0


def ultimul_commit_continut(acum: datetime, repo: str) -> float | None:
    """Vârsta în ore a ultimului commit pe data/articles.json; None dacă nu există."""
    iesire = _gh("api", f"repos/{repo}/commits", "-f", "path=data/articles.json",
                 "-F", "per_page=1", "--jq", ".[0].commit.committer.date")
    date = iesire.strip()
    return _varsta_ore(date, acum) if date and date != "null" else None


def ultima_rulare(workflow: str, acum: datetime, repo: str) -> float | None:
    """Vârsta în ore a ultimei rulări a workflow-ului; None dacă nicio rulare."""
    iesire = _gh("run", "list", "--workflow", workflow, "--repo", repo,
                 "--limit", "1", "--json", "createdAt", "--jq", ".[0].createdAt")
    date = iesire.strip()
    return _varsta_ore(date, acum) if date and date != "null" else None


def constata(repo: str, acum: datetime) -> list[str]:
    """Toate încălcările de tăcere, ca mesaje citibile. Lista goală = totul viu."""
    probleme: list[str] = []
    varsta = ultimul_commit_continut(acum, repo)
    if varsta is None:
        probleme.append("commit de conținut: niciunul găsit pe data/articles.json")
    elif varsta > PLAFON_CONTINUT_ORE:
        probleme.append(f"conținut înghețat: ultimul commit pe data/articles.json "
                        f"are {varsta:.1f}h (plafon {PLAFON_CONTINUT_ORE}h)")
    for workflow, plafon in MECANISME:
        varsta = ultima_rulare(workflow, acum, repo)
        if varsta is None:
            probleme.append(f"workflow `{workflow}`: nicio rulare înregistrată")
        elif varsta > plafon:
            probleme.append(f"workflow `{workflow}` tăcut: ultima rulare "
                            f"{varsta:.1f}h în urmă (plafon {plafon}h)")
    return probleme


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "Ramanul/izz-ro")
    acum = datetime.now(timezone.utc)
    try:
        probleme = constata(repo, acum)
    except (RuntimeError, ValueError) as exc:
        print(f"NECLAR: detectorul nu a putut verifica ({exc}). "
              "Tăcerea detectorului e tot tăcere — trateaz-o ca incident.")
        return 2
    if not probleme:
        print("OK: mecanismele programate au rulat în plafon.")
        return 0
    print("TĂCERE DETECTATĂ:")
    for p in probleme:
        print(f"  - {p}")
    Path("alerta.md").write_text(
        "## Tăcere pipeline — " + acum.isoformat(timespec="seconds") + "\n\n"
        + "\n".join(f"- {p}" for p in probleme) + "\n",
        encoding="utf-8",
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
