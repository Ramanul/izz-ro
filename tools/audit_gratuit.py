"""Audit extern gratuit pe site-ul LIVE - complementul post-deploy al masuratorilor locale.

Context: tools/audit.sh masoara Lighthouse + pa11y pe `output/` servit local, INAINTE de
deploy (specs/masuratori-frontend.md). Aici e complementul pe care acelasi doc il cere:
scanere externe, gratuite, pe ce serveste izz.ro acum:
  - PageSpeed Insights API  (lab + field CrUX, per URL)   [keyless; cheie optionala]
  - Mozilla Observatory     (antete HTTP de securitate)   [keyless]
  - SSL Labs                (nota TLS)                    [keyless, cu rate limit]
  - W3C Nu HTML validator   (markup pe esantion)          [keyless, volum mic si politicos]
  - W3C CSS validator       (styles.css)                  [keyless]
  - JSON-LD schema.org      (NewsArticle minim)           [local, fara retea catre validator]
  - lychee                  (linkuri rupte)               [scanarea ruleaza ca step de Actions;
                                                             subcomanda `lychee` normalizeaza
                                                             raportul brut in formatul casei]

IndexNow NU e aici: exista deja in pipeline (cheia in config, render.py scrie fisierul
root, tools/indexnow_submit.py anunta URL-urile noi la fiecare rulare) — nu se dubleaza.

Regula casei (feedcheck.yml): un esec de scan NU blocheaza. Fiecare subcomanda scrie
reports/<nume>.json cu stare OK / ATENTIE / ESUAT / SARIT si iese mereu 0; sumarul le aduna.

Doar biblioteca standard. Rulare locala: python tools/audit_gratuit.py <subcomanda>.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

# Hostul SCANAT (Observatory/SSL Labs au nevoie de numele public, nu de origin).
SITE_HOST = os.environ.get("AUDIT_SITE_HOST", "izz.ro")
# Origin-ul de rezerva daca anti-bot-ul de pe izz.ro blocheaza sondele din datacenter
# (statica e identica; vezi STATE.md: Worker origin e calea de fallback).
ORIGIN_DEFAULT = os.environ.get("AUDIT_ORIGIN", "https://izz-ro.andifreelancer2.workers.dev")
REPORTS_DIR = os.environ.get("AUDIT_REPORTS_DIR", "reports")
UA = "izz-ro-audit/1.0 (+https://github.com/Ramanul/izz-ro; tools/audit_gratuit.py)"

STARE_OK, STARE_ATENTIE, STARE_ESUAT, STARE_SARIT = "OK", "ATENTIE", "ESUAT", "SARIT"


def reports_path(name: str) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return os.path.join(REPORTS_DIR, name)


def write_report(name: str, stare: str, detaliu: str, date: dict) -> None:
    payload = {
        "sursa": name,
        "stare": stare,
        "detaliu": detaliu,
        "generat": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "date": date,
    }
    with open(reports_path(f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"[{name}] {stare}: {detaliu}")


def http_get(url: str, timeout: int = 30) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (urllib.error.URLError, OSError) as exc:
        raise ConnectionError(f"{url}: {exc}") from exc


def http_post(url: str, body: bytes, content_type: str, timeout: int = 60) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url, data=body, headers={"User-Agent": UA, "Content-Type": content_type}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def fetch_base() -> str:
    """ Rezolva de unde se ia HTML-ul: izz.ro sau origin. Cache pe 2h in reports/target.json. """
    cache = reports_path("target.json")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            saved = json.load(fh)
        age = time.time() - os.path.getmtime(cache)
        if age < 2 * 3600:
            return saved["base"]
    for candidate, sursa in ((f"https://{SITE_HOST}", "live"), (ORIGIN_DEFAULT, "origin")):
        try:
            status, body = http_get(f"{candidate}/robots.txt", timeout=20)
            if status == 200 and b"User-agent" in body[:4000]:
                with open(cache, "w", encoding="utf-8") as fh:
                    json.dump({"base": candidate, "sursa": sursa}, fh)
                return candidate
        except ConnectionError:
            continue
    raise ConnectionError("nici izz.ro nici origin nu raspunde la /robots.txt")


def sitemap_entries(base: str) -> list[dict]:
    """ [(url, lastmod)] din sitemap.xml; daca e index, coboara in primii 3 copii. """
    status, body = http_get(f"{base}/sitemap.xml", timeout=30)
    entries: list[dict] = []
    if status == 200:
        entries = _parse_urlset(body.decode("utf-8", "replace"))
        if not entries:
            text = body.decode("utf-8", "replace")
            children = re.findall(r"<loc>([^<]+)</loc>", text)
            for child in children[:3]:
                st, cb = http_get(child, timeout=30)
                if st == 200:
                    entries.extend(_parse_urlset(cb.decode("utf-8", "replace")))
    return entries


def _parse_urlset(xml_text: str) -> list[dict]:
    out = []
    for block in re.findall(r"<url>(.*?)</url>", xml_text, re.S):
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        if loc:
            lm = re.search(r"<lastmod>([^<]+)</lastmod>", block)
            out.append({"url": loc.group(1).strip(), "lastmod": lm.group(1).strip() if lm else ""})
    return out


def esantion() -> None:
    """ Eșantion deterministic mic (politeness fata de validatorii publici). """
    base = fetch_base()
    entries = sitemap_entries(base)
    urls: list[str] = []
    if entries:
        by_lm = sorted(entries, key=lambda e: e["lastmod"] or "", reverse=True)
        azi = dt.datetime.now(dt.timezone.utc).date().isocalendar()
        seed = f"{azi.year}-w{azi.week}"
        rng = uuid.UUID(int=int(seed.replace("-", "").replace("w", ""), 16) % (2**128))
        pool = [e["url"] for e in by_lm]
        newest = pool[:3]
        middle = pool[len(pool) // 2 : len(pool) // 2 + 3]
        oldest = pool[-3:]
        head = int(str(rng)[:2], 16)
        random_set = [pool[head % len(pool)], pool[(head * 7 + 3) % len(pool)],
                      pool[(head * 13 + 5) % len(pool)]]
        urls = list(dict.fromkeys(newest + middle + oldest + random_set))[:10]
    home = base + "/"
    all_urls = [home] + [u for u in urls if u != home]
    styles_url = ""
    try:
        _, home_html = http_get(home, timeout=30)
        m = re.search(r'href="([^"]*styles\.css[^"]*)"', home_html.decode("utf-8", "replace"))
        if m:
            styles_url = urllib.parse.urljoin(home, m.group(1))
    except ConnectionError:
        pass
    with open(reports_path("urls.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(all_urls))
    write_report("esantion", STARE_OK if entries or all_urls else STARE_ATENTIE,
                 f"{len(all_urls)} URL-uri din sitemap ({len(entries)} intrari citite)",
                 {"base": base, "urls": all_urls, "sitemap_intri": len(entries), "styles_url": styles_url})


def psi() -> None:
    key = os.environ.get("PSI_API_KEY", "").strip()
    with open(reports_path("esantion.json"), encoding="utf-8") as fh:
        urls = json.load(fh)["date"]["urls"][:3]
    rezultate = []
    for url in urls:
        q = urllib.parse.quote(url, safe="")
        cats = "&category=performance&category=accessibility&category=best-practices&category=seo"
        api = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={q}&strategy=mobile{cats}"
        if key:
            api += f"&key={urllib.parse.quote(key)}"
        try:
            status, body = http_get(api, timeout=120)
            if status in (403, 429):
                write_report("psi", STARE_SARIT, f"HTTP {status} — fara cheie pe IP partajat; "
                             "adauga secretul gratuit PSI_API_KEY (25.000 apeluri/zi)", {"urls": urls})
                return
            if status != 200:
                rezultate.append({"url": url, "eroare": f"HTTP {status}"})
                continue
            data = json.loads(body.decode("utf-8", "replace"))
            cats_obj = data.get("lighthouseResult", {}).get("categories", {})
            scores = {c: round(cats_obj.get(c, {}).get("score", 0) * 100) for c in
                      ("performance", "accessibility", "best-practices", "seo")}
            field = data.get("loadingExperience", {})
            metrics = {}
            for mid, out in (("LARGEST_CONTENTFUL_PAINT_MS", "LCP_ms"), ("CUMULATIVE_LAYOUT_SHIFT_SCORE", "CLS_x100"),
                             ("INTERACTION_TO_NEXT_PAINT", "INP_ms")):
                if mid in field.get("metrics", {}):
                    metrics[out] = field["metrics"][mid].get("percentile")
            rezultate.append({"url": url, "scores": scores,
                              "field": field.get("overall_category", "fara date CrUX (trafic sub prag)"),
                              "metrics": metrics})
        except (ConnectionError, json.JSONDecodeError) as exc:
            rezultate.append({"url": url, "eroare": str(exc)[:200]})
        time.sleep(3)
    ok = [r for r in rezultate if "scores" in r]
    stare = STARE_OK if len(ok) == len(rezultate) and rezultate else STARE_ATENTIE
    write_report("psi", stare, f"{len(ok)}/{len(rezultate)} URL-uri scanate (mobile)",
                 {"ruluri": rezultate, "cu_cheie": bool(key)})


def observatory() -> None:
    api = f"https://observatory-api.mdn.mozilla.net/api/v2/scan?host={urllib.parse.quote(SITE_HOST)}"
    status, body = http_post(api, b"{}", "application/json", timeout=60)
    if status != 200:
        write_report("observatory", STARE_ESUAT, f"HTTP {status} de la API-ul Mozilla", {"raspuns": body[:300].decode('utf-8', 'replace')})
        return
    data = json.loads(body.decode("utf-8", "replace"))
    write_report("observatory", STARE_OK if data.get("grade") in ("A+", "A", "A-", "B+", "B") else STARE_ATENTIE,
                 f"nota {data.get('grade')} ({data.get('score')}/100)",
                 {"nota": data.get("grade"), "scor": data.get("score"),
                  "testuri": data.get("test_counts", {})})


def ssllabs() -> None:
    api = (f"https://api.ssllabs.com/api/v3/analyze?host={urllib.parse.quote(SITE_HOST)}"
           "&publish=off&all=done&ignoreMismatch=on")
    stare_scan = ""
    for incercare in range(12):
        status, body = http_get(api, timeout=30)
        if status != 200:
            write_report("ssllabs", STARE_ESUAT, f"HTTP {status} de la SSL Labs", {})
            return
        data = json.loads(body.decode("utf-8", "replace"))
        stare_scan = data.get("status", "")
        if stare_scan == "READY":
            endpoints = data.get("endpoints", [])
            note = [e.get("grade", "?") for e in endpoints]
            write_report("ssllabs", STARE_OK if any(n and n[0] in "AB" for n in note) else STARE_ATENTIE,
                         f"note: {', '.join(note) or 'fara endpointuri'}", {"note": note})
            return
        if stare_scan == "ERROR":
            write_report("ssllabs", STARE_ESUAT, data.get("statusMessage", "eroare necunoscuta"), {})
            return
        time.sleep(20)
    write_report("ssllabs", STARE_ATENTIE, "scanare inca in curs dupa 4 min — se completeaza singura; "
                 "saptamana viitoare vine din cache", {"status": stare_scan})


def css() -> None:
    with open(reports_path("esantion.json"), encoding="utf-8") as fh:
        styles_url = json.load(fh)["date"]["styles_url"]
    if not styles_url:
        write_report("css", STARE_SARIT, "nu am gasit URL-ul styles.css in homepage", {})
        return
    status, body = http_get(styles_url, timeout=30)
    if status != 200:
        write_report("css", STARE_ESUAT, f"styles.css da HTTP {status}", {"url": styles_url})
        return
    form = urllib.parse.urlencode({"text": body.decode("utf-8", "replace"), "profile": "css3svg"}).encode()
    vstatus, vbody = http_post("https://jigsaw.w3.org/css-validator/validator?output=json",
                               form, "application/x-www-form-urlencoded", timeout=90)
    if vstatus != 200:
        write_report("css", STARE_ESUAT, f"validatorul a raspuns HTTP {vstatus}", {"url": styles_url})
        return
    data = json.loads(vbody.decode("utf-8", "replace")).get("cssvalidationresult", {})
    erori = data.get("errors", {}).get("errorcount", 0)
    avertismente = data.get("warnings", {}).get("warningcount", 0)
    write_report("css", STARE_OK if erori == 0 else STARE_ATENTIE,
                 f"{erori} erori, {avertismente} avertismente W3C CSS",
                 {"url": styles_url, "erori": erori, "avertismente": avertismente})


def nu() -> None:
    with open(reports_path("urls.txt"), encoding="utf-8") as fh:
        urls = [l.strip() for l in fh if l.strip()]
    per_url, mesaje_repetate = [], {}
    for url in urls[:11]:
        try:
            status, body = http_get(url, timeout=30)
            if status != 200:
                per_url.append({"url": url, "eroare": f"HTTP {status}"})
                continue
            vstatus, vbody = http_post("https://validator.w3.org/nu/?out=json", body,
                                       "text/html; charset=utf-8", timeout=60)
            if vstatus != 200:
                per_url.append({"url": url, "eroare": f"validator HTTP {vstatus}"})
                continue
            msgs = json.loads(vbody.decode("utf-8", "replace")).get("messages", [])
            erori = [m for m in msgs if m.get("type") == "error"]
            for m in erori:
                text = m.get("message", "")[:120]
                mesaje_repetate[text] = mesaje_repetate.get(text, 0) + 1
            per_url.append({"url": url, "erori": len(erori), "avertismente": len(msgs) - len(erori)})
        except (ConnectionError, json.JSONDecodeError) as exc:
            per_url.append({"url": url, "eroare": str(exc)[:150]})
        time.sleep(1.5)
    top = sorted(mesaje_repetate.items(), key=lambda kv: -kv[1])[:5]
    total = sum(p.get("erori", 0) for p in per_url)
    write_report("nu_html", STARE_OK if total == 0 else STARE_ATENTIE,
                 f"{total} erori HTML W3C pe {len(per_url)} pagini (validator public, volum mic)",
                 {"pagini": per_url, "top_mesaje": top})


def jsonld() -> None:
    with open(reports_path("urls.txt"), encoding="utf-8") as fh:
        urls = [l.strip() for l in fh if l.strip()]
    necesare = ("headline", "datePublished", "author", "publisher", "image")
    lipsa: dict[str, int] = {}
    tipuri: dict[str, int] = {}
    analizate = 0
    for url in urls[:11]:
        try:
            status, body = http_get(url, timeout=30)
            if status != 200:
                continue
            analizate += 1
            for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                                  body.decode("utf-8", "replace"), re.S):
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    lipsa["JSON invalid"] = lipsa.get("JSON invalid", 0) + 1
                    continue
                for nod in (data.get("@graph") if isinstance(data, dict) and "@graph" in data else [data]):
                    tip = nod.get("@type", "") if isinstance(nod, dict) else ""
                    tipuri[tip] = tipuri.get(tip, 0) + 1
                    if tip == "NewsArticle":
                        for prop in necesare:
                            if not nod.get(prop):
                                lipsa[prop] = lipsa.get(prop, 0) + 1
        except ConnectionError:
            continue
        time.sleep(1)
    stare = STARE_OK if not lipsa and analizate else STARE_ATENTIE
    write_report("jsonld", stare, f"{analizate} pagini; NewsArticle fara campuri: {lipsa or 'niciunul'}",
                 {"tipuri": tipuri, "campuri_lipsa": lipsa})


def lychee() -> None:
    """Converteste iesirea CRUDA a actiunii lychee in formatul casei (`reports/lychee.json`).

    De ce exista: actiunea scrie raportul ei in `reports/lychee-raw.json`, cu schema ei
    (versiune-dependenta), iar `sumar` citeste doar formatul casei (`stare` + `detaliu`).
    Fara conversie, linia din sumar iesea „lychee | ? |" — raportul exista, dar nu spunea nimic.
    Ambele forme cunoscute sunt acceptate (lista de rezultate pe link / obiect cu `fail_map`
    si numaratori), pentru ca schema difera intre versiunile de lychee.
    """
    path = reports_path("lychee-raw.json")
    if not os.path.exists(path):
        write_report("lychee", STARE_SARIT, "actiunea lychee nu a produs raportul brut", {})
        return
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)

    total = ok = rupte = 0
    exemple: list[str] = []

    def _cod_numeric(valoare):
        try:
            return int(valoare)
        except (TypeError, ValueError):
            return None

    def _nota(entry) -> tuple[bool, str]:
        """(e_ok, detaliu) pentru un rezultat de link, oricare ar fi forma lui."""
        if not isinstance(entry, dict):
            return True, ""
        status = entry.get("status")
        cod = _cod_numeric(entry.get("code")
                           or (status.get("code") if isinstance(status, dict) else None))
        text = status.get("text") if isinstance(status, dict) else (status or "")
        url = str(entry.get("url") or "")[:120]
        if str(status).lower() in ("ok", "success", "successful") or (cod is not None and cod < 400):
            return True, ""
        return False, f"{url} -> {text or cod or 'fara detaliu'}"

    if isinstance(raw, list):                       # forma veche: lista de rezultate
        total = len(raw)
        for entry in raw:
            e_ok, nota = _nota(entry)
            if e_ok:
                ok += 1
            else:
                rupte += 1
                if len(exemple) < 10:
                    exemple.append(nota)
    elif isinstance(raw, dict):                     # forma noua: numaratori + harti
        total = int(raw.get("total") or 0)
        ok = int(raw.get("successful") or raw.get("success") or 0)
        rupte = int(raw.get("errors") or raw.get("failures") or 0) + int(raw.get("timeouts") or 0)
        for harta in ("fail_map", "error_map", "timeout_map"):
            for _fisier, intrari in (raw.get(harta) or {}).items():
                for entry in (intrari if isinstance(intrari, list) else []):
                    _e_ok, nota = _nota(entry)
                    if nota and len(exemple) < 10:
                        exemple.append(nota)
        if not total:
            total = ok + rupte
        elif rupte == 0 and raw.get("fail_map") is None and raw.get("error_map") is None:
            rupte = max(0, total - ok)
    else:
        write_report("lychee", STARE_ESUAT, f"raport brut cu forma necunoscuta: {type(raw).__name__}", {})
        return

    # Schema noua (v0.24.x, verificata in sursa lychee) are si `unknown`/`unsupported`
    # (status nedeterminat) si `excluded` (excluse intentionat). Nu intra in verdictul de
    # „rupte" — un link nedeterminat de la un site care filtreaza boții nu e un link rupt —
    # dar se raporteaza, ca sa nu se piarda informatia.
    nedescis = 0
    if isinstance(raw, dict):
        nedescis = int(raw.get("unknown") or 0) + int(raw.get("unsupported") or 0)
    detaliu = f"{rupte} linkuri rupte din {total} verificate (ok: {ok}"
    if nedescis:
        detaliu += f", nedeterminate: {nedescis}"
    detaliu += "); exemple: " + ("; ".join(exemple) if exemple else "niciunul")
    stare = STARE_OK if rupte == 0 else STARE_ATENTIE
    write_report("lychee", stare, detaliu,
                 {"total": total, "ok": ok, "rupte": rupte, "nedeterminate": nedescis,
                  "exemple": exemple})


def sumar() -> None:
    surse = ["psi", "observatory", "ssllabs", "css", "nu_html", "jsonld", "lychee"]
    randuri = []
    for sursa in surse:
        path = reports_path(f"{sursa}.json")
        if not os.path.exists(path):
            randuri.append(f"| {sursa} | LIPSA | pasul a esuat inainte de raport | |")
            continue
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        rezultat = data.get("detaliu", "")
        randuri.append(f"| {data.get('sursa', sursa)} | {data.get('stare', '?')} | {rezultat} | |")
    linii = [
        "## Audit extern gratuit — site LIVE",
        f"Generat: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Prima rulare stabileste baseline-ul live; urmatoarele rulari se compara cu el.",
        "Masuratorile locale (inainte de deploy) raman in tools/audit.sh — asta e complementul.",
        "",
        "| Sursa | Stare | Rezultat | Nota |",
        "|---|---|---|---|",
        *randuri,
    ]
    raport = "\n".join(linii) + "\n"
    with open(reports_path("sumar.md"), "w", encoding="utf-8") as fh:
        fh.write(raport)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(raport)
    else:
        print(raport)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit extern gratuit izz.ro (detalii in docstring)")
    sub = parser.add_subparsers(dest="comanda", required=True)
    sub.add_parser("esantion", help="alege esantionul de URL-uri din sitemap")
    sub.add_parser("psi", help="PageSpeed Insights (lab + field)")
    sub.add_parser("observatory", help="Mozilla Observatory (antete securitate)")
    sub.add_parser("ssllabs", help="SSL Labs (nota TLS)")
    sub.add_parser("css", help="W3C CSS validator pe styles.css")
    sub.add_parser("nu", help="W3C Nu HTML validator pe esantion")
    sub.add_parser("jsonld", help="JSON-LD schema.org minim pe esantion")
    sub.add_parser("lychee", help="converteste raportul brut lychee in formatul casei")
    sub.add_parser("sumar", help="agrega rapoartele in markdown")
    args = parser.parse_args()
    comenzi = {"esantion": esantion, "psi": psi, "observatory": observatory, "ssllabs": ssllabs,
               "css": css, "nu": nu, "jsonld": jsonld, "lychee": lychee, "sumar": sumar}
    try:
        comenzi[args.comanda]()
    except Exception as exc:  # un esec de scan nu blocheaza niciodata workflow-ul
        write_report(args.comanda, STARE_ESUAT, f"exceptie: {type(exc).__name__}: {exc}", {})
    return 0


if __name__ == "__main__":
    sys.exit(main())
