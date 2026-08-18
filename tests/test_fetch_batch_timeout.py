import time

from generator import config, fetch


def test_fetch_batch_timeout_does_not_block_all_sources(monkeypatch):
    sources = {
        "hung": {"url": "https://hung.invalid/feed"},
        "fast": {"url": "https://fast.invalid/feed"},
    }
    monkeypatch.setattr(config, "SOURCES", sources)
    monkeypatch.setattr(fetch, "MAX_WORKERS", 2)
    monkeypatch.setattr(fetch, "FETCH_BATCH_TIMEOUT_S", 0.03)
    monkeypatch.setattr(fetch, "_cache_load", lambda: {})
    monkeypatch.setattr(fetch, "_cache_save", lambda cache: None)

    def fake_fetch_one(key, source, cache=None, pacer=None):
        if key == "hung":
            time.sleep(0.20)
        return ([{"src": key}], None)

    monkeypatch.setattr(fetch, "_fetch_one_guarded", fake_fetch_one)
    started = time.monotonic()
    items, dead = fetch.fetch_all()
    elapsed = time.monotonic() - started

    assert elapsed < 0.12
    assert {item["src"] for item in items} == {"fast"}
    assert any(err.startswith("hung: fetch batch timeout") for err in dead)
