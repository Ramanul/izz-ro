"""Dossier persistence, plain-text schemas, target freshness and explained relationships."""
import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape

from generator import dossiers, editorial, publication, render

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
    env.filters["cat_label"] = lambda category: category
    env.filters["href_extern"] = render._href_extern
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
            "public_paths": [editorial.public_path(article)],
            "review": {"state": "approved", "kind": "documentary", "reviewer": "documentary test",
                       "reviewed_at": "2026-10-17T09:00:00Z",
                       "input_fingerprint": editorial.source_fingerprint(article)},
            "evidence": [{"id": "notice", "url": article["original_link"], "locator": "Paragraful 1",
                          "role": "Emitent", "verified_at": "2026-10-17T09:00:00Z"}],
            "claims": [{"id": "announcement", "text": "Instituția a publicat anunțul.",
                        "status": "documented", "evidence_ids": ["notice"]}],
            "relations": relations}


def correction(article, state="corrected", presentation=None):
    row = {"key": editorial.annotation_key(article), "public_paths": [editorial.public_path(article)],
           "state": state, "notice": "Datele prezentate anterior au fost revizuite.",
           "evidence_url": "https://institution.example/correction/",
           "review": {"state": "approved", "kind": "documentary", "reviewer": "test-only",
                      "reviewed_at": "2026-10-17T18:00:00Z",
                      "input_fingerprint": editorial.source_fingerprint(article)},
           "presentation": (presentation or {"title": "Instituția publică informațiile corectate despre calendar"})
           if state == "corrected" else {}}
    return {row["key"]: row}


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
    active = publication.apply([article, target], correction(target, "withdrawn"))
    links = dossiers.prepare_dossiers(catalog, active, {record["key"]: record}, NOW)[1]
    assert len(links[record["key"]]) == 1  # only the separate dossier context link
    article["title"] = "Sursa a fost schimbată material."
    assert dossiers.prepare_dossiers(catalog, [article], {record["key"]: record}, NOW)[1] == {}


def test_corrected_article_link_requires_current_presentation_review(catalog, article):
    active = publication.apply([article], correction(article))
    assert dossiers.prepare_dossiers(catalog, active, now=NOW)[1] == {}
    catalog["public-service"]["article_links"][0]["input_fingerprint"] = editorial.source_fingerprint(active[0])
    refresh(catalog)
    assert dossiers.prepare_dossiers(catalog, active, now=NOW)[1]


@pytest.mark.parametrize("presentation", [
    {"title": "Instituția publică informațiile corectate despre calendar"}, {"county": "TIMIS"},
])
def test_material_correction_of_relation_target_requires_new_target_review(article, presentation):
    target = {**article, "slug": "target", "title": "Ținta originală"}
    approved_target = editorial.source_fingerprint(target)
    record = annotation(article, [relation(editorial.annotation_key(target), approved_target)])
    active = publication.apply([article, target], correction(target, presentation=presentation))
    target = active[1]
    pages, links, _, report = dossiers.prepare_dossiers({}, [article, target], {record["key"]: record}, NOW)
    assert pages == [] and links == {}
    assert report["suppressed"][0]["reason"] == "article_target_absent_or_changed"
    record["relations"][0]["target_fingerprint"] = editorial.source_fingerprint(target)
    assert dossiers.prepare_dossiers({}, [article, target], {record["key"]: record}, NOW)[1]


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


@pytest.mark.parametrize("relations", [None, "", {}, False])
def test_relations_require_array_even_when_empty(article, relations):
    record = annotation(article, relations)
    with pytest.raises(editorial.EditorialError, match="array required"):
        dossiers.prepare_dossiers({}, [article], {record["key"]: record}, NOW)


@pytest.mark.parametrize("kind", ["catalog", "relation"])
def test_invalid_dossier_data_preserves_previous_build(tmp_path, monkeypatch, catalog, article, kind):
    out = tmp_path / "output"
    out.mkdir()
    sentinel = out / "previous.html"
    sentinel.write_text("previous release", encoding="utf-8")
    records = {}
    if kind == "catalog":
        catalog["public-service"]["documents"][0]["url"] = "javascript:alert(1)"
    else:
        edge = relation(editorial.annotation_key(article), "0" * 64)
        edge["evidence_ids"] = ["missing"]
        record = annotation(article, [edge])
        records[record["key"]] = record
    monkeypatch.setattr(render, "OUT_DIR", str(out))
    monkeypatch.setattr(dossiers, "load_dossiers", lambda: catalog)
    monkeypatch.setattr(editorial, "load_annotations", lambda: records)
    monkeypatch.setattr(publication, "load", lambda: {})
    with pytest.raises(editorial.EditorialError):
        render.build([article])
    assert sentinel.read_text(encoding="utf-8") == "previous release"


