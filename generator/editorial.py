"""Validated documentary context on article copies; no factual overrides."""
import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from . import config
from .select import _dedup_sources, anunt_oficial_fara_corp

PATH_RE = re.compile(r"^/[a-z0-9-]+/[a-z0-9-]+/$")
ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
RECORD_FIELDS = {"key", "public_paths", "review", "claims", "evidence", "uncertainties"}
REVIEW_FIELDS = {"state", "kind", "reviewer", "reviewed_at", "input_fingerprint"}
EVIDENCE_FIELDS = {"id", "url", "locator", "role", "verified_at", "published_at", "status"}
CLAIM_FIELDS = {"id", "text", "status", "evidence_ids"}
CLAIM_LABELS = {"reported": "Relatarea sursei", "documented": "Document examinat",
                "interpretation": "Interpretare", "forecast": "Prognoză"}


class EditorialError(ValueError):
    """A blocking catalog error, identified by public record and field."""


def public_path(article):
    path = f"/{article.get('category', '')}/{article.get('slug', '')}/"
    if not PATH_RE.fullmatch(path) or article.get("category") not in config.CATEGORIES:
        raise EditorialError("article: missing or unsafe category/slug")
    return path


def annotation_key(article):
    story_id = article.get("story_id") if article.get("model") == "C" else None
    if story_id is not None and (not isinstance(story_id, str) or not story_id.strip()):
        raise EditorialError("article.story_id: non-empty persisted identity required")
    return story_id or "article:" + public_path(article)


def _canonical(value):
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in sorted(value.items())}
    return value


