"""Citire RSS robusta (Atom-safe) + filtru de agentii de presa + scraper HTML pentru surse fara RSS."""
import collections
import json
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.request
import defusedxml.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from defusedxml.common import DefusedXmlException
from datetime import datetime, timezone

# Cate intrari brute sunt aruncate la INGESTIE, si de ce. Pana la 2026-09-02 nimeni nu stia:
# `main.py` numara ce se pierde DUPA fetch (`stale_skipped`, `deferred`, itemele fara
# substanta), dar ce nu intra niciodata in pipeline era invizibil prin constructie — un item
# sarit nu apare pe site, nu apare in `articles.json` si nu apare in log.
#
# Sect. 7 PRESCRIE pierderea tacuta („SARE itemul"), deci contorul nu o schimba: o face
# numarabila. Cifra care intereseaza cel mai mult e „garda de continut ostil" — pana acum
# nimeni nu putea spune cate articole respinge `guard` intr-o rulare reala.
_SARITE = collections.Counter()


def pierderi_ingestie() -> dict:
    """Ce s-a aruncat la ingestie in rularea curenta. Se citeste din `main.py`, la final."""
    return dict(_SARITE)

from html.parser import HTMLParser
from urllib.parse import urljoin

import feedparser

from . import config, guard
from .util import normalize_url, domain_of, clean_html, cuvinte_adaugate

USER_AGENT = "IZZ.ro Bot/1.0 (+https://izz.ro)"
TIMEOUT = 10  # secunde per feed
SITEMAP_ARTICLE_TIMEOUT = float(os.environ.get("SITEMAP_ARTICLE_TIMEOUT", "6"))


class _MetaDescriptionParser(HTMLParser):
    """Extrage doar meta description dintr-o pagină editorială, fără scraping de navigație."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.description = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta" or self.description:
            return
        fields = {str(key).lower(): str(value or "") for key, value in attrs}
        name = fields.get("name", "").lower()
        prop = fields.get("property", "").lower()
        if name == "description" or prop == "og:description":
            self.description = clean_html(fields.get("content", ""))


def _fetch_meta_description(url: str) -> str:
    """Fetch bounded metadata; failure means the item remains safely unprocessed."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=SITEMAP_ARTICLE_TIMEOUT) as response:
            raw = response.read(min(MAX_RESPONSE_BYTES, 512 * 1024))
        parser = _MetaDescriptionParser()
        parser.feed(raw.decode("utf-8", errors="replace"))
        return parser.description
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, ValueError, OSError):
        return ""

# Plafon de raspuns. `resp.read()` fara argument citeste CAT TRIMITE serverul: o sursa
# compromisa poate servi gigaocteti si omoara runnerul de CI prin memorie, nu prin continut.
# Cifra e MASURATA, nu aleasa (R3 din specs/securitate-ingestie.md): pe un esantion de 7
# feeduri reale, cel mai mare a fost 198 139 B (unica.ro), median ~25 kB. 8 MiB = ~40x peste
# maximul observat, deci un feed legitim nu-l atinge nici daca isi dubleaza de cinci ori
# volumul, iar memoria ramane marginita.
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def _read_limitat(resp) -> bytes:
    """`resp.read()` cu plafon. Peste plafon ARUNCA, nu trunchiaza.

    Trunchierea tacuta ar da un XML rupt pe care parserul l-ar raporta ca „sursa stricata",
    adica exact diagnosticul gresit. `ValueError` e deja prins de toti apelantii si devine
    o eroare normala de sursa, logata pe nume.
    """
    raw = resp.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError(f"raspuns peste plafonul de {MAX_RESPONSE_BYTES} B")
    return raw


# Fetch-ul e I/O-bound: threadurile asteapta reteaua, nu CPU-ul. 8 e conservator
# fata de ~40+ surse; FETCH_WORKERS=1 revine la secvential.
MAX_WORKERS = int(os.environ.get("FETCH_WORKERS", "8"))
# Plafon pentru fereastra paralela. Daca unele hosturi nu inchid conexiunea, nu lasam
# executorul sa astepte la nesfarsit toate threadurile. Taskurile neterminate devin surse
# moarte pentru aceasta rulare si pot fi reverificate ulterior.
FETCH_BATCH_TIMEOUT_S = float(os.environ.get("FETCH_BATCH_TIMEOUT_S", "90"))
# Deadline pentru intreaga ingestie, nu doar pentru o fereastra paralela. Zero dezactiveaza
# limita globala (util pentru depanare), dar valoarea implicita protejeaza rularea reala.
FETCH_GLOBAL_DEADLINE_S = float(os.environ.get("FETCH_GLOBAL_DEADLINE_S", "300"))
FETCH_PROGRESS_EVERY = max(1, int(os.environ.get("FETCH_PROGRESS_EVERY", "10")))

