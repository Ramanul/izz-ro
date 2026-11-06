"""Oglinda GitHub Pages nu primeste fisiere de imagine de articol.

DE CE EXISTA. Paginile raman pe oglinda si dupa ce articolul expira, deci o pagina care cere o
imagine ar deveni imagine rupta in clipa in care imaginea e curatata. Masurat 2026-10-31:
imaginile de articol erau 2,88 din cei 3,73 GB publicati, cu plafonul GitHub Pages la 1 GB.
Comutatorul `ARTICLE_IMAGE_FILES=0` apara ambele parti: niciun fisier scris, nicio referinta.

Cazul cu comutatorul pornit e garda garzii: daca fixtura ar scrie zero imagini de la sine,
testul ar trece pe nimic (IZZ-0177).
"""
import re
from pathlib import Path

import pytest
import yaml

from generator import config, covers, editorial, publication, render

ROOT = Path(__file__).resolve().parent.parent
IMAGINE_ARTICOL = re.compile(r"/(?:cover\.jpg|art\.jpg|art\.webp|photo\.jpg|photo\.webp)")
LEAD = {"art": "lead.jpg", "webp": "lead.webp", "cover": "lead.c.jpg", "kind": "person",
        "name": "Persoana", "license": "CC0", "page": "https://example.org/poza"}


@pytest.fixture
def articol():
    return {"model": "B", "category": "local", "slug": "anunt-pilot",
            "url": "https://institution.example/notice/",
            "title": "Instituția anunță un calendar pentru serviciul public",
            "teaser": "Calendarul este o informație anunțată, nu un rezultat verificat.",
            "original_link": "https://institution.example/notice/", "source_name": "Instituția",
            "published": "2026-10-14T08:00:00Z", "processed_by": "official"}


def _randeaza(monkeypatch, tmp_path, articol, pornit, lead=LEAD):
    iesire = tmp_path / "output"

    def scrie(_src, dst):
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        Path(dst).write_bytes(b"imagine")
        return True

    monkeypatch.setattr(config, "ARTICLE_IMAGE_FILES", pornit)
    monkeypatch.setattr(render, "OUT_DIR", str(iesire))
    monkeypatch.setattr(render, "_load_leadphotos", lambda: {render.htmlart.art_id(articol): lead} if lead else {})
    monkeypatch.setattr(render, "_use_media", scrie)
    monkeypatch.setattr(covers, "generate", lambda _a, dst: scrie(None, dst))
    monkeypatch.setattr(render, "_quality_gate", lambda _a: True)
    monkeypatch.setattr(editorial, "load_annotations", lambda: {})
    monkeypatch.setattr(publication, "load", lambda: {})
    render.build([articol])
    return iesire / "local" / "anunt-pilot"


def test_primarul_pastreaza_imaginile(monkeypatch, tmp_path, articol):
    director = _randeaza(monkeypatch, tmp_path, articol, pornit=True)
    assert (director / "cover.jpg").exists()
    assert (director / "art.jpg").exists()
    assert IMAGINE_ARTICOL.search((director / "index.html").read_text(encoding="utf-8"))


def test_oglinda_nu_scrie_si_nu_cere_imagini(monkeypatch, tmp_path, articol):
    director = _randeaza(monkeypatch, tmp_path, articol, pornit=False)
    pagina = (director / "index.html").read_text(encoding="utf-8")
    assert [f.name for f in director.iterdir()] == ["index.html"]
    assert not IMAGINE_ARTICOL.search(pagina)
    assert "/og/local.jpg" in pagina      # previzualizarea sociala cade pe coperta de categorie
    assert "article-art-fig" not in pagina


@pytest.mark.parametrize("pornit", [True, False])
def test_imaginea_din_date_urmeaza_comutatorul(monkeypatch, tmp_path, articol, pornit):
    articol["event_chart"] = {"tip": "cutremur"}
    director = _randeaza(monkeypatch, tmp_path, articol, pornit, lead=None)
    assert (director / "art.jpg").exists() is pornit


def test_doar_jobul_mirror_opreste_imaginile():
    joburi = yaml.safe_load((ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8"))["jobs"]
    pasi = [(nume, pas) for nume, job in joburi.items() for pas in job.get("steps", [])]
    cu_comutator = [nume for nume, pas in pasi if "ARTICLE_IMAGE_FILES" in (pas.get("env") or {})]
    assert cu_comutator == ["mirror"]