@pytest.mark.parametrize("state", ["approved", "withdrawn", "needs_review"])
def test_build_dossier_search_and_sitemap_follow_review_state(tmp_path, monkeypatch, catalog, article, state):
    out = tmp_path / "output"
    record = catalog["public-service"]
    if state == "withdrawn":
        record["review"]["state"] = "withdrawn"
        record["withdrawal_note"] = "Dosarul a fost retras: documentul nu mai susține sinteza."
    elif state == "needs_review":
        record["summary"] = "Sinteză schimbată, încă neexaminată."
    monkeypatch.setattr(render, "OUT_DIR", str(out))
    monkeypatch.setattr(dossiers, "load_dossiers", lambda: catalog)
    monkeypatch.setattr(editorial, "load_annotations", lambda: {})
    monkeypatch.setattr(publication, "load", lambda: {})
    # No active article is needed: the dossier/document route survives article expiration.
    render.build([])
    path = "/dosar/public-service-history/"
    page = (out / "dosar/public-service-history/index.html").read_text(encoding="utf-8")
    report = json.loads((out / "editorial-report.json").read_text(encoding="utf-8"))["dossiers"]
    search = json.loads((out / "search-index.json").read_text(encoding="utf-8"))["a"]
    assert report["emitted"] == 1
    assert (path in (out / "sitemap.xml").read_text(encoding="utf-8")) == (state == "approved")
    assert (path in (out / "sitemap-priority.xml").read_text(encoding="utf-8")) == (state == "approved")
    assert any(row[0] == path for row in search) == (state == "approved")
    if state == "approved":
        assert 'data-pagefind-body' in page and report["indexable"] == 1
        assert article["original_link"] in page
        assert editorial.public_path(article) not in page
        assert "nu reprezintă o revizie umană" in page
    else:
        assert 'data-pagefind-ignore' in page and 'noindex,follow' in page
        assert report["indexable"] == 0
        assert record["summary"] not in page
    metadata = json.loads((out / "build.json").read_text(encoding="utf-8"))
    assert metadata["article_count"] == 0


@pytest.mark.parametrize("path", ["//foreign.example/page/", "javascript:alert(1)"])
def test_relation_template_keeps_internal_links_on_site(path):
    relation_view = {"path": path, "title": "Unsafe supplied path", "label": "Context",
                     "explanation": "Synthetic direct template probe", "identity_basis": "Test only",
                     "evidence": [{"anchor": path}]}
    rendered = html("_editorial_relations.html", editorial_relations=[relation_view])
    assert f'href="/{path.lstrip(chr(47))}"' in rendered
    assert 'href="javascript:' not in rendered and 'href="//foreign.example' not in rendered


@pytest.mark.parametrize("unsafe", [{"category": "foreign"}, {"slug": "//foreign.example"},
                                    {"slug": r"/\foreign.example"}, {"slug": "/\t/foreign.example"}])
def test_article_relation_target_requires_safe_published_path(article, unsafe):
    target = {**article, "model": "C", "story_id": "unsafe-target", **unsafe}
    edge = relation("unsafe-target", editorial.source_fingerprint(target))
    record = annotation(article, [edge])
    with pytest.raises(editorial.EditorialError, match="unsafe category/slug"):
        dossiers.prepare_dossiers({}, [article, target], {record["key"]: record}, NOW)


@pytest.mark.parametrize("count", [1, 2])
def test_dossier_source_label_matches_examined_document_count(catalog, count):
    record = catalog["public-service"]
    if count == 2:
        record["documents"].append({**record["documents"][0], "id": "second-notice"})
        refresh(catalog)
    page = dossiers.prepare_dossiers(catalog, [], now=NOW)[0][0]
    rendered = html("dossier.html", dossier=page)
    assert f"<h2>{'Sursă' if count == 1 else 'Surse'}</h2>" in rendered
    assert rendered.count('class="sources-box"') == 1