def source_fingerprint(article):
    """Ignore renderer fields and normalize the renderer's existing source dedup."""
    item = copy.deepcopy(article)
    _dedup_sources(item)
    fields = ("model", "category", "slug", "story_id", "title", "teaser", "synthesis",
              "original_link", "url", "sources", "members", "entities", "processed_by")
    material = {k: item.get(k) for k in fields}
    if anunt_oficial_fara_corp(item):
        material["teaser"] = ""
    raw = json.dumps(_canonical(material), sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value


def load_annotations(path=None):
    path = Path(path) if path is not None else Path(config.ROOT) / "content/editorial/annotations.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EditorialError(f"{path}: invalid UTF-8 JSON") from exc
    if (not isinstance(data, dict) or set(data) != {"schema_version", "records"}
            or type(data.get("schema_version")) is not int or data["schema_version"] != 1
            or not isinstance(data.get("records"), list)):
        raise EditorialError(f"{path}: expected schema_version=1 and records array")
    index = {}
    for record in data["records"]:
        if not isinstance(record, dict) or not _text(record.get("key")):
            raise EditorialError("records.key: non-empty string required")
        if record["key"] in index:
            raise EditorialError(f"{record['key']}: duplicate key")
        index[record["key"]] = record
    return index


def _date(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _url(value):
    if not _text(value) or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None)
    except ValueError:
        return False


def validate_annotations(index, articles):
    """Return field errors. Old or absent ordinary context is withheld, not approved."""
    errors, current = [], {}
    for article in articles:
        key = annotation_key(article)
        if key in current:
            errors.append(f"{key}: ambiguous article identity")
        current[key] = article
    for key, record in index.items():
        def error(field, message):
            errors.append(f"{key}.{field}: {message}")
        if not isinstance(record, dict) or record.get("key") != key:
            error("key", "catalog key mismatch")
            continue
        if set(record) - RECORD_FIELDS:
            error("fields", "unsupported or private field in context-only pilot")
        review = record.get("review")
        if not isinstance(review, dict):
            error("review", "object required")
            continue
        if set(review) - REVIEW_FIELDS:
            error("review", "unsupported or private field")
        if review.get("state") not in ("draft", "approved", "withdrawn"):
            error("review.state", "unknown state")
        approved = review.get("state") == "approved"
        paths = record.get("public_paths")
        if (not isinstance(paths, list) or not paths
                or any(not isinstance(p, str) or not PATH_RE.fullmatch(p) for p in paths)):
            error("public_paths", "observed safe article paths required")
        elif key in current and public_path(current[key]) not in paths:
            error("public_paths", "current article path absent")
        if approved:
            if review.get("kind") not in ("human", "documentary"):
                error("review.kind", "explicit human/documentary kind required")
            if not _text(review.get("reviewer")) or "@" in review["reviewer"]:
                error("review.reviewer", "reviewer identifier required; no email")
            if not _date(review.get("reviewed_at")):
                error("review.reviewed_at", "ISO datetime with timezone required")
            fingerprint = review.get("input_fingerprint")
            if not isinstance(fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", fingerprint):
                error("review.input_fingerprint", "SHA256 required")
        evidence = record.get("evidence")
        if not isinstance(evidence, list):
            error("evidence", "array required")
            continue
        evidence_ids, withdrawn_ids = set(), set()
        for item in evidence:
            if not isinstance(item, dict):
                error("evidence", "object required")
                continue
            eid = item.get("id")
            if not isinstance(eid, str) or not ID_RE.fullmatch(eid) or eid in evidence_ids:
                error("evidence.id", "safe unique id required")
                continue
            evidence_ids.add(eid)
            if set(item) - EVIDENCE_FIELDS:
                error("evidence", "unsupported or private field")
            if not _url(item.get("url")) or not all(_text(item.get(k)) for k in ("locator", "role")):
                error("evidence", "URL, precise locator and source role required")
            if item.get("status", "active") not in ("active", "withdrawn"):
                error("evidence.status", "active or withdrawn required")
            if item.get("status") == "withdrawn":
                withdrawn_ids.add(eid)
            if approved and not _date(item.get("verified_at")):
                error("evidence.verified_at", "examined-at datetime with timezone required")
            if item.get("published_at") is not None and not _date(item["published_at"]):
                error("evidence.published_at", "ISO datetime with timezone required")
        claims = record.get("claims")
        if not isinstance(claims, list) or (approved and not claims):
            error("claims", "array with at least one approved claim required")
            continue
        ids = set()
        for claim in claims:
            if not isinstance(claim, dict):
                error("claims", "object required")
                continue
            cid = claim.get("id")
            if not isinstance(cid, str) or not ID_RE.fullmatch(cid) or cid in ids:
                error("claims.id", "safe unique id required")
            else:
                ids.add(cid)
            if (set(claim) - CLAIM_FIELDS or not _text(claim.get("text"))
                    or claim.get("status") not in tuple(CLAIM_LABELS)):
                error("claims", "known fields, non-empty text and claim status required")
            refs = claim.get("evidence_ids")
            if (not isinstance(refs, list) or not refs
                    or any(not isinstance(ref, str) or ref not in evidence_ids for ref in refs)):
                error("claims.evidence_ids", "existing evidence references required")
            elif approved and any(ref in withdrawn_ids for ref in refs):
                error("claims.evidence_ids", "withdrawn evidence requires another review")
        unknowns = record.get("uncertainties", [])
        if not isinstance(unknowns, list):
            error("uncertainties", "array required")
            continue
        for item in unknowns:
            if (not isinstance(item, dict) or set(item) != {"question", "needed"}
                    or not all(_text(item.get(k)) for k in ("question", "needed"))):
                error("uncertainties", "question and required evidence must be explicit")
    return errors


def apply_view(article, index):
    """Withhold missing, unapproved or changed context; never alter input."""
    view = copy.deepcopy(article)
    view.pop("editorial", None)
    view.pop("editorial_status", None)
    record = index.get(annotation_key(article))
    if record is None:
        return view
    errors = validate_annotations({annotation_key(article): record}, [article])
    if errors:
        raise EditorialError("\n".join(errors))
    if record["review"]["state"] != "approved":
        return view
    if record["review"]["input_fingerprint"] != source_fingerprint(article):
        view["editorial_status"] = "needs_review"
        return view
    # No reviewer identity or internal metadata in the public context.
    context = {k: copy.deepcopy(record.get(k, [])) for k in ("claims", "evidence", "uncertainties")}
    context["review_kind"] = record["review"]["kind"]
    context["reviewed_at"] = record["review"]["reviewed_at"]
    for evidence in context["evidence"]:
        evidence["scheme"] = urlsplit(evidence["url"]).scheme
        evidence["destination"] = evidence["url"][len(evidence["scheme"]) + 3:]
    for claim in context["claims"]:
        claim["label"] = CLAIM_LABELS[claim["status"]]
    view["editorial"] = context
    return view


def catalog_report(index, articles):
    current = {annotation_key(a): a for a in articles}
    result = {"schema_version": 1, "publishable_articles": len(articles),
              "catalog_records": len(index), "approved": 0, "draft": 0, "withdrawn": 0,
              "fresh": 0, "needs_review": 0, "absent": 0}
    for key, record in index.items():
        state = record["review"]["state"]
        result[state] += 1
        if key not in current:
            result["absent"] += 1
        elif state == "approved":
            field = "fresh" if record["review"]["input_fingerprint"] == source_fingerprint(current[key]) else "needs_review"
            result[field] += 1
    result["coverage"] = {"numerator": result["fresh"], "denominator": len(articles)}
    return result
