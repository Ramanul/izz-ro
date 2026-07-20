"""AI: modelul B (teaser pe articol) si modelul C (sinteza pe cluster).

Apararea in adancime: chiar daca AI depaseste limita sau pica, codul taie la
TEASER_MAX_WORDS / SYNTHESIS_MAX_WORDS si are fallback determinist (fara AI).
"""
import json
import re

from . import config
from .util import truncate_words, domain_of

# ---- Prompturi calibrate juridic (zero propozitii copiate din original) ----

SYSTEM_B = ("Esti editor de stiri. Scopul tau: titlul reda ESENTA faptului, iar rezumatul comprima "
            "faptele de baza, cu cuvintele tale. Concret, nu vag. Raspunzi exclusiv JSON valid.")

USER_B = """Titlu original: {title}
Descriere: {description}

Scrie un titlu si un rezumat care REDAU ESENTA, cu cuvintele tale.
Returneaza JSON:
{{"title": "<esenta faptului: CINE face/pateste CE (si unde/cand daca e cheie); concret si clar; 6-16 cuvinte; fara clickbait, fara formulari vagi precum 'iata ce', 'ce a patit'>",
  "teaser": "<rezumat COMPRIMAT al faptelor de baza in 25-40 de cuvinte: cine, ce, cand, unde, cat/de ce; reformulat 100%, ZERO propozitii copiate din original; trebuie sa transmita esenta fara a citi articolul>",
  "category": "<una din: {cats}>",
  "entities": ["<1-4 nume proprii cheie din stire (persoane, organizatii, locuri), forma scurta canonica, ex. 'Nicusor Dan', 'PSD', 'Timisoara'>"],
  "icon": "<pictograma care surprinde cel mai bine subiectul, UN slug din: {icons}; null daca niciuna nu se potriveste>"}}
Reguli: titlul trebuie sa se inteleaga singur si sa contina faptul real, nu o intrebare/teaser; NU copia nicio propozitie din original; zero opinii; daca descrierea e saraca, extrage esenta din titlul original (tot reformulat)."""

SYSTEM_C = ("Esti editor care sintetizeaza un eveniment din MAI MULTE surse, cu cuvintele tale. "
            "Titlul reda esenta evenimentului; sinteza comprima faptele confirmate. Raspunzi exclusiv JSON valid.")

USER_C = """Eveniment, relatat de surse:
{sources_block}

Scrie titlu + sinteza care REDAU ESENTA evenimentului, cu cuvintele tale.
Returneaza JSON:
{{"title": "<esenta evenimentului: ce s-a intamplat, concret; 6-16 cuvinte; fara clickbait>",
  "synthesis": "<sinteza COMPRIMATA in 40-80 de cuvinte: faptele confirmate de mai multe surse (cine, ce, cand, unde, cat), reformulate 100%; marcheaza daca sursele se contrazic>",
  "category": "<una din: {cats}>",
  "entities": ["<1-4 nume proprii cheie din eveniment (persoane, organizatii, locuri), forma scurta canonica>"],
  "icon": "<pictograma care surprinde cel mai bine evenimentul, UN slug din: {icons}; null daca niciuna nu se potriveste>"}}
Reguli: trianguleaza faptele comune; ZERO propozitii copiate; titlul contine faptul real, nu un teaser; zero opinii."""


SYSTEM_BATCH = ("Esti editor de stiri. Pentru FIECARE stire primita, titlul reda ESENTA faptului, "
                "iar teaserul comprima faptele de baza, cu cuvintele tale. Concret, nu vag. "
                "Raspunzi EXCLUSIV cu un array JSON valid.")

USER_BATCH = """Ai mai multe stiri (fiecare cu un id). Pentru FIECARE, scrie titlu (esenta) + teaser (rezumat comprimat), cu cuvintele tale.

Stiri:
{items_block}

Returneaza EXCLUSIV un array JSON, cate UN obiect per stire, cu acelasi id primit:
[{{"id": <id>, "title": "<esenta faptului: CINE face/pateste CE; concret; 6-16 cuvinte; fara clickbait, fara vag>", "teaser": "<rezumat comprimat 25-40 cuvinte: cine/ce/cand/unde/cat; reformulat 100%, ZERO propozitii copiate>", "category": "<{cats}>", "entities": ["<1-4 nume proprii cheie: persoane, organizatii, locuri>"], "icon": "<UN slug din lista de la final sau null>"}}]
Pictograme permise: {icons}
Reguli: pastreaza id-ul EXACT (numar); un obiect per id; daca stirea e in alta limba, scrie in romana; titlul = faptul real, nu intrebare; zero opinii."""


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


