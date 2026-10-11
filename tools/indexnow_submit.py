#!/usr/bin/env python
"""Anunta la IndexNow (Bing, Seznam, Yandex etc.) URL-urile al caror CONTINUT s-a schimbat.

  python tools/indexnow_submit.py --plan   # calculeaza ce s-a schimbat, scrie manifest + coada
  python tools/indexnow_submit.py --send   # trimite coada scrisa de --plan
  python tools/indexnow_submit.py          # ambele, intr-un pas (rulare locala/manuala)

DE CE PE HASH, NU PE FEREASTRA DE TIMP. Pana la 2026-08-06 filtrul era `published >= now-3h`,
adica „ce a aparut recent". Consecinta gasita la gap-check: o sinteza C care absoarbe o stire
noua isi rescrie titlul si corpul la ACELASI permalink (IZZ-0151/PR #142), dar isi pastreaza
`published` — deci daca evenimentul era mai vechi de 3 ore, versiunea actualizata NU era
anuntata nicaieri. La fel, un bump de `PROMPT_VERSION` reproceseaza ~1100 de articole si
niciunul nu ajungea la motoare. Feature livrat, efect zero pe indexare.

DE CE DOI PASI. Manifestul trebuie sa supravietuiasca rularii (runnerul CI e stateless), deci
se comite — dar anuntul trebuie sa plece DUPA ce continutul e publicat, adica dupa commit.
`--plan` ruleaza inainte de commit si lasa manifestul in arborele de lucru, unde intra in
commit-ul de continut care oricum se face; `--send` ruleaza dupa. Zero commituri in plus,
deci zero build-uri Cloudflare in plus (bugetul din build.yml §17 ramane neatins).

Daca push-ul esueaza, `build.yml` iese cu 1 si `--send` nu mai ruleaza, iar manifestul nu e
comis — deci URL-urile revin ca „schimbate" la rularea urmatoare. Invariantul se tine singur.

Cheia e publica prin protocol (motorul o citeste de la https://izz.ro/<cheie>.txt ca dovada
ca detinem domeniul); render.py scrie fisierul.

DE CE PREFLIGHT. „403" de la IndexNow are doua cauze complet diferite, iar codul singur nu le
distinge: (a) motorul nu poate citi cheia publica — zona izz.ro are bot protection, iar
runnerilor GitHub li s-a servit deja `cf-mitigated: challenge` (observat de deploy-failover);
(b) motorul citeste cheia, dar refuza domeniul pentru ea — „UserForbiddedToAccessSite". Masurat
2026-10-11: fisierul cu cheia raspunde 200 cu cheia in corp din trei clienti independenti
(inclusiv alte retele de datacenter), dar api.indexnow.org raspunde 403
UserForbiddedToAccessSite, adica (b) e activ ACUM si se vede abia din corpul raspunsului.
Preflight-ul acopera (a) inainte de POST: nu trimite nimic si nu marcheaza nimic cand cheia nu
e citibila de aici, iar mesajul spune care e pasul urmator.

DE CE `--reopen`. `--plan` marcheaza transa ca vazuta INAINTE de commit, iar `--send` ruleaza
dupa. Daca POST-ul esueaza, URL-urile ar ramane „vazute" si nu ar mai fi anuntate niciodata
(runnerul e stateless, coada efemera moare cu el). `--reopen` sterge din manifest exact
URL-urile care n-au plecat, deci revin in coada la rularea urmatoare — acelasi invariant ca la
push-ul esuat („manifestul nu se comite, deci URL-urile revin ca schimbate").
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config  # noqa: E402

STATE = os.path.join(config.ROOT, "data", "articles.json")
MANIFEST = os.path.join(config.ROOT, "data", "indexnow_seen.json")
QUEUE = os.path.join(config.ROOT, "data", ".indexnow_queue.json")   # gitignored, efemer
ENDPOINT = "https://api.indexnow.org/indexnow"
BATCH_MAX = 500          # plafonul protocolului IndexNow per cerere, nu o valoare aleasa aici
USER_AGENT = "izz-indexnow/1.0 (+https://izz.ro)"
TIMEOUT = 20


def _key_location() -> str:
    """Adresa publica de unde motorul isi verifica cheia (dovada de domeniu)."""
    return f"{config.SITE['url']}/{config.INDEXNOW_KEY}.txt"


def _http_get(url: str) -> tuple[int, bytes, dict]:
    """GET fara exceptii pe HTTP: intoarce si codul, si corpul, si antetele."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # nosec B310
            return resp.status, resp.read(8192), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(8192), dict(exc.headers or {})


