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
  · ortografia      — cuvintele din titlu care sunt deformări interne ale unor
                      cuvinte din sursă (cazul care o cere: „Artizeții" in loc de
                      „Artiștii", PR #371)

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
    cod: str          # citat_inventat | cifra_straina | rezerva_pierduta | cuvant_strain_titlu
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


# Un separator leaga doua grupuri de cifre intr-un SINGUR numar doar cand arata a
# separator de mii: cel mult 3 cifre in stanga, exact 3 in dreapta („1.500.000", „1 500").
# Orice altceva — o data („13.08.2026"), o enumerare („2026, 13") — sunt numere distincte.
# Tiparul vechi, `\d[\d.,\s]*\d`, inghitea separatori MULTIPLI si lipea tot ce prindea:
# „13.08.2026" devenea „13082026", deci „13" si „2026" nu mai existau in sursa si un
# rezumat corect era marcat `cifra_straina`. Masurat 2026-09-06 pe rularea 34013150305:
# a blocat publicarea intregului site pe doua anunturi de primarie.
_GRUP_NUMERIC = re.compile(r"\d+(?:[.,\s]\d+)*")
_SEPARATOR_MII = re.compile(r"^\d{1,3}(?:[.,\s]\d{3})+$")


def _variante_numar(token: str) -> set[str]:
    """Formele sub care acelasi token numeric poate fi recunoscut.

    Un format valid de mii se citeste DOAR lipit („1.500.000" e un milion si jumatate,
    nu 1, 500 si 000). Restul se citeste in ambele feluri, ca o data sau o enumerare sa
    nu isi ascunda componentele.
    """
    parti = [p for p in re.split(r"[.,\s]+", token) if p]
    lipit = "".join(parti)
    out: set[str] = set()
    if len(lipit) >= 2:
        out.add(lipit)
    if not _SEPARATOR_MII.match(token):
        out.update(p for p in parti if len(p) >= 2)
    return out


def _cifre(text: str) -> list[str]:
    """Numerele din text, normalizate.

    Numerele de o singura cifra se ignora: apar peste tot din motive gramaticale si ar
    produce zgomot, nu semnal.
    """
    iesire = []
    for token in _GRUP_NUMERIC.findall(text or ""):
        variante = _variante_numar(token)
        if variante:
            iesire.append(min(sorted(variante), key=len))
    return iesire


def _index_cifre(text: str) -> set[str]:
    """Toate formele numerelor din sursa.

    Indexarea e GENEROASA deliberat, si asimetria e voita: gate-ul e blocant, deci un
    fals pozitiv opreste publicarea unui articol corect (costul masurat: site inghetat),
    pe cand un fals negativ cere ca numarul inventat sa fie exact concatenarea a doua
    numere reale alaturate din sursa.
    """
    idx: set[str] = set()
    for token in _GRUP_NUMERIC.findall(text or ""):
        idx |= _variante_numar(token)
    return idx


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
    in_sursa = _index_cifre(sursa)
    straine = []
    for token in _GRUP_NUMERIC.findall(rezumat or ""):
        variante = _variante_numar(token)
        if variante and not (variante & in_sursa):
            straine.append(min(sorted(variante), key=len))
    return straine


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


# --- Praguri BLOCANTE pentru §2.2, derivate din REGULA, nu din statistici ---------
# Jurnalul de calibrare (data/raport_copiere.jsonl, 21 randuri la 2026-09-05) NU conține
# corpus real: 7 din 21 sunt artefacte sintetice (același URL de test „bizbrasov.ro/a"),
# deci nu există distribuție pe care să o citim — un prag statistic ar fi ghicit.
# În schimb, §2.2 spune literal „reformulare integrală, ZERO propoziții copiate":
# o secvență verbatim de 15+ cuvinte în afara citatelor E cel puțin o propoziție copiată
# integral, indiferent de corpus. Aceeași logică pentru titlu: un titlu de 6+ cuvinte
# regăsit cuvânt cu cuvânt în sursă este un titlu transcris, nu reformulat.
# Recalibrarea statistică rămâne deschisă: dacă jurnalul acumulează corpus real și arată
# fals pozitive, pragurile se schimbă AICI, cu distribuția citată în comentariu.
PRAG_PROPOZITIE_COPIATA = 15
PRAG_TITLU_COPIAT = 6


def _fara_citate_echilibrate(text: str) -> str:
    """Scoate spanurile dintre perechile de ghilimele.

    §2.3 permite citatul exact, deci un citat verbatim lung NU e copiere ilicită. Se
    elimină doar perechile echilibrate: un ghilimel neînchis nu aruncă restul textului
    sub prag — mai bine un fals blocant decât o copiere ascunsă de o ghilimeală pierdută.
    """
    text = text or ""
    for deschis, inchis in _PERECHI_GHILIMELE:
        text = re.sub(re.escape(deschis) + r"[^" + re.escape(inchis) + r"]*?" + re.escape(inchis),
                      " ", text)
    return text


def propozitii_copiate(rezumat: str, sursa: str) -> list[str]:
    """Fragmentele din rezumat (în afara citatelor) copiate verbatim ≥ PRAG cuvinte."""
    r = _cuvinte(_fara_citate_echilibrate(rezumat or ""))
    s = _cuvinte(sursa or "")
    lungime, fragment = _cea_mai_lunga_comuna(r, s)
    if lungime >= PRAG_PROPOZITIE_COPIATA:
        return [fragment]
    return []


def titlu_copiat(titlu: str, sursa: str) -> bool:
    """True când titlul (≥ PRAG_TITLU_COPIAT cuvinte) există cuvânt cu cuvânt în sursă."""
    t = _cuvinte(titlu or "")
    if len(t) < PRAG_TITLU_COPIAT:
        return False
    lungime, _ = _cea_mai_lunga_comuna(t, _cuvinte(sursa or ""))
    return lungime == len(t)


# --- Garda ortografiei titlului: cuvinte deformate intern (2026-10-01) -------------
# Cazul real care o cere (PR #371): titlul sintetizat de model a scris „Artizeții" în
# loc de „Artiștii", eroarea a ajuns în titlu, H1 și în slug-ul URL, publicată și
# indexată. Verificările existente n-o vedeau: ele se uită la citate, cifre și
# copiere — nimic nu compara ortografia cuvintelor din titlu cu textul sursei.
#
# DIRECȚIA VERIFICĂRII, decisă după prima rundă de teste: NU „titlul nu poate conține
# decât cuvinte din sursă" — acolo modelul scrie legitime cuvinte pe care rezumatul-
# sursă (descrierea din feed) nu le conține („anunțați" nu era în descrierea B365), deci
# alarme false pe cuvinte corecte. Ci invers: se semnalează doar cuvântul care este
# DEFORMARE INTERNĂ a unui cuvânt care ESTE în sursă:
#   · vecin în sursă la distanță Levenshtein ≤ 2 (cazul real: z→s + „e" în plus = 2);
#   · trece fără semnal dacă diferența arată a inflexiune românească: un cuvânt este
#     prefixul celuilalt („consiliu"→„consiliului") sau divergența e doar în
#     terminație („hotărârea"→„hotărârii");
#   · cuvânt fără vecin în sursă trece — vocabularul modelului e mai mare decât
#     descrierea din feed, și asta e normal.
# RAPORTEAZĂ, nu respinge: codul NU e în `_BLOCKING` din `raport_copiere.py` până
# când rata de alarme false nu e măsurată pe rulări reale — jurnalul acumulează
# `advisory_issues` de la prima rulare, activarea e o linie în `_BLOCKING`.
_LUNGIME_MIN_CUVANT = 5
# ALEGERE DE PORNIRE, NU PRAG MASURAT (aceeași disciplină ca `_LUNGIME_SECVENTA`):
# sub 5 litere, acronimele și numele prescurtate („Fest", „SIDA") ar produce zgomot.
_MAX_DISTANTA = 2
_PORCIUNE_SUFIX = 0.7
# Divergența dintre cuvinte se ia „infecție" doar dacă e îngropată în corpul cuvântului;
# dacă apare în ultimele ~30% (terminația), arată a caz gramatical, nu deformare.
_DELTA_PREFIX_MAX = 3


def _levenshtein_pană_la(a: str, b: str, limită: int) -> int:
    """Distanța Levenshtein, tăiată la `limită` (rânduri DP + abandon devreme).

    Întoarce limită+1 când depășește limita — apelantul compară cu `_MAX_DISTANTA`.
    Cuvintele sunt scurte (≤15 litere), deci DP-ul simplu bate orice indexare specială.
    """
    if abs(len(a) - len(b)) > limită:
        return limită + 1
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curent = [i] + [0] * len(b)
        minim_rând = curent[0]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curent[j] = min(anterior[j] + 1, curent[j - 1] + 1, anterior[j - 1] + cost)
            minim_rând = min(minim_rând, curent[j])
        if minim_rând > limită:
            return limită + 1
        anterior = curent
    return anterior[-1]


def _arata_a_inflexiune(c: str, vecin: str) -> bool:
    """Diferența dintre c și vecin arată a caz gramatical, nu a deformare internă."""
    mare, mic = (c, vecin) if len(c) >= len(vecin) else (vecin, c)
    if mare.startswith(mic) and len(mare) - len(mic) <= _DELTA_PREFIX_MAX:
        return True
    prima_diferență = next((i for i in range(len(mic)) if c[i] != vecin[i]), len(mic))
    return prima_diferență / len(mare) >= _PORCIUNE_SUFIX


def cuvinte_straine_titlu(titlu: str, sursa: str) -> list[str]:
    """Cuvintele din titlu suspectate de deformare internă față de cuvinte din sursă.

    Vezi comentariul de bloc de mai sus pentru direcție și reguli. Fără cifre (au
    propria verificare, `cifre_straine`) și fără cuvinte sub `_LUNGIME_MIN_CUVANT`.
    O sursă fără niciun cuvânt întoarce []: nu putem verifica nimic față de nimic,
    iar `masoara_sinteza.py` numără oricum cazul ca neverificabil.
    """
    vocabular = set(_cuvinte(sursa or ""))
    if not vocabular:
        return []
    straine, vazute = [], set()
    for c in _cuvinte(titlu or ""):
        if len(c) < _LUNGIME_MIN_CUVANT or c.isdigit() or c in vazute:
            continue
        vazute.add(c)
        if c in vocabular:
            continue
        vecini = [v for v in vocabular
                  if _levenshtein_pană_la(c, v, _MAX_DISTANTA) <= _MAX_DISTANTA]
        if not vecini:
            continue
        if any(not _arata_a_inflexiune(c, v) for v in vecini):
            straine.append(c)
    return straine


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
    for fragment in propozitii_copiate(rezumat, sursa):
        probleme.append(Problema(
            "text_copiat",
            f"{PRAG_PROPOZITIE_COPIATA}+ cuvinte verbatim în afara citatelor: {fragment[:100]}",
        ))
    if titlu_copiat(titlu, sursa):
        probleme.append(Problema(
            "titlu_copiat",
            f"titlul ({len(_cuvinte(titlu or ''))} cuvinte) reproduce cuvânt cu cuvânt o secvență din sursă",
        ))
    for c in cuvinte_straine_titlu(titlu, sursa):
        probleme.append(Problema(
            "cuvant_strain_titlu",
            f"„{c}” nu există în sursă la distanță de editare ≤ 1",
        ))
    return probleme
