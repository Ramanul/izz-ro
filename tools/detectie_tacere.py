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

# (workflow, plafon_ore): cât maxim poate tăcea un mecanism viu. Plafoanele pentru
# workflow-uri planificate sunt calibrate pe CADENȚA MĂSURATĂ, nu pe cron-ul scris:
# GitHub întârzie/omite rulările programate la vârf, iar o alertă permanentă e o alertă
# ignorată. Măsurat 2026-09-05 (gh run list): monitor.yml cu cron */10 a rulat efectiv la
# 01:16 / 05:51 / 10:03 (≈4,5h) => plafon 6h. build.yml orar cu poartă ~2h => 6h.
# smoke.yml: cron orar, dar măsurat 2026-09-05 rulase la 23:18 / 01:23 / 06:18 / 10:54
# (goluri de până la ~5h — aceleași întârzieri GitHub) => plafon 6h. feedcheck.yml zilnic => 26h.
MECANISME = [
    ("build.yml", 6),
    ("monitor.yml", 6),
    ("smoke.yml", 6),
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
