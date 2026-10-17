"""Examined provenance, attributed disagreement, geographic binding and expiry."""
import copy
import json
from datetime import datetime, timezone

import pytest

from generator import config, editorial, render


@pytest.fixture
def examined():
    article = {"model": "B", "category": "local", "slug": "pilot",
               "title": "Anunt oficial despre lucrari", "original_link": "https://authority.example/notice/",
               "processed_by": "official"}
    key = editorial.annotation_key(article)
    stamp = "2026-10-17T09:00:00Z"
    source = {"id": "s1", "name": "Authority", "url": article["original_link"],
              "role": "Official notice", "locator": "Paragraph 1", "verified_at": stamp,
              "origin": {"url": article["original_link"], "relation": "original",
                         "locator": "Identified issuer", "verified_at": stamp}}
    resource = {"id": "r1", "article_key": key, "title": "Read the notice", "url": source["url"],
                "organizer": "Authority", "area": "Locality A", "locator": "Paragraph 2",
                "verified_at": stamp, "expires_at": "2026-10-18T18:00:00+03:00",
                "deadline_basis": "Local time, explicitly examined"}
    record = {"key": key, "public_paths": [editorial.public_path(article)],
              "review": {"state": "approved", "kind": "documentary", "reviewer": "test",
                         "reviewed_at": stamp, "input_fingerprint": editorial.source_fingerprint(article)},
              "claims": [{"id": "c1", "text": "The authority announces an interruption.",
                          "status": "reported", "evidence_ids": ["e1"]}],
              "evidence": [{"id": "e1", "url": source["url"], "locator": "Paragraph 1",
                            "role": "Official notice", "verified_at": stamp, "provenance_id": "s1"}],
              "impacts": [{"group": "Users in Locality A", "effect": "Announced interruption",
                           "status": "projected", "horizon": "17–18 October", "evidence_ids": ["e1"]}],
              "actions": [{"resource_id": "r1", "area": "Locality A", "evidence_ids": ["e1"]}]}
    return article, record, {"sources": {"s1": source}, "resources": {"r1": resource}}


def view(examined, now="2026-10-17T12:00:00+00:00"):
    article, record, provenance = examined
    return editorial.apply_view(article, {record["key"]: record}, provenance, datetime.fromisoformat(now))


def test_five_republications_have_one_known_origin(examined):
    _, record, provenance = examined
    for i in range(2, 6):
        sid, eid = f"s{i}", f"e{i}"
        source = copy.deepcopy(provenance["sources"]["s1"])
        source.update(id=sid, name=f"Publication {i}", url=f"https://publication{i}.example/notice/")
        source["origin"]["relation"] = "republication"
        provenance["sources"][sid] = source
        evidence = copy.deepcopy(record["evidence"][0])
        evidence.update(id=eid, url=source["url"], provenance_id=sid)
        record["evidence"].append(evidence)
    before = copy.deepcopy(examined)
    context = view(examined)["editorial"]
    assert len(context["comparison"]) == 5
    assert context["known_origins"] == 1 and context["unknown_origins"] == 0
    assert examined == before
    html = render._env().get_template("_source_comparison.html").render(a={"editorial": context})
    assert "1 origine documentată" in html and "nu reprezintă verificări independente" in html
    assert html.count("Preluare cu origine comună documentată") == 4


def test_unknown_origin_never_claims_independence(examined):
    examined[2]["sources"]["s1"].pop("origin")
    context = view(examined)["editorial"]
    assert context["known_origins"] == 0 and context["unknown_origins"] == 1
    html = render._env().get_template("_source_comparison.html").render(a={"editorial": context})
    assert "independența nu a fost verificată" in html


def test_disagreement_keeps_both_attributed_numbers(examined):
    _, record, _ = examined
    second = copy.deepcopy(record["evidence"][0])
    second.update(id="e2", url="https://other.example/report/")
    second.pop("provenance_id")
    record["evidence"].append(second)
    record["differences"] = [{"topic": "Number affected", "positions": [
        {"evidence_id": "e1", "text": "The authority reports 10 users."},
        {"evidence_id": "e2", "text": "The publication reports 20 users."}]}]
    html = render._env().get_template("_source_comparison.html").render(a=view(examined))
    assert "10 users" in html and "20 users" in html and "15 users" not in html
    assert '#editorial-evidence-e1' in html and '#editorial-evidence-e2' in html
    record["differences"][0]["positions"][1]["evidence_id"] = "e1"
    with pytest.raises(editorial.EditorialError, match="different examined evidence"):
        view(examined)


@pytest.mark.parametrize("now,state", [("2026-10-18T14:59:59+00:00", "current"),
                                      ("2026-10-18T15:00:00+00:00", "expired"),
                                      ("2026-10-19T08:00:00+00:00", "expired")])
