#!/usr/bin/env python
"""Sanatatea surselor RSS din config.SOURCES — per sursa: HTTP, numar intrari, prospetime.

  python tools/feed_check.py                # toate sursele
  python tools/feed_check.py lifestyle fashion discounturi   # doar categoriile date

Ruleaza in GitHub Actions (feedcheck.yml, dispatch) — runnerii au internet, sandbox-urile nu.
Prinde si cazul pe care fetch.py NU-l raporteaza: URL care raspunde 200 dar NU e feed
(feedparser -> 0 intrari, tacut). Exit 1 daca vreo sursa activa e moarta/goala, ca sa fie
vizibil in CI inainte de a lasa o sursa noua in productie.
"""
import socket
import sys
import urllib.error
import urllib.request

import feedparser

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from generator import config  # noqa: E402
from generator.fetch import USER_AGENT, TIMEOUT  # noqa: E402


def main() -> int:
    only = set(sys.argv[1:])
    bad = 0
    print(f"=== feed check ({len(config.SOURCES)} surse configurate) ===")
    for key, src in config.SOURCES.items():
        if only and src["category"] not in only:
            continue
        if src.get("type") == "html_list":
            # sursele fara RSS: rulam scraper-ul real si raportam cate articole extrage
            from generator.fetch import _fetch_one  # noqa: E402
            arts, err = _fetch_one(key, src)
            if err or not arts:
                print(f"  DEAD {key:12s} [{src['category']}] {src['type']} -> {err or '0 articole'}")
                bad += 1
            else:
                newest = max((a.get("published", "") for a in arts), default="")[:10]
                print(f"  ok   {key:12s} [{src['category']}] {src['type']}, {len(arts)} articole, cea mai noua: {newest or '-'}")
            continue
        try:
            req = urllib.request.Request(src["url"], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                status = resp.status
        except (urllib.error.URLError, socket.timeout, ValueError) as exc:
            print(f"  DEAD {key:12s} [{src['category']}] {src['url']} -> {exc}")
            bad += 1
            continue
        feed = feedparser.parse(raw)
        n = len(feed.entries)
        newest = ""
        if n:
            tm = feed.entries[0].get("published_parsed") or feed.entries[0].get("updated_parsed")
            newest = f"{tm.tm_year}-{tm.tm_mon:02d}-{tm.tm_mday:02d}" if tm else "fara data"
        mark = "ok  " if n > 0 else "GOL "
        if n == 0:
            bad += 1
        print(f"  {mark} {key:12s} [{src['category']}] HTTP {status}, {n} intrari, cea mai noua: {newest or '-'}")
    if bad:
        print(f"\nFAIL: {bad} surse moarte sau fara intrari.")
        return 1
    print("\nOK: toate sursele verificate raspund cu intrari.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
