#!/usr/bin/env python
"""Fotografie LEAD reala per articol (Wikidata P18) -> imagine principala "foto".

Ruleaza in GitHub Actions (are internet; sandbox-urile nu). Pentru fiecare articol
publicat cauta prima entitate "photo-worthy" (vezi fetch_portraits.is_photo_worthy)
a carei imagine P18 e, in acelasi timp:
  - LANDSCAPE (latime >= 1.2 x inaltime) -> se incadreaza curat in 960x504 / 1200x630
    fara sa taie un portret vertical (bara de calitate "Zero Zgomot"), si
  - ATRIBUIRE-LIBERA (Public domain / CC0) -> poate aparea si pe carduri/og, unde
    regula sect. 7 interzice orice eticheta de credit.
Daca gaseste, descarca o rendite mare, o incadreaza cu Pillow in cover (1200x630) +
art (960x504, JPEG+WebP), auto-gazduite in media/leads/, si scrie intrarea in
data/leadphotos.json (cheie = art_id, comis). Negativele se cacheaza.

Fiecare candidat trece printr-un ULTIM filtru: judecatorul AI (generator/photojudge)
verifica potrivirea foto<->articol (respinge partea care a pierdut / subiectul gresit /
un rezultat fals). Cu GEMINI_API_KEY activ e pornit; fara cheie ramane pe regulile
deterministe. Fail-safe: apel esuat -> se sare candidatul.

Fotografiile CC-BY (atribuire obligatorie) NU intra aici -- raman in strip-ul cu
credit gestionat de fetch_portraits.py. Fara potrivire -> articolul pastreaza
coperta generata (pictograma). Orice eroare pe o entitate nu opreste restul.

  python tools/fetch_leadphotos.py          # incremental, plafonat

Env: MAX_LEAD_LOOKUPS (default 20)
"""
import importlib.util
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from generator import state, htmlart, localities, photojudge  # noqa: E402
from generator.process import get_provider  # noqa: E402

# reutilizam pipeline-ul Wikidata deja validat (potrivire stricta, licenta, notorietate)
_spec = importlib.util.spec_from_file_location(
    "fetch_portraits", os.path.join(ROOT, "tools", "fetch_portraits.py"))
fp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fp)

try:
    from PIL import Image
except ImportError:
    Image = None

CACHE = os.path.join(ROOT, "data", "leadphotos.json")
OUTDIR = os.path.join(ROOT, "media", "leads")
MAX_LOOKUPS = int(os.getenv("MAX_LEAD_LOOKUPS", "20"))
# Versiunea REGULILOR care produc un `miss`. Creste cand apare o ruta noua de cautare:
# miss-urile scrise sub o versiune mai veche se reincearca o data (vezi `_needs_lookup`).
# v2 = adaugarea rutei de localitate (2026-08-01).
MISS_VERSION = 2
UA = fp.UA
LEAD_W = 1400                       # rendite sursa: acopera 1200x630 la calitate buna
COVER_W, COVER_H = 1200, 630        # og / share (fara text: foto curata)
ART_W, ART_H = 960, 504            # imaginea de pe carduri / hero / pagina de articol
LANDSCAPE_RATIO = 1.2              # latime >= 1.2 x inaltime -> "clar landscape"

# licente atribuire-LIBERA (pot aparea pe carduri/og fara credit). CC-BY e EXCLUS.
import re  # noqa: E402
_PD_OK = re.compile(r"^(cc0|cc[ -]?zero|public domain|pd([ -]|$))", re.I)


def is_public_domain(short_name: str) -> bool:
    """Doar Public domain / CC0 -- fara obligatie de atribuire. CC-BY(-SA) => False."""
    return bool(_PD_OK.match((short_name or "").strip()))


def is_landscape(w: int, h: int) -> bool:
    return bool(w) and bool(h) and w >= h * LANDSCAPE_RATIO


def is_big_enough(w: int) -> bool:
    """Coperta og e 1200x630; sub atat imaginea ar fi marita si vizibil interpolata."""
    return bool(w) and w >= localities.MIN_WIDTH


def qualifies(info: dict) -> bool:
    """info = {width,height,license,...}. Poate deveni LEAD (carduri/og) daca e
    destul de mare, landscape SI atribuire-libera."""
    return is_big_enough(info.get("width", 0)) and \
        is_landscape(info.get("width", 0), info.get("height", 0)) and \
        is_public_domain(info.get("license", ""))