def test_expiry_boundary_and_public_copy(examined, now, state):
    current = view(examined, now)
    assert current["editorial"]["actions"][0]["state"] == state
    html = render._env().get_template("_editorial_context.html").render(a=current)
    assert ("informație istorică" in html) == (state == "expired")
    assert ("Interval anunțat încă neîncheiat" in html) == (state == "current")
    assert "efect anunțat sau prognozat; nu confirmă rezultatul" in html
    assert "18.10.2026, 18:00" in html


def test_undated_resource_is_not_counted_as_current(examined):
    article, record, provenance = examined
    provenance["resources"]["r1"].pop("expires_at")
    assert view(examined)["editorial"]["actions"][0]["state"] == "undated"
    report = editorial.catalog_report({record["key"]: record}, [article], provenance)
    assert report["resources_without_deadline"] == 1 and report["resources_current"] == 0


@pytest.mark.parametrize("mutation", ["area", "article", "destination", "withdrawn", "missing_source"])
def test_wrong_area_article_unexamined_destination_and_withdrawal_block(examined, mutation):
    _, record, provenance = examined
    if mutation == "area":
        record["actions"][0]["area"] = "Locality B"
    elif mutation == "article":
        provenance["resources"]["r1"]["article_key"] = "article:/local/elsewhere/"
    elif mutation == "destination":
        provenance["resources"]["r1"]["url"] = "https://unexamined.example/"
    elif mutation == "withdrawn":
        record["evidence"][0]["status"] = "withdrawn"
    else:
        record["evidence"][0]["provenance_id"] = "missing"
    with pytest.raises(editorial.EditorialError):
        view(examined)


@pytest.mark.parametrize("field,value", [("url", "javascript:alert(1)"), ("verified_at", "2026-10-17"),
                                        ("origin", []), ("private", "secret")])
def test_bad_provenance_catalog_fails_closed(tmp_path, examined, field, value):
    provenance = examined[2]
    provenance["sources"]["s1"][field] = value
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({"schema_version": 1, "records": list(provenance["sources"].values()),
                                "resources": list(provenance["resources"].values())}), encoding="utf-8")
    with pytest.raises(editorial.EditorialError):
        editorial.load_provenance(path)


def test_examined_catalog_roundtrip_and_no_unexamined_deadline(tmp_path, examined):
    provenance = examined[2]
    data = {"schema_version": 1, "records": list(provenance["sources"].values()),
            "resources": list(provenance["resources"].values())}
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert editorial.load_provenance(path) == provenance
    data["resources"][0].pop("deadline_basis")
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(editorial.EditorialError, match="deadline_basis"):
        editorial.load_provenance(path)


def test_changed_article_hides_practical_resource(examined):
    examined[0]["title"] = "Changed material needs another review"
    assert "editorial" not in view(examined)


def test_report_matches_rendered_resources_and_excludes_absent_articles(examined):
    article, record, provenance = examined
    index = {record["key"]: record}
    report = editorial.catalog_report(index, [article], provenance, datetime(2026, 10, 19, tzinfo=timezone.utc))
    assert report["articles_with_provenance"] == report["articles_with_impacts"] == report["resources_expired"] == 1
    absent = editorial.catalog_report(index, [], provenance)
    assert absent["resources_current"] == absent["resources_expired"] == absent["articles_with_provenance"] == 0


def test_unannotated_article_has_no_new_context(examined):
    article = examined[0]
    assert editorial.apply_view(article, {}, examined[2]) == article


def test_context_without_new_provenance_keeps_existing_presentation(examined):
    _, record, _ = examined
    record["evidence"][0].pop("provenance_id")
    record.pop("impacts")
    record.pop("actions")
    current = view(examined)
    assert current["editorial"]["comparison"] == []
    html = render._env().get_template("_editorial_context.html").render(a=current)
    assert "Proveniența documentelor examinate" not in html
    assert "Informații practice documentate" not in html


def test_bad_provenance_stops_before_removing_previous_output(monkeypatch, tmp_path, examined):
    catalog = tmp_path / "content/editorial/source-provenance.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text('{"schema_version":1,"records":"invalid","resources":[]}', encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "previous.html"
    sentinel.write_text("Previous good output", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", str(tmp_path))
    monkeypatch.setattr(render, "OUT_DIR", str(output))
    monkeypatch.setattr(render, "_quality_gate", lambda a: True)
    with pytest.raises(editorial.EditorialError, match="provenance.records"):
        render.build([examined[0]])
    assert sentinel.read_text(encoding="utf-8") == "Previous good output"


def test_republication_needs_an_examined_original_in_catalog(tmp_path, examined):
    source = examined[2]["sources"]["s1"]
    source["origin"].update(relation="republication", url="https://unexamined.example/original/")
    path = tmp_path / "provenance.json"
    path.write_text(json.dumps({"schema_version": 1, "records": [source], "resources": []}), encoding="utf-8")
    with pytest.raises(editorial.EditorialError, match="examined original"):
        editorial.load_provenance(path)
