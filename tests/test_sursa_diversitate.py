from generator import render


def _art(domain: str, i: int) -> dict:
    return {
        "original_link": f"https://{domain}/stire-{i}",
        "source_name": domain,
    }


def test_diversify_caps_a_dominant_source_in_first_window():
    items = [_art("fcinternews.it", i) for i in range(10)] + [
        _art("gsp.ro", 0),
        _art("digisport.ro", 0),
        _art("sport.ro", 0),
        _art("fanatik.ro", 0),
    ]
    out = render._diversify(list(items), max_run=2, max_per_window=3, window_size=10)
    first = [render.domain_of(a["original_link"]) for a in out[:10]]
    assert first.count("fcinternews.it") == 3
    assert len(first) == 10


def test_diversify_keeps_all_items_after_the_window():
    items = [_art("fcinternews.it", i) for i in range(10)] + [_art("gsp.ro", 0)]
    out = render._diversify(list(items), max_run=2, max_per_window=3, window_size=10)
    assert len(out) == len(items)
    assert {id(x) for x in out} == {id(x) for x in items}


def test_diversify_does_not_cap_when_no_window_quota_is_requested():
    items = [_art("fcinternews.it", i) for i in range(5)]
    out = render._diversify(list(items), max_run=2)
    assert len(out) == 5


def test_diversify_uses_fallback_when_too_few_sources_exist():
    items = [_art("fcinternews.it", i) for i in range(5)]
    out = render._diversify(list(items), max_run=2, max_per_window=2, window_size=5)
    assert [a["source_name"] for a in out] == ["fcinternews.it"] * 5
