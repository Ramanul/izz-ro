"""Gărzi pentru punctele rezolvate din auditul de SEO de pe 7 nov 2026.

Fiecare test apără o proprietate, nu un simptom — raportul număra instance:

1. **Linkul către sursă poartă `nofollow`** (pct. 1, „scurgerea de autoritate”): 57 de linkuri
   externe DoFollow pe prima pagină, zero backlinkuri primite. Creditul de imagine (Wikimedia,
   licență) rămâne DoFollow — e obligație de licență, nu recomandare algoritmică.
2. **Slug fără cuvinte de legătură și fără prepoziție atârnată la coadă** (pct. 2).
3. **Title 50–60 / descriere 120–160 pe prima pagină** (pct. 3).
4. **Ierarhie: secțiunea e `<h2>`, articolul e `<h3>`; niciun `<img>` fără `alt`, nicio
   săritură de nivel** (pct. 4 — și pct. 6, care se dovedește alarmă falsă: `alt=""` e alt
   valid pentru imagine decorativă, iar pozele de pe card sunt decorative prin construcție).
5. **Ancora de categorie poartă cuvântul cheie** (pct. 5).
6. **`llms.txt`** (pct. 7) — fișierul, forma lui și faptul că nu trimite spre pagini moarte.

Ce NU acoperă: pct. 8 (backlinkuri, conturi de social) nu e o modificare de cod, e decizie de
proprietar. Alarmele pe care raportul le recomandă ignorate rămân ignorate: niciun Pixel (siteul
rulează deliberat fără măsurare în browserul cititorului — `_write_headers`, D6 din
`specs/plan-paradigma-izz.md`) și fără LocalBusiness schema (nu e o afacere locală).
"""
import importlib
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
a11y = importlib.import_module("tools.a11y_static")

from generator import config, render  # noqa: E402

TITLU_MIN, TITLU_MAX = 50, 60
DESC_MIN, DESC_MAX = 120, 160
# Gazde care nu sunt „sursa agregată”: creditul de imagine și licența lui — rămân DoFollow.
ATTRIBUIT = ("commons.wikimedia.org", "creativecommons.org", "wikimedia.org")
# Blocurile în care stau linkurile către publicațiile citate.
SURSE_BLOC = (r'<span class="sources-inline">(.*?)</span>',
              r"<h3>Surs[^<]*</h3>\s*<ul>(.*?)</ul>",
              r'<div class="sources-box">.*?<ul>(.*?)</ul>')
LEGATURA = re.compile(r'<a\s+[^>]*href="(https?://[^"]+)"[^>]*>', re.I)


def _citit(out, *parti) -> str:
    return Path(out, *parti).read_text(encoding="utf-8")


def _linkuri_ext(bucata: str):
    """Fiecare `<a>` cu URL absolut dintr-o bucată de HTML, cu `rel`-ul lui."""
    for m in LEGATURA.finditer(bucata):
        rel = re.search(r'rel="([^"]*)"', m.group(0))
        yield m.group(1), (rel.group(1) if rel else "")


def _un_articol(output_randat) -> str:
    """Prima pagină de articol linkată de pe homepage — cale reală, nu ghicită."""
    html = _citit(output_randat, "index.html")
    for href in re.findall(r'href="(/[^/"]+/[^/"]+/)"', html):
        cale = Path(output_randat, href.strip("/"), "index.html")
        if cale.is_file():
            return cale.read_text(encoding="utf-8")
    return ""


# --- 1. nofollow pe surse, DoFollow pe atribuire ----------------------------------------

def test_fiecare_link_catre_sursa_poarta_nofollow(output_randat):
    pagini = [_citit(output_randat, "index.html"),
              _citit(output_randat, "surse", "index.html"),
              _un_articol(output_randat)]
    vazute = 0
    for html in pagini:
        for bloc in SURSE_BLOC:
            for bucata in re.findall(bloc, html, re.S):
                for url, rel in _linkuri_ext(bucata):
                    vazute += 1
                    assert "nofollow" in rel, (url, rel)
    assert vazute > 0, "testul nu a găsit niciun link de sursă de verificat"


def test_creditul_de_imagine_ramane_dofollow(output_randat):
    """`nofollow` nu se extinde pe atribuire: linkul de licență e obligație, nu recomandare."""
    gasit = False
    for html in (_citit(output_randat, "index.html"), _un_articol(output_randat)):
        for url, rel in _linkuri_ext(html):
            if any(g in url for g in ATTRIBUIT):
                gasit = True
                assert "nofollow" not in rel, url
    if not gasit:
        pytest.skip("esantionul randat nu conține nicio fotografie cu credit Wikimedia")


