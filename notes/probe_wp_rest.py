"""Probe ieftin pe WordPress-urile fara wp-json (181): celelalte cai standard inainte
de orice scraper — bunele practici: epuizezi interfetele standard ale platformei.
  1) /?rest_route=/wp/v2/posts&per_page=8  (API-ul merge si fara permalink-uri)
  2) /feed/rss/, /index.php/feed/, /?feed=rss2&post_type=post  (feed-uri pe alte cai)
  3) /sitemap.xml cu lastmod >= 2026 (tip sitemap_news existent in fetch.py)
Feed valid = <rss/<feed + o data >= 2026-01-01; sitemap = urlset + lastmod >= 2026.
"""
import csv
import email.utils
import json
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

WORKERS = 16
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
OUT = r"C:/Users/cw_26/AppData/Local/Temp/wp_rest_rez.csv"


def get(u, limit=300_000):
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
        return r.read(limit).decode("utf-8", "replace")


def datele(body):
    dates = []
    for m in re.findall(r"<(pubDate|published|updated|dc:date)>([^<]+)</", body):
        raw = m[1].strip()
        d = None
        try:
            d = email.utils.parsedate_to_datetime(raw)
        except Exception:
            try:
                d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:
                pass
        if d:
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            dates.append(d)
    for m in re.findall(r"<lastmod>([^<]+)</lastmod>", body):
        try:
            d = datetime.fromisoformat(m.strip().replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            dates.append(d)
        except Exception:
            pass
    return max(dates).strftime("%Y-%m-%d") if dates else ""


def probe(row):
    base = (row["url"] or "").strip().rstrip("/")
    if not base:
        return None
    # 1) rest_route — fara permalink-uri
    try:
        body = get(base + "/?rest_route=/wp/v2/posts&per_page=8&_fields=title,date,link")
        data = json.loads(body)
        if isinstance(data, list) and data:
            newest = max((d.get("date") or "") for d in data)
            if newest >= "2026-01-01":
                return {"judet": row["judet"], "localitate": row["localitate"],
                        "url": base + "/?rest_route=/wp/v2/posts&per_page=8",
                        "tip": "wp_json", "newest": newest[:10], "n_items": len(data)}
    except Exception:
        pass
    # 2) feed-uri pe alte cai
    for p in ("/feed/rss/", "/index.php/feed/", "/?feed=rss2&post_type=post", "/feed/atom/"):
        try:
            body = get(base + p, 200_000)
            if "<rss" in body or "<feed" in body:
                newest = datele(body)
                if newest >= "2026-01-01":
                    return {"judet": row["judet"], "localitate": row["localitate"],
                            "url": base + p, "tip": "rss_extra", "newest": newest, "n_items": body.count("<item")}
        except Exception:
            continue
    # 3) sitemap cu lastmod
    try:
        body = get(base + "/sitemap.xml", 250_000)
        if "<urlset" in body or "<sitemapindex" in body:
            newest = datele(body)
            if newest >= "2026-01-01":
                return {"judet": row["judet"], "localitate": row["localitate"],
                        "url": base + "/sitemap.xml", "tip": "sitemap_news",
                        "newest": newest, "n_items": body.count("<url")}
    except Exception:
        pass
    return None


rows = list(csv.DictReader(open(r"C:/Users/cw_26/AppData/Local/Temp/wp_rest.csv", encoding="utf-8")))
print(f"probe pe {len(rows)} WordPress fara wp-json", flush=True)

hits = []
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(probe, r): r for r in rows}
    for i, fut in enumerate(as_completed(futs), 1):
        h = fut.result()
        if h:
            hits.append(h)
        if i % 40 == 0:
            print(f"  {i}/{len(rows)} — {len(hits)} gasite", flush=True)

with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["judet", "localitate", "url", "tip", "newest", "n_items"])
    w.writeheader()
    w.writerows(hits)

from collections import Counter
print("DONE:", len(hits), "| pe tip:", dict(Counter(h["tip"] for h in hits)))
