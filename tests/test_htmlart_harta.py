"""Coperta cu silueta judetului: alegere, incadrare si caderea pe template-urile vechi.

De ce exista felia: pe 2026-09-04 coperta unui articol `economic` scria „ECONOMIC", adica NUMELE
RUBRICII — o informatie pe care cititorul o are deja in badge, in URL si in meniu. Toate cele
1.184 de articole economice aratau la fel. La `local`/`judetean` eticheta era macar localitatea,
dar restul cadrului ramanea gol. Silueta judetului umple cadrul cu ceva ADEVARAT despre articol.

Geometria e `data/harta_judete.json` — Natural Earth, domeniu public, deja in repo pentru harta
stirilor. Deci nicio cerere de retea la randare si nicio licenta de tert: testele de aici pot
rula offline, si asta e si motivul pentru care s-a ales varianta asta in locul tile-urilor OSM.
"""
import json

import pytest

from generator import htmlart


LOCAL_CU_JUDET = {"category": "local", "source": "pl_cluj_orasul_floresti",
                  "title": "Lucrari la reteaua de apa", "url": "u1"}


def test_judetele_din_fisier_acopera_tara():
    """42 de judete, exact cheile pe care le intoarce `geo.judet_sursa`. Daca fisierul se
    schimba si pierde judete, coperta cade tacut pe template-ul vechi — de-aia se verifica aici."""
    assert len(htmlart._harta()) == 42


def test_articol_local_primeste_silueta():
    html = htmlart.build_html(LOCAL_CU_JUDET)
    assert "<svg" in html and "<path" in html


def test_silueta_e_a_judetului_cerut():
    """Path-ul injectat e chiar geometria CLUJ, nu a altui judet."""
    html = htmlart.build_html(LOCAL_CU_JUDET)
    assert htmlart._harta()["CLUJ"] in html


@pytest.mark.parametrize("articol", [
    {"category": "economic", "source": "ziarul", "title": "Firme dizolvate"},
    {"category": "extern", "source": "pl_cluj_orasul_floresti", "title": "Summit la Bruxelles"},
    {"category": "sport", "source": "cj_cluj", "title": "Meci amanat"},
])
def test_categoriile_fara_axa_geografica_nu_primesc_harta(articol):
    """Silueta apare doar unde LOCUL e subiectul. O stire externa publicata de o sursa clujeana
    n-are nicio treaba cu conturul Clujului."""
    assert htmlart._judet(articol) is None
    assert "<svg" not in htmlart.build_html(articol)


def test_regional_e_exclus_desi_sursa_are_judet():
    """`regional` acopera mai multe judete: orice silueta unica ar fi o afirmatie falsa (§7)."""
    a = {"category": "regional", "source": "cj_cluj", "title": "Seceta in Transilvania"}
    assert htmlart._judet(a) is None


def test_sursa_nationala_nu_ghiceste_judetul():
    """Fara judet in cheia sursei nu se deduce nimic din titlu: o silueta gresita e mai rea
    decat niciuna. Articolul isi pastreaza template-ul din rotatia veche."""
    a = {"category": "local", "source": "protv", "title": "Accident la Cluj-Napoca"}
    assert htmlart._judet(a) is None
    assert "<svg" not in htmlart.build_html(a)


def test_subtitlul_arata_judetul_nu_categoria():
    """„Florești / CLUJ" spune ceva; „Florești / LOCAL" repeta rubrica."""
    assert htmlart._sub_harta(LOCAL_CU_JUDET, "CLUJ").strip().lower() == "cluj"


def test_subtitlul_nu_repeta_eticheta():
    """Cand eticheta E deja judetul, subtitlul cade pe categorie in loc de „CLUJ / CLUJ"."""
    a = {"category": "judetean", "source": "cj_cluj", "title": "Consiliul Judetean a aprobat"}
    eticheta = htmlart._eticheta(a)
    assert htmlart._sub_harta(a, "CLUJ").strip().lower() != eticheta.strip().lower()


