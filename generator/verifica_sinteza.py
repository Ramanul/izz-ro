"""Verificari MECANICE pe iesirea modelului, comparata cu textul sursa.

De ce exista fisierul asta separat de prompturi: din regulile de sinteza
(REGULI-SINTEZA.md), o parte se pot VERIFICA determinist — adica prin comparatie de
text, cu acelasi rezultat de fiecare data — iar restul se pot doar CERE modelului.
Nu e acelasi lucru. Un prompt cu 17 reguli obtine respectare partiala, iar regulile de
la coada listei sunt cele scapate. O regula care traieste doar in prompt e o speranta;
una verificata aici produce o iesire pe care o citim.

Ce se verifica aici (§2.3, §2.5, §2.7 din REGULI-SINTEZA.md):
  · citatele        — ce e intre ghilimele TREBUIE sa existe cuvant cu cuvant in sursa
  · cifrele         — orice numar din rezumat trebuie sa apara in sursa
  · rezerva         — daca sursa spune „ar fi / acuzat / presupus" si rezumatul nu, semnal
  · text copiat     — cate cuvinte consecutive din rezumat exista identic in sursa (§2.2)

Ce NU se poate verifica aici si ramane in prompt: esenta vs detaliul secundar (§1.1),
informatia grea la inceput (§1.2), atribuirea (§2.6). Nicio masina nu le poate citi.

MOD DE LUCRU: functiile astea RAPORTEAZA, nu resping. Pragul de respingere se stabileste
dupa masurarea pe corpusul real (`tools/masoara_sinteza.py`), nu ghicit — aceeasi
disciplina ca la pragul de 16 caractere/cuvant din garda de continut (IZZ-0168), derivat
din 6714 campuri reale.
"""
from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple


class Problema(NamedTuple):
    cod: str          # citat_inventat | cifra_straina | rezerva_pierduta
    detaliu: str


# Ghilimele romanesti („...") si drepte ("..."), plus franceze (« ») care apar in feeduri.
_PERECHI_GHILIMELE = [("„", "”"), ("“", "”"), ('"', '"'),
                      ("«", "»")]

# Marcatori de rezerva. Ordinea nu conteaza; prezenta oricaruia inseamna „sursa nu afirma
# faptul ca fiind stabilit". Lista e deliberat scurta si concreta: una lunga ar potrivi
# accidental cuvinte obisnuite si ar face semnalul inutil.
_REZERVE = (
    "ar fi", "ar putea", "presupus", "presupusa", "presupusul",
    "acuzat", "acuzata", "acuzatie", "suspectat", "suspectata",
    "potrivit unor surse", "surse neoficiale", "neconfirmat", "neconfirmata",
    "sustine ca", "sustin ca", "pretinde ca", "afirma ca",
    "urmeaza sa", "ar urma sa", "in curs de", "posibil",
)


