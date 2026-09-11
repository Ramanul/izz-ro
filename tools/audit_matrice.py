#!/usr/bin/env python3
"""Verifica registrul de mecanisme de protectie (`specs/audit-unificat.tsv`) fata de repo.

DE CE EXISTA. Auditul unificat a sosit ca registru Excel: 36 de mecanisme, 66 de coloane,
zero formule. Toate agregatele din foaia Dashboard erau constante scrise de mana, iar
dovezile erau numere de linie (`fetch.py:11-13`). Doua consecinte, ambele masurate pe
2026-09-11:

  1. Agregatele se contraziceau cu datele. Coloana `Prioritate` continea si `Ridicata`, si
     `Ridicată`; Dashboard-ul raporta „Prioritate P0: 1" cand randurile marcate erau 2.
  2. Un mecanism inventariat ca poarta activa, fail-closed, cu cea mai mare eroziune din
     matrice (4) si cu o actiune P0 derivata din el, nu exista: `ramanul-triage-blockers`
     e o RAMURA cu un commit de 14 linii in `generator/util.py`, nemergeuita in main si deja
     consemnata `masurat-fals` in `IZZ-0266` — cu trei zile INAINTE de audit.

Al doilea caz e chiar failure mode-ul pe care auditul si-l defineste singur („Stale rule")
si incalca chiar principiul pe care si-l scrie in README („existenta unui tool nu
echivaleaza cu autoritate de blocare"). Un audit care nu e legat mecanic de repo devine, in
cateva zile, o descriere a unui sistem care nu mai exista.

CE FACE, deci. Registrul ramane date; agregatele se CALCULEAZA; fiecare dovada e o cale
verificata pe disc, nu un numar de linie. Unealta iese != 0 la orice drift, ca sa poata fi
gardă in CI (`tests/test_audit_matrice.py`).

CE NU FACE, spus pe fata ca sa nu para mai mult decat e. Verifica faptele care se pot citi
din repo: ca fisierul exista, ca vocabularul e inchis, ca agregatele se reproduc, ca
declaratiile nu se contrazic intre ele. NU verifica daca un mecanism chiar isi face treaba
— aia e treaba testelor lui. Autoritatea marcata `conditionata` depinde de setari GitHub
(required status checks) care nu se pot citi din sesiune; unealta o pastreaza ca declaratie
explicita de necunoscut, nu o rezolva.
"""
from __future__ import annotations

import argparse
import csv
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = os.path.join(ROOT, "specs", "audit-unificat.tsv")

COLOANE = (
    "id", "categorie", "mecanism", "dovada", "pozitie", "poate_bloca", "autoritate",
    "conditie_autoritate", "mod", "esec", "bypass", "eroziune", "risc", "stare", "nota",
)

# Vocabulare inchise. Toate valorile sunt ASCII fara diacritice, deliberat: exact clasa de
# bug care a stricat Dashboard-ul original (`Ridicata` vs `Ridicată` numarate separat).
VOCAB = {
    "categorie": {
        "guard", "quality-gate", "validator", "sanity-check", "integrity-check",
        "automated-test", "lint-static", "security-scan", "human-review", "fallback",
        "failover", "monitor", "smoke-probe", "audit", "observability",
        "defensive-coding", "isolation", "backup", "legal",
    },
    "pozitie": {"fetch", "process", "render", "moderation", "build", "deploy", "probe",
                "monitor", "dev"},
    "poate_bloca": {"da", "nu"},
    "autoritate": {"efectiva", "conditionata", "niciuna"},
    "mod": {"preventiv", "detectiv", "recuperare"},
    "esec": {"inchis", "deschis"},
    "bypass": {"da", "nu"},
    "stare": {"activ", "activ-partial", "absent"},
}
SCORURI = ("eroziune", "risc")


def citeste(cale: str = TSV) -> list[dict]:
    with open(cale, encoding="utf-8", newline="") as fh:
        randuri = list(csv.DictReader(fh, delimiter="\t"))
    if not randuri:
        raise SystemExit(f"FAIL: {cale} nu contine niciun rand.")
    lipsa = set(COLOANE) - set(randuri[0])
    if lipsa:
        raise SystemExit(f"FAIL: coloane lipsa in {cale}: {sorted(lipsa)}")
    return randuri


def _cai(rand: dict) -> list[str]:
    return [p for p in (rand["dovada"] or "").split(";") if p and p != "-"]


