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

Ruta pe ENTITATI ramane doar Public domain / CC0. Ruta de LOCALITATE (stirile primariilor)
accepta si CC BY / CC BY-SA (`localities.usable`): render.py le tine doar pe pagina de
articol, sub legenda completa, niciodata pe card sau in og:image (#205, 2026-08-29).
Fara potrivire -> articolul pastreaza coperta generata. Orice eroare pe o entitate nu
opreste restul. Fiecare miss pastreaza MOTIVUL (`motiv_loc`, `motiv_ent`), iar poza unei
localitati deja cunoscute se refoloseste fara retea si fara plafon (`index_localitati`).

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
from generator import state, htmlart, localities, photojudge, render  # noqa: E402
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
# v3 = poarta rutei de localitate trece pe `localities.usable` (CC BY permis, doar pe pagina de
#      articol — render.py separa nivelurile din #205) + motivul fiecarui miss (2026-10-17).
MISS_VERSION = 3
# Sub atatea articole in stare, curatarea cache-ului se sare: o stare partiala ar sterge
# intrari valide si ar retrimite sute de interogari. Starea reala are ~10.000 de articole.
MIN_ARTICOLE_CURATARE = 500
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


def is_acceptable_lead_license(short_name: str) -> bool:
    """Public domain / CC0 sau CC BY / CC BY-SA (care se afiseaza cu credit)."""
    return is_public_domain(short_name) or render._is_credit_required_license(short_name)


def is_landscape(w: int, h: int) -> bool:
    return bool(w) and bool(h) and w >= h * LANDSCAPE_RATIO


def is_acceptable_format(w: int, h: int) -> bool:
    """Landscape clasic sau portret vertical / patrat decupabil curat (w/h >= 0.5, latime/inaltime >= 400)."""
    if not (w and h):
        return False
    if is_landscape(w, h):
        return True
    return w >= 400 and h >= 400 and (w / h) >= 0.5


def is_big_enough(w: int, h: int = 0) -> bool:
    """Coperta og e 1200x630; imaginea trebuie sa acopere dimensiunea fara interpolare excesiva."""
    return bool(w) and (w >= localities.MIN_WIDTH or (h >= localities.MIN_WIDTH and w >= 600))


def qualifies(info: dict) -> bool:
    """info = {width,height,license,...}. Poate deveni LEAD daca e
    destul de mare, are format decupabil curat SI licenta compatibila (PD/CC0 sau CC BY cu credit)."""
    return is_big_enough(info.get("width", 0), info.get("height", 0)) and \
        is_acceptable_format(info.get("width", 0), info.get("height", 0)) and \
        is_acceptable_lead_license(info.get("license", ""))


def crop_to(im, w: int, h: int, focus_y: float | None = None):
    """Redimensioneaza + incadreaza la exact w x h (fara deformare).
    Daca focus_y este specificat (0.0 .. 1.0), centrarea verticala se orienteaza
    in jurul punctului cerut, protejand capul si fata de decupare arbitrara.
    """
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    nw, nh = max(w, round(sw * scale)), max(h, round(sh * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    if focus_y is not None:
        target_y = round(nh * focus_y)
        top = target_y - h // 2
        top = max(0, min(top, nh - h))
    else:
        top = (nh - h) // 2
    return im.crop((left, top, left + w, top + h))


def _get_focus_y(name: str, info: dict) -> float | None:
    """Calculeaza punctul vertical de focalizare (0.0 .. 1.0) pentru incadrarea portretelor."""
    w, h = info.get("width", 0), info.get("height", 0)
    if is_landscape(w, h):
        return None
    try:
        with open(render.PORTRAITS_JSON, encoding="utf-8") as f:
            portret = json.load(f).get(fp.norm(name)) or {}
        poz = htmlart.incadrare_portrete().get(portret.get("img") or "", {}).get("poz") or ""
        return max(0.15, min(float(poz.split()[1].rstrip("%")) / 100.0, 0.45))
    except (OSError, ValueError, IndexError):
        return 0.28


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


def _save_renditions(data: bytes, slug: str, focus_y: float | None = None) -> dict | None:
    """Din rendite descarcata produce cover+art+webp incadrate. None daca invalida."""
    import io
    im = Image.open(io.BytesIO(data)).convert("RGB")
    cover = crop_to(im, COVER_W, COVER_H, focus_y=focus_y)
    art = crop_to(im, ART_W, ART_H, focus_y=focus_y)
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


def _qid_din_intrare(e: dict) -> str | None:
    """QID-ul localitatii unei intrari hit (campul `qid`, sau din numele fisierului `loc-Q…`)."""
    if e.get("qid"):
        return e["qid"]
    m = re.search(r"loc-(Q\d+)\.", e.get("art") or "")
    return m.group(1) if m else None


def index_localitati(cache: dict) -> dict:
    """`{qid: intrare hit}` din cache — fotografia unei localitati, refolosibila FARA retea.

    Cheia de fisier e deja QID-ul (`loc-Q….jpg`), deci 15 stiri de la aceeasi primarie aveau
    aceeasi poza, dar fiecare platea o interogare Commons si o descarcare din plafonul de 20.
    Masurat 2026-10-17: 212 articole actuale fara poza tin de 33 de localitati a caror poza
    exista deja in cache. Se refolosesc doar intrarile cu licenta inca acceptata."""
    idx = {}
    for e in cache.values():
        if not e or e.get("miss") or e.get("kind") != "locality":
            continue
        q = _qid_din_intrare(e)
        if q and localities.license_free(e.get("license", "")):
            idx.setdefault(q, e)
    return idx


def lead_for_locality(a: dict, by_name: dict, memo: dict | None = None):
    """(intrare, motiv) pentru fotografia LOCALITATII unei stiri venite de la primaria ei.

    Se incearca INAINTEA rutei pe entitati, fiindca e mult mai fiabila: cheia e slug-ul
    determinist al sursei (`pl_<judet>_<localitate>`), nu entitatile extrase din text.

    Garda Negativa Epistemica (Argon): stirile locale despre tragedii, accidente, decese
    sau fapte penale grave nu au voie sa poarte fotografia insorita a localitatii/primariei.
    Cititorul ar asocia cladirea/reperul cu scena accidentului sau fapta penala.

    Poarta de licenta e `localities.usable` (CC0/PD si CC BY/BY-SA, NC/ND respinse), nu
    `qualifies` (ruta pe entitati). Bariera stricta din 2026-08-19 (01d6107) exista fiindca atunci
    orice poza lead ajungea si pe carduri si in previzualizarea sociala, fara credit. Din
    2026-08-29 (ef398cd, #205) render-ul tine CC BY separat: doar pe pagina de articol, sub
    legenda completa, niciodata pe card sau in og:image. Bariera ramasese mai stricta decat
    tine politica (`content/legal/images.md`).

    NU trece prin `photojudge`: acela intreaba daca poza e o ilustratie EXACTA a subiectului,
    test potrivit pentru „poza persoanei X pe stirea despre X", dar gresit aici — poza de
    localitate e declarata ILUSTRATIE, nu document al evenimentului. Garantiile raman
    deterministe: localitatea corecta din judetul corect, licenta permisa si dimensiune.

    `memo` (`{qid: intrare | motiv}`) tine rezultatul per LOCALITATE in rulare: a doua stire
    din aceeasi localitate nu mai face nicio cerere de retea.
    """
    if localities.stire_tragica(a):
        return None, "loc_exclus_tematic"

    rec = localities.locality_for_article(a, by_name)
    if not rec:
        if not localities.eligible(a):
            return None, "loc_neeligibil"
        return None, "loc_negasit_sau_fara_imagine"
    memo = {} if memo is None else memo
    q = rec["qid"]
    if q in memo:
        hit = memo[q]
        if isinstance(hit, dict):
            return {**hit, "name": rec["display"]}, "loc_refolosit"
        return None, hit
    info = commons_lead_info(rec["img"])
    if not info or not info.get("thumb"):
        memo[q] = "loc_fara_info_commons"
        return None, memo[q]
    if not localities.usable(info):
        memo[q] = ("loc_licenta" if not localities.license_free(info.get("license", ""))
                   else "loc_dimensiune_sau_format")
        return None, memo[q]
    data = urllib.request.urlopen(
        urllib.request.Request(info["thumb"], headers=UA), timeout=30).read()
    if len(data) < 3000:
        return None, "loc_descarcare"
    # cheia de fisier e QID-ul, NU numele: 4 comune Costesti, 3 Ungheni, 2 Zarnesti si
    # 2 Faurei distincte au poze diferite si ar scrie toate in acelasi `loc-costesti.jpg`,
    # ultima descarcare suprascriind-o pe precedenta -> poza altui judet pe stirea locala.
    rend = _save_renditions(data, f"loc-{q}")
    if not rend:
        return None, "loc_descarcare"
    hit = {**rend, "artist": info["artist"], "license": info["license"],
           "page": info["page"], "name": rec["display"], "kind": "locality", "qid": q}
    memo[q] = hit
    return hit, "loc_ok"


# Etapele rutei pe entitati, in ordinea in care un candidat le parcurge. Un miss pastreaza
# etapa CEA MAI AVANSATA atinsa de vreun candidat: raportul spune unde se pierd pozele, nu
# doar ca s-au pierdut (pana in 2026-10-17 miss-ul era `{"miss": true, "v": 2}`, fara motiv).
_ETAPE_ENT = ("ent_fara_entitati", "ent_fara_qid", "ent_nenotabila", "ent_fara_p18",
              "ent_licenta_sau_format", "ent_respinsa_de_judecator", "ent_descarcare")


def lead_for_article(a: dict, provider=None):
    """(intrare, motiv): prima entitate a articolului cu P18 landscape + atribuire-libera care
    trece SI de judecatorul AI de potrivire (photojudge) -> intrare LEAD; altfel (None, motiv)."""
    summary = a.get("synthesis") or a.get("teaser") or ""
    etapa = 0
    # `etapa` se ridica INAINTE de fiecare poarta: numeste poarta la care s-a oprit candidatul,
    # nu ultima trecuta (constatare Gemini pe #492 — motivele erau decalate cu o pozitie).
    for name in a.get("entities") or []:
        if not name or len(name.split()) < 2:
            continue
        etapa = max(etapa, 1)
        qid = fp.wd_match(name)
        if not qid:
            continue
        etapa = max(etapa, 2)
        ent = fp.wd_entity(qid)
        claims = ent.get("claims", {})
        if not fp.is_photo_worthy(claims, len(ent.get("sitelinks", {}))):
            continue
        etapa = max(etapa, 3)
        f = fp.portrait_file(claims)
        if not f:
            continue
        etapa = max(etapa, 4)
        info = commons_lead_info(f)
        if not info or not info.get("thumb") or not qualifies(info):
            continue
        etapa = max(etapa, 5)
        # ultima poarta: AI verifica potrivirea foto<->articol (nu partea care a pierdut,
        # nu un rezultat fals). provider None -> True; eroare -> False (fail-safe).
        if not photojudge.photo_fits(provider, a.get("title", ""), summary, name, _caption(f)):
            continue
        etapa = max(etapa, 6)
        data = urllib.request.urlopen(urllib.request.Request(info["thumb"], headers=UA), timeout=30).read()
        if len(data) < 3000:
            continue
        slug = fp.slugish(name)
        focus_y = _get_focus_y(name, info)
        rend = _save_renditions(data, slug, focus_y=focus_y)
        if not rend:
            continue
        return {**rend, "artist": info["artist"], "license": info["license"],
                "page": info["page"], "name": name, "kind": "entity"}, "ent_ok"
    return None, _ETAPE_ENT[etapa]


def curata_cache(cache: dict, aids_actuale: set) -> int:
    """Scoate intrarile articolelor care nu mai exista. Intoarce cate a scos.

    Masurat 2026-10-17: 11.793 din cele 12.833 de intrari erau pentru articole expirate.
    RAMAN hit-urile de LOCALITATE, chiar daca articolul lor a expirat: ele sunt memoria per
    QID (`index_localitati`) — urmatoarea stire de la aceeasi primarie isi ia poza din ele,
    fara retea. Sunt cateva sute, nu mii. Fisierele din media/ nu se ating aici."""
    moarte = [k for k, v in cache.items()
              if k not in aids_actuale and not (v and not v.get("miss") and v.get("kind") == "locality")]
    for k in moarte:
        del cache[k]
    return len(moarte)


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
    memo = index_localitati(cache)
    print(f">> localitati cu poza deja in cache: {len(memo)}")
    done = refolosite = 0
    motive: dict = {}
    # Prioritizare pe categorii (Argon): articolul #1 (cel mai recent) din fiecare
    # categorie primeste prioritate de interogare (0), creand cate o ancora vizuala pe
    # fiecare rubrica a primei pagini. Urmeaza restul stirilor locale (1), apoi fluxul general (2).
    seen_cats = set()
    first_in_cat = set()
    for a in arts:
        cat = a.get("category")
        if cat and cat not in seen_cats:
            seen_cats.add(cat)
            first_in_cat.add(htmlart.art_id(a))

    def _prioritate_articol(x: dict) -> int:
        aid = htmlart.art_id(x)
        if aid in first_in_cat:
            return 0
        if localities.eligible(x):
            return 1
        return 2

    for a in sorted(arts, key=_prioritate_articol):
        aid = htmlart.art_id(a)
        if not _needs_lookup(aid, a, cache):
            continue
        # Localitatea cu poza deja cunoscuta se rezolva FARA retea, deci fara plafon
        # (cu conditia sa nu fie o stire de tragedie/accident -- Garda Negativa Argon).
        rec = localities.locality_for_article(a, by_name)
        if rec and isinstance(memo.get(rec["qid"]), dict) and not localities.stire_tragica(a):
            cache[aid] = {**memo[rec["qid"]], "name": rec["display"]}
            refolosite += 1
            continue
        if done >= MAX_LOOKUPS:
            continue
        done += 1
        try:
            # intai localitatea (determinista, acoperire mare), apoi entitatile din text
            entry, m_loc = lead_for_locality(a, by_name, memo)
            m_ent = None
            if not entry:
                entry, m_ent = lead_for_article(a, provider)
        except Exception as exc:  # o entitate/retea esuata nu opreste restul
            print(f"  ! {aid}: {exc}")
            done -= 1              # eroare de retea -> nu consuma plafonul
            continue
        if entry:
            cache[aid] = entry
        else:
            cache[aid] = {"miss": True, "v": MISS_VERSION, "motiv_loc": m_loc, "motiv_ent": m_ent}
            for m in (m_loc, m_ent):
                motive[m] = motive.get(m, 0) + 1
        print(f"  {'ok  ' if entry else 'miss'} {aid} "
              f"{entry['name'] + ' [' + entry.get('kind', 'entity') + ']' if entry else m_loc + ' / ' + str(m_ent)}")
        time.sleep(1)             # politete API
    if len(arts) >= MIN_ARTICOLE_CURATARE:
        scoase = curata_cache(cache, {htmlart.art_id(a) for a in arts})
        print(f">> cache curatat: {scoase} intrari ale articolelor expirate")
    if motive:
        print(">> motivele miss-urilor din rularea asta: "
              + ", ".join(f"{k}={v}" for k, v in sorted(motive.items(), key=lambda kv: -kv[1])))
    # scriem doar hit-urile in fisierul consumat de render (miss-urile raman doar in memorie/cache-disk)
    hits = {k: v for k, v in cache.items() if not (v or {}).get("miss")}
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f">> leadphotos: {done} interogari noi, {refolosite} refolosite fara retea, "
          f"{len(hits)} lead-uri, {len(cache)} intrari cache")
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
    sys.exit(main())
