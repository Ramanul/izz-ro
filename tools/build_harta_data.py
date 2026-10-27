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
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from generator import config, geo, moderation
from generator.util import title_tokens

ARTICLES = os.path.join(ROOT, "data", "articles.json")
MAP = os.path.join(ROOT, "data", "harta_judete.json")
SIRUTA = os.path.join(ROOT, "data", "siruta_raw.csv")
LOCALITIES = os.path.join(ROOT, "data", "harta_localitati.json")
OUT = os.path.join(ROOT, "static", "harta-stiri", "data", "map.json")
MAX_ARTICLES = 1500
# Fereastra principala e de VOLUM (1500 de articole ~= 37h de stiri), deci o sursa care
# publica rar — primariile de comuna, cateva anunturi pe luna — cade integral din fereastra
# si judetul ei apare gol pe harta desi registrul il acopera (masurat pe live 2026-10-03:
# OLT 0 stiri cu 3 surse configurate, SALAJ 0/11, SATU MARE 0/9, TELEORMAN 0/3).
# Backfill: fiecare sursa locala ACTIVA (a publicat ceva in ultimele BACKFILL_DAYS zile)
# care n-a prins fereastra primeste cel mai recent articol al ei, marcat `backfill: true`
# si afisat cu data reala — o stire veche de o saptamana, etichetata onest, e informatie;
# un judet pur si simplu absent arata ca o panza moarta.
BACKFILL_DAYS = 14

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
    # „Brigada 2 Vanatori de Munte" (Brasov) ajungea in MEHEDINTI — masurat 2026-10-16.
    "VANATORI",
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
    parents: dict[str, str] = {}
    for row in rows:
        niv = str(row.get("NIV") or "")
        if niv not in {"2", "3"}:
            continue
        name = clean_name(row.get("DENLOC") or "")
        county = counties.get(str(row.get("JUD") or "").strip(), "")
        if not name or not county:
            continue
        siruta = ""
        for key in ("SIRUTA", "CODSIRUTA", "COD SIRUTA", "COD_SIRUTA", "COD_SIRUTA_LOCALITATE"):
            if row.get(key):
                siruta = str(row[key]).strip()
                break
        rec = {"name": name, "county": county, "siruta": siruta_key(siruta), "level": niv}
        if niv == "3":
            # SIRSUP = codul UAT-ului parinte (NIV2): satul -> comuna/orasul lui. E baza
            # asignarii DETERMINISTE la UAT (vezi `locate`): hit-testul geometric intoarce
            # vecinul cand satul sta la mai putin de toleranta de simplificare de granita
            # (masurat 2026-10-02: 102 puncte, Apuseni preponderent). Se colecteaza pentru
            # TOATE satele, si pentru cele filtrate mai jos din by_name: un articol poate
            # ajunge aici cu SIRUTA rezolvata doar prin puncte, nu prin nume.
            parent = siruta_key(row.get("SIRSUP") or "")
            if parent:
                parents[rec["siruta"]] = parent
        if niv == "3" and (len(name) < 5 or name in STOPWORDS or name in AMBIGUE or name in duplicate_sats):
            continue
        by_name.setdefault(name, []).append(rec)
    return counties, by_name, parents


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


LOCALITY_LABELS = os.path.join(ROOT, "data", "localities.json")
_ETICHETE_LOCALITATI: tuple[dict, dict] | None = None


