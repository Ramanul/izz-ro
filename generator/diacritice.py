"""Garda de diacritice: prinde reformularile AI care pierd diacriticele pe care sursa le are.

DE CE EXISTA. Masurat 2026-10-04 pe 24h de publicatii (747 articole): 13 (1,7%) aveau titlul
SI rezumatul fara nicio diacritica, iar 9 din cele 13 erau output AI (model B, `v2-esenta`) cu
diacriticele pierdute din cuvinte care in sursa le aveau („brand romanesc ... apa termala").
Nimic nu le prindea: promptul cere „SCRIE IN ROMANA" fara sa numeasca diacriticele, iar
`qa_check.py` nu masoara diacritice. Nu e o eroare de continut — dar pe un site de stiri o
propozitie scrisa „romanesc" se citeste ca text facut pe genunchi, si de-aia merita o garda.

CUM DECIDE, SI DE CE ASA. Predicatul NU se uita daca textul „arata româneste" (nu exista asa
ceva, iar jumatate din titluri n-au nevoie de nicio diacritica: „Cancelarul german Friedrich
Merz a vizitat Kievul" e corect fara ele). Se uita la SURSA: semnaleaza doar cand textul
generat n-are NICIO diacritica si cel putin DOUA cuvinte ale lui apar in sursa intr-o forma
CU diacritice (comparate fara diacritice, insensibil la majuscule) — „romanesc" din text
corespunde cu „românesc" din sursa. Un cuvant singur poate coincide intamplator
(„era" < „eră"); doua coincidente simultane sunt zgomot statistic, nu semnal.

Nu cheama AI si nu decide singura: `process.repara_diacritice` cere o singura reformulare
(una per lot, in bugetul de apeluri), iar ce ramane nereparat se numara si apare in logul de
build. Garda NU blocheaza publicarea unui articol: un provider degradat (toate textele fara
diacritice) ar goli site-ul daca am sari itemele, iar o eroare de gust nu merita o pană.
"""

from __future__ import annotations

import re

from .util import strip_diacritics

DIACRITICE = "ăâîșțĂÂÎȘȚ"

# Cuvant = litera (inclusiv diacritice) sau cratima, minim 2 caractere. Cifrele si semnele nu
# intra: „2026" nu poate purta diacritice, deci nu are ce cauta in comparatie.
_CUVANT = re.compile(r"[A-Za-zăâîșțĂÂÎȘȚ][A-Za-zăâîșțĂÂÎȘȚ-]*")

# Cate cuvinte trebuie sa coincida cu o forma diacritica din sursa ca sa semnalam.
PRAG_CUVINTE = 2


def are_diacritice(text: str) -> bool:
    return any(ch in DIACRITICE for ch in (text or ""))


def _cuvinte(text: str) -> list[str]:
    """Cuvintele normalizate (litere mici, fara diacritice) — cheia de comparatie."""
    return [strip_diacritics(w).lower() for w in _CUVANT.findall(text or "")]


def forme_diacritice(sursa: str) -> set[str]:
    """Formele FARA diacritice ale cuvintelor din sursa care AU diacritice.

    Doar ele ne intereseaza: daca sursa scrie „apa", textul generat care scrie „apa" nu a
    pierdut nimic. Daca sursa scrie „apă", un „apa" in textul generat e o pierdere.
    """
    return {strip_diacritics(w).lower() for w in _CUVANT.findall(sursa or "")
            if are_diacritice(w)}


def cuvinte_pierdute(sursa: str, generat: str) -> list[str]:
    """Cuvintele din textul generat care corespund unei forme diacritice din sursa."""
    forme = forme_diacritice(sursa)
    if not forme:
        return []
    return [w for w in _cuvinte(generat) if w in forme]


def lipsesc_diacriticele(sursa: str, generat: str, prag: int = PRAG_CUVINTE) -> bool:
    """True doar cand pierderea e clara: zero diacritice in text SI >= `prag` cuvinte pierdute."""
    if not are_diacritice(sursa) or are_diacritice(generat):
        return False
    return len(cuvinte_pierdute(sursa, generat)) >= prag


def text_generat(art: dict) -> str:
    """Textul care se publica: titlul + corpul (sinteza la C, teaser la B)."""
    corp = art.get("synthesis") if art.get("model") == "C" else art.get("teaser")
    return f"{art.get('title') or ''} {corp or ''}"


def text_sursa(art: dict) -> str:
    """Textul brut al sursei, cat timp mai exista pe item.

    `original_title`/`description` sunt sterse la salvare (`state._scrub_processed`), deci
    garda se poate rula DOAR in pipeline, pe itemele proaspete. Un rep C care actualizeaza un
    articol deja procesat nu le mai are — de aceea main.py ii da textul grupului
    (`text_grup`), nu textul mostenit de la reprezentant.
    """
    return " ".join(str(art.get(k) or "") for k in ("original_title", "description")).strip()


def text_grup(membri: list) -> str:
    """Textul brut al unui cluster: ce au scris sursele, membru cu membru."""
    parti = []
    for m in membri:
        brut = text_sursa(m)
        parti.append(brut or text_generat(m))
    return " ".join(p for p in parti if p)


# --- contoare pentru logul de build -------------------------------------------------------
# O garda care ruleaza fara sa spuna ce a gasit e o garda de decor. Cifrele ajung intr-o linie
# in logul de build ("... texte au pierdut diacriticele, ... reparate"), ca sa se poata urmari
# in timp daca problema se repara la sursa sau doar se cosmetizeaza.

_STAT = {"verificate": 0, "semnalate": 0, "reparate": 0}


def _bump(camp: str, n: int = 1) -> None:
    _STAT[camp] = _STAT.get(camp, 0) + n


def noteaza_verificate(n: int) -> None:
    _bump("verificate", n)


def noteaza_semnalate(n: int) -> None:
    _bump("semnalate", n)


def noteaza_reparate(n: int) -> None:
    _bump("reparate", n)


def goleste() -> None:
    for cheie in _STAT:
        _STAT[cheie] = 0


def raport() -> str:
    """Linia de log, sau '' cand nu s-a semnalat nimic (ca sa nu scrie zgomot la fiecare rulare)."""
    if not _STAT["semnalate"]:
        return ""
    return (f">> diacritice: {_STAT['semnalate']}/{_STAT['verificate']} texte noi au pierdut "
            f"diacriticele la reformulare, {_STAT['reparate']} reparate cu 1 apel AI")


def statistici() -> dict:
    return dict(_STAT)
