"""Teste pentru reproiectarea copertei clasice (2026-09-06): data ca element de design."""
from generator import htmlart


def _art(**over):
    a = {"category": "sport", "source": "digi24", "title": "FCSB a câștigat derby-ul",
         "published": "2026-09-04T18:30:00+00:00"}
    a.update(over)
    return a


def test_data_copertei_parseaza_si_esueaza_curat():
    dt = htmlart._data_copertei(_art())
    assert dt == {"zi": "04", "zi_n": "4", "wk": "vineri", "luna": "septembrie", "an": "2026"}
    assert htmlart._data_copertei(_art(published="")) is None
    assert htmlart._data_copertei(_art(published=None)) is None
    assert htmlart._data_copertei(_art(published="garbage")) is None


def test_toate_patru_template_au_data_si_eticheta():
    for i in range(4):
        seed_probe = _art(title=f"titlu de proba {i}")
        html = htmlart.build_html(seed_probe)
        assert "septembrie" in html, f"template-ul {i} nu are luna"
        assert 'class="eticheta"' in html
        assert "izz.ro" in html


def test_fara_data_publicatie_nu_afiseaza_none():
    html = htmlart.build_html(_art(published=None))
    assert "None" not in html
    assert "NaN" not in html


def test_determinism_acelasi_articol_acelasi_html():
    a = _art(title="Aceeasi veste din doua surse")
    assert htmlart.build_html(a) == htmlart.build_html(a)
    assert htmlart.build_html(a, cover=True) == htmlart.build_html(a, cover=True)


def test_coperta_og_scaleaza_tipografia():
    a = _art()
    banner, og = htmlart.build_html(a), htmlart.build_html(a, cover=True)
    # fontul etichetei din og e cu ~25% mai mare decat in banner (1200/960)
    import re
    px = [int(m) for m in re.findall(r'font-size:(\d+)px', banner + og)]
    assert px, "niciun font-size inline gasit"
    assert max(px) > 90  # tipografia mare exista in set


def test_marimea_etichetei_treptata_pe_lungime():
    k = 1.0
    scurt = htmlart._et_px("SIBIU", ((8, 128), (13, 102), (18, 82), (99, 60)), k)
    lung = htmlart._et_px("MUNICIPIUL BUZĂU", ((8, 128), (13, 102), (18, 82), (99, 60)), k)
    si_mai_lung = htmlart._et_px("BISTRIȚA-NĂSĂUD SEVERIN", ((8, 128), (13, 102), (18, 82), (99, 60)), k)
    assert scurt == 128 and lung == 82 and si_mai_lung == 60
