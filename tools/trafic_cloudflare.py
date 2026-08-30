#!/usr/bin/env python3
"""Cate cereri primeste izz.ro — citit din Cloudflare GraphQL Analytics.

DE CE EXISTA. Pe 2026-08-29 s-a masurat ca izz.ro nu are NICIO sursa de date de
trafic: contul Ahrefs raspunde `Insufficient plan` la 4 din 4 apeluri, inclusiv la
endpointul documentat ca gratuit (`IZZ-0251`); GA4 si Search Console raspund 401,
deci hostul trece dar lipseste credentiala (`IZZ-0250`); iar `api.cloudflare.com`
e refuzat de proxy-ul de agent dintr-o sesiune remote (`IZZ-0252`).

Al patrulea canal insa AJUNGE: runnerul de GitHub Actions. Si secretele
`CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` exista deja, folosite de
`deploy-worker.yml`. Deci intrebarea nu e "de unde luam un cont", ci "are tokenul
existent scope-ul de analytics?". Scriptul asta raspunde MASURAT, nu deductiv:
daca nu-l are, tipareste eroarea exacta a API-ului, care numeste permisiunea.

Rulat prin `.github/workflows/trafic.yml` (`workflow_dispatch`).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://api.cloudflare.com/client/v4/graphql"

INTEROGARE = """
query ($account: String!, $de_la: Time!, $pana_la: Time!) {
  viewer {
    accounts(filter: {accountTag: $account}) {
      workersInvocationsAdaptive(
        limit: 100
        filter: {datetime_geq: $de_la, datetime_leq: $pana_la}
        orderBy: [datetime_ASC]
      ) {
        sum { requests errors }
        dimensions { datetime scriptName }
      }
    }
  }
}
"""


def fereastra(zile: int, azi: date | None = None) -> tuple[str, str]:
    """Intervalul cerut, in formatul cerut de API. Pur, deci testabil fara retea."""
    # `date.today()` e naiv si ruff (DTZ, `IZZ-0124`) il refuza pe buna dreptate:
    # fereastra ceruta API-ului e in UTC, deci si "azi" trebuie sa fie tot in UTC.
    azi = azi or datetime.now(timezone.utc).date()
    return (f"{azi - timedelta(days=zile)}T00:00:00Z", f"{azi}T00:00:00Z")


def rezuma(raspuns: dict) -> list[tuple[str, int, int]]:
    """(script, cereri, erori) pe zi. Pur: primeste JSON-ul deja adus."""
    conturi = (((raspuns or {}).get("data") or {}).get("viewer") or {}).get("accounts") or []
    randuri = []
    for cont in conturi:
        for punct in cont.get("workersInvocationsAdaptive") or []:
            dim, suma = punct.get("dimensions") or {}, punct.get("sum") or {}
            randuri.append((f"{dim.get('datetime', '?')[:10]} {dim.get('scriptName', '?')}",
                            int(suma.get("requests") or 0), int(suma.get("errors") or 0)))
    return randuri


def erori(raspuns: dict) -> list[str]:
    """Mesajele de eroare ale API-ului. ASTA e rezultatul util cand tokenul n-are scope."""
    return [f"{e.get('code', '?')}: {e.get('message', '')}".strip()
            for e in (raspuns or {}).get("errors") or []]


def interogheaza(token: str, cont: str, zile: int = 7) -> dict:
    de_la, pana_la = fereastra(zile)
    corp = json.dumps({"query": INTEROGARE,
                       "variables": {"account": cont, "de_la": de_la, "pana_la": pana_la}}).encode()
    cerere = urllib.request.Request(API, data=corp, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(cerere, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        # Corpul unui 403 de la Cloudflare contine motivul; fara el n-am masurat nimic.
        try:
            return json.loads(exc.read())
        except Exception:
            return {"errors": [{"code": exc.code, "message": exc.reason}]}


def main() -> int:
    token, cont = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not token or not cont:
        print("LIPSA: CLOUDFLARE_API_TOKEN si/sau CLOUDFLARE_ACCOUNT_ID nu sunt in mediu.")
        return 2
    raspuns = interogheaza(token, cont)
    if (mesaje := erori(raspuns)):
        print("API-ul a refuzat. Mesajul EXACT, ca sa nu se deduca permisiunea lipsa:")
        for m in mesaje:
            print(f"  - {m}")
        print("\nDaca scrie ceva de genul 'Authentication error' / 'not authorized', tokenul din"
              "\nsecretul CLOUDFLARE_API_TOKEN are nevoie de permisiunea 'Account Analytics: Read'"
              "\n(Cloudflare -> My Profile -> API Tokens -> tokenul folosit de deploy-worker.yml).")
        return 1
    randuri = rezuma(raspuns)
    if not randuri:
        print("Raspuns valid, dar fara date in fereastra ceruta.")
        return 0
    total = sum(c for _, c, _ in randuri)
    print(f"Cereri catre Workers, ultimele 7 zile: {total:,}\n")
    for eticheta, cereri, err in randuri:
        print(f"  {eticheta:<32} {cereri:>10,} cereri  {err:>6,} erori")
    return 0


if __name__ == "__main__":
    sys.exit(main())
