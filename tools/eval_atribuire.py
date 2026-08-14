#!/usr/bin/env python3
"""Masoara atribuirea (categorie + loc pe badge) pe setul de aur. Cifra, nu impresie.

De ce exista: pana acum fiecare masuratoare de clasificare a fost aruncata dupa ce a fost facuta,
deci nimeni nu putea spune „am reparat" — doar „am schimbat". Cu 663 de articole care au stat pe
rubrica gresita saptamani intregi fara ca cineva sa afle (vezi `specs/atribuire-cercetare-si-plan.md`
C7/C8), lipsa masuratorii E defectul, nu un lux.

Ruleaza:  python tools/eval_atribuire.py [--verbose]
Iesire:   trei fractii — categoria STOCATA, categoria pe CODUL DE AZI, locul de pe badge.

**De ce trei si nu doua (2026-08-09).** Prima versiune raporta o singura fractie de categorie,
citita din `articles.json`, si aia descria DATELE, nu codul. Cifra ei — 25/39, 64% — a ajuns in
`specs/STATE.md` ca stare a atribuirii si era gata sa trimita felia urmatoare sa repare o logica
deja reparata: 8 din cele 14 rateuri erau victime ale lui `_resync_pinned` (#165), pe care codul de
azi le clasifica CORECT si care se vindeca singure prin expirare. Categoria se calculeaza la
ingestie, deci orice fix are o fereastra oarba de ~7 zile in care masuratoarea pe date stocate
arata vechiul defect. O unealta care nu separa cele doua raporteaza la infinit un defect inexistent.

Cele trei verdicte pe un rand picat, in ordinea crescatoare a gravitatii:
  DATE VECHI   — codul de azi da corect; articolul stocat asteapta expirarea. Nimic de facut.
  LIPSA ai_cat — codul de azi da gresit, dar articolului ii lipseste tema modelului (nu se salva
                 inainte de #159). Cu tema recuperata din judecata manuala iese corect, deci nu e
                 logica de reparat, e un camp absent. Se vindeca tot prin rostogolirea corpusului.
  PICA AZI     — codul dezaproba judecata manuala si cu intrarile complete. **Singurul care
                 justifica o felie** — dar citeste cazul inainte sa scrii cod: eticheta spune
                 „cod != om", nu „codul greseste". Setul de aur e referinta, insa e judecata
                 omeneasca si poate fi ea de revizuit. Exemplu masurat 2026-08-09: #31, unde
                 titlul zice „judetul Brasov" iar teaserul rafineaza la Sercaia — codul da `local`
                 dupa regula proprietarului („LOCAL = unde se intampla") si e apararabil; #26,
                 unde textul enumera DOUA judete si tot iese `local`, nu e.

**Randurile PICA AZI sunt clasa de erori pe care versiunea veche nu o putea vedea deloc**, fiindca
ea compara doar ce e STOCAT: un articol clasificat corect la ingestie, pe care o schimbare
ulterioara de cod l-ar strica, trecea drept verde. Regresia s-ar fi vazut abia peste 7 zile, in
date, dupa ce ajungea la cititori.

Compara starea de ACUM a codului cu judecata manuala din `specs/gold-geo-*.tsv`. Nu foloseste
coloana `badge_verdict` din TSV ca adevar: aia a fost data pe codul de la momentul judecatii, iar
codul se schimba. Adevarul e `cat_corecta` + `loc_corect`, care sunt judecati despre STIRE, nu
despre cod, deci nu expira.
"""
import argparse
import csv
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from generator import config, htmlart, process  # noqa: E402
from generator.util import strip_diacritics  # noqa: E402

# Rubricile geografice: pentru ele `ai_cat` nu poate fi recuperat din judecata manuala, fiindca
# `cat_corecta` e atunci rezultatul axei geografice, nu tema aleasa de model.
_GEO = ("local", "judetean", "regional")


def _norm(s: str) -> str:
    return strip_diacritics(s or "").strip().lower()


def _tema_recuperata(rand: dict) -> str | None:
    """Tema pe care modelul ar fi ales-o, dedusa din judecata manuala — DOAR pentru rubricile
    tematice. Nu e circular: `ai_cat` e o INTRARE a lui `_resolve_category` (tema povestii), iar
    `cat_corecta` e IESIREA asteptata (rubrica). Sunt acelasi cuvant doar cand stirea pleaca de pe
    axa geografica — exact cazul sportului, unde lipsa campului e tot defectul.
    """
    corecta = _norm(rand["cat_corecta"])
    if corecta in _GEO or corecta == "general":
        return None
    return corecta if corecta in {_norm(c) for c in config.CATEGORIES} else None


