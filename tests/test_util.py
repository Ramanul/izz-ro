"""Teste pentru functiile pure din generator/util.py."""
from generator.util import (clean_html, domain_of, normalize_url,
                            strip_diacritics, title_tokens, truncate_words)


def test_strip_diacritics():
    assert strip_diacritics("șțăâî ȘȚĂÂÎ") == "staai STAAI"


def test_normalize_url_dedup_key():
    # www + tracking + fragment + trailing slash -> aceeasi cheie
    a = normalize_url("https://www.Example.com/articol/?utm_source=fb&fbclid=x#top")
    b = normalize_url("https://example.com/articol")
    assert a == b == "https://example.com/articol"


def test_normalize_url_keeps_real_query():
    assert "id=42" in normalize_url("https://example.com/a?id=42&utm_medium=rss")
    assert "utm_medium" not in normalize_url("https://example.com/a?id=42&utm_medium=rss")


def test_domain_of():
    assert domain_of("https://www.Digi24.ro/stiri/x") == "digi24.ro"
    assert domain_of("") == ""


def test_clean_html_strips_tags_and_footers():
    raw = '<p>Guvernul a <b>decis</b> azi.</p> The post Guvernul appeared first on Site.'
    assert clean_html(raw) == "Guvernul a decis azi."


def test_clean_html_bullets_and_entities():
    assert clean_html("• Primul &amp; al doilea") == "Primul & al doilea"


def test_truncate_words():
    assert truncate_words("unu doi trei patru", 2) == "unu doi..."
    assert truncate_words("unu doi", 5) == "unu doi"


def test_title_tokens_filters_stopwords_and_short():
    toks = title_tokens("Guvernul a decis creșterea pensiilor în România")
    assert "guvernul" in toks and "pensiilor" in toks
    assert "a" not in toks and "in" not in toks
