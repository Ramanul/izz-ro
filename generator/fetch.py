"""Citire RSS robusta (Atom-safe) + filtru de agentii de presa + scraper HTML pentru surse fara RSS."""
import json
import os
import re
import socket
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser

import feedparser

from . import config
from .util import normalize_url, domain_of, clean_html

USER_AGENT = "IZZ.ro Bot/1.0 (+https://izz.ro)"
TIMEOUT = 10  # secunde per feed
# Fetch-ul e I/O-bound: threadurile asteapta reteaua, nu CPU-ul. 8 e conservator
# fata de ~40+ surse; FETCH_WORKERS=1 revine la secvential.
MAX_WORKERS = int(os.environ.get("FETCH_WORKERS", "8"))

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


# ---- Sitemap Google News: fetch legal pentru surse fara RSS (ex. piataauto.md) ----
# Multe publicatii NU expun RSS, dar publica un sitemap Google News (declarat in
# robots.txt, destinat indexarii) cu exact ce ne trebuie: <loc> + news:title +
# news:publication_date. Preferat fata de scraping HTML: XML curat si stabil, fara
# JS/Cloudflare, si 100% legal (robots.txt Allow + doar titlu+link+data, link catre sursa).
_SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}


def _parse_w3c_date(raw: str) -> str:
    """news:publication_date (W3C: 'YYYY-MM-DD' sau ISO 8601 datetime) -> ISO 8601 UTC."""
    raw = (raw or "").strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):     # doar data -> miezul noptii UTC
            d = datetime.strptime(raw, "%Y-%m-%d")
            return d.replace(tzinfo=timezone.utc).isoformat()
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _fetch_sitemap_news(key: str, source: dict) -> tuple[list, str | None]:
    """Fetch dintr-un sitemap Google News: Title + URL + data. Legal (robots.txt: Allow /)."""
    items: list = []
    try:
        req = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, ValueError) as exc:
        return items, f"{key}: {exc}"

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        return items, f"{key}: XML invalid ({exc})"

    urls = root.findall("sm:url", _SITEMAP_NS)
    if not urls:
        return items, f"{key}: 0 intrari in sitemap (posibil structura schimbata)"

    for url_el in urls[: config.MAX_PER_SOURCE]:
        loc = (url_el.findtext("sm:loc", default="", namespaces=_SITEMAP_NS) or "").strip()
        title = clean_html(
            url_el.findtext("news:news/news:title", default="", namespaces=_SITEMAP_NS) or "")
        date_raw = url_el.findtext("news:news/news:publication_date", default="",
                                   namespaces=_SITEMAP_NS)
        if not loc or not title or _is_agency(loc, source["name"]):
            continue
        items.append({
            "url": normalize_url(loc),
            "original_link": loc,
            "source": key,
            "source_name": source["name"],
            "source_lang": source.get("lang", "ro"),
            "original_title": title,
            "title": title,
            "description": "",          # descrierea va fi generata de AI din titlu
            "category": source["category"],
            "published": _parse_w3c_date(date_raw),
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
    if source.get("type") == "sitemap_news":
        return _fetch_sitemap_news(key, source)
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
    """Returneaza (toate_articolele_brute, surse_moarte).

    Fetch-ul e paralel (I/O-bound: fiecare sursa asteapta reteaua).

    Doua invariante pe care paralelizarea NU are voie sa le strice:

    1. ORDINEA. Bugetul AI proceseaza articolele in ordinea din config.SOURCES;
       ce ajunge la coada e infometat. `executor.map` returneaza rezultatele in
       ordinea intrarii, indiferent de ordinea in care se termina taskurile, deci
       ordinea finala e identica cu varianta secventiala.
    2. CACHE-UL. Fiecare task citeste si scrie DOAR `cache[key]`-ul lui, iar
       atribuirea pe dict e atomica sub GIL. Nu e nevoie de lock.

    FETCH_WORKERS=1 forteaza modul secvential (depanare, sau daca o sursa se
    supara pe cereri concurente).
    """
    all_items, dead = [], []
    cache = _cache_load()
    sources = list(config.SOURCES.items())

    if MAX_WORKERS <= 1:
        results = [_fetch_one(key, source, cache) for key, source in sources]
    else:
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(sources) or 1)) as pool:
            results = list(pool.map(lambda kv: _fetch_one(kv[0], kv[1], cache), sources))

    for items, err in results:
        if err:
            dead.append(err)
        all_items.extend(items)

    _cache_save(cache)
    return all_items, dead
