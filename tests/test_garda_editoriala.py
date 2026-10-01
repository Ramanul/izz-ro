"""Garzi peste output-ul RANDAT pentru doua reguli permanente din CLAUDE.md §7.

De ce exista fisierul asta: ambele reguli erau proza in contract, respectata de cod si de
nimeni impusa. O proprietate corecta pe care n-o verifica nimeni e o proprietate care se
pierde tacut la primul refactor — exact tiparul `IZZ-0192` (garda cu selector mort) si
`IZZ-0286` (regula cu numar de linie vechi).

**Amandoua au fost masurate INAINTE de a fi scrise, pe o randare reala de 15.202 pagini
(2026-09-05), si amandoua treceau deja: 74/74 si 11.718/11.718.** Deci nu repara un bug —
INCUIE un comportament corect. Aia e toata treaba lor.

Deliberat NU e aici: o garda pe concentrarea surselor. Masurata in aceeasi zi (digi24.ro
5,9% din 13.486 de linkuri, 166 de domenii), e sanatoasa — dar un prag pe ea ar depinde de
CONTINUT, nu de cod, si ar inrosi `main` din cauza fluxului de stiri al zilei. Cifra sta in
registru, nu intr-un assert.
"""
import re
from pathlib import Path

H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
TITLU_INTEGRAL = re.compile(r'<details class="source-title">(.*?)</details>', re.S)
CASETA_SURSE = re.compile(
    r'<div class="sources-box">\s*<h2>(Surs[ăa]|Surse)</h2>\s*<ul>(.*?)</ul>', re.S
)
FARA_MARCAJ = re.compile(r"<[^>]+>")


def _pagini_de_articol(radacina: str):
    """Paginile de articol: cele cu caseta de surse (§7 — fiecare articol are exact una)."""
    for cale in Path(radacina).glob("*/*/index.html"):
        text = cale.read_text(encoding="utf-8", errors="replace")
        if "sources-box" in text:
            yield cale, text


def test_titlul_taiat_ramane_accesibil_integral_pe_pagina(output_randat):
    """Un `<h1>` scurtat de `titlu_afisare` obliga la titlul integral pe aceeasi pagina.

    `select.py:titlu_afisare` taie titlurile oficiale foarte lungi ca sa nu rupa ierarhia pe
    mobil, si promite in docstring ca „titlul integral ramane disponibil ca detaliu secundar
    pe pagina". Promisiunea e implementata in `templates/article.html`
    (`<details class="source-title">`) — dar nimic nu o tinea. Fara garda, o stergere din
    sablon ar lasa cititorul care aterizeaza direct pe articol fara nicio cale catre titlul
    complet, si niciun test n-ar pica.
    """
    fara_titlu_integral = []
    taiate = 0
    for cale, html in _pagini_de_articol(output_randat):
        titlu = H1.search(html)
        if not titlu or not FARA_MARCAJ.sub("", titlu.group(1)).strip().endswith("…"):
            continue
        taiate += 1
        bloc = TITLU_INTEGRAL.search(html)
        if not bloc or not FARA_MARCAJ.sub(" ", bloc.group(1)).strip():
            fara_titlu_integral.append(str(cale))

    assert not fara_titlu_integral, (
        f"{len(fara_titlu_integral)} din {taiate} pagini cu titlu scurtat nu ofera titlul "
        f"integral nicaieri: {fara_titlu_integral[:5]}"
    )


def test_eticheta_de_provenienta_urmeaza_numarul_de_surse(output_randat):
    """`Sursă` la exact una, `Surse` la doua sau mai multe — formula permanenta din §7.

    Regula e marcata „PERMANENTA (decizie proprietar 2026-07-04)" si se aplica fiecarei
    suprafete de stire. Pana acum traia doar in contract; un `{{ 'Surse' }}` hardcodat intr-un
    sablon nou ar fi trecut nevazut prin CI.
    """
    gresite = []
    verificate = 0
    for cale, html in _pagini_de_articol(output_randat):
        caseta = CASETA_SURSE.search(html)
        if not caseta:
            gresite.append((str(cale), "caseta de surse neparsabila"))
            continue
        verificate += 1
        eticheta, corp = caseta.group(1), caseta.group(2)
        numar = corp.count("<li>")
        asteptat = "Sursă" if numar == 1 else "Surse"
        if eticheta != asteptat:
            gresite.append((str(cale), f"{eticheta!r} pentru {numar} surse"))

    assert not gresite, (
        f"{len(gresite)} din {verificate + len(gresite)} pagini cu eticheta gresita "
        f"(§7): {gresite[:5]}"
    )
