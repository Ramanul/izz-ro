"""Regresii pentru suprafetele publice de incredere si descoperire.

Aceste teste protejeaza lucrurile care ar putea disparea tacut dintr-o randare:
canalul RFC 9116, contextul real al cautarii si actiunea de raportare a erorilor.
"""
from pathlib import Path

from generator import covers, render


def _article(**extra):
    article = {
        "category": "general",
        "slug": "test-de-incredere",
        "title": "Titlu de test",
        "display_title": "Titlu de test",
        "published": "2026-08-19T09:00:00+00:00",
        "published_human": "19 august 2026, 12:00",
        "updated_human": "19 august 2026, 14:00",
        "model": "C",
        "synthesis": "O sinteză de test bazată pe două surse publice.",
        "teaser": "",
        "source_name": "Sursa A",
        "original_link": "https://example.test/a",
        "sources": [
            {"name": "Sursa A", "url": "https://example.test/a"},
            {"name": "Sursa B", "url": "https://example.test/b"},
        ],
        "first_source": "Sursa A",
        "anunt_fara_corp": False,
        "ai_generat": True,
        "art_path": None,
        "art_webp": None,
        "lead_credit": None,
    }
    article.update(extra)
    return article


def test_security_txt_has_required_public_contact_and_policy(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_security_txt()
    text = (tmp_path / ".well-known" / "security.txt").read_text(encoding="utf-8")
    assert "Contact: mailto:contact@izz.ro" in text
    assert "Policy: https://izz.ro/legal/security/" in text
    assert "Canonical: https://izz.ro/.well-known/security.txt" in text
    assert "Expires: " in text
    assert len(text.splitlines()) == 5


def test_responsive_webp_scales_only_when_it_saves_bytes(tmp_path):
    assert covers.Image is not None, "Pillow este dependință de producție pentru imagini"
    source = tmp_path / "source.jpg"
    target = tmp_path / "card.webp"
    covers.Image.effect_noise((960, 504), 80).convert("RGB").save(source, "JPEG", quality=92)
    assert render._responsive_webp(str(source), str(target), max_width=480)
    with covers.Image.open(target) as image:
        assert image.size == (480, 252)


def test_search_page_explains_the_actual_index_scope():
    html = render._env().get_template("search.html").render(**render._base_ctx(
        "/cauta/", search_count=3519, search_days=7))
    assert "3,519" not in html  # nu formatam artificial: valoarea se afiseaza exact din generator
    assert "3519 știri păstrate în ultimele 7 zile" in html
    assert "nu textul integral al surselor" in html
    assert 'data-result-limit="50"' in html


def test_article_exposes_update_source_chronology_and_error_reporting():
    html = render._env().get_template("article.html").render(**render._base_ctx(
        "/general/test-de-incredere/", a=_article(), active_cat="general",
        topics=[], people=[], related=[]))
    assert "Actualizat: 19 august 2026, 14:00" in html
    assert "publicată prima" in html
    assert "Raportează o eroare" in html
    assert "Vezi politica de corecții" in html
    assert "contact@izz.ro?subject=" in html


def test_corrections_and_security_sources_exist():
    root = Path(render.ROOT) / "content" / "legal"
    assert (root / "corrections.md").is_file()
    assert (root / "security.md").is_file()


def test_csp_allows_only_observed_cloudflare_bootstrap_variants(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_headers()
    headers = (tmp_path / "_headers").read_text(encoding="utf-8")
    assert "sha256-DzqzfYrgtaakHyuPGKa5knFv5IoTaJszzL9Fca3521M=" in headers
    assert "sha256-LXd89R0ZNPfUJLyGqvxXmhTIA1mSPILGag0zh9noF7U=" in headers
    script_policy = headers.split("script-src ", 1)[1].split(";", 1)[0]
    assert "unsafe-inline" not in script_policy
