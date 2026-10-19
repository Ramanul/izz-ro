"""Persistent documentary dossiers and evidence-backed, fingerprint-bound relations."""
import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from . import config
from .editorial import EditorialError, annotation_key, public_path, source_fingerprint

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_ARTICLE_KEY = re.compile(r"^(?:article:/[a-z0-9-]+/[a-z0-9-]+/|[A-Za-z0-9_-]+)$")
RELATION_LABELS = {
    "same_project": "Același proiect", "follow_up": "Continuarea unei decizii",
    "cites_document": "Documentul invocat", "affects": "Efect documentat sau anunțat",
    "context": "Context documentar", "co_occurrence": "Coapariție în relatări",
}
_DOSSIER_FIELDS = {
    "id", "slug", "title", "question", "summary", "summary_evidence_ids", "review",
    "period", "documents", "events", "uncertainties", "history", "relations",
    "article_links", "subjects", "withdrawal_note",
}
_REVIEW_FIELDS = {"state", "kind", "reviewer", "reviewed_at", "input_fingerprint"}
_RELATION_FIELDS = {
    "type", "target", "target_fingerprint", "explanation", "evidence_ids", "review",
    "identity_basis", "effect_status", "effect_evidence_ids",
}


def _fail(field, reason):
    raise EditorialError(f"{field}: {reason}")


def _object(item, allowed, field):
    if not isinstance(item, dict) or set(item) - allowed:
        _fail(field, "object with known fields required")


def _text(value):
    # No rich HTML: all catalog prose is plain, autoescaped text.
    return (isinstance(value, str) and bool(value.strip())
            and not any(ord(c) < 32 and c not in "\n\t" for c in value)
            and not re.search(r"<\s*/?\s*[a-zA-Z!]", value))


def _texts(item, fields, field):
    if not all(_text(item.get(k)) for k in fields):
        _fail(field, "non-empty plain text required: " + ", ".join(fields))


