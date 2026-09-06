"""Date de eveniment desenate pe coperta: prognoza meteo pentru stirile locale.

Clasa B din propunerea 2026-09-03: cand o stire are DATE numerice (temperatura,
epicentru, serii), coperta o deseneaza din date — grafica proprie, zero drepturi
de terti. Felia 1: meteo. Poarta (categoria local/judetean + cuvinte de vreme +
sursa de primarie) reutilizeaza mecanismul din `localities.py`; coordonatele
sunt luate pe QID-ul din dataset si puse in cache comis
(`data/localities_coords.json`), ca build-ul sa nu depinda de Wikidata la
fiecare rulare.

Fail-safe (sect. 7 "No mangled output"): orice veriga lipseste — nu e stire de
vreme, sursa nu e primarie, qid fara coordonate, open-meteo picat — si
articolul NU primeste grafic: coperta ramane cea de azi. Niciodata o coperta
cu date inventate. Chartul e desenat de `htmlart._t_meteo` din
`event_chart`; regenerarea imaginii la schimbarea datelor e asigurata de
semnatura din `tools/gen_images.py`.

Partile de retea sunt izolate in `_http_get`; parsarea si poarta sunt pure si
testate offline.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import urllib.request

from . import geo, localities

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COORDS = os.path.join(ROOT, "data", "localities_coords.json")
TARI = os.path.join(ROOT, "data", "tari.json")
UA = "izz.ro-pipeline/1.0 (coperti din date; contact: contact@izz.ro)"

_ZILE = ["L", "M", "M", "J", "V", "S", "D"]
_METEO = re.compile(
    r"meteo|vreme|prognoz|ninsoare|canicul|ploaie|averse|descărcări|"
    r"ger\b|îngheț|umidit| temperatur", re.I)
_CUTREMUR = re.compile(r"\bcutremur|\bseism\b|\bseisme\b", re.I)
# Caseta României (toată seismicitatea din țară, Vrancea inclusiv, întra în ea).
_RO_BOX = {"minlatitude": 43.5, "maxlatitude": 48.5, "minlongitude": 20.0, "maxlongitude": 30.0}
_MAG_MIN = 2.5
_EMSC = "https://www.seismicportal.eu/fdsnws/event/1/query?format=json&orderby=magnitude&limit=30"


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=20).read()


def gate(a: dict, by_name: dict) -> dict | None:
    """Articolul de vreme -> inregistrarea localitatii lui, altfel None.

    Locul NU e rezolvat aici cu o euristică nouă — reutilizează exact lanțul
    care desenează badge-ul de județ pe coperte (geo.judet_sursa pe sursă,
    apoi geo.loc_din_titlu cu garzile lui de ambiguitate, măsurate pe setul
    de aur; fallback `loc_din_sursa` pentru primării). Apoi numele merge în
    datasetul de localități (`localities.match`, care refuza deja omonimele
    dintre județe) și cere qid + poza, pentru qid -> coordonate.
    """
    if a.get("category") not in localities._GEO_CATEGORIES:
        return None
    text = f"{a.get('title') or ''} {a.get('teaser') or ''}"
    if not _METEO.search(text):
        return None
    judet = geo.judet_sursa(a.get("source"))
    if not judet:
        parsed = localities.parse_source_slug(a.get("source") or "")
        judet = parsed[0] if parsed else None
    if not judet:
        return None
    nume = (geo.loc_din_titlu(a.get("title") or "", judet)
            or geo.loc_din_sursa(a.get("source")))
    if not nume:
        return None
    key = re.sub(r"^judetul\s+", "", localities.norm(nume), flags=re.I)
    rec = localities.match(judet, key, by_name)
    if not rec or not rec.get("img") or not rec.get("qid"):
        return None
    return {**rec, "display": rec.get("label") or key.title()}


def _load_coords(path: str = COORDS) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def coords_for(qid: str, cache: dict, path: str = COORDS) -> tuple[float, float] | None:
    """(lat, lon) din cache; la miss, P625 din Wikidata, scris apoi in cache."""
    if qid in cache:
        lat, lon = cache[qid]
        return float(lat), float(lon)
    try:
        raw = json.loads(_http_get(
            f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"))
        val = raw["entities"][qid]["claims"]["P625"][0]["mainsnak"]["datavalue"]["value"]
        lat, lon = float(val["latitude"]), float(val["longitude"])
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None
    cache[qid] = [lat, lon]
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError:
        pass  # cache esuat -> doar refetch la rularea urmatoare
    return lat, lon


def parse_open_meteo(payload: dict) -> list[dict]:
    """Raspuns daily -> [{zi, lit, max, min}]. Pure; ridica KeyError la forma stricata."""
    daily = payload["daily"]
    out = []
    for day, tmax, tmin in zip(daily["time"],
                               daily["temperature_2m_max"],
                               daily["temperature_2m_min"]):
        lit = _ZILE[datetime.date.fromisoformat(day).weekday()]
        out.append({"zi": day[8:], "lit": lit,
                    "max": round(float(tmax)), "min": round(float(tmin))})
    return out


def prognoza(loc: dict, lat: float, lon: float) -> dict | None:
    """Chartul meteo pentru localitate, sau None la orice eșec de retea/parsare."""
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}"
           "&daily=temperature_2m_max,temperature_2m_min"
           "&timezone=Europe%2FBucharest&forecast_days=7")
    try:
        zile = parse_open_meteo(json.loads(_http_get(url)))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not zile:
        return None
    return {"tip": "meteo", "localitate": loc.get("display") or "",
            "zile": zile, "sursa": "open-meteo.com"}


# ---------------------------------------------------------------- cutremure --
def parse_emsc(payload: dict) -> list[dict]:
    """Feature-urile FDSN -> [{mag, lat, lon, adancime, timp}]. Pure; ridica KeyError."""
    out = []
    for f in payload["features"]:
        p, c = f["properties"], f["geometry"]["coordinates"]
        mag = p.get("mag")
        if mag is None:
            continue
        out.append({"mag": round(float(mag), 1),
                    "lat": float(c[1]), "lon": float(c[0]),
                    # EMSC livreaza uneori adancimi negative (chibritul dat invers);
                    # Vrancea are seisme intermediare ~100 km, deci |d| e valoarea reala.
                    "adancime": max(0, abs(round(float(c[2])))),
                    "timp": (p.get("time") or "")[:10]})
    return out


def _fereastra_cutremur(a: dict) -> tuple[str, str]:
    """[publicat-2 zile, publicat+6h] in ISO, pe data publicarii (fara ora -> miezul noptii)."""
    pub = (a.get("published") or "")[:10]
    d0 = datetime.date.fromisoformat(pub)
    return ((d0 - datetime.timedelta(days=2)).isoformat(),
            (d0 + datetime.timedelta(hours=30)).isoformat()[:10])


# ------------------------------------------------------------------- tari --
_TARI_CACHE: dict | None = None


def _incarca_tari() -> dict:
    """{nume normalizat (fara diacritice): inregistrare}. Fail-safe {} la fisier lipsa."""
    global _TARI_CACHE
    if _TARI_CACHE is not None:
        return _TARI_CACHE
    try:
        raw = json.load(open(TARI, encoding="utf-8"))
        _TARI_CACHE = {localities.norm(nume): recs
                       for nume, recs in raw.get("by_name", {}).items()}
    except (OSError, ValueError):
        _TARI_CACHE = {}
    return _TARI_CACHE


def tara(a: dict, tari: dict | None = None) -> dict | None:
    """Tara numita in titlu/rezumat, sau None. Cea mai lunga denumire bate (Nigeria > Niger;
    \b la granita de cuvant taie 'Niger' din 'Nigeria' oricum). Numarul complexe
    ('M 5,2') nu poate colisiona pentru ca numele incep cu litera."""
    tari = tari if tari is not None else _incarca_tari()
    if not tari:
        return None
    text = " " + localities.norm(f"{a.get('title') or ''} {a.get('teaser') or ''}") + " "
    for nume in sorted(tari, key=len, reverse=True):
        if re.search(rf"\b{re.escape(nume)}\b", text):
            return tari[nume][0]
    return None


def cutremur(a: dict, tari: dict | None = None) -> dict | None:
    """Cel mai puternic seism relevant pentru articol in fereastra lui, sau None.

    Doua rute deterministe, in ordine:
      - TARA numita in text (stirile externe): cutia EMSC = centroid ± jumatatea
        tarii (din data/tari.json, generat din Wikidata), minmagnitude 4.0;
      - ROMANIA (local/judetean): caseta fixa a tarii, minmagnitude 2.5. EMSC, nu
        USGS — masurat 2026-09-06: Vrancea M2.5-3.4 e in EMSC, absent din USGS.
    Alegerea max-magnitudine e determinista; fail-safe complet la retea/parsare.
    """
    text = f"{a.get('title') or ''} {a.get('teaser') or ''}"
    if not _CUTREMUR.search(text):
        return None
    rec = tara(a, tari)
    if rec:
        box = (f"minlatitude={rec['lat'] - rec['jumatate_grade']:.2f}"
               f"&maxlatitude={rec['lat'] + rec['jumatate_grade']:.2f}"
               f"&minlongitude={rec['lon'] - rec['jumatate_grade'] * 1.35:.2f}"
               f"&maxlongitude={rec['lon'] + rec['jumatate_grade'] * 1.35:.2f}")
        mag_min, loc = 4.0, rec["ro"]
    elif a.get("category") in localities._GEO_CATEGORIES:
        box = "&".join(f"{k}={v}" for k, v in _RO_BOX.items())
        mag_min, loc = _MAG_MIN, None
    else:
        return None
    t0, t1 = _fereastra_cutremur(a)
    url = f"{_EMSC}&starttime={t0}&endtime={t1}&minmagnitude={mag_min}&{box}"
    try:
        evenimente = parse_emsc(json.loads(_http_get(url)))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not evenimente:
        return None
    top = max(evenimente, key=lambda e: (e["mag"], e["timp"]))
    return {"tip": "cutremur", "mag": top["mag"], "lat": top["lat"], "lon": top["lon"],
            "adancime": top["adancime"], "data": top["timp"], "sursa": "EMSC", "loc": loc}


def attach(articles: list[dict], by_name: dict | None = None,
           coords_path: str = COORDS) -> int:
    """Ataseaza `event_chart` articolelor eligibile, in loc. Returneaza cate.

    Un singur apel per rulare in pipeline, pe articolele NOI; cache-ul de
    coordonate creste incremental si se comisoreaza odata cu stare.
    """
    by_name = by_name if by_name is not None else localities.load_dataset()
    tari = _incarca_tari()
    cache = _load_coords(coords_path)
    n = 0
    for a in articles:
        if a.get("event_chart"):
            continue
        chart = None
        loc = gate(a, by_name)
        if loc and loc.get("qid"):
            latlon = coords_for(loc["qid"], cache, coords_path)
            if latlon:
                chart = prognoza(loc, latlon[0], latlon[1])
        if chart is None:
            chart = cutremur(a, tari)
        if chart:
            a["event_chart"] = chart
            n += 1
    return n
