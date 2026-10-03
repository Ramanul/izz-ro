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

# AGREGAT PE ZI. Doua greseli, amandoua masurate pe runner, amandoua scrise aici ca sa nu
# se repete:
#   1. Prima versiune grupa dupa `datetime` — granularitate de SECUNDA — deci fiecare rand
#      avea „1 cerere", iar totalul tiparit era chiar `limit: 100`. `izz-ro` nici nu aparea,
#      taiat de limita, fiindca `datetime_ASC` livra cea mai veche zi.
#   2. A doua versiune a cerut `workersInvocationsAdaptiveGroups`, dedus prin analogie cu
#      alte seturi Cloudflare care au varianta `...Groups`. API-ul a raspuns
#      `unknown field "workersInvocationsAdaptiveGroups"`: setul NU exista.
# Corect e setul din prima versiune, cu DIMENSIUNEA schimbata: `date` in loc de `datetime`.
# Agregarea o face API-ul pe dimensiunile cerute; problema n-a fost niciodata setul.
INTEROGARE = """
query ($account: String!, $de_la: Time!, $pana_la: Time!) {
  viewer {
    accounts(filter: {accountTag: $account}) {
      workersInvocationsAdaptive(
        limit: 1000
        filter: {datetime_geq: $de_la, datetime_leq: $pana_la}
        orderBy: [date_ASC]
      ) {
        sum { requests errors }
        dimensions { date scriptName status }
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
            eticheta = f"{str(dim.get('date', '?'))[:10]} {dim.get('scriptName', '?')}"
            # `status` e in dimensiuni fiindca „erori" nu inseamna acelasi lucru peste tot:
            # documentatia Cloudflare separa success / clientDisconnected / scriptThrewException /
            # exceededResources / internalError. Masurat 2026-08-30: izz-failover avea ~1.400 de
            # „erori" pe zi, aproape CONSTANTE, in timp ce cererile variau intre 1.940 si 3.391.
            # O cifra care nu se misca odata cu traficul nu e proportionala cu utilizatorii —
            # dar care dintre stari e, nu se poate deduce, se cere de la API.
            if (stare := dim.get("status")):
                eticheta += f"  [{stare}]"
            randuri.append((eticheta,
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
    # Semgrep semnaleaza `urlopen` cu argument ne-literal (dynamic-urllib-use-detected) si are
    # dreptate ca REGULA: `urllib` accepta `file://`, deci un URL venit din afara ar citi fisiere.
    # Aici nu vine din afara — `API` e constanta de modul, iar din exterior intra doar tokenul si
    # id-ul de cont, amandoua in ANTET si in CORP, niciodata in URL. Garda de mai jos nu e o
    # suprimare: e invarianta scrisa executabil, ca o editare viitoare care ar parametriza
    # endpointul sa pice AICI, nu in productie. Acelasi principiu ca `guard.url_ostil`.
    if not API.startswith("https://api.cloudflare.com/"):
        raise ValueError(f"endpoint neasteptat: {API!r}")
    cerere = urllib.request.Request(API, data=corp, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(cerere, timeout=30) as r:  # noqa: S310 - vezi garda de mai sus
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        # Corpul unui 403 de la Cloudflare contine motivul; fara el n-am masurat nimic.
        try:
            return json.loads(exc.read())
        except Exception:
            return {"errors": [{"code": exc.code, "message": exc.reason}]}


# --- IZZ-0427: vizibilitatea pe CAI (teme) -------------------------------------------------------------
# Totalurile din INTEROGARE raspund „cat se intampla", dar nu POT borcan numarul pe subiecte:
# workersInvocationsAdaptive nu are nici path, nici referer. Zona izz.ro trece tot traficul
# prin proxy-ul Cloudflare (ruta `izz.ro/*` din infra/wrangler.toml), deci datasetul DE ZONA
# httpRequestsAdaptiveGroups vede aceleasi cereri, cu path. Sonda e BEST-EFFORT peste raportul
# de baza: daca tokenul nu are scope de zona, eroarea API se tipareste si programul NU pica —
# o cifra pe care n-o pot masura ramane nenotata, niciodata inventata.
INTEROGARE_CAI = """
query ($zona: String!, $de_la: Time!, $pana_la: Time!) {
  viewer {
    zones(filter: {zoneTag: $zona}) {
      httpRequestsAdaptiveGroups(
        limit: 300
        filter: {datetime_geq: $de_la, datetime_leq: $pana_la}
        orderBy: [sum_requests_DESC]
      ) {
        sum { requests }
        dimensions { clientRequestPath clientCountryName }
      }
    }
  }
}
"""


def _zone_tag(token: str, zone: str = "izz.ro") -> str | None:
    """ID-ul zonei dupa nume, prin REST. Masurat de ce e REST, nu GraphQL: filt-ul GraphQL
    pe zone NU accepta `zoneName` (eroarea exacta, 2026-10-03: 'unknown arg zoneName')."""
    cerere = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones?name={zone}",
        headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(cerere, timeout=30) as r:  # noqa: S310 - endpoint literal
            date_ = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        print(f"  REST /zones a refuzat: {exc.code}")
        return None
    rezultate = date_.get("result") or []
    return rezultate[0].get("id") if rezultate else None


def interogheaza_cai(token: str, zile: int = 7) -> dict:
    zona = _zone_tag(token)
    if not zona:
        return {"errors": [{"code": "zone-id", "message": "nu am putut rezolva id-ul zonei"}]}
    de_la, pana_la = fereastra(zile)
    corp = json.dumps({"query": INTEROGARE_CAI,
                       "variables": {"zona": zona, "de_la": de_la, "pana_la": pana_la}}).encode()
    cerere = urllib.request.Request(API, data=corp, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(cerere, timeout=30) as r:  # noqa: S310 - aceeasi garda
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read())
        except Exception:
            return {"errors": [{"code": exc.code, "message": exc.reason}]}


def rezuma_cai(raspuns: dict) -> dict:
    """Cereri agregate pe prefix tematic (/sport/, /local/...). Pur, testabil fara retea."""
    conturi = (((raspuns or {}).get("data") or {}).get("viewer") or {}).get("zones") or []
    pe_tema: dict[str, int] = {}
    pe_tara: dict[str, int] = {}
    total = 0
    for zona in conturi:
        for punct in zona.get("httpRequestsAdaptiveGroups") or []:
            dim, suma = punct.get("dimensions") or {}, punct.get("sum") or {}
            cale = dim.get("clientRequestPath") or ""
            cereri = int(suma.get("requests") or 0)
            total += cereri
            tema = cale.strip("/").split("/")[0] if cale not in ("", "/") else "<home>"
            pe_tema[tema] = pe_tema.get(tema, 0) + cereri
            tara = dim.get("clientCountryName") or "?"
            pe_tara[tara] = pe_tara.get(tara, 0) + cereri
    return {"total": total, "pe_tema": pe_tema, "pe_tara": pe_tara}


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

    # IZZ-0427: sondajul pe cai e aditiv si optional — esecul LUI nu transforma raportul
    # de baza in esec (diagram: erorile de scope se tiparesc, nu se reduc in tacere).
    print("\n-- Cereri pe cai (top 300), zone httpRequests —")
    raspuns_cai = interogheaza_cai(token)
    if (mesaje_cai := erori(raspuns_cai)):
        print("  sondajul pe cai a refuzat; mesajul API:")
        for m in mesaje_cai:
            print(f"  - {m}")
    else:
        agregat = rezuma_cai(raspuns_cai)
        if not agregat["total"]:
            print("  raspuns valid, dar fara randuri — zona n-a vazut cereri in fereastra.")
        else:
            print(f"  total in fereastra (poate diferi de Workers: include media/static): "
                  f"{agregat['total']:,}")
            print("  pe precourseul tematic (primul segment din URL):")
            for tema, cereri in sorted(agregat["pe_tema"].items(), key=lambda kv: -kv[1])[:15]:
                print(f"    /{tema:<15} {cereri:>8,}  ({cereri / agregat['total'] * 100:.0f}%)")
            print("  pe tari (top 8):")
            for tara, cereri in sorted(agregat["pe_tara"].items(), key=lambda kv: -kv[1])[:8]:
                print(f"    {tara:<18} {cereri:>8,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