def crop_to(im, w: int, h: int):
    """Redimensioneaza + incadreaza central la exact w x h (fara deformare)."""
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    nw, nh = max(w, round(sw * scale)), max(h, round(sh * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return im.crop((left, top, left + w, top + h))


def commons_lead_info(filename: str) -> dict | None:
    """Marime originala + rendite mare + credit. None daca lipseste imaginea."""
    t = urllib.parse.quote("File:" + filename)
    d = fp._get(f"https://commons.wikimedia.org/w/api.php?action=query&titles={t}"
                f"&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth={LEAD_W}&format=json")
    for p in d.get("query", {}).get("pages", {}).values():
        for ii in p.get("imageinfo", []):
            meta = ii.get("extmetadata", {})
            return {"thumb": ii.get("thumburl"),
                    "width": ii.get("width", 0),
                    "height": ii.get("height", 0),
                    "license": meta.get("LicenseShortName", {}).get("value", ""),
                    "artist": fp.clean_html(meta.get("Artist", {}).get("value", "")),
                    "page": ii.get("descriptionurl")}
    return None


def _save_renditions(data: bytes, slug: str) -> dict | None:
    """Din rendite descarcata produce cover+art+webp incadrate. None daca invalida."""
    import io
    im = Image.open(io.BytesIO(data)).convert("RGB")
    cover = crop_to(im, COVER_W, COVER_H)
    art = crop_to(im, ART_W, ART_H)
    cov_p = os.path.join(OUTDIR, f"{slug}.c.jpg")
    art_p = os.path.join(OUTDIR, f"{slug}.jpg")
    web_p = os.path.join(OUTDIR, f"{slug}.webp")
    cover.save(cov_p, quality=86)
    art.save(art_p, quality=86)
    art.save(web_p, quality=82)
    if os.path.getsize(cov_p) < 3000 or os.path.getsize(art_p) < 3000:
        return None
    return {"cover": f"leads/{slug}.c.jpg", "art": f"leads/{slug}.jpg", "webp": f"leads/{slug}.webp"}


def _caption(filename: str) -> str:
    """Numele fisierului Commons e cel mai puternic semnal semantic despre poza
    (ex. 'Echipa U Cluj sarbatorind promovarea'). Il facem lizibil pt. judecatorul AI."""
    base = re.sub(r"\.[A-Za-z0-9]+$", "", urllib.parse.unquote(filename or ""))
    return re.sub(r"[_\s]+", " ", base).strip()


def _needs_lookup(aid: str, a: dict, cache: dict) -> bool:
    """Articolul trebuie interogat, sau cache-ul e definitiv?

    Un `miss` nu e adevar etern: e rezultatul REGULILOR care existau cand a fost scris.
    Cele 1684 de miss-uri din cache au fost produse cand exista doar ruta pe entitati;
    fara invalidare, `aid in cache` ar bloca ruta de localitate pe tot continutul actual
    si slice-ul n-ar avea niciun efect vizibil. Miss-urile mai vechi decat MISS_VERSION
    se reincearca O SINGURA DATA, si doar pentru articolele eligibile pentru noua ruta
    (`pl_*`) — restul raman cache-uite, ca sa nu se recheltuie plafonul degeaba.
    """
    entry = cache.get(aid)
    if entry is None:
        return True
    if not entry.get("miss"):
        return False                                  # hit: nu se reinterogheaza niciodata
    if entry.get("v", 0) >= MISS_VERSION:
        return False
    return bool(localities.eligible(a))


def lead_for_locality(a: dict, by_name: dict) -> dict | None:
    """Fotografia LOCALITATII pentru o stire venita de la primaria acelei localitati.

    Se incearca INAINTEA rutei pe entitati, fiindca e mult mai fiabila: cheia e slug-ul
    determinist al sursei (`pl_<judet>_<localitate>`), nu entitatile extrase din text.

    Poarta de licență este `qualifies`, nu `localities.usable`: o fotografie LEAD
    ajunge și în carduri, hero și previzualizări sociale, unde creditul complet nu este
    garantat. Din acest motiv acceptăm numai domeniul public sau CC0; CC-BY și CC-BY-SA
    rămân excluse din fluxul de copertă, chiar dacă ar putea fi folosite într-un context
    separat cu legendă completă.

    NU trece prin `photojudge`: acela întreabă dacă poza e o ilustrație EXACTĂ a
    subiectului, test potrivit pentru „poza persoanei X pe știrea despre X”, dar greșit
    aici — poza de localitate este declarată ILUSTRAȚIE, nu document al evenimentului.
    Garanțiile rămân deterministe: localitatea corectă din județul corect, licență fără
    obligație de atribuire și dimensiune suficientă.
    """
    rec = localities.locality_for_article(a, by_name)
    if not rec:
        return None
    info = commons_lead_info(rec["img"])
    if not info or not info.get("thumb") or not qualifies(info):
        return None
    data = urllib.request.urlopen(
        urllib.request.Request(info["thumb"], headers=UA), timeout=30).read()
    if len(data) < 3000:
        return None
    # cheia de fisier e QID-ul, NU numele: 4 comune Costesti, 3 Ungheni, 2 Zarnesti si
    # 2 Faurei distincte au poze diferite si ar scrie toate in acelasi `loc-costesti.jpg`,
    # ultima descarcare suprascriind-o pe precedenta -> poza altui judet pe stirea locala.
    rend = _save_renditions(data, f"loc-{rec['qid']}")
    if not rend:
        return None
    return {**rend, "artist": info["artist"], "license": info["license"],
            "page": info["page"], "name": rec["display"], "kind": "locality"}


def lead_for_article(a: dict, provider=None) -> dict | None:
    """Prima entitate a articolului cu P18 landscape + atribuire-libera care trece SI
    de judecatorul AI de potrivire (photojudge) -> intrare LEAD. None (miss) altfel."""
    summary = a.get("synthesis") or a.get("teaser") or ""
    for name in a.get("entities") or []:
        if not name or len(name.split()) < 2:
            continue
        qid = fp.wd_match(name)
        if not qid:
            continue
        ent = fp.wd_entity(qid)
        claims = ent.get("claims", {})
        if not fp.is_photo_worthy(claims, len(ent.get("sitelinks", {}))):
            continue
        f = fp.portrait_file(claims)
        if not f:
            continue
        info = commons_lead_info(f)
        if not info or not info.get("thumb") or not qualifies(info):
            continue
        # ultima poarta: AI verifica potrivirea foto<->articol (nu partea care a pierdut,
        # nu un rezultat fals). provider None -> True; eroare -> False (fail-safe).
        if not photojudge.photo_fits(provider, a.get("title", ""), summary, name, _caption(f)):
            continue
        data = urllib.request.urlopen(urllib.request.Request(info["thumb"], headers=UA), timeout=30).read()
        if len(data) < 3000:
            continue
        slug = fp.slugish(name)
        rend = _save_renditions(data, slug)
        if not rend:
            continue
        return {**rend, "artist": info["artist"], "license": info["license"],
                "page": info["page"], "name": name}
    return None


def main() -> int:
    if Image is None:
        print(">> Pillow indisponibil -- lead photos skip"); return 0
    arts = [a for a in state.load() if a.get("title")]
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    os.makedirs(OUTDIR, exist_ok=True)
    provider = get_provider()   # judecator AI foto<->articol; None fara cheie -> reguli deterministe
    print(f">> photo judge: {'ON (' + provider.name + ')' if provider else 'OFF (fara cheie AI) -> reguli deterministe'}")
    by_name = localities.load_dataset()
    print(f">> localitati: {len(by_name)} nume in dataset"
          f"{' — LIPSA, ruta localitate inactiva' if not by_name else ''}")
    done = 0
    for a in arts:
        aid = htmlart.art_id(a)
        if not _needs_lookup(aid, a, cache) or done >= MAX_LOOKUPS:
            continue
        done += 1
        try:
            # intai localitatea (determinista, acoperire mare), apoi entitatile din text
            entry = lead_for_locality(a, by_name) or lead_for_article(a, provider)
        except Exception as exc:  # o entitate/retea esuata nu opreste restul
            print(f"  ! {aid}: {exc}")
            done -= 1              # eroare de retea -> nu consuma plafonul
            continue
        cache[aid] = entry or {"miss": True, "v": MISS_VERSION}
        print(f"  {'ok  ' if entry else 'miss'} {aid} "
              f"{entry['name'] + ' [' + entry.get('kind', 'entity') + ']' if entry else ''}")
        time.sleep(1)             # politete API
    # scriem doar hit-urile in fisierul consumat de render (miss-urile raman doar in memorie/cache-disk)
    hits = {k: v for k, v in cache.items() if not (v or {}).get("miss")}
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=0)
    print(f">> leadphotos: {done} interogari noi, {len(hits)} lead-uri, {len(cache)} intrari cache")
    return 0


if __name__ == "__main__":
    sys.exit(main())
