"""Evidence, limited review scope, stale input and fail-before-clean contracts."""
import copy
import json
import os
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

from generator import config, editorial, render


class Elements(HTMLParser):
    """Inspect rendered tags with the standard library, without a new dependency."""

    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


@pytest.fixture
def article():
    return {"model": "B", "category": "local", "slug": "anunt-pilot",
            "title": "Primaria anunta lucrari la reteaua de apa",
            "teaser": "Lucrarile anuntate de institutie au un calendar public. Cititorii pot consulta documentul original.",
            "original_link": "https://institutie.example/anunt/", "source_name": "Instituția",
            "published": "2026-10-14T08:00:00Z", "processed_by": "official"}


@pytest.fixture
def record(article):
    return {"key": editorial.annotation_key(article),
            "public_paths": [editorial.public_path(article)],
            "review": {"state": "approved", "kind": "documentary", "reviewer": "internal-pilot-id",
                       "reviewed_at": "2026-10-14T09:00:00Z",
                       "input_fingerprint": editorial.source_fingerprint(article)},
            "claims": [{"id": "c1", "text": "Instituția anunță un calendar; nu confirmăm rezultatul.",
                        "status": "reported", "evidence_ids": ["e1"]}],
            "evidence": [{"id": "e1", "url": article["original_link"], "locator": "Paragraful 2",
                          "role": "Instituția emitentă; o singură sursă",
                          "verified_at": "2026-10-14T09:00:00Z"}],
            "uncertainties": [{"question": "Lucrările s-au încheiat?", "needed": "Un raport ulterior."}]}


def index(record):
    return {record["key"]: record}


def context_html(article, record):
    view = editorial.apply_view(article, index(record))
    return render._env().get_template("_editorial_context.html").render(a=view)


def test_missing_catalog_and_unannotated_copy(tmp_path, article):
    assert editorial.load_annotations(tmp_path / "missing.json") == {}
    view = editorial.apply_view(article, {})
    assert view == article and view is not article


def test_approved_context_leaves_both_inputs_identical(article, record):
    before_article, before_record = copy.deepcopy(article), copy.deepcopy(record)
    view = editorial.apply_view(article, index(record))
    view["editorial"]["claims"][0]["text"] = "Changed view"
    assert article == before_article and record == before_record
    assert "reviewer" not in view["editorial"]


@pytest.mark.parametrize("field,value", [("title", "Altă afirmație"), ("teaser", "Nu se mai aplică"),
                                       ("original_link", "https://alta.example/anunt/")])
def test_changed_material_withholds_context(article, record, field, value):
    article[field] = value
    view = editorial.apply_view(article, index(record))
    assert "editorial" not in view and view["editorial_status"] == "needs_review"
    report = editorial.catalog_report(index(record), [article])
    assert report["fresh"] == 0 and report["needs_review"] == 1


def test_render_fields_and_whitespace_do_not_change_fingerprint(article):
    fingerprint = editorial.source_fingerprint(article)
    article.update(published_human="Today", updated_human="Later", ai_generat=False,
                   display_title="Display", ghid={"name": "Guide"}, editorial={"old": "data"})
    article["title"] = "  " + article["title"].replace(" ", "  ") + "\n"
    assert editorial.source_fingerprint(article) == fingerprint


def test_official_empty_body_and_source_dedup_have_stable_fingerprint(article):
    article.update(teaser="Detalii pe sursa.", sources=[{"name": "A", "url": "https://a.example/x"},
                                                      {"name": "A again", "url": "https://a.example/y"}])
    fingerprint = editorial.source_fingerprint(article)
    render._dedup_sources(article)
    article["teaser"] = ""
    assert editorial.source_fingerprint(article) == fingerprint


@pytest.mark.parametrize("state", ["draft", "withdrawn"])
def test_unapproved_context_is_hidden(article, record, state):
    record["review"]["state"] = state
    assert "editorial" not in editorial.apply_view(article, index(record))


@pytest.mark.parametrize("field,value", [("kind", None), ("reviewed_at", "2026-10-14"),
                                       ("reviewer", "private@example.com"), ("input_fingerprint", "guess")])
def test_review_metadata_is_explicit(article, record, field, value):
    record["review"][field] = value
    assert editorial.validate_annotations(index(record), [article])


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,unsafe", "//example.com/a",
                                 "https://user:password@example.com/", "https://example.com/ bad", "https://[",
                                 "\x01https://example.com/"])
def test_unsafe_evidence_url_blocks(article, record, url):
    record["evidence"][0]["url"] = url
    with pytest.raises(editorial.EditorialError):
        editorial.apply_view(article, index(record))


def test_broken_reference_and_withdrawn_document_block(article, record):
    record["claims"][0]["evidence_ids"] = ["missing"]
    assert any("evidence_ids" in e for e in editorial.validate_annotations(index(record), [article]))
    record["claims"][0]["evidence_ids"] = ["e1"]
    record["evidence"][0]["status"] = "withdrawn"
    assert any("withdrawn" in e for e in editorial.validate_annotations(index(record), [article]))


@pytest.mark.parametrize("field,value", [("review", []), ("claims", "bad"), ("evidence", [None]),
                                       ("uncertainties", [{}]), ("public_paths", ["../../unsafe"])])
def test_malformed_fields_fail_with_messages(article, record, field, value):
    record[field] = value
    with pytest.raises(editorial.EditorialError):
        editorial.apply_view(article, index(record))


