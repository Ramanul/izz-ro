"""Coperta cu portret: chipul trebuie sa fie al celui despre care e stirea — si sa se vada.

Regresii reale de pe /extern/ din 2026-10-16 (sesizarea proprietarului): Trump pe stirea cu
rachetele Patriot (pomenit doar in rezumat), Jair Bolsonaro pe o stire despre fiul lui,
Flavio, comuna Mihail Kogalniceanu cu portretul omului politic. Plus incadrarea: poza de grup
si fata de cativa pixeli nu au ce cauta intr-un medalion.
"""
import importlib.util
import os

import pytest

from generator import htmlart, render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _a(title, teaser="", **over):
    a = {"category": "extern", "title": title, "teaser": teaser, "slug": "x",
         "published": "2026-10-16T06:00:00+00:00"}
    a.update(over)
    return a


def _p(a, nume, in_titlu=True):
    return htmlart.persoana_potrivita(a, nume, in_titlu=in_titlu)


# ---- context -------------------------------------------------------------------

def test_pomenit_doar_in_rezumat_nu_ajunge_pe_coperta():
    a = _a("Ucraina ar fi epuizat stocul de rachete interceptoare Patriot pe fondul tensiunilor cu SUA",
           "Apărarea antiaeriană ucraineană se confruntă cu o criză, în timp ce relațiile cu "
           "administrația Trump sunt tensionate.")
    assert not _p(a, "Donald Trump")
    assert _p(a, "Donald Trump", in_titlu=False), "in corp e pomenit: caseta de pe articol il poate arata"


def test_numele_de_familie_in_titlu_ajunge():
    assert _p(_a("Ucraina își reorientează atacurile economice asupra Rusiei după acordul cu Trump"),
              "Donald Trump")
    assert _p(_a("Președintele Zelenski cere sprijin financiar la Bruxelles"), "Volodimir Zelenski"), (
        "functia la inceput de propozitie nu e prenumele altcuiva")


def test_omonim_cu_alt_prenume_nu_primeste_portret():
    a = _a("Sondajele indică o competiție strânsă între Lula și Bolsonaro în Brazilia",
           "Institutul Datafolha îl plasează pe reprezentantul dreptei, Flavio Bolsonaro, ușor în față.")
    assert not _p(a, "Jair Bolsonaro")
    assert not _p(_a("Flavio Bolsonaro și Lula se înfruntă în turul doi"), "Jair Bolsonaro")


def test_nume_de_familie_folosit_ca_prenume_sau_cu_sufix_e_alt_om():
    assert not _p(_a("Dan Barna critică guvernul"), "Nicușor Dan")
    assert _p(_a("Nicușor Dan a promulgat legea"), "Nicușor Dan")
    assert not _p(_a("Donald Trump Jr. lansează o carte"), "Donald Trump")


def test_prenumele_singur_nu_identifica():
    assert not _p(_a("Donald, un urs brun, a fost relocat"), "Donald Trump")


def test_omonim_geografic_pe_stire_locala():
    a = _a("Mihail Kogălniceanu pregătește extinderea iluminatului public", category="local")
    assert not _p(a, "Mihail Kogălniceanu")
    assert _p(_a("Mihail Kogălniceanu, omul care a scris Constituția", category="cultura"),
              "Mihail Kogălniceanu")


def test_numele_unui_loc_nu_e_omul():
    assert not _p(_a("Probleme urbane grave sesizate pe strada Maica Domnului din Capitală",
                     category="general"), "Maica Domnului")
    assert not _p(_a("Elevii de la Liceul Mihai Viteazul au câștigat olimpiada", category="general"),
                  "Mihai Viteazul")
    assert _p(_a("Mihai Viteazul, în noua expoziție a Muzeului Național", category="cultura"),
              "Mihai Viteazul")


def test_entitate_neumana_se_cere_intreaga():
    assert not _p(_a("Ploi abundente în Transilvania în weekend", category="general"),
                  "Banca Transilvania")
    assert _p(_a("Banca Transilvania exclude un dividend special", category="economic"),
              "Banca Transilvania")


