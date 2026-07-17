"""Citire RSS robusta (Atom-safe) + filtru de agentii de presa + scraper HTML pentru surse fara RSS."""
import json
import os
import re
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

import feedparser

from . import config
from .util import normalize_url, domain_of, clean_html

USER_AGENT = "IZZ.ro Bot/1.0 (+https://izz.ro)"
TIMEOUT = 10  # secunde per feed

# Conditional GET (ETag / Last-Modified): nu re-descarcam feed-uri neschimbate.
# Valabilitate limitata la 3h: mecanismul de defer (iteme amanate la 429 AI) se
# bazeaza pe re-fetch pentru retry -- un 304 onorat la nesfarsit pe un feed lent
# ar bloca reincercarea. Cache-ul e comis in repo (rularile CI sunt stateless).
CACHE_PATH = os.path.join(config.ROOT, "data", "feed_cache.json")
CACHE_MAX_AGE_H = 3


def _cache_load() -> dict:
    try:
        with open(CACHE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _cache_save(cache: dict) -> None:
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=1)
    except OSError:
        pass


def _cache_fresh(entry: dict) -> bool:
    try:
        t = datetime.fromisoformat(entry.get("fetched_at", ""))
        age = (datetime.now(timezone.utc) - t).total_seconds()
        return age < CACHE_MAX_AGE_H * 3600
    except (ValueError, TypeError):
        return False


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

    if not parser.items:
        # pagina a raspuns OK dar parser-ul n-a gasit niciun container -> structura
        # HTML s-a schimbat probabil; raportam ca sursa moarta ca sa nu esueze tacut
        return items, f"{key}: 0 articole extrase (posibil structura HTML schimbata)"

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
            "source_lang": source.get("lang", "ro"),
            "original_title": title,
            "title": title,
            "description": "",          # descrierea va fi generata de AI din titlu
            "category": source["category"],
            "published": published,
            "model": None,
        })
    return items, None


# ---- Monitor Local: scraper generic config-driven pentru surse fara RSS ----
# Multe primarii/institutii NU au feed RSS, dar publica anunturile intr-o lista HTML.
# Un singur motor parametrizat (selectoare tag.class per sursa) scaneaza oricare din
# ele, in loc de un parser hardcodat per site. stdlib-only (fara bs4/lxml).

_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
              "link", "meta", "param", "source", "track", "wbr"}

_RO_MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4, "mai": 5, "iunie": 6,
    "iulie": 7, "august": 8, "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}


def _sel(spec: str | None) -> tuple[str | None, str | None]:
    """'div.news-item' -> ('div', 'news-item'); 'article' -> ('article', None); None -> (None, None)."""
    if not spec:
        return (None, None)
    if "." in spec:
        tag, cls = spec.split(".", 1)
        return (tag or None, cls or None)
    return (spec, None)


