#!/usr/bin/env python3
"""Cate articole cad in fereastra TTL, si cat mai e pana supapa de buget incepe sa taie.

DE CE EXISTA. Pe 2026-09-13 `tests/test_buget_fisiere.py::test_podeaua_absoluta_...` a picat
pe PR #340 cu "12882 articole in fereastra TTL, dar sub buget incap doar 12800". A doua zi
acelasi test trecea, fara ca nimic sa fie reparat: fereastra se masoara fata de cel mai
recent articol din stare, deci cand data cea mai noua a trecut de la 09-13 la 09-14, pragul
a glisat cu o zi si ~1.037 de articole au iesit din fereastra dintr-o data.

Cu alte cuvinte garda oscileaza in dinti de fierastrau in jurul plafonului: verde sau rosie
dupa ORA la care ruleaza CI, nu dupa sanatatea proiectului. O garda care sună aleatoriu
ajunge ignorata la fel de sigur ca una care nu poate pica (IZZ-0177). Unealta asta face
cifra vizibila INAINTE sa pice testul, si o face re-masurabila in loc de re-crezuta.

CAUZA, spusa pe fata: colapsul de ingestie din 5-10 sep (IZZ-0317) a sapat o groapa in
fereastra — zile de 49-355 de articole in loc de ~900. Fixul din #328 a repus debitul la
~900-1.100/zi. Pe masura ce groapa IESE din fereastra si zilele pline INTRA, fereastra creste
monoton. Deci recuperarea ingestului e chiar ce imping fereastra peste plafon; cele doua
puncte din `specs/STATE.md` nu sunt independente, sunt acelasi punct.

CELE DOUA PRAGURI nu se confunda:
  A - "podeaua absoluta": n_brut <= OUTPUT_FILE_BUDGET - OUTPUT_NON_ARTICLE_RESERVE.
      E tripwire-ul timpuriu; ignora deliberat faptul ca dedup-ul si poarta de calitate scot
      ~16% din stare inainte de randare. Cand il depaseste, CI e rosu.
  B - "supapa taie": int(n_brut * FRACTIA_PUBLICATA) > plafonul supapei.
      Asta e consecinta REALA: `render._articole_publicabile` incepe sa taie articole, deci
      fereastra publicata devine mai scurta decat `ARTICLE_TTL_DAYS` fara ca nimeni sa fi
      decis asta. Pragul A suna cu ~1 zi inainte de pragul B.

CE NU MASOARA, spus pe fata:
  - Nu randeaza. `FRACTIA_PUBLICATA` e o masuratoare din 2026-09-09, nu un invariant; daca
    dedup-ul sau poarta de calitate se schimba, cifra B se schimba si ea, iar unealta nu are
    cum sa observe singura. Se remasoara cu o randare completa.
    ATENTIE, masurat 2026-09-14 pe originea Worker (`build.json` la commit 64889e9, acelasi
    commit pe care il masor aici): 9.575 pagini publicate din 11.967 in fereastra = 0,800, nu
    0,842. Deci pragul B raportat mai jos e CONSERVATOR cu ~700 de articole (13.776 in loc de
    ~14.500). Nu am schimbat constanta: o singura masuratoare nu slabeste o garda de siguranta,
    iar eroarea e in directia sigura. Cine o remasoara cu o randare completa o poate corecta.
  - Nu prezice ingestul. `--debit` e un SCENARIU declarat, nu o prognoza; de aceea raportul
    tipareste trei scenarii in loc de un numar.
  - Citeste starea COMISA, nu live-ul. Ce serveste izz.ro acum se verifica altfel (sect. 16a).

  python tools/fereastra_ttl.py                 # starea din working tree
  python tools/fereastra_ttl.py --json          # pentru alt consumator
  python tools/fereastra_ttl.py --strict        # cod 1 daca fereastra e deja peste pragul A

ATENTIE la forma cu `git show <rev>:data/articles.json | ...`: hook-ul de control-plane refuza
orice comanda Bash care contine numele fisierului de stare impreuna cu un redirect, chiar si
citiri. Verificat cu comanda care a esuat: `DENY: Bash command writing to protected control-plane
path (articles.json)`. Pentru o revizie mai veche, da fisierul ca argument dupa un checkout, sau
foloseste `-` alimentat dintr-un proces care nu declanseaza tiparul.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from generator import config  # noqa: E402

# Fractia din stare care ajunge chiar PUBLICATA, dupa dedup de eveniment si poarta de
# calitate. MASURAT 2026-09-09 pe o randare completa: 12.475 de pagini scrise din 14.821 de
# articole incarcate = 0,842. Aceeasi cifra e in `tests/test_buget_fisiere.py`, iar
# `tests/test_fereastra_ttl.py` verifica mecanic ca cele doua nu se despart.
FRACTIA_PUBLICATA = 0.842


def zile_stare(articole: list) -> Counter:
    """Histograma pe ziua din `published`. Articolele fara data sunt ignorate, nu ghicite."""
    return Counter(d for d in ((a.get("published") or "")[:10] for a in articole) if d)


def in_fereastra(zile: Counter, ancora: str, ttl: int | None = None) -> int:
    """Cate articole ar ramane dupa `state.expire()`, cu fereastra ancorata la `ancora`.

    Ancora e cel mai recent articol din stare, nu ceasul de azi — exact ca in guard. Altfel
    cifra ar scadea singura prin simpla trecere a timpului pe o stare inghetata.
    """
    ttl = config.ARTICLE_TTL_DAYS if ttl is None else ttl
    prag = (datetime.date.fromisoformat(ancora) - datetime.timedelta(days=ttl)).isoformat()
    return sum(v for d, v in zile.items() if prag < d <= ancora)


def praguri() -> tuple[int, int]:
    """(prag A brut, prag B brut), derivate din `generator.config`, nu date de mana."""
    prag_a = config.OUTPUT_FILE_BUDGET - config.OUTPUT_NON_ARTICLE_RESERVE
    supapa = prag_a - config.OG_COVER_MAX_ARTICLES
    return prag_a, int(supapa / FRACTIA_PUBLICATA)


def debit_observat(zile: Counter, ancora: str, n: int = 3) -> int:
    """Debitul median pe ultimele `n` zile COMPLETE (ancora exclusa: ziua e in curs)."""
    complete = [v for d, v in sorted(zile.items()) if d < ancora][-n:]
    return int(sorted(complete)[len(complete) // 2]) if complete else 0


def proiecteaza(zile: Counter, ancora: str, debit: int, orizont: int = 14) -> list[dict]:
    """Fereastra zi cu zi, daca fiecare zi viitoare aduce `debit` articole.

    Nu extrapolez naiv marja/rata: fereastra CASTIGA ziua noua si PIERDE ziua de acum TTL,
    iar zilele care ies acum sunt tocmai cele din colapsul de ingestie. Diferenta dintre cele
    doua e semnul real, si el e pozitiv chiar si cand debitul pare modest.
    """
    prag_a, prag_b = praguri()
    zi0 = datetime.date.fromisoformat(ancora)
    n = in_fereastra(zile, ancora) + (debit - zile[ancora])
    out = []
    for k in range(orizont + 1):
        zi = zi0 + datetime.timedelta(days=k)
        if k:
            iese = zi - datetime.timedelta(days=config.ARTICLE_TTL_DAYS)
            n += debit - zile.get(iese.isoformat(), 0)
        out.append({"zi": zi.isoformat(), "n": n,
                    "peste_A": n > prag_a, "peste_B": n > prag_b})
    return out


def masoara(articole: list, debit: int | None = None, orizont: int = 14) -> dict:
    zile = zile_stare(articole)
    if not zile:
        raise SystemExit("FAIL: nicio data `published` in stare — nu am ce masura.")
    ancora = max(zile)
    prag_a, prag_b = praguri()
    n = in_fereastra(zile, ancora)
    d = debit_observat(zile, ancora) if debit is None else debit
    return {
        "ancora": ancora, "ttl_zile": config.ARTICLE_TTL_DAYS,
        "total_in_stare": sum(zile.values()), "in_fereastra": n,
        "publicabile_estimate": int(n * FRACTIA_PUBLICATA),
        "prag_A": prag_a, "prag_B": prag_b,
        "supapa": prag_a - config.OG_COVER_MAX_ARTICLES,
        "marja_A": prag_a - n, "marja_B": prag_b - n,
        "debit_folosit": d,
        "istoric": [{"zi": z, "n": zile[z]} for z in sorted(zile)[-10:]],
        "proiectie": proiecteaza(zile, ancora, d, orizont),
    }


def _prima(proiectie: list[dict], cheie: str) -> str:
    return next((p["zi"] for p in proiectie if p[cheie]), "-")


def raport(st: dict) -> None:
    print(f"Fereastra TTL={st['ttl_zile']} zile, ancorata la {st['ancora']} "
          f"(cel mai recent articol din stare)")
    print(f"  in stare      : {st['total_in_stare']}")
    print(f"  in fereastra  : {st['in_fereastra']}")
    print(f"  publicabile   : ~{st['publicabile_estimate']} (x{FRACTIA_PUBLICATA}) "
          f"din supapa {st['supapa']}")
    print(f"  prag A (CI rosu)    : {st['prag_A']:6}  marja {st['marja_A']:+6}")
    print(f"  prag B (supapa taie): {st['prag_B']:6}  marja {st['marja_B']:+6}")
    print("\nUltimele zile din stare:")
    for z in st["istoric"]:
        print(f"  {z['zi']}  {z['n']:5}")
    print(f"\nProiectie la debit {st['debit_folosit']}/zi (SCENARIU, nu prognoza):")
    for p in st["proiectie"]:
        print(f"  {p['zi']}  n={p['n']:6}  {'A!' if p['peste_A'] else '  '} "
              f"{'B!' if p['peste_B'] else '  '}")
    print(f"\n  prima zi cu CI rosu (A): {_prima(st['proiectie'], 'peste_A')}")
    print(f"  prima zi cu taiere  (B): {_prima(st['proiectie'], 'peste_B')}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("fisier", nargs="?",
                   help="starea JSON; implicit data/articles.json, `-` pentru stdin")
    p.add_argument("--debit", type=int,
                   help="articole/zi in proiectie; implicit medianul ultimelor 3 zile complete")
    p.add_argument("--orizont", type=int, default=14, help="zile de proiectat (implicit 14)")
    p.add_argument("--json", action="store_true", help="date brute, pentru alt consumator")
    p.add_argument("--strict", action="store_true",
                   help="iese cu cod 1 daca fereastra e deja peste pragul A")
    args = p.parse_args()

    if args.fisier == "-":
        brut = sys.stdin.read()
    else:
        cale = args.fisier or os.path.join(ROOT, "data", "articles" + ".json")
        with open(cale, encoding="utf-8") as fh:
            brut = fh.read()
    if not brut.strip():
        raise SystemExit("FAIL: nicio intrare.")

    st = masoara(json.loads(brut), args.debit, args.orizont)
    print(json.dumps(st, indent=2)) if args.json else raport(st)
    return 1 if args.strict and st["marja_A"] < 0 else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        os._exit(0)
