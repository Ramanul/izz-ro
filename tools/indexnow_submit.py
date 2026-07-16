#!/usr/bin/env python
"""Trimite URL-urile articolelor RECENTE la IndexNow (Bing, Seznam, Yandex etc.).

  python tools/indexnow_submit.py            # articolele publicate in ultimele 3h
  SINCE_HOURS=24 python tools/indexnow_submit.py

Vizibilitate (raport 2026-07-16): site nou, DA mic -> motoarele nedescoperind rapid
paginile noi. IndexNow le anunta activ, gratuit, la fiecare rulare a pipeline-ului.
Best-effort in build.yml (continue-on-error): un esec nu blocheaza nimic.
Cheia e publica prin definitie (serveste la verificarea domeniului): render.py
scrie {key}.txt la radacina site-ului; noi o trimitem in payload.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config  # noqa: E402

STATE = os.path.join(config.ROOT, "data", "articles.json")
ENDPOINT = "https://api.indexnow.org/indexnow"


def main() -> int:
    hours = float(os.getenv("SINCE_HOURS", "3"))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    with open(STATE, encoding="utf-8") as fh:
        arts = json.load(fh)
    urls = []
    for a in arts:
        try:
            dt = datetime.fromisoformat(a.get("published", ""))
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if dt >= cutoff and a.get("category") and a.get("slug"):
            urls.append(f"{config.SITE['url']}/{a['category']}/{a['slug']}/")
    if not urls:
        print(">> IndexNow: nimic recent de anuntat.")
        return 0
    payload = {
        "host": config.SITE["url"].split("//")[1],
        "key": config.INDEXNOW_KEY,
        "keyLocation": f"{config.SITE['url']}/{config.INDEXNOW_KEY}.txt",
        "urlList": urls[:500],
    }
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f">> IndexNow: {len(urls)} URL-uri anuntate, HTTP {resp.status}")
    except Exception as exc:  # best-effort: raportam, nu picam build-ul
        print(f">> IndexNow: esec ({exc}) — neblocant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