def _parse_ro_date(raw: str) -> str:
    """Data unui anunt de primarie in ISO 8601 UTC; fallback = acum.
    Accepta: '17.07.2026', '17/07/2026', '17-07-2026', '2026-07-17', '17 iulie 2026'."""
    raw = (raw or "").strip().lower()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)                       # ISO
    if m:
        y, mo, d = (int(x) for x in m.groups())
    else:
        m = re.search(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})", raw)     # dd.mm.yyyy
        if m:
            d, mo, y = (int(x) for x in m.groups())
        else:
            m = re.search(r"(\d{1,2})\s+([a-zăâîșț]+)\s+(\d{4})", raw)    # 17 iulie 2026
            if m and m.group(2) in _RO_MONTHS:
                d, mo, y = int(m.group(1)), _RO_MONTHS[m.group(2)], int(m.group(3))
            else:
                return datetime.now(timezone.utc).isoformat()
    try:
        return datetime(y, mo, d, tzinfo=timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


class _GenericListParser(HTMLParser):
    """Parser generic pentru o lista de anunturi. Config per sursa:
        item  = 'div.news-item'  container repetat (obligatoriu)
        title = 'a.title'        ancora titlului (optional; implicit prima <a> din item)
        date  = 'span.date'      elementul cu data (optional)
    Depth-tracking pe container: div-urile imbricate NU inchid prematur item-ul, iar
    elementele void (<img>, <br>) nu strica numaratoarea de adancime.
    """

    def __init__(self, base_url: str, item: str, title: str | None = None, date: str | None = None):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url.rstrip("/")
        self._item = _sel(item)
        self._title = _sel(title) if title else None
        self._date = _sel(date) if date else None
        self.items: list[dict] = []
        self._depth = 0
        self._item_at: int | None = None
        self._title_at: int | None = None
        self._date_at: int | None = None
        self._anchor_at: int | None = None
        self._cur: dict = {}

    @staticmethod
    def _match(tag: str, classes: list, want: tuple) -> bool:
        want_tag, want_cls = want
        if want_tag and tag != want_tag:
            return False
        if want_cls and want_cls not in classes:
            return False
        return True

    def handle_startendtag(self, tag, attrs):   # <img/> — nu modifica adancimea
        pass

    def handle_starttag(self, tag, attrs):
        if tag in _VOID_TAGS:
            return
        ad = dict(attrs)
        classes = (ad.get("class") or "").split()
        self._depth += 1

        if self._item_at is None:
            if self._match(tag, classes, self._item):
                self._item_at = self._depth
                self._cur = {}
            return

        if self._title and self._title_at is None and self._match(tag, classes, self._title):
            self._title_at = self._depth
        if self._date and self._date_at is None and self._match(tag, classes, self._date):
            self._date_at = self._depth

        if tag == "a" and "href" in ad and "href" not in self._cur:
            take = self._title_at is not None if self._title else True
            if take:
                href = ad["href"].strip()
                if href.startswith("/"):
                    href = self.base_url + href
                self._cur["href"] = href
                self._anchor_at = self._depth

    def handle_data(self, data):
        if self._item_at is None:
            return
        text = data.strip()
        if not text:
            return
        in_title = self._title_at is not None if self._title else self._anchor_at is not None
        if in_title:
            self._cur["title"] = (self._cur.get("title", "") + " " + text).strip()
        if self._date_at is not None:
            self._cur["date_raw"] = (self._cur.get("date_raw", "") + " " + text).strip()

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS:
            return
        if self._anchor_at is not None and self._depth <= self._anchor_at:
            self._anchor_at = None
        if self._title_at is not None and self._depth <= self._title_at:
            self._title_at = None
        if self._date_at is not None and self._depth <= self._date_at:
            self._date_at = None
        if self._item_at is not None and self._depth <= self._item_at:
            if self._cur.get("href") and self._cur.get("title"):
                self.items.append(dict(self._cur))
            self._item_at = None
            self._cur = {}
        self._depth -= 1


def _fetch_html_list(key: str, source: dict) -> tuple[list, str | None]:
    """Scraper generic pentru o lista de anunturi HTML (surse fara RSS). Legal: pagina publica."""
    items: list = []
    try:
        req = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, ValueError) as exc:
        return items, f"{key}: {exc}"

    parser = _GenericListParser(source["base_url"], source["item"],
                                source.get("title"), source.get("date"))
    parser.feed(raw)
    if not parser.items:
        return items, f"{key}: 0 articole extrase (posibil structura HTML schimbata)"

    for entry in parser.items[: config.MAX_PER_SOURCE]:
        link = entry["href"]
        title = clean_html(entry["title"])
        if not link or not title or _is_agency(link, source["name"]):
            continue
        items.append({
            "url": normalize_url(link),
            "original_link": link,
            "source": key,
            "source_name": source["name"],
            "source_lang": source.get("lang", "ro"),
            "original_title": title,
            "title": title,
            "description": "",          # descrierea o genereaza AI din titlu
            "category": source["category"],
            "published": _parse_ro_date(entry.get("date_raw", "")),
            "model": None,
        })
    return items, None


def _fetch_one(key: str, source: dict, cache: dict | None = None) -> tuple[list, str | None]:
    """Returneaza (articole, eroare). Alege metoda de fetch in functie de tipul sursei."""
    if source.get("type") == "html_scraper":
        return _fetch_html_scraper(key, source)
    if source.get("type") == "html_list":
        return _fetch_html_list(key, source)

    items = []
    headers = {"User-Agent": USER_AGENT}
    ent = (cache or {}).get(key) or {}
    if _cache_fresh(ent):
        if ent.get("etag"):
            headers["If-None-Match"] = ent["etag"]
        if ent.get("last_modified"):
            headers["If-Modified-Since"] = ent["last_modified"]
    try:
        req = urllib.request.Request(source["url"], headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            if cache is not None:
                cache[key] = {
                    "etag": resp.headers.get("ETag"),
                    "last_modified": resp.headers.get("Last-Modified"),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return items, None   # feed neschimbat -> nimic nou, sursa e sanatoasa
        return items, f"{key}: {exc}"
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
            "source_lang": source.get("lang", "ro"),
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
    cache = _cache_load()
    for key, source in config.SOURCES.items():
        items, err = _fetch_one(key, source, cache)
        if err:
            dead.append(err)
        all_items.extend(items)
    _cache_save(cache)
    return all_items, dead
