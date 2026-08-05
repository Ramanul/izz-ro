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
import json
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

# Gruparea de AFISARE (owner, 2026-08-02): pe /surse/ vrem 7 regiuni, nu 9 — Crisana si
# Maramuresul intra la Transilvania. E o decizie EDITORIALA de prezentare si sta separat
# INTENTIONAT: `REGIUNI` de mai sus alimenteaza clasificarea articolelor, iar comasarea
# acolo ar schimba ce ajunge pe `regional`. Listele de judete nu se dubleaza — se derive.
_COMASARI_AFISARE = {"CRISANA": "TRANSILVANIA", "MARAMURES": "TRANSILVANIA"}

ORDINE_REGIUNI_AFISARE = ("TRANSILVANIA", "BANAT", "BUCOVINA", "MOLDOVA",
                          "MUNTENIA", "OLTENIA", "DOBROGEA")

ETICHETE_REGIUNI = {
    "TRANSILVANIA": "Transilvania", "BANAT": "Banat", "BUCOVINA": "Bucovina",
    "MOLDOVA": "Moldova", "MUNTENIA": "Muntenia", "OLTENIA": "Oltenia",
    "DOBROGEA": "Dobrogea",
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

# Nume care sunt SI localitate reala, SI altceva foarte frecvent: o zi, o luna, un prenume,
# un nume de familie, o institutie. Nu pot intra in `_CUVINTE_COMUNE` — Romanul e municipiu
# cu primarie care publica pe izz.ro, Voluntari e oras de 40.000 — deci nu se sterg din
# index, ci li se cere o MARCA geografica in text (vezi `_MARCA_GEO`). Fara ea nu conteaza.
#
# Lista e MASURATA pe corpus (1733 de articole, 2026-08-03), nu ghicita: fiecare nume de aici
# a produs cel putin o clasificare gresita, si sunt notate exact bucatile care le-au produs.
# Se extinde la fel — prin masuratoare, nu prin intuitie; multe par inofensive pana le vezi
# in text („Luna august", „INSCRIERI SAMBATA", „Aeroportul Avram Iancu").
_AMBIGUE = {
    "LUNA",          # „Luna august 2026" — comuna in Cluj, 17 potriviri gresite
    "SAMBATA",       # „INSCRIERI -SAMBATA 22.08" — comuna in Brasov
    "ROMAN",         # „Festivalul Roman Apulum", „Oana Roman", „Institutul Cultural Roman"
    "BALA",          # „bratului Bala" — comuna in Mehedinti
    "BANCA",         # „Banca Centrala Europeana" — comuna in Vaslui
    "CURTEA",        # „Curtea de Apel", „Curtea de Casatie din Franta"
    "VOLUNTARI",     # „programul Voluntari Pregatiti pentru Viata" — oras in Ilfov
    "TRAIAN",        # „Traian Basescu", „Piata Traian"
    "VLADIMIR",      # „Vladimir Putin" — comuna in Gorj
    "OVIDIU",        # „Ovidiu Bojor" — oras in Constanta
    "CRISTIAN",      # „Cristian Iliescu" — comune in Brasov si Sibiu
    "BACIU",         # „antrenorul Marius Baciu" — comuna in Cluj
    "DRAGUS",        # „Denis Dragus", fotbalistul — comuna in Brasov
    "CIOBANU",       # „Adrian Ciobanu" — comuna in Constanta
    "FLORICA",       # „Florica Bertzi" — comuna in Dambovita
    "CATALINA",      # prenume — comune in Cluj, Covasna, Maramures
    "MAIA",          # „Maia Morgenstern" — comuna in Ialomita
    "AVRAM IANCU",   # „Aeroportul International Avram Iancu", nume de strada
    "GEORGE ENESCU", # „Filarmonica George Enescu" — comuna in Botosani
    "MIHAI BRAVU",   # nume de strada in mai multe orase
    "GRADINARI",     # aparea intr-o insiruire de strazi
}

_INDEX = None

# Satele, atarnate de judet. NU intra in indexul global de mai sus si nu pot: numele lor se
# repeta intre judete (POIANA x38, "SATU NOU" x42), iar masurat pe corpus adaugarea chiar si
# a celor unice a facut 49 de articole `local` gresit — „Saturn retrograd" (Saturn e sat in
# Constanta), horoscopul, „FCSB vs FK Auda". Un nume unic poate fi tot un cuvant obisnuit.
# Aici se folosesc DOAR cand se stie judetul sursei; atunci „Poiana" dintr-un ziar de Vrancea
# e Poiana din Vrancea, iar sursele nationale — de la care veneau toate falsurile — n-au judet,
# deci pentru ele poarta asta nu se deschide niciodata.
_SATE_CSV = os.path.join(config.ROOT, "data", "sate_judet.csv")
_SATE: dict | None = None
_REGEX_SATE: dict = {}


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

# Marca geografica ceruta numelor din `_AMBIGUE`: ori calificativul administrativ de mai sus,
# ori o prepozitie locativa. Masurat pe corpus, prepozitiile sunt indispensabile — „la Roman"
# si „din Roman" sunt de departe forma obisnuita in presa, iar „municipiul Roman" e rara.
# Atentie ca asta NU e o gramatica: „a ajuns la Vladimir Putin" trece. E un filtru ieftin
# calibrat pe ce produce greseli real, nu un analizor de limba.
_MARCA_GEO = re.compile(
    r"(JUDETULUI|JUDETELE|JUDETUL|JUDETE|JUDET|JUD\.|MUNICIPIULUI|MUNICIPIUL|ORASULUI|"
    r"ORASUL|COMUNEI|COMUNA|SATULUI|SATUL|LOCALITATEA|LOCALITATII|"
    r"\bLA|\bDIN|\bIN|\bSPRE|\bCATRE|\bLANGA)\s+$")

# Numele regiunilor istorice sunt SI nume comerciale sau de institutii („Banca Transilvania",
# „Universitatea Transilvania", „Autostrada A3 Transilvania"), SI numele unui stat vecin
# („Republica Moldova"). Masurat pe corpus (1714 articole): din 31 de potriviri de nume de
# regiune, 24 sunt NEgeografice, iar 13 dintre ele sunt Republica/Republicii Moldova.
#
# Mecanismul `_AMBIGUE` de mai sus NU se poate refolosi aici, si asta e masurat, nu presupus:
# cerandu-le o marca geografica se pierde un articol corect („magistralele care conecteaza
# Capitala DE Moldova" — `de` nu e prepozitie locativa) si cade „in REGIUNEA Banatului",
# fiindca REGIUNEA nu e in `_MARCA_GEO`. Regiunile apar legitim fara prepozitie: „Transilvania
# a fost lovita de furtuna".
#
# Discriminatorul ales dintre sase variante comparate pe tot corpusul: un cuvant cu MAJUSCULA
# lipit inaintea numelui (doar spatii intre ele, fara punctuatie). Repara 7 din 9 articole
# `regional` gresite si nu pierde niciunul corect; la nivel de aparitie respinge 23, toate 23
# negeografice. Varianta cu exceptie la inceput de fraza a fost respinsa tot pe cifre: strica
# exact cazul-samanta, „Banca Transilvania ofera..." fiind la pozitia 0.
#
# Whitelist-ul e substantivele geo-relationale care preced legitim o regiune. Pe corpusul de
# azi niciunul nu apare, deci nu schimba nicio clasificare — exista pentru „Toata Oltenia se
# afla sub cod rosu" si „Regiunea Banatului a inregistrat...", verificate pe sonde sintetice.
_GEO_RELATIONAL = {
    "NORDUL", "SUDUL", "ESTUL", "VESTUL", "CENTRUL",
    "REGIUNEA", "ZONA", "TOATA", "INTREAGA", "PROVINCIA",
}
# Fereastra de 32 de caractere e generoasa fata de cel mai lung cuvant plauzibil
# („Inspectoratul", 13): daca ar taia cuvantul, prima litera ar parea mica si garda ar rata.
# Cifrele sunt in clasa intentionat: „Autostrada A3 Transilvania" — fara ele bucata dinainte
# se termina in „3 ", nu se potriveste nimic, si numele comercial ar trece drept geografie.
# Un token pur numeric nu declanseaza nimic, fiindca „2026"[:1].isupper() e False.
_CUVANT_INAINTE = re.compile(r"([A-Za-z0-9]+) +$")

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


def _sate() -> dict:
    """{JUDET: (nume,)}, din `data/sate_judet.csv` (generat de tools/build_gazetteer.py)."""
    global _SATE
    if _SATE is None:
        _SATE = {}
        try:
            with open(_SATE_CSV, encoding="utf-8") as fh:
                for rand in csv.DictReader(fh):
                    judet = (rand.get("judet") or "").strip()
                    nume = (rand.get("nume") or "").strip()
                    if judet and nume:
                        _SATE.setdefault(judet, []).append(nume)
        except OSError:
            pass          # fara fisier, poarta satelor pur si simplu nu se deschide
    return _SATE


def _regex_sate(judet: str):
    """Alternanta satelor unui singur judet, compilata o data. Numele lungi primele, ca la
    indexul global: altfel „SATU NOU" ar fi taiat de „SATU"."""
    if judet not in _REGEX_SATE:
        nume = _sate().get(judet) or []
        _REGEX_SATE[judet] = re.compile(
            r"\b(" + "|".join(re.escape(n) for n in sorted(nume, key=len, reverse=True)) +
            r")" + _ARTICOL + r"\b") if nume else None
    return _REGEX_SATE[judet]


def judet_sursa(cheie: str | None) -> str | None:
    """Judetul unei surse: campul `judet` din config daca exista, altfel dedus din cheie.

    Primariile si consiliile judetene isi codeaza judetul in cheie (`pl_cluj_...`), ziarele
    judetene nu — `zcj` nu spune nimanui ca e Cluj — deci alea il declara in `config.SOURCES`.
    """
    if not cheie:
        return None
    declarat = (config.SOURCES.get(cheie) or {}).get("judet")
    if declarat:
        return strip_diacritics(declarat).upper()
    return judet_din_cheie(cheie)


def _ambiguu_fara_marca(m, plat: str) -> bool:
    """Potrivirea e pe un nume din `_AMBIGUE` si textul nu-l marcheaza ca loc -> se ignora.

    Fereastra de 16 caractere acopera cel mai lung marker („LOCALITATII " are 12). Numele
    NEambigue nu platesc nimic: pentru ele functia iese la prima verificare.
    """
    return (m.group(1) in _AMBIGUE
            and not _MARCA_GEO.search(plat[max(0, m.start() - 16):m.start()]))


def _regiune_ca_nume_propriu(m, original: str, plat: str) -> bool:
    """Numele de regiune e a doua bucata dintr-un nume propriu compus -> nu e geografie.

    Se cheama DOAR pentru potriviri de nivel `regional` (12 nume), deci restul indexului nu
    plateste nimic. Cazul-samanta: „Banca Transilvania". Cel dominant: „Republica Moldova".
    """
    inainte = _CUVANT_INAINTE.search(original[max(0, m.start() - 32):m.start()])
    if not inainte:
        return False              # inceput de text, sau punctuatie intre cuvinte
    cuvant = inainte.group(1)
    if not cuvant[:1].isupper() or cuvant.upper() in _GEO_RELATIONAL:
        return False
    # O prepozitie locativa cu majuscula la inceput de fraza — „In Ardeal s-au inregistrat..."
    # — arata exact ca un nume propriu compus pentru regula de mai sus. `_MARCA_GEO` o
    # recunoaste deja; refolosita aici, nu duplicata, ca sa nu se desparta cele doua liste.
    # Prins de un test care exista dinainte, nu de corpus: forma e rara in titluri si teasere.
    return not _MARCA_GEO.search(plat[max(0, m.start() - 16):m.start()])


def regiune_din_text(text: str) -> str | None:
    """Numele regiunii pe care textul o NUMESTE, cu diacritice — sau None.

    De ce exista separat de `clasifica`: aceea intoarce doar NIVELUL (`regional`), deci numele
    regiunii potrivite se pierde, iar coperta ajungea sa scrie „REGIONAL" — o eticheta care nu
    spune cititorului nimic. Regiunea nu se salveaza in `articles.json` (verificat 2026-08-05:
    cheile unui articol sunt category/entities/.../title/url, niciuna geografica), deci se
    recalculeaza aici din text.

    NU modifica `clasifica`: aceea e poarta calibrata care a redus 14 din 15 clasificari gresite
    (vezi antetul fisierului), are semnatura folosita in tot pipeline-ul si teste peste ea.
    Functia asta doar CITESTE acelasi index si aceleasi garzi, deci nu poate muta niciun articol
    dintr-o rubrica in alta.

    Comaseaza la cele 7 regiuni de AFISARE (Crisana si Maramures -> Transilvania), ca eticheta
    de pe coperta sa fie consecventa cu gruparea de pe /surse/ (decizie de proprietar 2026-08-02).
    """
    if not text:
        return None
    rx = _regex()
    if rx is None:
        return None
    index = _index()
    plat = strip_diacritics(text).upper()
    original = text
    for m in rx.finditer(plat):
        nume = m.group(1)
        if index.get(nume) != "regional":
            continue
        if not original[m.start():m.start() + 1].isupper():
            continue
        if _regiune_ca_nume_propriu(m, original, plat):
            continue          # „Banca Transilvania", „Republica Moldova"
        cheie = _ALIAS_REGIUNI.get(nume, nume)
        cheie = _COMASARI_AFISARE.get(cheie, cheie)
        eticheta = ETICHETE_REGIUNI.get(cheie)
        if eticheta:
            return eticheta
    return None


def clasifica(text: str, judet: str | None = None) -> str | None:
    """Rubrica geografica a textului, sau None daca nu contine niciun nume de loc.

    None NU inseamna esec: inseamna ca articolul nu apartine axei geografice si ramane pe
    tema lui. Asta e regula proprietarului si e cea care opreste scurgerile.

    `judet` e judetul SURSEI, si deschide potrivirea pe sate (vezi `_SATE`). Fara el,
    comportamentul e neschimbat, bit cu bit — o sursa nationala nu castiga si nu pierde nimic.
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
        if _ambiguu_fara_marca(m, plat):
            continue
        nivel = index[m.group(1)]
        if nivel == "regional" and _regiune_ca_nume_propriu(m, original, plat):
            continue
        calif = _CALIFICATIV.search(plat[max(0, m.start() - 12):m.start()])
        if calif:
            nivel = _NIVEL_CALIFICATIV[calif.group(1)]
        if gasit is None or _ORDINE[nivel] > _ORDINE[gasit]:
            gasit = nivel
            if gasit == "local":
                break        # nu exista nivel mai specific
    if gasit == "local" or not judet:
        return gasit

    # Nimic la nivel de UAT si stim judetul sursei -> incercam satele lui. Doar aici, si doar
    # ale lui: un sat din alt judet nu spune nimic despre ce publica sursa asta.
    rx_sate = _regex_sate(judet)
    if rx_sate is None:
        return gasit
    for m in rx_sate.finditer(plat):
        if not original[m.start():m.start() + 1].isupper():
            continue
        # Aici NU se mai verifica `_AMBIGUE`: fiecare nume de acolo e si UAT (invariantul e
        # testat), deci garda de mai jos il taie oricum. O a doua verificare ar fi cod care
        # nu ruleaza niciodata — verificat, scoaterea ei nu misca niciun articol din corpus.
        # Ambiguitatea specifica SATELOR e alta problema, netratata inca: un ziar de Iasi care
        # scrie „Crucea Rosie" potriveste satul CRUCEA. Nu s-a produs in 1733 de articole.
        # Numele care exista SI in indexul de UAT-uri au fost deja judecate mai sus, la
        # nivelul lor corect. Fara garda asta, SIRUTA (care are sate omonime cu judetul lor)
        # transforma „judetul Galati" in stire locala: masurat, 3 din 15 schimbari erau exact
        # asta — Galati, Brasov, Vaslui, toate articole judetene.
        if index.get(m.group(1)):
            continue
        return "local"
    return gasit


# ---- Gruparea surselor institutionale pe regiune -> judet (pentru /surse/) ----

_JUD_DIN_CHEIE: dict | None = None


def _judete_normalizate() -> dict:
    """{'BISTRITA_NASAUD': 'BISTRITA-NASAUD', ...} — forma din cheia sursei -> numele din CSV.
    Cheile sunt slug-uri (`pl_bistrita_nasaud_...`), deci cratima devine underscore."""
    global _JUD_DIN_CHEIE
    if _JUD_DIN_CHEIE is None:
        _JUD_DIN_CHEIE = {}
        for judete in REGIUNI.values():
            for j in judete:
                _JUD_DIN_CHEIE[j.replace("-", "_").replace(" ", "_")] = j
    return _JUD_DIN_CHEIE


def judet_din_cheie(cheie: str) -> str | None:
    """Judetul unei surse institutionale, din cheia ei de config.

    `pl_bistrita_nasaud_municipiul_bistrita` -> 'BISTRITA-NASAUD' · `cj_cluj` -> 'CLUJ'.
    Potrivirea e pe cel mai LUNG nume: altfel `satu_mare` s-ar opri la un judet mai scurt.
    Returneaza None pentru sursele care nu codeaza un judet (ziare, surse nationale).
    """
    if not cheie:
        return None
    rest = cheie.split("_", 1)[1] if "_" in cheie else ""
    if not rest:
        return None
    rest = rest.upper()
    judete = _judete_normalizate()
    for slug in sorted(judete, key=len, reverse=True):
        if rest == slug or rest.startswith(slug + "_"):
            return judete[slug]
    return None


def regiune_afisare(judet: str | None) -> str | None:
    """Regiunea de AFISARE a unui judet (7 regiuni), sau None daca judetul e necunoscut."""
    if not judet:
        return None
    for regiune, judete in REGIUNI.items():
        if judet in judete:
            return _COMASARI_AFISARE.get(regiune, regiune)
    return None


_ETICHETE_JUDETE: dict | None = None


def eticheta_judet(judet: str | None) -> str:
    """Numele judetului CU diacritice, pentru afisare: 'BISTRITA-NASAUD' -> 'Bistrița-Năsăud'.

    Sursa e `data/localities.json` (campul `judet`, deja cu diacritice, construit de
    build_gazetteer) — CSV-ul primariilor le are doar in antet, nu si in valori.
    """
    global _ETICHETE_JUDETE
    if _ETICHETE_JUDETE is None:
        _ETICHETE_JUDETE = {}
        try:
            with open(os.path.join(config.ROOT, "data", "localities.json"),
                      encoding="utf-8") as fh:
                date = json.load(fh)
            for intrari in (date.get("by_name") or {}).values():
                for e in intrari:
                    brut = (e.get("judet") or "").strip()
                    if not brut:
                        continue
                    curat = re.sub(r"^Jude[tț]ul\s+", "", brut).strip()
                    _ETICHETE_JUDETE.setdefault(
                        strip_diacritics(curat).upper(), curat)
        except (OSError, ValueError):
            pass
    if not judet:
        return ""
    # Cele doua pe care gazetteer-ul nu le acopera: Bucurestiul nu e judet acolo, iar
    # Valcea apare doar fara diacritice. Verificate una cate una, nu ghicite.
    return _ETICHETE_JUDETE.get(judet) or {
        "BUCURESTI": "București", "VALCEA": "Vâlcea",
    }.get(judet, judet.title())


def judet_copertei(a: dict) -> str:
    """Ce scrie pe badge-ul copertei in locul categoriei — judetul sursei, sau "" daca nu se poate.

    La `zonal` si `local` locul E subiectul, iar „Brasov" spune cititorului care vede cardul
    distribuit mult mai mult decat „ZONAL" — acolo se ia judetul SURSEI.

    La `regional` judetul sursei ar fi FALS (articolul acopera mai multe judete), dar regiunea
    e corecta si o numeste chiar articolul: poarta geografica il pune pe `regional` DOAR cand
    textul numeste regiunea, nu prin deducere din judet. Pana pe 2026-08-05 se afisa „REGIONAL",
    o eticheta care nu spune nimic; acum se recupereaza numele din titlu cu `regiune_din_text`.
    Ramane "" cand titlul nu-l contine (regiunea putea fi in corp) — mai bine categoria decat
    o regiune ghicita.

    La restul categoriilor locul nu e subiectul.

    Acoperire masurata 2026-08-04 pe 2128 articole: zonal 395/435 (91%), local 237/398 (60%).
    Restul raman pe categorie — de-aia intoarce "" in loc sa ghiceasca.
    """
    cat = a.get("category") or ""
    if cat == "regional":
        return regiune_din_text(a.get("title") or "") or ""
    if cat not in ("zonal", "local"):
        return ""
    return eticheta_judet(judet_sursa(a.get("source")))
