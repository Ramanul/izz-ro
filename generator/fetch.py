"""Citire RSS robusta (Atom-safe) + filtru de agentii de presa."""
import socket
import urllib.request
from datetime import datetime, timezone

import feedparser

from . import config
from .util import normalize_url, domain_of

USER_AGENT = "IZZ.ro Bot/1.0 (+https://izz.ro)"
TIMEOUT = 10  # secunde per feed


def _is_agency(url: str, source_name: str) -> bool:
    """True daca linkul sau numele sursei tine de o agentie de presa (continut licentiat)."""
    haystack = (domain_of(url) + " " + source_name).lower()
    return any(bad in haystack for bad in config.AGENCY_BLOCKLIST)


def _parse_date(entry) -> str:
    """Data publicarii in ISO 8601 UTC; fallback = acum."""
    for key in ("published_parsed", "updated_parsed"):
        tm = entry.get(key)
        if tm:
            try:
                return datetime(*tm[:6], tzinfo=timezone.utc).isoformat()
            except (ValueError, TypeError):
                pass
    return datetime.now(timezone.utc).isoformat()


def _fetch_one(key: str, source: dict) -> tuple[list, str | None]:
    """Returneaza (articole, eroare). Eroarea e None daca sursa a raspuns."""
    items = []
    try:
        req = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
    except (urllib.error.URLError, socket.timeout, ValueError) as exc:
        return items, f"{key}: {exc}"

    feed = feedparser.parse(raw)
    for entry in feed.entries[: config.MAX_PER_SOURCE]:
        link = entry.get("link", "").strip()
        title = (entry.get("title") or "").strip()
        if not link or not title:
            continue
        if _is_agency(link, source["name"]):
            continue
        items.append({
            "url": normalize_url(link),
            "original_link": link,
            "source": key,
            "source_name": source["name"],
            "original_title": title,
            "title": title,                       # inlocuit de AI in process.py
            "description": (entry.get("summary") or entry.get("description") or "").strip(),
            "category": source["category"],       # categorie initiala (AI o poate ajusta)
            "published": _parse_date(entry),
            "model": None,                          # "B" / "C" dupa procesare
        })
    return items, None


def fetch_all() -> tuple[list, list]:
    """Returneaza (toate_articolele_brute, surse_moarte)."""
    all_items, dead = [], []
    for key, source in config.SOURCES.items():
        items, err = _fetch_one(key, source)
        if err:
            dead.append(err)
        all_items.extend(items)
    return all_items, dead
