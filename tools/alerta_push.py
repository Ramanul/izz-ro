#!/usr/bin/env python3
"""Trimite o alertă de ultimă oră către cititorii abonați (Web Push, VAPID).

    python tools/alerta_push.py --stare
    python tools/alerta_push.py --uscat --titlu "..." --text "..." --url "..."
    python tools/alerta_push.py --titlu "..." --text "..." --url "..."

DE CE EXISTĂ UNEALTA, ȘI NU UN BUTON ÎN SITE. Cine apasă „trimite" decide ce e
*breaking news* pentru toți cititorii — o decizie editorială, nu una tehnică, deci nu se
automatizează. Unealta asta doar face ca decizia să se poată executa într-o singură
comandă, cu aceleași reguli pe care le aplică și serverul.

REGULILE SUNT ALE SERVERULUI, NU ALE UNELTEI. Politica «Zgomot zero» și plafonul de o
alertă pe zi trăiesc în `infra/push.js::verificaAlerta` și în cheia `cap:<zi>` din KV, nu
aici: un client care le-ar aplica singur ar putea fi ocolit cu un `curl`, iar o regulă care
se poate ocoli nu e o regulă. Unealta doar raportează refuzul, în românește.

TRIMITEREA E PE LOTURI, DINTR-UN MOTIV MĂSURABIL: planul Workers Free dă 10 ms de CPU per
invocare (developers.cloudflare.com/workers/platform/pricing/), cât pentru câteva zeci de
 perechi ECDH + AES-GCM, nu pentru mii. Un lot mic, reluat până la epuizarea cursorului,
înseamnă că fiecare lot primește bugetul lui întreg.

STDLIB-ONLY, deliberat: `requests` nu e în requirements.txt și n-o să intre pentru un
singur POST pe zi.

Coduri de ieșire: 0 trimis · 1 refuzat de politică sau de plafon · 2 lipsă configurație ·
3 eroare de rețea/răspuns neașteptat.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

IMPLICIT_URL = "https://izz.ro"
PAUZA_LOTURI = 1.0   # secunde între loturi; lasă KV-ul să respire și lasă loc de Ctrl-C
TIMEOUT = 30


def _baza() -> str:
    return (os.getenv("PUSH_URL") or IMPLICIT_URL).rstrip("/")


def _cheie() -> str:
    return (os.getenv("PUSH_ADMIN_TOKEN") or "").strip()


def _cere(cale: str, corp: dict | None = None, metoda: str | None = None) -> tuple[int, dict]:
    """Un apel JSON către Worker. Intoarce (status, corp_parsat)."""
    date = None
    antete = {"accept": "application/json"}
    if corp is not None:
        date = json.dumps(corp).encode("utf-8")
        antete["content-type"] = "application/json"
    if _cheie():
        antete["authorization"] = f"Bearer {_cheie()}"
    cerere = urllib.request.Request(
        _baza() + cale, data=date, headers=antete, method=metoda or ("POST" if date else "GET"))
    try:
        with urllib.request.urlopen(cerere, timeout=TIMEOUT) as raspuns:
            return raspuns.status, json.loads(raspuns.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except (ValueError, OSError):
            return e.code, {}
    except (urllib.error.URLError, OSError) as e:
        print(f"!! rețea: {e}", file=sys.stderr)
        return 0, {}


def stare() -> int:
    status, date = _cere("/push/stare")
    if status == 0:
        return 3
    if status != 200:
        print(f"!! serverul a răspuns {status}: {date}", file=sys.stderr)
        return 2 if status in (401, 503) else 3
    print(f"Abonamente: {date.get('abonati', '?')}")
    ultima = date.get("ultima")
    if ultima:
        print(f"Ultima alertă: {ultima.get('la', '?')} — „{ultima.get('titlu', '')}” "
              f"({ultima.get('trimise', 0)} trimise, {ultima.get('esecuri', 0)} eșecuri, "
              f"{ultima.get('sterse', 0)} abonamente moarte șterse)")
    else:
        print("Ultima alertă: niciuna.")
    return 0


def trimite(titlu: str, text: str, url: str, uscat: bool, limita: int | None) -> int:
    if not _cheie() and not uscat:
        # Repetiția are nevoie de cheie și ea (serverul cere autorizare), dar refuzul ei
        # blochează doar repetiția: mesajul spune exact ce lipsește.
        print("!! lipsește PUSH_ADMIN_TOKEN (secretul de pe Worker). "
              "Vezi infra/PUSH-SETUP.md §3.", file=sys.stderr)
        return 2

    loturi = 0
    total = {"trimise": 0, "esecuri": 0, "sterse": 0}
    cursor = None
    while True:
        corp = {"titlu": titlu, "text": text, "url": url, "uscat": uscat}
        if limita:
            corp["limita"] = limita
        if cursor:
            corp["cursor"] = cursor
        status, date = _cere("/push/trimite", corp)
        if status == 0:
            return 3
        if status == 422:
            print("REFUZAT — alerta nu trece politica «Zgomot zero»:")
            for motiv in date.get("motive", []):
                print(f"  · {motiv}")
            return 1
        if status == 409:
            print(f"REFUZAT — {'; '.join(date.get('motive', ['maxim o alertă pe zi']))}")
            return 1
        if status in (401, 503):
            print(f"!! {date.get('eroare', date)}", file=sys.stderr)
            return 2
        if status != 200:
            print(f"!! răspuns neașteptat {status}: {date}", file=sys.stderr)
            return 3

        loturi += 1
        if uscat:
            print(f"REPETIȚIE: ar pleca la {date.get('arFiPlecat', 0)} abonamente "
                  f"(lotul {loturi}). Nimic nu s-a trimis.")
        else:
            for camp in total:
                total[camp] += int(date.get(camp, 0) or 0)
            print(f"lotul {loturi}: {date.get('trimise', 0)} trimise, "
                  f"{date.get('esecuri', 0)} eșecuri, {date.get('sterse', 0)} abonamente moarte șterse")
        cursor = date.get("cursor_urmator")
        if not cursor:
            break
        time.sleep(PAUZA_LOTURI)

    if not uscat:
        print(f"\nGata: {total['trimise']} alerte trimise, {total['esecuri']} eșecuri, "
              f"{total['sterse']} abonamente moarte șterse, în {loturi} lot(uri).")
        print(f"Consemnat: {datetime.now(timezone.utc).isoformat()} — următoarea alertă, mâine.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="alertă de ultimă oră — IZZ.ro")
    ap.add_argument("--titlu", help="titlul alertei (12–90 caractere, fără „!”/„?”/emoji)")
    ap.add_argument("--text", help="textul alertei (30–200 caractere)")
    ap.add_argument("--url", help="pagina articolului: https://izz.ro/{categorie}/{slug}/")
    ap.add_argument("--uscat", action="store_true",
                    help="repetiție: validează și numără, dar NU trimite și NU consumă ziua")
    ap.add_argument("--limita", type=int, help="abonamente per lot (implicit 40, maxim 100)")
    ap.add_argument("--stare", action="store_true", help="câți abonați sunt și când s-a trimis ultima dată")
    args = ap.parse_args(argv)

    if args.stare:
        return stare()
    if not (args.titlu and args.text and args.url):
        ap.error("--titlu, --text și --url sunt obligatorii (sau folosește --stare)")
    return trimite(args.titlu, args.text, args.url, args.uscat, args.limita)


if __name__ == "__main__":
    sys.exit(main())
