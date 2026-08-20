"""Citeste `data/raport_copiere.jsonl` si spune, in romana, cat de rau e.

Jurnalul scris de `generator/raport_copiere.py` are un rand per rezumat produs. Unealta
asta il rezuma: distributia, cazurile cele mai apropiate de sursa, si cifra de care e
nevoie ca sa se aleaga un prag. NU decide nimic si nu modifica nimic.

    python tools/citeste_raport_copiere.py [cale.jsonl] [--exemple N]

De ce exista separat de jurnal: pragul de respingere pentru §2.2 nu e stabilit — cautat
in `registru.py` si `HANDOFF.md` inainte de a scrie codul, zero randuri pe subiect. Se
alege dupa ce se vad cifre de pe rulari reale, exact disciplina de la pragul de 16
caractere/cuvant din garda de continut, derivat din 6714 campuri reale.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PRAGURI = (0, 1, 10, 25, 50, 75, 100)


def _pentru_consola(text: str) -> str:
    """Text tiparibil pe consola curenta fara sa cada.

    Nu e cosmetica: consola Windows e cp1252, fragmentele vin din articole reale cu
    diacritice, iar un UnicodeEncodeError ar opri unealta exact pe randul cel mai
    important. Ce nu incape se inlocuieste, nu darama.
    """
    codec = sys.stdout.encoding or "utf-8"
    return (text or "").encode(codec, errors="replace").decode(codec, errors="replace")


def _histograma(valori: list[float]) -> list[tuple[str, int]]:
    """Cate rezumate cad in fiecare banda de procent."""
    benzi = []
    for i, jos in enumerate(PRAGURI[:-1]):
        sus = PRAGURI[i + 1]
        n = sum(1 for v in valori if jos <= v < sus)
        benzi.append((f"{jos:>3}-{sus:<3}%", n))
    benzi.append((f"{PRAGURI[-1]:>3}%    ", sum(1 for v in valori if v >= PRAGURI[-1])))
    return benzi


def main() -> int:
    argv = sys.argv[1:]
    nr_exemple = 10
    pozitionale = []
    i = 0
    while i < len(argv):
        if argv[i] == "--exemple" and i + 1 < len(argv):
            nr_exemple = int(argv[i + 1])
            i += 2                     # sare si peste VALOAREA lui, altfel ajunge „cale"
            continue
        if not argv[i].startswith("-"):
            pozitionale.append(argv[i])
        i += 1
    cale = (Path(pozitionale[0]) if pozitionale
            else Path(__file__).resolve().parents[1] / "data" / "raport_copiere.jsonl")

    if not cale.exists():
        print(f"NU EXISTA: {cale}")
        print("Jurnalul se scrie la prima rulare a generatorului cu AI activ.")
        return 1

    randuri = []
    stricate = 0
    for linie in cale.read_text(encoding="utf-8").splitlines():
        linie = linie.strip()
        if not linie:
            continue
        try:
            randuri.append(json.loads(linie))
        except json.JSONDecodeError:
            stricate += 1

    if not randuri:
        print(f"Jurnal gol: {cale}")
        return 1

    print(f"REZUMATE MASURATE: {len(randuri)}")
    if stricate:
        print(f"  (plus {stricate} randuri necitibile, ignorate)")
    for model in ("B", "C"):
        n = sum(1 for r in randuri if r.get("model") == model)
        print(f"  model {model}: {n}")

    for camp, eticheta in (("text_procent", "TEXT (teaser/sinteza)"), ("titlu_procent", "TITLU")):
        valori = [float(r.get(camp) or 0) for r in randuri]
        print(f"\n--- {eticheta}: cat din rezumat exista cuvant-cu-cuvant in sursa ---")
        for banda, n in _histograma(valori):
            procent = 100.0 * n / len(valori)
            bara = "#" * int(procent / 2)
            print(f"  {banda} {n:>6}  {procent:>5.1f}%  {bara}")

    maxime = [int(r.get("text_max_cuvinte") or 0) for r in randuri]
    peste8 = sum(1 for m in maxime if m >= 8)
    print("\n--- CEA MAI LUNGA SECVENTA IDENTICA (cuvinte) ---")
    print(f"  maxim absolut: {max(maxime)}")
    print(f"  rezumate cu 8+ cuvinte consecutive identice: {peste8} "
          f"({100.0 * peste8 / len(maxime):.1f}%)")

    print(f"\n--- CELE MAI APROPIATE DE SURSA (primele {nr_exemple}) ---")
    for r in sorted(randuri, key=lambda x: (-(x.get("text_max_cuvinte") or 0),
                                            -(x.get("text_procent") or 0)))[:nr_exemple]:
        print(f"  [{r.get('model')}] {r.get('text_max_cuvinte')} cuvinte, "
              f"{r.get('text_procent')}% — {r.get('id', '')[:70]}")
        if r.get("fragment"):
            print('       "' + _pentru_consola(r["fragment"]) + '"')

    print("\nPRAGUL NU E STABILIT. Cifrele de mai sus sunt materia prima pentru a-l alege;")
    print("nimic din pipeline nu respinge nimic pe baza lor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
