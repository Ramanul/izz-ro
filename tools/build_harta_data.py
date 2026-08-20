#!/usr/bin/env python
"""Genereaza datasetul static consumat de harta de stiri."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from generator import geo
from generator.util import title_tokens

ARTICLES = os.path.join(ROOT, "data", "articles.json")
MAP = os.path.join(ROOT, "data", "harta_judete.json")
SIRUTA = os.path.join(ROOT, "data", "siruta_raw.csv")
LOCALITIES = os.path.join(ROOT, "data", "harta_localitati.json")
OUT = os.path.join(ROOT, "static", "harta-stiri", "data", "map.json")
MAX_ARTICLES = 1500

STOPWORDS = {
    "UNIREA", "VICTORIA", "LIBERTATEA", "INDEPENDENTA", "PROGRESU", "PROGRESUL",
    "VIITORUL", "BISERICA", "BISERICANI", "GARA", "CENTRU", "PIATA", "VALEA",
    "DEALU", "DEALUL", "PADUREA", "LUNCA", "POIANA", "MOVILA", "IZVORU", "IZVORUL",
    "FANTANA", "FANTANELE", "PODURI", "PODUL", "MALU", "MALUL", "OSTROV", "SAT",
    "SATU", "SATUL", "SLOBOZIA", "RACOVITA", "COTU", "COASTA", "FRASIN", "FRUMOASA",
}
AMBIGUE = {
    "LUNA", "SAMBATA", "ROMAN", "BALA", "BANCA", "CURTEA", "VOLUNTARI", "TRAIAN",
    "VLADIMIR", "OVIDIU", "CRISTIAN", "BACIU", "DRAGUS", "CIOBANU", "FLORICA",
    "CATALINA", "MAIA", "AVRAM IANCU", "GEORGE ENESCU", "MIHAI BRAVU", "GRADINARI",
}
# Cuvinte care pot fi localități în SIRUTA, dar apar frecvent în textele jurnalistice.
# Fără un județ deja confirmat prin titlu sau sursă, nu reprezintă o bază suficientă pentru
# plasarea unei știri pe hartă.
BARE_LOCALITY_BLOCKLIST = AMBIGUE | STOPWORDS | {
    "VECHI", "VECHE", "VECHII", "LEGII", "ROMANI", "ROMANIA", "ROMANIEI", "LUMII",
    "ZILEI", "DREPTULUI", "STATULUI", "PACII", "NOI", "NOU", "NOUA", "MARE", "MARI",
}
PREFIXES = ("MUNICIPIUL ", "ORASUL ", "ORAS ", "COMUNA ", "JUDETUL ", "SATUL ")


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", (value or "").strip())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("Đ", "D").replace("đ", "d")
    value = re.sub(r"[^A-Za-z0-9]+", " ", value).upper().strip()
    return re.sub(r"\s+", " ", value)


def clean_name(value: str) -> str:
    name = norm(value)
    for prefix in PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):].strip()
    return name


def siruta_key(value: str) -> str:
    """Normalizeaza codul SIRUTA intre surse (ex. `32394,00` == `32394` == `32394.0`).
    `.0` e un artefact de float lasat de sursele GeoJSON/WFS (campuri numerice), nu parte
    din cod -- fara pasul asta, "1026.0" din baza de puncte si "1026" dintr-un articol nu
    se potrivesc niciodata, desi sunt acelasi SIRUTA (masurat 2026-08-13, vezi load_locality_points)."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.split(",", 1)[0].strip()
    if raw.endswith(".0"):
        raw = raw[:-2]
    return raw.lstrip("0") or "0"