def locality_label(name: str, county: str, text: str = "") -> str:
    """Numele de afisare al localitatii, cu diacritice („GIROC" -> „Giroc", „TIMISOARA" ->
    „Timișoara"), din gazetteerul Wikidata (`data/localities.json`). Lista hartii tiparea pana
    acum codul din date, cu majuscule si fara diacritice. Satele lipsa din gazetteer cad pe
    forma cu majuscula initiala — mai lizibila decat un cod, fara sa inventeze diacritice."""
    global _ETICHETE_LOCALITATI
    if not name:
        return ""
    if _ETICHETE_LOCALITATI is None:
        pe_judet: dict = {}
        pe_nume: dict = {}
        if os.path.exists(LOCALITY_LABELS):
            for cheie, intrari in (load_json(LOCALITY_LABELS).get("by_name") or {}).items():
                for e in intrari:
                    eticheta = str(e.get("label") or "").strip()
                    if not eticheta:
                        continue
                    judet = re.sub(r"^(JUDETUL|MUNICIPIUL) ", "", norm(e.get("judet") or ""))
                    pe_judet[(norm(cheie), judet)] = eticheta
                    pe_nume.setdefault(norm(cheie), set()).add(eticheta)
        _ETICHETE_LOCALITATI = (pe_judet, pe_nume)
    pe_judet, pe_nume = _ETICHETE_LOCALITATI
    eticheta = pe_judet.get((norm(name), norm(county)))
    if eticheta:
        return eticheta
    variante = pe_nume.get(norm(name)) or set()
    if len(variante) == 1:
        return next(iter(variante))
    # Satele lipsesc din gazetteer (14 din 475 pe 17 oct.), dar stirea care le-a numit le scrie
    # corect: „din satul Zălan" -> „Zălan". Se ia forma din text, daca e scrisa ca nume propriu.
    cuvinte = re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", text or "")
    lungime = len(name.split(" "))
    for i in range(len(cuvinte) - lungime + 1):
        grup = " ".join(cuvinte[i:i + lungime])
        if grup[:1].isupper() and norm(grup) == norm(name):
            return grup
    return " ".join(w.capitalize() for w in name.split(" "))


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


def load_uat_ids() -> set[str]:
    """Codurile SIRUTA (natcode) ale UAT-urilor din stratul de poligoane, pentru asignarea
    determinista din `locate`. Se citesc de pe disc, nu se deduc — daca build-ul UAT n-a
    rulat, asignarea cade pe hit-testul geometric, exact ca inainte de campul `uat`."""
    ids: set[str] = set()
    uat_dir = os.path.join(ROOT, "static", "harta-stiri", "data", "uat")
    if not os.path.isdir(uat_dir):
        return ids
    for filename in os.listdir(uat_dir):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(uat_dir, filename), encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        for unit in data.get("uats") or []:
            code = siruta_key((unit or {}).get("id") or "")
            if code:
                ids.add(code)
    return ids


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


# Un nume de REGIUNE din id-ul sursei nu este un judet. Cautarea de mai jos e pe subsir, iar
# „jurnalulOLTeniei", „cronicaOLTeniei" si „stirileOLTeniei" contin literele OLT — asa incat tot
# ce publicau cele trei ziare regionale de Oltenia ajungea in judetul Olt. MASURAT pe map.json
# generat 2026-08-21 (509 articole): 8 articole gresite, intre care Craiova de 3 ori (e in Dolj),
# „Spitalul Regional Craiova", Rovinari si Termocentrala Turceni (ambele in Gorj). Singurul OLT
# corect era Caracal, care chiar e in Olt — si ramane corect si dupa fix, prin localitate.
#
# Se mascheaza DOAR regiunile care nu sunt totodata judete: MARAMURES este si regiune, si judet,
# iar mascarea lui ar rupe „emaramures" -> MARAMURES (17 articole corecte in acelasi corpus).
# Stem-ul plus [A-Z]* acopera flexiunea: „OLTENIA" si „OLTENIEI" deopotriva.
_JUDETE_DIN_REGIUNI = {norm(j) for judete in geo.REGIUNI.values() for j in judete}
_REGIUNI_NEJUDET = [r for r in geo.REGIUNI if norm(r) not in _JUDETE_DIN_REGIUNI]
_RE_REGIUNI = re.compile("|".join(
    rf"{re.escape(norm(r).rstrip('A'))}[A-Z]*"
    for r in sorted(_REGIUNI_NEJUDET, key=len, reverse=True)
))


