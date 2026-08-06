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
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config  # noqa: E402

STATE = os.path.join(config.ROOT, "data", "articles.json")
MANIFEST = os.path.join(config.ROOT, "data", "indexnow_seen.json")
QUEUE = os.path.join(config.ROOT, "data", ".indexnow_queue.json")   # gitignored, efemer
ENDPOINT = "https://api.indexnow.org/indexnow"
BATCH_MAX = 500          # plafonul protocolului IndexNow per cerere, nu o valoare aleasa aici


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
    """Trimite coada scrisa de `plan`. Best-effort: raporteaza, nu pica build-ul."""
    urls = _load(QUEUE, [])
    if not urls:
        print(">> IndexNow: nimic de anuntat.")
        return 0
    payload = {
        "host": config.SITE["url"].split("//")[1],
        "key": config.INDEXNOW_KEY,
        "keyLocation": f"{config.SITE['url']}/{config.INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f">> IndexNow: {len(urls)} URL-uri anuntate, HTTP {resp.status}")
    except Exception as exc:
        # `::warning::` intentionat, nu doar print: in acest punct manifestul e deja comis,
        # deci aceste URL-uri nu vor mai fi propuse (hash-ul lor e marcat ca vazut) pana la
        # urmatoarea lor modificare. Pierderea trebuie sa fie vizibila in Actions, nu tacuta.
        print(f"::warning::IndexNow: esec la trimiterea a {len(urls)} URL-uri ({exc}) — "
              f"deja marcate ca vazute, NU vor fi reincercate")
    try:
        os.remove(QUEUE)
    except OSError:
        pass
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="IndexNow: anunta URL-urile cu continut schimbat")
    ap.add_argument("--plan", action="store_true", help="calculeaza si scrie manifest + coada")
    ap.add_argument("--send", action="store_true", help="trimite coada scrisa de --plan")
    arg = ap.parse_args()
    if arg.plan and not arg.send:
        return plan()
    if arg.send and not arg.plan:
        return send()
    return plan() or send()


if __name__ == "__main__":
    sys.exit(main())
