"""Shadow selection, documented reasons and conservative fallbacks."""
import copy
from datetime import datetime, timezone

import pytest

from generator import editorial, render
from generator.select import editorial_selection_comparison
import test_editorial_context as fixtures
import test_editorial_sources_practical as practical

article = fixtures.article
record = fixtures.record
examined = practical.examined

NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)


def selection(**changes):
    return {"priority": "context", "reason": "Documented context", "area": "national",
            "evidence_ids": ["e1"], **changes}


def test_valid_reason_and_input_preserved(article, record):  # noqa: F811
    record["selection"] = selection()
    before = copy.deepcopy(article)
    view = editorial.apply_view(article, {record["key"]: record}, {"sources": {}, "resources": {}}, NOW)
    report = editorial_selection_comparison([view], NOW)
    assert report["mode"] == "shadow"
    assert report["selected"][0]["reason"] == "Documented context"
    assert "reviewer" not in str(report)
    assert article == before


@pytest.mark.parametrize("value", [{}, selection(priority="positive"),
    selection(evidence_ids=["missing"]), selection(area=""),
    selection(expires_at="2026-10-01"), selection(priority="time_sensitive"),
    selection(priority="public_impact"), selection(priority="public_impact", impact_index=True)])
def test_invalid_reason_rejected(article, record, value):  # noqa: F811
    record["selection"] = value
    assert any("selection" in e for e in editorial.validate_annotations(
        {record["key"]: record}, [article], {"sources": {}, "resources": {}}))


def test_expired_scope_and_stale_views(article, record):  # noqa: F811
    rows = []
    for slug, changes in [("a", {}), ("b", {"area": "B"}),
                          ("c", {"expires_at": "2026-10-19T00:00:00Z"})]:
        rows.append({**article, "slug": slug, "editorial": {"selection": selection(**changes)}})
    before = copy.deepcopy(rows)
    report = editorial_selection_comparison(rows, NOW, area="TM")
    assert [r["path"] for r in report["selected"]] == ["/local/a/"]
    assert {r["reason"] for r in report["excluded"]} == {"expired", "outside_area"}
    assert rows == before
    assert editorial_selection_comparison(list(reversed(rows)), NOW, area="TM")["selected"] == report["selected"]
    assert not editorial_selection_comparison([article], NOW)["selected"]
    record["selection"] = selection()
    article["title"] += " changed"
    view = editorial.apply_view(article, {record["key"]: record}, {"sources": {}, "resources": {}}, NOW)
    assert not editorial_selection_comparison([view], NOW)["selected"]


@pytest.mark.parametrize("priority", ["time_sensitive", "public_impact"])
def test_documented_service_or_impact_is_eligible(examined, priority):  # noqa: F811
    item, annotation, provenance = examined
    annotation["selection"] = selection(priority=priority, area="Locality A")
    if priority == "time_sensitive":
        annotation["selection"]["expires_at"] = provenance["resources"]["r1"]["expires_at"]
    else:
        annotation["selection"]["impact_index"] = 0
    now = datetime(2026, 10, 17, tzinfo=timezone.utc)
    view = editorial.apply_view(item, {annotation["key"]: annotation}, provenance, now)
    assert editorial_selection_comparison([view], now)["selected"]


@pytest.mark.parametrize("field,value", [("actions", None), ("impacts", None),
    ("actions", [{"evidence_ids": [{}]}]), ("impacts", [{"evidence_ids": [{}]}])])
def test_malformed_evidence_extensions_return_errors(examined, field, value):  # noqa: F811
    item, annotation, provenance = examined
    annotation["selection"] = selection(
        priority="time_sensitive" if field == "actions" else "public_impact",
        area="Locality A", expires_at="2026-10-18T18:00:00+03:00", impact_index=0)
    annotation[field] = value
    assert editorial.validate_annotations({annotation["key"]: annotation}, [item], provenance)


def test_pilot_template_explains_reason_and_keeps_chronology(article):  # noqa: F811
    template = render._env().get_template("_editorial_selection.html")
    assert not template.render(editorial_selection=[], base="").strip()
    html = template.render(editorial_selection=[{
        "article": article, "reason": "<script>unsafe()</script>", "area": "Locality A"}], base="")
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert '/azi/' in html and '/principii/#cum-alegem-materialele-din-pilot' in html
    assert '/local/anunt-pilot/#editorial-context-title' in html
    assert 'data-pagefind-ignore' in html


def test_featured_and_ties_are_explicit_and_deterministic(article):  # noqa: F811
    rows = [{**article, "slug": slug, "featured": featured,
             "editorial": {"selection": selection()}}
            for slug, featured in [("z", False), ("a", False), ("f", True)]]
    chosen = editorial_selection_comparison(rows, NOW)["selected"]
    assert [row["path"] for row in chosen] == ["/local/f/", "/local/a/", "/local/z/"]