def _gold(path: str | None = None) -> list[dict]:
    """Cel mai recent set de aur din `specs/`, sau cel indicat."""
    if not path:
        cand = sorted(glob.glob(os.path.join(ROOT, "specs", "gold-geo-*.tsv")))
        if not cand:
            raise SystemExit("!! niciun specs/gold-geo-*.tsv")
        path = cand[-1]
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _articole() -> dict:
    """{url: articol} din starea pipeline-ului."""
    with open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8") as fh:
        date = json.load(fh)
    lst = date if isinstance(date, list) else (date.get("articles") or [])
    return {a["url"]: a for a in lst if isinstance(a, dict) and a.get("url")}


def evalueaza(verbose: bool = False) -> int:
    rows, arts = _gold(), _articole()
    lipsa = [r for r in rows if r["url"] not in arts]
    prezente = [r for r in rows if r["url"] in arts]

    cat_ok = azi_ok = loc_ok = loc_total = 0
    n_vechi = n_lipsa = n_defect = 0
    picate = []
    for r in prezente:
        a = arts[r["url"]]
        # 1. Categoria STOCATA (ce vede cititorul acum) vs cea judecata manual
        corect = _norm(r["cat_corecta"])
        stocat_ok = _norm(a.get("category")) == corect
        cat_ok += stocat_ok

        # 2. Categoria pe CODUL DE AZI, pe aceleasi date de intrare. Diferenta fata de (1) e
        #    fereastra oarba: fix aterizat, articol vechi neatins.
        #    Anunturile oficiale (`pl_`/`cj_`/`pr_`) NU trec prin `_resolve_category` in productie:
        #    `main.process_new` le trimite la `process_official` -> `process_single(it, None)`, care
        #    iese la `provider is None` fara sa atinga `category`; rubrica ramane cea declarata a
        #    sursei (`local_sources.py:133`). A le recalcula aici ar masura o cale care nu ruleaza —
        #    prima versiune a facut exact asta si raporta 6 „defecte" inexistente (2026-08-09).
        if str(a.get("source", "")).startswith(process.OFFICIAL_PREFIXES):
            azi = _norm(a.get("category"))
        else:
            azi = _norm(process._resolve_category(a, a.get("ai_cat") or "", a.get("entities")))
        azi_ok += azi == corect
        if azi == corect and not stocat_ok:
            n_vechi += 1
            picate.append(("DATE VECHI", r["idx"], f"stocat={a.get('category')} -> codul de azi da"
                           f" {azi!r}, corect; asteapta expirarea", (a.get("title") or "")[:52]))
        elif azi != corect:
            # Greseste si azi. Intrare lipsa sau logica? Distinctia nu e cosmetica: prima se
            # vindeca singura, a doua cere o felie.
            tema = _tema_recuperata(r) if not a.get("ai_cat") else None
            if tema and _norm(process._resolve_category(a, tema, a.get("entities"))) == corect:
                n_lipsa += 1
                eticheta, ce = "LIPSA ai_cat", (f"azi={azi!r}, corect={corect!r}; cu tema {tema!r} "
                                                f"recuperata iese corect — articol pre-#159")
            else:
                n_defect += 1
                eticheta, ce = "PICA AZI", f"azi={azi!r} != {corect!r} cu intrarile complete"
            picate.append((eticheta, r["idx"], ce, (a.get("title") or "")[:52]))
        # 2. Locul de pe badge — doar unde exista un loc corect de asteptat
        astept = r["loc_corect"].strip()
        if not astept:
            continue
        loc_total += 1
        badge = htmlart._eticheta(a)
        if _norm(astept) in _norm(badge) or _norm(badge) in _norm(astept):
            loc_ok += 1
        else:
            picate.append(("LOC", r["idx"], f"badge={badge!r} != {astept!r}",
                           (a.get("title") or "")[:52]))

    n = len(prezente)
    pct = lambda k, t: f"  ({k/t:.0%})" if t else ""  # noqa: E731
    print(f"set de aur: {len(rows)} randuri, {n} inca in articles.json"
          + (f", {len(lipsa)} expirate (ignorate)" if lipsa else ""))
    print(f"  categorie STOCATA (ce vede cititorul): {cat_ok}/{n}{pct(cat_ok, n)}")
    print(f"  categorie pe CODUL DE AZI            : {azi_ok}/{n}{pct(azi_ok, n)}")
    print(f"  loc corect pe badge                  : {loc_ok}/{loc_total}{pct(loc_ok, loc_total)}")
    print(f"\n  din rateuri: {n_vechi} date vechi (se vindeca prin expirare) · "
          f"{n_lipsa} lipsa ai_cat (idem) · {n_defect} pica pe codul de azi")
    if n_defect:
        print("  ^ doar ultima cifra justifica o felie — si citeste cazul intai, poate fi\n"
              "    judecata din setul de aur cea de revizuit, nu codul.")
    if verbose and picate:
        print("\n  picate:")
        for tip, idx, ce, titlu in picate:
            print(f"    [{tip}] #{idx:>2}  {ce}\n           {titlu}")
    elif picate:
        print("  (--verbose pentru randurile picate)")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verbose", "-v", action="store_true")
    sys.exit(evalueaza(p.parse_args().verbose))
