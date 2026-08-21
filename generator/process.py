"""AI: modelul B (teaser pe articol) si modelul C (sinteza pe cluster).

Apararea in adancime: chiar daca AI depaseste limita sau pica, codul taie la
TEASER_MAX_WORDS / SYNTHESIS_MAX_WORDS si are fallback determinist (fara AI).
"""
import json
import re
from datetime import datetime, timezone

from . import config, geo, raport_copiere
from .util import truncate_words, domain_of, strip_diacritics

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
Reguli: SCRIE IN ROMANA — daca stirea primita e in alta limba, tradu-o, nu o reda in original; titlul trebuie sa se inteleaga singur si sa contina faptul real, nu o intrebare/teaser; NU copia nicio propozitie din original; zero opinii; foloseste DOAR fapte prezente in textul primit — daca un fapt (cine, unde, cand) nu apare acolo, nu-l inventa si nu-l inlocui cu o formulare vaga."""

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
Reguli: SCRIE IN ROMANA — daca sursele sunt in alta limba, tradu; trianguleaza faptele comune; ZERO propozitii copiate; titlul contine faptul real, nu un teaser; zero opinii. Verifica semantic fiecare verb: nu transforma „au pretins”, „s-au dat drept” sau „au oprit” într-un verb de percepție precum „au simțit”; dacă sursele spun că suspecții s-au dat drept polițiști, formulează explicit acest fapt."""


SYSTEM_C_BATCH = ("Esti editor care sintetizeaza MAI MULTE evenimente, fiecare din mai multe surse, "
                   "cu cuvintele tale. Titlul reda esenta evenimentului; sinteza comprima faptele "
                   "confirmate. Raspunzi EXCLUSIV cu un array JSON valid.")

USER_C_BATCH = """Ai mai multe evenimente (fiecare cu un id), fiecare relatat de mai multe surse.

Evenimente:
{events_block}

Pentru FIECARE eveniment, scrie titlu + sinteza care REDAU ESENTA, cu cuvintele tale.
Returneaza EXCLUSIV un array JSON, cate UN obiect per eveniment, cu acelasi id primit:
[{{"id": <id>, "title": "<esenta evenimentului: ce s-a intamplat, concret; 6-16 cuvinte; fara clickbait>", "synthesis": "<sinteza COMPRIMATA in 40-80 de cuvinte: faptele confirmate de mai multe surse (cine, ce, cand, unde, cat), reformulate 100%; marcheaza daca sursele se contrazic>", "category": "<{cats}>", "entities": ["<1-4 nume proprii cheie din eveniment>"], "icon": "<UN slug din lista de la final sau null>"}}]
Pictograme permise: {icons}
Reguli: SCRIE IN ROMANA — daca sursele sunt in alta limba, tradu; pastreaza id-ul EXACT (numar); un obiect per id; trianguleaza faptele comune DOAR din sursele evenimentului cu acelasi id -- NU amesteca fapte intre evenimente diferite, chiar daca par legate; ZERO propozitii copiate; titlul contine faptul real, nu un teaser; zero opinii. Verifica semantic verbele: nu transforma „au pretins”, „s-au dat drept” sau „au oprit” în „au simțit”; când sursele descriu o identitate falsă, scrie explicit „s-au dat drept polițiști”."""


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
    """Returneaza providerul cerut, cu Ollama local ca fallback AUTOMAT daca AI_PROVIDER e
    gemini/anthropic (nu invers: Ollama ramane doar completare, cloud-ul e mereu incercat intai).

    De ce: fara asta, un 429 (quota Gemini epuizata) sau o cheie lipsa amana articolul complet
    (regula 'No mangled output') -- desi un model local, gratuit, sta pornit pe masina si ar
    putea totusi sa-i scrie titlul. Cascada (`CascadeProvider`) incearca Ollama DOAR cand
    cloud-ul esueaza propriu-zis, deci nu schimba nimic cand cloud-ul merge normal.
    In CI (GitHub Actions) Ollama nu ruleaza -> `available()` cade rapid pe conexiune refuzata,
    cascada devine efectiv providerul cloud singur, comportament neschimbat fata de inainte.
    """
    if config.AI_PROVIDER == "anthropic":
        from .providers.anthropic import AnthropicProvider
        primary = AnthropicProvider()
    elif config.AI_PROVIDER == "ollama":
        from .providers.ollama import OllamaProvider
        p = OllamaProvider()
        return p if p.available() else None
    else:
        from .providers.gemini import GeminiProvider
        primary = GeminiProvider()

    providers = [primary]
    if config.AI_ROUTER_MODE == "multi":
        from .providers.openai_compat import configured_compatible_providers
        providers.extend(configured_compatible_providers())
    if config.AI_FALLBACK_OLLAMA:
        from .providers.ollama import OllamaProvider
        providers.append(OllamaProvider())

    # Pastreaza ordinea si elimina duplicatele de nume, pentru ca un provider
    # configurat accidental de doua ori sa nu primeasca acelasi articol de doua ori.
    unique = []
    seen = set()
    for provider in providers:
        if provider.name not in seen:
            unique.append(provider)
            seen.add(provider.name)
    available = [p for p in unique if p.available()]
    if not available:
        return None
    if len(available) == 1:
        return available[0]
    from .providers.cascade import CascadeProvider
    return CascadeProvider(available)