def test_portret_liber_alege_persoana_din_titlu_nu_prima_entitate(monkeypatch):
    monkeypatch.setattr(htmlart, "_PORTRETE_LIBERE", {
        "donald trump": {"img": "portraits/donald-trump.jpg", "name": "Donald Trump", "taiere": None},
        "marco rubio": {"img": "portraits/marco-rubio.jpg", "name": "Marco Rubio", "taiere": None},
    })
    a = _a("Marco Rubio cere Europei să își consolideze apărarea",
           "Secretarul de stat al administrației Trump a vorbit la Atena.",
           entities=["Donald Trump", "Marco Rubio"])
    assert htmlart._portret_liber(a)["name"] == "Marco Rubio"


# ---- incadrare -----------------------------------------------------------------

def _tool():
    spec = importlib.util.spec_from_file_location(
        "incadrare_portrete", os.path.join(ROOT, "tools", "incadrare_portrete.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_regula_de_incadrare():
    t = _tool()
    assert t.decide(330, 454, [(170, 60, 47, 55), (40, 60, 40, 48)])["respins"] == "grup"
    assert t.decide(330, 522, [(140, 50, 38, 44)])["respins"] == "fata-mica"
    assert t.decide(330, 282, []) == {"fete": 0}, "fara fata (harta, cladire): incadrarea implicita"
    r = t.decide(330, 601, [(190, 75, 51, 60)])          # jucator in picioare, fata sus-dreapta
    tai = r["taiere"]
    s = 2.6 * 51
    assert tai["pw"] == pytest.approx(330 / s * 100, abs=0.05), "zoom pe fata, nu tot cadrul"
    # fata ajunge in medalion: centrul ei cade in interiorul cutiei de decupaj
    cx = (190 + 25.5) / s * 100 + tai["px"]
    cy = (75 + 30 + 6) / s * 100 + tai["py"]
    assert 30 < cx < 70 and 30 < cy < 70


def test_decupajul_nu_iese_din_imagine():
    t = _tool()
    tai = t.decide(330, 565, [(230, 140, 115, 130)])["taiere"]   # fata la marginea dreapta
    assert tai["px"] <= 0 and tai["py"] <= 0
    assert tai["px"] >= -(tai["pw"] - 100) - 0.01, "imaginea ar lasa gol in dreapta medalionului"


def test_medalionul_foloseste_decupajul(monkeypatch):
    s = {"tpl": "arc", "pal": 0, "eticheta": "Externe", "sub": "", "treapta": 0, "data": None,
         "portret": {"img": "portraits/x.jpg", "name": "X",
                     "taiere": {"pw": 249.25, "px": -110.85, "py": -33.49}}}
    html = str(render._env().get_template("_art.html").module.art({"art_style": s}))
    assert "art-portret--fata" in html and "--pw:249.25%" in html and "--py:-33.49%" in html
    css = open(os.path.join(ROOT, "static", "styles.css"), encoding="utf-8").read()
    assert ".art-portret-wrap .art-portret--fata" in css, (
        "fara doua clase, `.card-media img` intinde decupajul inapoi pe tot medalionul")


def test_portretul_respins_nu_apare_nici_pe_articol(monkeypatch, tmp_path):
    monkeypatch.setattr(htmlart, "_INCADRARE", {"portraits/grup.jpg": {"respins": "grup"}})
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    assert render._portret({"x y": {"img": "portraits/grup.jpg", "name": "X Y"}}, "X Y") is None


def test_incadrarea_comisa_acopera_portretele_de_pe_disc():
    """Garda de livrare: un portret nou fara incadrare cade pe decupajul orb din CSS."""
    t = _tool()
    if not os.path.exists(t.OUT):
        pytest.skip("data/portrete_incadrare.json lipseste")
    lipsa = t.de_incadrat()
    assert len(lipsa) <= 25, f"{len(lipsa)} portrete fara incadrare: pasul din build.yml nu ruleaza"
