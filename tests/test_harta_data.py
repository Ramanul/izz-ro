"""Teste pentru datasetul static al hărții știrilor."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path("tools/build_harta_data.py")
spec = importlib.util.spec_from_file_location("build_harta_data", MODULE_PATH)
assert spec and spec.loader
harta_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harta_data)


def item(title: str, *, county: str = "BRASOV", locality: str = "", published: str = "2026-08-19T10:00:00+00:00") -> dict:
    return {
        "title": title,
        "slug": title.lower().replace(" ", "-"),
        "county": county,
        "locality": locality,
        "published": published,
        "source": "sursa-test",
    }


def test_similar_local_articles_are_grouped_as_one_event():
    articles = [
        item("Accident rutier grav cu trei răniți pe DN1 în Brașov", locality="BRASOV"),
        item("Accident grav pe DN1 în Brașov: trei răniți", locality="BRASOV", published="2026-08-19T10:30:00+00:00"),
    ]
    result = harta_data.annotate_events(articles)
    assert result[0]["event_id"] == result[1]["event_id"]
    assert result[0]["event_article_count"] == 2


def test_events_from_different_localities_or_counties_are_never_merged():
    articles = [
        item("Accident rutier grav cu trei răniți pe DN1", locality="BRASOV"),
        item("Accident rutier grav cu trei răniți pe DN1", locality="SACELE"),
        item("Accident rutier grav cu trei răniți pe DN1", county="CLUJ", locality="CLUJ"),
    ]
    result = harta_data.annotate_events(articles)
    assert len({article["event_id"] for article in result}) == 3


def test_events_from_different_regions_are_never_merged():
    articles = [
        {**item("Avertizare meteo regională", county=""), "region": "Transilvania"},
        {**item("Avertizare meteo regională", county=""), "region": "Oltenia"},
    ]
    result = harta_data.annotate_events(articles)
    assert result[0]["event_id"] != result[1]["event_id"]


def test_event_grouping_rejects_articles_far_apart_in_time():
    articles = [
        item("Accident rutier grav cu trei răniți pe DN1", locality="BRASOV"),
        item("Accident rutier grav cu trei răniți pe DN1", locality="BRASOV", published="2026-08-22T11:00:00+00:00"),
    ]
    result = harta_data.annotate_events(articles)
    assert result[0]["event_id"] != result[1]["event_id"]


def test_generated_dataset_has_coherent_quality_metrics():
    import json

    data = json.loads(Path("static/harta-stiri/data/map.json").read_text(encoding="utf-8"))
    articles = data["articles"]
    stats = data["stats"]
    named = {
        article["siruta"] or f"{harta_data.norm(article['locality'])}|{article['county']}"
        for article in articles
        if article.get("locality")
    }
    assert data["version"] >= 4
    assert data["latest_article_at"]
    assert stats["total"] == len(articles)
    assert stats["events"] == len({article["event_id"] for article in articles})
    assert stats["localities"] == len(named)
    assert stats["county_only"] == sum(bool(article.get("county")) and not article.get("locality") for article in articles)
    assert stats["regional"] == sum(article.get("geo_level") == "regional" for article in articles)
    assert all(article.get("geo_level") in {"local", "judetean", "regional"} for article in articles)
    assert stats["coordinates"] == sum(article.get("x") is not None and article.get("y") is not None for article in articles)
    assert stats["geocoded_localities"] <= stats["localities"]


def test_ambiguous_locality_requires_an_independent_county_confirmation():
    by_name = {
        "VECHI": [{"name": "VECHI", "county": "TELEORMAN", "siruta": "152859", "level": "3"}],
    }
    text = "Stocuri vechi de materiale nucleare au fost găsite în Siria"
    assert harta_data.locality_from_text(text, None, by_name) is None
    assert harta_data.locality_from_text(text, "TELEORMAN", by_name)["county"] == "TELEORMAN"
