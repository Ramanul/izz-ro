"""Rezolvarea LOCALITATII unei stiri locale -> intrarea Wikidata a acelei localitati.

De ce exista: fotografia principala a unui articol local se alegea dupa entitatile-PERSOANA
din text (P18 al primarului). Portretele sunt verticale si aproape mereu CC-BY, iar poarta
cerea simultan landscape SI PD/CC0 -> intersectie vida (0 hit-uri din 1684 incercari).
Localitatea e alegerea corecta: are poza peisaj (panorama, centru, cladire), e mereu
relevanta pentru o stire a primariei, si nu depinde de calitatea extractiei de entitati.

Cheia de rezolvare e slug-ul SURSEI (`pl_<judet>_<localitate>`), nu textul articolului:
e determinist, construit de `local_sources._make_slug`, deci reversibil fara ghicit.

Modul PUR: zero retea, zero I/O in afara de `load_dataset`. Datasetul (`data/localities.json`)
e construit rar de `tools/fetch_localities.py` si comis in repo, ca build-ul sa nu depinda
de disponibilitatea Wikidata.
"""
import json
import os
import re

from .util import strip_diacritics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(ROOT, "data", "localities.json")

# Latimea minima a sursei: coperta og e 1200x630. Sub 1200 px imaginea ar fi marita,
# iar "Zero Zgomot" (sect. 7) exclude publicarea unei poze vizibil interpolate.
# Fara acest prag, o poza de 450x338 trece de raportul landscape si ajunge pe site.
MIN_WIDTH = 1200
LANDSCAPE_RATIO = 1.2

# Licente acceptate. CC-BY / CC-BY-SA cer atribuire, care se face pe PAGINA DE ARTICOL
# (`figcaption.art-credit`); CC 4.0 §3(a)(2) si CC 3.0 §4(c) permit indeplinirea obligatiei
# printr-un link catre resursa cu informatiile, iar cardul linkuieste articolul -> cardurile
# raman fara element de credit si formula de atribuire din sect. 7 ramane neatinsa.
# Orice licenta necunoscuta, GPL sau "fair use" -> respinsa (fail-safe).
#
# `cc[ -]?by` TREBUIE sa refuze explicit NC si ND, altfel "CC BY-NC 4.0" si "CC BY-ND 4.0"
# trec ca libere (masurat: treceau). NC interzice folosirea comerciala, ND interzice
# operele derivate -- iar noi DECUPAM fiecare imagine, deci producem un derivat.
_FREE_LICENSE = re.compile(
    r"^(cc0|cc[ -]?zero|public domain|pd([ -]|$)|copyrighted free use|"
    r"cc[ -]?by(?![ -]?n[cd]))", re.I)

# Prefixele administrative din CSV-ul de primarii, eliminate pe CUVANT INTREG.
# `ORA[SS](UL)?` si nu `ORA[SS]UL?`: forma majoritara in CSV e "ORAS X" fara -UL, iar
# varianta gresita lasa "Oras" lipit de nume si rateaza fiecare oras (bug masurat: 64/120).
_PREFIX = re.compile(r"^(MUNICIPIUL?|ORA[SȘ](UL)?|COMUNA)\b\s*", re.I)

_SOURCE_PREFIX = "pl_"

# Categoriile in care o fotografie a localitatii sursei e o ilustratie onesta.
_GEO_CATEGORIES = frozenset({"local", "zonal"})

# Singurele judete al caror nume are doua cuvinte. Multime INCHISA (cele 41 de judete +
# Bucuresti sunt fixe), deci se poate enumera in loc sa se ghiceasca punctul de taiere:
# fara ea, `prahova_valea_calugareasca` s-ar rupe in judetul "prahova valea".
_MULTI_WORD_JUDET = frozenset({"bistrita nasaud", "caras severin", "satu mare"})


def norm(s: str) -> str:
    """Cheie de potrivire: fara diacritice, lowercase, separatorii colapsati la spatiu."""
    return re.sub(r"[^a-z0-9]+", " ", strip_diacritics(s or "").lower()).strip()


