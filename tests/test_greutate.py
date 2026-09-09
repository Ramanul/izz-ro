"""Garda pentru unealta dimensiunii 5: separarea eager/lazy si rezolvarea cailor.

DE CE testele astea si nu altele: cele doua feluri in care o unealta de masura minte sunt
(1) sa numere ce nu se descarca si (2) sa nu gaseasca fisierul si sa raporteze 0 in tacere.
`IZZ-0275` a costat o sesiune intreaga exact asa — o unealta de masura necalibrata pe un caz
cu raspuns cunoscut. Aici cazul cu raspuns cunoscut e construit deliberat.
"""
import pytest

from tools import greutate


@pytest.fixture
def output_fals(tmp_path, monkeypatch):
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "s.css").write_bytes(b"x" * 1000)
    (tmp_path / "poza.jpg").write_bytes(b"y" * 5000)
    (tmp_path / "lazy.jpg").write_bytes(b"z" * 9000)
    monkeypatch.setattr(greutate, "OUTPUT", tmp_path)
    return tmp_path


def test_lazy_nu_intra_in_prima_incarcare(output_fals):
    """Cifra din IZZ-0237 parea mai mica tocmai fiindca lazy si eager erau amestecate."""
    p = output_fals / "index.html"
    p.write_text('<link rel="stylesheet" href="/static/s.css">'
                 '<img src="/poza.jpg"><img src="/lazy.jpg" loading="lazy">', encoding="utf-8")
    r = greutate.cantareste(p)
    assert r["eager"] == 6000 and r["nr_eager"] == 2, r
    assert r["lazy"] == 9000 and r["nr_lazy"] == 1, r


def test_ce_nu_se_descarca_nu_se_numara(output_fals):
    """`rel=alternate`/`canonical`, `data:` si linkurile externe nu sunt cereri de pagina."""
    p = output_fals / "a.html"
    p.write_text('<link rel="canonical" href="/static/s.css">'
                 '<link rel="alternate" href="/static/s.css">'
                 '<img src="data:image/gif;base64,R0lGOD">'
                 '<img src="https://alt.example/x.jpg">', encoding="utf-8")
    r = greutate.cantareste(p)
    assert r["eager"] == 0 and r["nr_eager"] == 0, r


def test_caile_relative_si_absolute_se_rezolva_amandoua(output_fals):
    """O cale nerezolvata raporteaza 0 tacut — modul principal in care unealta ar minti."""
    (output_fals / "sub").mkdir()
    p = output_fals / "sub" / "b.html"
    (output_fals / "sub" / "vecin.jpg").write_bytes(b"q" * 700)
    p.write_text('<img src="vecin.jpg"><img src="/poza.jpg">', encoding="utf-8")
    r = greutate.cantareste(p)
    assert r["eager"] == 5700, r


def test_srcset_ia_prima_varianta(output_fals):
    p = output_fals / "c.html"
    p.write_text('<source srcset="/poza.jpg 400w, /lazy.jpg 800w">', encoding="utf-8")
    assert greutate.cantareste(p)["eager"] == 5000


def test_fisier_lipsa_nu_arunca(output_fals):
    """Un asset lipsa e o constatare, nu o exceptie — altfel o pagina stricata opreste tot."""
    p = output_fals / "d.html"
    p.write_text('<img src="/nu-exista.jpg">', encoding="utf-8")
    r = greutate.cantareste(p)
    assert r["eager"] == 0 and r["nr_eager"] == 1, "referinta se numara, octetii nu"
