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

DELIBERAT diferit de fetcher-ul de productie, si de aia rezultatul e diagnostic, nu dovada
echivalenta cu productia: se face O SINGURA cerere simpla, fara retry si fara validatorii de
cache (ETag / If-Modified-Since). Retry-ul ar masca fix fenomenul cautat — o incercare care
reuseste dupa doua esecuri arata "200 ok" si ascunde ca prima a fost respinsa; iar un 304
conditional ar intoarce un corp gol legitim, care aici s-ar citi gresit ca "feed gol".
Pentru masuratoarea echivalenta cu productia exista deja `feed_check.py`, care chiar cheama
`_fetch_one_guarded`. Astea doua raspund la intrebari diferite; nu le confunda.
"""
import gzip
import http.client
import os
import socket
import sys
import time
import urllib.error
import urllib.request
import zlib

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

BODY_HEAD = 400        # octeti din corp afisati; destul pentru <?xml ... <rss> sau <!DOCTYPE html>
MAX_READ = 2_000_000   # plafon de citire; un corp mai mare decat atat e el insusi un rezultat

# Semnatura interstitialului anti-bot masurat 2026-08-02 pe 72 din 74 de surse tacute de pe
# runner (65 de pe openresty/1.31.1.1). Vine cu HTTP 200 si un corp HTTP valid, deci nici
# statusul nici parserul nu-l semnaleaza; singurul lucru care il distinge e continutul.
CHALLENGE_MARK = b"One moment, please"
# Pagina isi cere singura reincarcarea dupa 5000 ms. Asteptam putin peste, o singura data.
RETRY_AFTER_S = float(os.environ.get("IZZ_PROBE_RETRY_S", "6"))
RETRY_ON_CHALLENGE = os.environ.get("IZZ_PROBE_RETRY", "") == "1"


def _printable(raw: bytes, limit: int = BODY_HEAD) -> str:
    """Primii `limit` octeti, pe un singur rand, cu spatiul alb colapsat."""
    text = raw[:limit].decode("utf-8", errors="replace")
    return " ".join(text.split()) or "(corp gol)"


def _read_body(resp) -> tuple[bytes, str | None]:
    """Citeste corpul marginit, si intoarce (octeti, nota-de-anomalie sau None).

    Un raspuns taiat la mijloc ridica `http.client.IncompleteRead`, care NU e subclasa de
    `URLError` — deci fara ramura asta o singura sursa trunchiata ar opri toata proba, fix
    pe modul de esec pe care scriptul il are in lista de diagnostice.
    """
    try:
        raw = resp.read(MAX_READ + 1)
    except http.client.IncompleteRead as exc:
        # Octetii primiti inainte de taiere sunt exact dovada cautata; nu-i arunca.
        return exc.partial, f"TRUNCHIAT de sursa: {len(exc.partial)} octeti primiti, {exc.expected} lipsa"
    except http.client.HTTPException as exc:
        return b"", f"raspuns invalid la nivel HTTP: {type(exc).__name__}: {exc}"

    if len(raw) > MAX_READ:
        return raw[:MAX_READ], f"taiat DE PROBA la {MAX_READ} octeti (corpul e mai mare)"

    declared = resp.headers.get("Content-Length")
    if declared and declared.isdigit() and len(raw) < int(declared):
        return raw, f"citire scurta: {len(raw)} octeti primiti, Content-Length spunea {declared}"
    return raw, None


def _decode_body(raw: bytes, cenc: str) -> tuple[bytes | None, str | None]:
    """Decomprima corpul daca e nevoie. Intoarce (octeti_utilizabili sau None, nota).

    Conteaza pentru ca un corp comprimat afisat brut arata ca gunoi binar, iar gunoiul
    binar s-ar citi gresit ca "raspuns corupt". Diagnostic fals — exact ce nu are voie
    scriptul asta sa produca.
    """
    enc = (cenc or "").strip().lower()
    if enc in ("", "-", "identity"):
        return raw, None
    try:
        if enc == "gzip":
            return gzip.decompress(raw), "decomprimat gzip"
        if enc == "deflate":
            return zlib.decompress(raw, -zlib.MAX_WBITS), "decomprimat deflate"
    except (OSError, zlib.error) as exc:
        return None, f"decomprimare {enc} esuata ({type(exc).__name__}) — corpul de mai jos e brut"
    return None, f"Content-Encoding '{enc}' nesuportat aici — corpul de mai jos e brut"


def _is_challenge(body: bytes) -> bool:
    """True daca raspunsul e interstitialul anti-bot, nu continut."""
    return CHALLENGE_MARK in body[:4000]


def probe(key: str, url: str, _retried: bool = False) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw, read_note = _read_body(resp)
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
    except http.client.HTTPException as exc:
        print(f"    EROARE HTTP {type(exc).__name__}: {exc}")
        return

    body, dec_note = _decode_body(raw, cenc)
    parsed = body if body is not None else raw

    if _is_challenge(parsed):
        if RETRY_ON_CHALLENGE and not _retried:
            print(f"    CHALLENGE   interstitial anti-bot; reincerc o data dupa {RETRY_AFTER_S}s")
            time.sleep(RETRY_AFTER_S)
            return probe(key, url, _retried=True)
        marca = " (si dupa reincercare)" if _retried else ""
        print(f"    CHALLENGE   interstitial anti-bot servit cu {status}{marca}")

    feed = feedparser.parse(parsed)
    bozo = feed.get("bozo", 0)
    bozo_exc = type(feed.get("bozo_exception")).__name__ if feed.get("bozo_exception") else "-"

    print(f"    status      {status}   octeti: {len(raw)}")
    if final_url != url:
        print(f"    REDIRECT    -> {final_url}")
    print(f"    content-type {ctype}   content-encoding: {cenc}")
    print(f"    server      {server}   CF-Ray: {cfray}   Set-Cookie: {setck}")
    if read_note:
        print(f"    ANOMALIE    {read_note}")
    if dec_note:
        print(f"    corp        {dec_note}")
    print(f"    feedparser  intrari: {len(feed.entries)}   bozo: {bozo} ({bozo_exc})")
    print(f"    corp[:{BODY_HEAD}] {_printable(parsed)}")


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
    print("  linia CHALLENGE                  -> interstitial anti-bot, NU sursa moarta")
    print("  linia ANOMALIE                   -> raspuns taiat sau mai scurt decat Content-Length")
    print("\nRezultatul e diagnostic, o singura cerere fara retry (vezi docstring-ul).")
    print("Ce se face cu el (proxy, self-hosted runner, taierea corpusului) e decizie de")
    print("proprietar: topologie de deploy, CLAUDE.md sectiunea 10.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
