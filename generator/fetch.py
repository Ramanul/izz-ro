"""Citire RSS robusta (Atom-safe) + filtru de agentii de presa + scraper HTML pentru surse fara RSS."""
import re
import socket
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

import feedparser

from . import config
from .util import normalize_url, domain_of, clean_html

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


def _parse_piataauto_date(raw: str) -> str:
        """Parseaza data in format '24 IUNIE 2026, 23:55' -> ISO 8601 UTC."""
        months = {
            "IANUARIE": 1, "FEBRUARIE": 2, "MARTIE": 3, "APRILIE": 4,
            "MAI": 5, "IUNIE": 6, "IULIE": 7, "AUGUST": 8,
            "SEPTEMBRIE": 9, "OCTOMBRIE": 10, "NOIEMBRIE": 11, "DECEMBRIE": 12,
        }
        # Extrage doar partea de data/ora (ignoram categoriile dupa "|")
        date_part = raw.split("|")[0].strip()
        m = re.match(r"(\d{1,2})\s+([A-Z]+)\s+(\d{4}),\s+(\d{2}):(\d{2})", date_part)
        if m:
                    day, mon_str, year, hour, minute = m.groups()
                    month = months.get(mon_str.upper(), 1)
                    try:
                                    return datetime(int(year), month, int(day), int(hour), int(minute),
                                                                                tzinfo=timezone.utc).isoformat()
except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat()


class _PiataAutoParser(HTMLParser):
        """Parser HTML minimal pentru pagina de stiri piataauto.md.

            Structura paginii:
                    div.d19nwl_tz           <- container articol
                                div.d19nwl_tt
                                                a.d19nLk        <- titlu + href relativ
                                                            div.d19nwl_dt       <- data + categorii (text)
                                                                """

    def __init__(self, base_url: str):
                super().__init__()
                self.base_url = base_url.rstrip("/")
                self.items: list[dict] = []
                self._in_tz = False        # suntem in container articol
        self._in_tt = False        # suntem in div titlu
        self._in_dt = False        # suntem in div data
        self._in_link = False      # suntem in <a> cu titlul
        self._current: dict = {}

    def handle_starttag(self, tag, attrs):
                attrs_d = dict(attrs)
                cls = attrs_d.get("class", "")

        if tag == "div" and "d19nwl_tz" in cls:
                        self._in_tz = True
                        self._current = {}
elif self._in_tz and tag == "div" and "d19nwl_tt" in cls:
                self._in_tt = True
elif self._in_tz and tag == "div" and "d19nwl_dt" in cls:
                self._in_dt = True
elif self._in_tt and tag == "a" and "d19nLk" in cls:
                href = attrs_d.get("href", "")
                if href.startswith("/"):
                                    href = self.base_url + href
                                self._current["href"] = href
            self._in_link = True

    def handle_endtag(self, tag):
                if tag == "div":
                                if self._in_link:
                                                    self._in_link = False
                                                if self._in_tt:
                                                                    self._in_tt = False
elif self._in_dt:
                self._in_dt = False
elif self._in_tz:
                # Iesim din containerul articolului
                if self._current.get("href") and self._current.get("title"):
                                        self.items.append(dict(self._current))
                                    self._in_tz = False
                self._current = {}

    def handle_data(self, data):
                text = data.strip()
        if not text:
                        return
        if self._in_link:
                        self._current["title"] = self._current.get("title", "") + text
elif self._in_dt:
            self._current["date_raw"] = self._current.get("date_raw", "") + " " + text


def _fetch_html_scraper(key: str, source: dict) -> tuple[list, str | None]:
        """Scraper HTML pentru surse care nu au RSS. Legal: citeste pagina publica."""
    base_url = source["base_url"]
    scrape_url = source["url"]
    items = []
    try:
                req = urllib.request.Request(scrape_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                        raw = resp.read().decode("utf-8", errors="replace")
except (urllib.error.URLError, socket.timeout, ValueError) as exc:
        return items, f"{key}: {exc}"

    parser = _PiataAutoParser(base_url)
    parser.feed(raw)

    for entry in parser.items[: config.MAX_PER_SOURCE]:
                link = entry["href"]
        title = clean_html(entry["title"])
        if not link or not title:
                        continue
        published = _parse_piataauto_date(entry.get("date_raw", ""))
        items.append({
                        "url": normalize_url(link),
                        "original_link": link,
                        "source": key,
                        "source_name": source["name"],
                        "original_title": title,
                        "title": title,
                        "description": "",          # descrierea va fi generata de AI din titlu
                        "category": source["category"],
                        "published": published,
                        "model": None,
        })
    return items, None


def _fetch_one(key: str, source: dict) -> tuple[list, str | None]:
        """Returneaza (articole, eroare). Alege metoda de fetch in functie de tipul sursei."""
    if source.get("type") == "html_scraper":
                return _fetch_html_scraper(key, source)

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
        title = clean_html(entry.get("title") or "")
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
                        "title": title,
                        "description": clean_html(entry.get("summary") or entry.get("description") or ""),
                        "category": source["category"],
                        "published": _parse_date(entry),
                        "model": None,
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
