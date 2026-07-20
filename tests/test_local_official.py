"""Surse oficiale (primarii/CJ): procesare determinista, fara AI."""
from generator import config
from generator.process import process_official
from generator.main import process_new


def _official(**kw):
    base = {"source": "pl_ab_test", "original_title": "Sedinta de consiliu",
            "description": "Astazi a avut loc sedinta de consiliu local.",
            "category": "local", "url": "https://ex.ro/1", "source_lang": "ro"}
    base.update(kw)
    return base


def _normal(**kw):
    base = {"source": "digi24", "original_title": "Stire nationala",
            "description": "Descriere stire nationala.",
            "category": "general", "url": "https://ex.ro/2", "source_lang": "ro"}
    base.update(kw)
    return base


def test_official_basic():
    items = [_official()]
    result = process_official(items)
    assert len(result) == 1
    a = result[0]
    assert a["model"] == "B"
    assert a["processed_by"] == "official"
    assert a["title"] == "Sedinta de consiliu"
    assert a["teaser"]


def test_official_teaser_truncated():
    items = [_official(description="cuvant " * 60)]
    a = process_official(items)[0]
    assert len(a["teaser"].split()) <= config.TEASER_MAX_WORDS


def test_official_skips_english():
    assert process_official([_official(source_lang="en")]) == []


def test_process_new_handles_official_with_zero_budget():
    off = _official()
    norm = _normal()
    processed, folded, used = process_new([off, norm], provider=None, budget=0)
    urls = {a["url"] for a in processed}
    assert off["url"] in urls, "official should be processed even with budget=0"
    assert norm["url"] not in urls, "normal items should not appear in processed"
    official = [a for a in processed if a["url"] == off["url"]]
    assert official[0]["processed_by"] == "official"
