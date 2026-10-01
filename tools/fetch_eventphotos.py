#!/usr/bin/env python
"""Poze DE LA EVENIMENT (Commons, licente libere) -> lead photo pentru stirile mari.

Clasa A din propunerea 2026-09-03. Diferenta fata de fetch_leadphotos: acolo sursa e
P18-ul unei entitati (poza SUBIECTULUI); aici se cauta pe Commons fotografii luate LA
eveniment, filtrate pe fereastra de timp a stirii:

  query     = "<loc>" + "<substantivul de eveniment in engleza>" (dict inchis, mai jos)
  fereastra = DateTimeOriginal in [publicat - 2 zile, publicat + 7 zile] -> poza
              luata in jurul evenimentului; CELELALTE SE SAR (arhiva de subiect NU
              devine lead — ar induce in eroare, sect. 7)
  portile   = EXACT aceleasi ca la lead (qualifies: PD/CC0 + landscape + >= 1200px),
              apoi judecatorul AI de potrivire (photojudge), apoi renditele si
              intrarea in data/leadphotos.json — render.py le consuma NEschimbat,
              cu porile lui de credit si bugetul lui de fisiere.

Fail-safe: orice veriga lipseste (nu e stire de eveniment, loc nerezolvabil, zero
rezultate in fereastra, retea) -> articolul ramane pe coperta curenta. Miss-urile
se tin in data/eventphotos-miss.json (SEPARAT de cache-ul leadphotos, ca sa nu
interactionam cu semantica de versiuni de acolo).

  python tools/fetch_eventphotos.py          # incremental, plafonat

Env: MAX_EVENT_LOOKUPS (default 10)
"""
import datetime
import importlib.util
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from generator import eventdata, geo, htmlart, photojudge, state  # noqa: E402
from generator.process import get_provider  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "fetch_leadphotos", os.path.join(ROOT, "tools", "fetch_leadphotos.py"))
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)

MISS = os.path.join(ROOT, "data", "eventphotos-miss.json")
MISS_VERSION = 1
MAX_LOOKUPS = int(os.getenv("MAX_EVENT_LOOKUPS", "10"))

# substantivul de eveniment, RO -> EN pentru cautarea pe Commons (dict inchis:
# cuvant nou doar cu test pe mostre reale, nu improvizat in pas)
_NOUNS = [
    (re.compile(r"inundaț|viitur|revârs", re.I), "flood"),
    (re.compile(r"cutremur|seism", re.I), "earthquake"),
    (re.compile(r"incendiu", re.I), "fire"),
    (re.compile(r"alunecare", re.I), "landslide"),
    (re.compile(r"avalanș", re.I), "avalanche"),
    (re.compile(r"explozie", re.I), "explosion"),
    (re.compile(r"erupț", re.I), "eruption"),
    (re.compile(r"protest|manifesta", re.I), "protest"),
]
# pozele de eveniment se publica pe Commons INAINTEA ultimului articol despre criza
# in curs (au fost luate la fata locului, apoi incarcate), deci fereastra e asimetrica
# spre trecut: luata in [publicat-7 zile, publicat+2 zile].
_FEREASTRA = (datetime.timedelta(days=-7), datetime.timedelta(days=2))

# clasa C v1: NASA (imagini public domain, API gratuit fara cheie) pentru stiri de
# spatiu/stiinta. Poza de AICI e a OBIECTULUI (telescopul, racheta), nu a evenimentului
# — ca P18-ul: o arhiva onesta, deci fereastra larga, iar photojudge decide potrivirea.
_NASA = re.compile(
    r"\bnasa\b|spa[țt]ial|spa[țt]iul|rachet|satelit|telescop|astronaut|cosmonaut|"
    r"\bmarte\b|lunar|\blună\b|cosmos|cosmic|artemis|webb|hubble|voyager", re.I)
_NASA_FEREASTRA = (datetime.timedelta(days=-365), datetime.timedelta(days=2))


