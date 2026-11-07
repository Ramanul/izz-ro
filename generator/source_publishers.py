"""E1 — metadată secă de editor și grup media verificată din casetele editoriale oficiale.

Regula de bază (`specs/plan-paradigma-izz.md` §3 E1 și `specs/editorial-sources-practical.md`):
- intră DOAR domeniile ale căror pagini oficiale („Despre", „Redacția", „Termeni și condiții",
  raport anual) au fost verificate direct, cu `evidence_url` și `verified_at`;
- niciun domeniu neexaminat nu primește etichetă dedusă din nume sau din reputație;
- nicio judecată de valoare („credibil", „de încredere", „tabloid", „independent", „partizan"):
  doar editorul juridic, grupul media ori regimul instituțional declarat în act.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date

from . import config, guard
from .util import domain_of
from .verifica_sinteza import _norm

PUBLISHER_PATH = os.path.join(config.ROOT, "content", "editorial", "source-publishers.json")

_FEED_DOMAIN_ALIASES = {
    "feeds.bbci.co.uk": "bbc.co.uk",
    "bbc.com": "bbc.co.uk",
    "rss.dw.com": "dw.com",
}

# Garda anti-evaluare: registrul are voie să spună CINE editează publicația conform actului,
# niciodată cât de „bună", „serioasă", „credibilă" sau „independentă" este.
_JUDECATA_VALOARE = re.compile(
    r"\b(?:credibil|necredibil|incredere|indoielnic|partizan|nepartizan|propagand|tabloid|"
    r"serios|neserios|independent|obiectiv|subiectiv|recomandat|nerecomandat|calitat|"
    r"echilibrat|dezinform|toxic|ireprosabil|prestigios)\w*\b",
)


def canonical_domain(url_or_domain: str) -> str:
    raw = (url_or_domain or "").strip()
    if not raw:
        return ""
    dom = domain_of(raw if "://" in raw else f"https://{raw}/")
    return _FEED_DOMAIN_ALIASES.get(dom, dom)


def format_label(rec: dict) -> str:
    parts = [rec["publisher"]]
    if rec.get("group"):
        parts.append(rec["group"])
    if rec.get("funding_note"):
        parts.append(rec["funding_note"])
    return " · ".join(parts)


def validate_record(domain: str, rec: dict) -> dict:
    if not domain or "." not in domain or domain != domain.lower():
        raise ValueError(f"domeniu invalid în source-publishers.json: {domain!r}")
    if not isinstance(rec, dict):
        raise ValueError(f"înregistrare invalidă pentru {domain}: {type(rec).__name__}")
    publisher = (rec.get("publisher") or "").strip()
    if not publisher:
        raise ValueError(f"{domain}: lipsește 'publisher'")
    group = (rec.get("group") or "").strip() or None
    funding_note = (rec.get("funding_note") or "").strip() or None
    evidence_url = (rec.get("evidence_url") or "").strip()
    if not evidence_url.startswith("https://") or guard.url_ostil(evidence_url) is not None:
        raise ValueError(f"{domain}: 'evidence_url' trebuie să fie https:// valid: {evidence_url!r}")
    verified_at = (rec.get("verified_at") or "").strip()
    try:
        date.fromisoformat(verified_at)
    except ValueError as exc:
        raise ValueError(f"{domain}: 'verified_at' invalid ({verified_at!r})") from exc

    text_verificat = _norm(" ".join(x for x in (publisher, group, funding_note) if x))
    m = _JUDECATA_VALOARE.search(text_verificat)
    if m:
        raise ValueError(f"{domain}: termen evaluativ interzis în metadată ({m.group(0)!r})")

    out = {
        "domain": domain,
        "publisher": publisher,
        "group": group,
        "funding_note": funding_note,
        "evidence_url": evidence_url,
        "verified_at": verified_at,
    }
    out["label"] = format_label(out)
    return out


def load(path: str | None = None) -> dict[str, dict]:
    target = path or PUBLISHER_PATH
    if not os.path.exists(target):
        return {}
    with open(target, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError(f"{target}: schema_version necunoscut")
    pubs = raw.get("publishers")
    if not isinstance(pubs, dict):
        raise ValueError(f"{target}: 'publishers' trebuie să fie obiect JSON")
    return {dom: validate_record(dom, rec) for dom, rec in sorted(pubs.items())}


def _name_to_domain() -> dict[str, str]:
    return {
        meta["name"]: canonical_domain(meta["url"])
        for meta in config.SOURCES.values()
        if meta.get("name") and meta.get("url")
    }


def for_url(url: str, publishers: dict[str, dict] | None = None) -> dict | None:
    pubs = load() if publishers is None else publishers
    return pubs.get(canonical_domain(url))


def shared_groups(sources: list | None, publishers: dict[str, dict] | None = None) -> list[dict]:
    """Grupurile media verificate care apar prin cel puțin două publicații distincte în `sources`."""
    if not sources or len(sources) < 2:
        return []
    pubs = load() if publishers is None else publishers
    if not pubs:
        return []
    by_name = _name_to_domain()
    membri_pe_grup: dict[str, set[str]] = {}
    for s in sources:
        if not isinstance(s, dict):
            continue
        nume = (s.get("name") or "").strip()
        if not nume:
            continue
        dom = canonical_domain(s.get("url") or "") or by_name.get(nume, "")
        info = pubs.get(dom)
        if info and info.get("group"):
            membri_pe_grup.setdefault(info["group"], set()).add(nume)
    return [
        {"group": grup, "members": sorted(membri)}
        for grup, membri in sorted(membri_pe_grup.items())
        if len(membri) >= 2
    ]