# Contextul afirmă explicit o identitate falsă. Lista e deliberat scurtă și concretă: una vagă
# ar potrivi și știri obișnuite despre declarații.
_IDENTITY_CLAIM_MARKERS = (
    "s-au dat drept", "s au dat drept", "au pretins ca sunt", "au pretins ca",
    "pretindeau ca sunt", "falsificandu-si identitatea",
)

# Degradarea semantică observată: modelul transformă „s-au dat drept / au pretins” în „au simțit”.
_DEGRADARE_RE = re.compile(r"\bau\s+simtit\b")


def _revendica_identitate(context: str) -> bool:
    return any(m in strip_diacritics(context or "").lower() for m in _IDENTITY_CLAIM_MARKERS)


def _repair_synthesis_title(title: str, context: str) -> str:
    """Repară deformarea semantică observată în titlurile sintetizate.

    Modelul confundă uneori „au pretins/s-au dat drept” cu „au simțit”. Regula este
    intenționat îngustă: intervenim numai când contextul confirmă explicit identitatea
    falsă și păstrăm restul titlului neschimbat.

    Reparația acoperă UN caz — „au simțit polițiști". Pentru restul clasei există garda
    `_titlu_sustinut_de_context`, care rulează DUPĂ asta.
    """
    if not isinstance(title, str):
        return ""
    if _revendica_identitate(context) and "au simtit politisti" in strip_diacritics(title).lower():
        return re.sub(r"au simțit polițiști", "s-au dat drept polițiști", title, flags=re.IGNORECASE)

    return title.strip()


def _titlu_sustinut_de_context(title: str, context: str) -> bool:
    """Titlul mai e compatibil cu ce spun sursele, DUPĂ ce s-a încercat reparația?

    Recuperată din `7ee576db` (Manus AI, 2026-08-19), commit care nu a ajuns în `main`: acolo
    exista garda, aici supraviețuise doar lista de markeri. Auditul din 2026-08-20 a semnalat
    ([C4]) că reparația de mai sus tratează UN caz dintr-o CLASĂ — orice altă formulare a
    aceleiași deformări trecea nereparată și nesemnalată.

    Cele două sunt complementare, nu concurente, și de-aia rulează în ordinea asta:
    reparația salvează titlul când poate (nu pierdem articolul), garda îl respinge când nu poate.
    Un candidat respins NU se publică — clusterul rămâne pentru o reîncercare, conform regulii
    „No mangled output". Costul e un apel AI în plus; alternativa e o formulare plauzibilă și
    falsă pe site.

    Deliberat îngustă și deterministă: nu pretinde fact-checking general și nu introduce o a
    doua judecată AI în calea critică de publicare.
    """
    if not isinstance(title, str) or not title.strip():
        return False
    if not _revendica_identitate(context):
        return True
    return not _DEGRADARE_RE.search(strip_diacritics(title).lower())


