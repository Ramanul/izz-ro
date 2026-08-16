"""Poarta de calitate a atribuirii: badge-ul nu are voie sa regreseze pe setul de aur.

De ce exista testul asta si nu doar `tools/eval_atribuire.py`: unealta MASOARA, testul OPRESTE.
Cauza C8 din `specs/atribuire-cercetare-si-plan.md` e ca nu exista nicio masuratoare continua —
663 de articole au stat pe rubrica gresita saptamani intregi si nimeni n-a aflat, fiindca nimic
nu verifica. O unealta pe care trebuie sa-ti amintesti s-o rulezi are exact acelasi mod de esec.

Testul e INDEPENDENT de `data/articles.json`: titlul si sursa sunt inghetate in TSV, iar categoria
folosita e `cat_corecta` (judecata manuala). Altfel setul s-ar goli in 7 zile, pe masura ce
articolele expira — unul deja lipsea la 24 de ore dupa ce a fost construit.

Doua porti, nu una (a doua adaugata 2026-08-09):
  1. badge-ul numeste locul corect — `geo.eticheta_copertei` (31/32)
  2. nivelul geografic nu regreseaza — `geo.clasifica` (15/20)

Ce NU acopera nici acum: rubrica FINALA, cand ea depinde de tema aleasa de model (`ai_cat`).
Aia nu e deterministica, deci nu are ce cauta intr-o poarta — se masoara cu
`tools/eval_atribuire.py`, care raporteaza separat categoria stocata si categoria pe codul de azi.
"""
import csv
import glob
import os

import pytest

from generator import geo
from generator.process import OFFICIAL_PREFIXES
from generator.util import strip_diacritics

# Rubricile deciise de `geo.clasifica`. Restul (`sport`, `general`, teme) vin din `ai_cat`.
NIVELURI = {"local", "judetean", "regional"}

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