# Retry pe refuzuri tranzitorii. Feedcheck-ul din 2026-07-24 (run 30093310671) a prins
# 429 pe libertatea, unica si bzi de pe runnerii GitHub — iar build.yml ruleaza pe aceiasi
# runneri, deci productia chiar pierdea sursele alea la prima incercare.
RETRY_STATUSES = (429, 503)
RETRY_ATTEMPTS = 2               # incercari SUPLIMENTARE, peste prima
RETRY_BACKOFF = (1, 3)           # secunde, per incercare esuata
RETRY_AFTER_CAP = 15             # peste atat nu asteptam: un host lent ar bloca un worker

# Conditional GET (ETag / Last-Modified): nu re-descarcam feed-uri neschimbate.
# Valabilitate limitata la 3h: mecanismul de defer (iteme amanate la 429 AI) se
# bazeaza pe re-fetch pentru retry -- un 304 onorat la nesfarsit pe un feed lent
# ar bloca reincercarea. Cache-ul e comis in repo (rularile CI sunt stateless).
CACHE_PATH = os.path.join(config.ROOT, "data", "feed_cache.json")
CACHE_MAX_AGE_H = 3

# Interstitial anti-bot servit cu HTTP 200 de furnizorul de gazduire al multor primarii.
# Masurat 2026-08-02 pe runnerii GitHub: dintr-o matura de 189 de surse, 66 din cele 68
# servite de `openresty` l-au primit, fata de 0/24 LiteSpeed si 0/19 nginx. Are corp HTML
# valid, deci nici statusul nici feedparser nu-l semnaleaza — fara marca asta ajunge in
# `dead` etichetat "feed gol", ceea ce ar duce pe cineva sa scoata din config surse bune.
# NU se rezolva prin reincercare: masurat pe 40 de surse, 40/40 au primit acelasi
# interstitial si dupa o pauza de 6 s (pagina isi cere singura reload la 5 s).
CHALLENGE_MARK = b"One moment, please"

# Ritmul cu care lovim un singur furnizor de gazduire. Masurat 2026-08-02, matura de 189 de
# surse de pe un runner GitHub: 66 din cele 68 servite de `openresty` au primit challenge,
# fata de 0/24 LiteSpeed si 0/19 nginx. Cele 66 de domenii rezolva la IP-uri DIFERITE, deci
# nu se poate distanta nici per hostname, nici per IP — singurul lucru care identifica
# furnizorul e antetul `Server`, pe care il aflam abia din raspuns, deci din rularea trecuta.
# Grupurile mici nu sunt problema si nu se incetinesc.
PACE_INTERVAL_S = float(os.environ.get("FETCH_PACE_S", "2.0"))
PACE_GROUP_MIN = int(os.environ.get("FETCH_PACE_GROUP_MIN", "10"))


def _is_challenge(body: bytes | str) -> bool:
    """True daca raspunsul e interstitialul anti-bot, nu continut.

    Accepta si `str`, pentru ca `_fetch_html_list` decodeaza corpul inainte de a-l parsa.
    Se uita doar in antetul corpului: un articol care citeaza fraza nu e un challenge.
    """
    head = body[:4000]
    if isinstance(head, str):
        head = head.encode("utf-8", errors="replace")
    return CHALLENGE_MARK in head


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

