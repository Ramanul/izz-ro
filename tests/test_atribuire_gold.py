"""Poarta de calitate a atribuirii: badge-ul nu are voie sa regreseze pe setul de aur.

De ce exista testul asta si nu doar `tools/eval_atribuire.py`: unealta MASOARA, testul OPRESTE.
Cauza C8 din `specs/atribuire-cercetare-si-plan.md` e ca nu exista nicio masuratoare continua —
663 de articole au stat pe rubrica gresita saptamani intregi si nimeni n-a aflat, fiindca nimic
nu verifica. O unealta pe care trebuie sa-ti amintesti s-o rulezi are exact acelasi mod de esec.

Testul e INDEPENDENT de `data/articles.json`: titlul si sursa sunt inghetate in TSV, iar categoria
folosita e `cat_corecta` (judecata manuala). Altfel setul s-ar goli in 7 zile, pe masura ce
articolele expira — unul deja lipsea la 24 de ore dupa ce a fost construit.

Ce NU acopera: corectitudinea CATEGORIEI, care depinde de pipeline-ul viu si se masoara cu
`tools/eval_atribuire.py` (baseline 2026-08-08: 25/39). Aici se verifica doar functia care alege
locul de pe badge (31/32 la aceeasi data).
"""
import csv
import glob
import os

import pytest

from generator import geo
from generator.util import strip_diacritics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Randurile care NU trec, fiecare cu cauza VERIFICATA — nu cu o presupunere. Lista e o
# CONSTATARE, nu o tinta: cine repara unul il scoate de aici si poarta devine mai stricta.
# Cine adauga unul trebuie sa scrie de ce, altfel lista devine locul unde se ascund regresiile.
CUNOSCUTE = {
    # Verificat din al doilea unghi inainte de a fi declarat expirat: sursa `pressalert` e vie
    # (37 de articole in stare, ultimul in aceeasi zi) si URL-ul nu a fost rescris (zero
    # potriviri dupa coada lui), deci chiar e iesire prin TTL, nu o sursa moarta.
    "21": "articolul expirase cand s-a inghetat setul. RE-captureaza cazul cand setul creste: "
          "„Socolari” lipseste cu totul din gazetteer, iar badge-ul anunta „Timiș” (judetul "
          "declarat al sursei) pentru o comuna din Caras-Severin — afirmatie geografica FALSA",
    # `BUCIUM` e in `_CUVINTE_COMUNE` (geo.py), scos DELIBERAT din index fiindca e si cuvant
    # comun. Nu e o scapare de reparat aici: reintroducerea aduce inapoi fals-pozitivele
    # pentru care lista a fost construita. Compromisul e deja luat si masurat.
    "40": "„Bucium” e exclus intentionat din index ca nume-cuvant-comun; badge-ul cade pe judet",
}


def _gold() -> list[dict]:
    cale = sorted(glob.glob(os.path.join(ROOT, "specs", "gold-geo-*.tsv")))[-1]
    with open(cale, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _norm(s: str) -> str:
    return strip_diacritics(s or "").strip().lower()


def _cazuri():
    """Doar randurile cu un loc de asteptat si cu titlu inghetat."""
    return [r for r in _gold() if r["loc_corect"].strip() and r["titlu"].strip()]


def test_setul_de_aur_nu_si_a_pierdut_datele():
    """Garda peste garda: daca cineva regenereaza TSV-ul fara titluri, testul de mai jos ar
    trece cu zero cazuri si ar raporta verde pe nimic — exact modul de esec pe care poarta
    asta trebuie sa-l previna."""
    fara = [r["idx"] for r in _gold() if not r["titlu"].strip()]
    assert len(fara) <= 1, f"{len(fara)} randuri fara titlu inghetat ({fara})"
    assert len(_cazuri()) >= 30, "prea putine cazuri evaluabile; setul de aur s-a degradat"


@pytest.mark.parametrize("rand", _cazuri(), ids=lambda r: f"gold{r['idx']}")
def test_badgeul_numeste_locul_corect(rand):
    """Pentru fiecare articol judecat manual, badge-ul contine locul corect.

    Categoria folosita e `cat_corecta`, nu cea stocata: intrebarea e „daca articolul e clasificat
    corect, eticheta lui e corecta?". Clasificarea insasi e alta masuratoare, alta unealta.

    **Cele doua asertiuni dinaintea potrivirii nu sunt paranoia, sunt ce face testul capabil sa
    PICE.** Potrivirea e bidirectionala, ca sa accepte judetul drept aproximare adevarata a unei
    localitati („Cluj” pentru „Cluj-Napoca”) — dar asta inseamna ca un badge GOL ar trece pe
    orice, fiindca `"" in orice` e mereu adevarat. Fara garda, o atribuire complet moarta ar
    arata identic cu una care merge, iar poarta ar raporta verde exact cand conteaza cel mai
    mult. La fel, un badge care a cazut inapoi pe numele categoriei („local”) nu e un loc.
    """
    if rand["idx"] in CUNOSCUTE:
        pytest.xfail(CUNOSCUTE[rand["idx"]])
    a = {"title": rand["titlu"], "source": rand["sursa"], "category": rand["cat_corecta"]}
    badge, astept = geo.eticheta_copertei(a), rand["loc_corect"]

    assert badge, f"badge GOL pentru {rand['titlu'][:60]!r} — nicio eticheta de loc"
    assert _norm(badge) != _norm(rand["cat_corecta"]), (
        f"badge={badge!r} a cazut inapoi pe numele categoriei, nu e un loc")
    assert _norm(astept) in _norm(badge) or _norm(badge) in _norm(astept), (
        f"badge={badge!r} dar locul corect e {astept!r} — {rand['titlu'][:60]!r}")
