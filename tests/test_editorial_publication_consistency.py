"""Synthetic correction/withdrawal contracts, never production editorial records."""
import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from generator import editorial, publication, render
from tools import build_harta_data


@pytest.fixture
def article():
    return {"model": "B", "category": "local", "slug": "synthetic-correction",
            "title": "Primăria Arad anunță lucrări la rețeaua de apă",
            "teaser": "Instituția anunță lucrări la rețeaua de apă din municipiu. Calendarul este disponibil în documentul publicat de instituție.",
            "original_link": "https://institutie.example/anunt/", "source_name": "Instituția",
            "url": "https://institutie.example/anunt/",
            "source": "pl_arad_municipiul_arad", "processed_by": "official",
            "published": datetime.now(timezone.utc).isoformat()}


def correction(article, state="corrected"):
    row = {"key": editorial.annotation_key(article), "public_paths": [editorial.public_path(article)],
           "state": state, "notice": "Localitatea menționată anterior era greșită.",
           "evidence_url": "https://institutie.example/corectie/",
           "review": {"state": "approved", "kind": "documentary", "reviewer": "test-only",
                      "reviewed_at": "2026-10-17T18:00:00Z",
                      "input_fingerprint": editorial.source_fingerprint(article)},
           "presentation": {"title": "Primăria Timișoara anunță lucrări la rețeaua de apă",
                            "county": "TIMIS"} if state == "corrected" else {}}
    return {row["key"]: row}


def test_correction_copies_and_fingerprint_guards(article):
    rows = correction(article)
    before = copy.deepcopy((article, rows))
    result = publication.apply([article], rows)
    assert (article, rows) == before
    assert result[0]["editorial_county"] == "TIMIS"
    assert "Timișoara" in result[0]["title"]
    article["title"] += " cu date schimbate"
    with pytest.raises(editorial.EditorialError, match="source changed"):
        publication.apply([article], rows)


@pytest.mark.parametrize("change", [
    lambda r: r["presentation"].update(title="<script>alert(1)</script>"),
    lambda r: r["presentation"].update(county="UNKNOWN"),
    lambda r: r.update(evidence_url="javascript:alert(1)"),
    lambda r: r["review"].update(private_message="private"),
    lambda r: r.update(public_paths=["/../unsafe/"]),
])
def test_invalid_correction_rejected(article, change):
    rows = correction(article)
    change(next(iter(rows.values())))
    with pytest.raises(editorial.EditorialError):
        publication.apply([article], rows)


def test_deterministic_manifest_and_expired_withdrawal(article):
    rows = correction(article, "withdrawn")
    assert publication.apply([article], rows) == []
    manifest = publication.manifest([], rows)
    assert manifest == publication.manifest([], rows)
    assert manifest["active"] == []
    assert manifest["withdrawals"][0]["paths"] == [editorial.public_path(article)]
    publication.validate(rows, [])  # historical observed path persists after article expiry
    assert "test-only" not in json.dumps(manifest)


def test_county_list_and_map_agree_after_correction(article):
    view = publication.apply([article], correction(article))[0]
    assert render._stiri_pentru_judet([view], "TIMIS") == [view]
    assert render._stiri_pentru_judet([view], "ARAD") == []
    item = build_harta_data.locate(view, ["TIMIS", "ARAD"], {}, {})
    assert item["county"] == "TIMIS" and item["confidence"] == "editorial"


def test_expired_corrected_article_keeps_explanation(tmp_path, monkeypatch, article):
    out = tmp_path / "output"
    rows = correction(article)
    monkeypatch.setattr(render, "OUT_DIR", str(out))
    monkeypatch.setattr(publication, "load", lambda: rows)
    monkeypatch.setattr(editorial, "load_annotations", lambda: {})
    render.build([])
    page = (out / "local/synthetic-correction/index.html").read_text(encoding="utf-8")
    assert "Istoricul corecției" in page and "Localitatea menționată" in page
    manifest = json.loads((out / "editorial-publication.json").read_text(encoding="utf-8"))
    assert manifest["active"] == [] and manifest["history"][0]["state"] == "corrected"


def test_invalid_correction_preserves_previous_build(tmp_path, monkeypatch, article):
    out = tmp_path / "output"
    out.mkdir()
    sentinel = out / "previous.html"
    sentinel.write_text("previous release")
    rows = correction(article)
    next(iter(rows.values()))["review"]["input_fingerprint"] = "0" * 64
    monkeypatch.setattr(render, "OUT_DIR", str(out))
    monkeypatch.setattr(publication, "load", lambda: rows)
    monkeypatch.setattr(editorial, "load_annotations", lambda: {})
    with pytest.raises(editorial.EditorialError, match="source changed"):
        render.build([article])
    assert sentinel.read_text() == "previous release"


def test_map_and_manifest_share_future_and_budget_exclusions(tmp_path, monkeypatch, article):
    out = tmp_path / "output"
    future = {**article, "slug": "future-only", "url": "https://institutie.example/future/",
              "title": "Primăria anunță un calendar pentru lucrările viitoare",
              "published": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()}
    older = {**article, "slug": "budget-excluded", "url": "https://institutie.example/older/",
             "title": "Primăria publică un alt calendar pentru lucrările locale",
             "published": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}
    monkeypatch.setattr(render, "OUT_DIR", str(out))
    monkeypatch.setattr(publication, "load", lambda: {})
    monkeypatch.setattr(editorial, "load_annotations", lambda: {})
    monkeypatch.setattr(render, "_articole_publicabile", lambda n: 1)
    render.build([article, older, future])
    manifest = json.loads((out / "editorial-publication.json").read_text(encoding="utf-8"))
    map_data = json.loads((out / "static/harta-stiri/data/map.json").read_text(encoding="utf-8"))
    assert [row["path"] for row in manifest["active"]] == [editorial.public_path(article)]
    assert all(row["slug"] == article["slug"] for row in map_data["articles"])
    assert not (out / "local/future-only").exists()
    assert not (out / "local/budget-excluded").exists()


@pytest.mark.parametrize("withdrawn", [False, True])
def test_full_render_has_one_active_version(tmp_path, monkeypatch, article, withdrawn):
    out = tmp_path / "output"
    rows = correction(article, "withdrawn" if withdrawn else "corrected")
    monkeypatch.setattr(render, "OUT_DIR", str(out))
    monkeypatch.setattr(publication, "load", lambda: rows)
    monkeypatch.setattr(editorial, "load_annotations", lambda: {})
    render.build([article])
    manifest = json.loads((out / "editorial-publication.json").read_text(encoding="utf-8"))
    map_data = json.loads((out / "static/harta-stiri/data/map.json").read_text(encoding="utf-8"))
    assert manifest["digest"] == map_data["publication_digest"]
    page = (out / "local/synthetic-correction/index.html").read_text(encoding="utf-8")
    if withdrawn:
        assert "Material retras" in page and "Primăria Arad" not in page
        assert not manifest["active"] and not map_data["articles"]
        assert not (out / "local/synthetic-correction/cover.jpg").exists()
        for filename in ("index.html", "feed.xml", "search-index.json", "sitemap.xml"):
            assert "/local/synthetic-correction/" not in (out / filename).read_text(encoding="utf-8")
    else:
        assert "Primăria Timișoara" in page and "Corectat la" in page
        assert "Primăria Arad" not in page
        assert map_data["articles"][0]["county"] == "TIMIS"
        assert manifest["active"][0]["state"] == "corrected"
        for filename in ("index.html", "feed.xml", "search-index.json"):
            assert "Primăria Timișoara" in (out / filename).read_text(encoding="utf-8")
