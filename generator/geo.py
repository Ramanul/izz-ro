"""Poarta geografica DETERMINISTA: decide `regional` / `zonal` / `local` din textul stirii.

De ce exista: prompturile trimit AI-ului rubricile geografice ca etichete goale
(`regional|zonal|local`), la gramada cu `sport` si `auto`, fara nicio definitie. Modelul
n-are de unde sti ca Transilvania e regiune iar Vrancea e judet, deci ghiceste — masurat
2026-07-25: 14 din 15 articole din `regional` erau gresite (un sat elvetian, Comisia
Europeana, DNA), si 30 de articole intrasera pe axa geografica de la surse fara nicio
legatura cu geografia.

Regula proprietarului (2026-08-01):
  regiune istorica -> regional · judet -> zonal · municipiu/oras/comuna/sat -> local
  Mai multe nume in text  -> castiga cel mai SPECIFIC.
  Niciun nume de loc      -> articolul NU intra pe axa geografica; ramane pe tema.

Sursa datelor: `data/raport_complet_primarii.csv` (coloanele Judet, Localitate) — 3187 de
randuri, 42 de judete, deja in repo. Regiunile istorice sunt singura parte scrisa de mana.
"""
import csv
import os
import re

from . import config
from .util import strip_diacritics

_CSV = os.path.join(config.ROOT, "data", "raport_complet_primarii.csv")

# Regiunile istorice, aproximate la nivel de JUDET. Aproximarea e reala si asumata:
# granitele istorice taie judetele de azi (Aradul e impartit intre Crisana si Banat,
# Suceava intre Bucovina si Moldova, Mehedintiul intre Oltenia si Banat). Maparea serveste
# gruparea editoriala, nu rigoarea istorica; un articol ajunge pe `regional` doar cand
# numeste EL INSUSI regiunea, nu prin deducere din judet.
REGIUNI = {
    "TRANSILVANIA": ["ALBA", "BISTRITA-NASAUD", "BRASOV", "CLUJ", "COVASNA", "HARGHITA",
                     "HUNEDOARA", "MURES", "SALAJ", "SIBIU"],
    "BANAT": ["TIMIS", "CARAS-SEVERIN"],
    "CRISANA": ["BIHOR", "ARAD"],
    "MARAMURES": ["MARAMURES", "SATU MARE"],
    "BUCOVINA": ["SUCEAVA"],
    "MOLDOVA": ["BACAU", "BOTOSANI", "GALATI", "IASI", "NEAMT", "VASLUI", "VRANCEA"],
    "MUNTENIA": ["ARGES", "BRAILA", "BUZAU", "CALARASI", "DAMBOVITA", "GIURGIU", "IALOMITA",
                 "ILFOV", "PRAHOVA", "TELEORMAN", "BUCURESTI"],
    "OLTENIA": ["DOLJ", "GORJ", "MEHEDINTI", "OLT", "VALCEA"],
    "DOBROGEA": ["CONSTANTA", "TULCEA"],
}

# Sinonime uzuale in presa pentru regiuni.
_ALIAS_REGIUNI = {
    "ARDEAL": "TRANSILVANIA",
    "BARAGAN": "MUNTENIA",
    "TARA BARSEI": "TRANSILVANIA",
    "TINUTUL SECUIESC": "TRANSILVANIA",
}

# Prefixe de tip din CSV: "MUNICIPIUL ALBA IULIA" -> "ALBA IULIA". Comunele n-au prefix.
_PREFIXE = ("MUNICIPIUL ", "ORASUL ", "ORAS ", "COMUNA ")

# Nume de localitati care sunt si cuvinte comune in romana sau engleza. Fara ele, "Valea"
# dintr-o propozitie oarecare sau "spring" dintr-un citat englezesc ar clasifica stirea ca
# `local`. Lista e derivata empiric din corpus (vezi tests/test_geo.py), nu ghicita: sunt
# exact numele care produceau potriviri false pe articole reale.
_CUVINTE_COMUNE = {
    "VALEA", "LUNCA", "POIANA", "UNIREA", "CETATEA", "LIVEZILE", "SPRING", "VIDRA",
    "DUMBRAVA", "PADURENI", "GURA", "VARFURILE", "PROGRESUL", "VICTORIA", "INDEPENDENTA",
    "LIBERTATEA", "BUCIUM", "LIVADA", "PLOPU", "MOVILA", "CRUCEA", "GRADINA", "COTU",
    "BALTA", "CIRESU", "FRASIN", "MAGURA", "PERISORU", "RACHITA", "SALCIA", "STEJARU",
    "VULTURU", "ZORILE", "CENTRUL", "PIATRA", "DEALU", "PODU", "VADU", "IZVOARE",
}

_INDEX = None