def source_county(source: str, county_keys: list[str]) -> str | None:
    # Judetul DECLARAT in catalog (`config.SOURCES[...]["judet"]`) castiga: e acelasi contract
    # ca `geo.judet_sursa`, pe care il folosesc restul pipeline-ului. Subsirul din id ramane
    # doar fallback, pentru sursele care isi codeaza judetul in nume (`pl_cluj_...`, `alba24`).
    # MASURAT pe starea din 2026-10-16 (598 de articole pe harta): 14 din cele 20 de ziare cu
    # judet declarat (bihon, pressalert, tion, zcj, opiniatm...) nu-l aveau in id, deci harta
    # le trata ca surse fara judet si le plasa dupa orice nume de localitate din text —
    # „spitalul din Oradea" (bihon) ajungea in DAMBOVITA prin cuvantul „ferestrelor".
    # Cu catalogul: 4 articole se muta, toate 4 corecte, si 6 revin pe harta.
    declarat = norm(str((config.SOURCES.get(source) or {}).get("judet") or ""))
    if declarat:
        potrivit = next((c for c in county_keys if norm(c) == declarat), None)
        if potrivit:
            return potrivit
    t = _RE_REGIUNI.sub(" ", norm(source))
    return next((c for c in sorted(county_keys, key=len, reverse=True) if norm(c) in t), None)


# Context in fata numelui potrivit. Doar in fata: in romana marca de loc precede numele
# („Primaria X", „din X", „strada X"). MASURAT pe starea din 2026-10-16: fara context,
# candidatul cu numele cel mai lung castiga, si 9 din 82 de plasari facute doar din numele
# localitatii erau gresite — numele era de fapt o strada (Decebal), o persoana (primarul
# Baluta) sau un cuvant comun (Ferestre, din „ferestrelor"), iar localitatea reala, numita
# cu marca administrativa („Primaria Giroc", „Municipiul Lugoj"), pierdea fiindca era mai scurta.
_MARCA_ADMIN = re.compile(
    r"(?:PRIMARIA|PRIMARIEI|MUNICIPIUL|MUNICIPIULUI|ORASUL|ORASULUI|COMUNA|COMUNEI|"
    r"LOCALITATEA|LOCALITATII|SATUL|SATULUI|CONSILIUL LOCAL|CONSILIULUI LOCAL) $")
TITLU_BONUS = 1
_MARCA_LOC = re.compile(r"(?:\bDIN|\bLA|\bIN|\bSPRE|\bLANGA|\bDE LANGA|\bDINSPRE) $")
# Dupa aceste cuvinte urmeaza o strada, un cartier sau o persoana, nu un UAT.
_MARCA_NELOC = re.compile(
    r"(?:STRADA|STRAZII|STR|BULEVARDUL|BULEVARDULUI|BD|CALEA|CALEII|SOSEAUA|SOSELEI|ALEEA|"
    r"PARCUL|PARCULUI|PIATA|PIETEI|SPLAIUL|INTRAREA|CARTIERUL|CARTIERULUI|"
    r"RAUL|RAULUI|PARAUL|PARAULUI|LACUL|LACULUI|MUNTII|MUNTILOR|MASIVUL|MASIVULUI|"
    r"PRIMARUL|PRIMARULUI|PRIMARITA|PREFECTUL|PREFECTULUI|MINISTRUL|MINISTRULUI|DEPUTATUL|"
    r"SENATORUL|DIRECTORUL|PRESEDINTELE|PRESEDINTELUI|DOMNUL|DOAMNA|PREOTUL|PARINTELE) $")


def _marca(name: str, padded: str) -> int:
    """Marca numelui, peste toate aparitiile: cea mai buna marca POZITIVA (+2 administrativ,
    +1 loc) daca exista; altfel -2 daca macar o aparitie e non-loc („primarului Daniel Baluta"
    nu devine loc doar fiindca a doua mentiune n-are marca); altfel 0."""
    best = None
    neloc = False
    start = 0
    needle = f" {name} "
    while (i := padded.find(needle, start)) != -1:
        before = padded[max(0, i - 24):i + 1]
        if _MARCA_ADMIN.search(before):
            scor = 2
        elif _MARCA_NELOC.search(before):
            scor = -2
            neloc = True
        elif _MARCA_LOC.search(before):
            scor = 1
        else:
            scor = 0
        best = scor if best is None else max(best, scor)
        start = i + 1
    if best and best > 0:
        return best
    return -2 if neloc else 0