def _norm(text: str) -> str:
    """Fara diacritice, fara spatii multiple, litere mici.

    Diacriticele se ignora deliberat: modelul adauga adesea diacritice pe care sursa nu
    le are (feeduri de primarie scriu „hotarare"), iar un citat corect nu devine inventat
    fiindca s-a scris „hotărâre".
    """
    fara = unicodedata.normalize("NFKD", text or "")
    fara = "".join(c for c in fara if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", fara).strip().lower()


def _cifre(text: str) -> list[str]:
    """Siruri de cifre, normalizate: separatorii de mii si zecimalele se arunca.

    „1.500", „1 500" si „1500" sunt acelasi numar. Numerele de o singura cifra se ignora:
    apar peste tot din motive gramaticale si ar produce zgomot, nu semnal.
    """
    brut = re.findall(r"\d[\d.,\s]*\d|\d", text or "")
    iesire = []
    for n in brut:
        curat = re.sub(r"[.,\s]", "", n)
        if len(curat) >= 2:
            iesire.append(curat)
    return iesire


def citate_inventate(rezumat: str, sursa: str) -> list[str]:
    """Fragmentele dintre ghilimele care NU apar cuvant cu cuvant in sursa.

    §2.3: un citat se reproduce exact sau deloc. Parafrazarea unei declaratii ca si cum
    ar fi citat e interzisa — e cazul in care cititorul crede ca are cuvintele omului.
    """
    s = _norm(sursa)
    gasite = []
    for deschis, inchis in _PERECHI_GHILIMELE:
        tipar = re.escape(deschis) + r"([^" + re.escape(deschis + inchis) + r"]{8,})" + re.escape(inchis)
        for fragment in re.findall(tipar, rezumat or ""):
            if _norm(fragment) not in s:
                gasite.append(fragment.strip())
    return gasite


def cifre_straine(rezumat: str, sursa: str) -> list[str]:
    """Numerele din rezumat care nu exista in sursa.

    §2.7: cifrele se transporta exact. Un numar aparut din compresie e cel mai usor de
    prins tip de fapt inventat, si cel mai greu de observat cu ochiul liber.
    """
    in_sursa = set(_cifre(sursa))
    return [n for n in _cifre(rezumat) if n not in in_sursa]


def rezerva_pierduta(rezumat: str, sursa: str) -> bool:
    """True cand sursa marcheaza incertitudine si rezumatul n-o mai are deloc.

    §2.5, regula cu cel mai mare risc juridic: „X e acuzat ca ar fi delapidat" nu devine
    „X a delapidat". Comprimarea sterge marcatorii primii, fiindca arata a umplutura.

    Euristica — adica un semnal aproximativ, nu o dovada: sursa poate marca rezerva pe un
    detaliu secundar care nici nu ajunge in rezumat. De aceea RAPORTEAZA, nu respinge.
    """
    s, r = _norm(sursa), _norm(rezumat)
    if not any(m in s for m in _REZERVE):
        return False
    return not any(m in r for m in _REZERVE)


# --- §2.2: reformulare integrala, ZERO propozitii copiate ------------------------
# Singura regula din REGULI-SINTEZA.md cu expunere de DREPT DE AUTOR, si singura care
# pana acum traia doar in prompt (5 aparitii in `process.py`). Masuratoarea de aici nu
# respinge nimic: pragul se stabileste dupa ce vedem cifre pe rulari reale, nu invers.
#
# De ce se masoara IN ZBOR si nu pe corpusul publicat: textul sursei nu se pastreaza in
# stare. `process.py` il sterge deliberat (comentariul de la `process_cluster` ii spune
# „scrub juridic"), deci dupa salvare nu mai exista cu ce compara. Verificat pe
# `data/articles.json`: 0 din 3907 articole mai au `original_title` sau `description`.
# Consecinta: masuram cat timp ambele texte sunt in memorie si salvam DOAR scorul —
# niciodata textul sursei, ca sa nu reintroducem prin usa din dos exact ce a scos scrubul.

# ALEGERE DE PORNIRE, NU PRAG MASURAT. Cautat inainte de a o scrie: `registru.py find
# suprapunere|copiat` -> zero randuri pe subiect, `HANDOFF.md` si `REGULI-SINTEZA.md` -> nimic.
# Deci nu exista masuratoare anterioara de care sa se agate. 8 vine din rationament, nu din
# date: sub 8, formulari uzuale („a declarat ca in cursul zilei de miercuri") ies drept
# copiere si semnalul se ineaca. Se recalibreaza dupa primele rulari reale.
_LUNGIME_SECVENTA = 8


class Suprapunere(NamedTuple):
    procent: float      # cat din rezumat exista cuvant-cu-cuvant in sursa (0-100)
    max_cuvinte: int    # cea mai lunga secventa identica, in cuvinte
    fragment: str       # secventa aia, ca sa se poata citi cu ochiul


def _cuvinte(text: str) -> list[str]:
    """Cuvintele normalizate, fara punctuatie.

    Punctuatia se arunca deliberat: „politisti." si „politisti" sunt acelasi cuvant, iar
    daca n-ar fi, o virgula mutata ar ascunde o propozitie copiata integral.
    """
    return re.findall(r"[a-z0-9]+", _norm(text))


def _secvente(cuvinte: list[str], n: int) -> set[tuple]:
    """Toate ferestrele de n cuvinte consecutive."""
    if len(cuvinte) < n:
        return set()
    return {tuple(cuvinte[i:i + n]) for i in range(len(cuvinte) - n + 1)}


def _cea_mai_lunga_comuna(a: list[str], b: list[str]) -> tuple[int, str]:
    """Cel mai lung sir de cuvinte consecutive prezent in ambele texte.

    Programare dinamica pe doua randuri: memoria e O(len(b)), nu O(len(a)*len(b)). Textele
    sunt scurte (rezumat ~60 de cuvinte, sursa ~600), deci costul e neglijabil per articol.
    Cifra asta e mai usor de citit de un om decat procentul: „14 cuvinte identice la rand"
    se intelege imediat, „31%" nu.
    """
    if not a or not b:
        return 0, ""
    anterior = [0] * (len(b) + 1)
    best, best_sfarsit = 0, 0
    for i in range(1, len(a) + 1):
        curent = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                curent[j] = anterior[j - 1] + 1
                if curent[j] > best:
                    best, best_sfarsit = curent[j], i
        anterior = curent
    return best, " ".join(a[best_sfarsit - best:best_sfarsit])


def suprapunere_sursa(rezumat: str, sursa: str, n: int = _LUNGIME_SECVENTA) -> Suprapunere:
    """Cat din rezumat e copiat cuvant-cu-cuvant din sursa.

    RAPORTEAZA, nu respinge — vezi antetul modulului. `procent` e fractia de ferestre de
    n cuvinte din rezumat care se regasesc identic in sursa; 0 inseamna reformulare
    completa, 100 inseamna ca tot rezumatul e transcris.

    Un rezumat mai scurt de n cuvinte da procent 0 prin constructie, nu fiindca e curat.
    De aceea `max_cuvinte` se calculeaza separat, fara pragul de lungime: pe titluri —
    care au 6-16 cuvinte — el e singurul semnal disponibil.
    """
    r, s = _cuvinte(rezumat), _cuvinte(sursa)
    ferestre_r = _secvente(r, n)
    if ferestre_r:
        ferestre_s = _secvente(s, n)
        procent = 100.0 * len(ferestre_r & ferestre_s) / len(ferestre_r)
    else:
        procent = 0.0
    max_cuvinte, fragment = _cea_mai_lunga_comuna(r, s)
    return Suprapunere(round(procent, 1), max_cuvinte, fragment)


def verifica(titlu: str, rezumat: str, sursa: str) -> list[Problema]:
    """Toate verificarile, pe titlu + rezumat impreuna.

    Titlul si rezumatul se verifica in acelasi bloc fiindca regulile sunt aceleasi si
    fiindca o cifra poate migra din unul in celalalt.
    """
    text = f"{titlu or ''} {rezumat or ''}"
    probleme: list[Problema] = []
    for c in citate_inventate(text, sursa):
        probleme.append(Problema("citat_inventat", c[:120]))
    for n in cifre_straine(text, sursa):
        probleme.append(Problema("cifra_straina", n))
    if rezerva_pierduta(text, sursa):
        probleme.append(Problema("rezerva_pierduta", ""))
    return probleme