def _resolve_category(item: dict, ai_cat: str) -> str:
    """Categoria finala a unui articol.

    Rubricile GEOGRAFICE (config.PINNED_CATEGORIES, ex. 'local') sunt o axa proprie:
    un articol de la un ziar judetean ramane in sectiunea lui geografica, nu e mutat
    pe axa de TEMA (sport/politic) de catre AI -- altfel sectiunea locala s-ar goli.
    La fetch, item['category'] = categoria sursei, inainte ca AI sa o suprascrie.
    """
    if item.get("category") in getattr(config, "PINNED_CATEGORIES", set()):
        return item["category"]
    return _valid_category(ai_cat, item.get("category", "general"))


_ICON_SLUGS = ("gavel certificate building-monument podium writing percentage receipt-tax "
               "building-bank currency-euro pig-money chart-line building-factory shopping-cart "
               "bolt gas-station tractor swords rocket shield flag plane train car truck "
               "ship helicopter globe compass building-hospital stethoscope vaccine virus pill microscope "
               "satellite robot cpu device-mobile wifi shield-lock database ball-football "
               "ball-tennis ball-basketball swimming bike run medal trophy movie music school "
               "building-church ambulance firetruck crane home umbrella trees speakerphone sun "
               "cloud-storm snowflake flame alert-triangle")
_ICON_SET = set(_ICON_SLUGS.split())

# lista de categorii vine din config (ca {icons}): o rubrica noua adaugata in
# config.CATEGORIES intra automat si in prompturile AI, fara enumerari duplicate
_CATS = "|".join(config.CATEGORIES)

USER_B = USER_B.replace("{icons}", _ICON_SLUGS).replace("{cats}", _CATS)
USER_C = USER_C.replace("{icons}", _ICON_SLUGS).replace("{cats}", _CATS)
USER_BATCH = USER_BATCH.replace("{icons}", _ICON_SLUGS).replace("{cats}", _CATS)


def _clean_icon(raw) -> str | None:
    return raw if isinstance(raw, str) and raw in _ICON_SET else None


def _clean_entities(raw) -> list:
    """Valideaza lista de entitati din raspunsul AI: doar stringuri scurte,
    curatate si deduplicate (case-insensitive), maxim 5."""
    out, seen = [], set()
    for e in (raw or [])[:8]:
        if not isinstance(e, str):
            continue
        e = e.strip().strip(".,;:!?„”\"'")
        if not (2 <= len(e) <= 60) or "<" in e or ">" in e:
            continue
        k = e.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out[:5]


