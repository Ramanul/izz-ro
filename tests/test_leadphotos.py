"""Teste offline pentru partile pure ale fetcher-ului de lead-photos."""
import importlib.util
import os

from PIL import Image

spec = importlib.util.spec_from_file_location(
    "fetch_leadphotos", os.path.join(os.path.dirname(__file__), "..", "tools", "fetch_leadphotos.py"))
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)


def test_public_domain_gate_excludes_cc_by():
    for ok in ("CC0", "cc-zero", "Public domain", "PD", "PD-old"):
        assert lp.is_public_domain(ok), ok
    for bad in ("CC BY 4.0", "CC BY-SA 4.0", "Copyrighted", "Fair use", "", None):
        assert not lp.is_public_domain(bad), bad


def test_landscape_gate():
    assert lp.is_landscape(1200, 800)      # 1.5 -> landscape
    assert lp.is_landscape(1000, 800)      # 1.25 -> landscape (>=1.2)
    assert not lp.is_landscape(800, 800)   # patrat
    assert not lp.is_landscape(600, 900)   # portret
    assert not lp.is_landscape(0, 0)


def test_qualifies_needs_both_landscape_and_pd():
    assert lp.qualifies({"width": 1600, "height": 900, "license": "Public domain"})
    assert not lp.qualifies({"width": 1600, "height": 900, "license": "CC BY 4.0"})   # PD lipsa
    assert not lp.qualifies({"width": 800, "height": 1200, "license": "CC0"})         # portret
    assert not lp.qualifies({"width": 0, "height": 0, "license": "CC0"})


def test_crop_to_produces_exact_dims_without_distortion():
    src = Image.new("RGB", (2000, 1000), (10, 20, 30))   # 2:1
    for w, h in [(1200, 630), (960, 504)]:
        out = lp.crop_to(src, w, h)
        assert out.size == (w, h)
    # sursa mai mica decat tinta -> tot produce exact dimensiunile (upscale, fara crash)
    small = Image.new("RGB", (400, 300), (0, 0, 0))
    assert lp.crop_to(small, 1200, 630).size == (1200, 630)


def test_save_renditions_writes_valid_cover_art_webp(tmp_path, monkeypatch):
    import io
    monkeypatch.setattr(lp, "OUTDIR", str(tmp_path))
    buf = io.BytesIO()
    Image.new("RGB", (1600, 1000), (30, 90, 160)).save(buf, format="JPEG")
    rend = lp._save_renditions(buf.getvalue(), "test-entity")
    assert rend == {"cover": "leads/test-entity.c.jpg", "art": "leads/test-entity.jpg",
                    "webp": "leads/test-entity.webp"}
    assert Image.open(tmp_path / "test-entity.c.jpg").size == (lp.COVER_W, lp.COVER_H)
    assert Image.open(tmp_path / "test-entity.jpg").size == (lp.ART_W, lp.ART_H)
    assert (tmp_path / "test-entity.webp").exists()