# Octetii pe care XML 1.0 ii interzice in continut (vezi `_curata_control`).
_CONTROL_RE = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _parse_w3c_date(raw: str) -> str:
    """news:publication_date (W3C: 'YYYY-MM-DD' sau ISO 8601 datetime) -> ISO 8601 UTC."""
    raw = (raw or "").strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):     # doar data -> miezul noptii UTC
            # Intr-o singura instructiune intentionat: despartita in doua, `ruff` raporteaza
            # DTZ007 („strptime fara %z") fiindca nu vede `.replace(tzinfo=...)` de peste
            # legatura `d`. Invariantul UTC era deja respectat — asta e o reformulare cu zero
            # schimbare de comportament, care in plus face marcarea UTC vizibila la fata locului.
            return datetime.strptime(raw, "%Y-%m-%d").replace(
                tzinfo=timezone.utc).isoformat()
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _curata_control(raw: bytes) -> bytes:
    """Scoate octetii de control pe care XML 1.0 ii interzice, ca un singur caracter stricat
    sa nu transforme o sursa vie in „sursa moarta".

    PREVENTIV, nu reparativ — spus explicit ca sa nu para masurat. Ce s-a masurat: la
    2026-08-06, o descarcare a fiecareia din cele doua surse `sitemap_news` (`monitorulsv`,
    `piataauto`) a dat 0 octeti de control si a parsat curat. Atat. UN esantion, la UN moment,
    nu poate distinge „nu se intampla" de „se intampla rar" — un document stricat aparut o
    data pe luna ar arata identic in verificarea aia. Deci nu se poate scrie ca sursele sunt
    curate, doar ca nu am prins nimic.

    Ce justifica cele cinci linii nu e frecventa, ci consecinta: `ET.fromstring` respinge TOT
    documentul la primul `\\x0c` (verificat: `not well-formed (invalid token)`), iar sursa ar
    aparea in `dead` — adica exact clasa de verdict fals care a tinut `ziaruldeiasi` marcat
    DEAD de 15 ori si era cat pe ce sa-l scoata din config.

    Calea RSS nu are problema asta: feedparser recupereaza si din XML bozo (vezi comentariul
    `gazetadecluj` din config). Calea `sitemap_news` merge direct la stdlib, deci era singura
    descoperita.

    Valide in XML 1.0: #x9, #xA, #xD si tot ce e >= #x20. Se filtreaza deci exact
    #x00-#x08, #x0B, #x0C, #x0E-#x1F.

    Se lucreaza pe OCTETI, nu pe text decodat, ca sa nu pierdem declaratia de encoding pe care
    `ET.fromstring` o citeste singur din prolog. E corect pentru orice encoding
    ASCII-compatibil (UTF-8, ISO-8859-*, windows-1252): acolo octetii de continuare sunt
    >= #x80, deci nu pot fi confundati cu un control. UTF-16 e exceptia — acolo #x00 e un
    octet legitim din fiecare caracter ASCII — si de aceea documentele cu BOM UTF-16 se lasa
    NEATINSE; sitemaps.org cere oricum UTF-8, dar a strica un document valid ar fi mai rau
    decat a nu repara unul stricat.
    """
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw
    return _CONTROL_RE.sub(b"", raw)


