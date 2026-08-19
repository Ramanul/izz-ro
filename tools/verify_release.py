#!/usr/bin/env python3
"""Verifică dacă Cloudflare Pages și domeniul public servesc un release derivat din SHA-ul așteptat.

Un simplu test de HTTP 200 nu prinde cel mai costisitor incident IZZ.ro: buildul Pages sare sau
servește un commit vechi, iar site-ul pare sănătos, dar nu conține conținutul publicat. Manifestul
/build.json este generat în același build ca HTML-ul; această probă îl așteaptă pe ambele origini.

Acceptă un commit mai nou decât SHA-ul de conținut: pe `main` pot apărea modificări editoriale sau
de cod între pushul pipeline-ului și terminarea deployului, iar buildul nou conține totuși release-ul
cerut. Relația de descendență este verificată prin GitHub Compare API, nu presupusă după ordine.
"""

from __future__ import annotations

import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO = os.getenv("RELEASE_REPO", "Ramanul/izz-ro")
EXPECTED = os.getenv("EXPECTED_COMMIT", "").strip()
BASE_URLS = tuple(
    url.strip().rstrip("/")
    for url in os.getenv("RELEASE_BASE_URLS", "https://izz-ro.pages.dev,https://izz.ro").split(",")
    if url.strip()
)
POLL_SECONDS = int(os.getenv("RELEASE_POLL_SECONDS", "30"))
TIMEOUT_SECONDS = int(os.getenv("RELEASE_TIMEOUT_SECONDS", "1500"))


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
    deployed = str(data.get("commit") or "")
    if not deployed or deployed == "local":
        return False, "manifest fără SHA de Pages"
    if data.get("branch") != "main":
        return False, f"ramură neașteptată: {data.get('branch')!r}"
    if not _is_expected_or_descendant(deployed):
        return False, f"servește {deployed[:12]}, care nu include {EXPECTED[:12]}"
    if not isinstance(data.get("article_count"), int) or data["article_count"] < 1:
        return False, "manifest cu article_count invalid"
    return True, f"{deployed[:12]} (articole: {data['article_count']})"


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
            return 0
        if time.monotonic() >= deadline:
            print("Release-ul nu a devenit verificabil înainte de expirarea intervalului:", file=sys.stderr)
            for base, detail in last.items():
                print(f"- {base}: {detail}", file=sys.stderr)
            return 1
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