def _http_post(url: str, payload: dict) -> tuple[int, str]:
    """POST fara exceptii pe HTTP: intoarce codul SI corpul.

    Corpul conteaza: `403` de la IndexNow are doua cauze complet diferite („n-am putut citi
    cheia" vs „refuz legatura cheie-domeniu"), iar textul lor e singurul care le distinge.
    Fara el, ambele arata la fel in jurnal si nu se poate sti ce e de facut.
    """
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # nosec B310
            return resp.status, resp.read(2048).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(2048).decode("utf-8", "replace")


def _motiv(status: int, corp: str) -> str:
    """Textul care transforma un cod de eroare intr-o cauza si un pas urmator."""
    if "UserForbiddedToAccessSite" in corp:
        return (" — motorul refuza DOMENIUL pentru cheia asta („User is unauthorized to access "
                "the site”), desi preflight-ul tocmai a citit cheia publica. Doua cauze ramase, "
                "distinse de o singura observatie: in Cloudflare, Security -> Events, filtreaza "
                f"pe calea /{config.INDEXNOW_KEY}.txt — daca acolo apare un challenge/block pe "
                "cererea motorului, vina e la bot protection (pe planul Free, Bot Fight Mode NU "
                "poate fi sărit de reguli WAF: fie IP Access Rule de tip Allow, fie oprirea lui "
                "— decizie de proprietar); daca nu apare nimic, fisierul chiar e servit si "
                "refuzul e legatura cheie↔domeniu, in contul motorului (verificarea site-ului "
                "in Bing Webmaster Tools sau o cheie noua generata acolo)")
    if status == 422:
        return " — lista contine URL-uri respinse (host diferit de cheie sau format invalid)"
    if status == 429:
        return " — rate limit al motorului"
    return f" — corp: {corp[:180]!r}" if corp else ""


def _preflight() -> tuple[bool, str]:
    """Poate motorul sa citeasca cheia de domeniu? `(ok, detaliu)` — nu ridica.

    Un `403` de la IndexNow inseamna aproape intotdeauna „n-am putut verifica cheia", nu
    „lista e rea". Verificarea o facem pe loc, ca mesajul de eroare sa fie diagnostic, nu cod.
    """
    url = _key_location()
    try:
        status, body, headers = _http_get(url)
    except Exception as exc:  # noqa: BLE001 - orice eroare de retea e „nu pot verifica"
        return False, f"nu am putut citi {url} ({exc})"
    if status == 200 and config.INDEXNOW_KEY.encode() in body:
        return True, f"cheia publica raspunde pe {url}"
    mitigat = str(headers.get("cf-mitigated") or headers.get("Cf-Mitigated") or "").lower()
    if status in (403, 503) and (mitigat == "challenge" or b"cf-chl" in body
                                 or b"Just a moment" in body or b"challenge-platform" in body):
        return False, (f"HTTP {status} + bot challenge pe {url}: zona izz.ro blocheaza "
                       "clientii non-browser din datacenter (aceeasi cauza ca sondele care "
                       "primesc 403 din runnerii GitHub)")
    return False, (f"HTTP {status} pe {url}, iar corpul nu contine cheia "
                   f"({len(body)} octeti primiti)")


def _remediation(detaliu: str) -> None:
    """Mesajul care transforma un 403 opac in pasul urmator concret."""
    print(f"::error::IndexNow: cheia de domeniu nu poate fi verificata de PE ACEST CLIENT "
          f"({detaliu}). Motoarele citesc {_key_location()} inainte sa accepte lista, deci "
          "orice trimitere primeste 403. Primul lucru de facut e sa distingi cauza: deschide "
          f"{_key_location()} intr-un browser obisnuit — daca raspunde 200 cu cheia in corp, "
          "fisierul e public si blocajul e pe clasa de client, adica pe bot protection "
          "(regula custom de User-Agent se poate excepta; Bot Fight Mode, pe planul Free, NU "
          "poate fi sărit de reguli WAF — se foloseste o IP Access Rule de tip Allow sau se "
          "opreste Bot Fight Mode, decizie de proprietar). Daca nici browserul nu-l vede, "
          "deploy-ul e vinovat si se repara in repo. Pana atunci nu se pierde nimic: "
          "URL-urile rămân neanuntate si reintra in coada la rularea urmatoare.")


