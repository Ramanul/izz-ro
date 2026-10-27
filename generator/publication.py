"""Approved corrections on publication copies, never on collected state."""
import copy
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

from . import config, editorial, geo

FIELDS = {"key", "public_paths", "state", "review", "notice", "evidence_url", "presentation"}
PRESENTATION = {"title", "teaser", "synthesis", "county"}


def _plain(value):
    return (isinstance(value, str) and bool(value.strip()) and "<" not in value
            and ">" not in value and not any(ord(c) < 32 and c not in "\n\t" for c in value))


def load(path=None):
    path = Path(path or Path(config.ROOT) / "content/editorial/corrections.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise editorial.EditorialError("corrections: invalid UTF-8 JSON") from exc
    if (not isinstance(data, dict) or set(data) != {"schema_version", "records"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or not isinstance(data["records"], list)):
        raise editorial.EditorialError("corrections: schema_version=1 and records required")
    result = {}
    for row in data["records"]:
        if not isinstance(row, dict) or not _plain(row.get("key")) or row["key"] in result:
            raise editorial.EditorialError("corrections: unique record key required")
        result[row["key"]] = row
    return result


def validate(index, articles):
    current = {editorial.annotation_key(a): a for a in articles}
    seen = set()
    for key, row in index.items():
        def fail(message):
            raise editorial.EditorialError(f"corrections.{key}: {message}")
        if set(row) != FIELDS or row["key"] != key:
            fail("exact public fields required")
        if row["state"] not in {"corrected", "withdrawn"}:
            fail("corrected/withdrawn state required")
        paths = row["public_paths"]
        if (not isinstance(paths, list) or not paths
                or any(not isinstance(p, str) or not editorial.PATH_RE.fullmatch(p) for p in paths)
                or len(set(paths)) != len(paths) or seen.intersection(paths)):
            fail("unique observed public paths required")
        seen.update(paths)
        if key in current and editorial.public_path(current[key]) not in paths:
            fail("current article path not observed")
        if not _plain(row["notice"]) or not editorial._url(row["evidence_url"]):
            fail("plain explanation and examined evidence URL required")
        review = row["review"]
        if (not isinstance(review, dict) or set(review) != editorial.REVIEW_FIELDS
                or review.get("state") != "approved" or review.get("kind") not in {"human", "documentary"}
                or not _plain(review.get("reviewer")) or "@" in review["reviewer"]
                or not editorial._date(review.get("reviewed_at"))
                or not isinstance(review.get("input_fingerprint"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", review["input_fingerprint"])):
            fail("explicit approved review, date and source fingerprint required")
        if key in current and editorial.source_fingerprint(current[key]) != review["input_fingerprint"]:
            fail("source changed; publication blocked until correction is reviewed")
        presentation = row["presentation"]
        if (not isinstance(presentation, dict) or set(presentation) - PRESENTATION
                or any(not _plain(v) for v in presentation.values())):
            fail("plain known presentation fields required")
        if row["state"] == "corrected" and not presentation:
            fail("corrected presentation required")
        if row["state"] == "withdrawn" and presentation:
            fail("withdrawal cannot republish article content")
        if "county" in presentation and not geo.regiune_afisare(presentation["county"]):
            fail("recognized county code required")
        for other_key, article in current.items():
            if other_key != key and editorial.public_path(article) in paths:
                fail("public path belongs to a different current article")


def apply(articles, index):
    """Validate against original inputs before applying any override or output cleanup."""
    validate(index, articles)
    result = []
    for article in articles:
        view = copy.deepcopy(article)
        row = index.get(editorial.annotation_key(article))
        if row:
            if row["state"] == "withdrawn":
                continue
            view.update({k: v for k, v in row["presentation"].items() if k != "county"})
            if "county" in row["presentation"]:
                view["editorial_county"] = row["presentation"]["county"]
            view["updated"] = row["review"]["reviewed_at"]
            view["correction"] = public_notice(row)
            # Images/related caches derived from the old wording cannot survive an override.
            for field in ("display_title", "cover_path", "art_path", "photo_path", "lead_credit",
                          "editorial", "timeline", "ghid"):
                view.pop(field, None)
        result.append(view)
    return result


def public_notice(row):
    scheme = urlsplit(row["evidence_url"]).scheme
    return {"state": row["state"], "notice": row["notice"], "evidence_url": row["evidence_url"],
            "scheme": scheme, "destination": row["evidence_url"][len(scheme) + 3:],
            "reviewed_at": row["review"]["reviewed_at"], "kind": row["review"]["kind"]}


def revisions(index):
    """Small, deterministic version signal; never download the active news manifest."""
    records = [{"paths": row["public_paths"], "presentation": row["presentation"],
                **public_notice(row)} for _, row in sorted(index.items())]
    version = (hashlib.sha256(json.dumps(records, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
               if records else "original")
    return {"schema_version": 1, "version": version}


def manifest(articles, index):
    active = [{"path": editorial.public_path(a), "title": a["title"],
               "fingerprint": editorial.source_fingerprint(a),
               "state": "corrected" if a.get("correction") else "active",
               "county": a.get("editorial_county", "")} for a in articles]
    withdrawals = [{"paths": row["public_paths"], **public_notice(row)}
                   for _, row in sorted(index.items()) if row["state"] == "withdrawn"]
    history = [{"paths": row["public_paths"], **public_notice(row)} for _, row in sorted(index.items())]
    body = {"schema_version": 1, "active": active, "withdrawals": withdrawals, "history": history}
    body["digest"] = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                              separators=(",", ":")).encode()).hexdigest()
    return body


def corrections_feed(index, site_url=None, now=None):
    """Deterministic RSS 2.0 feed for approved corrections and withdrawals.

    - Empty when no approved corrections exist in the catalog (clean RSS channel).
    - Exposes review date, notice explanation, state and site explanation link.
    - Never republishes withdrawn/old expired story bodies.
    """
    site_url = (site_url or config.SITE["url"]).rstrip("/")
    feed_url = f"{site_url}/corectii/feed.xml"
    policy_url = f"{site_url}/legal/corrections/"
    build_date = format_datetime((now or datetime.now(timezone.utc)).astimezone(timezone.utc))

    entries = []
    # Sort deterministically: newest review date first, then unique record key
    for _, row in sorted(index.items(), key=lambda item: (item[1]["review"]["reviewed_at"], item[0]), reverse=True):
        reviewed_at = row["review"]["reviewed_at"]
        try:
            dt = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            pub_date = format_datetime(dt.astimezone(timezone.utc))
        except (ValueError, TypeError):
            pub_date = ""

        path = row["public_paths"][0] if row["public_paths"] else "/legal/corrections/"
        item_link = f"{site_url}/{path.lstrip('/')}"

        if row["state"] == "corrected":
            title = f"Corecție: {row['presentation'].get('title', 'Articol corectat')}"
            guid = f"{item_link}#corectie-{reviewed_at}"
        else:
            title = "Retragere: Material retras din publicație"
            guid = f"{item_link}#retragere-{reviewed_at}"

        pub_xml = f"      <pubDate>{xml_escape(pub_date)}</pubDate>\n" if pub_date else ""
        entries.append(
            "    <item>\n"
            f"      <title>{xml_escape(title)}</title>\n"
            f"      <link>{xml_escape(item_link)}</link>\n"
            f"      <guid isPermaLink=\"false\">{xml_escape(guid)}</guid>\n"
            f"{pub_xml}"
            f"      <description>{xml_escape(row['notice'])}</description>\n"
            "    </item>"
        )

    items_block = ("\n" + "\n".join(entries)) if entries else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '<channel>\n'
        '  <title>Corecții și retrageri — IZZ.ro</title>\n'
        f'  <link>{xml_escape(policy_url)}</link>\n'
        f'  <atom:link href="{xml_escape(feed_url)}" rel="self" type="application/rss+xml"/>\n'
        '  <description>Jurnalul public al corecțiilor materiale și retragerilor editoriale IZZ.ro.</description>\n'
        f'  <language>{config.SITE.get("lang", "ro")}</language>\n'
        f'  <lastBuildDate>{build_date}</lastBuildDate>{items_block}\n'
        '</channel>\n'
        '</rss>\n'
    )
