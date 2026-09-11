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


def citeste(cale: str | None = None) -> list[dict]:
    # Legare TARZIE, nu `cale: str = TSV`: o valoare implicita se leaga la DEFINIREA
    # functiei, deci constanta de modul nu mai poate fi suprascrisa — iar un test care
    # crede ca a redirectionat registrul ar verifica de fapt fisierul comis si ar trece
    # degeaba. Gasit scriind chiar testul pentru constatarea Codex.
    cale = cale or TSV
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


# --- eroziune: cele opt dimensiuni, si care dintre ele se pot MASURA -------------------
#
# Foaia `Eroziune` a auditului defineste opt dimensiuni in detaliu, apoi le lasa GOALE pe
# toate cele 36 de randuri, iar scorul agregat „Nivel eroziune (0-5)" e introdus direct.
# Un scor care nu deriva din nimic nu poate fi infirmat, deci nu e o masuratoare.
#
# Aici nu completez cele opt cu judecata mea — ar fi aceeasi greseala, cu alta mana. Calculez
# indicatorii care CHIAR se pot citi din repo si din registru, si declar restul nemasurate.
# Patru da, patru nu; motivul e scris langa fiecare.
DIMENSIUNI = {
    "autoritate": "MASURAT — poate_bloca=da dar autoritatea nu e efectiva",
    "bypass": "MASURAT — ruta alternativa documentata in registru",
    "temporala": "INDICATOR — vechimea ultimei atingeri a dovezilor (git)",
    "acoperire": "NEMASURAT — cere graful de apeluri per mecanism, nu o coloana",
    "strictete": "NEMASURAT — cere istoricul pragurilor, iar relaxarea legitima arata identic",
    "integrare": "NEMASURAT — cere ordinea reala a pipeline-ului per proprietate",
    "duplicare": "NEMASURAT — cere compararea REGULILOR, nu a cailor de fisier",
    "orbire": "NEMASURAT — prin definitie, garda nu poate raporta ce nu vede",
}

# Nota de metoda, pastrata fiindca e chiar greseala pe care auditul original a facut-o.
# Prima versiune a acestei unelte marca drept „duplicare" orice doua mecanisme care impart
# un fisier de dovada. A produs 20+ semnale din 44 de mecanisme — adica zgomot, nu masuratoare:
# `generator/fetch.py` gazduieste legitim garda XML, retry-ul si garda de redirectare, care nu
# se dubleaza intre ele. Dimensiunea „duplicare/conflict" din foaia de audit inseamna doua
# mecanisme care pot DECIDE DIFERIT asupra aceluiasi caz; caile de fisier nu spun nimic despre
# asta. Ce ramane masurabil e altceva, si e o observatie despre REGISTRU, nu despre sistem:
# doua mecanisme cu dovezi IDENTICE nu pot fi deosebite unul de altul pe baza registrului.


def _zile_de_la_ultima_atingere(cale: str) -> int | None:
    """Zile de cand nu s-a mai atins fisierul. `None` daca git nu raspunde."""
    import subprocess
    from datetime import datetime, timezone
    try:
        ies = subprocess.run(["git", "log", "-1", "--format=%cI", "--", cale],
                             capture_output=True, text=True, cwd=ROOT, timeout=20).stdout.strip()
        if not ies:
            return None
        return (datetime.now(timezone.utc) - datetime.fromisoformat(ies)).days
    except Exception:
        return None


def eroziune(randuri: list[dict]) -> dict:
    """Indicatorii masurabili, per mecanism viu. NU un scor compozit, deliberat.

    Un numar unic ar ascunde tocmai ce conteaza: ca patru dimensiuni din opt nu se pot citi
    din repo. Insumate cu zero in locul lor, ar arata ca un sistem sanatos.
    """
    viu = [r for r in randuri if r["stare"] != "absent"]

    out = {}
    for r in viu:
        cai = _cai(r)
        semnale = []
        if r["poate_bloca"] == "da" and r["autoritate"] != "efectiva":
            semnale.append(f"autoritate: poate bloca, dar e {r['autoritate']}")
        if r["bypass"] == "da":
            semnale.append("bypass: ruta alternativa documentata")
        varste = [z for z in (_zile_de_la_ultima_atingere(c) for c in cai) if z is not None]
        out[r["id"]] = {
            "mecanism": r["mecanism"],
            "semnale": semnale,
            "zile_de_la_ultima_atingere": max(varste) if varste else None,
        }
    return out


