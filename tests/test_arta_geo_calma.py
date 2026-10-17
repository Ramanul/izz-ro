"""Arta stirilor locale/judetene: compozitia calma (cerere proprietar 2026-10-17).

Ce pazesc testele de aici:
  1. pe local/judetean nu mai apare ziua lunii (nici in pagina, nici pe coperta og);
  2. forma desenata urmeaza ETICHETA afisata — cardul care scrie „IAȘI" deseneaza Iasiul;
  3. conturul localitatii (UAT) se foloseste doar cand e sigur, altfel judetul, altfel nimic;
  4. forma e in aur, nu in culoarea textului (in `currentColor` iesea gri/negru).

Fiecare garda are si un caz negativ (IZZ-0177).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import htmlart, render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _art(**over):
    a = {"category": "local", "source": "digi24", "slug": "x", "url": "https://izz.ro/x",
         "title": "Incendiu puternic la un transformator din incinta CET Iași",
         "published": "2026-10-17T18:30:00+00:00"}
    a.update(over)
    return a


def _macro():
    return render._env().get_template("_art.html").module.art


def _css():
    with open(os.path.join(ROOT, "static", "styles.css"), encoding="utf-8") as fh:
        return fh.read()


# --- 1. fara data -------------------------------------------------------------------

def test_stirea_locala_nu_poarta_ziua_lunii():
    for cat in ("local", "judetean"):
        s = htmlart.stil_inline(_art(category=cat))
        assert s.get("geo") is True and s["tpl"] == "arc" and s["data"] is None
        html = str(_macro()({"art_style": s}))
        assert "art--geo" in html
        text = re.sub(r"<svg.*?</svg>", "", html, flags=re.S)   # coordonatele formei nu sunt text
        for urma in ("art-num-zi", "art-seal", "art-brand", "octombrie", "17"):
            assert urma not in text, f"{cat}: «{urma}» a ramas pe arta"


def test_NEGATIV_celelalte_categorii_isi_pastreaza_compozitiile():
    s = htmlart.stil_inline(_art(category="sport", title="FCSB a câștigat derby-ul"))
    assert not s.get("geo") and s["data"] is not None


def test_coperta_og_a_stirii_locale_nu_poarta_data():
    html = htmlart.build_html(_art(), cover=True)
    assert "octombrie" not in html.lower() and "sâmbătă" not in html.lower()
    assert htmlart.GEO_AUR in html, "forma de pe coperta og nu e in aur"


# --- 2. forma urmeaza eticheta ------------------------------------------------------

def test_forma_urmeaza_judetul_numit_in_titlu_chiar_si_de_la_o_sursa_nationala():
    s = htmlart.stil_inline(_art())          # digi24 nu are judet in config
    assert s["eticheta"] == "Iași"
    assert s.get("harta") and s["harta"]["d"]
    assert s["sub"] == "", "sub numele judetului nu se mai repeta categoria"


def test_localitatea_primariei_primeste_conturul_ei_si_judetul_ca_subtitlu():
    a = _art(source="pl_cluj_floresti", title="Ședința consiliului local")
    s = htmlart.stil_inline(a)
    assert s["eticheta"] == "Florești" and s["sub"] == "Cluj"
    judet = htmlart._harta()["CLUJ"]
    assert s["harta"]["d"] != judet, "a desenat judetul, nu localitatea"
    assert s["harta"]["d"] == htmlart._uat_judet("CLUJ")["FLORESTI"]


def test_NEGATIV_localitate_omonima_fara_judet_sursa_nu_primeste_forma():
    """„Florești" exista in trei judete; fara judetul sursei, oricare forma ar fi o ghicire."""
    assert len(htmlart.geo.judetele_localitatii("Florești")) > 1
    s = htmlart.stil_inline(_art(title="Accident grav la Florești, pe drumul național"))
    if s["eticheta"] == "Florești":
        assert not s.get("harta")


