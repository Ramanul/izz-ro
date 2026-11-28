"""Vocea site-ului: recunoaște subiectele grele și violența ca metaforă în titluri.

Felia 1 din `specs/vocea-site-ului-felia1.md`. Cod DETERMINIST, zero apeluri AI.

- `subiect_greu()` — True când titlul vorbește LITERAL despre moarte sau violență
  asupra oamenilor. Alege precizia, nu acoperirea: un semn pus pe sport sau economie strică
  credibilitatea etichetei. Două straturi:
    1. lexic de precizie înaltă, valabil în orice rubrică;
    2. lexic contextual (victimă, masacru, crimă), numai în rubricile unde cuvintele au sens fizic.
- `violenta_in_titlu()` — metafore și intensificatori („a spulberat", „devastator"). Folosit ca
  CONTOR în QA/log, nu ca filtru: o știre validă nu se aruncă pentru un cuvânt din titlu.

Textul se normalizează (litere mici, fără diacritice, ș/ş și ț/ţ identice) și se potrivește pe
frontiere de cuvânt, ca „violet", „amortizor" sau „mort de râs" să nu declanșeze nimic.
"""
from __future__ import annotations

import re
import unicodedata

# Rubricile în care cuvintele de strat 2 au de obicei sens figurat („masacru pe bursă",
# „victimă a inflației", „crima perfectă" într-o recenzie). Numele vin din `data/articles.json`.
RUBRICI_FARA_STRAT_2 = frozenset({
    "sport", "economic", "tech", "cultura", "lifestyle", "ai", "discounturi",
})


def normalizeaza(text: str) -> str:
    """Litere mici, fără diacritice; ș/ş și ț/ţ devin s și t."""
    descompus = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in descompus if not unicodedata.combining(c)).lower()


def _rx(*expresii: str) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(expresii) + r")\b")


# Strat 1 — precizie înaltă. „mort" simplu lipsește intenționat („mort de râs", „punct mort",
# „natură moartă"); rămân formele care spun deja că e vorba de oameni.
_STRAT_1 = _rx(
    r"a murit", r"au murit", r"a decedat", r"au decedat", r"decedat\w*", r"decese", r"deces",
    r"morti", r"gasit mort", r"gasita moarta", r"gasiti morti", r"gasite moarte",
    r"omor\w*", r"omucid\w*", r"ucis\w*", r"ucid\w*", r"ucigas\w*", r"asasin\w*",
    r"sinucid\w*", r"suicid\w*", r"femicid\w*", r"cadavr\w*", r"spanzurat\w*",
    r"carbonizat\w*", r"impuscat\w*", r"injunghiat\w*", r"injunghier\w*", r"impuscatur\w*",
    r"viol", r"violul", r"violului", r"violuri", r"violator\w*",
    r"agresiune sexuala", r"agresiuni sexuale", r"abuz sexual", r"abuzuri sexuale",
)

# Strat 2 — contextual; nu se aplică în RUBRICI_FARA_STRAT_2.
_STRAT_2 = _rx(
    r"victima", r"victime", r"victimele", r"victimei", r"victimelor", r"masacr\w*", r"crima", r"crime", r"crimei",
    r"atac armat", r"atacuri armate",
)

# Metafore și intensificatori de violență în titlurile scrise de site.
_METAFORE = _rx(
    r"spulber\w*", r"zdrobit\w*", r"anihilat\w*", r"macelarit\w*", r"pulverizat\w*",
    r"devastator\w*", r"socant\w*", r"cutremurator\w*", r"zguduitor\w*",
)


# „fără victime", „nicio victimă", „nu s-au înregistrat morți": negația scoate cuvântul înainte
# de potrivire (măsurat 28.11.2026: 17 articole marcate greșit din cauza ei).
_NEGATIE = re.compile(
    r"\b(?:fara|nicio|nici o|nu au existat|nu exista|nu sunt|nu s-au inregistrat|nu s-au semnalat)"
    r"\s+(?:\w+\s+)?(?:victim\w*|morti|raniti|decese|deces)\b"
)


def subiect_greu(titlu: str, rubrica: str = "") -> bool:
    """True dacă TITLUL vorbește literal despre moarte sau violență asupra oamenilor.

    Doar titlul, nu rezumatul: pe corpusul din 28.11.2026, 327 din 803 marcaje veneau numai din
    rezumat și erau în mare parte false („victima unei escrocherii", registru de decese, moștenire).
    """
    text = _NEGATIE.sub(" ", normalizeaza(titlu or ""))
    if _STRAT_1.search(text):
        return True
    if normalizeaza(rubrica) in RUBRICI_FARA_STRAT_2:
        return False
    return bool(_STRAT_2.search(text))


def violenta_in_titlu(titlu: str) -> list[str]:
    """Metaforele/intensificatorii găsiți în titlu (formele normalizate), în ordinea apariției."""
    return _METAFORE.findall(normalizeaza(titlu))