def _parse_sitemap_news(raw: bytes, key: str, source: dict) -> tuple[list, str | None]:
    """XML sitemap -> (articole, eroare). Pur (fara retea), ca sa fie testabil pe fixture."""
    items: list = []
    try:
        root = ET.fromstring(_curata_control(raw))
    # `DefusedXmlException` NU e subclasa de `ParseError` (verificat: mro-ul ei trece prin
    # ValueError, nu prin ParseError), deci un `except ParseError` singur ar lasa un sitemap
    # cu entitati sa OMOARE procesul in loc sa marcheze sursa cu eroare — adica fix invers
    # decat scopul intaririi. Se prind impreuna, dar mesajul le DISTINGE: „invalid" si
    # „respins" sunt diagnostice diferite (unul e sursa stricata, celalalt e politica
    # noastra), iar cine citeste raportul de surse trebuie sa stie pe care din ele o repara.
    except (ET.ParseError, DefusedXmlException) as exc:
        cum = "respins" if isinstance(exc, DefusedXmlException) else "invalid"
        return items, f"{key}: XML {cum} ({type(exc).__name__}: {exc})"

    urls = root.findall("sm:url", _SITEMAP_NS)
    if not urls:
        return items, f"{key}: 0 intrari in sitemap (posibil structura schimbata)"

    # plafonul se aplica dupa filtrare (nu pe felia bruta): daca primele intrari sunt
    # inutilizabile, sursa nu trebuie sa iasa goala cat timp exista intrari bune mai jos.
    unusable = 0
    respinse = 0
    for url_el in urls:
        if len(items) >= config.MAX_PER_SOURCE:
            break
        loc = (url_el.findtext("sm:loc", default="", namespaces=_SITEMAP_NS) or "").strip()
        title = clean_html(
            url_el.findtext("news:news/news:title", default="", namespaces=_SITEMAP_NS) or "")
        date_raw = url_el.findtext("news:news/news:publication_date", default="",
                                   namespaces=_SITEMAP_NS)
        if not loc or not title:
            unusable += 1
            _SARITE["item incomplet (fara link sau titlu)"] += 1
            continue
        resolved_loc = urljoin(source.get("url", ""), loc)
        if _is_agency(resolved_loc, source["name"]):
            _SARITE["agentie de presa (exclusa deliberat)"] += 1
            continue
        motiv = (guard.verdict(title) or guard.url_ostil(resolved_loc)
                 or guard.anomalie(title, source.get("lang", "ro")))
        if motiv:
            respinse += 1
            print(f"   !! garda ingestie (sitemap): sar [{key}] {title[:60]!r} — {motiv}")
            _SARITE["garda de continut ostil"] += 1
            continue
        items.append({
            "url": normalize_url(resolved_loc),
            "original_link": resolved_loc,
            "source": key,
            "source_name": source["name"],
            "source_lang": source.get("lang", "ro"),
            "original_title": title,
            "title": title,
            "description": "",
            "category": source["category"],
            "published": _parse_w3c_date(date_raw),
            "model": None,
        })

    if (motiv := guard.carantina(respinse, respinse + len(items), key)):
        print(f"   !! {motiv}")
        return [], motiv

    if not items:
        # esec TACUT altfel: sursa raspunde 200 si are <url>-uri, dar nu produce nimic
        # -> nu aparea in lista surselor moarte si degrada nevazut (piataauto, iulie 2026).
        return items, (f"{key}: {len(urls)} intrari in sitemap, 0 utilizabile "
                       f"({unusable} fara loc/news:title -> namespace sau structura schimbata)")
    return items, None


def _fetch_sitemap_news(key: str, source: dict) -> tuple[list, str | None]:
    """Fetch dintr-un sitemap Google News: Title + URL + data. Legal (robots.txt: Allow /)."""
    try:
        req = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = _read_limitat(resp)
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, ValueError) as exc:
        return [], f"{key}: {exc}"
    items, error = _parse_sitemap_news(raw, key, source)
    if source.get("enrich_sitemap") and not error:
        for item in items:
            item["description"] = _fetch_meta_description(item["original_link"])
    return items, error


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
        self._fallback_href: str | None = None  # primul href din item, folosit doar daca titlul
                                                  # e imbricat in ACEEASI ancora (un singur <a>
                                                  # care invaluie tot cardul) -- fara asta href-ul
                                                  # nu se prinde niciodata, fiindca conditia de mai
                                                  # jos cere title_at deja setat inainte de <a>.

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
                # containerul e chiar ancora <a>: nu mai iesim, ca sa se extraga href-ul
                # in blocul de mai jos (altfel link-ul e pierdut definitiv pentru acest item)
                if tag != "a":
                    return
            else:
                return

        if self._title and self._title_at is None and self._match(tag, classes, self._title):
            self._title_at = self._depth
        if self._date and self._date_at is None and self._match(tag, classes, self._date):
            self._date_at = self._depth

        if tag == "a" and "href" in ad and "href" not in self._cur:
            href = ad["href"].strip()
            if href.startswith("/"):
                href = self.base_url + href
            if self._fallback_href is None:
                self._fallback_href = href
            take = self._title_at is not None if self._title else True
            if take:
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
            href = self._cur.get("href") or self._fallback_href
            if href and self._cur.get("title"):
                self._cur["href"] = href
                self.items.append(dict(self._cur))
            self._item_at = None
            self._cur = {}
            self._fallback_href = None
        self._depth -= 1


def _fetch_html_list(key: str, source: dict) -> tuple[list, str | None]:
    """Scraper generic pentru o lista de anunturi HTML (surse fara RSS). Legal: pagina publica."""
    try:
        req = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = _read_limitat(resp).decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, ValueError) as exc:
        return [], f"{key}: {exc}"
    return _items_from_html(raw, key, source)


