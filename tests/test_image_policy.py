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