def verifica(randuri: list[dict]) -> list[str]:
    """Toate problemele gasite, ca linii de text. Lista goala = registrul e curat."""
    probleme: list[str] = []
    vazute: set[str] = set()

    for r in randuri:
        rid = r["id"]
        eticheta = f"#{rid} {r['mecanism'][:40]}"

        if rid in vazute:
            probleme.append(f"{eticheta}: id duplicat")
        vazute.add(rid)

        for camp, valori in VOCAB.items():
            if r[camp] not in valori:
                probleme.append(
                    f"{eticheta}: {camp}={r[camp]!r} in afara vocabularului {sorted(valori)}"
                )
        for camp in SCORURI:
            if not r[camp].isdigit() or not 0 <= int(r[camp]) <= 5:
                probleme.append(f"{eticheta}: {camp}={r[camp]!r} nu e intreg 0-5")

        # Dovada: fiecare cale trebuie sa existe. Asta e legatura dintre registru si repo —
        # fara ea, registrul descrie un sistem care poate sa fi disparut (cazul #32).
        for cale in _cai(r):
            if not os.path.exists(os.path.join(ROOT, cale)):
                probleme.append(f"{eticheta}: dovada inexistenta pe disc: {cale}")

        # Contradictii logice. Fiecare vine dintr-un principiu scris in README-ul auditului.

        # „Un monitor nu este automat un gate": ceva ce nu poate bloca nu poate avea autoritate.
        if r["poate_bloca"] == "nu" and r["autoritate"] != "niciuna":
            probleme.append(
                f"{eticheta}: poate_bloca=nu dar autoritate={r['autoritate']} — "
                "un mecanism care nu opreste fluxul nu are autoritate"
            )
        # Un gate care, la propriul defect, lasa fluxul sa treaca nu are autoritate EFECTIVA;
        # cel mult conditionata. Exact contradictia gasita la #25/#26/#30/#34 in matricea Excel.
        if r["autoritate"] == "efectiva" and r["esec"] == "deschis":
            probleme.append(
                f"{eticheta}: autoritate=efectiva dar esec=deschis — "
                "un mecanism fail-open nu opreste nimic cand cade"
            )
        # O autoritate conditionata fara conditia numita e o afirmatie nefalsificabila.
        if r["autoritate"] == "conditionata" and r["conditie_autoritate"] in ("", "-"):
            probleme.append(f"{eticheta}: autoritate=conditionata fara conditie_autoritate")
        if r["autoritate"] != "conditionata" and r["conditie_autoritate"] not in ("", "-"):
            probleme.append(
                f"{eticheta}: conditie_autoritate completata desi autoritate={r['autoritate']}"
            )
        # Un mecanism absent nu blocheaza, nu are autoritate si nu se poate eroda: nu e acolo.
        if r["stare"] == "absent":
            if r["poate_bloca"] != "nu" or r["autoritate"] != "niciuna":
                probleme.append(
                    f"{eticheta}: stare=absent dar inca declarat ca blocheaza / are autoritate"
                )
            if int(r["eroziune"]) or int(r["risc"]):
                probleme.append(
                    f"{eticheta}: stare=absent cu eroziune/risc nenule — "
                    "un mecanism inexistent nu are ce eroda"
                )
        if not r["nota"].strip():
            probleme.append(f"{eticheta}: nota goala")

    return probleme


def agregate(randuri: list[dict]) -> dict:
    """Dashboard-ul, CALCULAT. Nicio cifra de aici nu se scrie de mana nicaieri."""
    viu = [r for r in randuri if r["stare"] != "absent"]
    return {
        "mecanisme_in_registru": len(randuri),
        "mecanisme_vii": len(viu),
        "mecanisme_absente": len(randuri) - len(viu),
        "autoritate_efectiva": sum(1 for r in viu if r["autoritate"] == "efectiva"),
        "autoritate_conditionata": sum(1 for r in viu if r["autoritate"] == "conditionata"),
        "fara_autoritate": sum(1 for r in viu if r["autoritate"] == "niciuna"),
        "fail_inchis": sum(1 for r in viu if r["esec"] == "inchis"),
        "fail_deschis": sum(1 for r in viu if r["esec"] == "deschis"),
        "bypass_documentat": sum(1 for r in viu if r["bypass"] == "da"),
        "eroziune_peste_2": sum(1 for r in viu if int(r["eroziune"]) > 2),
        "risc_cel_putin_3": sum(1 for r in viu if int(r["risc"]) >= 3),
        "categorii": len({r["categorie"] for r in viu}),
    }


def raport(randuri: list[dict]) -> None:
    ag = agregate(randuri)
    print("REGISTRU DE PROTECTII — agregate calculate din date\n")
    for cheie, val in ag.items():
        print(f"  {cheie:26s} {val}")

    print("\nPe categorie (mecanisme vii):")
    viu = [r for r in randuri if r["stare"] != "absent"]
    for cat, n in sorted(Counter(r["categorie"] for r in viu).items()):
        efect = sum(1 for r in viu if r["categorie"] == cat and r["autoritate"] == "efectiva")
        print(f"  {cat:18s} {n:2d}  (cu autoritate efectiva: {efect})")

    atentie = [r for r in viu if int(r["risc"]) >= 3 or r["stare"] == "activ-partial"]
    if atentie:
        print("\nCer atentie (risc >= 3 sau activ-partial):")
        for r in sorted(atentie, key=lambda x: -int(x["risc"])):
            print(f"  #{r['id']:>2s} risc={r['risc']} {r['stare']:14s} {r['mecanism']}")

    absente = [r for r in randuri if r["stare"] == "absent"]
    if absente:
        print("\nInventariate dar ABSENTE din sistemul viu:")
        for r in absente:
            print(f"  #{r['id']:>2s} {r['mecanism']}\n      {r['nota']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("comanda", nargs="?", default="verifica",
                   choices=("verifica", "raport"))
    args = p.parse_args()

    randuri = citeste()
    if args.comanda == "raport":
        raport(randuri)
        return 0

    probleme = verifica(randuri)
    if probleme:
        print(f"FAIL: {len(probleme)} probleme in specs/audit-unificat.tsv:")
        for pb in probleme:
            print(f"  - {pb}")
        return 1
    ag = agregate(randuri)
    print(
        f"OK: {ag['mecanisme_in_registru']} mecanisme inventariate, "
        f"{ag['mecanisme_vii']} vii, dovezile exista pe disc, "
        "vocabular inchis, fara contradictii de autoritate."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # `… raport | head` inchide stdout la mijloc. Un exit normal ar mai incerca un flush
        # si ar tipari un traceback peste iesirea utila; `os._exit` sare peste flush.
        os._exit(0)