# Randurile pe care `geo.clasifica` le da altfel decat omul. Ca si CUNOSCUTE, e o CONSTATARE
# masurata 2026-08-09, nu o tinta — iar eticheta e „cod != om", nu „codul greseste": #31 arata
# ca uneori judecata din setul de aur e cea de revizuit.
CUNOSCUTE_NIVEL = {
    # Teaserul zice „Sublocotenentul Razvan BUDA"; BUDA e comuna (jud. Buzau), deci un nume de
    # PERSOANA deschide axa locala. Verificat: pe titlul singur iese `judetean`, corect — teaserul
    # e cel care strica. Clasa de defect: antroponim omonim cu UAT.
    "24": "numele de familie „Buda” din teaser potriveste comuna omonima -> `local` in loc de "
          "`judetean`; pe titlul singur clasificarea e corecta",
    # „Perchezitii ample in Maramures SI Suceava": SUCEAVA e si municipiu-resedinta, iar
    # potrivirea pe UAT bate potrivirea pe judet. Doua judete numite nu pot da o stire locala
    # prin nicio citire — asta e defectul cel mai clar din cele cinci.
    "26": "textul enumera DOUA judete; SUCEAVA prinde ca municipiu si nivelul cade la `local`",
    "27": "„la Brasov” — nume simultan municipiu si judet; codul alege mereu municipiul, omul a "
          "judecat judetean (tribunal = nivel judetean)",
    # NU e o regresie de reparat: teaserul chiar rafineaza locul la Sercaia, iar regula
    # proprietarului („LOCAL = unde se intampla”) da `local`. Ramane aici ca sa nu inroseasca
    # poarta, dar cine o repara ar trebui sa corecteze TSV-ul, nu `geo.py`.
    "31": "APARABIL: titlul zice „judetul Brasov”, teaserul rafineaza la Sercaia -> `local` e "
          "corect dupa regula proprietarului; de revizuit judecata din TSV, nu codul",
    "37": "„la Botosani” — acelasi nume ambiguu oras/judet ca #27",
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


def _cazuri_nivel():
    """Randurile pe care `geo.clasifica` chiar le decide in productie.

    Sursele oficiale (`pl_`/`cj_`/`pr_`) sunt EXCLUSE, si nu ca sa fie poarta mai verde:
    `main.process_new` le trimite la `process_official` -> `process_single(it, None)`, care iese
    la `provider is None` fara sa atinga `category`. Rubrica lor vine declarata din
    `local_sources.py`. A le trece prin `clasifica` ar testa o cale care nu ruleaza.
    """
    return [r for r in _gold()
            if r["cat_corecta"].strip() in NIVELURI
            and r["titlu"].strip()
            and not r["sursa"].startswith(OFFICIAL_PREFIXES)]


def test_setul_de_aur_nu_si_a_pierdut_datele():
    """Garda peste garda: daca cineva regenereaza TSV-ul fara titluri, testul de mai jos ar
    trece cu zero cazuri si ar raporta verde pe nimic — exact modul de esec pe care poarta
    asta trebuie sa-l previna."""
    fara = [r["idx"] for r in _gold() if not r["titlu"].strip()]
    assert len(fara) <= 1, f"{len(fara)} randuri fara titlu inghetat ({fara})"
    assert len(_cazuri()) >= 30, "prea putine cazuri evaluabile; setul de aur s-a degradat"
    assert len(_cazuri_nivel()) >= 18, (
        f"doar {len(_cazuri_nivel())} cazuri de nivel geografic; poarta s-a ingustat tacit")
    fara_teaser = [r["idx"] for r in _cazuri_nivel() if not r["teaser"].strip()]
    assert len(fara_teaser) <= 2, (
        f"{len(fara_teaser)} randuri fara teaser inghetat ({fara_teaser}) — clasificarea "
        f"citeste title+teaser, deci fara el poarta masoara altceva decat productia")
    # Fara cazuri ne-`local` care chiar se evalueaza, poarta de nivel nu poate deosebi
    # clasificarea corecta de un cod care raspunde „local" la orice.
    #
    # Istoricul pragului, fiindca e o MASURATOARE, nu o preferinta:
    #   2026-08-12: 1 singur caz (#34). Comentariul de atunci spunea „minimul absolut, nu o tinta".
    #   2026-08-16: 11 randuri noi (#41-#51), toate `judetean` de la surse NEOFICIALE — alea sunt
    #               singurele care ajung la `clasifica` in productie (vezi `_cazuri_nivel`).
    #               Verificat prin mutatie, `clasifica` -> mereu „local": pica 12, era 1.
    # Pragul e 8, nu 12: lasa loc ca 3-4 randuri sa treaca in CUNOSCUTE_NIVEL daca o schimbare
    # viitoare de clasificare le muta, fara sa devina o poarta care se rescrie la fiecare felie.
    # Sub 8 inseamna ca setul s-a erodat destul cat sa merite completat, nu ca a picat ceva.
    MINIM_DISCRIMINANTE = 8
    discrimineaza = [r["idx"] for r in _cazuri_nivel()
                     if r["cat_corecta"].strip() != "local" and r["idx"] not in CUNOSCUTE_NIVEL]
    assert len(discrimineaza) >= MINIM_DISCRIMINANTE, (
        f"doar {len(discrimineaza)} cazuri `judetean`/`regional` evaluabile ({discrimineaza}) — "
        f"sub pragul de {MINIM_DISCRIMINANTE}. Poarta de nivel se apropie de starea in care ar "
        f"trece si pe un cod care raspunde „local” la orice; completeaza setul cu cazuri ne-locale "
        f"de la surse neoficiale.")


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


@pytest.mark.parametrize("rand", _cazuri_nivel(), ids=lambda r: f"nivel{r['idx']}")
def test_nivelul_geografic_nu_regreseaza(rand):
    """`geo.clasifica` alege acelasi nivel pe care l-a judecat omul.

    Intrarea e title+teaser, ca in productie (`process._text_clasificabil` le lipeste, plus
    `synthesis` la clustere), si e citita din TSV, nu din `data/articles.json` — altfel poarta
    s-ar goli in 7 zile prin TTL.

    Judetul sursei se transmite fiindca ELE deschid potrivirea pe sate (`geo._SATE`), si numai
    ale lui. Fara el s-ar testa calea surselor nationale pe articole de ziar local.

    Asertiunea pe `None` nu e redundanta cu cea de egalitate: `None` inseamna „textul nu numeste
    niciun loc", iar aici fiecare rand ARE un loc judecat manual. Daca gazetteer-ul s-ar goli sau
    regexul ar cadea, toate randurile ar da `None` — si un mesaj care spune „None != local" ar
    trimite urmatorul cititor sa caute in logica de nivel, nu in index.

    **PUTEREA REALA A ACESTEI PORTI, MASURATA PRIN MUTATIE 2026-08-09 — citeste inainte sa te
    bazezi pe ea:**
      `clasifica` -> `None`     : 15 din 15 pica. Prinde complet o clasificare moarta.
      `clasifica` -> mereu `local`: **1 din 15 pica.** Aproape oarba.
    Cauza nu e testul, e esantionul: 14 din cele 15 cazuri evaluabile au `cat_corecta == local`,
    deci un cod care raspunde „local" la orice trece. Singurul caz `judetean` care ramane sa
    discrimineze e #34 — restul de cinci sunt in `CUNOSCUTE_NIVEL`. Un fix care ar cobori totul
    la `local` (exact directia in care cele cinci greselile de azi merg deja) ar trece pe langa
    poarta asta. **Ca sa aiba putere reala, setul de aur are nevoie de cazuri `judetean`/`regional`
    de la surse neoficiale** — E5 din `specs/atribuire-cercetare-si-plan.md`, cresterea la ~150.
    Pana atunci poarta e o plasa cu ochiuri mari intr-o singura directie, nu o dovada.
    """
    if rand["idx"] in CUNOSCUTE_NIVEL:
        pytest.xfail(CUNOSCUTE_NIVEL[rand["idx"]])
    text = f"{rand['titlu']} {rand['teaser']}".strip()
    nivel = geo.clasifica(text, geo.judet_sursa(rand["sursa"]))

    assert nivel is not None, (
        f"niciun loc gasit in {rand['titlu'][:60]!r} — gazetteer gol sau index cazut?")
    assert nivel == rand["cat_corecta"], (
        f"clasifica={nivel!r} dar omul a judecat {rand['cat_corecta']!r} — {rand['titlu'][:60]!r}")