def parse_source_slug(slug: str) -> tuple[str, str] | None:
    """`pl_vrancea_municipiul_focsani` -> ('vrancea', 'focsani'). None daca nu e sursa de primarie.

    Judetele compuse ('bistrita-nasaud', 'caras-severin') devin 'bistrita_nasaud' in slug,
    deci judetul NU se poate separa dupa primul '_'. Doua reguli deterministe, in ordine:
    (1) prefixul administrativ ('municipiul'/'oras'/'comuna') marcheaza exact granita;
    (2) fara prefix (comunele), se taie dupa doua cuvinte doar daca acelea formeaza unul
        dintre cele trei judete cu nume compus, altfel dupa unul singur.
    """
    if not slug or not slug.startswith(_SOURCE_PREFIX):
        return None
    rest = slug[len(_SOURCE_PREFIX):]
    parts = [p for p in rest.split("_") if p]
    if len(parts) < 2:
        return None
    # prefixul administrativ marcheaza inceputul localitatii, cand e prezent
    for i, p in enumerate(parts):
        if _PREFIX.match(p + " ") and i >= 1:
            judet = " ".join(parts[:i])
            name = " ".join(parts[i + 1:])
            if name:
                return judet, name
    # comuna: fara prefix -> judetul e primul token, sau primele doua daca e judet compus
    cut = 2 if (len(parts) > 2 and " ".join(parts[:2]) in _MULTI_WORD_JUDET) else 1
    if len(parts) <= cut:
        return None
    return " ".join(parts[:cut]), " ".join(parts[cut:])


def load_dataset(path: str = DATASET) -> dict:
    """Datasetul comis: {nume_normalizat: [inregistrari]}. {} daca lipseste (fail-safe)."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError):
        return {}
    return data.get("by_name", {}) if isinstance(data, dict) else {}


def match(judet: str, name: str, by_name: dict) -> dict | None:
    """Inregistrarea localitatii din JUDETUL cerut. None daca nu exista acolo.

    Potrivirea de judet e OBLIGATORIE si fara fallback: masurat pe cele 120 de primarii
    GOLD, 12 nume au omonime in alte judete (Zarnesti/Brasov vs Zarnesti/Buzau). Un
    fallback pe "primul candidat cu poza" ar pune fotografia altui oras pe o stire locala,
    exact tipul de eroare pe care sect. 7 il interzice.
    """
    cands = by_name.get(norm(name)) or []
    jf = norm(judet)
    if not jf:
        return None
    hits = [c for c in cands if _judet_matches(jf, norm(c.get("judet", "")))]
    if not hits:
        return None
    # doua localitati cu acelasi nume in ACELASI judet (comuna + satul resedinta):
    # castiga cea cu poza, apoi cea mai populata
    hits.sort(key=lambda c: (bool(c.get("img")), c.get("pop") or 0), reverse=True)
    return hits[0]


def _judet_matches(jf: str, wd_judet: str) -> bool:
    """Judetul din CSV ('VRANCEA') vs eticheta Wikidata ('Județul Vrancea')."""
    if not jf or not wd_judet:
        return False
    wd = re.sub(r"^judetul\s+", "", wd_judet)
    return wd == jf or jf == wd_judet or wd.startswith(jf) or jf.startswith(wd)


def license_free(short_name: str) -> bool:
    """Licenta permite reutilizarea comerciala cu cel mult obligatia de atribuire?"""
    return bool(_FREE_LICENSE.match((short_name or "").strip()))


def usable(info: dict | None) -> bool:
    """Imaginea Commons poate deveni fotografie principala?

    Trei conditii, toate necesare: destul de mare pentru coperta og, clar peisaj (nu se
    taie un portret vertical), si licenta libera. Orice camp lipsa -> False.
    """
    if not info:
        return False
    w, h = info.get("width") or 0, info.get("height") or 0
    return bool(w >= MIN_WIDTH and h and w >= h * LANDSCAPE_RATIO
                and license_free(info.get("license", "")))


def eligible(a: dict) -> tuple[str, str] | None:
    """(judet, localitate) daca articolul poate primi o fotografie de localitate, altfel None.

    Predicat UNIC, ca poarta sa fie aceeasi si la alegerea fotografiei, si la decizia de
    a reinterogha un `miss` vechi -- doua conditii scrise in doua locuri diverg tacut.
    """
    if a.get("category") not in _GEO_CATEGORIES:
        return None
    return parse_source_slug(a.get("source") or "")


def locality_for_article(a: dict, by_name: dict) -> dict | None:
    """Inregistrarea localitatii unui articol local, sau None daca ruta nu se aplica.

    Doua conditii, amandoua necesare: sursa e o primarie (`source` = `pl_*`) SI articolul
    e clasificat `local`/`zonal`. Sursa singura nu ajunge: poarta geografica decide unde
    se INTAMPLA stirea, nu cine o publica, deci o primarie care scrie despre un subiect
    national ajunge in alta categorie -- si acolo poza localitatii ar fi o ilustratie
    arbitrara. Azi toate cele 204 articole `pl_*` sunt `local`, deci conditia nu taie
    nimic; e acolo ca sa nu se strecoare cand se schimba poarta.
    """
    parsed = eligible(a)
    if not parsed:
        return None
    judet, name = parsed
    rec = match(judet, name, by_name)
    if not rec or not rec.get("img"):
        return None
    return {**rec, "display": rec.get("label") or name.title()}
