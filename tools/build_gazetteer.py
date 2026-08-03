#!/usr/bin/env python
"""Construieste `data/gazetteer.csv` (nume, nivel) din nomenclatorul oficial SIRUTA.

Sursa: SIRUTA (INS), via https://github.com/andrei-furnica/localitati-romania (data.gov.ro).
Fisierul brut e `data/siruta_raw.csv` (cp1250, `;`, zecimale cu virgula).

De ce filtram: satele (NIV=3) au ~5000 de nume care se repeta intre judete (POIANA x38,
"SATU NOU" x42). Intr-un index NAME->nivel fara context, un asemenea nume ar potrivi orice
text. Deci pastram doar satele cu nume UNIC global, >=5 litere, si nu in lista de cuvinte
comune. UAT-urile (NIV=2: municipii/orase/comune) si judetele (NIV=1) intra toate — sunt
granularitatea pe care poarta o foloseste deja, si sunt putine si distincte.

Satele ambigue raman pentru un slice viitor: dezambiguizare pe judetul SURSEI (un ziar de
Vrancea care scrie "Poiana" = Poiana din Vrancea). Vezi specs/STATE.md.
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from generator.util import strip_diacritics  # noqa: E402

RAW = os.path.join(ROOT, "data", "siruta_raw.csv")
OUT = os.path.join(ROOT, "data", "gazetteer.csv")
OUT_SATE = os.path.join(ROOT, "data", "sate_judet.csv")

# Cuvinte care sunt si nume de sat, dar apar mult mai des cu sensul lor comun in stiri.
# Un sat "Unirea" nu trebuie sa faca dintr-o stire despre Uniunea Europeana o stire locala.
STOPWORDS = {
    "UNIREA", "VICTORIA", "LIBERTATEA", "INDEPENDENTA", "PROGRESU", "PROGRESUL",
    "VIITORUL", "BISERICA", "BISERICANI", "GARA", "CENTRU", "PIATA", "VALEA",
    "DEALU", "DEALUL", "PADUREA", "LUNCA", "POIANA", "MOVILA", "IZVORU", "IZVORUL",
    "FANTANA", "FANTANELE", "PODURI", "PODUL", "MALU", "MALUL", "OSTROV", "SAT",
    "SATU", "SATUL", "SLOBOZIA", "RACOVITA", "COTU", "COASTA", "FRASIN", "FRUMOASA",
}

# Nivelul din SIRUTA (NIV): 1=judet, 2=UAT (municipiu/oras/comuna), 3=sat component.
NIVEL_SIRUTA = {"1": "zonal", "2": "local", "3": "local"}


def _citeste_siruta():
    with open(RAW, encoding="cp1250") as fh:
        yield from csv.DictReader(fh, delimiter=";")


def construieste() -> dict:
    rows = list(_citeste_siruta())

    # Nume de sat care se repeta -> ambigue fara context. Le identificam intai.
    sate = [r for r in rows if r.get("NIV") == "3"]
    nume_sat = [strip_diacritics(r["DENLOC"].strip()).upper() for r in sate]
    din_mai_multe = {n for n in nume_sat if nume_sat.count(n) > 1}

    gaz: dict[str, str] = {}
    tinut = {"judet": 0, "uat": 0, "sat_ok": 0, "sat_scos": 0}
    for r in rows:
        niv = r.get("NIV")
        nivel = NIVEL_SIRUTA.get(niv)
        if not nivel:
            continue
        nume = strip_diacritics(r["DENLOC"].strip()).upper()
        # Curatam prefixele administrative din nume: "MUNICIPIUL AIUD" -> "AIUD".
        for pref in ("MUNICIPIUL ", "ORASUL ", "ORAS ", "COMUNA ", "JUDETUL ", "SATUL "):
            if nume.startswith(pref):
                nume = nume[len(pref):]
                break
        if niv == "3":
            if nume in din_mai_multe or len(nume) < 5 or nume in STOPWORDS:
                tinut["sat_scos"] += 1
                continue
            tinut["sat_ok"] += 1
        elif niv == "2":
            tinut["uat"] += 1
        else:
            tinut["judet"] += 1
        # local (mai specific) bate zonal daca doua niveluri au acelasi nume.
        if gaz.get(nume) != "local":
            gaz[nume] = nivel
    return gaz, tinut


def sate_pe_judet() -> dict:
    """{JUDET: [nume de sat]} — TOATE satele, inclusiv cele cu nume repetat.

    Perechea cu `construieste()` de mai sus, si complementul ei: acolo satele ambigue se
    ARUNCA fiindca indexul global n-are cum sa aleaga intre cele 38 de Poiana; aici numele
    se pastreaza pentru ca judetul SURSEI face alegerea. Un ziar de Vrancea care scrie
    „Poiana" inseamna Poiana din Vrancea, si numai poarta care stie judetul poate spune asta.
    Fara acel judet, indexul asta NU se foloseste — vezi `geo.clasifica(text, judet)`.
    """
    rows = list(_citeste_siruta())
    # NIV=1 sunt judetele; codul lor (JUD) e cheia dupa care se atarna satele.
    cod = {}
    for r in rows:
        if r.get("NIV") == "1":
            nume = strip_diacritics(r["DENLOC"].strip()).upper()
            cod[r["JUD"]] = nume[len("JUDETUL "):] if nume.startswith("JUDETUL ") else nume
    out: dict[str, set] = {}
    scoase = 0
    for r in rows:
        if r.get("NIV") != "3":
            continue
        judet = cod.get(r["JUD"])
        nume = strip_diacritics(r["DENLOC"].strip()).upper()
        if nume.startswith("SATUL "):
            nume = nume[len("SATUL "):]
        # Aceleasi doua garduri ca la indexul global: sub 5 litere numele se ciocnesc de
        # cuvinte obisnuite, iar STOPWORDS sunt exact numele care apar mai des cu sensul lor
        # comun decat ca localitate. Judetul sursei nu apara de „Unirea" dintr-o propozitie.
        if not judet or len(nume) < 5 or nume in STOPWORDS:
            scoase += 1
            continue
        out.setdefault(judet, set()).add(nume)
    return {j: sorted(n) for j, n in sorted(out.items())}, scoase


def main() -> int:
    gaz, tinut = construieste()
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["nume", "nivel"])
        for nume in sorted(gaz):
            w.writerow([nume, gaz[nume]])
    print(f"gazetteer.csv: {len(gaz)} nume")
    print(f"  judete: {tinut['judet']}  UAT-uri: {tinut['uat']}")
    print(f"  sate pastrate: {tinut['sat_ok']}  sate scoase (ambigue/scurte/comune): {tinut['sat_scos']}")

    sate, scoase = sate_pe_judet()
    with open(OUT_SATE, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["judet", "nume"])
        for judet, nume in sate.items():
            for n in nume:
                w.writerow([judet, n])
    print(f"sate_judet.csv: {sum(len(n) for n in sate.values())} sate pe {len(sate)} judete "
          f"({scoase} scoase: scurte sau cuvinte comune)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