def _url(a: dict) -> str:
    return f"{config.SITE['url']}/{a['category']}/{a['slug']}/"


def _hash(a: dict) -> str:
    """Amprenta a ceea ce VEDE cititorul. Se schimba exact cand pagina merita re-crawlata.

    Titlu + corp, atat: `published` nu intra (nu se schimba la o actualizare de sinteza, deci
    n-ar adauga nimic), iar campurile interne nu intra fiindca o reorganizare de stare nu e o
    schimbare de continut si ar trimite tot corpusul la motoare degeaba.

    64 de biti (16 hex) ajung: coliziunea care ar conta e „doua continuturi diferite ale
    ACELUIASI URL dau acelasi hash", nu coliziunea globala — spatiul e o pagina, nu corpusul.
    """
    corp = a.get("synthesis") if a.get("model") == "C" else a.get("teaser")
    return hashlib.sha1(f"{a.get('title', '')}\x00{corp or ''}".encode("utf-8")).hexdigest()[:16]


def _load(path: str, implicit):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return implicit


def _proaspete(arts: list, ore: float) -> list:
    """URL-urile publicate in ultimele `ore` — comportamentul de dinainte, pastrat pentru
    insamantarea manifestului la prima rulare."""
    taietura = datetime.now(timezone.utc) - timedelta(hours=ore)
    out = []
    for a in arts:
        try:
            dt = datetime.fromisoformat(a.get("published", ""))
        except (ValueError, TypeError):
            continue
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if dt >= taietura:
            out.append(_url(a))
    return out


def plan() -> int:
    """Compara starea cu manifestul; scrie manifestul nou si coada de trimis."""
    arts = [a for a in _load(STATE, []) if a.get("category") and a.get("slug")]
    curent = {_url(a): _hash(a) for a in arts}
    vazut = _load(MANIFEST, None)
    seed = vazut is None

    if seed:
        # PRIMA rulare: manifest inexistent. Nu trimitem cele ~2600 de URL-uri deodata — ar fi
        # un val fara informatie (motoarele le au deja din sitemap). Se INSAMANTEAZA manifestul
        # cu tot si se anunta doar ce e proaspat, adica exact comportamentul de dinainte.
        # De la a doua rulare incolo, diferenta pe hash preia treaba.
        ore = float(os.getenv("SINCE_HOURS", "3"))
        de_trimis = _proaspete(arts, ore)
        print(f">> IndexNow: manifest absent -> insamantez {len(curent)} URL-uri, "
              f"anunt doar {len(de_trimis)} proaspete (ultimele {ore:g}h)")
    else:
        de_trimis = [u for u, h in curent.items() if vazut.get(u) != h]
        noi = sum(1 for u in de_trimis if u not in vazut)
        print(f">> IndexNow: {len(de_trimis)} de anuntat ({noi} noi, "
              f"{len(de_trimis) - noi} cu continut schimbat) din {len(curent)} publicabile")

    # Peste plafon se trimite prima transa, iar restul NU se marcheaza ca vazute — altfel un
    # bump de PROMPT_VERSION (~1100 de articole eligibile deodata) ar pierde definitiv tot ce
    # depaseste plafonul. Asa, restul revine la rularea urmatoare pana se stinge coada.
    transa = de_trimis[:BATCH_MAX]
    if len(de_trimis) > len(transa):
        print(f"   plafon {BATCH_MAX}/cerere: {len(de_trimis) - len(transa)} raman "
              f"pentru rularea urmatoare")

    trimise = set(transa)
    if transa:
        # Poarta de dinaintea manifestului: fara cheie citibila public, motorul respinge tot
        # (403). Nu marcam nimic ca vazut — altfel transa s-ar pierde exact cand nu se poate
        # trimite — si nu scriem coada, ca pasul de send sa fie un no-op tacut.
        ok, detaliu = _preflight()
        if not ok:
            _remediation(detaliu)
            with open(QUEUE, "w", encoding="utf-8") as fh:
                json.dump([], fh, ensure_ascii=False)
            return 0
        print(f">> IndexNow: preflight ok ({detaliu})")

    if seed:
        # Se insamanteaza tot, MINUS ce a fost pus in coada dar n-a incaput in transa: alea
        # trebuie sa ramana nevazute ca sa iasa la rularea urmatoare. Fara exceptia asta, o
        # prima rulare cu peste `BATCH_MAX` articole proaspete (rulare de recuperare cu buget
        # marit) le-ar marca pe toate ca anuntate si diferenta nu s-ar mai anunta niciodata.
        amanate = set(de_trimis) - trimise
        manifest = {u: h for u, h in curent.items() if u not in amanate}
    else:
        # Manifestul pastreaza DOAR URL-urile inca in stare (articolele expira la TTL), altfel
        # ar creste la nesfarsit. Cele netrimise isi pastreaza hash-ul VECHI ca sa recada in
        # coada; cele noi care n-au incaput raman fara intrare, deci tot in coada.
        manifest = {u: (h if u in trimise else vazut[u])
                    for u, h in curent.items() if u in trimise or u in vazut}

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)
    with open(QUEUE, "w", encoding="utf-8") as fh:
        json.dump(transa, fh, ensure_ascii=False)
    return 0