def test_NEGATIV_fara_loc_nu_se_inventeaza_nicio_forma():
    s = htmlart.stil_inline(_art(category="judetean", title="Prețul pâinii crește din nou"))
    assert s["eticheta"] == "Județean"
    assert not s.get("harta")


def test_nume_dublat_in_acelasi_judet_e_tratat_ca_ambiguu(tmp_path, monkeypatch):
    (tmp_path / "TEST.json").write_text(
        '{"uats": [{"name": "VALEA", "path": "M0 0 L1 1 Z"}, {"name": "VALEA", "path": "M2 2 L3 3 Z"},'
        ' {"name": "UNIC", "path": "M4 4 L5 5 Z"}]}', encoding="utf-8")
    monkeypatch.setattr(htmlart, "_UAT_DIR", str(tmp_path))
    monkeypatch.setattr(htmlart, "_UAT_CACHE", {})
    idx = htmlart._uat_judet("TEST")
    assert idx["UNIC"] and not idx["VALEA"]


# --- 3. aurul -----------------------------------------------------------------------

def test_forma_e_in_aur_nu_in_culoarea_textului():
    css = _css()
    regula = re.search(r"\.art--geo \.art-harta path\s*\{([^}]*)\}", css)
    assert regula, "lipseste regula pentru forma pe .art--geo"
    assert "var(--art-geo-aur)" in regula.group(1) and "currentColor" not in regula.group(1)
    m = re.search(r"--art-geo-aur:\s*(#[0-9a-fA-F]{6})", css)
    assert m and m.group(1).lower() == htmlart.GEO_AUR.lower(), "CSS si generatorul nu au acelasi aur"
    assert m.group(1).lower() != "#8b6918"


def test_textul_de_pe_arta_locala_nu_scade_sub_10px_pe_card():
    """Auditul 2026-10-17, sect. 3.1: textul decorativ de 4-6px. Cardul are ~341px latime."""
    m = re.search(r"\.art--geo \.art-subrow \.art-sub\s*\{[^}]*font-size:\s*([\d.]+)cqw", _css())
    assert m and float(m.group(1)) * 3.41 >= 10


# --- 4. numele compuse cu cratima -----------------------------------------------------

def test_localitatile_cu_cratima_isi_primesc_eticheta_si_forma():
    """Indexul le scrie cu spatiu, scanerul de titluri le gaseste cu cratima: Cluj-Napoca
    cadea pe eticheta rubricii (46 de titluri locale, masurat 2026-10-17)."""
    a = _art(source="protv", title="Accident la Cluj-Napoca")
    assert htmlart.geo.eticheta_copertei(a) == "Cluj-Napoca"
    s = htmlart.stil_inline(a)
    assert s["sub"] == "Cluj"
    assert s["harta"]["d"] == htmlart._uat_judet("CLUJ")["CLUJ NAPOCA"]


def test_afisele_nu_mai_folosesc_tonul_maro_mustar():
    """Sesizarea proprietarului 2026-10-17: `#8b6918` se citea maroniu pe TOATE afisele, nu
    doar pe cele locale. Aurul ramane `GOLD` in decor; textul ia accentul paletei."""
    css = _css()
    bloc = css[css.index("--art-a0:"):css.index(".art--p0")]
    assert "#8b6918" not in bloc.split("/*")[0].lower()
    assert all(acc.lower() != "#8b6918" for acc, _bg in htmlart._PALETE)
    for f in ("generator/htmlart.py", "generator/covers.py"):
        cod = open(os.path.join(os.path.dirname(__file__), "..", f), encoding="utf-8").read()
        linii = [ln for ln in cod.splitlines() if not ln.lstrip().startswith("#")]
        assert not any(re.search(r"8b6918|\(154, 114, 9\)", ln.split("#  ")[0].split("  # ")[0])
                       for ln in linii), f
    m = re.search(r"--art-a0:\s*(#[0-9a-fA-F]{6})", css)
    assert m and m.group(1).lower() == htmlart._PALETE[0][0].lower(), "CSS si _PALETE difera"