def read_siruta(county_alias: dict[str, str] | None = None) -> tuple[dict[str, str], dict[str, list[dict]]]:
    with open(SIRUTA, encoding="cp1250", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))

    county_alias = county_alias or {}
    counties: dict[str, str] = {}
    for row in rows:
        if row.get("NIV") != "1":
            continue
        code = str(row.get("JUD") or "").strip()
        name = clean_name(row.get("DENLOC") or "")
        if code and name:
            counties[code] = county_alias.get(norm(name), name)

    sat_names = [clean_name(r.get("DENLOC") or "") for r in rows if r.get("NIV") == "3"]
    counts: dict[str, int] = {}
    for name in sat_names:
        if name:
            counts[name] = counts.get(name, 0) + 1
    duplicate_sats = {name for name, count in counts.items() if count > 1}

    by_name: dict[str, list[dict]] = {}
    for row in rows:
        niv = str(row.get("NIV") or "")
        if niv not in {"2", "3"}:
            continue
        name = clean_name(row.get("DENLOC") or "")
        county = counties.get(str(row.get("JUD") or "").strip(), "")
        if not name or not county:
            continue
        if niv == "3" and (len(name) < 5 or name in STOPWORDS or name in AMBIGUE or name in duplicate_sats):
            continue
        siruta = ""
        for key in ("SIRUTA", "CODSIRUTA", "COD SIRUTA", "COD_SIRUTA", "COD_SIRUTA_LOCALITATE"):
            if row.get(key):
                siruta = str(row[key]).strip()
                break
        rec = {"name": name, "county": county, "siruta": siruta_key(siruta), "level": niv}
        by_name.setdefault(name, []).append(rec)
    return counties, by_name


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_locality_points() -> dict[str, dict]:
    """{siruta_normalizat|nume|judet: punct}. `harta_localitati.json` e cheiat cu SIRUTA brut
    din campul GeoJSON/WFS sursa (`tools/build_harta_localitati.py:141`), care vine ca float
    ("1026.0", nu "1026") -- fara re-cheiere aici, `point_for()` cauta un SIRUTA normalizat
    ("1026") intr-un dictionar cheiat cu string-uri de float, deci NU gaseste niciodata nimic:
    masurat 2026-08-13, 0 din 497 articole din map.json aveau x/y, desi 13750 de puncte reale
    existau in fisier si articolele aveau SIRUTA rezolvat corect (doar formatul de cheie nu
    se potrivea). Efectul in UI: harta se marea pe judet dar nu aparea NICIUN punct de
    localitate -- exact "se blocheaza" raportat, fiindca nu era nimic de dat click pe el."""
    if not os.path.exists(LOCALITIES) or os.path.getsize(LOCALITIES) == 0:
        return {}
    payload = load_json(LOCALITIES)
    raw = payload.get("localities") or {}
    points: dict[str, dict] = {}
    for entry in raw.values():
        siruta = siruta_key(entry.get("siruta") or "")
        if siruta:
            points.setdefault(siruta, entry)
        key = f"{norm(entry.get('name'))}|{norm(entry.get('county'))}"
        points.setdefault(key, entry)
    return points


def point_for(locality: dict | None, points: dict[str, dict]) -> dict | None:
    if not locality:
        return None
    siruta = siruta_key(locality.get("siruta") or "")
    if siruta and siruta in points:
        return points[siruta]
    key = f"{norm(locality.get('name'))}|{norm(locality.get('county'))}"
    return points.get(key)


def explicit_county(text: str, county_keys: list[str]) -> str | None:
    t = norm(text)
    for county in sorted(county_keys, key=len, reverse=True):
        patterns = (
            rf"(?:JUDETUL|JUDETULUI|JUDETELE|JUDET|JUD\.)\s+{re.escape(norm(county))}\b",
            rf"\b{re.escape(norm(county))}\b",
        )
        if any(re.search(p, t) for p in patterns):
            return county
    return None


def source_county(source: str, county_keys: list[str]) -> str | None:
    t = norm(source)
    return next((c for c in sorted(county_keys, key=len, reverse=True) if norm(c) in t), None)


def locality_from_text(
    text: str,
    source_county: str | None,
    by_name: dict[str, list[dict]],
    points: dict[str, dict] | None = None,
) -> dict | None:
    padded = f" {norm(text)} "
    candidates = []
    for name, records in by_name.items():
        if len(name) < 4 or f" {name} " not in padded:
            continue
        # O localitate cu nume comun poate fi folosită numai după ce județul a fost confirmat
        # separat. Altfel, expresii ca „stocuri vechi”, „respectarea legii” sau „Curtea” ar
        # inventa puncte în județe fără nicio legătură cu articolul.
        if not source_county and name in BARE_LOCALITY_BLOCKLIST:
            continue
        same = [r for r in records if not source_county or norm(r["county"]) == norm(source_county)]
        if len(same) == 1:
            candidates.append(same[0])
            continue
        # Municipiile apar uneori de două ori în SIRUTA: ca UAT (NIV 2) și ca localitate
        # (NIV 3). Se alege explicit intrarea unică ce are punct pe hartă. Este cea care poate
        # fi agregată corect într-un UAT, de exemplu Timișoara, nu doar județul Timiș.
        mapped = []
        if points:
            for record in same:
                # Potrivirea trebuie să fie exactă pe SIRUTA: fallback-ul după nume ar găsi
                # același punct și pentru UAT-ul părinte, anulând diferența NIV 2/NIV 3.
                siruta = siruta_key(record.get("siruta") or "")
                if siruta and siruta in points:
                    mapped.append(record)
        if len(mapped) == 1:
            candidates.append(mapped[0])
            continue
    candidates.sort(key=lambda r: len(r["name"]), reverse=True)
    return candidates[0] if candidates else None