def send() -> int:
    """Trimite coada scrisa de `plan`. Best-effort: raporteaza, NU pica build-ul.

    Cod de iesire: 0 = nimic de trimis sau trimitere reusita; 1 = coada n-a plecat (pasul
    din `build.yml` e `continue-on-error`, deci build-ul nu se opreste, dar pasul urmator
    vede `outcome == 'failure'` si redeschide URL-urile cu `--reopen`).
    """
    urls = _load(QUEUE, [])
    if not urls:
        print(">> IndexNow: nimic de anuntat.")
        return 0
    ok, detaliu = _preflight()
    if not ok:
        _remediation(detaliu)
        return 1
    payload = {
        "host": config.SITE["url"].split("//")[1],
        "key": config.INDEXNOW_KEY,
        "keyLocation": _key_location(),
        "urlList": urls,
    }
    try:
        status, corp = _http_post(ENDPOINT, payload)
    except Exception as exc:
        # `::error::` intentionat, nu doar print: in acest punct manifestul e deja comis,
        # deci aceste URL-uri nu vor mai fi propuse (hash-ul lor e marcat ca vazut) pana nu
        # le redeschide pasul urmator din workflow. Pierderea trebuie sa fie vizibila.
        print(f"::error::IndexNow: esec la trimiterea a {len(urls)} URL-uri ({exc}) — "
              f"coada rămâne pe disc pentru `--reopen`")
        return 1
    if 200 <= status < 300:
        print(f">> IndexNow: {len(urls)} URL-uri anuntate, HTTP {status}")
        try:
            os.remove(QUEUE)
        except OSError:
            pass
        return 0
    print(f"::error::IndexNow: esec la trimiterea a {len(urls)} URL-uri (HTTP {status})"
          f"{_motiv(status, corp)} — coada rămâne pe disc pentru `--reopen`")
    return 1


def reopen() -> int:
    """Redeschide URL-urile din coada care n-au plecat: ies din manifest, deci revin in coada.

    Se cheama dupa un `send()` esuat. Nu atinge hash-urile altor URL-uri si nu comite nimic
    (commit-ul il face pasul de workflow), ca unealta sa rămână testabila fara git.
    """
    urls = _load(QUEUE, [])
    manifest = _load(MANIFEST, {})
    redeschise = [u for u in urls if u in manifest]
    for u in redeschise:
        manifest.pop(u, None)
    if redeschise:
        with open(MANIFEST, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)
    try:
        os.remove(QUEUE)
    except OSError:
        pass
    print(f">> IndexNow: {len(redeschise)} URL-uri redeschise pentru reincercare "
          f"(din {len(urls)} in coada) — revin la urmatoarea rulare.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="IndexNow: anunta URL-urile cu continut schimbat")
    ap.add_argument("--plan", action="store_true", help="calculeaza si scrie manifest + coada")
    ap.add_argument("--send", action="store_true", help="trimite coada scrisa de --plan")
    ap.add_argument("--reopen", action="store_true",
                    help="dupa un send esuat: scoate din manifest URL-urile care n-au plecat")
    arg = ap.parse_args()
    if arg.reopen:
        return reopen()
    if arg.plan and not arg.send:
        return plan()
    if arg.send and not arg.plan:
        return send()
    return plan() or send()


if __name__ == "__main__":
    sys.exit(main())