@pytest.mark.parametrize("field", ["withdrawal_note", "document_note", "event_date_basis"])
@pytest.mark.parametrize("invalid", ["", {}, [], None, "<em>unsafe</em>", "\x01"])
def test_optional_catalog_prose_is_plain_text_when_present(catalog, field, invalid):
    record = catalog["public-service"]
    if field == "withdrawal_note":
        record[field] = invalid
    elif field == "document_note":
        record["documents"][0]["note"] = invalid
    else:
        record["events"][0]["event_at"] = None
        record["events"][0][field] = invalid
    with pytest.raises(editorial.EditorialError, match="plain text"):
        dossiers.validate_dossiers(catalog)


@pytest.mark.parametrize("owner", ["article", "dossier"])
@pytest.mark.parametrize("overlapping", [False, True])
def test_effect_relation_displays_every_distinct_proof_and_hides_inactive_effect(catalog, article, owner, overlapping):
    target = {**article, "slug": "affected-service"}
    edge = relation(editorial.annotation_key(target), editorial.source_fingerprint(target), "affects")
    edge.update(effect_status="observed", effect_evidence_ids=["notice", "effect"] if overlapping else ["effect"])
    effect = {**catalog["public-service"]["documents"][0], "id": "effect",
              "title": "Constatarea efectului", "url": "https://institution.example/effect/"}
    annotations = {}
    if owner == "dossier":
        catalog["public-service"]["documents"].append(effect)
        catalog["public-service"]["relations"] = [edge]
        refresh(catalog)
    else:
        record = annotation(article, [edge])
        effect = {**record["evidence"][0], "id": "effect", "url": "https://institution.example/effect/"}
        record["evidence"].append(effect)
        annotations = {record["key"]: record}
        catalog = {}

    def prepared_relations():
        pages, links, _, report = dossiers.prepare_dossiers(catalog, [article, target], annotations, NOW)
        return (pages[0]["relations"] if owner == "dossier" else links.get(record["key"], [])), report

    relations, _ = prepared_relations()
    assert [proof["id"] for proof in relations[0]["evidence"]] == ["notice", "effect"]
    rendered = html("_editorial_relations.html", editorial_relations=relations)
    assert "Efect observat în probele citate." in rendered
    for proof in relations[0]["evidence"]:
        assert f'href="{proof["anchor"] or proof["scheme"] + "://" + proof["destination"]}"' in rendered
    assert rendered.count("Proba legăturii</a>") == 2

    effect["status"] = "withdrawn"
    if owner == "dossier":
        effect["note"] = "Constatarea efectului a fost retrasă."
    refresh(catalog)
    relations, report = prepared_relations()
    assert relations == []
    assert any(item["reason"] == "relation_review_or_evidence_inactive" for item in report["suppressed"])


@pytest.mark.parametrize("invalid", ["", None, {}, [], "f" * 63, "g" * 64, 1, int("1" * 64)])
def test_optional_relation_review_fingerprint_is_valid_sha256_when_present(catalog, article, invalid):
    edge = relation(editorial.annotation_key(article), editorial.source_fingerprint(article))
    edge["review"]["input_fingerprint"] = invalid
    catalog["public-service"]["relations"] = [edge]
    with pytest.raises(editorial.EditorialError, match="input_fingerprint"):
        dossiers.validate_dossiers(catalog)


def test_optional_valid_relation_review_fingerprint_is_accepted(catalog, article):
    edge = relation(editorial.annotation_key(article), editorial.source_fingerprint(article))
    edge["review"]["input_fingerprint"] = "a" * 64
    catalog["public-service"]["relations"] = [edge]
    assert dossiers.validate_dossiers(catalog) is catalog


def test_history_version_proof_links_are_visibly_separated(catalog):
    record = catalog["public-service"]
    record["documents"].append({**record["documents"][0], "id": "second-notice"})
    record["history"] = [{"version": 1, "at": "2026-10-17T09:00:00Z", "summary": record["summary"],
                          "reason": "Prima versiune documentată.", "evidence_ids": ["notice", "second-notice"]}]
    refresh(catalog)
    page = dossiers.prepare_dossiers(catalog, [], now=NOW)[0][0]
    rendered = html("dossier.html", dossier=page)
    assert 'Documentul versiunii</a> · <a href="#document-second-notice"' in rendered