def _fetch_html_list_js(key: str, source: dict) -> tuple[list, str | None]:
    """Ca `_fetch_html_list`, dar randeaza pagina intr-un Chromium headless (crawl4ai/Playwright)
    inainte de a o parsa cu acelasi `_GenericListParser`.

    Exista pentru site-urile primariilor care isi construiesc lista de anunturi in JavaScript
    (Next.js/React) — `urllib` primeste doar bundle-ul JS gol, 0 articole. Confirmat 2026-08-12
    pe primariatm.ro/noutati: urllib -> 0 linkuri utile (raspunsul e un shell Next.js), crawl4ai
    cu 3s de asteptare dupa incarcare -> 12 anunturi reale, cu titlu/link/data.

    Optional: cere `crawl4ai` (si browserul Playwright descarcat de `crawl4ai-setup`), NEINCLUS
    in requirements.txt ca sa nu impinga un download de ~200MB in fiecare build CI (vezi §17,
    bugetul de build). Instalare LOCALA: `pip install crawl4ai && crawl4ai-setup`. Fara pachet,
    orice sursa `html_list_js` esueaza curat (eroare de sursa, nu crash de pipeline).
    """
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        return [], f"{key}: crawl4ai neinstalat (optional, doar local — vezi docstring _fetch_html_list_js)"

    import asyncio

    async def _render():
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=source["url"], page_timeout=30000, delay_before_return_html=3.0)
            return result

    try:
        result = asyncio.run(_render())
    except Exception as exc:  # crawl4ai/Playwright pot arunca o gama larga (timeout, browser crash)
        return [], f"{key}: crawl4ai {type(exc).__name__}: {exc}"
    if not result.success:
        return [], f"{key}: crawl4ai a esuat (status {result.status_code})"
    return _items_from_html(result.html, key, source)


def _items_from_html(raw: str, key: str, source: dict) -> tuple[list, str | None]:
    """Parseaza HTML-ul (deja descarcat, deja randat daca era nevoie) cu `_GenericListParser`
    si aplica garda de ingestie -- pas comun intre `_fetch_html_list` si `_fetch_html_list_js`."""
    items: list = []
    parser = _GenericListParser(source["base_url"], source["item"],
                                source.get("title"), source.get("date"))
    parser.feed(raw)
    if not parser.items:
        if _is_challenge(raw):
            return items, f"{key}: challenge anti-bot servit cu 200 (sursa NU e moarta)"
        return items, f"{key}: 0 articole extrase (posibil structura HTML schimbata)"

    respinse = 0
    for entry in parser.items[: config.MAX_PER_SOURCE]:
        link = entry["href"]
        title = clean_html(entry["title"])
        if not link or not title:
            _SARITE["item incomplet (fara link sau titlu)"] += 1
            continue
        if _is_agency(link, source["name"]):
            _SARITE["agentie de presa (exclusa deliberat)"] += 1
            continue
        motiv = (guard.verdict(title) or guard.url_ostil(link)
                 or guard.anomalie(title, source.get("lang", "ro")))
        if motiv:
            respinse += 1
            print(f"   !! garda ingestie (lista HTML): sar [{key}] {title[:60]!r} — {motiv}")
            _SARITE["garda de continut ostil"] += 1
            continue
        items.append({
            "url": normalize_url(link),
            "original_link": link,
            "source": key,
            "source_name": source["name"],
            "source_lang": source.get("lang", "ro"),
            "original_title": title,
            "title": title,
            "description": "",          # lista HTML nu poarta descriere: itemul ramane fara
                                        # substanta si e oprit inainte de AI (config.
                                        # MIN_SUBSTANTA_CUVINTE). NU se genereaza din titlu.
            "category": source["category"],
            "published": _parse_ro_date(entry.get("date_raw", "")),
            "model": None,
        })
    if (motiv := guard.carantina(respinse, respinse + len(items), key)):
        print(f"   !! {motiv}")
        return [], motiv

    if not items:
        # Acelasi esec tacut ca la RSS si la sitemap: 200, zero articole, invizibil in rapoarte.
        return items, f"{key}: 200 dar 0 articole din lista HTML (selector schimbat sau pagina goala)"
    return items, None


def _retry_delay(exc: urllib.error.HTTPError, attempt: int) -> float | None:
    """Cate secunde asteptam inainte de a reincerca, sau None daca renuntam.

    Renuntam cand: statusul nu e tranzitoriu, am epuizat incercarile, sau serverul cere
    prin `Retry-After` mai mult decat `RETRY_AFTER_CAP` — mai bine o sursa moarta la runda
    asta decat un worker blocat, mai ales ca fetch-ul e paralel.
    """
    if exc.code not in RETRY_STATUSES or attempt >= RETRY_ATTEMPTS:
        return None
    after = exc.headers.get("Retry-After") if exc.headers else None
    if after:
        try:
            secs = float(str(after).strip())
        except (TypeError, ValueError):
            secs = None          # forma HTTP-date: ignoram, cadem pe backoff-ul nostru
        if secs is not None:
            return None if secs > RETRY_AFTER_CAP else max(secs, 0.0)
    return RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]


