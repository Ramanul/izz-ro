"""Regresii pentru politica de imagini: coperțile publice trebuie să fie fără credit obligatoriu."""
from generator import render


def _lead(license_name: str | None) -> dict:
    return {
        "cover": "leads/test.c.jpg",
        "art": "leads/test.jpg",
        "webp": "leads/test.webp",
        "license": license_name,
        "page": "https://commons.wikimedia.org/wiki/File:Test.jpg",
        "name": "Test",
    }


def test_credit_free_gate_accepts_public_domain_and_cc0():
    assert render._leadphoto_is_publication_safe(_lead("Public domain"))
    assert render._leadphoto_is_publication_safe(_lead("CC0"))


def test_credit_free_gate_rejects_attribution_and_unknown_licenses():
    for license_name in ("CC BY 4.0", "CC BY-SA 4.0", "Copyrighted", "", None):
        assert not render._leadphoto_is_publication_safe(_lead(license_name)), license_name


def test_public_policy_is_present_and_explains_the_source_image_rule():
    with open("content/legal/images.md", encoding="utf-8") as fh:
        policy = fh.read()
    assert "nu reproduce" in policy
    assert "nu reprezintă o licență" in policy
    assert "CC BY sau CC BY-SA" in policy


def test_credit_required_allowlist_is_positive_not_a_catch_all():
    """CC BY / CC BY-SA intră în nivelul cu credit; necunoscutul rămâne afară, nu cade în el."""
    for license_name in ("CC BY 4.0", "CC BY 3.0", "CC BY-SA 4.0", "CC BY-SA 3.0", "CC BY-SA 3.0 ro"):
        assert render._is_credit_required_license(license_name), license_name
    for license_name in ("Copyrighted", "Attribution", "CC BY-NC 4.0", "", None, "CC0", "Public domain"):
        assert not render._is_credit_required_license(license_name), license_name


def test_credit_required_photo_is_not_publication_safe_for_lead_surfaces():
    """Poarta LEAD (card / hero / og:image) rămâne închisă pentru orice cere atribuire."""
    for license_name in ("CC BY 4.0", "CC BY-SA 4.0", "CC BY-SA 3.0 ro"):
        rec = _lead(license_name)
        assert render._leadphoto_is_article_only(rec), license_name
        assert not render._leadphoto_is_publication_safe(rec), license_name


def test_article_only_gate_rejects_unusable_records():
    """Fără fișiere complete ori cu licență necunoscută, poza nu intră în niciun nivel."""
    assert not render._leadphoto_is_article_only({**_lead("CC BY 4.0"), "miss": True})
    assert not render._leadphoto_is_article_only({**_lead("CC BY 4.0"), "webp": ""})
    assert not render._leadphoto_is_article_only(_lead("Copyrighted"))


def test_license_url_matches_creative_commons_deed_and_is_none_otherwise():
    """CC BY 4.0 par.3(a)(1)(C) cere URI-ul licenței lângă credit, nu doar numele ei."""
    assert render._license_url("CC BY 4.0") == "https://creativecommons.org/licenses/by/4.0/"
    assert render._license_url("CC BY-SA 3.0 ro") == "https://creativecommons.org/licenses/by-sa/3.0/ro/"
    assert render._license_url("Public domain") is None
    assert render._license_url("CC0") is None


def test_article_template_prefers_credited_photo_and_keeps_it_off_cards():
    """`photo_path` apare numai în article.html; cardurile și hero-ul citesc doar `art_path`."""
    for path in ("templates/_card.html", "templates/index.html"):
        with open(path, encoding="utf-8") as fh:
            assert "photo_path" not in fh.read(), path
    with open("templates/article.html", encoding="utf-8") as fh:
        article = fh.read()
    assert "a.photo_path or a.art_path" in article
    assert "decupat de IZZ.ro" in article
    assert article.index('type="image/avif"') < article.index('type="image/webp"')
    assert article.index('type="image/webp"') < article.index('<img class="article-art"')
    for path in ("templates/_card.html", "templates/index.html"):
        with open(path, encoding="utf-8") as fh:
            template = fh.read()
        assert "art_avif" in template, path
        assert "photo_avif" not in template, path


def test_avif_media_helper_copies_only_the_adjacent_nonempty_derivative(tmp_path, monkeypatch):
    media = tmp_path / "media"
    source = media / "leads" / "sample.avif"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"validated-avif-output")
    monkeypatch.setattr(render, "MEDIA_DIR", str(media))

    destination = tmp_path / "output" / "article" / "art.avif"
    assert render._use_avif_media("leads/sample.jpg", str(destination))
    assert destination.read_bytes() == source.read_bytes()
    assert not render._use_avif_media(
        "leads/missing.jpg", str(tmp_path / "output" / "article" / "missing.avif")
    )


def test_avif_assets_receive_the_image_cache_policy(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_headers()
    headers = (tmp_path / "_headers").read_text(encoding="utf-8")
    assert "/*.avif\n  Cache-Control: public, max-age=86400" in headers