def _instant(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def _day(value):
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _url_parts(value):
    if (not isinstance(value, str) or not value.startswith(("https://", "http://"))
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
            or "\\" in value):
        return None
    try:
        parsed = urlsplit(value)
        if (not parsed.hostname or parsed.username is not None or parsed.password is not None
                or parsed.scheme not in {"https", "http"}):
            return None
        return {"scheme": parsed.scheme, "destination": value.split("://", 1)[1]}
    except ValueError:
        return None


def _list(value, field):
    if not isinstance(value, list):
        _fail(field, "array required")
    return value


def _review(item, field, fingerprint=False):
    _object(item, _REVIEW_FIELDS, field)
    if item.get("state") not in {"draft", "approved", "withdrawn"}:
        _fail(field, "known review state required")
    if item.get("kind") not in {"documentary", "human"}:
        _fail(field, "documentary or human review kind required")
    _texts(item, ("reviewer",), field)
    if "@" in item["reviewer"]:
        _fail(field, "reviewer must be a public identifier, not an email address")
    if not _instant(item.get("reviewed_at")):
        _fail(field, "zoned reviewed_at required")
    if fingerprint or "input_fingerprint" in item:
        value = item.get("input_fingerprint")
        if not isinstance(value, str) or not _HASH.fullmatch(value):
            _fail(field, "SHA-256 input_fingerprint required")


def _refs(value, evidence, field):
    refs = _list(value, field)
    if (not refs or any(not isinstance(ref, str) or ref not in evidence for ref in refs)
            or len(refs) != len(set(refs))):
        _fail(field, "non-empty unique existing evidence IDs required")
    return refs


def dossier_fingerprint(record):
    """Bind review to dossier content and approved navigation; relations have own review."""
    fields = ("id", "slug", "title", "question", "summary", "summary_evidence_ids",
              "period", "documents", "events", "uncertainties", "history", "withdrawal_note",
              "article_links", "subjects")
    material = {field: record.get(field) for field in fields}
    raw = json.dumps(material, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_dossiers(path=None):
    path = Path(path) if path is not None else Path(config.ROOT) / "content/editorial/dossiers.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EditorialError(f"{path}: invalid UTF-8 JSON") from exc
    if (not isinstance(data, dict) or set(data) != {"schema_version", "records"}
            or type(data.get("schema_version")) is not int or data["schema_version"] != 1):
        _fail("dossiers", "schema_version=1 and records required")
    catalog = {}
    for record in _list(data["records"], "dossiers.records"):
        if not isinstance(record, dict) or not _ID.fullmatch(str(record.get("id", ""))):
            _fail("dossiers.id", "safe persisted ID required")
        if record["id"] in catalog:
            _fail("dossiers.id", "duplicate ID")
        catalog[record["id"]] = record
    validate_dossiers(catalog)
    return catalog


def _validate_relation(relation, evidence, catalog, field):
    _object(relation, _RELATION_FIELDS, field)
    if relation.get("type") not in RELATION_LABELS:
        _fail(field, "known relation type required")
    _texts(relation, ("target", "explanation", "identity_basis"), field)
    _review(relation.get("review"), field + ".review")
    _refs(relation.get("evidence_ids"), evidence, field + ".evidence_ids")
    target = relation["target"]
    if target.startswith("dossier:"):
        if target[8:] not in catalog:
            _fail(field, "existing dossier target required")
    elif not _ARTICLE_KEY.fullmatch(target):
        _fail(field, "safe article key or existing dossier target required")
    if not _HASH.fullmatch(str(relation.get("target_fingerprint", ""))):
        _fail(field, "target fingerprint required")
    if relation["type"] == "affects":
        if relation.get("effect_status") not in {"observed", "projected"}:
            _fail(field, "explicit observed/projected effect status required")
        _refs(relation.get("effect_evidence_ids"), evidence, field + ".effect_evidence_ids")
    elif "effect_status" in relation or "effect_evidence_ids" in relation:
        _fail(field, "effect fields are only valid for affects")


def validate_dossiers(catalog):
    """Strict schema validation; expired article references are assessed at preparation."""
    if not isinstance(catalog, dict):
        _fail("dossiers", "catalog object required")
    slugs = set()
    for key, record in catalog.items():
        field = "dossier:" + str(key)
        _object(record, _DOSSIER_FIELDS, field)
        if record.get("id") != key or not isinstance(key, str) or not _ID.fullmatch(key):
            _fail(field, "safe persisted matching ID required")
        slug = record.get("slug")
        if not isinstance(slug, str) or not _ID.fullmatch(slug) or slug in slugs:
            _fail(field, "safe unique persisted slug required")
        slugs.add(slug)
        _texts(record, ("title", "question", "summary"), field)
        _review(record.get("review"), field + ".review", fingerprint=True)
        if "withdrawal_note" in record and not _text(record["withdrawal_note"]):
            _fail(field, "withdrawal_note must be non-empty plain text when present")
        if record["review"]["state"] == "withdrawn" and not _text(record.get("withdrawal_note")):
            _fail(field, "withdrawal_note required for withdrawn dossier")
        period = record.get("period")
        _object(period, {"start", "end", "scope"}, field + ".period")
        _texts(period, ("scope",), field + ".period")
        if not all(_day(period.get(k)) for k in ("start", "end")) or period["start"] > period["end"]:
            _fail(field, "ordered date-only coverage period required")
        documents = {}
        for doc in _list(record.get("documents"), field + ".documents"):
            _object(doc, {"id", "title", "url", "locator", "verified_at", "published_at", "status", "note"}, field + ".document")
            did = doc.get("id")
            if not isinstance(did, str) or not _ID.fullmatch(did) or did in documents:
                _fail(field, "safe unique document ID required")
            _texts(doc, ("title", "locator"), field + ".document")
            if not _url_parts(doc.get("url")) or not _instant(doc.get("verified_at")):
                _fail(field, "examined safe HTTP(S) URL and zoned date required")
            if doc.get("published_at") is not None and not (_day(doc["published_at"]) or _instant(doc["published_at"])):
                _fail(field, "separate valid document publication date required")
            if doc.get("status") not in {"active", "unavailable", "withdrawn"}:
                _fail(field, "explicit document status required")
            if "note" in doc and not _text(doc["note"]):
                _fail(field, "document note must be non-empty plain text when present")
            if doc["status"] != "active" and not _text(doc.get("note")):
                _fail(field, "unavailable/withdrawn document explanation required")
            documents[did] = doc
        _refs(record.get("summary_evidence_ids"), documents, field + ".summary_evidence_ids")
        event_ids = set()
        for event in _list(record.get("events"), field + ".events"):
            _object(event, {"id", "text", "event_at", "event_date_basis", "published_at", "status", "evidence_ids"}, field + ".event")
            eid = event.get("id")
            if not isinstance(eid, str) or not _ID.fullmatch(eid) or eid in event_ids:
                _fail(field, "safe unique event ID required")
            event_ids.add(eid)
            _texts(event, ("text",), field + ".event")
            if event.get("status") not in {"reported", "documented", "forecast"}:
                _fail(field, "explicit event status required")
            if "event_date_basis" in event and not _text(event["event_date_basis"]):
                _fail(field, "event_date_basis must be non-empty plain text when present")
            if event.get("event_at") is not None:
                if not (_day(event["event_at"]) or _instant(event["event_at"])) or not _text(event.get("event_date_basis")):
                    _fail(field, "known event date requires explicit date basis")
            if event.get("published_at") is not None and not (_day(event["published_at"]) or _instant(event["published_at"])):
                _fail(field, "valid independent publication date required")
            _refs(event.get("evidence_ids"), documents, field + ".event.evidence_ids")
        if not event_ids:
            _fail(field, "at least one documented event required")
        for unknown in _list(record.get("uncertainties", []), field + ".uncertainties"):
            _object(unknown, {"question", "needed"}, field + ".uncertainty")
            _texts(unknown, ("question", "needed"), field + ".uncertainty")
        previous_at = None
        history = _list(record.get("history", []), field + ".history")
        for version, entry in enumerate(history, start=1):
            _object(entry, {"version", "at", "summary", "reason", "evidence_ids"}, field + ".history")
            _texts(entry, ("summary", "reason"), field + ".history")
            if type(entry.get("version")) is not int or entry["version"] != version:
                _fail(field, "consecutive history versions starting at 1 required")
            if not _instant(entry.get("at")):
                _fail(field, "ordered zoned correction dates required")
            instant = datetime.fromisoformat(entry["at"].replace("Z", "+00:00"))
            if previous_at is not None and instant < previous_at:
                _fail(field, "ordered zoned correction dates required")
            previous_at = instant
            _refs(entry.get("evidence_ids"), documents, field + ".history.evidence_ids")
        if history and history[-1]["summary"] != record["summary"]:
            _fail(field, "latest corrected summary must equal current summary")
        for relation in _list(record.get("relations", []), field + ".relations"):
            _validate_relation(relation, documents, catalog, field + ".relation")
        article_keys = set()
        for link in _list(record.get("article_links", []), field + ".article_links"):
            _object(link, {"key", "input_fingerprint", "explanation", "evidence_ids", "identity_basis"}, field + ".article_link")
            _texts(link, ("key", "explanation", "identity_basis"), field + ".article_link")
            if not _ARTICLE_KEY.fullmatch(link["key"]) or link["key"] in article_keys:
                _fail(field, "unique stable article key required")
            article_keys.add(link["key"])
            if not _HASH.fullmatch(str(link.get("input_fingerprint", ""))):
                _fail(field, "article input fingerprint required")
            _refs(link.get("evidence_ids"), documents, field + ".article_link.evidence_ids")
        for subject in _list(record.get("subjects", []), field + ".subjects"):
            _object(subject, {"slug", "identity_basis"}, field + ".subject")
            if not isinstance(subject.get("slug"), str) or not _ID.fullmatch(subject["slug"]):
                _fail(field, "explicit safe subject slug required")
            _texts(subject, ("identity_basis",), field + ".subject")
    return catalog


def prepare_dossiers(catalog, articles, annotations=None, now=None):
    """Prepare pages/navigation immutably; article annotations must be validated first."""
    validate_dossiers(catalog)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        _fail("dossiers.now", "zoned datetime required")
    article_index = {annotation_key(a): a for a in articles}
    annotations = annotations or {}
    pages, article_relations, subjects = [], {}, {}
    report = {"emitted": 0, "indexable": 0, "withdrawn": 0, "suppressed": []}

    def suppress(key, reason):
        report["suppressed"].append({"key": key, "reason": reason})

    def evidence_active(refs, evidence):
        return all(evidence[ref].get("status", "active") == "active" for ref in refs)

    def proof_links(refs, evidence, dossier_path=None):
        result = []
        for ref in refs:
            doc = evidence[ref]
            parts = _url_parts(doc.get("url"))
            if parts:
                result.append({**parts, "locator": doc["locator"], "id": ref,
                               "title": doc.get("title", doc.get("role", "Document examinat")),
                               "anchor": f"{dossier_path}#document-{ref}" if dossier_path else None})
        return result

    ready = {}
    for key, record in catalog.items():
        review = record["review"]
        if review["state"] == "draft":
            continue
        page = copy.deepcopy(record)
        page.update({"path": f"/dosar/{record['slug']}/", "reviewed_at": review["reviewed_at"],
                     "review_kind": review["kind"], "indexable": False,
                     "article_links": [], "relations": [], "state": review["state"]})
        if review["state"] == "withdrawn":
            page.update({"summary": record["withdrawal_note"], "documents": [], "events": [],
                         "history": [], "uncertainties": []})
            report["withdrawn"] += 1
        else:
            documents = {doc["id"]: doc for doc in record["documents"]}
            fresh = review["input_fingerprint"] == dossier_fingerprint(record)
            active_summary = evidence_active(record["summary_evidence_ids"], documents)
            if not fresh or not active_summary:
                page.update({"state": "needs_review", "summary": "Sinteza necesită o nouă examinare documentară.",
                             "events": [], "history": [], "uncertainties": []})
                suppress("dossier:" + key, "input_changed" if not fresh else "summary_evidence_inactive")
            else:
                page["indexable"] = True
                ready[key] = page
            page["documents"] = [{**doc, **_url_parts(doc["url"])} for doc in record["documents"]]
            for event in page["events"]:
                event["evidence_inactive"] = not evidence_active(event["evidence_ids"], documents)
        pages.append(page)

    def relation_view(relation, evidence, owner, dossier_path=None):
        _validate_relation(relation, evidence, catalog, owner + ".relation")
        refs = list(dict.fromkeys(relation["evidence_ids"] + relation.get("effect_evidence_ids", [])))
        if relation["review"]["state"] != "approved" or not evidence_active(refs, evidence):
            suppress(owner, "relation_review_or_evidence_inactive")
            return None
        target = relation["target"]
        if target.startswith("dossier:"):
            record = catalog[target[8:]]
            page = ready.get(target[8:])
            if page is None or relation["target_fingerprint"] != dossier_fingerprint(record):
                suppress(owner, "dossier_target_changed_or_inactive")
                return None
            path, title = page["path"], page["title"]
        else:
            article = article_index.get(target)
            # Target approval concerns the facts the reader will see, including a
            # material presentation or geographic correction.
            if (article is None
                    or relation["target_fingerprint"] != source_fingerprint(article)):
                suppress(owner, "article_target_absent_or_changed")
                return None
            path, title = public_path(article), article["title"]
        return {"path": path, "title": title, "label": RELATION_LABELS[relation["type"]],
                "type": relation["type"], "explanation": relation["explanation"],
                "effect_status": relation.get("effect_status"),
                "identity_basis": relation["identity_basis"],
                "evidence": proof_links(refs, evidence, dossier_path)}

    for key, page in ready.items():
        record = catalog[key]
        documents = {doc["id"]: doc for doc in record["documents"]}
        for relation in record.get("relations", []):
            view = relation_view(relation, documents, "dossier:" + key, page["path"])
            if view:
                page["relations"].append(view)
        for link in record.get("article_links", []):
            article = article_index.get(link["key"])
            if (article is None
                    or source_fingerprint(article) != link["input_fingerprint"]
                    or not evidence_active(link["evidence_ids"], documents)):
                suppress(link["key"], "dossier_article_absent_or_changed")
                continue
            page["article_links"].append({"path": public_path(article), "title": article["title"]})
            article_relations.setdefault(link["key"], []).append({
                "path": page["path"], "title": page["title"], "type": "context",
                "label": RELATION_LABELS["context"], "explanation": link["explanation"],
                "identity_basis": link["identity_basis"],
                "evidence": proof_links(link["evidence_ids"], documents, page["path"]),
            })
        for subject in record.get("subjects", []):
            subjects.setdefault(subject["slug"], []).append({"path": page["path"], "title": page["title"],
                                                           "identity_basis": subject["identity_basis"]})
    for key, annotation in annotations.items():
        relations = _list(annotation.get("relations", []), key + ".relations")
        if not relations:
            continue
        evidence = {e["id"]: e for e in annotation.get("evidence", [])}
        for relation in relations:
            _validate_relation(relation, evidence, catalog, key + ".relation")
        article = article_index.get(key)
        review = annotation.get("review", {})
        if (article is None or review.get("state") != "approved"
                or review.get("input_fingerprint") != source_fingerprint(article)):
            suppress(key, "relation_source_absent_or_changed")
            continue
        for relation in relations:
            view = relation_view(relation, evidence, key)
            if view:
                article_relations.setdefault(key, []).append(view)
    report.update({"emitted": len(pages), "indexable": len(ready), "prepared_at": now.isoformat()})
    return pages, article_relations, subjects, report