def _entry_body(entry) -> str:
    """Textul cel mai bogat pe care il trimite feedul, curatat de HTML.

    `feedparser` pune `<content:encoded>` in `entry.content[0].value`, NU in `summary`. Pana la
    2026-08-04 se citea doar `summary`/`description`, deci corpul se pierdea la sursele care il
    trimit acolo — un defect de FETCH raportat pana acum ca defect de SURSA. Masurat pe feeduri
    live, DUPA curatare (14 surse x 8 iteme): 27 din 111 iteme trec pragul de substanta care
    inainte le respingea, 84 raman fara corp. Castigul e concentrat: `pl_neamt_municipiul_roman`
    sare de la `summary` gol la o mediana de 112 cuvinte peste titlu. Contra-verificat pe
    `digisport`, unde `content` exista pe toate itemele dar nu adauga niciun caracter peste
    `summary`: acolo sursa chiar nu trimite nimic, si asta ramane un defect de sursa, nu de fetch.

    Cel mai lung candidat DUPA `clean_html`, nu inainte: un `content` plin de markup poate curata
    mai scurt decat un `summary` de text simplu, iar comparatia pe HTML brut ar alege atunci
    varianta mai saraca. `summary` ramane candidat, deci nicio sursa nu poate pierde ce avea.
    """
    raw = [c.get("value") or "" for c in (entry.get("content") or []) if isinstance(c, dict)]
    raw += [entry.get("summary") or "", entry.get("description") or ""]
    return max((clean_html(t) for t in raw), key=len, default="")


