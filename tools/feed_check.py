#!/usr/bin/env python
"""Sanatatea surselor din config.SOURCES — per sursa: cate articole extrage fetcher-ul
REAL al pipeline-ului, plus prospetime.

  python tools/feed_check.py                # toate sursele
  python tools/feed_check.py lifestyle fashion discounturi   # doar categoriile date

Ruleaza in GitHub Actions (feedcheck.yml, dispatch) — runnerii au internet, sandbox-urile nu.

Foloseste EXACT fetcher-ul de productie (generator.fetch._fetch_one_guarded — aceeasi functie
pe care fetch_all() o cheama per sursa), NU o reimplementare proprie. Pana la 2026-07-25
scriptul isi reimplementa fetch-ul RSS (urllib + feedparser, cu constante copiate din
fetch.py). Masurat: doua rulari feedcheck la ~15 minute distanta, pe cod aproape identic
(un rand sters dintr-un denylist), au raportat 1 sursa moarta si respectiv 74 — desi
verificare independenta a 4 din cele 74 (contributors, bookhub, pl_ialomita_bucu,
stirilemoldovei) a aratat ca sunt vii: fetch direct din sandbox si din runnerul de pe
`main` (run 30152246525, 09:06 UTC) le arata cu articole reale, HTTP 200. Reproducerea
directa a celor 4 (acest sandbox, ambele implementari de fetch) NU a aratat nicio diferenta
de comportament intre reimplementare si fetch.py — deci reimplementarea in sine nu era
cauza mecanica a puseului. Cauza masurata: fals-negativele apar doar in rulari CI reale, pe
tot setul de 189 surse, niciodata izolat — semnul unei limitari tranzitorii, dependente de
IP/timp, pe infrastructura gazdelor (nu a codului). Motivul real pentru unificare ramane
valabil independent de asta: inainte, verificatorul si productia puteau diverge tacit (politici
de retry/parsare duplicate); acum vad EXACT acelasi cod, pentru orice tip de sursa (RSS,
sitemap_news, html_list) — o singura sursa de adevar pentru "e vie sau nu".
"""
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from generator import config  # noqa: E402
from generator.fetch import _fetch_one_guarded  # noqa: E402

# Eroarea finala a unui 429/503 (dupa epuizarea retry-ului din fetch.py) ramane formatata
# de urllib ca "HTTP Error 429: Too Many Requests" -- acelasi text pe care _fetch_one l-ar
# fi produs si pentru fetch.py in productie. Nu inseamna "sursa moarta", inseamna "gazda
# limiteaza dupa frecventa, per IP" (masurat 2026-07-24, vezi specs/istoric-executie.md).
_RATE_LIMIT_RE = re.compile(r"HTTP Error (429|503):")

# 403 NU inseamna sursa moarta: gazdele care ruleaza Cloudflare (sau orice bot-fight) resping
# IP-urile de datacenter ale runnerului, desi feedul e viu pentru oricine altcineva. Masurat
# 2026-08-05: ziaruldeiasi.ro/rss a fost raportat DEAD de 15 rulari consecutive, iar de pe o
# retea obisnuita raspunde 200 cu 15 KB de continut -- inclusiv cu curl simplu, fara User-Agent.
# Acelasi fenomen care tinea garda vizuala rosie 19 zile (PR #136). Clasificat gresit, semnalul
# ar fi dus la scoaterea unei surse zonale VII.
_BLOCKED_RE = re.compile(r"HTTP Error 403:")


def main() -> int:
    only = set(sys.argv[1:])
    bad = 0
    limited = 0
    print(f"=== feed check ({len(config.SOURCES)} surse configurate) ===")
    for key, src in config.SOURCES.items():
        if only and src["category"] not in only:
            continue

        arts, err = _fetch_one_guarded(key, src)
        kind = src.get("type")
        tag = f"{kind}, " if kind else ""

        if err:
            detail = err[len(key) + 2:] if err.startswith(f"{key}: ") else err
            if _RATE_LIMIT_RE.search(detail):
                print(f"  LIMIT {key:12s} [{src['category']}] {detail} — rate-limit pe IP, "
                      f"NEVERIFICABIL de aici (nu inseamna sursa moarta)")
                limited += 1
            elif _BLOCKED_RE.search(detail):
                print(f"  BLOCAT {key:11s} [{src['category']}] {detail} — IP de datacenter "
                      f"respins, NEVERIFICABIL de aici (reverifica de pe alt IP inainte "
                      f"sa scoti sursa)")
                limited += 1
            else:
                print(f"  DEAD {key:12s} [{src['category']}] {src['url']} -> {detail}")
                bad += 1
            continue

        if not arts:
            # HTTP a mers (altfel err ar fi fost setat), dar 0 articole utilizabile: feed
            # gol, feed care nu e RSS/Atom (feedparser -> 0 intrari, tacut), sau toate
            # intrarile filtrate ca agentie de presa. Exact cazul pe care fetch.py NU-l
            # raporteaza (o sursa "goala" nu e o eroare de retea) si pe care CI trebuie sa-l
            # vada, ca sa nu ramana o sursa noua inghetata neobservata.
            print(f"  GOL  {key:12s} [{src['category']}] {tag}0 articole")
            bad += 1
            continue

        newest = max((a.get("published", "") for a in arts), default="")[:10]
        print(f"  ok   {key:12s} [{src['category']}] {tag}{len(arts)} articole "
              f"(cap productie: {config.MAX_PER_SOURCE}), cea mai noua: {newest or '-'}")

    if limited:
        print(f"\nATENTIE: {limited} surse rate-limitate sau blocate pe IP de aici — de "
              f"reverificat de pe alt IP (local, sau alt moment). Nu sunt considerate esec.")
    if bad:
        print(f"\nFAIL: {bad} surse moarte sau fara articole.")
        return 1
    print("\nOK: toate sursele verificabile de aici raspund cu articole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
