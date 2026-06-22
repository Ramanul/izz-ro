"""AI: modelul B (teaser pe articol) si modelul C (sinteza pe cluster).

Apararea in adancime: chiar daca AI depaseste limita sau pica, codul taie la
TEASER_MAX_WORDS / SYNTHESIS_MAX_WORDS si are fallback determinist (fara AI).
"""
import json
import re

from . import config
from .util import truncate_words

# ---- Prompturi calibrate juridic (zero propozitii copiate din original) ----

SYSTEM_B = ("Esti editor de stiri. Reformulezi titlul direct, fara clickbait, si extragi "
            "DOAR faptele esentiale in propozitii complet noi. Raspunzi exclusiv JSON valid.")

USER_B = """Titlu original: {title}
Descriere RSS: {description}

Returneaza: {{"title": "<titlu reformulat care transmite faptul COMPLET, fara clickbait; max 22 de cuvinte; NU taia ideea cu '...'>",
             "teaser": "<max 40 de cuvinte, faptele cheie, propozitii 100% noi, NICIO fraza copiata; ramane util DOAR ca rezumat scurt, nu ca inlocuitor al articolului>",
             "category": "<una din: general|politic|economic|extern|tech|sport>"}}
Reguli: zero propozitii reproduse din original; zero opinii; daca descrierea e insuficienta -> teaser = "Detalii pe sursa."
"""

SYSTEM_C = ("Esti editor care sintetizeaza un eveniment din MAI MULTE surse, cu cuvintele tale. "
            "Raspunzi exclusiv JSON valid.")

USER_C = """Eveniment, relatat de surse:
{sources_block}

Returneaza: {{"title": "<titlu reformulat care transmite faptul complet; max 22 de cuvinte; fara clickbait>",
             "synthesis": "<max 90 de cuvinte: faptele comune confirmate de surse, reformulate complet; un rand de context propriu; mentioneaza ca detaliile sunt la surse>",
             "category": "<una din: general|politic|economic|extern|tech|sport>"}}
Reguli: trianguleaza faptele (ce confirma mai multe surse); zero propozitii copiate; marcheaza daca sursele se contrazic.
"""


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
    except Exception as exc:
        rep["title"] = truncate_words(rep.get("original_title", ""), config.TITLE_MAX_WORDS)
        rep["synthesis"] = truncate_words(rep.get("description") or "Detalii pe surse.",
                                          config.SYNTHESIS_MAX_WORDS)
        rep["processed_by"] = "fallback"
        rep["error"] = str(exc)
    return rep
