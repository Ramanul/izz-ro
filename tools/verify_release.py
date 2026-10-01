#!/usr/bin/env python3
"""Verifică dacă Cloudflare Workers și domeniul public servesc release-ul așteptat.

Un simplu test de HTTP 200 nu prinde incidentul critic IZZ.ro: deployul poate servi un commit vechi,
în timp ce site-ul pare sănătos. Manifestul `/build.json` este generat în același build ca HTML-ul;
această probă verifică manifestul pe toate originile configurate.

Acceptă un commit mai nou decât SHA-ul de conținut: pe `main` pot apărea modificări editoriale sau
de cod între pushul pipeline-ului și terminarea deployului, iar buildul nou conține totuși release-ul
cerut. Relația de descendență este verificată prin GitHub Compare API, nu presupusă după ordine.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO = os.getenv("RELEASE_REPO", "Ramanul/izz-ro")
EXPECTED = os.getenv("EXPECTED_COMMIT", "").strip()
# Originile publice verificate. `izz.ro` este domeniul si este mereu in lista in CI. A doua origine
# este configurabila pentru o ruta fara bot challenge; in productie `build.yml` o seteaza la Worker
# origin. Nesetata, sonda verifica doar domeniul public — nu inventam o origine alternativa.
_ALT_ORIGIN = os.getenv("RELEASE_ALT_ORIGIN", "").strip().rstrip("/")
_IMPLICIT = ",".join(u for u in (_ALT_ORIGIN, "https://izz.ro") if u)
BASE_URLS = tuple(
    url.strip().rstrip("/")
    for url in os.getenv("RELEASE_BASE_URLS", _IMPLICIT).split(",")
    if url.strip()
)
POLL_SECONDS = int(os.getenv("RELEASE_POLL_SECONDS", "30"))
TIMEOUT_SECONDS = int(os.getenv("RELEASE_TIMEOUT_SECONDS", "1500"))

# Mirror-ul: ținta failover-ului, verificată NEBLOCANT și pe ALT criteriu (`IZZ-0370`).
#
# De ce exista. Pana azi, prospetimea mirror-ului nu era verificata de nimeni: `monitor.yml`
# il probeaza la fiecare 10 minute dar compara doar codul HTTP, iar sonda asta ii sarea peste
# el. Adica exact originea pe care comutam cand primarul cade era singura despre care nu
# stiam daca serveste continut vechi — chiar esecul descris in docstring-ul de sus.
#
# De ce dupa TIMESTAMP, nu dupa commit ca originile primare. Jobul `mirror` face checkout pe
# `content_sha`, dar manifestul ia commitul din `GITHUB_SHA` (SHA-ul care a declansat rularea,
# un STRAMOS al continutului), fiindca in `render._write_build_metadata` `GITHUB_SHA` are
# precedenta peste `BUILD_COMMIT_SHA`. Deci o comparatie de commit ar raporta „vechi" la
# fiecare rulare, corect tehnic si inutil practic. `generated_at` masoara direct ce conteaza:
# cat de veche e copia.
#
# Remediul curat cere DOUA schimbari, nu una — prima versiune a acestui comentariu prescria doar
# a doua, care singura n-ar fi facut nimic:
#   (a) `BUILD_COMMIT_SHA` trebuie sa BATA `GITHUB_SHA` in `render._write_build_metadata`.
#       Facut: e acum primul in lant, fiindca e override EXPLICIT, iar celelalte sunt valori
#       deduse din mediu. Fara asta, pasul (b) e inert: `GITHUB_SHA` e mereu setat in Actions.
#   (b) o linie `BUILD_COMMIT_SHA: ${{ needs.pipeline.outputs.content_sha }}` in pasul de render
#       al jobului `mirror`. Blocata in sesiune de hook-ul de control-plane, verificat incercand:
#       `DENY: direct agent edit blocked for .github/workflows/build.yml`.
#
# De ce NEBLOCANT. Cand sonda asta ruleaza, primarul a servit deja release-ul cerut; site-ul
# public functioneaza. Un mirror ramas in urma degradeaza redundanta, nu publicarea, si a face
# pipeline-ul rosu pentru asta ar opri stirile din cauza plasei de siguranta. `monitor.yml`
# trateaza identic: `::warning::` pentru mirror jos, `::error::` doar cand cad ambele origini.
MIRROR_URL = os.getenv("RELEASE_MIRROR_URL", "https://ramanul.github.io").strip().rstrip("/")
# 360 min: cadenta reala masurata e ~4h mediana, cu maxim observat 369 min (`IZZ-0364`), deci
# un prag mai strans ar suna alarma la fiecare gol normal de planificator.
MIRROR_MAX_AGE_MIN = int(os.getenv("RELEASE_MIRROR_MAX_AGE_MIN", "360"))


def _get_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "izz-release-probe/1.0 (+https://izz.ro)"})
    with urlopen(req, timeout=20) as response:  # nosec B310: URL-uri controlate de configurarea CI
        return json.loads(response.read().decode("utf-8"))


def _is_expected_or_descendant(deployed: str) -> bool:
    if deployed == EXPECTED:
        return True
    url = f"https://api.github.com/repos/{REPO}/compare/{EXPECTED}...{deployed}"
    try:
        data = _get_json(url)
    except (HTTPError, URLError, ValueError) as exc:
        print(f"  GitHub Compare indisponibil pentru {deployed[:12]}: {exc}")
        return False
    return data.get("status") in {"identical", "ahead"}


def _probe(base: str) -> tuple[bool, str]:
    nonce = f"release={EXPECTED[:12]}-{int(time.time())}"
    try:
        data = _get_json(f"{base}/build.json?{nonce}")
    except (HTTPError, URLError, ValueError) as exc:
        return False, f"manifest indisponibil ({exc})"
    if not isinstance(data, dict):
        return False, f"manifest care nu e obiect JSON: {type(data).__name__}"
    deployed = str(data.get("commit") or "")
    if not deployed or deployed == "local":
        return False, "manifest fără SHA public"
    if data.get("branch") != "main":
        return False, f"ramură neașteptată: {data.get('branch')!r}"
    if not _is_expected_or_descendant(deployed):
        return False, f"servește {deployed[:12]}, care nu include {EXPECTED[:12]}"
    if not isinstance(data.get("article_count"), int) or data["article_count"] < 1:
        return False, "manifest cu article_count invalid"
    return True, f"{deployed[:12]} (articole: {data['article_count']})"


def verifica_mirror(base: str = "", max_age_min: int = 0) -> tuple[bool, str]:
    """Cât de veche e copia de pe mirror. `(ok, detaliu)`; nu ridică și nu blochează.

    Returnează `False` și pentru mirror inaccesibil, și pentru manifest fără `generated_at`:
    ambele înseamnă „nu pot ști dacă plasa e bună", iar necunoscutul se raportează, nu se
    presupune verde — exact eșecul „sondă verde-pe-nimic" din 2026-08-21.
    """
    base = (base or MIRROR_URL).rstrip("/")
    max_age_min = max_age_min or MIRROR_MAX_AGE_MIN
    if not base:
        return True, "neconfigurat, sărit"
    try:
        data = _get_json(f"{base}/build.json?mirror={int(time.time())}")
    except (HTTPError, URLError, ValueError) as exc:
        return False, f"manifest indisponibil ({exc})"
    # JSON valid sintactic dar care nu e obiect — `[]` dupa o publicare stricata — ar da
    # `AttributeError` pe `.get`, adica un traceback si cod de iesire nenul TOCMAI in bucata
    # proiectata sa fie neblocanta. Ar fi transformat plasa de siguranta in blocaj.
    if not isinstance(data, dict):
        return False, f"manifest care nu e obiect JSON: {type(data).__name__}"
    brut = str(data.get("generated_at") or "")
    if not brut:
        return False, "manifest fără `generated_at`"
    try:
        generat = datetime.fromisoformat(brut)
    except ValueError:
        return False, f"`generated_at` neinterpretabil: {brut!r}"
    if generat.tzinfo is None:
        generat = generat.replace(tzinfo=timezone.utc)
    varsta = (datetime.now(timezone.utc) - generat).total_seconds() / 60
    detaliu = f"generat acum {varsta:.0f} min (prag {max_age_min})"
    return varsta <= max_age_min, detaliu


def main() -> int:
    if len(EXPECTED) < 7:
        print("EXPECTED_COMMIT trebuie să conțină SHA-ul commitului publicat.", file=sys.stderr)
        return 2
    if not BASE_URLS:
        print("RELEASE_BASE_URLS este gol.", file=sys.stderr)
        return 2

    deadline = time.monotonic() + TIMEOUT_SECONDS
    last: dict[str, str] = {}
    while True:
        all_ready = True
        for base in BASE_URLS:
            ok, detail = _probe(base)
            last[base] = detail
            print(f"{'ok' if ok else 'wait'}  {base}: {detail}")
            all_ready = all_ready and ok
        if all_ready:
            print(f"Release verificat pentru {EXPECTED[:12]} pe {len(BASE_URLS)} origini.")
            # Mirror-ul DUPĂ originile primare, și doar o dată: publicarea e deja confirmată,
            # aici se raportează starea plasei de siguranță. Nu schimbă codul de ieșire.
            ok_mir, det_mir = verifica_mirror()
            print(f"{'ok' if ok_mir else 'ATENTIE'}  mirror {MIRROR_URL}: {det_mir}")
            if not ok_mir:
                print(f"::warning::mirror în urmă sau necunoscut ({det_mir}) — redundanța e "
                      "degradată, publicarea NU e afectată")
            return 0
        if time.monotonic() >= deadline:
            print("Release-ul nu a devenit verificabil înainte de expirarea intervalului:", file=sys.stderr)
            for base, detail in last.items():
                print(f"- {base}: {detail}", file=sys.stderr)
            return 1
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    # Windows: stdout/stderr trebuie sa afiseze diacritice fara sa mascheze un esec real cu
    # UnicodeEncodeError. In CI (Linux, UTF-8) nu se vede, dar scriptul este util si local.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
