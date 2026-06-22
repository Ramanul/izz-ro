"""AI: modelul B (teaser pe articol) si modelul C (sinteza pe cluster).

Apararea in adancime: chiar daca AI depaseste limita sau pica, codul taie la
TEASER_MAX_WORDS / SYNTHESIS_MAX_WORDS si are fallback determinist (fara AI).
"""
import json
import re

from . import config
from .util import truncate_words

# ---- Prompturi calibrate juridic (zero propozitii copiate din original) ----

SYSTEM_B = ("Esti editor de stiri. Scopul tau: titlul reda ESENTA faptului, iar rezumatul comprima "
            "faptele de baza, cu cuvintele tale. Concret, nu vag. Raspunzi exclusiv JSON valid.")

USER_B = """Titlu original: {title}
Descriere: {description}

Scrie un titlu si un rezumat care REDAU ESENTA, cu cuvintele tale.
Returneaza JSON:
{{"title": "<esenta faptului: CINE face/pateste CE (si unde/cand daca e cheie); concret si clar; 6-16 cuvinte; fara clickbait, fara formulari vagi precum 'iata ce', 'ce a patit'>",
  "teaser": "<rezumat COMPRIMAT al faptelor de baza in 25-40 de cuvinte: cine, ce, cand, unde, cat/de ce; reformulat 100%, ZERO propozitii copiate din original; trebuie sa transmita esenta fara a citi articolul>",
  "category": "<una din: general|politic|economic|extern|tech|sport>"}}
Reguli: titlul trebuie sa se inteleaga singur si sa contina faptul real, nu o intrebare/teaser; NU copia nicio propozitie din original; zero opinii; daca descrierea e saraca, extrage esenta din titlul original (tot reformulat)."""

SYSTEM_C = ("Esti editor care sintetizeaza un eveniment din MAI MULTE surse, cu cuvintele tale. "
            "Titlul reda esenta evenimentului; sinteza comprima faptele confirmate. Raspunzi exclusiv JSON valid.")

USER_C = """Eveniment, relatat de surse:
{sources_block}

Scrie titlu + sinteza care REDAU ESENTA evenimentului, cu cuvintele tale.
Returneaza JSON:
{{"title": "<esenta evenimentului: ce s-a intamplat, concret; 6-16 cuvinte; fara clickbait>",
  "synthesis": "<sinteza COMPRIMATA in 40-80 de cuvinte: faptele confirmate de mai multe surse (cine, ce, cand, unde, cat), reformulate 100%; marcheaza daca sursele se contrazic>",
  "category": "<una din: general|politic|economic|extern|tech|sport>"}}
Reguli: trianguleaza faptele comune; ZERO propozitii copiate; titlul contine faptul real, nu un teaser; zero opinii."""


def get_provider():
    """Returneaza providerul cerut daca e disponibil, altfel None (-> fallback)."""
    if config.AI_PROVIDER == "anthropic":
        from .providers.anthropic import AnthropicProvider
        p = AnthropicProvider()
    else:
        from .providers.gemini import GeminiProvider
        p = GeminiProvider()
    return p if p.available() else None


def _parse_json(text: str) -> dict:
    """Extrage primul obiect JSON din raspuns (tolerant la ```json fences)."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


def _valid_category(cat: str, fallback: str) -> str:
    return cat if cat in config.CATEGORIES else fallback


def process_single(item: dict, provider) -> dict:
    """Model B. Modifica item-ul pe loc: title/teaser/category/model/processed_by."""
    item["model"] = "B"
    if provider is None:
        item["title"] = truncate_words(item.get("original_title", ""), config.TITLE_MAX_WORDS)
        item["teaser"] = truncate_words(item.get("description") or "Detalii pe sursa.",
                                        config.TEASER_MAX_WORDS)
        item["processed_by"] = "fallback"
        return item
    try:
        raw = provider.complete(SYSTEM_B, USER_B.format(
            title=item.get("original_title", ""), description=item.get("description", "")))
        data = _parse_json(raw)
        item["title"] = (data.get("title") or item.get("original_title", "")).strip()
        item["teaser"] = truncate_words(data.get("teaser", "") or "Detalii pe sursa.",
                                        config.TEASER_MAX_WORDS)
        item["category"] = _valid_category(data.get("category", ""), item.get("category", "general"))
        item["processed_by"] = provider.name
        item["prompt_version"] = config.PROMPT_VERSION
    except Exception as exc:  # un esec pe un articol nu opreste pipeline-ul
        item["title"] = truncate_words(item.get("original_title", ""), config.TITLE_MAX_WORDS)
        item["teaser"] = truncate_words(item.get("description") or "Detalii pe sursa.",
                                        config.TEASER_MAX_WORDS)
        item["processed_by"] = "fallback"
        item["error"] = str(exc)
    return item


def process_cluster(group: list, provider) -> dict:
    """Model C. Returneaza un articol-reprezentant cu sinteza + lista de surse."""
    rep = dict(min(group, key=lambda a: a.get("published") or ""))
    rep["model"] = "C"
    _seen_src = set()
    rep["sources"] = [
        {"name": a["source_name"], "url": a["original_link"]}
        for a in group
        if a["source_name"] not in _seen_src and not _seen_src.add(a["source_name"])
    ]

    if provider is None:
        rep["title"] = truncate_words(rep.get("original_title", ""), config.TITLE_MAX_WORDS)
        rep["synthesis"] = truncate_words(rep.get("description") or "Detalii pe surse.",
                                          config.SYNTHESIS_MAX_WORDS)
        rep["processed_by"] = "fallback"
        return rep

    block = "\n".join(f"- {a['source_name']}: {a.get('original_title','')} - {a.get('description','')}"
                      for a in group)
    try:
        raw = provider.complete(SYSTEM_C, USER_C.format(sources_block=block))
        data = _parse_json(raw)
        rep["title"] = (data.get("title") or rep.get("original_title", "")).strip()
        rep["synthesis"] = truncate_words(data.get("synthesis", "") or "Detalii pe surse.",
                                          config.SYNTHESIS_MAX_WORDS)
        rep["category"] = _valid_category(data.get("category", ""), rep.get("category", "general"))
        rep["processed_by"] = provider.name
        rep["prompt_version"] = config.PROMPT_VERSION
    except Exception as exc:
        rep["title"] = truncate_words(rep.get("original_title", ""), config.TITLE_MAX_WORDS)
        rep["synthesis"] = truncate_words(rep.get("description") or "Detalii pe surse.",
                                          config.SYNTHESIS_MAX_WORDS)
        rep["processed_by"] = "fallback"
        rep["error"] = str(exc)
    return rep
