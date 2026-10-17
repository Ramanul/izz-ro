"""Validated documentary context on article copies; no factual overrides."""
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from . import config
from .select import _dedup_sources, anunt_oficial_fara_corp

PATH_RE = re.compile(r"^/[a-z0-9-]+/[a-z0-9-]+/$")
ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
RECORD_FIELDS = {"key", "public_paths", "review", "claims", "evidence", "uncertainties",
                 "impacts", "actions", "differences"}
REVIEW_FIELDS = {"state", "kind", "reviewer", "reviewed_at", "input_fingerprint"}
EVIDENCE_FIELDS = {"id", "url", "locator", "role", "verified_at", "published_at", "status", "provenance_id"}
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


def load_provenance(path=None):
    """Only explicitly examined artifacts/resources; absence never proves independence."""
    path = Path(path) if path is not None else Path(config.ROOT) / "content/editorial/source-provenance.json"
    if not path.exists():
        return {"sources": {}, "resources": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EditorialError(f"{path}: invalid UTF-8 JSON") from exc
    if (not isinstance(data, dict) or set(data) != {"schema_version", "records", "resources"}
            or type(data.get("schema_version")) is not int or data["schema_version"] != 1):
        raise EditorialError("provenance: expected schema_version=1, records and resources")
    result = {"sources": {}, "resources": {}}
    for field, target in (("records", "sources"), ("resources", "resources")):
        items = data[field]
        if not isinstance(items, list):
            raise EditorialError(f"provenance.{field}: array required")
        for item in items:
            allowed = ({"id", "name", "url", "role", "locator", "verified_at", "origin"}
                       if target == "sources" else
                       {"id", "article_key", "title", "url", "organizer", "area", "locator",
                        "verified_at", "expires_at", "deadline_basis"})
            if not isinstance(item, dict) or set(item) - allowed:
                raise EditorialError(f"provenance.{field}: known fields required")
            iid = item.get("id")
            if not isinstance(iid, str) or not ID_RE.fullmatch(iid) or iid in result[target]:
                raise EditorialError(f"provenance.{field}.id: safe unique id required")
            texts = ("name", "role", "locator") if target == "sources" else ("article_key", "title", "organizer", "area", "locator")
            if (not all(_text(item.get(k)) for k in texts) or not _url(item.get("url"))
                    or not _date(item.get("verified_at"))):
                raise EditorialError(f"provenance.{iid}: examined URL, locator, role/scope and date required")
            if item.get("expires_at") is not None and not _date(item["expires_at"]):
                raise EditorialError(f"provenance.{iid}.expires_at: zoned datetime required")
            if target == "resources" and item.get("expires_at") is not None and not _text(item.get("deadline_basis")):
                raise EditorialError(f"provenance.{iid}.deadline_basis: examined time basis required")
            origin = item.get("origin")
            if origin is not None:
                if (not isinstance(origin, dict) or set(origin) != {"url", "relation", "locator", "verified_at"}
                        or origin.get("relation") not in {"original", "republication"}
                        or not _url(origin.get("url")) or not _text(origin.get("locator"))
                        or not _date(origin.get("verified_at"))):
                    raise EditorialError(f"provenance.{iid}.origin: documented origin and relationship required")
                if origin["relation"] == "original" and origin["url"] != item["url"]:
                    raise EditorialError(f"provenance.{iid}.origin: original must identify this artifact")
            result[target][iid] = item
    originals = {source["url"] for source in result["sources"].values()
                 if source.get("origin", {}).get("relation") == "original"}
    for source in result["sources"].values():
        origin = source.get("origin")
        if origin and origin["relation"] == "republication" and origin["url"] not in originals:
            raise EditorialError(f"provenance.{source['id']}.origin: examined original artifact required")
    return result


def _validate_extensions(record, provenance, error):
    evidence = {e["id"]: e for e in record["evidence"] if isinstance(e, dict) and isinstance(e.get("id"), str)}

    def refs_valid(refs):
        return (isinstance(refs, list) and bool(refs)
                and all(isinstance(r, str) and r in evidence and evidence[r].get("status", "active") == "active" for r in refs))

    for item in evidence.values():
        sid = item.get("provenance_id")
        if sid is not None:
            source = provenance["sources"].get(sid) if isinstance(sid, str) else None
            if source is None or source["url"] != item.get("url"):
                error("evidence.provenance_id", "existing examined artifact with the same URL required")
    for field in ("impacts", "actions", "differences"):
        items = record.get(field, [])
        if not isinstance(items, list):
            error(field, "array required")
            continue
        for item in items:
            if not isinstance(item, dict):
                error(field, "object required")
                continue
            if field == "impacts":
                if (set(item) != {"group", "effect", "status", "horizon", "evidence_ids"}
                        or not all(_text(item.get(k)) for k in ("group", "effect", "horizon"))
                        or item.get("status") not in {"observed", "projected"}
                        or not refs_valid(item.get("evidence_ids"))):
                    error(field, "attributed group, effect, horizon, observed/projected status and active evidence required")
            elif field == "actions":
                rid = item.get("resource_id")
                resource = provenance["resources"].get(rid) if isinstance(rid, str) else None
                refs = item.get("evidence_ids")
                if (set(item) != {"resource_id", "area", "evidence_ids"} or resource is None
                        or resource["article_key"] != record["key"] or item.get("area") != resource["area"]
                        or not refs_valid(refs)):
                    error(field, "examined resource for this article and geographic scope with active evidence required")
                elif not any(evidence[r].get("url") == resource["url"] for r in refs):
                    error(field, "resource destination must be an examined evidence URL")
            else:
                positions = item.get("positions")
                if (set(item) != {"topic", "positions"} or not _text(item.get("topic"))
                        or not isinstance(positions, list) or len(positions) < 2):
                    error(field, "explicit topic and at least two attributed positions required")
                    continue
                ids = []
                for position in positions:
                    if (not isinstance(position, dict) or set(position) != {"evidence_id", "text"}
                            or not _text(position.get("text")) or not refs_valid([position.get("evidence_id")])):
                        error(field, "each position needs text and active evidence")
                    else:
                        ids.append(position["evidence_id"])
                if len(set(ids)) < 2:
                    error(field, "different examined evidence required; no invented average")


def validate_annotations(index, articles, provenance=None):
    """Return field errors. Old or absent ordinary context is withheld, not approved."""
    provenance = load_provenance() if provenance is None else provenance
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
        _validate_extensions(record, provenance, error)
    return errors


def apply_view(article, index, provenance=None, now=None):
    """Withhold missing, unapproved or changed context; never alter input."""
    view = copy.deepcopy(article)
    view.pop("editorial", None)
    view.pop("editorial_status", None)
    record = index.get(annotation_key(article))
    if record is None:
        return view
    provenance = load_provenance() if provenance is None else provenance
    errors = validate_annotations({annotation_key(article): record}, [article], provenance)
    if errors:
        raise EditorialError("\n".join(errors))
    if record["review"]["state"] != "approved":
        return view
    if record["review"]["input_fingerprint"] != source_fingerprint(article):
        view["editorial_status"] = "needs_review"
        return view
    # No reviewer identity or internal metadata in the public context.
    context = {k: copy.deepcopy(record.get(k, [])) for k in ("claims", "evidence", "uncertainties", "impacts", "differences")}
    context["review_kind"] = record["review"]["kind"]
    context["reviewed_at"] = record["review"]["reviewed_at"]
    for evidence in context["evidence"]:
        evidence["scheme"] = urlsplit(evidence["url"]).scheme
        evidence["destination"] = evidence["url"][len(evidence["scheme"]) + 3:]
    for claim in context["claims"]:
        claim["label"] = CLAIM_LABELS[claim["status"]]
    context["comparison"] = []
    origins = set()
    for evidence in context["evidence"]:
        source = provenance["sources"].get(evidence.get("provenance_id"))
        row = {"evidence_id": evidence["id"], "name": source["name"] if source else evidence["role"],
               "role": source["role"] if source else evidence["role"], "origin": copy.deepcopy(source.get("origin")) if source else None}
        if row["origin"]:
            origins.add(row["origin"]["url"])
            row["origin"]["scheme"] = urlsplit(row["origin"]["url"]).scheme
            row["origin"]["destination"] = row["origin"]["url"][len(row["origin"]["scheme"]) + 3:]
        context["comparison"].append(row)
    context["known_origins"] = len(origins)
    context["unknown_origins"] = sum(row["origin"] is None for row in context["comparison"])
    if not any(e.get("provenance_id") for e in context["evidence"]) and not context["differences"]:
        context["comparison"] = []
    now = now or datetime.now(timezone.utc)
    context["actions"] = []
    for action in record.get("actions", []):
        resource = copy.deepcopy(provenance["resources"][action["resource_id"]])
        expires = resource.get("expires_at")
        resource["expired"] = bool(expires and datetime.fromisoformat(expires.replace("Z", "+00:00")) <= now)
        resource["state"] = "expired" if resource["expired"] else "current" if expires else "undated"
        resource["expires_label"] = datetime.fromisoformat(expires.replace("Z", "+00:00")).strftime("%d.%m.%Y, %H:%M") if expires else ""
        resource["scheme"] = urlsplit(resource["url"]).scheme
        resource["destination"] = resource["url"][len(resource["scheme"]) + 3:]
        resource["evidence_ids"] = copy.deepcopy(action["evidence_ids"])
        resource.pop("article_key")
        context["actions"].append(resource)
    view["editorial"] = context
    return view


def catalog_report(index, articles, provenance=None, now=None):
    provenance = load_provenance() if provenance is None else provenance
    now = now or datetime.now(timezone.utc)
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
    result["examined_sources"] = len(provenance["sources"])
    result["examined_resources"] = len(provenance["resources"])
    result["resources_current"] = result["resources_expired"] = result["resources_without_deadline"] = 0
    result["generated_at"] = now.isoformat()
    result["articles_with_provenance"] = result["articles_with_impacts"] = 0
    for key, record in index.items():
        if key in current and record["review"]["state"] == "approved" and record["review"]["input_fingerprint"] == source_fingerprint(current[key]):
            result["articles_with_provenance"] += any(e.get("provenance_id") for e in record["evidence"])
            result["articles_with_impacts"] += bool(record.get("impacts"))
            for action in record.get("actions", []):
                deadline = provenance["resources"][action["resource_id"]].get("expires_at")
                expired = deadline and datetime.fromisoformat(deadline.replace("Z", "+00:00")) <= now
                field = "resources_expired" if expired else "resources_current" if deadline else "resources_without_deadline"
                result[field] += 1
    return result
