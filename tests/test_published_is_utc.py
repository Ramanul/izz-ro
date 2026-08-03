"""`published` e sortat ca SIR DE CARACTERE, nu ca moment in timp.

`state.save`, `render.by_date` si pagina de subiect fac toate
`sorted(key=lambda a: a.get("published") or "")`. Asta da ordinea corecta doar cat timp toate
valorile sunt in ACELASI fus: `2026-08-03T09:00:00+03:00` e mai devreme decat
`2026-08-03T07:00:00+00:00` ca moment, dar mai tarziu ca sir.

Masurat pe `data/articles.json` la 2026-08-03: **1736 din 1736** de articole sunt pe `+00:00`,
pentru ca `_parse_w3c_date` si `_parse_ro_date` inchid amandoua cu `astimezone(timezone.utc)`.
Deci sortarea e corecta azi — nu prin proiectare, ci pentru ca invariantul tine.

De aceea testele astea apara invariantul in loc sa rescrie sortarea. O cale de intrare noua care
lasa un offset local sau o data naiva sa treaca nu strica nimic zgomotos: articolele apar doar
in ordine gresita pe prima pagina, ceea ce nimeni nu citeste ca defect de cod. Un refactor pe
`datetime` in cele trei locuri ar ascunde exact aceeasi problema mai bine — ordinea ar fi
corecta, dar `published` ar continua sa poarte fusuri amestecate in datele publicate,
in JSON-LD (`datePublished`) si in feed.
"""
import json
import os
import re

import pytest

from generator import fetch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "articles.json")

# Sufixul obligatoriu. `Z` e ISO valid si acelasi moment, dar NU sorteaza la fel ca `+00:00`
# ('Z' = 0x5A, '+' = 0x2B), deci un amestec al celor doua ar sparge exact ordinea.
_UTC_SUFFIX = "+00:00"


def _published(a: dict) -> str:
    return a.get("published") or ""


@pytest.mark.parametrize("raw,asteptat_suffix", [
    ("2026-08-03T09:00:00+03:00", _UTC_SUFFIX),   # offset local -> convertit
    ("2026-08-03T06:00:00Z", _UTC_SUFFIX),        # Z -> forma numerica
    ("2026-08-03T06:00:00", _UTC_SUFFIX),         # naiv -> presupus UTC
    ("2026-08-03", _UTC_SUFFIX),                  # doar data -> miezul noptii UTC
    ("", _UTC_SUFFIX),                            # gol -> acum, tot UTC
    ("nu e o data", _UTC_SUFFIX),                 # negramatical -> acum
])
def test_w3c_parser_normalizes_to_utc(raw, asteptat_suffix):
    assert fetch._parse_w3c_date(raw).endswith(asteptat_suffix)


@pytest.mark.parametrize("raw", ["17.07.2026", "17/07/2026", "2026-07-17", "17 iulie 2026", "aiurea"])
def test_ro_parser_normalizes_to_utc(raw):
    assert fetch._parse_ro_date(raw).endswith(_UTC_SUFFIX)


def test_w3c_parser_converts_rather_than_truncating():
    """Nu e destul sa se termine in +00:00 — ora trebuie sa fie mutata, nu eticheta schimbata."""
    assert fetch._parse_w3c_date("2026-08-03T09:00:00+03:00").startswith("2026-08-03T06:00:00")


def test_string_sort_matches_chronological_sort_on_real_state():
    """Garda de capat: ordinea lexicografica pe care se sprijina codul trebuie sa fie aceeasi
    cu ordinea reala pe datele publicate azi. Daca cele doua se despart, sortarea din
    `state.save` / `render` a inceput sa minta si refactorul pe `datetime` devine necesar."""
    from datetime import datetime
    if not os.path.exists(STATE):
        pytest.skip("data/articles.json lipseste (clona partiala)")
    with open(STATE, encoding="utf-8") as fh:
        arts = [a for a in json.load(fh) if _published(a)]
    if len(arts) < 2:
        pytest.skip("prea putine articole cu data")
    ca_sir = [_published(a) for a in sorted(arts, key=_published, reverse=True)]
    ca_timp = [_published(a) for a in
               sorted(arts, key=lambda a: datetime.fromisoformat(_published(a)), reverse=True)]
    assert ca_sir == ca_timp, "sortarea pe sir nu mai da ordinea cronologica"


def test_state_carries_no_mixed_offsets():
    """Cauza pentru care testul de mai sus ar pica. Verificat separat, ca esecul sa arate
    fusul intrus, nu doua liste lungi care difera."""
    if not os.path.exists(STATE):
        pytest.skip("data/articles.json lipseste (clona partiala)")
    with open(STATE, encoding="utf-8") as fh:
        arts = json.load(fh)
    gresite = {}
    for a in arts:
        p = _published(a)
        if not p:
            continue
        m = re.search(r"([+-]\d{2}:\d{2}|Z)$", p)
        suf = m.group(1) if m else "FARA FUS"
        if suf != _UTC_SUFFIX:
            gresite.setdefault(suf, []).append(a.get("url") or a.get("title") or "?")
    assert not gresite, "published nu mai e uniform UTC: " + json.dumps(
        {k: v[:3] for k, v in gresite.items()}, ensure_ascii=False)