def test_niciun_link_extern_fara_noopener(output_randat):
    lipsa = [u for u, rel in _linkuri_ext(_citit(output_randat, "index.html"))
             if "noopener" not in rel]
    assert not lipsa, lipsa[:3]


def test_nofollow_nu_inlocuieste_noopener_in_sabloane():
    """Regula permanentă din CLAUDE.md §7: `target="_blank"` + `noopener noreferrer`.

    Unde apare `nofollow`, apare în fața aceleiași formule, nu în locul ei — un `rel` care ar
    pierde `noopener` pe o linie cu `nofollow` ar redeschide `window.opener` pe tot siteul.
    """
    gresite = []
    for cale in Path(ROOT, "templates").glob("*.html"):
        for nr, linie in enumerate(cale.read_text(encoding="utf-8").splitlines(), 1):
            if "nofollow" not in linie:
                continue
            for m in re.finditer(r'<a\b[^>]*>', linie):
                if 'target="_blank"' in m.group(0) and \
                        'rel="nofollow noopener noreferrer"' not in m.group(0):
                    gresite.append(f"{cale.name}:{nr}")
    assert not gresite, gresite


# --- 2. slug: fără zgomot, fără prepoziție la coadă -------------------------------------

EXEMPLE_RAPORT = [
    ("Turcia lansează un program energetic masiv în valoare de 500 de miliarde de dolari",
     "turcia-lanseaza-program-energetic-masiv-valoare-500-miliarde-dolari"),
    ("Slăbirea timpurie a vortexului polar crește riscul de valuri de frig în Europa",
     "slabirea-timpurie-vortexului-polar-creste-riscul-valuri-frig-europa"),
]


@pytest.mark.parametrize("titlu,asteptat", EXEMPLE_RAPORT)
def test_slug_exemplelor_din_raport(titlu, asteptat):
    assert render._slug_de_baza(titlu) == asteptat


def test_slug_nu_se_termina_in_cuvant_de_legatura():
    """Coada atârnată — 793 din 7.324 de slug-uri (10,8%) pe starea de pe 7 nov 2026."""
    titluri = [
        "Primăria anunță o investiție în valoare de 500 de milioane de euro pentru",
        "Slăbirea timpurie a vortexului polar crește riscul de valuri de frig în",
        "Atacantul român Daniel Bîrligea este favorit să câștige postul de titular la",
    ]
    for t in titluri:
        s = render._slug_de_baza(t)
        assert s.split("-")[-1] not in render._SLUG_JOARDE, s
        assert len(s) <= 80, s


def test_slug_pastreaza_cuvintele_care_sunt_continut():
    """Lista de stop-words e închisă exact cât trebuie: aceste cuvinte NU se ating."""
    # „i\" / „ii\" sunt cifre romane, nu pronume — fără excepție, „Liga I\" și „Liga II\"
    # ar coliza pe același slug.
    assert render._slug_de_baza("Liga I și Liga II") == "liga-i-si-liga-ii"
    assert "peste" in render._slug_de_baza("Peste 300 de tone de pește")
    assert "mai" in render._slug_de_baza("Inflația se încetinește în mai")


def test_slug_nu_mancina_abrevierile_de_forma_juridica():
    """Garda de clasă pentru „Aquaserv S.A.\": vecinul de o singură literă protejează tokenul.

    Fără ea, `a` (articol nehotărât, dar și litera din „S.A.\") dispărea din 21 de titluri
    de pe starea de pe 7 nov 2026 și lăsa în URL un „-s\" de unul singur. Cifrele nu
    protejează nimic: „... nr. 4 din\" rămâne tăiat de coadă.
    """
    assert render._slug_de_baza("Comunicat Compania Aquaserv S.A.") == \
        "comunicat-compania-aquaserv-s-a"
    assert render._slug_de_baza("Primăria începe lucrările de modernizare la Școala nr. 4 din") \
        .endswith("-nr-4")
    assert not render._slug_de_baza("Primăria începe lucrările de modernizare la Școala nr. 4 din") \
        .endswith("-din")


def test_slug_din_numai_prepozitii_nu_dispare():
    s = render._slug_de_baza("de la la")
    assert s and not s.startswith("-") and "--" not in s and not s.endswith("-")


def test_slug_existent_nu_se_rescrie(output_randat):
    """Permalinkul e proprietate publicată: curățarea se aplică doar la atribuirea inițială."""
    arts = [{"slug": "stirea-veche-de-la-2024", "title": "Stire nouă de la 2024",
             "category": "general"}]
    render.assign_slugs(arts)
    assert arts[0]["slug"] == "stirea-veche-de-la-2024"


# --- 3. title / meta description pe prima pagină ----------------------------------------

def _meta(output_randat):
    html = _citit(output_randat, "index.html")
    titlu = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    descr = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
    return titlu, descr