def test_single_history_version_is_initial_baseline_not_a_correction(catalog):
    record = catalog["public-service"]
    record["history"] = [{"version": 1, "at": "2026-10-17T09:00:00Z", "summary": record["summary"],
                          "reason": "Prima versiune documentată.", "evidence_ids": ["notice"]}]
    refresh(catalog)
    page = dossiers.prepare_dossiers(catalog, [], now=NOW)[0][0]
    rendered = html("dossier.html", dossier=page)
    assert "Istoricul sintezei și al corecțiilor" in rendered
    assert "Prima versiune documentată." in rendered
    assert "Versiunea 1" in rendered
    assert "Ce s-a schimbat" not in rendered
    assert record["summary"] in rendered


def test_withdrawal_does_not_repeat_original_question_or_coverage(catalog):
    record = catalog["public-service"]
    record.update(question="Premisă greșită ce trebuie retrasă.", withdrawal_note="Încadrarea documentară a fost retrasă.")
    record["period"]["scope"] = "Domeniu documentar atribuit greșit."
    record["review"]["state"] = "withdrawn"
    page = dossiers.prepare_dossiers(catalog, [], now=NOW)[0][0]
    rendered = html("dossier.html", dossier=page)
    assert "Dosar retras" in rendered and record["withdrawal_note"] in rendered
    assert record["title"] in rendered and "Examinat la" in rendered
    assert record["question"] not in rendered
    assert record["period"]["scope"] not in rendered
    assert "Perioada documentată:" not in rendered


@pytest.mark.parametrize("path", ["//foreign.example/path/", "javascript:alert(1)", "/dosar/valid/"])
@pytest.mark.parametrize("template", ["dossier.html", "subject.html"])
def test_dossier_navigation_templates_keep_internal_links_on_site(catalog, path, template):
    link = {"path": path, "title": "Synthetic navigation probe", "identity_basis": "Test only"}
    if template == "dossier.html":
        page = dossiers.prepare_dossiers(catalog, [], now=NOW)[0][0]
        page["article_links"] = [link]
        rendered = html(template, dossier=page)
    else:
        rendered = html(template, name="Test", slug="test", articles=[], subject_dossiers=[link])
    assert f'href="/{path.lstrip(chr(47))}"' in rendered
    assert 'href="javascript:' not in rendered and 'href="//foreign.example' not in rendered


@pytest.mark.parametrize("owner", ["dossier", "relation"])
def test_dossier_reviewers_are_public_identifiers_not_email_addresses(catalog, article, owner):
    record = catalog["public-service"]
    if owner == "dossier":
        record["review"]["reviewer"] = "editor@example.com"
    else:
        edge = relation(editorial.annotation_key(article), editorial.source_fingerprint(article))
        edge["review"]["reviewer"] = "editor@example.com"
        record["relations"] = [edge]
    with pytest.raises(editorial.EditorialError, match="reviewer"):
        dossiers.validate_dossiers(catalog)


def test_dossier_search_scope_excludes_boilerplate_and_historical_summaries(catalog):
    record = catalog["public-service"]
    record["history"] = [
        {"version": 1, "at": "2026-10-17T09:00:00Z", "summary": "Obsolete historical wording.",
         "reason": "Initial version.", "evidence_ids": ["notice"]},
        {"version": 2, "at": "2026-10-17T13:00:00Z", "summary": record["summary"],
         "reason": "Current version.", "evidence_ids": ["notice"]},
    ]
    refresh(catalog)
    page = dossiers.prepare_dossiers(catalog, [], now=NOW)[0][0]
    rendered = html("dossier.html", dossier=page)
    bodies = re.findall(r'<([a-z0-9]+)\b[^>]*\bdata-pagefind-body\b[^>]*>(.*?)</\1>', rendered, re.S)
    indexed = " ".join(re.sub(r"<[^>]+>", " ", body) for _, body in bodies)
    for content in [record["title"], record["question"], record["summary"], record["events"][0]["text"]]:
        assert content in indexed
    for noise in ["Documentat cu asistență AI", "Un termen anunțat nu dovedește", "Documentul sintezei",
                  "Obsolete historical wording.", record["documents"][0]["locator"]]:
        assert noise not in indexed


def test_indexable_dossier_exposes_search_category_and_date_sort_metadata(catalog):
    page = dossiers.prepare_dossiers(catalog, [], now=NOW)[0][0]
    rendered = html("dossier.html", dossier=page)
    assert 'data-pagefind-filter="categorie: dosar"' in rendered
    assert f'data-pagefind-sort="data: {page["reviewed_at"][:19]}"' in rendered