@pytest.mark.parametrize("cod", ["CLUJ", "CONSTANTA", "ILFOV", "TULCEA", "BUCURESTI"])
def test_silueta_incape_intreaga_in_cutie(cod):
    """Judetul trebuie sa intre COMPLET in cutia data, oricat de diferite i-ar fi proportiile.

    Prima varianta il ancora la -110px si il scala la 560px: iesea din cadru pe trei parti si
    se citea ca o pata gri, nu ca un judet (masurat vizual, randare Chromium, 2026-09-04).
    Aici verificam ce lipsea atunci: bbox-ul transformat sta in interiorul cutiei.
    """
    if cod not in htmlart._harta():
        pytest.skip(f"{cod} lipseste din fisierul de geometrie")
    lat, inalt = 360.0, 364.0
    svg = htmlart._silueta(cod, lat, inalt, "#000", 0.15)
    tx, ty, s = _transformarea(svg)
    x0, y0, x1, y1 = htmlart._bbox(htmlart._harta()[cod])
    eps = 0.5
    assert -eps <= x0 * s + tx and x1 * s + tx <= lat + eps
    assert -eps <= y0 * s + ty and y1 * s + ty <= inalt + eps


def test_silueta_umple_cutia_pe_axa_lunga():
    """Scalarea nu doar incape — foloseste spatiul: latura mare atinge marginea cutiei.
    Fara asta, un judet compact ca Ilfov ar aparea ca un punct in mijloc."""
    svg = htmlart._silueta("ILFOV", 360.0, 364.0, "#000", 0.15)
    _, _, s = _transformarea(svg)
    x0, y0, x1, y1 = htmlart._bbox(htmlart._harta()["ILFOV"])
    assert max((x1 - x0) * s / 360.0, (y1 - y0) * s / 364.0) == pytest.approx(1.0, abs=0.01)


def test_conturul_ramane_egal_de_gros_pe_toate_judetele():
    """`stroke-width` se imparte la scara, altfel un judet mic (scalat mult) ar avea contur gros
    si unul mare un fir subtire — pe aceeasi pagina, carduri alaturate."""
    grosimi = []
    for cod in ("ILFOV", "TIMIS", "CLUJ"):
        svg = htmlart._silueta(cod, 360.0, 364.0, "#000", 0.15)
        _, _, s = _transformarea(svg)
        grosimi.append(float(svg.split('stroke-width="')[1].split('"')[0]) * s)
    assert max(grosimi) - min(grosimi) < 0.05


def test_geometrie_lipsa_nu_arunca():
    """Un cod necunoscut da "" si articolul isi pastreaza coperta — niciodata exceptie in pipeline."""
    assert htmlart._silueta("JUDET-INEXISTENT", 100, 100, "#000", 0.1) == ""
    assert htmlart._silueta(None, 100, 100, "#000", 0.1) == ""


def test_fisierul_de_geometrie_ramane_domeniu_public():
    """Temeiul legal al feliei sta in antetul fisierului, nu in memoria cuiva. Daca sursa se
    schimba pe una cu licenta restrictiva, testul cade si obliga la o decizie constienta (§18)."""
    with open(htmlart._HARTA_PATH, encoding="utf-8") as f:
        sursa = json.load(f).get("sursa", "")
    assert "domeniu public" in sursa.lower()


def test_randarea_e_determinista():
    """Aceeasi intrare -> acelasi HTML. Altfel fiecare rulare ar rescrie mii de imagini."""
    assert htmlart.build_html(LOCAL_CU_JUDET) == htmlart.build_html(LOCAL_CU_JUDET)


def test_coperta_og_pastreaza_silueta():
    """Varianta 1200x630 (og:image) trece prin acelasi sablon — pe share se vede coperta, nu
    un al doilea design."""
    assert "<svg" in htmlart.build_html(LOCAL_CU_JUDET, cover=True)


def _transformarea(svg: str):
    """(tx, ty, scala) din atributul `transform` al grupului."""
    bucata = svg.split('transform="translate(')[1].split(')"')[0]
    mutare, scara = bucata.split(") scale(")
    tx, ty = (float(v) for v in mutare.split())
    return tx, ty, float(scara)
