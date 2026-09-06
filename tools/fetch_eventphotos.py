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
from generator import geo, htmlart, photojudge, state  # noqa: E402
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
        if not loc or loc.lower() in ("local", "judetean", "general", "extern", "sport",
                                      "stiri", "regional"):
            continue  # fara loc rezolvabil nu am query onest
        m = miss_cache.get(aid)
        if m and m.get("v", 0) >= MISS_VERSION:
            continue
        q = f"{loc} {noun}"
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
                                         f"{loc} {noun}", lp._caption(c["filename"])):
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
                         "page": c["page"], "name": loc, "kind": "event",
                         "noun": noun, "data_poza": c["data"]}
                break
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
