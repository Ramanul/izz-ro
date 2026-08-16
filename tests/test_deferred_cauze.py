"""`deferred` numara doar ce se poate INTOARCE, nu si ce e respins definitiv.

De ce exista (2026-08-16): raportul de la finalul rularii tiparea „Amanate (buget AI epuizat)"
si punea in acelasi numar doua marimi opuse — itemele lasate afara fiindca s-a terminat bugetul
(revin si se proceseaza la rularea urmatoare) si itemele fara substanta (respinse INAINTE de
clustering si de buget, deci revin la fiecare rulare si sunt respinse din nou, la nesfarsit).

Masurat pe 6 build-uri reale, prin `gh run view --log`:

    rulare            fara substanta   deferred   buget folosit
    31920738670             27            27         11/18
    31915086605             28            28         15/18
    31909820457             29           107         18/18
    31898707192             30           254         18/18

In cele doua rulari in care bugetul NU s-a epuizat, `deferred` era EXACT numarul de iteme fara
substanta — presiune reala pe buget ZERO, raportata ca „buget AI epuizat". Conteaza dincolo de
cosmetica: `specs/STATE.md` pune tocmai cifra asta drept poarta pentru decizia „merita batching
la Model C?", deci o cifra umflata ar fi decis o felie de lucru pe o premisa falsa.
"""
from datetime import datetime, timedelta, timezone

import pytest

from generator import config, main


def _item(url: str, src_extra: int | None, sursa: str = "test_src") -> dict:
    return {
        "url": url, "original_link": url, "source": sursa, "source_name": sursa,
        "title": f"Titlu pentru {url}", "original_title": f"Titlu pentru {url}",
        "description": "", "category": "extern", "model": None,
        "src_extra": src_extra,
        "published": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
    }


# --- predicatul, o singura sursa de adevar ------------------------------------------------

def test_predicatul_taie_exact_sub_prag():
    prag = config.MIN_SUBSTANTA_CUVINTE
    iteme = [_item("https://ex.ro/sub", prag - 1), _item("https://ex.ro/exact", prag),
             _item("https://ex.ro/peste", prag + 40)]
    urls = {i["url"] for i in main.itemele_fara_substanta(iteme)}
    assert urls == {"https://ex.ro/sub"}, "pragul e strict mai mic, nu <="


def test_itemele_fara_src_extra_nu_se_presupun():
    """`src_extra` lipseste pe iteme construite de teste vechi; acolo nu ghicim."""
    assert main.itemele_fara_substanta([_item("https://ex.ro/necunoscut", None)]) == []


def test_process_new_foloseste_acelasi_predicat(monkeypatch):
    """Daca cele doua locuri s-ar desincroniza, cifra ar redeveni gresita in tacere."""
    vazute = []
    monkeypatch.setattr(main, "itemele_fara_substanta",
                        lambda items: (vazute.append(len(items)) or []))
    main.process_new([_item("https://ex.ro/a", 99)], provider=None, budget=0)
    assert vazute, "process_new nu mai trece prin predicatul comun"


# --- cifra raportata ----------------------------------------------------------------------

def _deferred(iteme: list) -> int:
    """Cheama contorul REAL din `main`, nu o copie a formulei lui.

    Prima versiune a testului asta reimplementa aici formula si trecea si cu contorul de
    productie stricat — verificat prin mutatie. De-aia `numara_amanate` a fost scoasa din
    `run()` intr-o functie proprie: ca testul sa poata apela exact codul care ruleaza.
    """
    procesate, folded, _ = main.process_new(iteme, provider=None, budget=0)
    handled = {a.get("url") for a in procesate} | folded
    return main.numara_amanate(iteme, handled)


def test_itemele_fara_substanta_nu_se_numara_ca_amanate():
    """Cazul masurat: buget neatins, iar tot ce „lipsea" erau respingeri definitive."""
    prag = config.MIN_SUBSTANTA_CUVINTE
    iteme = [_item(f"https://ex.ro/gol{n}", prag - 1) for n in range(27)]
    assert _deferred(iteme) == 0, (
        "27 de iteme respinse definitiv au fost raportate ca amanate — exact cifra din "
        "build-ul 31920738670, unde bugetul era 11/18")


def test_amanarea_reala_se_numara_in_continuare():
    """Garda in cealalta directie: fixul nu are voie sa ascunda presiunea adevarata."""
    iteme = [_item(f"https://ex.ro/bun{n}", 99) for n in range(5)]
    assert _deferred(iteme) == 5, "itemele cu substanta, neprocesate, TREBUIE sa apara ca amanate"


def test_amestecul_se_separa_corect():
    prag = config.MIN_SUBSTANTA_CUVINTE
    iteme = ([_item(f"https://ex.ro/gol{n}", prag - 1) for n in range(29)]
             + [_item(f"https://ex.ro/bun{n}", 99) for n in range(78)])
    # tiparul rularii 31909820457: 107 „amanate" = 29 respinse + 78 presiune reala
    assert _deferred(iteme) == 78
    assert len(main.itemele_fara_substanta(iteme)) == 29