def test_title_primei_pagini_este_in_bugetul_serp(output_randat):
    titlu, _ = _meta(output_randat)
    assert TITLU_MIN <= len(titlu) <= TITLU_MAX, (len(titlu), titlu)
    assert "știri" in titlu.lower() and "românia" in titlu.lower(), titlu


def test_descrierea_primei_pagini_este_in_bugetul_serp(output_randat):
    _, descr = _meta(output_randat)
    assert DESC_MIN <= len(descr) <= DESC_MAX, (len(descr), descr)
    assert "surse" in descr.lower(), descr


def test_og_title_si_og_description_urmeaza_meta(output_randat):
    """Un singur izvor pentru cele două: blocurile din `base.html`, nu texte separate."""
    html = _citit(output_randat, "index.html")
    titlu, descr = _meta(output_randat)
    assert f'<meta property="og:title" content="{titlu}"' in html
    assert f'<meta property="og:description" content="{descr}"' in html


# --- 4. ierarhia titlurilor și ancorele --------------------------------------------------

def test_cardurile_de_pe_prima_pagina_sunt_h3(output_randat):
    html = _citit(output_randat, "index.html")
    assert '<h2 class="card-title">' not in html
    assert '<h3 class="card-title">' in html


def test_sectionile_raman_h2(output_randat):
    html = _citit(output_randat, "index.html")
    assert html.count('<h2 class="section-title">') >= 2


def test_structura_semantica_fara_saritura_de_nivel(output_randat):
    """Prin unealta proprie de a11y, pe ambele suprafețe atinse de schimbare."""
    tacute = 0
    for cale in (Path(output_randat, "index.html"),
                 Path(output_randat, "general", "index.html")):
        if not cale.is_file():
            continue
        tacute += 1
        verdict = a11y.verifica(str(cale))
        assert not verdict["tari"], (cale.name, verdict["tari"])
        sarituri = [s for s in verdict["slabe"] if "saritura de nivel" in s]
        assert not sarituri, (cale, sarituri)
    assert tacute, "nimic randat de verificat"


def test_nivel_intermediar_pe_pagina_de_categorie(output_randat):
    """Fără h2-ul intermediar, cardurile de pe /cat/ ar sări de la h1 la h3."""
    html = _citit(output_randat, "general", "index.html")
    assert html.index("<h1") < html.index('<h2 class="visually-hidden">') \
        < html.index('<h3 class="card-title">')


def test_ancora_de_categorie_pune_cuvantul_cheie_inainte(output_randat):
    html = _citit(output_randat, "index.html")
    ancore = re.findall(r'<a class="see-all"[^>]*>([^<]+?)\s*&rarr;</a>', html)
    assert ancore, "nu s-a găsit nicio legătură de categorie"
    assert all(a.lower().startswith("toate știrile") for a in ancore), ancore
    assert not any("vezi toate" in a.lower() for a in ancore), ancore


# --- 7. llms.txt ------------------------------------------------------------------------

def _llms(output_randat) -> str:
    cale = Path(output_randat, "llms.txt")
    assert cale.is_file(), "llms.txt nu se scrie la build"
    return cale.read_text(encoding="utf-8")


def test_llms_txt_are_forma_specificata(output_randat):
    text = _llms(output_randat)
    linii = text.splitlines()
    assert linii[0] == f"# {config.SITE['name']}"
    assert linii[2].startswith("> "), "al doilea element al formatului e blockquote-ul de sumar"
    assert text.endswith("\n")
    assert {"## Secțiuni", "## Utilitare", "## Feeds și descoperire", "## Transparență"} == \
        {l.strip() for l in linii if l.startswith("## ")}, text
    assert len(text.encode("utf-8")) < 8192, "llms.txt e un index, nu o a doua arhivă"


def test_llms_txt_nu_promite_ce_nu_exista(output_randat):
    """Orice adresă de pe izz.ro din fișier există în build — altfel indexăm fantome."""
    out = Path(output_randat)
    Link = re.compile(r"-\s*\[[^\]]+\]\((https?://[^)]+)\)")
    vazute = 0
    for m in Link.finditer(_llms(output_randat)):
        url = m.group(1)
        assert url.startswith(config.SITE["url"]), url
        parte = url[len(config.SITE["url"]):].strip("/")
        if parte.endswith("/") or "." not in parte:
            tinta = out / parte / "index.html" if parte else out / "index.html"
        else:
            tinta = out / parte
        assert tinta.exists(), url
        vazute += 1
    assert vazute >= len(config.CATEGORIES) + 7, vazute


def test_llms_txt_acopera_toate_categoriile(output_randat):
    text = _llms(output_randat)
    lipsa = [c for c in config.CATEGORIES if f"]({config.SITE['url']}/{c}/)" not in text]
    assert not lipsa, lipsa