def locate(article: dict, county_keys: list[str], by_name: dict[str, list[dict]], points: dict[str, dict]) -> dict | None:
    category = article.get("category") or ""
    if category not in {"local", "judetean", "regional"}:
        return None
    text = " ".join(str(article.get(k) or "") for k in ("title", "teaser", "synthesis"))
    base = {
        "category": category,
        "geo_level": category,
        "slug": article.get("slug", ""),
        "title": article.get("title") or article.get("original_title") or "Fără titlu",
        "teaser": article.get("teaser") or "",
        "synthesis": article.get("synthesis") or "",
        "published": article.get("published") or "",
        "source": article.get("source") or "",
        "source_name": article.get("source_name") or article.get("source") or "",
    }
    if category == "regional":
        # O regiune ajunge pe hartă numai dacă este recunoscută de aceeași poartă
        # deterministă care a clasificat articolul. Nu se deduce regiunea din sursă.
        region = geo.regiune_din_text(text)
        if not region:
            return None
        return {
            **base,
            "region": region,
            "county": "",
            "locality": "",
            "siruta": "",
            "x": None,
            "y": None,
            "confidence": "text",
        }
    sc = source_county(str(article.get("source") or ""), county_keys)
    tc = explicit_county(text, county_keys)
    # Cine castiga cand sursa si textul numesc judete DIFERITE depinde de ce fel de sursa e.
    #
    # Site de stiri: textul castiga. Un ziar regional relateaza in mod normal si din judetele
    # vecine, iar judetul lui de resedinta nu spune nimic despre locul evenimentului.
    #
    # Anunt OFICIAL: sursa castiga. O primarie publica despre teritoriul ei; alt oras numit in
    # text e context (echipa oaspete, firma contractanta), nu locul faptei.
    #
    # MASURAT pe corpusul din 2026-08-20, inainte de a schimba ceva (505 articole pe harta):
    #   sursa si text DIVERG in 26 de cazuri
    #     - 24 la site-uri de stiri (jurnalulolteniei 11, bizbrasov 6, alba24 2, cronicaolteniei 3,
    #       emaramures 1, criticarad 1) -> verificate, TEXTUL e corect acolo; raman neatinse
    #     -  2 la surse oficiale -> ambele GRESITE inainte de regula asta:
    #        `pl_prahova_municipiul_ploiesti` „Restrictii ... Stadionului «Ilie Oana»" ajungea in
    #        BUCURESTI fiindca teaserul zice „FC Petrolul Ploiesti si Rapid Bucuresti";
    #        `pl_neamt_municipiul_roman` (pulverizare aeriana) ajungea in BACAU in loc de NEAMT.
    # Regula inversa, „sursa castiga mereu", ar fi stricat 24 de atribuiri corecte ca sa repare 2.
    # Gasita de `tools/integration_check.py`, recuperat din 7749e192 (Manus AI) in aceeasi trecere.
    oficial = article.get("processed_by") == "official"
    county = (sc or tc) if oficial else (tc or sc)
    locality = locality_from_text(text, county, by_name, points)
    if not county and locality:
        county = locality["county"]
    if not county:
        return None
    # Eticheta se schimba DOAR cand sursa chiar a decis contra textului — adica exact in cazurile
    # pe care regula de mai sus le repara. Cand cele doua sunt de acord (63 de articole in corpusul
    # masurat), eticheta ramane cea dinainte: reeticheta lor ar muta 24 de articole din „text" in
    # „source" fara ca atribuirea sa se fi schimbat, iar cifra din `stats` ar parea o regresie.
    if oficial and sc and tc and sc != tc:
        confidence = "source"
    else:
        confidence = "text" if tc else "source" if sc else "siruta"
    point = point_for(locality, points)
    return {
        **base,
        "region": geo.ETICHETE_REGIUNI.get(geo.regiune_afisare(county), ""),
        "county": county,
        "locality": locality["name"] if locality else "",
        "siruta": siruta_key(locality["siruta"]) if locality else "",
        "x": point.get("x") if point else None,
        "y": point.get("y") if point else None,
        "confidence": confidence,
    }


