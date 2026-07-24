#!/usr/bin/env python
"""De ce dau 429 unele feed-uri de pe runnerii GitHub: e User-Agent-ul sau e IP-ul?

  python tools/ua_probe.py                      # sursele cunoscute cu 429
  python tools/ua_probe.py libertatea elle      # doar cheile date

Ruleaza in GitHub Actions (ua-probe.yml, dispatch) — de pe IP-ul de acasa nu are sens,
sursele astea raspund 200 acolo. Nu scrie nimic, nu consuma AI quota.

Testam DOAR user-agenti onesti: fiecare varianta declara in continuare cine suntem si
linkul catre site. Nu ne dam drept Googlebot si nu ne dam drept un om — daca singura
varianta care trece e un UA de browser curat, asta e un rezultat de RAPORTAT, nu de
implementat in tacere: inseamna ca sursa refuza deliberat agregatoarele, iar decizia
de a insista apartine proprietarului, nu scriptului.
"""
import socket
import sys
import urllib.error
import urllib.request

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from generator import config  # noqa: E402
from generator.fetch import USER_AGENT, TIMEOUT  # noqa: E402

# Sursele care au dat 429 in feedcheck-urile din 2026-07-24 (30093310671, 30095060877).
DEFAULT_KEYS = ["libertatea", "unica", "elle", "bzi"]

CANDIDATES = [
    ("actual", USER_AGENT),
    # Multe WAF-uri resping orice UA care nu incepe cu "Mozilla/5.0", indiferent de rest.
    # Varianta asta pastreaza identitatea si linkul — nu ascunde nimic, doar respecta forma.
    ("mozilla-compatible", "Mozilla/5.0 (compatible; IZZ.ro/1.0; +https://izz.ro)"),
    # Format clasic de feed reader, tot declarat.
    ("feedreader", "IZZ.ro/1.0 feed reader (+https://izz.ro; contact via site)"),
    # Diagnostic PUR: daca doar asta trece, sursa blocheaza agregatoarele ca politica.
    ("browser-diagnostic", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"),
]


def probe(url: str, ua: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return f"{resp.status} ({len(resp.read())} octeti)"
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}"
    except (urllib.error.URLError, socket.timeout, ValueError) as exc:
        return f"EROARE {exc}"


def main() -> int:
    keys = sys.argv[1:] or DEFAULT_KEYS
    print("=== ua probe ===")
    print(f"Surse: {', '.join(keys)}\n")
    for key in keys:
        src = config.SOURCES.get(key)
        if not src:
            print(f"{key}: NU exista in config.SOURCES — sarit")
            continue
        print(f"{key}  [{src['category']}]  {src['url']}")
        for label, ua in CANDIDATES:
            print(f"    {label:20s} -> {probe(src['url'], ua)}")
        print()
    print("Citire: daca 'actual' da 429 iar 'mozilla-compatible' da 200, e forma UA-ului.")
    print("Daca TOATE dau 429, e IP-ul runnerului — UA-ul nu are ce rezolva.")
    print("Daca doar 'browser-diagnostic' trece, sursa refuza deliberat agregatoarele:")
    print("raporteaza, nu implementa — decizia e a proprietarului site-ului izz.ro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