def _marcheaza_fallback(item: dict) -> None:
    """Marcheaza itemul ca `fallback` DOAR daca textul pastrat vine de la sursa, nu de la model.

    De ce nu e o simpla atribuire (audit 2026-08-20, [C1]): pe calea fara provider, apelantii
    scriu `title = original_title or title` si `synthesis = description or synthesis`. Pe un item
    PROASPAT ambele campuri originale exista, deci textul e al sursei si `fallback` e corect.
    Pe un reprezentant DEJA PUBLICAT insa, `state._scrub_processed` a sters `original_title` si
    `description` (drept de autor, L8/1996), deci expresiile de mai sus pastreaza titlul si
    sinteza SCRISE DE MODEL — iar `render.py` calculeaza `ai_generat` ca
    `processed_by not in ("official", "fallback")`. Degradarea la `fallback` ar sterge marcajul
    de continut generat de AI, obligatoriu prin AI Act art. 50(4), de pe text scris de AI.

    `original_title` e martorul: prezent -> textul e al sursei; absent -> a fost scrub-uit dupa o
    procesare AI, deci fluxul anterior se pastreaza. Cand nu exista niciun flux anterior, campul
    ramane nesetat si `ai_generat` iese True — directia sigura, aceeasi cu
    `tests/test_marcaj_ai.py::test_articolele_vechi_fara_flux_se_marcheaza`.
    """
    if item.get("original_title"):
        item["processed_by"] = "fallback"