def _adauga(index: dict, nume: str, nivel: str) -> None:
    """Cel mai specific nivel castiga la coliziune: Cluj e si judet, Cluj-Napoca e oras."""
    nume = nume.strip()
    # Judetele scurte ne trebuie (Olt are 3 litere). Localitatile scurte NU: exista comune
    # numite Leu, Apa, Pui, Rus — un curs valutar ("leu-euro") sau o stire despre Rusia ar
    # deveni stire locala. Comunele minuscule pierdute asa costa mult mai putin.
    minim = 3 if nivel in ("zonal", "regional") else 4
    if len(nume) < minim or nume in _CUVINTE_COMUNE:
        return
    ordine = {"local": 3, "zonal": 2, "regional": 1}
    if ordine[nivel] > ordine.get(index.get(nume), 0):
        index[nume] = nivel


def _construieste() -> dict:
    """{NUME_NORMALIZAT: nivel}. Construit o data, la prima clasificare."""
    index = {}
    for regiune in REGIUNI:
        _adauga(index, regiune, "regional")
    for alias in _ALIAS_REGIUNI:
        _adauga(index, alias, "regional")

    try:
        with open(_CSV, encoding="utf-8-sig") as fh:
            for rand in csv.DictReader(fh):
                judet = strip_diacritics((rand.get("Județ") or "").strip()).upper()
                if judet:
                    _adauga(index, judet, "zonal")
                loc = strip_diacritics((rand.get("Localitate") or "").strip()).upper()
                for pref in _PREFIXE:
                    if loc.startswith(pref):
                        loc = loc[len(pref):]
                        break
                if loc:
                    _adauga(index, loc, "local")
    except OSError:
        # Fara gazetteer nu inventam o clasificare; clasificarea va returna None si
        # articolul ramane pe axa de tema, care e exact comportamentul sigur.
        return index
    return index


def _index() -> dict:
    global _INDEX
    if _INDEX is None:
        _INDEX = _construieste()
    return _INDEX


_ORDINE = {"local": 3, "zonal": 2, "regional": 1}

# Calificativul administrativ din text bate indexul: "judetul Tulcea" e judet, chiar daca
# Tulcea e si municipiu. Fara asta, orice resedinta de judet ar trage stirea pe `local`.
# Formele flexionate conteaza: "in nordul judetULUI Tulcea" e la fel de frecvent in presa
# ca "in judetul Tulcea", si fara genitiv calificativul se rata -> stirea cadea pe `local`
# pentru ca Tulcea e si municipiu. Alternantele lungi primele, ca sa castige.
_CALIFICATIV = re.compile(
    r"(JUDETULUI|JUDETELE|JUDETUL|JUDETE|JUDET|JUD\.|"
    r"MUNICIPIULUI|MUNICIPIUL|ORASULUI|ORASUL|COMUNEI|COMUNA|SATULUI|SATUL)\s*$")
_NIVEL_CALIFICATIV = {
    "JUDETULUI": "zonal", "JUDETELE": "zonal", "JUDETUL": "zonal", "JUDETE": "zonal",
    "JUDET": "zonal", "JUD.": "zonal",
    "MUNICIPIULUI": "local", "MUNICIPIUL": "local", "ORASULUI": "local", "ORASUL": "local",
    "COMUNEI": "local", "COMUNA": "local", "SATULUI": "local", "SATUL": "local",
}

# Articolul hotarat lipit de nume: Cluj -> Clujul, Brasov -> Brasovului. Fara asta,
# "a vizitat Clujul" nu s-ar potrivi deloc.
_ARTICOL = r"(?:ULUI|UL|UI)?"

_REGEX = None


def _regex():
    """O singura alternanta, cu numele lungi primele: castiga potrivirea cea mai lunga,
    deci `CLUJ-NAPOCA` inaintea lui `CLUJ`."""
    global _REGEX
    if _REGEX is None:
        nume = sorted(_index(), key=len, reverse=True)
        if not nume:
            return None
        _REGEX = re.compile(r"\b(" + "|".join(re.escape(n) for n in nume) + r")" +
                            _ARTICOL + r"\b")
    return _REGEX


def clasifica(text: str) -> str | None:
    """Rubrica geografica a textului, sau None daca nu contine niciun nume de loc.

    None NU inseamna esec: inseamna ca articolul nu apartine axei geografice si ramane pe
    tema lui. Asta e regula proprietarului si e cea care opreste scurgerile.
    """
    if not text:
        return None
    rx = _regex()
    if rx is None:
        return None

    # Potrivim pe textul FARA diacritice si cu majuscule, dar cerem ca aparitia din textul
    # ORIGINAL sa inceapa cu majuscula: in romana numele proprii sunt capitalizate, iar
    # cerinta asta taie potrivirile accidentale pe cuvinte comune.
    original = strip_diacritics(text)
    plat = original.upper()
    index = _index()

    gasit = None
    for m in rx.finditer(plat):
        if not original[m.start():m.start() + 1].isupper():
            continue
        nivel = index[m.group(1)]
        calif = _CALIFICATIV.search(plat[max(0, m.start() - 12):m.start()])
        if calif:
            nivel = _NIVEL_CALIFICATIV[calif.group(1)]
        if gasit is None or _ORDINE[nivel] > _ORDINE[gasit]:
            gasit = nivel
            if gasit == "local":
                break        # nu exista nivel mai specific
    return gasit
