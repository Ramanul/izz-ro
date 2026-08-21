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


def test_article_template_keeps_credited_photo_off_cards_and_og():
    """`photo_path` apare numai în article.html; cardurile și hero-ul citesc doar `art_path`."""
    for path in ("templates/_card.html", "templates/index.html"):
        with open(path, encoding="utf-8") as fh:
            assert "photo_path" not in fh.read(), path
    with open("templates/article.html", encoding="utf-8") as fh:
        article = fh.read()
    assert "a.photo_path or a.art_path" in article
    assert "credit_required" in article    # mențiunea modificării, cerută de CC BY-SA
