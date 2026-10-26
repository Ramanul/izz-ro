"""Source text observations expose their denominator, coverage and limits."""
import copy

from generator import render


def _measured(comparisons=3, changed=1):
    return {"text_observations": {"v": 1, "comparisons": comparisons, "changed": changed,
            "first_at": "2026-10-25T10:00:00+00:00", "last_at": "2026-10-25T12:00:00+00:00"}}


def _sources(catalog):
    for group in catalog:
        yield from group["with_stats"]
        for region in group["regions"]:
            for county in region["counties"]:
                yield from county["with_stats"]


def test_observation_coverage_uses_unique_first_source_urls_only():
    primary = {"name": "HotNews", "url": "https://hotnews.ro/first"}
    secondary = {"name": "Digi24", "url": "https://digi24.ro/second"}
    article = {"model": "C", "first_source": "HotNews", "sources": [primary, secondary]}
    third = copy.deepcopy(article)
    third["sources"][0]["url"] = "https://hotnews.ro/never-reread"
    metadata = {primary["url"]: _measured(), secondary["url"]: _measured(100, 0),
                "https://hotnews.ro/never-reread": {"sha256": "legacy-baseline"}}
    snapshot = copy.deepcopy(metadata)
    catalog, _, _ = render._source_catalog([article, copy.deepcopy(article), third], metadata)
    rows = {s["name"]: s for s in _sources(catalog)}
    observed = rows["HotNews"]["text_observations"]
    assert rows["HotNews"]["first"] == 3
    assert observed["articles_total"] == 2
    assert observed["articles_revisited"] == 1
    assert (observed["stable"], observed["comparisons"]) == (2, 3)
    assert rows["Digi24"]["text_observations"]["comparisons"] == 0
    assert metadata == snapshot


def test_legacy_and_invalid_history_are_unknown_not_a_stability_percentage():
    observed = render._source_text_observations({"legacy", "bad"}, {
        "legacy": {"sha256": "baseline"}, "bad": _measured(1, 2),
    })
    assert observed["articles_total"] == 2
    assert observed["articles_revisited"] == observed["comparisons"] == 0
    assert observed["first_at"] is observed["last_at"] is None


def test_invalid_url_history_cannot_inflate_or_erase_other_url_comparisons():
    invalid = _measured(500, 0)
    invalid["text_observations"]["v"] = True
    metadata = {"valid": _measured(), "invalid": invalid, "corrupt": [1]}
    snapshot = copy.deepcopy(metadata)
    observed = render._source_text_observations(set(metadata), metadata)
    assert (observed["articles_total"], observed["articles_revisited"]) == (3, 1)
    assert (observed["comparisons"], observed["stable"]) == (3, 2)
    assert metadata == snapshot


def test_window_is_union_of_comparable_observations_not_publication_dates():
    early = _measured(1, 0)
    early["text_observations"]["first_at"] = "2026-10-24T10:00:00+00:00"
    observed = render._source_text_observations({"early", "late"}, {"early": early, "late": _measured()})
    assert observed["first_at_human"] == "2026-10-24 10:00"
    assert observed["last_at_human"] == "2026-10-25 12:00"
    assert (observed["articles_revisited"], observed["comparisons"], observed["stable"]) == (2, 4, 3)


def test_observation_cell_shows_fraction_coverage_window_and_unknown():
    template = render._env().get_template("surse.html").make_module(render._base_ctx(
        "/surse/", catalog=[], total_sources=0, stats_sources=0, ttl_days=12, harta=None,
    ))
    observed = render._source_text_observations({"a", "b"}, {"a": _measured()})
    html = template.text_observations_cell({"text_observations": observed})
    assert "2/3" in html and "1/2 articole recitite" in html
    assert 'datetime="2026-10-25T10:00:00+00:00"' in html
    assert "UTC" in html and "%" not in html
    unknown = template.text_observations_cell({"text_observations": render._source_text_observations({"a"}, {})})
    assert "Nemăsurat" in unknown and "0/1 articole recitite" in unknown
    assert "0%" not in unknown


def test_sources_page_includes_limit_and_no_data_text():
    article = {"model": "C", "first_source": "HotNews", "sources": [
        {"name": "HotNews", "url": "https://hotnews.ro/a"},
        {"name": "Digi24", "url": "https://digi24.ro/a"},
    ]}
    catalog, total, stats = render._source_catalog([article, copy.deepcopy(article)], {})
    html = render._env().get_template("surse.html").render(**render._base_ctx(
        "/surse/", catalog=catalog, total_sources=total, stats_sources=stats,
        ttl_days=12, harta=None,
    ))
    assert "Text la recitire" in html and "Nemăsurat" in html
    assert "fracția nu măsoară adevărul" in html
    assert "intervalul observat, în UTC" in html
    assert "0/1 articole recitite" in html
