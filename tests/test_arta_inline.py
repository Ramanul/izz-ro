"""Arta desenata in pagina (2026-09-09, intoarcerea pe Workers Free).

De ce exista: pe planul gratuit o versiune de Worker are cel mult 20.000 de fisiere, iar
arta per articol consuma singura 65% din ele. Compozitiile fiind tipografie si geometrie,
se deseneaza acum din CSS. Testele de aici pazesc trei lucruri care se pot rupe tacut:

  1. arta inline si rasterul din `media/` trebuie sa aleaga ACEEASI compozitie si aceeasi
     paleta pentru acelasi articol -- altfel og:image-ul si pagina arata diferit;
  2. sabloanele nu au voie sa mai ceara `art.jpg`/`art.webp` pentru arta generata;
  3. fiecare clasa emisa de sablon trebuie sa existe in `static/styles.css` -- un `art--p7`
     fara regula CSS nu da eroare nicaieri, doar o caseta goala pe card.

Fiecare garda are si un caz negativ (IZZ-0177).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import htmlart, render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _art(**over):
    a = {"category": "sport", "source": "digi24", "slug": "fcsb-derby",
         "title": "FCSB a câștigat derby-ul", "url": "https://izz.ro/x",
         "published": "2026-09-04T18:30:00+00:00"}
    a.update(over)
    return a


def _css():
    with open(os.path.join(ROOT, "static", "styles.css"), encoding="utf-8") as fh:
        return fh.read()


def _macro():
    return render._env().get_template("_art.html").module.art


# --- 1. inline si raster descriu aceeasi imagine -----------------------------------

def test_stilul_inline_alege_aceeasi_compozitie_ca_rasterul():
    """Daca cele doua se despart, og:image-ul arata altfel decat pagina pe care o anunta."""
    for i in range(40):
        a = _art(title=f"titlu de proba {i}", url=f"https://izz.ro/{i}")
        s = htmlart.stil_inline(a)
        raster = htmlart.build_html(a)
        acc, bg = htmlart._PALETE[s["pal"]]
        assert acc in raster and bg in raster, (
            f"paleta {s['pal']} nu e cea folosita de raster pentru '{a['title']}'")
        # compozitia: fiecare sablon are un marcaj propriu in HTML-ul raster
        semne = {"editorial": "Portalul știrilor tale", "inversat": "rotate(45deg)",
                 "banda": "white-space:nowrap", "arc": "border-radius:50%"}
        assert semne[s["tpl"]] in raster, f"compozitia {s['tpl']} nu se regaseste in raster"


def test_determinism_acelasi_articol_acelasi_stil():
    a = _art(title="Aceeași veste din două surse")
    assert htmlart.stil_inline(a) == htmlart.stil_inline(a)


def test_NEGATIV_articole_diferite_primesc_stiluri_diferite():
    """O functie care intoarce mereu acelasi stil ar trece testul de determinism."""
    stiluri = {(htmlart.stil_inline(_art(title=f"stire {i}"))["tpl"],
                htmlart.stil_inline(_art(title=f"stire {i}"))["pal"]) for i in range(60)}
    assert len(stiluri) > 6, f"doar {len(stiluri)} combinatii distincte pe 60 de titluri"


def test_treapta_etichetei_scade_cu_lungimea_numelui():
    """Numele lungi trebuie sa coboare o treapta, altfel ies din cadru."""
    assert htmlart._treapta_eticheta("Cluj") == 0
    assert htmlart._treapta_eticheta("Caraș-Severin") == 1
    assert htmlart._treapta_eticheta("Satu Mare-Baia") == 2
    assert htmlart._treapta_eticheta("Bistrița-Năsăud și împrejurimi") == 3


def test_fara_data_publicatie_nu_afiseaza_none():
    s = htmlart.stil_inline(_art(published=None))
    assert s["data"] is None
    html = str(_macro()({"art_style": s}))
    assert "None" not in html and "NaN" not in html


# --- 2. sabloanele nu mai cer fisiere pentru arta generata --------------------------

def test_cardul_deseneaza_arta_in_loc_sa_ceara_fisier():
    a = _art()
    a["art_style"] = htmlart.stil_inline(a)
    card = render._env().get_template("_card.html").module.card
    html = str(card(a))
    assert 'class="art art--' in html
    assert "art.jpg" not in html and "art.webp" not in html and "art-card" not in html


def test_NEGATIV_cand_exista_fotografie_reala_cardul_foloseste_fisierul():
    """Fotografiile reale RAMAN fisiere -- inline-ul e doar pentru arta generata."""
    a = _art()
    a["art_style"] = htmlart.stil_inline(a)
    a["art_path"] = "/sport/fcsb-derby/art.jpg?v=abc"
    card = render._env().get_template("_card.html").module.card
    html = str(card(a))
    assert "art.jpg" in html
    assert 'class="art art--' not in html, "fotografia si arta generata nu apar amandoua"


def test_arta_e_decor_deci_ascunsa_de_cititorul_de_ecran():
    """Eticheta si data sunt deja in text pe card; anuntate din nou ar fi repetitie."""
    a = _art()
    html = str(_macro()({"art_style": htmlart.stil_inline(a)}))
    assert 'aria-hidden="true"' in html


def test_fara_stil_nu_se_emite_nimic():
    """Un articol fara `art_style` nu trebuie sa produca o caseta goala."""
    assert str(_macro()({})).strip() == ""


# --- 3. fiecare clasa emisa are regula in CSS --------------------------------------

def test_toate_paletele_si_compozitiile_au_reguli_in_css():
    css = _css()
    for i in range(len(htmlart._PALETE)):
        assert f".art--p{i} " in css, f"paleta art--p{i} nu are regula CSS"
    for tpl in htmlart._NUME_TEMPLATE:
        assert f".art--{tpl} " in css, f"compozitia art--{tpl} nu are regula CSS"
    for t in range(len(htmlart._ET_TREPTE) + 1):
        assert f".art--t{t} " in css, f"treapta art--t{t} nu are regula CSS"


def test_clasele_emise_de_sablon_exista_toate_in_css():
    """Garda pe LEGATURA: sablonul poate inventa o clasa fara ca nimic sa se planga."""
    css = _css()
    emise = set()
    for i in range(40):
        a = _art(title=f"titlu de proba {i}", url=f"https://izz.ro/{i}")
        html = str(_macro()({"art_style": htmlart.stil_inline(a)}))
        for atr in re.findall(r'class="([^"]+)"', html):
            emise.update(c for c in atr.split() if c.startswith("art"))
    lipsa = sorted(c for c in emise if f".{c}" not in css)
    assert not lipsa, f"clase emise fara regula in styles.css: {lipsa}"


def test_paleta_artei_nu_se_inverseaza_pe_tema_intunecata():
    """Arta e un artefact tiparit, ca o imagine: nu-si schimba culorile cu tema.

    Verificat prin UNICITATEA definitiei, nu prin pozitia in fisier: un `--art-gold`
    redefinit intr-un bloc de tema ar trece orice test care se uita doar la `:root`.
    """
    css = _css()
    for token in ("--art-a0:", "--art-b0:", "--art-gold:"):
        assert css.count(token) == 1, (
            f"{token} e definit de {css.count(token)} ori — arta si-ar schimba culorile "
            f"cu tema, desi e un artefact tiparit")


def test_arta_scaleaza_din_container_nu_din_marimi_fixe():
    """Aceeasi compozitie trebuie sa arate identic pe card (360px) si pe articol (729px)."""
    css = _css()
    bloc = css[css.index(".art {"):css.index(".art-grain")]
    assert "container-type: inline-size" in bloc
    assert "aspect-ratio: 960 / 504" in bloc
    assert "cqw" in css, "fara unitati de container, arta nu scaleaza cu locul in care sta"
