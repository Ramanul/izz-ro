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
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config  # noqa: E402
from generator.fetch import _fetch_one_guarded  # noqa: E402

# Pauza dintre cele doua incercari ale unei surse suspecte. Zero in teste (monkeypatch), ca
# suita sa nu doarma degeaba; in CI, 2 secunde ajung cat sa treaca un timeout de retea scurt.
RETRY_PAUZA_S = float(os.environ.get("FEED_CHECK_RETRY_PAUZA_S", "2"))

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
# ar fi dus la scoaterea unei surse județene VII.
_BLOCKED_RE = re.compile(r"HTTP Error 403:")

# ACEEASI clasa de fals-pozitiv, dar cu alt text: `fetch._fetch_one` intoarce explicit
# „challenge anti-bot servit cu 200 (sursa NU e moarta)" cand gazda raspunde 200 cu
# interstitialul in loc de feed. Pana pe 2026-10-11 textul asta cadea in ramura DEAD, desi
# FETCH-UL insusi declara sursa vie — adica verificatorul contrazicea sursa de adevar pe care
# o cheama. Efectul e vizibil in istoric: feedcheck a fost rosu la FIECARE rulare programata
# (46 din 46, 25 iul - 10 oct), iar un job rosu permanent nu mai semnaleaza nimic.
# Numerele din `fetch._fetch_one` arata scara: 76 de surse (din 189 pe 2026-08-02) ies goale de
# pe IP-urile runnerilor si dau articole de pe IP de acasa. Tratat ca „neverificabil de aici",
# aceeasi galeata ca 403/429 — nu ca „moarta".
_CHALLENGE_RE = re.compile(r"challenge anti-bot servit cu 200")


def _clasifica(arts: list, err: str | None) -> tuple[str, str]:
    """(categorie, detaliu) pentru o sursa: ok / limit / blocat / gol / dead.

    „blocat" nu e „mort": 403, 429/503 si challenge-ul anti-bot servit cu 200 sunt toate
    raspunsuri ale gazdei pe care le primim DOAR din datacenter — din alta retea sursa poate fi
    perfect vie, deci raportul le scoate din verdict (vezi comentariile de la regex-uri).
    """
    if err:
        detail = err[len(err.split(":")[0]) + 2:] if ": " in err else err
        if _RATE_LIMIT_RE.search(detail):
            return "limit", detail
        # 403 si challenge-ul servit cu 200 sunt aceeasi poveste (gazda respinge IP-ul de
        # datacenter), doar etichetate diferit de fetch.py.
        if _BLOCKED_RE.search(detail) or _CHALLENGE_RE.search(detail):
            return "blocat", detail
        return "dead", detail
    if not arts:
        # HTTP a mers (altfel err ar fi fost setat), dar 0 articole utilizabile: feed
        # gol, feed care nu e RSS/Atom (feedparser -> 0 intrari, tacut), sau toate
        # intrarile filtrate ca agentie de presa. Exact cazul pe care fetch.py NU-l
        # raporteaza (o sursa "goala" nu e o eroare de retea) si pe care CI trebuie sa-l
        # vada, ca sa nu ramana o sursa noua inghetata neobservata.
        return "gol", "0 articole"
    return "ok", ""


def main() -> int:
    only = set(sys.argv[1:])
    bad: list[tuple[str, str]] = []
    limited = 0
    randuri_sumar: list[str] = []
    print(f"=== feed check ({len(config.SOURCES)} surse configurate) ===")
    for key, src in config.SOURCES.items():
        if only and src["category"] not in only:
            continue

        kind = src.get("type")
        tag = f"{kind}, " if kind else ""
        arts, err = _fetch_one_guarded(key, src)
        categorie, detail = _clasifica(arts, err)

        # A doua incercare DOAR pentru verdictul care conteaza (mort/gol): prima poate cadea pe
        # o pana de moment, iar un raport care striga „mort" pentru un timeout de 3 secunde
        # invata proprietarul sa ignore raportul (masurat: puseuri de 74 de fals-negative intr-o
        # singura rulare, toate vii la reverificare — vezi docstring-ul modulului).
        if categorie in ("dead", "gol"):
            time.sleep(RETRY_PAUZA_S)
            arts2, err2 = _fetch_one_guarded(key, src)
            categorie2, detail2 = _clasifica(arts2, err2)
            if categorie2 == "ok" or categorie2 in ("limit", "blocat"):
                categorie, detail, arts = categorie2, detail2, arts2
            else:
                categorie, detail = categorie2, detail2

        if categorie == "ok":
            newest = max((a.get("published", "") for a in arts), default="")[:10]
            linie = (f"  ok   {key:12s} [{src['category']}] {tag}{len(arts)} articole "
                     f"(cap productie: {config.MAX_PER_SOURCE}), cea mai noua: {newest or '-'}")
        elif categorie == "gol":
            linie = f"  GOL  {key:12s} [{src['category']}] {tag}{detail}"
            bad.append((key, "gol"))
        elif categorie == "limit":
            linie = (f"  LIMIT {key:12s} [{src['category']}] {detail} — rate-limit pe IP, "
                     f"NEVERIFICABIL de aici (nu inseamna sursa moarta)")
            limited += 1
        elif categorie == "blocat":
            linie = (f"  BLOCAT {key:11s} [{src['category']}] {detail} — IP de datacenter "
                     f"respins, NEVERIFICABIL de aici (reverifica de pe alt IP inainte "
                     f"sa scoti sursa)")
            limited += 1
        else:
            linie = f"  DEAD {key:12s} [{src['category']}] {src['url']} -> {detail}"
            bad.append((key, detail))
        print(linie)
        randuri_sumar.append(linie)

    if limited:
        print(f"\nATENTIE: {limited} surse rate-limitate sau blocate pe IP de aici — de "
              f"reverificat de pe alt IP (local, sau alt moment). Nu sunt considerate esec.")
    # Adnotarile intra in UI-ul rularii si in API (gh api .../annotations), deci esecul se
    # citeste fara jurnalele binare — care, la repo-ul asta, nu sunt accesibile din sandbox.
    sumar = ("## feed check\n\n" + "\n".join(randuri_sumar) + "\n\n"
             f"total: {len(randuri_sumar)} surse verificate, {len(bad)} moarte/goale, "
             f"{limited} neverificabile de aici\n")
    cale_sumar = os.environ.get("GITHUB_STEP_SUMMARY")
    if cale_sumar:
        with open(cale_sumar, "a", encoding="utf-8") as fh:
            fh.write(sumar)
    if bad:
        print(f"::error title=feed check:: {len(bad)} surse moarte sau goale: "
              + ", ".join(k for k, _ in bad[:30])
              + ("..." if len(bad) > 30 else ""))
        print(f"\nFAIL: {len(bad)} surse moarte sau fara articole.")
        return 1
    print("\nOK: toate sursele verificabile de aici raspund cu articole.")
    return 0


if __name__ == "__main__":
    # Windows: cp1252 nu are „ș"/„ț", deci un `print` cu diacritice arunca
    # UnicodeEncodeError si scriptul iese cu 1 — indistingibil de un esec real de
    # continut. Masurat 2026-08-20: `qa_check.py` iesea cu 1 pe date valide, iar cu
    # PYTHONIOENCODING=utf-8 cu 0. In CI (Linux, UTF-8) nu se vede. Acelasi idiom ca
    # in `scan_homepages.py`, extins la toate punctele de intrare cu diacritice.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