def _nasa_parse(payload: dict) -> list[dict]:
    """Raspunsul images-api.nasa.gov -> candidati [{nasa_id, titlu, centru, data, thumb}]."""
    out = []
    for it in (payload.get("collection", {}).get("items") or []):
        dd = (it.get("data") or [{}])[0]
        nid = dd.get("nasa_id")
        if not nid:
            continue
        links = it.get("links") or [{}]
        out.append({"nasa_id": nid, "titlu": dd.get("title", ""),
                    "centru": dd.get("center", ""),
                    "data": (dd.get("date_created") or "")[:10],
                    "thumb": links[0].get("href", "")})
    return out


def _nasa_cauta(q: str) -> list[dict]:
    qs = urllib.parse.urlencode({"q": q, "media_type": "image", "page_size": 6})
    payload = json.loads(eventdata._http_get(f"https://images-api.nasa.gov/search?{qs}"))
    return _nasa_parse(payload)


def _nasa_orig(nasa_id: str) -> bytes | None:
    """Asset-ul cel mai mare (~orig.jpg) pentru un nasa_id."""
    d = json.loads(eventdata._http_get(
        f"https://images-api.nasa.gov/asset/{urllib.parse.quote(nasa_id)}"))
    urls = [it.get("href", "") for it in d.get("collection", {}).get("items", [])]
    orig = [u for u in urls if u.endswith("~orig.jpg")] or \
           [u for u in urls if u.endswith("~large.jpg")]
    if not orig:
        return None
    return eventdata._http_get(orig[0])


def _nasa_candidat(a: dict, provider) -> dict | None:
    """Un candidat NASA PD pt. stirea de spatiu, sau None. Poarta finala: photojudge."""
    try:
        pub = datetime.date.fromisoformat((a.get("published") or "")[:10])
    except ValueError:
        return None
    lo, hi = pub + _NASA_FEREASTRA[0], pub + _NASA_FEREASTRA[1]
    q = " ".join((a.get("title") or "").split()[:6])
    for c in _nasa_cauta(q):
        try:
            d = datetime.date.fromisoformat(c["data"])
        except ValueError:
            continue
        if not (lo <= d <= hi):
            continue
        summary = a.get("synthesis") or a.get("teaser") or ""
        if not photojudge.photo_fits(provider, a.get("title", ""), summary,
                                     c["titlu"] or q, c["titlu"] or q):
            continue
        data = _nasa_orig(c["nasa_id"])
        if not data:
            continue
        rend = lp._save_renditions(data, f"nasa-{htmlart.art_id(a)}")
        if rend:
            return {**rend, "artist": f"NASA/{c['centru']}".rstrip("/"),
                    "license": "Public domain (NASA)",
                    "page": f"https://images.nasa.gov/details/{c['nasa_id']}",
                    "name": "NASA", "kind": "event", "noun": "nasa",
                    "data_poza": c["data"]}
    return None


def _fereastra(pub: str) -> tuple[datetime.date, datetime.date] | None:
    try:
        d = datetime.date.fromisoformat((pub or "")[:10])
    except ValueError:
        return None
    return d + _FEREASTRA[0], d + _FEREASTRA[1]


def event_noun(text: str) -> str | None:
    for pat, en in _NOUNS:
        if pat.search(text):
            return en
    return None


def _meta_date(meta: dict) -> str:
    return (meta.get("DateTimeOriginal", {}).get("value") or "")[:10]


def cauta(q: str) -> list[dict]:
    """Rezultate Commons pentru query, cu metadatele de care au nevoie portile."""
    qs = urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": q,
        "gsrnamespace": 6, "gsrlimit": 8, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": lp.LEAD_W, "format": "json"})
    d = lp.fp._get(f"https://commons.wikimedia.org/w/api.php?{qs}")
    out = []
    for p in (d.get("query", {}).get("pages") or {}).values():
        for ii in p.get("imageinfo", []):
            meta = ii.get("extmetadata", {})
            title = p.get("title", "")
            if not re.search(r"\.(jpe?g|png)$", title, re.I):
                continue
            out.append({"filename": title.removeprefix("File:"),
                        "thumb": ii.get("thumburl"),
                        "width": ii.get("width", 0), "height": ii.get("height", 0),
                        "license": meta.get("LicenseShortName", {}).get("value", ""),
                        "artist": lp.fp.clean_html(meta.get("Artist", {}).get("value", "")),
                        "page": ii.get("descriptionurl"),
                        "data": _meta_date(meta)})
    return out


