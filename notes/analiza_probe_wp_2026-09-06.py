"""Analiza rezultatelor probe wp_rest + ramase (6 sep 2026).

Intrebari la care raspunde:
 1. Cate din cele 181 WordPress-uri fara /wp-json/ au interfata standard functionala
    (rest_route, feed pe alta cale, sitemap_news) si cu content FRESH (>= 2026-01-01)?
 2. Cati din castigatori sunt DEJA in catalogul pipeline-ului
    (gold_integrare_2026-09-05.csv + html_sources_2026-09-05.csv)?
 3. Cati sunt NOI (candidati de integrat) si cati raman fara nicio cale standard
    (clienti pentru scraper/proxy)?
"""
import csv
from collections import Counter
from urllib.parse import urlparse

PROBE = [
    r"C:/Users/cw_26/AppData/Local/Temp/wp_rest_rez.csv",
    r"C:/Users/cw_26/AppData/Local/Temp/ramase_rez.csv",
]
CATALOG = [
    r"C:/Users/cw_26/izz-ro/data/primarii_lists/gold_integrare_2026-09-05.csv",
    r"C:/Users/cw_26/izz-ro/data/primarii_lists/html_sources_2026-09-05.csv",
]

def netloc(u):
    try:
        h = urlparse(u).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""

def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

# 1) unione probe, dedup pe domeniu, pastram randul cu cea mai buna vite (newest)
best = {}
for p in PROBE:
    try:
        rows = read_rows(p)
    except FileNotFoundError:
        print(f"lipsa: {p}")
        continue
    for r in rows:
        d = netloc(r.get("url", ""))
        if not d:
            continue
        prev = best.get(d)
        if prev is None or (r.get("newest", "") > prev.get("newest", "")):
            best[d] = r

FRESH = "2026-01-01"
fresh = [r for r in best.values() if (r.get("newest") or "") >= FRESH]
tip_all = Counter(r["tip"] for r in best.values())
tip_fresh = Counter(r["tip"] for r in fresh)
print(f"domenii unice acoperite de probe: {len(best)}")
print(f"  dupa tip (toate): {dict(tip_all)}")
print(f"  FRESH (newest >= {FRESH}): {len(fresh)}  dupa tip: {dict(tip_fresh)}")

# 2) deja in catalog?
cat_domains = set()
for c in CATALOG:
    try:
        for r in read_rows(c):
            for k, v in r.items():
                if v and ("http" in str(v)):
                    cat_domains.add(netloc(v))
            # coloane gen url/rss/feed/html_url
            for k in ("url", "rss", "feed", "html_url", "source"):
                v = r.get(k)
                if v and "http" in str(v):
                    cat_domains.add(netloc(v))
    except FileNotFoundError:
        print(f"lipsa catalog: {c}")
print(f"domenii in catalog: {len(cat_domains)}")

winner_domains = {netloc(r["url"]) for r in best.values()}
fresh_domains = {netloc(r["url"]) for r in fresh}
print(f"castigatori deja in catalog: {len(winner_domains & cat_domains)}")
print(f"castigatori FRESH deja in catalog: {len(fresh_domains & cat_domains)}")

new_fresh = [r for r in fresh if netloc(r["url"]) not in cat_domains]
print(f"NOI castigatori FRESH (de integrat): {len(new_fresh)}")
out = r"C:/Users/cw_26/izz-ro/data/primarii_lists/probe_wp_noapi_noi_2026-09-06.csv"
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["judet", "localitate", "url", "tip", "newest", "n_items"])
    w.writeheader()
    for r in sorted(new_fresh, key=lambda x: (x["judet"], x["localitate"])):
        w.writerow({k: r.get(k, "") for k in w.fieldnames})
print(f"scris: {out}")