def granularitate_registru(randuri: list[dict]) -> list[list[str]]:
    """Grupuri de mecanisme vii cu dovada IDENTICA — deci nedeosebibile din registru.

    Nu e eroziune si nu e o afirmatie despre sistem: e consecinta directa a deciziei de
    schema „dovada e o cale de fisier, niciodata un numar de linie" (numerele de linie
    putrezesc la prima refactorizare). Doua garzi legitime din acelasi fisier vor arata
    mereu la fel aici. Se raporteaza separat tocmai ca sa nu fie citit ca defect al
    sistemului; s-ar inchide trecand dovada la `cale#simbol`, verificabil prin cautare si
    la fel de rezistent la refactorizare — schimbare de schema, nu de raport.
    """
    grupuri: dict[tuple[str, ...], list[str]] = {}
    for r in randuri:
        if r["stare"] == "absent":
            continue
        if (cheie := tuple(sorted(_cai(r)))):
            grupuri.setdefault(cheie, []).append(r["id"])
    return [sorted(ids, key=int) for ids in grupuri.values() if len(ids) > 1]


def raport_eroziune(randuri: list[dict]) -> None:
    print("EROZIUNE — doar ce se poate masura din repo\n")
    for nume, explicatie in DIMENSIUNI.items():
        print(f"  {nume:12s} {explicatie}")

    date = eroziune(randuri)
    cu_semnale = {k: v for k, v in date.items() if v["semnale"]}
    print(f"\nMecanisme vii cu cel putin un semnal: {len(cu_semnale)} din {len(date)}")
    for rid, d in sorted(cu_semnale.items(), key=lambda kv: int(kv[0])):
        print(f"\n  #{rid:>2s} {d['mecanism']}")
        for s in d["semnale"]:
            print(f"       · {s}")

    vechi = sorted(((v["zile_de_la_ultima_atingere"] or 0), k, v["mecanism"])
                   for k, v in date.items())
    print("\nCele mai VECHI dovezi (indicator temporal, NU un verdict):")
    for zile, rid, mec in vechi[-5:][::-1]:
        print(f"  {zile:4d} zile  #{rid:>2s} {mec}")
    print("\n  Vechimea singura nu e eroziune: o garda stabila pe o suprafata stabila e sanatoasa.")
    print("  Semnalul e vechimea gardii langa o suprafata care S-A schimbat — comparatie care")
    print("  cere judecata, deci ramane aici indicator, nu scor.")

    if (grupuri := granularitate_registru(randuri)):
        n = sum(len(g) for g in grupuri)
        print(f"\nGRANULARITATEA REGISTRULUI (nu eroziune): {n} mecanisme in {len(grupuri)} "
              "grupuri cu dovada identica,")
        print("  deci nedeosebibile din registru. E consecinta schemei de dovada "
              "(cale de fisier, nu numar de linie), nu un defect al sistemului.")
        for g in grupuri:
            print("  #" + ", #".join(g))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("comanda", nargs="?", default="verifica",
                   choices=("verifica", "raport", "eroziune"))
    args = p.parse_args()

    randuri = citeste()

    # Verificarea ruleaza INTAI, pentru orice subcomanda. Un raport scos dintr-un registru
    # in drift — dovezi care nu mai exista pe disc, vocabular invalid, contradictii de
    # autoritate — arata exact ca o masuratoare si nu este una. Chiar teza acestei unelte.
    probleme = verifica(randuri)
    if probleme:
        print(f"FAIL: {len(probleme)} probleme in specs/audit-unificat.tsv:")
        for pb in probleme:
            print(f"  - {pb}")
        if args.comanda != "verifica":
            print(f"\n  Comanda `{args.comanda}` NU a rulat: un raport peste un registru "
                  "in drift ar fi o masuratoare falsa.")
        return 1

    if args.comanda == "eroziune":
        raport_eroziune(randuri)
        return 0
    if args.comanda == "raport":
        raport(randuri)
        return 0
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