def _in_fereastra(data: str, f: tuple[datetime.date, datetime.date]) -> bool:
    try:
        d = datetime.date.fromisoformat(data)
    except ValueError:
        return False
    return f[0] <= d <= f[1]


def main() -> int:
    arts = [a for a in state.load() if a.get("slug")]
    arts.sort(key=lambda a: a.get("published") or "", reverse=True)
    lead_cache = json.load(open(lp.CACHE, encoding="utf-8")) if os.path.isfile(lp.CACHE) else {}
    miss_cache = json.load(open(MISS, encoding="utf-8")) if os.path.isfile(MISS) else {}
    provider = get_provider()
    buget = MAX_LOOKUPS
    atasate = 0
    memo_query: dict[str, list[dict]] = {}  # acelasi eveniment din 3 surse = 1 cautare
    for a in arts:
        if buget <= 0:
            break
        aid = htmlart.art_id(a)
        entry = lead_cache.get(aid)
        if entry and not entry.get("miss"):
            continue  # are deja lead (P18/localitate) — nu suprascriu
        text = f"{a.get('title') or ''} {a.get('teaser') or ''}"
        noun = event_noun(text)
        fereastra = _fereastra(a.get("published"))
        if not noun or not fereastra:
            continue
        loc = geo.eticheta_copertei(a) or ""
        loc_query, loc_badge = loc, loc
        if not loc_query or loc_query.lower() in ("local", "judetean", "general", "extern",
                                                  "sport", "stiri", "regional"):
            tr = eventdata.tara(a)
            if not tr:
                continue  # fara loc rezolvabil (localitate sau tara) nu am query onest
            loc_query, loc_badge = tr["en"], tr["ro"]
        m = miss_cache.get(aid)
        if m and m.get("v", 0) >= MISS_VERSION:
            continue
        q = f"{loc_query} {noun}"
        if q in memo_query:
            cands = memo_query[q]  # acelasi eveniment relatat de 3 surse = 1 cautare,
        else:                      # si o singura unitate de buget (se scade abia aici)
            buget -= 1
            cands = [c for c in cauta(q)
                     if lp.qualifies(c) and _in_fereastra(c["data"], fereastra)]
            memo_query[q] = cands
        if not cands:
            miss_cache[aid] = {"miss": True, "v": MISS_VERSION, "r": "event",
                               "motiv": "zero rezultate in fereastra", "q": q}
            continue
        gasit = None
        for c in cands:
            summary = a.get("synthesis") or a.get("teaser") or ""
            if not photojudge.photo_fits(provider, a.get("title", ""), summary,
                                         f"{loc_badge} {noun}", lp._caption(c["filename"])):
                continue
            try:
                data = urllib.request.urlopen(
                    urllib.request.Request(c["thumb"], headers=lp.UA), timeout=30).read()
            except OSError:
                continue
            if len(data) < 3000:
                continue
            rend = lp._save_renditions(data, f"ev-{aid}")
            if rend:
                gasit = {**rend, "artist": c["artist"], "license": c["license"],
                         "page": c["page"], "name": loc_badge, "kind": "event",
                         "noun": noun, "data_poza": c["data"]}
                break
        if not gasit and _NASA.search(text):
            try:
                gasit = _nasa_candidat(a, provider)
            except (OSError, ValueError, KeyError):
                gasit = None
        if gasit:
            lead_cache[aid] = gasit
            atasate += 1
            print(f">> event-photo: {aid} <- {q} ({gasit['data_poza']}, {gasit['license']})")
        else:
            miss_cache[aid] = {"miss": True, "v": MISS_VERSION, "r": "event",
                               "motiv": "candidati respinsi de porti", "q": q}
    json.dump(lead_cache, open(lp.CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(miss_cache, open(MISS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f">> event-photos: {atasate} atasate, buget ramas {buget}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
