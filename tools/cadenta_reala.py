#!/usr/bin/env python3
"""Cat de des ruleaza DE FAPT `build.yml`, fata de cat declara cronul.

DE CE EXISTA. `CLAUDE.md` a afirmat luni de zile ca „build.yml incearca orar (13 * * * *),
dar poarta de 105 minute apara publicarea la ~2h". Prima parte e o citire a fisierului; a
doua e o deductie din cod. Masurata pe 40 de rulari programate consecutive (2026-09-05 …
2026-09-11), deductia e falsa: niciun interval intre rulari nu a coborat sub 105 minute, deci
poarta nu putea fi ce produce cadenta. Ce o produce e ca GitHub nu creeaza rularile programate
— rata observata a fost 25% dintr-un cron orar, cu un gol median de ~4 ore.

Concluzia practica nu e „schimba cronul" (regula din sect. 17 ramane), ci ca o cifra de
cadenta scrisa in contract trebuie sa poata fi RE-masurata, nu re-crezuta.

DE CE CITESTE DE LA STDIN, nu din API. Masuratoarea trebuie sa se poata verifica offline, cu
o fixtura, altfel unealta insasi devine o afirmatie netestabila. Aducerea datelor depinde de
mediu (`gh` exista in Actions, nu si in orice sesiune); calculul nu trebuie sa depinda de el.

  gh api "repos/OWNER/REPO/actions/workflows/build.yml/runs?event=schedule&per_page=100" \\
    | python tools/cadenta_reala.py

CE NU MASOARA, spus pe fata. Lista de rulari nu spune de ce lipseste o rulare: intarziere de
planificator, rulare nelivrata sau fereastra in care repo-ul era inactiv arata identic aici.
Si nu spune cate rulari au fost oprite de poarta — aia cere datele per job (o rulare oprita de
poarta se vede ca durata de cateva secunde, dar durata nu e dovada, ci indiciu).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "build.yml")


def _citeste_workflow(cale: str = WORKFLOW, interval_impus: int | None = None) -> tuple[int, int]:
    """(interval declarat in minute, pragul portii in minute), citite din workflow.

    Citite, nu primite ca argument: o baza de comparatie data de mana se poate potrivi cu
    concluzia dorita. Formele de cron acceptate sunt cele folosite efectiv; orice alta forma
    e o eroare explicita, nu o ghicire.

    `interval_impus` OCOLESTE parsarea cronului, nu o corecteaza dupa. Altfel portita
    documentata pentru forme neacoperite („foloseste --interval-min") era inutilizabila exact
    in cazul pentru care exista: `_citeste_workflow` iesea cu SystemExit inainte ca
    suprascrierea sa apuce sa se aplice.
    """
    text = open(cale, encoding="utf-8").read()
    p = re.search(r'PRAG_MIN:\s*"(\d+)"', text)
    prag = int(p.group(1)) if p else 0
    if interval_impus:
        return interval_impus, prag
    m = re.search(r'cron:\s*"([^"]+)"', text)
    if not m:
        raise SystemExit(f"FAIL: niciun `cron:` in {cale}")
    camp = m.group(1).split()
    if len(camp) != 5:
        raise SystemExit(f"FAIL: cron cu {len(camp)} campuri, asteptate 5: {m.group(1)!r}")
    minut, ora = camp[0], camp[1]
    if ora == "*":
        interval = 60
    elif (mo := re.fullmatch(r"\*/(\d+)", ora)):
        interval = 60 * int(mo.group(1))
    else:
        raise SystemExit(
            f"FAIL: forma de ora {ora!r} nu e acoperita; foloseste --interval-min explicit."
        )
    if not minut.isdigit():
        raise SystemExit(f"FAIL: minut {minut!r} neasteptat; foloseste --interval-min explicit.")
    return interval, prag


def _porniri(date: dict | list) -> list[datetime]:
    rulari = date["workflow_runs"] if isinstance(date, dict) else date
    out = []
    for r in rulari:
        if (s := r.get("run_started_at") or r.get("created_at")):
            out.append(datetime.fromisoformat(s.replace("Z", "+00:00")))
    return sorted(out)


def masoara(porniri: list[datetime], interval_min: int, prag_min: int) -> dict:
    """Statisticile, ca date. Fara verdict: „prea rar" e judecata editoriala, nu masuratoare."""
    if len(porniri) < 2:
        raise SystemExit("FAIL: cel putin doua rulari sunt necesare pentru un interval.")
    goluri = [(porniri[i + 1] - porniri[i]).total_seconds() / 60 for i in range(len(porniri) - 1)]
    fereastra = (porniri[-1] - porniri[0]).total_seconds() / 60
    return {
        "rulari": len(porniri),
        "de_la": porniri[0].isoformat(),
        "pana_la": porniri[-1].isoformat(),
        "fereastra_ore": round(fereastra / 60, 1),
        "interval_declarat_min": interval_min,
        # Rata se calculeaza pe INTERVALE, deci si cifrele comparate sunt intervale. Prima
        # versiune punea fata in fata `int(fereastra // interval)` (intervale) cu `len(porniri)`
        # (porniri): la 25 de porniri perfect orare pe 24h raporta „24 asteptate / 25 observate"
        # langa o rata de 100%, adica doua baze diferite in acelasi tabel.
        "intervale_asteptate": round(fereastra / interval_min),
        "intervale_observate": len(goluri),
        "rata_declansare": round(len(goluri) / (fereastra / interval_min), 3),
        "gol_min": round(min(goluri)),
        "gol_median": round(statistics.median(goluri)),
        "gol_max": round(max(goluri)),
        "prag_poarta_min": prag_min,
        "goluri_sub_prag": sum(1 for g in goluri if g < prag_min),
        "minute_de_pornire_distincte": len({p.minute for p in porniri}),
    }


def raport(st: dict) -> None:
    print(f"CADENTA REALA — {st['rulari']} rulari programate, "
          f"{st['fereastra_ore']}h ({st['de_la'][:16]} … {st['pana_la'][:16]})\n")
    print(f"  cron declarat            la fiecare {st['interval_declarat_min']} min")
    print(f"  intervale asteptate      {st['intervale_asteptate']}")
    print(f"  intervale observate      {st['intervale_observate']}")
    print(f"  rata de declansare       {st['rata_declansare']:.0%}")
    print(f"  (porniri in fereastra    {st['rulari']})\n")
    print(f"  gol intre rulari         min {st['gol_min']} · median {st['gol_median']}"
          f" · max {st['gol_max']} min")
    print(f"  pragul portii            {st['prag_poarta_min']} min")
    print(f"  goluri sub prag          {st['goluri_sub_prag']} din {st['rulari'] - 1}")
    print(f"  minute de pornire        {st['minute_de_pornire_distincte']} valori distincte\n")

    if st["prag_poarta_min"] and not st["goluri_sub_prag"]:
        print("  CITIRE: niciun interval nu coboara sub prag, deci poarta nu poate fi ce")
        print("  produce cadenta observata. Ce o produce e ca rularile programate lipsesc.")
    if st["minute_de_pornire_distincte"] > 3:
        print("  Minutul de pornire e imprastiat: planificatorul nu respecta minutul din cron.")
    print("\n  NU se poate citi de aici DE CE lipseste o rulare, si nici cate au fost oprite")
    print("  de poarta — aia cere datele per job.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("fisier", nargs="?", help="JSON de la API; implicit stdin")
    p.add_argument("--interval-min", type=int,
                   help="suprascrie intervalul citit din workflow (forme de cron neacoperite)")
    p.add_argument("--json", action="store_true", help="date brute, pentru alt consumator")
    args = p.parse_args()

    interval, prag = _citeste_workflow(interval_impus=args.interval_min)

    brut = open(args.fisier, encoding="utf-8").read() if args.fisier else sys.stdin.read()
    if not brut.strip():
        raise SystemExit("FAIL: nicio intrare. Vezi docstring-ul pentru comanda `gh api`.")
    st = masoara(_porniri(json.loads(brut)), interval, prag)
    print(json.dumps(st, indent=2)) if args.json else raport(st)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        os._exit(0)
