"""Fetch-ul paralel nu are voie sa strice ordinea surselor sau cache-ul.

Ordinea conteaza: bugetul AI proceseaza in ordinea din config.SOURCES, deci ce
ajunge la coada e infometat. Un `map` neordonat ar rearanja tacut prioritatile.
"""
import time

import pytest

from generator import config, fetch


def _fake_sources(n=12):
    return {f"src{i:02d}": {"url": f"https://example.invalid/{i}"} for i in range(n)}


def _patch(monkeypatch, sources, delay_for, err_keys=()):
    """Inlocuieste _fetch_one cu o varianta care intarzie controlat si scrie in cache."""
    monkeypatch.setattr(config, "SOURCES", sources)
    monkeypatch.setattr(fetch, "_cache_load", lambda: {})
    monkeypatch.setattr(fetch, "_cache_save", lambda cache: None)

    def fake_fetch_one(key, source, cache=None):
        time.sleep(delay_for(key))
        if cache is not None:
            cache[key] = {"etag": f"etag-{key}"}
        if key in err_keys:
            return [], f"{key}: mort"
        return [{"src": key}], None

    monkeypatch.setattr(fetch, "_fetch_one", fake_fetch_one)


def test_ordinea_surselor_se_pastreaza_desi_terminarea_e_inversa(monkeypatch):
    """Prima sursa e cea mai lenta, ultima cea mai rapida: ordinea trebuie sa reziste."""
    sources = _fake_sources(12)
    keys = list(sources)
    # src00 dureaza cel mai mult, src11 cel mai putin -> terminarea e fix inversa
    delays = {k: (len(keys) - i) * 0.02 for i, k in enumerate(keys)}
    _patch(monkeypatch, sources, lambda k: delays[k])

    items, dead = fetch.fetch_all()

    assert [it["src"] for it in items] == keys
    assert dead == []


def test_paralel_si_secvential_dau_acelasi_rezultat(monkeypatch):
    sources = _fake_sources(10)
    err = {"src03", "src07"}

    _patch(monkeypatch, sources, lambda k: 0.01, err_keys=err)
    monkeypatch.setattr(fetch, "MAX_WORKERS", 1)
    seq_items, seq_dead = fetch.fetch_all()

    _patch(monkeypatch, sources, lambda k: 0.01, err_keys=err)
    monkeypatch.setattr(fetch, "MAX_WORKERS", 8)
    par_items, par_dead = fetch.fetch_all()

    assert par_items == seq_items
    assert par_dead == seq_dead
    assert len(par_dead) == 2


def test_cache_primeste_toate_cheile_fara_pierderi(monkeypatch):
    """Fiecare task scrie doar cheia lui; nimic nu trebuie sa se piarda."""
    sources = _fake_sources(30)
    captured = {}

    monkeypatch.setattr(config, "SOURCES", sources)
    monkeypatch.setattr(fetch, "_cache_load", lambda: {})
    monkeypatch.setattr(fetch, "_cache_save", lambda cache: captured.update(cache))
    monkeypatch.setattr(fetch, "MAX_WORKERS", 8)

    def fake_fetch_one(key, source, cache=None):
        time.sleep(0.005)
        cache[key] = {"etag": f"etag-{key}"}
        return [{"src": key}], None

    monkeypatch.setattr(fetch, "_fetch_one", fake_fetch_one)
    fetch.fetch_all()

    assert set(captured) == set(sources)
    assert captured["src00"]["etag"] == "etag-src00"


def test_paralelizarea_chiar_e_mai_rapida(monkeypatch):
    """Sanity check: altfel testele ar trece si daca paralelizarea n-ar face nimic."""
    sources = _fake_sources(16)
    _patch(monkeypatch, sources, lambda k: 0.05)
    monkeypatch.setattr(fetch, "MAX_WORKERS", 8)

    start = time.monotonic()
    fetch.fetch_all()
    elapsed = time.monotonic() - start

    # secvential ar fi 16 * 0.05 = 0.8s; cu 8 workeri asteptam ~0.1s
    assert elapsed < 0.4, f"pare secvential: {elapsed:.2f}s"


def test_fetch_workers_1_ramane_secvential(monkeypatch):
    sources = _fake_sources(6)
    order = []

    monkeypatch.setattr(config, "SOURCES", sources)
    monkeypatch.setattr(fetch, "_cache_load", lambda: {})
    monkeypatch.setattr(fetch, "_cache_save", lambda cache: None)
    monkeypatch.setattr(fetch, "MAX_WORKERS", 1)

    def fake_fetch_one(key, source, cache=None):
        order.append(key)
        return [{"src": key}], None

    monkeypatch.setattr(fetch, "_fetch_one", fake_fetch_one)
    fetch.fetch_all()

    assert order == list(sources)


def _patch_raising(monkeypatch, sources, raise_keys):
    """`_fetch_one` care ARUNCA pentru anumite chei (feed malformat, bug in parser)."""
    monkeypatch.setattr(config, "SOURCES", sources)
    monkeypatch.setattr(fetch, "_cache_load", lambda: {})
    saved = {}
    monkeypatch.setattr(fetch, "_cache_save", lambda cache: saved.update(cache))

    def fake_fetch_one(key, source, cache=None):
        if key in raise_keys:
            raise ValueError(f"feed stricat: {key}")
        if cache is not None:
            cache[key] = {"etag": f"etag-{key}"}
        return [{"src": key}], None

    monkeypatch.setattr(fetch, "_fetch_one", fake_fetch_one)
    return saved


@pytest.mark.parametrize("workers", [8, 1])
def test_o_sursa_care_arunca_nu_omoara_fetch_ul(monkeypatch, workers):
    """O exceptie neprinsa dintr-o sursa = sursa moarta, NU build picat.

    `_fetch_one` prinde doar erorile de retea; `feedparser.parse` si bucla de
    entries pot arunca. Fara garda, `pool.map` re-ridica exceptia la iterare si
    pierde si sursele sanatoase, si cache-ul.
    """
    sources = _fake_sources(6)
    monkeypatch.setattr(fetch, "MAX_WORKERS", workers)
    saved = _patch_raising(monkeypatch, sources, raise_keys={"src02"})

    items, dead = fetch.fetch_all()

    assert [i["src"] for i in items] == [k for k in sources if k != "src02"]
    assert len(dead) == 1 and dead[0].startswith("src02: ")
    assert "feed stricat" in dead[0]
    assert "src02" not in saved and len(saved) == 5