def _fetch_one(key: str, source: dict, cache: dict | None = None) -> tuple[list, str | None]:
    """Returneaza (articole, eroare). Alege metoda de fetch in functie de tipul sursei."""
    if source.get("type") == "sitemap_news":
        return _fetch_sitemap_news(key, source)
    if source.get("type") == "html_list":
        return _fetch_html_list(key, source)
    if source.get("type") == "html_list_js":
        return _fetch_html_list_js(key, source)

    items = []
    headers = {"User-Agent": USER_AGENT}
    ent = (cache or {}).get(key) or {}
    if _cache_fresh(ent):
        if ent.get("etag"):
            headers["If-None-Match"] = ent["etag"]
        if ent.get("last_modified"):
            headers["If-Modified-Since"] = ent["last_modified"]
    raw = None
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(source["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = _read_limitat(resp)
                if cache is not None:
                    cache[key] = {
                        "etag": resp.headers.get("ETag"),
                        "last_modified": resp.headers.get("Last-Modified"),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        # Cheia de grupare pentru `_HostPacer`. Se salveaza si cand
                        # raspunsul a fost un challenge: antetul e tot al furnizorului,
                        # deci sursa intra in grupul corect chiar din runda in care a picat.
                        "server": resp.headers.get("Server"),
                    }
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                return items, None   # feed neschimbat -> nimic nou, sursa e sanatoasa
            delay = _retry_delay(exc, attempt)
            if delay is None:
                return items, f"{key}: {exc}"
            time.sleep(delay)
        except (urllib.error.URLError, socket.timeout, ValueError) as exc:
            return items, f"{key}: {exc}"

    if raw is None:   # garda: bucla iese doar prin break/return, dar RETRY_ATTEMPTS e tunabil
        return items, f"{key}: fetch esuat dupa {RETRY_ATTEMPTS + 1} incercari"

    feed = feedparser.parse(raw)
    respinse = 0
    for entry in feed.entries[: config.MAX_PER_SOURCE]:
        link = entry.get("link", "").strip()
        title = clean_html(entry.get("title") or "")
        if not link or not title:
            _SARITE["item incomplet (fara link sau titlu)"] += 1
            continue
        if _is_agency(link, source["name"]):
            _SARITE["agentie de presa (exclusa deliberat)"] += 1
            continue
        body = _entry_body(entry)
        # Garda de continut ostil: o sursa poate fi compromisa fara sa stim (vezi guard.py).
        # Se respinge itemul, nu se incearca reparatia — §7 „SARE itemul".
        motiv = (guard.verdict(title, body) or guard.url_ostil(link)
                 or guard.anomalie(title, source.get("lang", "ro")))
        if motiv:
            respinse += 1
            print(f"   !! garda ingestie: sar [{key}] {title[:60]!r} — {motiv}")
            _SARITE["garda de continut ostil"] += 1
            continue
        items.append({
            "url": normalize_url(link),
            "original_link": link,
            "source": key,
            "source_name": source["name"],
            "source_lang": source.get("lang", "ro"),
            "original_title": title,
            "title": title,
            "description": body,
            "category": source["category"],
            "published": _parse_date(entry),
            "model": None,
        })
    if (motiv := guard.carantina(respinse, respinse + len(items), key)):
        print(f"   !! {motiv}")
        return [], motiv

    if not items:
        # Esec TACUT altfel, aceeasi clasa ca la sitemap mai sus: sursa raspunde 200, iar
        # `dead` aduna DOAR erori, deci un feed care nu produce nimic nu aparea nicaieri.
        # Masurat 2026-08-02: 76 de surse ies goale de pe IP-urile runnerilor GitHub, iar
        # aceleasi surse dau 8 articole fiecare de pe IP de acasa — productia citeste ~861
        # articole unde o rulare locala citeste ~1428, si nimic din diferenta asta nu se
        # vedea in vreun raport.
        # Un 304 NU trece pe aici: iese mai sus, pentru ca „feed neschimbat" e sanatos.
        if _is_challenge(raw):
            # Sursa e vie; gazda ei ne-a servit un challenge in loc de feed. Eticheta
            # separata conteaza: "feed gol" ar invita la stergerea sursei din config.
            return items, f"{key}: challenge anti-bot servit cu 200 (sursa NU e moarta)"
        motiv = "feed gol" if not feed.entries else "intrari fara link/titlu, sau filtrate"
        if getattr(feed, "bozo", 0):
            motiv += f"; parser: {type(feed.get('bozo_exception')).__name__}"
        return items, f"{key}: 200 dar 0 articole din {len(feed.entries)} intrari ({motiv})"
    return items, None


def _server_sig(entry: dict) -> str | None:
    """Semnatura furnizorului dintr-o intrare de cache: `openresty/1.31.1.1` -> `openresty`.

    Versiunea se taie intentionat: acelasi furnizor ruleaza build-uri diferite pe masini
    diferite (masurat: `openresty/1.31.1.1` pe 67 de surse si `openresty/1.29.2.3` pe una),
    iar cota e a furnizorului, nu a build-ului.
    """
    srv = (entry or {}).get("server")
    return srv.split("/")[0].strip().lower() or None if srv else None


class _HostPacer:
    """Impune un interval minim intre cererile care impart acelasi furnizor.

    Nu incetineste nimic pe prima rulare de dupa deploy: semnaturile se invata din antetul
    `Server` salvat in cache, iar pana atunci fiecare sursa e in propriul grup de marime 1.
    Se auto-corecteaza de la a doua rulare.
    """

    def __init__(self, cache: dict, interval: float = PACE_INTERVAL_S,
                 group_min: int = PACE_GROUP_MIN):
        self._interval = interval
        self._lock = threading.Lock()
        self._next_free: dict[str, float] = {}
        sizes: dict[str, int] = {}
        for ent in (cache or {}).values():
            sig = _server_sig(ent)
            if sig:
                sizes[sig] = sizes.get(sig, 0) + 1
        # Doar grupurile mari sunt cele care declanseaza limitarea; restul trec liber.
        self._paced = {sig for sig, n in sizes.items() if n >= group_min}

    def wait(self, key: str, cache: dict | None) -> None:
        sig = _server_sig((cache or {}).get(key) or {})
        if not sig or sig not in self._paced or self._interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            due = max(now, self._next_free.get(sig, 0.0))
            self._next_free[sig] = due + self._interval
        delay = due - now
        if delay > 0:
            time.sleep(delay)


def _fetch_one_guarded(key: str, source: dict, cache: dict | None = None,
                       pacer: "_HostPacer | None" = None) -> tuple[list, str | None]:
    """`_fetch_one` care nu poate arunca: orice eroare devine sursa moarta.

    `_fetch_one` prinde doar erorile de retea; `feedparser.parse` si bucla de
    entries sunt in afara try-ului, deci un feed malformat poate arunca. In
    paralel asta e mai grav decat in secvential: `pool.map` re-ridica exceptia
    la iterarea rezultatelor, iar `_cache_save` nu se mai executa — tot fetch-ul
    (inclusiv sursele sanatoase) se pierde din cauza uneia singure.
    """
    try:
        if pacer is not None:
            pacer.wait(key, cache)
        return _fetch_one(key, source, cache)
    except Exception as exc:  # orice: o sursa stricata nu pica build-ul
        return [], f"{key}: {exc}"


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
    pacer = _HostPacer(cache)

    started = time.monotonic()

    def remaining_deadline() -> float | None:
        if FETCH_GLOBAL_DEADLINE_S <= 0:
            return None
        return max(0.0, FETCH_GLOBAL_DEADLINE_S - (time.monotonic() - started))

    def timeout_result(key: str) -> tuple[list, str]:
        return [], f"{key}: fetch global deadline dupa {FETCH_GLOBAL_DEADLINE_S:g}s"

    if MAX_WORKERS <= 1:
        results = []
        for idx, (key, source) in enumerate(sources, 1):
            remaining = remaining_deadline()
            if remaining is not None and remaining <= 0:
                results.extend(timeout_result(k) for k, _ in sources[idx - 1:])
                break
            results.append(_fetch_one_guarded(key, source, cache, pacer))
            if idx % FETCH_PROGRESS_EVERY == 0 or idx == len(sources):
                print(f"   fetch RSS: {idx}/{len(sources)} surse")
    else:
        ordered = [None] * len(sources)
        window_size = max(1, min(len(sources), MAX_WORKERS * 2))
        finished = 0
        for start in range(0, len(sources), window_size):
            remaining = remaining_deadline()
            if remaining is not None and remaining <= 0:
                for idx, (key, _source) in enumerate(sources[start:], start):
                    ordered[idx] = timeout_result(key)
                    finished += 1
                break

            window = sources[start:start + window_size]
            executor = ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(window)))
            futures = {
                executor.submit(_fetch_one_guarded, key, source, cache, pacer): (idx, key)
                for idx, (key, source) in enumerate(window, start)
            }
            try:
                window_timeout = FETCH_BATCH_TIMEOUT_S
                remaining = remaining_deadline()
                if remaining is not None:
                    window_timeout = min(window_timeout, remaining)
                for future in as_completed(futures, timeout=window_timeout):
                    idx, _key = futures[future]
                    ordered[idx] = future.result()
                    finished += 1
                    if finished % FETCH_PROGRESS_EVERY == 0 or finished == len(sources):
                        print(f"   fetch RSS: {finished}/{len(sources)} surse")
            except TimeoutError:
                for future, (idx, key) in futures.items():
                    if ordered[idx] is None:
                        future.cancel()
                        remaining = remaining_deadline()
                        if remaining is not None and remaining <= 0:
                            ordered[idx] = timeout_result(key)
                        else:
                            ordered[idx] = (
                                [], f"{key}: fetch batch timeout dupa {FETCH_BATCH_TIMEOUT_S:g}s"
                            )
                        finished += 1
            except KeyboardInterrupt:
                for future in futures:
                    future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                raise
            finally:
                # Nu folosim context managerul: __exit__ ar astepta threadurile blocate,
                # anuland tocmai protectia de timeout. Taskurile deja intrate in urllib
                # se termina singure la TIMEOUT; rezultatul rularii ramane determinist.
                executor.shutdown(wait=False, cancel_futures=True)

            if finished % FETCH_PROGRESS_EVERY == 0 or finished == len(sources):
                print(f"   fetch RSS: {finished}/{len(sources)} surse")
        results = [item for item in ordered if item is not None]

    for items, err in results:
        if err:
            dead.append(err)
        all_items.extend(items)

    # Cat aduce descrierea peste titlu. Se pune AICI, intr-un singur loc, nu la fiecare din cele
    # trei constructii de item: un tip nou de sursa l-ar uita, si tocmai tipurile care nu vin din
    # RSS (`sitemap_news`, `html_list`) sunt cele care au descrierea goala prin constructie.
    for it in all_items:
        it["src_extra"] = cuvinte_adaugate(it.get("title"), it.get("description"))

    _cache_save(cache)
    return all_items, dead
