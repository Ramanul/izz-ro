#!/usr/bin/env python3
"""Amprenta lui `output/`, ca o refactorizare sa se poata dovedi NEUTRA.

DE CE EXISTA: izz.ro e un generator static, deci output-ul e o functie de (cod + date).
Asta e o proprietate rara si puternica: orice refactorizare care nu schimba comportamentul
produce EXACT aceleasi fisiere. Deci certitudinea nu trebuie sa vina din citit cod — vine
din masuratoare. Fara unealta asta, singura verificare a unei restructurari e lectura, iar
`generator/` are 8.515 linii in 22 de module: nimeni nu le citeste onest inainte de fiecare
mutare de functie.

CUM SE FOLOSESTE, in jurul unei refactorizari:

    python -m generator.main --render-only
    python tools/echivalenta.py amprenta /tmp/inainte.json
    # ... refactorizezi ...
    python -m generator.main --render-only
    python tools/echivalenta.py amprenta /tmp/dupa.json
    python tools/echivalenta.py compara /tmp/inainte.json /tmp/dupa.json

    -> „IDENTIC" inseamna ca refactorizarea nu a schimbat NIMIC din ce vede cititorul.

CE NU FACE, ca sa nu fie folosita gresit: nu spune daca o diferenta e buna sau rea. Pentru
o schimbare INTENTIONATA de comportament (ex. fixul `Siria` din 2026-09-02, care a mutat 6
articole), unealta raporteaza corect „6 fisiere difera" — dar judecata daca mutarea e corecta
ramane a omului. Unealta apara refactorizarile, nu fixurile.

LIMITA MASURATA: acopera doar caile de cod pe care datele curente le ATING. O ramura pe care
niciunul din cele 13.462 de articole n-o parcurge poate fi stricata fara ca amprenta sa se
schimbe. De-aia se foloseste IMPREUNA cu coverage (`pytest --cov=generator`), nu in locul lui:
amprenta dovedeste ca ce se executa nu s-a schimbat, coverage-ul spune cat din cod se executa.

NEDETERMINISM: `render.py` pune ceasul in output in cateva locuri (`generated_at` din
build.json, `lastmod`, `expires`, anul din subsol). Alea se normalizeaza inainte de hash —
vezi `_NORMALIZARI`. Daca doua amprente pe ACELASI commit ies diferite, cauza e o sursa de
nedeterminism nenormalizata inca (ordinea unui `set`, un dict neordonat): comanda `compara`
o va arata ca lista de fisiere, si acolo se adauga regula noua.

MASURAT 2026-09-04, prima oara cand unealta a fost intoarsa asupra propriei premise: doua
randari ale ACELUIASI commit pe aceleasi date au dat **953 de fisiere diferite** din 47.222
(zero adaugate sau sterse). Predictia era „IDENTIC" si a fost gresita. Cauza, exact cea
ghicita mai sus: doua `set`-uri de siruri iterate in `render.py`, a caror ordine depinde de
PYTHONHASHSEED — randomizat la fiecare proces — si al caror rezultat intra intr-un `sorted`
STABIL cu chei care nu departajeaza egalitatile. La `[:6]` / `[:3]` asta schimba nu doar
ordinea, ci componenta listei: 945 din 4.307 pagini de subiect („Conexiuni") si 8 din 8.350
pagini de articol („Articole conectate"). Reparat prin chei de departajare deterministe.

A TREIA sursa, gasita abia la reverificare — 953 scazuse la 2, nu la 0: `weight = sum(idf[s]
for s in common)`, unde `common` e tot un `set`. Adunarea in virgula mobila NU e asociativa,
deci aceiasi termeni insumati in alta ordine dau alt ULP: masurat 23.80437088061844 vs
23.804370880618443. Un bit ajunge ca sortarea sa inverseze doi candidati si `[:3]` sa taie
altul. Reparat cu `sorted(common)`. Lectia operationala: dupa un fix de determinism,
reverificarea NU e formalitate — primul fix a lasat 0,2% din defect in urma, iar 0,2%
nedeterminist inseamna tot „plasa nu poate raporta IDENTIC".

Consecinta care conteaza pentru unealta asta: cat timp defectul a existat, `compara` NU putea
raporta „IDENTIC" niciodata, deci plasa care apara refactorizarile era decor. O plasa se
verifica pe ea insasi inainte sa fie crezuta.

A DOUA CAUZA POSIBILA, pe care textul de mai sus n-o numea si care NU s-a manifestat in
masuratoarea aia: ceasul nu intra doar in output, ci si in SELECTIE. `home_fresh()`
(`render.py`, sectiunile de pe homepage) taie la 72h fata de `datetime.now()`. Masurat in
aceeasi zi: 46 de articole ies din fereastra intr-un interval de 20 de minute. Doua amprente
luate la distanta — adica exact scenariul „amprenta, refactorizezi, amprenta" de mai sus —
nu au acelasi input. Pe 09-04 nu a muscat, fiindca articolele de la limita sunt cele mai
VECHI din setul proaspat, iar plafonul e de 4 carduri per categorie cu 41-584 de articole
proaspete in fiecare; dar in `regional`, cu 2 articole proaspete, tot ce e proaspat se
afiseaza, deci acolo un singur articol care traverseaza pragul schimba pagina. Cand `compara`
iese DIFERIT, discriminatorul e LISTA: diferente limitate la `index.html` (si eventual
`art-card.webp`) inseamna ceasul; orice altceva inseamna nedeterminism in cod.
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")

# Tipare care contin CEASUL, nu continut: se inlocuiesc cu un marcaj fix inainte de hash.
# Fiecare are un comentariu cu locul din care vine, ca sa se poata verifica.
_NORMALIZARI = [
    # render.py:1097 — `generated_at` din build.json, se schimba la FIECARE rulare
    (re.compile(rb'"generated_at"\s*:\s*"[^"]*"'), b'"generated_at":"<CEAS>"'),
    # data-time ISO complet, oriunde in HTML (lastmod din sitemap, dateModified din JSON-LD)
    (re.compile(rb'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})'), b'<CEAS>'),
    # render.py:1745 — data RFC 2822 din feed (`Wed, 02 Sep 2026 15:04:05 +0000`)
    (re.compile(rb'[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} [+-]\d{4}'), b'<CEAS>'),
    # `?v=<hash>` pe active: se schimba doar cand se schimba fisierul, deci NU se normalizeaza.
    # Daca s-ar normaliza, o pierdere de cache-bust (sect. 16.2) ar deveni invizibila aici.
]


def _normalizeaza(continut: bytes) -> bytes:
    for tipar, inlocuire in _NORMALIZARI:
        continut = tipar.sub(inlocuire, continut)
    return continut


def amprenta(out_dir: str) -> dict:
    """{cale relativa: sha256 al continutului normalizat}."""
    if not os.path.isdir(out_dir):
        raise SystemExit(f"!! {out_dir} lipseste — ruleaza intai `python -m generator.main --render-only`")
    rez = {}
    for radacina, _, fisiere in os.walk(out_dir):
        for f in fisiere:
            cale = os.path.join(radacina, f)
            rel = os.path.relpath(cale, out_dir)
            with open(cale, "rb") as fh:
                rez[rel] = hashlib.sha256(_normalizeaza(fh.read())).hexdigest()
    return rez


def compara(a: dict, b: dict) -> int:
    """0 daca identice. Tipareste diferentele grupate, nu la gramada."""
    doar_a = sorted(set(a) - set(b))
    doar_b = sorted(set(b) - set(a))
    difera = sorted(k for k in set(a) & set(b) if a[k] != b[k])

    if not (doar_a or doar_b or difera):
        print(f"IDENTIC — {len(a)} fisiere, acelasi continut normalizat.")
        print("Refactorizarea NU a schimbat nimic din ce vede cititorul.")
        return 0

    print(f"DIFERIT — {len(a)} vs {len(b)} fisiere")
    for eticheta, lst in (("doar in PRIMA", doar_a), ("doar in A DOUA", doar_b),
                          ("continut schimbat", difera)):
        if lst:
            print(f"\n  {eticheta}: {len(lst)}")
            for k in lst[:25]:
                print(f"    {k}")
            if len(lst) > 25:
                print(f"    ... si inca {len(lst) - 25}")
    print("\nO diferenta NU inseamna automat regresie: un fix intentionat schimba output-ul.")
    print("Inseamna doar ca schimbarea nu e neutra, deci cere judecata, nu doar teste verzi.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("amprenta", help="hash-urile lui output/, intr-un JSON")
    p1.add_argument("iesire")
    p1.add_argument("--dir", default=OUT, help=f"implicit {OUT}")

    p2 = sub.add_parser("compara", help="doua amprente; iese 1 daca difera")
    p2.add_argument("a")
    p2.add_argument("b")

    args = ap.parse_args()
    if args.cmd == "amprenta":
        h = amprenta(args.dir)
        with open(args.iesire, "w", encoding="utf-8") as fh:
            json.dump(h, fh, sort_keys=True)
        print(f"{len(h)} fisiere amprentate -> {args.iesire}")
        return 0

    with open(args.a, encoding="utf-8") as fh:
        a = json.load(fh)
    with open(args.b, encoding="utf-8") as fh:
        b = json.load(fh)
    return compara(a, b)


if __name__ == "__main__":
    sys.exit(main())