def _parse_json(text: str) -> dict:
    """Extrage primul obiect JSON din raspuns (tolerant la ```json fences si la
    wrapping in lista — Gemini 3.x intoarce uneori [{...}] in loc de {...})."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    data = None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    if isinstance(data, list):
        data = next((x for x in data if isinstance(x, dict)), None)
    return data if isinstance(data, dict) else {}


def _valid_category(cat: str, fallback: str) -> str:
    return cat if cat in config.CATEGORIES else fallback


def _text_clasificabil(item: dict) -> str:
    """Modelul B scrie 'teaser', modelul C scrie 'synthesis' — le luam pe amandoua, altfel
    clusterele s-ar clasifica doar dupa titlu."""
    return " ".join(filter(None, (item.get("title"), item.get("teaser"), item.get("synthesis"))))


def _locul_e_subiectul(item: dict, entities, judet) -> bool:
    """Stirea e DESPRE locul pe care textul il numeste, sau doar il mentioneaza?

    Doua trepte, si amandoua sunt masurate pe corpus (2704 articole, 2026-08-07), nu alese
    din intuitie:

    1. **Titlul numeste locul -> da, fara alta verificare.** Asa functioneaza titlurile: ele
       numesc subiectul. Masurat, compartimentul asta are 3 din 30 gresite (10%), fata de
       16 din 30 (53%) cand locul apare doar in corp — de 5 ori mai curat.

    2. **Altfel, cerem coroborare din `entities`** — lista pe care modelul o produce ca
       „1-4 nume proprii CHEIE din stire". Aia e judecata „despre ce e stirea", nu „ce
       cuvinte contine". Pe cele 30 de articole judecate manual din compartimentul 2:
       `kills_wrong = 13 din 18`, `kills_right = 2 din 12`. Raport 6,5:1.

    De ce NU se aplica treapta 2 si peste titluri, desi ar parea mai simplu: masurat, ar taia
    152 de articole din compartimentul 1, si aproape toate sunt CORECTE — locul e inghitit in
    numele institutiei („Muzeul de Arta Populara Constanta", „Salvamont Suceava", „Jandarmeria
    Maramures"), deci potrivirea exacta il rateaza. Compartimentul 1 are 10% eroare; nu-l
    reparam cu o regula care ii strica 20%.

    Varianta laxa (locul ca SUBSIR intr-o entitate) a fost incercata si e MAI PROASTA acolo
    unde conteaza: `kills_wrong` scade de la 13 la 9, iar `kills_right` ramane 2 — recupereaza
    „Curtea de Apel Bucuresti" (stire nationala) fara sa recupereze nimic corect.

    Fara entitati -> `True`. Filtrul nu are cu ce corobora, iar un filtru fara date nu sterge.
    """
    if geo.clasifica(item.get("title") or "", judet):
        return True
    if not entities:
        return True
    numite = geo.locuri_numite(_text_clasificabil(item))
    ent = {strip_diacritics(e).upper().strip() for e in entities if e}
    return bool(numite & ent)


def _resolve_category(item: dict, ai_cat: str, entities=None) -> str:
    """Categoria finala a unui articol.

    LOCAL inseamna UNDE se intampla, nu CINE publica (regula owner 2026-08-02). O rubrica
    geografica (`regional|judetean|local`) se decide din TEXTUL stirii, cu gazetteer-ul, la orice
    sursa -- inclusiv un ziar judetean. Un ziar de Cluj care scrie despre o comuna anume ajunge
    `local`, unul care scrie cursul BNR pleaca de pe axa geografica pe tema lui. Nu ne mai luam
    dupa categoria sursei: acopera si cazul in care AI-ul alege gresit o rubrica geografica
    (masurat 2026-07-25: 14 din 15 din `regional` erau gresite -- un sat elvetian, CE, DNA)
    SI cazul in care sursa e geografica dar stirea concreta nu e despre locul ei.
    """
    # Judetul sursei deschide potrivirea pe SATE, si numai pe ale lui. La sursele nationale e
    # None, deci pentru ele nimic nu se schimba — vezi geo._SATE pentru de ce conteaza asta.
    judet = geo.judet_sursa(item.get("source"))
    nivel = geo.clasifica(_text_clasificabil(item), judet)
    # Sportul NU intra pe axa geografica, chiar cand textul numeste locul. Nu e o exceptie de
    # la regula proprietarului, e regula lui aplicata corect: un meci se joaca undeva, dar
    # stirea nu e DESPRE locul ala. Numele clubului poarta numele orasului („Farul Constanta",
    # „Universitatea Cluj", „CFR Cluj"), iar gazetteer-ul nu are cum sa deosebeasca echipa de
    # oras — asta e o judecata de TEMA, si singurul care o are e modelul.
    #
    # Conventia e verificata pe patru site-uri comparabile (2026-08-07), nu dedusa:
    #   adevarul.ro/stiri-locale/constanta  0 stiri de sport din 33 — Farul lipseste complet
    #   adevarul.ro/stiri-locale/cluj-napoca 1 din 33, si aia „meciul schimba traseul
    #                                        autobuzelor", adica despre transport, nu meci
    #   digi24.ro/regional                  0 in snapshot
    #   monitorulcj.ro (ziar LOCAL din Cluj) sectiune `Sport` separata; „CFR pierde cu 0-5"
    #                                        e acolo, nu la Administratie
    # Linia lor e mai fina decat „sportul nu e local": meciul e Sport, dar devine local cand
    # SUBIECTUL e impactul local. Cazul ala se rezolva singur aici — la o stire despre autobuze
    # modelul nu alege `sport`, deci `nivel` ramane si articolul ramane local.
    #
    # Semnalul e tema POVESTII (`ai_cat`), nu categoria SURSEI — pe aia proprietarul a respins-o
    # explicit pe 2026-08-02, si masurat ar fi si gresita: din 159 de articole cu iconita de
    # sport aflate azi pe axa geografica, 63 (40%) vin din ziare locale, nu din presa sportiva.
    # O regula pe sursa le-ar rata pe toate.
    #
    # A treia conditie, `_locul_e_subiectul`: textul numeste locul, dar e stirea DESPRE el?
    # „Fitch mentine ratingul Romaniei" publicat de un ziar din Brasov numeste Bucurestiul si
    # nu e o stire brasoveana. Vezi acolo cifrele si de ce regula are doua trepte.
    if nivel and ai_cat != "sport" and _locul_e_subiectul(item, entities, judet):
        return nivel   # textul numeste un loc SI stirea e despre el -> axa geografica

    # Niciun nume de loc -> stirea nu apartine axei geografice. Cade pe rubrica de TEMA aleasa
    # de AI; daca si aceea e geografica (deci negasita in text), e nesigura -> `general`.
    cat = _valid_category(ai_cat, item.get("category", "general"))
    return cat if cat not in getattr(config, "PINNED_CATEGORIES", set()) else "general"


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
USER_C_BATCH = USER_C_BATCH.replace("{icons}", _ICON_SLUGS).replace("{cats}", _CATS)
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


def _lexical_tokens(text: str) -> set[str]:
    """Return normalized content tokens for a conservative cross-item comparison."""
    return {
        strip_diacritics(token).lower()
        for token in re.findall(r"[A-Za-zĂÂÎȘȚăâîșț0-9]{3,}", text or "")
    }


def _uppercase_anchors(text: str) -> set[str]:
    """Return distinctive all-caps anchors such as PESA, not ordinary sentence words."""
    return {
        token.lower()
        for token in re.findall(r"(?<![A-Za-zĂÂÎȘȚăâîșț])[A-ZĂÂÎȘȚ]{2,}(?![A-Za-zĂÂÎȘȚ])", text or "")
        if len(token) >= 3
    }


def _cross_item_contamination(candidate: str, own_source: str, peer_sources: list[str]) -> bool:
    """Reject a batch candidate whose distinctive facts belong to another item.

    This is deliberately conservative: it requires both several shared lexical anchors
    with a peer and a substantially better peer match than the candidate's own source.
    The all-caps anchor check catches the observed ``PESA`` leak without asking another
    model to judge its own output.
    """
    candidate_tokens = _lexical_tokens(candidate)
    own_tokens = _lexical_tokens(own_source)
    if len(candidate_tokens) < 5 or not peer_sources:
        return False
    own_overlap = len(candidate_tokens & own_tokens)
    own_score = own_overlap / len(candidate_tokens)
    candidate_anchors = _uppercase_anchors(candidate)
    own_anchors = _uppercase_anchors(own_source)
    for peer_source in peer_sources:
        peer_tokens = _lexical_tokens(peer_source)
        peer_overlap = candidate_tokens & peer_tokens
        peer_score = len(peer_overlap) / len(candidate_tokens)
        peer_anchors = _uppercase_anchors(peer_source)
        foreign_anchor = (candidate_anchors - own_anchors) & peer_anchors
        if foreign_anchor and len(peer_overlap) >= 3 and peer_score >= max(0.20, own_score + 0.08):
            return True
        if len(peer_overlap) >= 5 and peer_score >= 0.32 and peer_score >= own_score + 0.18:
            return True
    return False


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
    source_texts = [
        " ".join((it.get("original_title", ""), it.get("description", "")))
        for it in items
    ]
    for i, it in enumerate(items):
        obj = by_id.get(i)
        title = (obj.get("title") or "").strip() if isinstance(obj, dict) else ""
        teaser = (obj.get("teaser") or "").strip() if isinstance(obj, dict) else ""
        if title and teaser:
            candidate = f"{title} {teaser}"
            peers = source_texts[:i] + source_texts[i + 1:]
            if _cross_item_contamination(candidate, source_texts[i], peers):
                # Nu publicăm un candidat care pare să fi împrumutat fapte din alt
                # articol al aceluiași lot; itemul va fi reluat la rularea următoare.
                continue
            it["model"] = "B"
            it["title"] = title
            it["teaser"] = truncate_words(teaser, config.TEASER_MAX_WORDS)
            # entitatile INAINTEA categoriei: `_resolve_category` le foloseste ca sa verifice
            # daca locul numit in text e chiar subiectul stirii. Ordinea inversa le-ar fi dat
            # `None` si coroborarea ar fi cazut tacut pe fail-open.
            it["entities"] = _clean_entities(obj.get("entities"))
            # `ai_cat` = tema BRUTA aleasa de model, pastrata langa categoria rezolvata.
            # Fara ea, `_resolve_category` isi consuma intrarea si o arunca, deci nicio
            # schimbare de clasificare nu se poate rejuca pe corpus fara apeluri AI noi —
            # exact limitarea consemnata in registru la WS-0026 („nemasurabil retroactiv").
            # `entities` se salva deja, si fix de-aia #156 a putut fi masurat pe 1075 de
            # articole; asta e cealalta jumatate a intrarii lui `_resolve_category`.
            # Se scrie NEATINSA (fara strip/normalizare): valoarea care ajunge in fisier
            # trebuie sa fie identica cu cea primita de functie, altfel rejucarea minte.
            it["ai_cat"] = obj.get("category", "")
            it["category"] = _resolve_category(it, it["ai_cat"], it["entities"])
            it["icon"] = _clean_icon(obj.get("icon"))
            it["processed_by"] = provider.name
            it["prompt_version"] = config.PROMPT_VERSION
            # §2.2 (drept de autor): masoara cat din rezumat e copiat din sursa. Doar
            # noteaza intr-un jurnal; nu respinge nimic si nu poate ridica exceptii.
            raport_copiere.noteaza("B", it.get("original_link"), it["title"],
                                   it["teaser"], source_texts[i])
            done.append(it)
        # nemapat/invalid -> nu il adaugam (reluat la rularea urmatoare)
    return done


def process_single(item: dict, provider) -> dict | None:
    """Model B. Modifica item-ul pe loc: title/teaser/category/model/processed_by.

    Daca providerul exista dar apelul AI esueaza, returneaza None FARA a atinge
    item-ul: nu se publica brut, ci ramane neschimbat si se reia data viitoare
    (regula 'No mangled output'). Doar fara cheie (provider None) se face fallback.
    """
    if provider is None:
        item["model"] = "B"
        # Orice sursa care NU e in romana: fara provider AI nu exista cine sa traduca, deci
        # itemul se sare, nu se publica in limba originala. Testul era cablat pe "en" si
        # lasa sa treaca brut orice alta limba (it/de/fr) — vezi `lang` din config.SOURCES.
        if (item.get("source_lang") or "ro") != "ro":
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
    item["entities"] = _clean_entities(data.get("entities"))   # inaintea categoriei, vezi mai sus
    item["ai_cat"] = data.get("category", "")                  # tema bruta, vezi process_batch
    item["category"] = _resolve_category(item, item["ai_cat"], item["entities"])
    item["icon"] = _clean_icon(data.get("icon"))
    item["processed_by"] = provider.name
    item["prompt_version"] = config.PROMPT_VERSION
    raport_copiere.noteaza("B", item.get("original_link"), item["title"], item["teaser"],
                           f"{item.get('original_title', '')} {item.get('description', '')}")
    return item


def process_cluster(group: list, provider) -> dict | None:
    """Model C. Returneaza un articol-reprezentant cu sinteza + lista de surse.

    Daca providerul exista dar apelul AI esueaza (429/503/etc.), returneaza None:
    item-ul NU se publica brut, ci se reia la rularea urmatoare (regula 'No mangled
    output'). Doar in modul fara cheie (provider None) se face fallback determinist.
    """
    # Reprezentantul: un membru DEJA PUBLICAT daca grupul contine unul, altfel cel mai vechi.
    # Un cluster poate absorbi o stire din stare (`cluster.attach_recent`), iar de la IZZ-0151
    # inclusiv o sinteza C — si atunci url-ul aceluia e permalink-ul public deja indexat. Daca
    # rep-ul ar fi un item nou doar fiindca a aparut cu un minut mai devreme, pagina publicata
    # ar fi inlocuita cu alta. `processed_by` e marcajul: itemele proaspat citite nu-l au.
    # In interiorul fiecarei clase ordinea ramane cronologica: cine a publicat primul deschide
    # lista de surse (scor de originalitate).
    group = sorted(group, key=lambda a: (not a.get("processed_by"), a.get("published") or ""))
    actualizare = bool(group[0].get("processed_by"))
    rep = dict(group[0])
    rep["model"] = "C"
    # dedup dupa domeniu, nu dupa nume: 2 feed-uri RSS ale aceluiasi site
    # (ex. "Digi24" si "Digi24 Extern") nu sunt 2 surse independente.
    # Un membru poate fi el insusi o sinteza, cu mai multe surse: se preiau TOATE ale lui,
    # altfel coroborarea deja publicata s-ar reduce la un singur link la prima actualizare.
    _seen_domain = set()
    surse = []
    for a in group:
        for s in (a.get("sources")
                  or [{"name": a.get("source_name"), "url": a.get("original_link")}]):
            dom = domain_of(s.get("url") or "")
            if dom in _seen_domain:
                continue
            _seen_domain.add(dom)
            surse.append({"name": s.get("name"), "url": s.get("url")})
    rep["sources"] = surse
    rep["first_source"] = group[0].get("source_name")
    if actualizare:
        # acelasi permalink, alt continut -> `dateModified` din JSON-LD trebuie sa spuna asta
        rep["updated"] = datetime.now(timezone.utc).isoformat()

    if provider is None:
        if (rep.get("source_lang") or "ro") != "ro":
            rep["skip"] = True
            return rep
        # `original_title` lipseste de pe membrii deja publicati (scrub juridic); pe calea fara
        # cheie, un rep publicat ar ramane altfel cu titlu gol — exact „mangled output"-ul
        # interzis de §7. Titlul deja publicat e cea mai buna aproximare disponibila aici.
        rep["title"] = rep.get("original_title") or rep.get("title") or ""
        rep["synthesis"] = truncate_words(
            rep.get("description") or rep.get("synthesis") or "Detalii pe surse.",
            config.SYNTHESIS_MAX_WORDS)
        _marcheaza_fallback(rep)
        return rep

    # membrii deja procesati (scrubbed) nu mai au textul original -> folosim versiunea AI
    block = "\n".join(
        f"- {a['source_name']}: {a.get('original_title') or a.get('title') or ''}"
        f" - {a.get('description') or a.get('teaser') or ''}"
        for a in group)
    try:
        raw = provider.complete(SYSTEM_C, USER_C.format(sources_block=block))
        data = _parse_json(raw)
        context = " ".join(
            f"{a.get('original_title') or a.get('title') or ''} "
            f"{a.get('description') or a.get('teaser') or a.get('synthesis') or ''}"
            for a in group
        )
        candidat = _repair_synthesis_title(
            data.get("title") or rep.get("original_title") or rep.get("title") or "",
            context,
        )
        if not _titlu_sustinut_de_context(candidat, context):
            return None                        # deformare semantica -> amanat, ca la esecul AI
        rep["title"] = candidat
        rep["synthesis"] = truncate_words(data.get("synthesis", "") or "Detalii pe surse.",
                                          config.SYNTHESIS_MAX_WORDS)
        rep["entities"] = _clean_entities(data.get("entities"))   # inaintea categoriei, vezi mai sus
        rep["ai_cat"] = data.get("category", "")                  # tema bruta, vezi process_batch
        rep["category"] = _resolve_category(rep, rep["ai_cat"], rep["entities"])
        rep["icon"] = _clean_icon(data.get("icon"))
        rep["processed_by"] = provider.name
        rep["prompt_version"] = config.PROMPT_VERSION
        raport_copiere.noteaza("C", rep.get("original_link"), rep["title"],
                               rep["synthesis"], block)
    except Exception:
        return None                            # esec AI -> amanat, reluat data viitoare
    return rep


def _prep_cluster_rep(group: list) -> tuple:
    """Partea din process_cluster care NU cere AI: alege reprezentantul, aduna sursele,
    marcheaza actualizarea. Extrasa ca sa fie identica intre calea single (process_cluster)
    si cea in lot (process_clusters_batch) -- doua copii ale conditiei „cine e rep-ul" s-ar
    putea departe fara sa para stricat nimic, acelasi risc numit la `upgradable()` mai sus."""
    group = sorted(group, key=lambda a: (not a.get("processed_by"), a.get("published") or ""))
    actualizare = bool(group[0].get("processed_by"))
    rep = dict(group[0])
    rep["model"] = "C"
    _seen_domain = set()
    surse = []
    for a in group:
        for s in (a.get("sources")
                  or [{"name": a.get("source_name"), "url": a.get("original_link")}]):
            dom = domain_of(s.get("url") or "")
            if dom in _seen_domain:
                continue
            _seen_domain.add(dom)
            surse.append({"name": s.get("name"), "url": s.get("url")})
    rep["sources"] = surse
    rep["first_source"] = group[0].get("source_name")
    if actualizare:
        rep["updated"] = datetime.now(timezone.utc).isoformat()
    return group, rep


def process_clusters_batch(groups: list, provider) -> list:
    """Model C in LOT: UN apel AI pentru mai multe clustere deodata, in loc de unul per
    cluster (vezi config.CLUSTER_BATCH_SIZE pentru motiv si cifre masurate).

    Returneaza o lista ALINIATA cu `groups` (acelasi index): None acolo unde un cluster
    n-a fost mapat in raspuns sau tot apelul a esuat -- la fel ca la `process_cluster`
    singur, clusterul nemapat NU se publica brut, ramane neschimbat, reluat la rularea
    urmatoare (regula 'No mangled output'). Esecul NU e tacut: fiecare None intra direct
    in cifra "Amanate (buget AI epuizat)" din sumarul rularii (main.py) -- masurabil,
    exact cifra urmarita in specs/STATE.md la decizia de batching.
    """
    if not groups:
        return []
    preps = [_prep_cluster_rep(g) for g in groups]

    if provider is None:
        out = []
        for _, rep in preps:
            if (rep.get("source_lang") or "ro") != "ro":
                rep["skip"] = True
                out.append(rep)
                continue
            rep["title"] = rep.get("original_title") or rep.get("title") or ""
            rep["synthesis"] = truncate_words(
                rep.get("description") or rep.get("synthesis") or "Detalii pe surse.",
                config.SYNTHESIS_MAX_WORDS)
            _marcheaza_fallback(rep)
            out.append(rep)
        return out

    # membrii deja procesati (scrubbed) nu mai au textul original -> folosim versiunea AI,
    # exact ca in process_cluster. Fiecare eveniment e un bloc separat, cu id -- gardat
    # explicit in prompt ca sursele unui id sa nu se amestece cu alt id.
    events_block = "\n\n".join(
        f"[{i}] " + " | ".join(
            f"{a['source_name']}: {a.get('original_title') or a.get('title') or ''}"
            f" - {a.get('description') or a.get('teaser') or ''}"
            for a in group)
        for i, (group, _) in enumerate(preps))
    try:
        raw = provider.complete(SYSTEM_C_BATCH, USER_C_BATCH.format(events_block=events_block))
        arr = _parse_json_array(raw)
    except Exception:
        return [None] * len(preps)             # tot lotul a esuat -> reluat data viitoare (vezi docstring)

    by_id = {}
    for obj in arr:
        try:
            by_id[int(obj.get("id"))] = obj
        except (TypeError, ValueError, AttributeError):
            continue

    out = []
    for i, (_, rep) in enumerate(preps):
        obj = by_id.get(i)
        title = (obj.get("title") or "").strip() if isinstance(obj, dict) else ""
        synthesis = (obj.get("synthesis") or "").strip() if isinstance(obj, dict) else ""
        if not (title and synthesis):
            out.append(None)                   # nemapat -> amanat, ca la esecul unui apel singur
            continue
        context = " ".join(
            f"{a.get('original_title') or a.get('title') or ''} "
            f"{a.get('description') or a.get('teaser') or a.get('synthesis') or ''}"
            for a in preps[i][0]
        )
        candidat = _repair_synthesis_title(title, context)
        if not _titlu_sustinut_de_context(candidat, context):
            out.append(None)                   # deformare semantica -> amanat, ca la nemapat
            continue
        rep["title"] = candidat
        rep["synthesis"] = truncate_words(synthesis, config.SYNTHESIS_MAX_WORDS)
        rep["entities"] = _clean_entities(obj.get("entities"))
        rep["ai_cat"] = obj.get("category", "")
        rep["category"] = _resolve_category(rep, rep["ai_cat"], rep["entities"])
        rep["icon"] = _clean_icon(obj.get("icon"))
        rep["processed_by"] = provider.name
        rep["prompt_version"] = config.PROMPT_VERSION
        raport_copiere.noteaza("C", rep.get("original_link"), rep["title"],
                               rep["synthesis"], context)
        out.append(rep)
    return out