def _published_at(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _event_tokens(title: str) -> set[str]:
    """Semnătură conservatoare pentru gruparea articolelor despre același eveniment.

    Nu se încearcă o deducție semantică opacă: se cer cel puțin trei tokeni semnificativi
    comuni și o suprapunere reală. Localități explicite diferite nu se combină.
    """
    return {token[:6] for token in title_tokens(title or "")}


def _same_event(left: dict, right: dict, left_tokens: set[str], right_tokens: set[str]) -> bool:
    if (left["county"] != right["county"] or left.get("region") != right.get("region")
            or not left_tokens or not right_tokens):
        return False
    if left.get("locality") and right.get("locality") and left["locality"] != right["locality"]:
        return False
    left_time, right_time = _published_at(left.get("published", "")), _published_at(right.get("published", ""))
    if left_time and right_time and abs((left_time - right_time).total_seconds()) > 48 * 3600:
        return False
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection >= 3 and union > 0 and intersection / union >= 0.40


def annotate_events(items: list[dict]) -> list[dict]:
    """Atașează identificatori de eveniment și numărul de articole/surse asociate.

    Identificatorul este un hash al URL-urilor deja normalizate în pipeline. Astfel, harta
    poate afișa transparent „N relatări, M surse” fără a elimina articolele din dataset.
    """
    clusters: list[dict] = []
    for item in items:
        tokens = _event_tokens(item.get("title", ""))
        for cluster in clusters:
            if _same_event(item, cluster["leader"], tokens, cluster["tokens"]):
                cluster["items"].append(item)
                cluster["tokens"] |= tokens
                break
        else:
            clusters.append({"leader": item, "items": [item], "tokens": set(tokens)})

    for cluster in clusters:
        members = cluster["items"]
        # Slugul nu este suficient pentru unicitate în date sintetice sau când două surse
        # publică același titlu. Domeniul geografic și ziua primei relatări separă grupurile
        # care au aceeași formulare, dar sunt evenimente diferite.
        first_day = min((str(member.get("published") or "")[:10] for member in members), default="")
        localities = ",".join(sorted({str(member.get("locality") or "") for member in members}))
        slugs = "|".join(sorted(str(member.get("slug") or member.get("title") or "") for member in members))
        fingerprint = f"{cluster['leader'].get('region', '')}|{cluster['leader'].get('county', '')}|{localities}|{first_day}|{slugs}"
        event_id = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]
        source_count = len({member.get("source") for member in members if member.get("source")})
        for member in members:
            member["event_id"] = event_id
            member["event_article_count"] = len(members)
            member["event_source_count"] = source_count
    return items


def main() -> int:
    map_data = load_json(MAP)
    articles = load_json(ARTICLES)
    if not isinstance(articles, list):
        articles = articles.get("articles") or articles.get("items") or []
    counties = map_data.get("judete") or {}
    county_keys = list(counties)
    county_alias = {norm(key): key for key in county_keys}
    _, siruta = read_siruta(county_alias)
    points = load_locality_points()
    if not points:
        raise RuntimeError("harta_localitati.json nu contine puncte de localitati.")

    articles = sorted(articles, key=lambda a: str(a.get("published") or ""), reverse=True)
    located = []
    for article in articles[:MAX_ARTICLES]:
        item = locate(article, county_keys, siruta, points)
        if item:
            located.append(item)

    located = annotate_events(located)
    regions = {}
    for county in counties:
        key = geo.regiune_afisare(county)
        label = geo.ETICHETE_REGIUNI.get(key, "")
        if label:
            regions.setdefault(label, []).append(county)
    named_localities = {(a["siruta"] or f"{norm(a['locality'])}|{a['county']}") for a in located if a.get("locality")}
    geocoded_articles = sum(a.get("x") is not None and a.get("y") is not None for a in located)
    latest_article_at = max((a.get("published") or "" for a in located), default="")
    event_count = len({a.get("event_id") for a in located if a.get("event_id")})
    payload = {
        "version": 4,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_article_at": latest_article_at,
        "map": {"viewbox": map_data.get("viewbox", ""), "judete": counties, "regiuni": regions},
        "articles": located,
        "stats": {
            "total": len(located),
            "events": event_count,
            "local": sum(a["category"] == "local" for a in located),
            "judetean": sum(a["category"] == "judetean" for a in located),
            "regional": sum(a["category"] == "regional" for a in located),
            "counties": len({a["county"] for a in located if a.get("county")}),
            "regions": len({a["region"] for a in located if a.get("region")}),
            "localities": len(named_localities),
            "county_only": sum(bool(a.get("county")) and not a.get("locality") for a in located),
            "coordinates": geocoded_articles,
            "geocoded_localities": len({a["siruta"] or f"{norm(a['locality'])}|{a['county']}" for a in located if a.get("locality") and a.get("x") is not None and a.get("y") is not None}),
            "sources": len({a.get("source") for a in located if a.get("source")}),
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"harta-stiri: {len(located)} articole, {payload['stats']['events']} evenimente, {payload['stats']['localities']} localități confirmate, {payload['stats']['coordinates']} coordonate -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
