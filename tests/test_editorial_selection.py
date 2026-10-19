"""Shadow selection, documented reasons and conservative fallbacks."""
import copy
from datetime import datetime, timezone

import pytest

from generator import editorial
from generator.select import editorial_selection_comparison
import test_editorial_context as fixtures

article = fixtures.article
record = fixtures.record

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
