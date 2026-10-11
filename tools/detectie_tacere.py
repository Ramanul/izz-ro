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

# (workflow, plafon_ore): cât maxim poate tăcea un mecanism viu. Plafoanele sunt calibrate pe
# CADENȚA MĂSURATĂ (gh run list, 100 de rulări per workflow, 2026-10-11), nu pe cron-ul scris:
# GitHub livrează cererile `schedule` rarite, iar cron-ul de pe hârtie nu spune nimic despre
# ce se întâmplă în realitate. Măsurat atunci — median / p90 / maxim, în ore:
#   build.yml   5,1 / 7,0 / 9,0      monitor.yml 4,8 / 6,8 / 8,9
#   smoke.yml   0,8 / 4,5 / 7,6      feedcheck   23,8 / ~25 / 25 (fără golurile de dinainte
#                                                          de activarea programării)
# Vechile plafoane erau 6h pentru primele trei: 20% dintre intervalele NORMALE ale build.yml
# depășeau 6h, deci detectorul suna la fiecare ~a cincea rulare — și a sunat: două alerte în
# două zile (9 și 10 octombrie), ambele pe mecanisme care rulau normal, doar târziu. O alertă
# care sună pe normal e o alertă ignorată. 12h = maximul măsurat + ~30% marjă; feedcheck 30h.
MECANISME = [
    ("build.yml", 12),
    ("monitor.yml", 12),
    ("smoke.yml", 12),
    ("feedcheck.yml", 30),
]
# Cadența de conținut: măsurată pe ultimele 200 de commituri ale `data/articles.json`
# (2026-09-01 → 2026-10-11): mediană 4,7h, p90 6,9h, maxim 15,0h. Plafonul vechi de 6h cădea
# sub p90, deci alerga pe gol; 12h prinde o înghețare reală (inclusiv cele două ferestre de
# 14-15h din istoric) fără să confunde o întârziere de planificator cu o avarie.
PLAFON_CONTINUT_ORE = 12


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
    # -X GET obligatoriu: gh api cu flag-uri de campuri (-f/-F) face implicit POST,
    # iar POST pe /commits intoarce 404 (prins la prima rulare reala, 2026-09-05).
    iesire = _gh("api", f"repos/{repo}/commits", "-X", "GET", "-f", "path=data/articles.json",
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
        mesaj = f"Detectorul nu a putut verifica ({exc}). Tăcerea detectorului e tot tăcere."
        print(f"NECLAR: {mesaj} Trateaz-o ca incident.")
        Path("alerta.md").write_text(
            "## Tăcere pipeline — NECLAR — " + acum.isoformat(timespec="seconds") + "\n\n"
            + mesaj + "\n",
            encoding="utf-8",
        )
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
