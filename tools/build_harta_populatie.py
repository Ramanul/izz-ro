#!/usr/bin/env python3
"""Generatorul numitorului de populație pentru harta știrilor (F3, „moduri de scară").

De ce există: harta afișa doar VOLUM, iar volumul e o funcție de cât de mare e județul.
Un județ mic cu 8 știri și unul mare cu 40 pot avea aceeași intensitate pe cap de locuitor,
însă harta le colora diferit și publicul citea diferența ca pe o diferență de siguranță.
Modul „pe locuitor" are nevoie de un numitor, iar numitorul trebuie să aibă sursă și dată
(altfel mută doar locul unde se minte).

Sursa: `data/localities.json` — populații pe localități (Wikidata; Q659103 comună /
Q16858213 oraș / Q640364 municipiu), în mare parte recensământul INS 2021. Totalul agregat
este comparat mai jos cu totalul INS și iese în ~0,1 %, deci e un numitor bun pentru un
RAPORT (nu o cifră oficială de populație afișată ca atare — asta spune și footnote-ul din
pagină).

Ieșirea: `static/harta-stiri/data/populatie.json`, 42 de județe, chei = codurile din
`map.json` (TIMIS, BUCURESTI, ...). Fișierul e COMIS (ca map.json și data/uat/*.json), fiindcă
site-ul e static; pagina îl cere doar când cititorul comută pe „pe locuitor".

Usage: python tools/build_harta_populatie.py [--check]
       --check: nu scrie nimic, doar verifică fișierul comis (folosit în teste).
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALITATI = os.path.join(ROOT, "data", "localities.json")
MAP_JSON = os.path.join(ROOT, "static", "harta-stiri", "data", "map.json")
OUT = os.path.join(ROOT, "static", "harta-stiri", "data", "populatie.json")

# Totalul recensământului INS 2021, folosit DOAR ca gardă de plauzibilitate în instrument
# (nu se scrie în date). 19.053.815 = populația stabilă, INS, RPL 2021.
TOTAL_INS_2021 = 19_053_815
TOLERANTA = 0.02  # 2 %: sub asta, numitorul e utilizabil pentru ordine de mărime


def _fara_diacritice(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _cheie(text: str) -> str:
    """Formă de comparat: fără diacritice, majuscule, fără cratime, fără „Județul"."""
    text = re.sub(r"^jude[tț]ul\s+", "", (text or "").strip(), flags=re.I)
    return " ".join(_fara_diacritice(text).upper().replace("-", " ").split())


def harta_coduri() -> dict[str, str]:
    """{formă normalizată a numelui: codul din map.json}.

    Cheile din map.json NU sunt uniforme („SATU MARE" cu spațiu, „BISTRITA-NASAUD" cu
    cratimă), deci potrivirea se face pe forma normalizată, nu prin înlocuirea unui
    separator ghicit. Bucureștiul are o regulă proprie: în gazetteer apare cu `judet` =
    „România" (singura localitate din țară fără județ în sursă).
    """
    coduri = _coduri_harta()
    tabel: dict[str, str] = {}
    for cod in coduri:
        tabel[_cheie(cod)] = cod
    tabel["ROMANIA"] = "BUCURESTI"
    return tabel


def _coduri_harta() -> list[str]:
    with open(MAP_JSON, encoding="utf-8") as fh:
        date = json.load(fh)
    return sorted((date.get("map") or {}).get("judete") or {})


def construieste() -> dict:
    coduri = _coduri_harta()
    tabel = harta_coduri()
    with open(LOCALITATI, encoding="utf-8") as fh:
        gaz = json.load(fh)
    populatii: dict[str, int] = {}
    necunoscute: set[str] = set()
    for intrari in (gaz.get("by_name") or {}).values():
        for intrare in intrari:
            pop = intrare.get("pop")
            if not isinstance(pop, int) or pop <= 0:
                continue
            cod = tabel.get(_cheie(intrare.get("judet")))
            if not cod:
                necunoscute.add(intrare.get("judet") or "—")
                continue
            populatii[cod] = populatii.get(cod, 0) + pop
    lipsa = [cod for cod in coduri if cod not in populatii]
    if necunoscute:
        raise SystemExit(f"județe nerecunoscute în gazetteer: {sorted(necunoscute)}")
    if lipsa:
        raise SystemExit(f"județe fără populație: {lipsa}")
    total = sum(populatii.values())
    abatere = (total - TOTAL_INS_2021) / TOTAL_INS_2021
    if abs(abatere) > TOLERANTA:
        raise SystemExit(
            f"totalul agregat ({total:,}) diferă cu {abatere:+.2%} de INS 2021 — "
            "peste toleranța de 2 %, deci numitorul nu mai e utilizabil ca raport"
        )
    return {
        "version": 1,
        "unitate": "locuitori",
        "sursa": str(gaz.get("source") or "").strip() or "Wikidata",
        "referinta": "recensământul INS 2021 (populații pe localități, agregate)",
        "total": total,
        "total_ins_2021": TOTAL_INS_2021,
        "judete": dict(sorted(populatii.items())),
    }


def main() -> int:
    date = construieste()
    text = json.dumps(date, ensure_ascii=False, sort_keys=False, separators=(",", ":")) + "\n"
    if "--check" in sys.argv:
        try:
            with open(OUT, encoding="utf-8") as fh:
                comis = fh.read()
        except OSError as e:
            print(f"LIPSA: {OUT} ({e})", file=sys.stderr)
            return 1
        if comis != text:
            print("DIFERIT: populatie.json comis nu corespunde gazetteer-ului curent",
                  file=sys.stderr)
            return 1
        print(f"ok: {len(date['judete'])} județe, total {date['total']:,}")
        return 0
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    batere = (date["total"] - date["total_ins_2021"]) / date["total_ins_2021"]
    print(f"scris {OUT}")
    print(f"  județe: {len(date['judete'])}")
    print(f"  total:  {date['total']:,} vs INS 2021 {date['total_ins_2021']:,} ({batere:+.2%})")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
