#!/usr/bin/env python
"""Fotografii oficiale pentru entitatile publice din articole (Wikidata P18).

Ruleaza in GitHub Actions (are internet; sandbox-urile nu). Pentru entitatile AI
din articolele publicate cauta pe Wikidata o potrivire STRICTA si, doar daca
entitatea e "photo-worthy" -- fie persoana publica (om P31=Q5 cu functie P39 sau
notorietate), fie o entitate notorie dintr-un tip sigur din SAFE_TYPES (institutie,
oras, tara, club, universitate, cladire) -- si are imagine reprezentativa (P18) sub
licenta libera, descarca o miniatura mica in media/portraits/ (auto-gazduita ->
browserul cititorilor nu atinge servere terte) si scrie creditul in
data/portraits.json (comis). Negativele se cacheaza ca sa nu re-interogam.

  python tools/fetch_portraits.py          # incremental, plafonat

Env: MAX_PORTRAIT_LOOKUPS (default 20)
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from generator import state  # noqa: E402
from generator.util import strip_diacritics  # noqa: E402

CACHE = os.path.join(ROOT, "data", "portraits.json")
OUTDIR = os.path.join(ROOT, "media", "portraits")
MAX_LOOKUPS = int(os.getenv("MAX_PORTRAIT_LOOKUPS", "20"))
UA = {"User-Agent": "izz.ro-portraits/1.0 (contact@izz.ro)"}
THUMB_W = 320   # sursa pt. hero-ul de subiect 160px CSS la 2x DPR (retina crisp); strip-ul 96px e acoperit din plin

# licente Commons acceptate pentru re-gazduire cu atribuire
_LICENSE_OK = re.compile(r"^(cc[ -]|cc0|public domain|pd[ -]|attribution)", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", strip_diacritics((s or "").strip().lower()))


def license_ok(short_name: str) -> bool:
    return bool(_LICENSE_OK.match((short_name or "").strip()))


def clean_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def wd_match(name: str) -> str | None:
    """Cauta entitatea; accepta DOAR potrivire exacta (normalizata) pe label/alias."""
    q = urllib.parse.quote(name)
    d = _get(f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={q}"
             f"&language=ro&uselang=ro&type=item&limit=5&format=json")
    want = norm(name)
    for hit in d.get("search", []):
        labels = [hit.get("label", "")] + (hit.get("aliases") or [])
        if any(norm(l) == want for l in labels):
            return hit["id"]
    return None


def wd_entity(qid: str) -> dict:
    d = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    return d["entities"][qid]


SITELINKS_MIN = 15   # prag de notorietate: prezenta in >=15 editii Wikipedia

# Tipuri Wikidata (P31) de entitate NEUMANA pentru care P18 e o fotografie
# reprezentativa si neambigua (sediu, skyline, stadion) -- nu un logo (acela e P154).
# Restrangem strict la clase care apar frecvent in stirile RO si al caror portret
# vizual e sugestiv. Orice altceva -> fallback pe coperta generata.
SAFE_TYPES = frozenset({
    "Q43229",    # organizatie
    "Q4830453",  # afacere / business
    "Q6881511",  # intreprindere
    "Q783794",   # companie
    "Q891723",   # companie publica listata
    "Q7278",     # partid politic
    "Q327333",   # agentie guvernamentala
    "Q2659904",  # organizatie guvernamentala
    "Q192350",   # minister
    "Q476028",   # club de fotbal
    "Q847017",   # club sportiv
    "Q12973014", # echipa sportiva
    "Q515",      # oras
    "Q1549591",  # oras mare
    "Q6256",     # tara
    "Q3624078",  # stat suveran
    "Q3918",     # universitate
    "Q41176",    # cladire
    "Q33506",    # muzeu
    "Q1248784",  # aeroport
    "Q4989906",  # monument
})


def entity_types(claims: dict) -> set:
    """Toate QID-urile P31 (instance of) ale entitatii."""
    out = set()
    for c in claims.get("P31", []):
        qid = c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
        if qid:
            out.add(qid)
    return out


def is_public_figure(claims: dict, sitelinks: int = 0) -> bool:
    """Om (P31=Q5) care fie detine functie publica (P39), fie e notoriu la nivel
    international (>=SITELINKS_MIN editii Wikipedia) -- sportivi/artisti celebri.
    Ambele cai exclud structural omonimii obscuri."""
    human = "Q5" in entity_types(claims)
    return human and (bool(claims.get("P39")) or sitelinks >= SITELINKS_MIN)


def is_photo_worthy(claims: dict, sitelinks: int = 0) -> bool:
    """Entitate careia i se poate atasa o fotografie reala, legala si neambigua:
    fie persoana publica (regula existenta), fie o entitate dintr-un tip din
    SAFE_TYPES suficient de notorie (>=SITELINKS_MIN editii Wikipedia). Notorietatea
    + potrivirea exacta pe label previn atasarea unei poze gresite (omonime)."""
    if is_public_figure(claims, sitelinks):
        return True
    return bool(entity_types(claims) & SAFE_TYPES) and sitelinks >= SITELINKS_MIN


def portrait_file(claims: dict) -> str | None:
    for c in claims.get("P18", []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, str):
            return v
    return None


def commons_info(filename: str) -> dict | None:
    """thumburl + credit (artist, licenta, pagina fisierului) din extmetadata."""
    t = urllib.parse.quote("File:" + filename)
    d = _get(f"https://commons.wikimedia.org/w/api.php?action=query&titles={t}"
             f"&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth={THUMB_W}&format=json")
    pages = d.get("query", {}).get("pages", {})
    for p in pages.values():
        for ii in p.get("imageinfo", []):
            meta = ii.get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value", "")
            if not license_ok(lic):
                return None
            return {"thumb": ii.get("thumburl"),
                    "page": ii.get("descriptionurl"),
                    "artist": clean_html(meta.get("Artist", {}).get("value", "")),
                    "license": lic}
    return None


def slugish(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm(name)).strip("-")[:60] or "persoana"


def main() -> int:
    arts = [a for a in state.load() if a.get("title")]
    names: list = []
    for a in arts:
        for e in a.get("entities") or []:
            if e and e not in names and len(e.split()) >= 2:   # >=2 cuvinte: nume/denumiri specifice (evita omonime dintr-un cuvant)
                names.append(e)
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    os.makedirs(OUTDIR, exist_ok=True)
    done = 0
    for name in names:
        key = norm(name)
        if key in cache:
            continue
        if done >= MAX_LOOKUPS:
            break
        done += 1
        entry: dict = {"miss": True}
        try:
            qid = wd_match(name)
            if qid:
                ent = wd_entity(qid)
                claims = ent.get("claims", {})
                sitelinks = len(ent.get("sitelinks", {}))
                f = portrait_file(claims)
                if is_photo_worthy(claims, sitelinks) and f:
                    info = commons_info(f)
                    if info and info.get("thumb"):
                        fn = f"{slugish(name)}.jpg"
                        req = urllib.request.Request(info["thumb"], headers=UA)
                        data = urllib.request.urlopen(req, timeout=30).read()
                        if len(data) > 2000:
                            open(os.path.join(OUTDIR, fn), "wb").write(data)
                            entry = {"name": name, "qid": qid, "img": f"portraits/{fn}",
                                     "artist": info["artist"], "license": info["license"],
                                     "page": info["page"]}
        except Exception as exc:  # o entitate esuata nu opreste restul
            print(f"  ! {name}: {exc}")
            done -= 1              # eroare de retea -> nu consuma plafonul, reincearca alta data
            continue
        cache[key] = entry
        print(f"  {'ok  ' if not entry.get('miss') else 'miss'} {name}")
        time.sleep(1)              # politete API
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=0)
    hits = sum(1 for v in cache.values() if not v.get("miss"))
    print(f">> portraits: {done} interogari noi, {hits} portrete in cache, {len(cache)} total intrari")
    return 0


if __name__ == "__main__":
    sys.exit(main())
