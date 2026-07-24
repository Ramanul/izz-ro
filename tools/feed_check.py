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
import time
import urllib.error
import urllib.request

import feedparser

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from generator import config  # noqa: E402
from generator.fetch import USER_AGENT, TIMEOUT, RETRY_ATTEMPTS, _retry_delay  # noqa: E402


def main() -> int:
    only = set(sys.argv[1:])
    bad = 0
    limited = 0
    print(f"=== feed check ({len(config.SOURCES)} surse configurate) ===")
    for key, src in config.SOURCES.items():
        if only and src["category"] not in only:
            continue
        if src.get("type"):
            # Orice sursa care NU e RSS/Atom simplu (html_list, sitemap_news, ...): rulam
            # fetcher-ul real si raportam cate articole extrage. feedparser pe continutul
            # brut ar da 0 intrari si am raporta "GOL" o sursa perfect sanatoasa — exact ce
            # s-a intamplat cu piataauto (sitemap_news) in feedcheck-ul din 2026-07-24.
            from generator.fetch import _fetch_one  # noqa: E402
            arts, err = _fetch_one(key, src)
            if err or not arts:
                print(f"  DEAD {key:12s} [{src['category']}] {src['type']} -> {err or '0 articole'}")
                bad += 1
            else:
                newest = max((a.get("published", "") for a in arts), default="")[:10]
                print(f"  ok   {key:12s} [{src['category']}] {src['type']}, {len(arts)} articole, cea mai noua: {newest or '-'}")
            continue
        # Fetch propriu, DELIBERAT independent de fetch.py: asa prindem cazul "200 dar nu e
        # feed", pe care pipeline-ul il inghite tacit. Reutilizam doar POLITICA de retry
        # (aceleasi constante), ca sa nu raportam DEAD o sursa pe care productia o recupereaza.
        raw = status = None
        for attempt in range(RETRY_ATTEMPTS + 1):
            try:
                req = urllib.request.Request(src["url"], headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    raw = resp.read()
                    status = resp.status
                break
            except urllib.error.HTTPError as exc:
                delay = _retry_delay(exc, attempt)
                if delay is None:
                    # 429 = "nu am putut verifica", NU "sursa e moarta". Masurat 2026-07-24
                    # (ua-probe run 30096569916): aceste surse limiteaza dupa FRECVENTA, per IP
                    # de runner — prima cerere trece, urmatoarele nu, indiferent de User-Agent.
                    # Acelasi rationament ca la monitor.yml: un 403 de la edge = edge viu.
                    # Daca l-am numara ca esec, CI-ul ar fi rosu permanent din motive externe
                    # si am inceta sa ne mai uitam la el.
                    if exc.code in (429, 503):
                        print(f"  LIMIT{key:12s} [{src['category']}] {exc} — rate-limit pe IP, "
                              f"NEVERIFICABIL de aici (nu inseamna sursa moarta)")
                        limited += 1
                    else:
                        print(f"  DEAD {key:12s} [{src['category']}] {src['url']} -> {exc}")
                        bad += 1
                    break
                time.sleep(delay)
            except (urllib.error.URLError, socket.timeout, ValueError) as exc:
                print(f"  DEAD {key:12s} [{src['category']}] {src['url']} -> {exc}")
                bad += 1
                break
        if raw is None:
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
    if limited:
        print(f"\nATENTIE: {limited} surse rate-limitate de aici — de reverificat de pe alt IP "
              f"(local, sau alt moment). Nu sunt considerate esec.")
    if bad:
        print(f"\nFAIL: {bad} surse moarte sau fara intrari.")
        return 1
    print("\nOK: toate sursele verificabile de aici raspund cu intrari.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