def _parse_json_array(text: str) -> list:
    """Extrage un array JSON din raspuns (tolerant la ```json fences si la wrapping)."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data]
    return []


OFFICIAL_PREFIXES = ("pl_", "cj_", "pr_")


def process_official(items: list) -> list:
    done = []
    for it in items:
        out = process_single(it, None)
        if out is None or out.get("skip"):
            continue
        out["processed_by"] = "official"
        done.append(out)
    return done


def process_batch(items: list, provider) -> list:
    """Model B in LOT: un singur apel AI pentru `items`. Mapeaza raspunsul pe id (= index).
    Returneaza DOAR articolele procesate corect; cele nemapate NU se publica brute
    (regula 'No mangled output') -> raman in afara starii si sunt reluate la rularea urmatoare.
    """
    if not items:
        return []
    if provider is None:                       # fara AI -> fallback determinist per item
        return [process_single(it, provider) for it in items]

    block = "\n".join(
        f"[{i}] Titlu: {it.get('original_title','')} | Descriere: {(it.get('description') or '')[:500]}"
        for i, it in enumerate(items))
    try:
        raw = provider.complete(SYSTEM_BATCH, USER_BATCH.format(items_block=block))
        arr = _parse_json_array(raw)
    except Exception:
        return []                              # tot lotul a esuat -> reluat data viitoare

    by_id = {}
    for obj in arr:
        try:
            by_id[int(obj.get("id"))] = obj
        except (TypeError, ValueError, AttributeError):
            continue

    done = []
    for i, it in enumerate(items):
        obj = by_id.get(i)
        title = (obj.get("title") or "").strip() if isinstance(obj, dict) else ""
        teaser = (obj.get("teaser") or "").strip() if isinstance(obj, dict) else ""
        if title and teaser:
            it["model"] = "B"
            it["title"] = title
            it["teaser"] = truncate_words(teaser, config.TEASER_MAX_WORDS)
            it["category"] = _resolve_category(it, obj.get("category", ""))
            it["entities"] = _clean_entities(obj.get("entities"))
            it["icon"] = _clean_icon(obj.get("icon"))
            it["processed_by"] = provider.name
            it["prompt_version"] = config.PROMPT_VERSION
            done.append(it)
        # nemapat/invalid -> nu il adaugam (reluat la rularea urmatoare)
    return done


OFFICIAL_PREFIXES = ("pl_", "cj_", "pr_")


def process_official(items: list) -> list:
    """Surse oficiale (primarii/CJ): fara AI. Titlu original + teaser trunchiat
    (fallback determinist), marcate 'official' ca sa nu fie reluate de
    upgrade_fallbacks."""
    done = []
    for it in items:
        out = process_single(it, None)
        if out is None or out.get("skip"):
            continue
        out["processed_by"] = "official"
        done.append(out)
    return done


def process_single(item: dict, provider) -> dict | None:
    """Model B. Modifica item-ul pe loc: title/teaser/category/model/processed_by.

    Daca providerul exista dar apelul AI esueaza, returneaza None FARA a atinge
    item-ul: nu se publica brut, ci ramane neschimbat si se reia data viitoare
    (regula 'No mangled output'). Doar fara cheie (provider None) se face fallback.
    """
    if provider is None:
        item["model"] = "B"
        if item.get("source_lang") == "en":
            item["skip"] = True
            return item
        item["title"] = item.get("original_title", "")
        item["teaser"] = truncate_words(item.get("description") or "Detalii pe sursa.",
                                        config.TEASER_MAX_WORDS)
        item["processed_by"] = "fallback"
        return item
    try:
        raw = provider.complete(SYSTEM_B, USER_B.format(
            title=item.get("original_title", ""), description=item.get("description", "")))
        data = _parse_json(raw)
    except Exception:
        return None                            # esec AI -> amanat, item-ul ramane intact
    item["model"] = "B"
    item["title"] = (data.get("title") or item.get("original_title", "")).strip()
    item["teaser"] = truncate_words(data.get("teaser", "") or "Detalii pe sursa.",
                                    config.TEASER_MAX_WORDS)
    item["category"] = _resolve_category(item, data.get("category", ""))
    item["entities"] = _clean_entities(data.get("entities"))
    item["icon"] = _clean_icon(data.get("icon"))
    item["processed_by"] = provider.name
    item["prompt_version"] = config.PROMPT_VERSION
    return item


def process_cluster(group: list, provider) -> dict | None:
    """Model C. Returneaza un articol-reprezentant cu sinteza + lista de surse.

    Daca providerul exista dar apelul AI esueaza (429/503/etc.), returneaza None:
    item-ul NU se publica brut, ci se reia la rularea urmatoare (regula 'No mangled
    output'). Doar in modul fara cheie (provider None) se face fallback determinist.
    """
    # ordine cronologica: cine a publicat primul deschide lista (scor de originalitate)
    group = sorted(group, key=lambda a: a.get("published") or "")
    rep = dict(group[0])
    rep["model"] = "C"
    # dedup dupa domeniu, nu dupa nume: 2 feed-uri RSS ale aceluiasi site
    # (ex. "Digi24" si "Digi24 Extern") nu sunt 2 surse independente
    _seen_domain = set()
    rep["sources"] = [
        {"name": a["source_name"], "url": a["original_link"]}
        for a in group
        if domain_of(a["original_link"]) not in _seen_domain and not _seen_domain.add(domain_of(a["original_link"]))
    ]
    rep["first_source"] = group[0]["source_name"]

    if provider is None:
        if rep.get("source_lang") == "en":
            rep["skip"] = True
            return rep
        rep["title"] = rep.get("original_title", "")
        rep["synthesis"] = truncate_words(rep.get("description") or "Detalii pe surse.",
                                          config.SYNTHESIS_MAX_WORDS)
        rep["processed_by"] = "fallback"
        return rep

    # membrii deja procesati (scrubbed) nu mai au textul original -> folosim versiunea AI
    block = "\n".join(
        f"- {a['source_name']}: {a.get('original_title') or a.get('title') or ''}"
        f" - {a.get('description') or a.get('teaser') or ''}"
        for a in group)
    try:
        raw = provider.complete(SYSTEM_C, USER_C.format(sources_block=block))
        data = _parse_json(raw)
        rep["title"] = (data.get("title") or rep.get("original_title", "")).strip()
        rep["synthesis"] = truncate_words(data.get("synthesis", "") or "Detalii pe surse.",
                                          config.SYNTHESIS_MAX_WORDS)
        rep["category"] = _resolve_category(rep, data.get("category", ""))
        rep["entities"] = _clean_entities(data.get("entities"))
        rep["icon"] = _clean_icon(data.get("icon"))
        rep["processed_by"] = provider.name
        rep["prompt_version"] = config.PROMPT_VERSION
    except Exception:
        return None                            # esec AI -> amanat, reluat data viitoare
    return rep
