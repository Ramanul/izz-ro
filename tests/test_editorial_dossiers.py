"""Dossier persistence, plain-text schemas, target freshness and explained relationships."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape

from generator import dossiers, editorial

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)


@pytest.fixture
def article():
    return {"model": "B", "category": "local", "slug": "anunt-pilot",
            "title": "Instituția anunță un calendar pentru serviciul public",
            "teaser": "Calendarul este o informație anunțată, nu un rezultat verificat.",
            "original_link": "https://institution.example/notice/", "source_name": "Instituția",
            "published": "2026-10-14T08:00:00Z", "processed_by": "official"}


@pytest.fixture
def catalog(article):
    record = {
        "id": "public-service", "slug": "public-service-history", "title": "Calendarul serviciului public",
        "question": "Ce a anunțat instituția?", "summary": "Instituția anunță un calendar; rezultatul nu a fost testat.",
        "summary_evidence_ids": ["notice"],
        "review": {"state": "approved", "kind": "documentary", "reviewer": "documentary test",
                   "reviewed_at": "2026-10-17T09:00:00Z"},
        "period": {"start": "2026-10-13", "end": "2026-10-18", "scope": "Un singur anunț oficial."},
        "documents": [{"id": "notice", "title": "Anunțul instituției", "url": article["original_link"],
                       "locator": "Paragraful 1", "verified_at": "2026-10-17T09:00:00Z",
                       "published_at": "2026-10-13", "status": "active"}],
        "events": [{"id": "return", "text": "Revenirea anunțată, fără confirmare.",
                    "event_at": "2026-10-18T18:00:00+03:00", "event_date_basis": "Ora locală declarată.",
                    "published_at": "2026-10-13", "status": "forecast", "evidence_ids": ["notice"]}],
        "uncertainties": [{"question": "Serviciul a revenit?", "needed": "Verificare ulterioară."}],
        "history": [], "relations": [],
        "article_links": [{"key": editorial.annotation_key(article),
                           "input_fingerprint": editorial.source_fingerprint(article),
                           "explanation": "Documentul oficial este același.",
                           "identity_basis": "Instituția și identificatorul anunțului coincid.",
                           "evidence_ids": ["notice"]}],
        "subjects": [{"slug": "institution", "identity_basis": "Emitentul documentului identificat prin domeniul oficial."}],
    }
    record["review"]["input_fingerprint"] = dossiers.dossier_fingerprint(record)
    return {record["id"]: record}


def refresh(catalog):
    for record in catalog.values():
        record["review"]["input_fingerprint"] = dossiers.dossier_fingerprint(record)
    return catalog


def html(template, **ctx):
    env = Environment(loader=ChoiceLoader([
        DictLoader({"base.html": "<!doctype html><html lang='ro'><title>{% block title %}{% endblock %}</title><main>{% block content %}{% endblock %}</main></html>"}),
        FileSystemLoader(ROOT / "templates"),
    ]), autoescape=select_autoescape(["html"]))
    return env.get_template(template).render(base="", site={"name": "izz.ro"}, **ctx)


def relation(target, fingerprint, kind="context"):
    return {"type": kind, "target": target, "target_fingerprint": fingerprint,
            "explanation": "Legătura se bazează pe documentul citat.",
            "identity_basis": "Identificatori documentari distincți de numele persoanei.",
            "evidence_ids": ["notice"],
            "review": {"state": "approved", "kind": "documentary", "reviewer": "documentary test",
                       "reviewed_at": "2026-10-17T09:00:00Z"}}


def annotation(article, relations):
    return {"key": editorial.annotation_key(article),
            "review": {"state": "approved", "kind": "documentary", "reviewer": "documentary test",
                       "reviewed_at": "2026-10-17T09:00:00Z",
                       "input_fingerprint": editorial.source_fingerprint(article)},
            "evidence": [{"id": "notice", "url": article["original_link"], "locator": "Paragraful 1",
                          "role": "Emitent", "verified_at": "2026-10-17T09:00:00Z"}],
            "relations": relations}


def test_real_pilot_is_current_catalog_and_missing_catalog_is_empty(tmp_path):
    assert dossiers.load_dossiers(tmp_path / "missing.json") == {}
    catalog = dossiers.load_dossiers()
    pages, _, _, report = dossiers.prepare_dossiers(catalog, [], now=NOW)
    assert len(pages) == 1 and report["indexable"] == 1
    assert catalog["sector1-plati-octombrie-2026"]["review"]["kind"] == "documentary"


def test_preparation_does_not_mutate_and_retains_bounded_history_after_expiration(catalog, article):
    original, original_article = copy.deepcopy(catalog), copy.deepcopy(article)
    pages, links, subjects, report = dossiers.prepare_dossiers(catalog, [article], now=NOW)
    assert catalog == original and article == original_article
    assert report["indexable"] == 1
    assert links[editorial.annotation_key(article)][0]["path"] == pages[0]["path"]
    assert subjects["institution"][0]["title"] == pages[0]["title"]
    expired, links, _, report = dossiers.prepare_dossiers(catalog, [], now=NOW)
    assert expired[0]["summary"] == original["public-service"]["summary"]
    assert expired[0]["documents"] and expired[0]["article_links"] == [] and links == {}
    rendered = html("dossier.html", dossier=expired[0])
    assert "/local/anunt-pilot/" not in rendered
    assert "https://institution.example/notice/" in rendered
    assert "nu reprezintă o revizie umană" in rendered
    assert "nu pretinde o istorie completă" in rendered


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(extra=True),
    lambda r: r.update(slug="../../bad"),
    lambda r: r.update(summary="<script>alert(1)</script>"),
    lambda r: r.update(summary_evidence_ids=["missing"]),
    lambda r: r.update(documents=[]),
    lambda r: r["documents"][0].update(locator=""),
    lambda r: r["events"][0].update(event_at="2026-02-31"),
    lambda r: r["events"][0].update(event_date_basis=""),
    lambda r: r["events"][0].update(status="actual"),
    lambda r: r["review"].update(kind="automatically-human-approved"),
    lambda r: r["review"].update(reviewed_at="2026-10-17"),
    lambda r: r.update(period={"start": "2026-10-19", "end": "2026-10-13", "scope": "Interval"}),
    lambda r: r["subjects"][0].update(slug="/someone"),
    lambda r: r["article_links"][0].update(input_fingerprint=""),
])
def test_schema_rejects_incomplete_or_unsafe_content(catalog, mutation):
    mutation(catalog["public-service"])
    with pytest.raises(editorial.EditorialError):
        dossiers.prepare_dossiers(catalog, [], now=NOW)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "//evil.example", "HTTPS://evil.example/",
                                  "https://user:pass@evil.example/", "https://evil.example/a\n",
                                  "https://evil.example\\@good.example/", "https://[broken/"])
def test_unsafe_source_urls_are_blocked_at_catalog_boundary(catalog, url):
    catalog["public-service"]["documents"][0]["url"] = url
    with pytest.raises(editorial.EditorialError):
        dossiers.prepare_dossiers(catalog, [], now=NOW)


def test_event_date_is_not_invented_from_publication(catalog):
    catalog["public-service"]["events"][0]["event_at"] = None
    refresh(catalog)
    pages, _, _, _ = dossiers.prepare_dossiers(catalog, [], now=NOW)
    rendered = html("dossier.html", dossier=pages[0])
    assert "Data faptului nu este stabilită." in rendered
    assert "Publicarea relatării" in rendered
    assert pages[0]["events"][0]["event_at"] is None


@pytest.mark.parametrize("status", ["withdrawn", "unavailable"])
def test_inactive_document_requires_note_and_stops_current_summary(catalog, status):
    doc = catalog["public-service"]["documents"][0]
    doc.update(status=status)
    with pytest.raises(editorial.EditorialError):
        dossiers.prepare_dossiers(catalog, [], now=NOW)
    doc["note"] = "Retragere sau indisponibilitate constatată în documentare."
    refresh(catalog)
    pages, links, subjects, report = dossiers.prepare_dossiers(catalog, [], now=NOW)
    assert report["indexable"] == 0 and not links and not subjects
    assert pages[0]["state"] == "needs_review"
    assert pages[0]["events"] == []
    assert "Document retras" in html("dossier.html", dossier=pages[0]) if status == "withdrawn" else "Document indisponibil" in html("dossier.html", dossier=pages[0])


def test_changed_dossier_needs_review_and_withdrawal_keeps_explanatory_route(catalog):
    catalog["public-service"]["summary"] = "Sinteza s-a schimbat fără revizie."
    pages, _, _, report = dossiers.prepare_dossiers(catalog, [], now=NOW)
    assert pages[0]["state"] == "needs_review" and report["indexable"] == 0
    record = catalog["public-service"]
    record["review"]["state"] = "withdrawn"
    record["withdrawal_note"] = "Dosarul a fost retras pentru o nouă examinare."
    pages, _, _, report = dossiers.prepare_dossiers(catalog, [], now=NOW)
    assert pages[0]["path"] == "/dosar/public-service-history/"
    assert report["withdrawn"] == 1 and not pages[0]["indexable"]
    assert "Dosar retras" in html("dossier.html", dossier=pages[0])
    assert "institution.example" not in html("dossier.html", dossier=pages[0])


def test_draft_is_not_emitted(catalog):
    catalog["public-service"]["review"]["state"] = "draft"
    assert dossiers.prepare_dossiers(catalog, [], now=NOW)[0] == []


def test_correction_replaces_current_summary_and_retains_versions(catalog):
    record = catalog["public-service"]
    old = record["summary"]
    new = "Sinteză corectată pe baza documentului, fără confirmarea rezultatului."
    record["history"] = [
        {"version": 1, "at": "2026-10-17T09:00:00Z", "summary": old, "reason": "Prima versiune.", "evidence_ids": ["notice"]},
        {"version": 2, "at": "2026-10-17T13:00:00+03:00", "summary": new, "reason": "Clarificarea limitei.", "evidence_ids": ["notice"]},
    ]
    with pytest.raises(editorial.EditorialError, match="latest corrected summary"):
        dossiers.prepare_dossiers(catalog, [], now=NOW)
    record["summary"] = new
    refresh(catalog)
    pages = dossiers.prepare_dossiers(catalog, [], now=NOW)[0]
    assert pages[0]["summary"] == new and pages[0]["history"][0]["summary"] == old
    assert "Clarificarea limitei" in html("dossier.html", dossier=pages[0])


def test_article_and_dossier_targets_are_fingerprint_bound(catalog, article):
    target = {**article, "slug": "second-stage", "title": "Etapa a doua a calendarului"}
    record = annotation(article, [relation(editorial.annotation_key(target), editorial.source_fingerprint(target), "follow_up")])
    records = {record["key"]: record}
    links = dossiers.prepare_dossiers(catalog, [article, target], records, NOW)[1]
    assert any(x["type"] == "follow_up" for x in links[record["key"]])
    target["title"] = "Date materiale schimbate"
    links = dossiers.prepare_dossiers(catalog, [article, target], records, NOW)[1]
    assert not any(x["type"] == "follow_up" for x in links[record["key"]])
    record["relations"] = [relation("dossier:public-service", dossiers.dossier_fingerprint(catalog["public-service"]))]
    assert len(dossiers.prepare_dossiers(catalog, [article], records, NOW)[1][record["key"]]) == 2
    catalog["public-service"]["summary"] = "Materialul țintei s-a schimbat."
    refresh(catalog)
    links = dossiers.prepare_dossiers(catalog, [article], records, NOW)[1]
    assert len(links[record["key"]]) == 1


def test_source_change_and_withdrawn_target_hide_relations(catalog, article):
    target = {**article, "slug": "target"}
    record = annotation(article, [relation(editorial.annotation_key(target), editorial.source_fingerprint(target))])
    target["publication"] = {"state": "withdrawn"}
    links = dossiers.prepare_dossiers(catalog, [article, target], {record["key"]: record}, NOW)[1]
    assert len(links[record["key"]]) == 1  # only the separate dossier context link
    article["title"] = "Sursa a fost schimbată material."
    assert dossiers.prepare_dossiers(catalog, [article, target], {record["key"]: record}, NOW)[1] == {}


def test_corrected_views_use_preserved_input_fingerprint(catalog, article):
    original = editorial.source_fingerprint(article)
    article["title"] = "Titlul corectat pentru cititor"
    article["editorial_input_fingerprint"] = original
    article["publication"] = {"state": "corrected"}
    assert dossiers.prepare_dossiers(catalog, [article], now=NOW)[1]


@pytest.mark.parametrize("kind", list(dossiers.RELATION_LABELS))
def test_relation_types_explain_evidence_and_cooccurrence_is_noncausal(catalog, article, kind):
    target = {**article, "slug": "target"}
    edge = relation(editorial.annotation_key(target), editorial.source_fingerprint(target), kind)
    if kind == "affects":
        edge.update(effect_status="projected", effect_evidence_ids=["notice"])
    record = annotation(article, [edge])
    links = dossiers.prepare_dossiers({}, [article, target], {record["key"]: record}, NOW)[1][record["key"]]
    rendered = html("_editorial_relations.html", editorial_relations=links)
    assert "Proba legăturii" in rendered and "https://institution.example/notice/" in rendered
    if kind == "co_occurrence":
        assert "nu demonstrează cauzalitate" in rendered
    if kind == "affects":
        assert "rezultatul nu este confirmat" in rendered


def test_effect_relation_requires_explicit_status_and_evidence(catalog, article):
    edge = relation(editorial.annotation_key(article), editorial.source_fingerprint(article), "affects")
    record = annotation(article, [edge])
    with pytest.raises(editorial.EditorialError, match="effect status"):
        dossiers.prepare_dossiers({}, [article], {record["key"]: record}, NOW)
    edge.update(effect_status="observed", effect_evidence_ids=["absent"])
    with pytest.raises(editorial.EditorialError, match="evidence IDs"):
        dossiers.prepare_dossiers({}, [article], {record["key"]: record}, NOW)


def test_same_name_never_creates_relation_or_identity_merge(catalog, article):
    article["entities"] = ["Alex Example"]
    other = {**article, "slug": "other-person", "title": "O persoană diferită cu același nume"}
    assert dossiers.prepare_dossiers({}, [article, other], now=NOW)[1] == {}


def test_more_than_three_relations_are_available_by_keyboard_details(article):
    edge = relation(editorial.annotation_key(article), editorial.source_fingerprint(article))
    record = annotation(article, [copy.deepcopy(edge) for _ in range(4)])
    links = dossiers.prepare_dossiers({}, [article], {record["key"]: record}, NOW)[1][record["key"]]
    rendered = html("_editorial_relations.html", editorial_relations=links)
    assert "<details>" in rendered and "Alte legături documentate (1)" in rendered


def test_duplicate_catalog_ids_and_noninteger_version_are_rejected(tmp_path, catalog):
    path = tmp_path / "dossiers.json"
    record = catalog["public-service"]
    path.write_text(json.dumps({"schema_version": 1, "records": [record, record]}), encoding="utf-8")
    with pytest.raises(editorial.EditorialError, match="duplicate"):
        dossiers.load_dossiers(path)
    path.write_text(json.dumps({"schema_version": True, "records": []}), encoding="utf-8")
    with pytest.raises(editorial.EditorialError, match="schema_version"):
        dossiers.load_dossiers(path)
