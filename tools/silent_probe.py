#!/usr/bin/env python
"""Ce primesc EFECTIV runnerii GitHub de la sursele care raspund 200 si nu dau niciun articol?

  python tools/silent_probe.py                        # esantionul reprezentativ implicit
  python tools/silent_probe.py recorder zch bookhub   # doar cheile date

Ruleaza in GitHub Actions (silent-probe.yml, dispatch). De pe IP-ul de acasa serveste doar
ca martor: acolo sursele astea raspund normal, deci o rulare locala arata cum arata un
raspuns SANATOS, iar rularea de pe runner arata cu ce difera. Nu scrie nimic si nu consuma
AI quota.

De ce exista, separat de `ua_probe.py` si `feed_check.py`:
- `feed_check.py` spune CA o sursa da 0 articole, nu DE CE — pentru el totul e "GOL".
- `ua_probe.py` raspunde la o alta intrebare (429: e User-Agent-ul sau e IP-ul?) si nu se
  uita niciodata la corpul raspunsului, doar la status si la numarul de octeti.
- Intrebarea deschisa aici e a treia: statusul e 200, deci nu e un blocaj pe status, iar
  parsarea nu produce nimic. Asta poate insemna o pagina de challenge servita cu 200, un
  redirect catre altceva, un feed gol autentic, sau un corp comprimat/trunchiat. Fara
  corpul raspunsului nu se poate distinge intre ele. Masurat 2026-08-02: 73 din 75 de
  surse raportate GOL pe runner (run 30742957035) intorc articole reale de acasa, cu
  acelasi fetcher — deci diferenta nu e in sursa, e in punctul de observatie.

NU presupune HTTP 403. `feed_check` le-a raportat ca `GOL`, nu ca eroare, deci statusul era
bun. Scopul scriptului asta e sa inlocuiasca presupunerea cu un corp de raspuns citit.
"""
import socket
import sys
import urllib.error
import urllib.request

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
import feedparser  # noqa: E402

from generator import config  # noqa: E402
from generator.fetch import USER_AGENT, TIMEOUT  # noqa: E402

# Esantion din cele 73 confirmate vii de acasa si tacute pe runner (run 30742957035,
# masurat 2026-08-02). Amestecat deliberat: presa nationala, presa locala si primarii,
# ca sa se vada daca modul de esec e acelasi pentru toate sau difera pe categorie.
DEFAULT_KEYS = [
    "recorder", "contributors", "zch", "bookhub",
    "stirilemoldovei", "cronicaolteniei",
    "pl_bacau_municipiul_bacau", "pl_prahova_municipiul_ploiesti",
    "pl_sibiu_oras_agnita", "pl_cluj_oras_huedin",
]

BODY_HEAD = 400   # octeti din corp afisati; destul pentru <?xml ... <rss> sau <!DOCTYPE html>


def _printable(raw: bytes, limit: int = BODY_HEAD) -> str:
    """Primii `limit` octeti, pe un singur rand, cu spatiul alb colapsat."""
    text = raw[:limit].decode("utf-8", errors="replace")
    return " ".join(text.split()) or "(corp gol)"


def probe(key: str, url: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            status = resp.status
            final_url = resp.url
            ctype = resp.headers.get("Content-Type", "-")
            cenc = resp.headers.get("Content-Encoding", "-")
            server = resp.headers.get("Server", "-")
            # Antetele de mai jos apar cand un WAF/CDN se interpune; absenta lor e la fel
            # de informativa ca prezenta, de aia se tiparesc chiar si goale.
            cfray = resp.headers.get("CF-Ray", "-")
            setck = "da" if resp.headers.get("Set-Cookie") else "nu"
    except urllib.error.HTTPError as exc:
        print(f"    HTTP {exc.code} {exc.reason} — nu e cazul 'tacut', e eroare pe status")
        return
    except (urllib.error.URLError, socket.timeout, ValueError) as exc:
        print(f"    EROARE {exc}")
        return

    feed = feedparser.parse(raw)
    bozo = feed.get("bozo", 0)
    bozo_exc = type(feed.get("bozo_exception")).__name__ if feed.get("bozo_exception") else "-"

    print(f"    status      {status}   octeti: {len(raw)}")
    if final_url != url:
        print(f"    REDIRECT    -> {final_url}")
    print(f"    content-type {ctype}   content-encoding: {cenc}")
    print(f"    server      {server}   CF-Ray: {cfray}   Set-Cookie: {setck}")
    print(f"    feedparser  intrari: {len(feed.entries)}   bozo: {bozo} ({bozo_exc})")
    print(f"    corp[:{BODY_HEAD}] {_printable(raw)}")


def main() -> int:
    keys = sys.argv[1:] or DEFAULT_KEYS
    print("=== silent probe ===")
    print(f"User-Agent: {USER_AGENT}")
    print(f"Surse: {len(keys)}\n")
    for key in keys:
        src = config.SOURCES.get(key)
        if not src:
            print(f"{key}: NU exista in config.SOURCES — sarit\n")
            continue
        print(f"{key}  [{src['category']}]  {src['url']}")
        probe(key, src["url"])
        print()
    print("Citire:")
    print("  intrari > 0                      -> sursa raspunde normal DE AICI (martor sanatos)")
    print("  intrari 0 + corp <!DOCTYPE html> -> pagina HTML servita cu 200 (challenge/eroare deghizata)")
    print("  intrari 0 + corp XML valid       -> feed autentic gol; sursa n-are ce publica")
    print("  intrari 0 + REDIRECT             -> ne duce in alta parte; urmareste destinatia")
    print("  intrari 0 + corp gol/trunchiat   -> raspuns taiat; suspecteaza CDN/WAF, nu parserul")
    print("\nRezultatul e diagnostic. Ce se face cu el (proxy, self-hosted runner, taierea")
    print("corpusului) e decizie de proprietar: topologie de deploy, CLAUDE.md sectiunea 10.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
