"""Validare REALA a celor 51 de surse noi: fiecare trece prin _fetch_one (parserul
pipeline-ului), nu prin probe. Survivors = >=1 item. Scrie data/primarii_lists/
probe_wp_noapi_fetch_2026-09-06.json cu {key: {url, tip, n_items, eroare}}.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from concurrent.futures import ThreadPoolExecutor

from generator import config
from generator import fetch
from generator.local_sources import _make_slug

rows = json.load(open('data/primarii_lists/probe_wp_noapi_noi_valid.json', encoding='utf-8'))
best = {}
for r in rows:
    k = (r['judet'].strip().upper(), r['localitate'].strip().upper())
    p = best.get(k)
    if p is None or (r.get('newest') or '') > (p.get('newest') or ''):
        best[k] = r

TIP = {'sitemap_news': 'sitemap_news', 'rss_extra': 'rss', 'wp_json': 'wp_json'}
targets = {}
for (jud, loc), r in best.items():
    key = "pl_" + _make_slug(jud, loc)
    src = config.SOURCES.get(key)
    if src is None:
        targets[key] = {"url": r['url'], "tip": "LIPSA_DIN_CONFIG", "n_items": 0, "eroare": "nu e in SOURCES (limita/coliziune?)"}
    else:
        targets[key] = {"url": src['url'], "tip": TIP[r['tip']]}

def run(kv):
    key, meta = kv
    if meta["tip"] == "LIPSA_DIN_CONFIG":
        return key, meta
    src = config.SOURCES[key]
    try:
        items, err = fetch._fetch_one(key, src)
        meta["n_items"] = len(items or [])
        meta["eroare"] = err or ""
        if items:
            meta["exemplu"] = (items[0].get("title") or "")[:80]
    except Exception as e:
        meta["n_items"] = 0
        meta["eroare"] = f"EXCEPTIE: {e}"
    return key, meta

results = {}
with ThreadPoolExecutor(max_workers=12) as ex:
    for key, meta in ex.map(run, list(targets.items())):
        results[key] = meta

ok = {k: m for k, m in results.items() if m["n_items"] >= 1}
ko = {k: m for k, m in results.items() if m["n_items"] < 1}
print(f"VIABLE: {len(ok)} / {len(results)}")
from collections import Counter
print("dupa tip (viabile):", dict(Counter(m["tip"] for m in ok.values())))
print("--- esuate ---")
for k, m in sorted(ko.items()):
    print(f"  {k} [{m['tip']}] items={m['n_items']} err={m['eroare'][:90]}")
json.dump(results, open('data/primarii_lists/probe_wp_noapi_fetch_2026-09-06.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print("scris: data/primarii_lists/probe_wp_noapi_fetch_2026-09-06.json")