def test_duplicate_claim_and_evidence_ids_rejected(article, record):
    record["claims"].append(copy.deepcopy(record["claims"][0]))
    record["evidence"].append(copy.deepcopy(record["evidence"][0]))
    errors = editorial.validate_annotations(index(record), [article])
    assert any("claims.id" in e for e in errors) and any("evidence.id" in e for e in errors)


def test_future_slice_or_private_fields_rejected(article, record):
    record["presentation"] = {"title": "Unapproved correction"}
    record["review"]["private_message"] = "Hidden correspondence"
    assert len(editorial.validate_annotations(index(record), [article])) >= 2


def test_documentary_and_human_labels_are_limited_to_context(article, record):
    html = context_html(article, record)
    assert "asistență AI" in html and "nu reprezintă o revizie umană" in html
    assert "internal-pilot-id" not in html and "Revizia privește numai" in html
    record["review"]["kind"] = "human"
    assert "Acest bloc de context a fost revizuit de un editor uman" in context_html(article, record)


def test_conflicting_reports_and_forecast_remain_attributed(article, record):
    record["claims"] = [
        {"id": "source-a", "text": "Sursa A spune 10.", "status": "reported", "evidence_ids": ["e1"]},
        {"id": "source-b", "text": "Sursa B spune 12.", "status": "reported", "evidence_ids": ["e1"]},
        {"id": "forecast", "text": "Este estimată încheierea mâine.", "status": "forecast", "evidence_ids": ["e1"]},
    ]
    html = context_html(article, record)
    assert "Sursa A spune 10." in html and "Sursa B spune 12." in html and "Prognoză" in html
    assert "11" not in html


def test_text_is_escaped_and_claim_anchor_reaches_examined_url(article, record):
    record["claims"][0]["text"] = '<script>alert("unsafe")</script>'
    html = context_html(article, record)
    elements = Elements(html).elements
    assert not any(tag == "script" for tag, attrs in elements)
    assert any(tag == "a" and attrs.get("href") == "#editorial-evidence-e1" for tag, attrs in elements)
    assert any(attrs.get("id") == "editorial-evidence-e1" for tag, attrs in elements)
    assert any(tag == "a" and attrs.get("href") == article["original_link"] for tag, attrs in elements)
    assert all("open" not in attrs for tag, attrs in elements if tag == "details")


@pytest.mark.parametrize("url,expected", [("https://example.com/a?x=1&y=2#part", "https://example.com/a?x=1&y=2#part"),
                                         ("http://example.com/a", "http://example.com/a"),
                                         ("HTTPS://example.com/a", "https://example.com/a")])
def test_examined_http_destination_is_preserved(article, record, url, expected):
    record["evidence"][0]["url"] = url
    elements = Elements(context_html(article, record)).elements
    assert any(tag == "a" and attrs.get("href") == expected for tag, attrs in elements)


def test_model_c_uses_persisted_identity_and_b_uses_public_path(article):
    assert editorial.annotation_key(article) == "article:/local/anunt-pilot/"
    article.update(model="C", story_id="story-preserved")
    assert editorial.annotation_key(article) == "story-preserved"


def test_invalid_catalog_preserves_previous_output(monkeypatch, tmp_path, article, record):
    catalog = tmp_path / "content/editorial/annotations.json"
    catalog.parent.mkdir(parents=True)
    record["claims"][0]["evidence_ids"] = ["missing"]
    catalog.write_text(json.dumps({"schema_version": 1, "records": [record]}), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "previous.html"
    sentinel.write_text("Previous good output", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", str(tmp_path))
    monkeypatch.setattr(render, "OUT_DIR", str(output))
    monkeypatch.setattr(render, "_quality_gate", lambda a: True)
    with pytest.raises(editorial.EditorialError, match="evidence_ids"):
        render.build([article])
    assert sentinel.read_text(encoding="utf-8") == "Previous good output"


@pytest.mark.parametrize("data", [{"schema_version": True, "records": []}, {"schema_version": 1, "records": "bad"},
                                 {"schema_version": 1, "records": [None]}])
def test_bad_catalog_shape_blocks(tmp_path, data):
    path = tmp_path / "annotations.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(editorial.EditorialError):
        editorial.load_annotations(path)


def test_orphan_annotation_reports_absence_without_republishing(record):
    assert editorial.validate_annotations(index(record), []) == []
    report = editorial.catalog_report(index(record), [])
    assert report["coverage"] == {"numerator": 0, "denominator": 0} and report["absent"] == 1


def test_committed_pilot_is_valid_without_reexamining_the_source():
    from tools.validate_editorial import load_validated
    index, articles = load_validated(Path(config.ROOT) / "data/articles.json",
                                     Path(config.ROOT) / "content/editorial/annotations.json")
    assert isinstance(index, dict)
    # A fresh match is checked by the release validation, not a timeless test on mutable news.
    assert not editorial.validate_annotations(index, articles)


def test_report_stdout_is_machine_readable_even_when_pipeline_warns():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "tools/editorial_report.py")],
                            capture_output=True, text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONUTF8": "1"}, timeout=30, check=True)
    report = json.loads(result.stdout)
    assert report["coverage"]["denominator"] == report["publishable_articles"]
    assert report["coverage"]["numerator"] == report["fresh"]