def plat_cu_majuscule(value: str) -> str:
    """Ca `norm`, dar pastreaza majusculele: „Primăria Giroc" -> „ Primaria Giroc "."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return f" {re.sub(r'[^A-Za-z0-9]+', ' ', value).strip()} "


def _ca_nume_propriu(name: str, cased: str) -> bool:
    """Numele apare macar o data cu majuscula initiala. Romana scrie titlurile cu litera mica
    (sentence case), deci un cuvant comun care coincide cu o localitate — „un foisor",
    „ferestre", „sarbatoarea" — e scris cu litera mica, iar localitatea reala, cu majuscula."""
    if not cased:
        return True
    for m in re.finditer(rf"(?i)(?<= ){re.escape(name)}(?= )", cased):
        if m.group(0)[0].isupper():
            return True
    return False


def _scor_context(name: str, padded: str, padded_title: str = "", cased: str = "") -> int:
    """Marca + TITLU_BONUS daca numele e in titlu: titlul spune despre ce e stirea, teaserul
    adauga context („Uzina IAR Ghimbav" in titlu bate „producatorul ... din Brasov")."""
    scor = _marca(name, padded) + (TITLU_BONUS if padded_title and f" {name} " in padded_title else 0)
    return scor if _ca_nume_propriu(name, cased) else scor - 2


def locality_from_text(
    text: str,
    source_county: str | None,
    by_name: dict[str, list[dict]],
    points: dict[str, dict] | None = None,
    title: str = "",
) -> dict | None:
    padded = f" {norm(text)} "
    padded_title = f" {norm(title)} " if title else ""
    cased = plat_cu_majuscule(text)
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
    # Contextul primeaza asupra lungimii numelui: „Primaria Giroc ... strada Decebal" e despre
    # Giroc, desi DECEBAL e mai lung. Lungimea ramane departajarea la scor egal (comportamentul
    # de dinainte), deci un text fara nicio marca se rezolva exact ca inainte.
    candidates.sort(key=lambda r: (_scor_context(r["name"], padded, padded_title, cased), len(r["name"])),
                    reverse=True)
    return candidates[0] if candidates else None


def locate(
    article: dict,
    county_keys: list[str],
    by_name: dict[str, list[dict]],
    points: dict[str, dict],
    uat_ids: set[str] | None = None,
    siruta_parents: dict[str, str] | None = None,
) -> dict | None:
    category = article.get("category") or ""
    if category not in {"local", "judetean", "regional"}:
        return None
    # teaser si synthesis raman INTRARE pentru potrivirea geo de mai jos, dar nu mai pleaca
    # spre client: harta randeaza doar titlu + meta (renderList), deci erau 33 KB gzip de
    # payload pe care nicio linie din harta-stiri.js nu le citeste.
    text = " ".join(str(article.get(k) or "") for k in ("title", "teaser", "synthesis"))
    base = {
        "category": category,
        "geo_level": category,
        "slug": article.get("slug", ""),
        "title": article.get("title") or article.get("original_title") or "Fără titlu",
        "published": article.get("published") or "",
        "source": article.get("source") or "",
        "source_name": article.get("source_name") or article.get("source") or "",
    }
    # E3: numărăm numai domeniile măsurate de pipeline, nu lista publicațiilor.
    # Lipsa metadatelor (inclusiv o listă goală/invalidă) rămâne necunoscută.
    confirmate = article.get("cross_confirmed")
    if (isinstance(confirmate, list) and confirmate
            and all(isinstance(domain, str) and domain.strip() for domain in confirmate)):
        base["cross_confirmations"] = len({domain.strip().lower() for domain in confirmate})
    # Sursele originale unite la publicare (select._dedup uneste relatarile identice si
    # pastreaza lista) se pastreaza DOAR cand sunt mai multe: de ele depinde contorul
    # „N surse" din harta — altfel fiecare eveniment parea acoperit de o singura sursa,
    # desi pipeline-ul vazuse doua-trei relatari (masurat pe live 2026-10-03: 21 de
    # articole din fereastra aveau 2-3 surse, toate raportate ca 1).
    surse = article.get("sources")
    if isinstance(surse, list) and len(surse) > 1:
        base["sources"] = [{"name": str(s.get("name") or ""), "url": str(s.get("url") or "")}
                           for s in surse if isinstance(s, dict) and s.get("name")]
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
            "uat": "",
            "x": None,
            "y": None,
            "confidence": "text",
        }
    sc = source_county(str(article.get("source") or ""), county_keys)
    # Judetul REDACTIEI, pastrat separat de judetul faptei: `sc` de mai jos poate fi golit
    # cand localitatea din text muta stirea. Harta se coloreaza dupa locul stirii (IZZ-0433);
    # redactia explica in panou de unde vine numarul, fara sa-l schimbe.
    redactie = sc
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
    county = article.get("editorial_county") or ((sc or tc) if oficial else (tc or sc))
    titlu = str(article.get("title") or "")
    locality = locality_from_text(text, county, by_name, points, title=titlu)
    # Judetul dedus DOAR din numele sursei este cea mai slaba dovada disponibila: spune unde e
    # redactia, nu unde s-a intamplat fapta. Cand textul nu numeste niciun judet SI nicio
    # localitate din judetul sursei, dar numeste una neambigua din alt judet, aceea decide.
    # MASURAT pe corpusul din 2026-08-21: muta 4 articole, toate patru corecte — Medias -> SIBIU
    # (era ALBA, prin alba24), Ortisoara -> TIMIS (criticarad), Sinaia -> PRAHOVA (bizbrasov),
    # Oradea -> BIHOR (alba24). Zero mutari gresite. Cele 11 articole care gasesc o localitate
    # chiar in judetul sursei raman neatinse.
    #
    # Sursele OFICIALE sunt excluse deliberat: o primarie scrie despre teritoriul ei, iar alt
    # oras numit in text e context (echipa oaspete, firma contractanta) — exact regula de mai sus.
    if not article.get("editorial_county") and not oficial and sc and not tc and not locality:
        alta = locality_from_text(text, None, by_name, points, title=titlu)
        # Sa muti o stire din judetul DECLARAT al redactiei cere o marca de loc („din X",
        # „Primaria X") sau numele scris ca nume propriu („IRUM Reghin"), nu un cuvant comun:
        # „un foisor" (gazebo) mutase in DOLJ o stire b365 din Berceni (masurat 2026-10-16).
        marca_alta = _marca(alta["name"], f" {norm(text)} ") if alta else -1
        if alta and norm(alta["county"]) != norm(sc) and marca_alta >= 0 and (
                marca_alta > 0 or _ca_nume_propriu(alta["name"], plat_cu_majuscule(text))):
            county, locality = alta["county"], alta
            # Judetul nu mai vine de la sursa, ci de la localitatea din text: si eticheta de
            # incredere trebuie sa spuna asta, altfel `stats` raporteaza o certitudine falsa.
            sc = None
    if not county and locality:
        county = locality["county"]
    if not county:
        return None
    # Eticheta se schimba DOAR cand sursa chiar a decis contra textului — adica exact in cazurile
    # pe care regula de mai sus le repara. Cand cele doua sunt de acord (63 de articole in corpusul
    # masurat), eticheta ramane cea dinainte: reeticheta lor ar muta 24 de articole din „text" in
    # „source" fara ca atribuirea sa se fi schimbat, iar cifra din `stats` ar parea o regresie.
    if article.get("editorial_county"):
        confidence = "editorial"
    elif oficial and sc and tc and sc != tc:
        confidence = "source"
    else:
        confidence = "text" if tc else "source" if sc else "siruta"
    point = point_for(locality, points)
    # Asignarea DETERMINISTA la UAT: SIRUTA localitatii, direct (orase) sau prin parintele
    # SIRUP (sate). bate hit-testul geometric, care intoarce vecinul cand punctul satului
    # sta mai aproape de granita decat toleranta de simplificare (0.28 units ~ 200 m;
    # masurat 2026-10-02: 102 sate, Apuseni preponderent). JS o prefera pe asta, iar
    # hit-testul ramane doar fallback pentru articolele fara SIRUTA.
    loc_siruta = siruta_key(locality["siruta"]) if locality else ""
    uat_code = ""
    if loc_siruta and uat_ids:
        if loc_siruta in uat_ids:
            uat_code = loc_siruta
        else:
            parent = (siruta_parents or {}).get(loc_siruta, "")
            if parent in uat_ids:
                uat_code = parent
    return {
        **base,
        # Nivelul geografic e PRECIZIA localizarii, nu rubrica: „Local" promite o localitate
        # pe harta. MASURAT pe live 2026-10-16: 288 din 712 articole din rubrica /local/ (40%)
        # n-aveau nicio localitate, iar 14 din /judetean/ aveau — de aici totalurile care se
        # micsorau „inexplicabil" intre niveluri (645 -> 640 -> 596). Rubrica ramane in
        # `category` (linkul articolului depinde de ea).
        "geo_level": "local" if locality else "judetean",
        "region": geo.ETICHETE_REGIUNI.get(geo.regiune_afisare(county), ""),
        "county": county,
        "locality": locality["name"] if locality else "",
        "locality_label": locality_label(locality["name"], county, text) if locality else "",
        # Gol = sursa nu are judet de sediu (presa regionala sau nationala), nu „necunoscut".
        "source_county": redactie or "",
        "siruta": loc_siruta,
        "uat": uat_code,
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
        # Sursele unui eveniment = sursele fiecarui articol PLUS lista `sources` pastrata
        # de dedup-ul editorial (acolo se unesc relatarile identice inainte de harta, deci
        # fara aceasta lista aproape orice eveniment ar numara o singura sursa).
        source_names = set()
        for member in members:
            if member.get("source_name") or member.get("source"):
                source_names.add(member.get("source_name") or member.get("source"))
            for s in member.get("sources") or []:
                if s.get("name"):
                    source_names.add(s["name"])
        source_count = len(source_names)
        for member in members:
            member["event_id"] = event_id
            member["event_article_count"] = len(members)
            member["event_source_count"] = source_count
    return items


def main(articles=None, out=None, publication_digest=None) -> int:
    map_data = load_json(MAP)
    supplied = articles is not None
    articles = articles if supplied else load_json(ARTICLES)
    out = out or OUT
    if not isinstance(articles, list):
        articles = articles.get("articles") or articles.get("items") or []
    counties = map_data.get("judete") or {}
    county_keys = list(counties)
    county_alias = {norm(key): key for key in county_keys}
    _, siruta, siruta_parents = read_siruta(county_alias)
    points = load_locality_points()
    if not points:
        raise RuntimeError("harta_localitati.json nu contine puncte de localitati.")
    # Publicăm doar metadatele proiecției, nu dicționarul mare de localități: browserul
    # sincronizează fundalul decorativ cu viewBox-ul SVG, iar geometria tematică rămâne sursa.
    locality_meta = load_json(LOCALITIES)
    raw_projection = locality_meta.get("projection") if isinstance(locality_meta, dict) else None
    projection_payload = {
        "version": 1,
        "source": locality_meta.get("source", "") if isinstance(locality_meta, dict) else "",
        "source_url": locality_meta.get("source_url", "") if isinstance(locality_meta, dict) else "",
        "source_crs": locality_meta.get("source_crs", "") if isinstance(locality_meta, dict) else "",
        "projection": raw_projection if isinstance(raw_projection, dict) else None,
    }
    uat_ids = load_uat_ids()

    articles = sorted(articles, key=lambda a: str(a.get("published") or ""), reverse=True)

    # IZZ-0422: harta arata doar ce publica si site-ul. In pipeline, main.run aplica
    # `moderation.apply` inainte de `assign_slugs`, deci starea pastreaza articolele
    # ascunse (blocklist, spam pariuri, takedowns) FARA slug — si pana acum harta le
    # colecta ca evenimente fara link (masurat 2026-10-03: 22 in fereastra de 1.500).
    # Acelasi filtru, inainte de fereastra, ca sloturile sa ramana pentru ce e vizibil.
    inainte_filtru = len(articles)
    if not supplied:
        articles = moderation.apply(articles, moderation.load())
    ascunse = inainte_filtru - len(articles)
    if ascunse:
        print(f"harta-stiri: moderarea a ascuns {ascunse} articole — nu ajung pe harta.")

    # Dupa filtru, un articol cu URL dar fara slug e abatere intre moderare si
    # assign_slugs, nu o stare legitima. Avertisment, nu esec: harta-stiri.js randeaza
    # inregistrarile fara slug ca text simplu, nu ca ancora (un link ar fi fost
    # `/local//`, adica pagina de categorie).
    cu_url_fara_slug = [a for a in articles[:MAX_ARTICLES] if a.get("url") and not a.get("slug")]
    if cu_url_fara_slug:
        print(f"harta-stiri: ATENTIE {len(cu_url_fara_slug)} articole cu URL dar fara slug "
              f"(ex: {str(cu_url_fara_slug[0].get('title') or '')[:60]!r}) — vor aparea pe harta "
              f"fara link, ca text simplu.")

    located = []
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    surse_pe_harta: set[str] = set()
    for article in articles[:MAX_ARTICLES]:
        item = locate(article, county_keys, siruta, points, uat_ids, siruta_parents)
        if item:
            # Anunturi cu data in viitor (cazul real: „colectare deseuri 01.01.2027",
            # publicat cu published in 2027) ar urca `latest_article_at` si meta din lista
            # intr-un an care nu a venit. Pentru HARTA data viitoare nu e informatie.
            if item["published"] > now_iso:
                item["published"] = now_iso
            if item["source"]:
                surse_pe_harta.add(item["source"])
            located.append(item)

    # Backfill de acoperire (vezi BACKFILL_DAYS): sursele locale active care n-au prins
    # fereastra de volum aduc cel mult cate un articol — ultimul publicat — daca intra
    # sub pragul de vechime. Plecarea din fereastra, nu din tot istoricul, tine harta
    # oglinda a zilelor recente: o primarie tacuta de 3 luni NU aprinde judetul.
    prag_backfill = now_dt - timedelta(days=BACKFILL_DAYS)
    for article in articles[MAX_ARTICLES:]:
        source = str(article.get("source") or "")
        if not source or source in surse_pe_harta:
            continue
        if (article.get("category") or "") not in {"local", "judetean"}:
            continue
        published = _published_at(article.get("published"))
        if not published or published < prag_backfill:
            continue
        item = locate(article, county_keys, siruta, points, uat_ids, siruta_parents)
        if item:
            item["backfill"] = True
            surse_pe_harta.add(source)
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
        "publication_digest": publication_digest,
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
            # Fluxul intre judete (IZZ-0433): relatari despre un judet scrise de presa altuia,
            # si cate vin din presa fara judet de sediu. Masurat la decizie: 4,1% si 23%.
            "cross_county": sum(bool(a.get("source_county")) and bool(a.get("county"))
                                and a["source_county"] != a["county"] for a in located),
            "source_county_unknown": sum(bool(a.get("county")) and not a.get("source_county")
                                         for a in located),
            "counties": len({a["county"] for a in located if a.get("county")}),
            "regions": len({a["region"] for a in located if a.get("region")}),
            "localities": len(named_localities),
            "county_only": sum(bool(a.get("county")) and not a.get("locality") for a in located),
            "coordinates": geocoded_articles,
            "geocoded_localities": len({a["siruta"] or f"{norm(a['locality'])}|{a['county']}" for a in located if a.get("locality") and a.get("x") is not None and a.get("y") is not None}),
            "sources": len({a.get("source") for a in located if a.get("source")}),
            "backfill": sum(1 for a in located if a.get("backfill")),
        },
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    projection_out = os.path.join(os.path.dirname(out), "projection.json")
    with open(projection_out, "w", encoding="utf-8") as fh:
        json.dump(projection_payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"harta-stiri: {len(located)} articole, {payload['stats']['events']} evenimente, {payload['stats']['localities']} localități confirmate, {payload['stats']['coordinates']} coordonate -> {out}; proiecție -> {projection_out}")
    return 0


if __name__ == "__main__":
    # Windows: cp1252 nu are „ș"/„ț", deci un `print` cu diacritice arunca
    # UnicodeEncodeError si scriptul iese cu 1 — indistingibil de un esec real de
    # continut. Masurat 2026-08-20: `qa_check.py` iesea cu 1 pe date valide, iar cu
    # PYTHONIOENCODING=utf-8 cu 0. In CI (Linux, UTF-8) nu se vede. Acelasi idiom ca
    # in `scan_homepages.py`, extins la toate punctele de intrare cu diacritice.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())

