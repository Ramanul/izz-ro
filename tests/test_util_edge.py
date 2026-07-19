"""Edge-case tests for pure functions in generator/util.py."""
from generator.util import (clean_html, domain_of, normalize_url,
                            strip_diacritics, title_tokens, truncate_words)


def test_strip_diacritics_empty_and_ascii():
    assert strip_diacritics("") == ""
    assert strip_diacritics("hello world") == "hello world"


def test_normalize_url_no_scheme_and_port():
    result = normalize_url("www.Example.com/articol")
    assert result.startswith("https://")
    result_port = normalize_url("https://example.com:8080/path")
    assert ":8080" in result_port


def test_normalize_url_empty_and_query_stripping():
    assert normalize_url("") == ""
    result = normalize_url("https://example.com/page?fbclid=abc&gclid=xyz")
    assert "fbclid" not in result and "gclid" not in result
    assert result == "https://example.com/page"


def test_domain_of_invalid_and_empty():
    assert domain_of("") == ""
    assert domain_of("not-a-valid-url") == ""


def test_clean_html_empty_and_plain():
    assert clean_html("") == ""
    assert clean_html("text fara taguri") == "text fara taguri"


def test_truncate_words_empty_and_boundary():
    assert truncate_words("", 5) == ""
    assert truncate_words("a b c", 3) == "a b c"
    assert truncate_words("a b c", 2) == "a b..."


def test_title_tokens_only_stopwords_and_empty():
    assert title_tokens("") == set()
    assert title_tokens("si sau dar") == set()
    assert title_tokens("a b c d") == set()
