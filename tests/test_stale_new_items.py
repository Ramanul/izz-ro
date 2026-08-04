"""Un articol deja expirat la citire nu trebuie sa intre in pipeline.

Feed-urile institutionale (primarii) publica rar si isi tin intrarile luni de zile, asa
ca majoritatea itemelor „noi" sunt peste `ARTICLE_TTL_DAYS` chiar in clipa in care sunt
citite. Masurat pe un fetch real (2026-08-02): 795 din 1096 „noi" (73%), de la 126 de
surse. Inainte de fix fiecare dintre ele consuma din bugetul AI, ajungea in `combined`,
era sters de `expire()` la finalul ACELEIASI rulari si revenea „nou" la urmatoarea.

Ce NU se schimba: ce se publica. `expire()` le stergea oricum. Testul apara trei lucruri —
ca vechiturile sunt sarite, ca `stats["new"]` nu le mai numara, si ca itemele fara data
NU sunt victime colaterale (fara data, `_parse_iso` cade pe `now()`, deci sunt proaspete).
"""
from datetime import datetime, timedelta, timezone

import pytest

from generator import config, main, state


def _item(url: str, published: str | None) -> dict:
    """Forma minima a unui item asa cum il intoarce fetch."""
    it = {
        "url": url,
        "source": "test_src",
        "source_name": "Test",
        "title": f"titlu {url}",
        "original_title": f"titlu {url}",
        "description": "",
        "category": "extern",
        "model": None,
    }
    if published is not None:
        it["published"] = published
    return it


def _iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


@pytest.fixture
def ruleaza(tmp_path, monkeypatch):
    """Ruleaza main.run pe un set de iteme date, fara retea si fara AI."""
    def _run(items):
        p = tmp_path / "articles.json"
        p.write_text("[]", encoding="utf-8")
        monkeypatch.setattr(state, "STATE_PATH", str(p))
        monkeypatch.setattr(main.fetch, "fetch_all", lambda: (items, []))
        # fara provider -> fara apeluri AI; process_new merge pe calea fallback
        monkeypatch.setattr(main, "get_provider", lambda: None)
        return main.run(dry_run=True)
    return _run


def test_itemele_deja_expirate_nu_intra(ruleaza):
    vechi = config.ARTICLE_TTL_DAYS + 3
    stats = ruleaza([
        _item("https://x.ro/proaspat", _iso(1)),
        _item("https://x.ro/vechi-1", _iso(vechi)),
        _item("https://x.ro/vechi-2", _iso(vechi + 10)),
    ])
    assert stats["stale_skipped"] == 2
    assert stats["new"] == 1, "stats['new'] numara articole care nu pot supravietui rularii"


def test_itemul_fara_data_e_tratat_ca_proaspat(ruleaza):
    """Regresia de evitat: filtrul sa nu inghita itemele fara data.

    `expire()` foloseste `_parse_iso`, care pe o valoare lipsa sau invalida cade pe
    `now()`. Daca cineva schimba asta in „foarte vechi", articolele fara data ar
    disparea tacit — de aici testul.
    """
    stats = ruleaza([
        _item("https://x.ro/fara-data", None),
        _item("https://x.ro/data-aiurea", "nu-i o data"),
    ])
    assert stats["stale_skipped"] == 0
    assert stats["new"] == 2


def test_pragul_e_exact_ttl_ul_din_config(ruleaza):
    """Chiar sub prag ramane, clar peste prag pleaca — fara sa hardcodam 7."""
    stats = ruleaza([
        _item("https://x.ro/sub-prag", _iso(config.ARTICLE_TTL_DAYS - 0.5)),
        _item("https://x.ro/peste-prag", _iso(config.ARTICLE_TTL_DAYS + 0.5)),
    ])
    assert stats["stale_skipped"] == 1
    assert stats["new"] == 1


def test_nimic_expirat_nu_raporteaza_nimic(ruleaza):
    stats = ruleaza([_item("https://x.ro/a", _iso(0.1)), _item("https://x.ro/b", _iso(2))])
    assert stats["stale_skipped"] == 0
    assert stats["new"] == 2
