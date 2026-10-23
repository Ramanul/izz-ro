"""AI: modelul B (teaser pe articol) si modelul C (sinteza pe cluster).

Apararea in adancime: chiar daca AI depaseste limita sau pica, codul taie la
TEASER_MAX_WORDS / SYNTHESIS_MAX_WORDS si are fallback determinist (fara AI).
"""
import hashlib
import json
import re
from datetime import datetime, timezone

from . import config, dialectic, fetch_deep, geo, raport_copiere
from . import diacritice
from .verifica_sinteza import cifre_straine, slug_din_link, titlu_copiat
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

# E2 — sinteza dialectică (specs/plan-paradigma-izz.md §3 E2, §5). Modelul PROPUNE structura;
# `generator/dialectic.py` verifică fiecare citare și decide ce rămâne. De aceea regulile de mai
# jos nu sunt singura apărare: o regulă încălcată aici e o afirmație respinsă acolo.
SYSTEM_C_DIALECTIC = ("Esti grefier de stiri. Din propozitiile numerotate ale mai multor publicatii "
                      "extragi ce confirma ele impreuna, unde difera si ce apare intr-o singura "
                      "publicatie. Nu judeci, nu mediezi, nu completezi din cunostintele tale. "
                      "Raspunzi EXCLUSIV cu un array JSON valid.")

USER_C_DIALECTIC = """Ai mai multe evenimente, fiecare cu un id. Pentru fiecare primesti propozitiile publicatiilor:
[S<n>] = antetul publicatiei n; [S<n>.<k>] = propozitia k a ei. Numerele surselor sunt UNICE in tot mesajul: fiecare eticheta apartine unui singur eveniment.
[P<id>.<k>] = fapt din versiunea anterioara a sintezei evenimentului <id>, cu publicatiile lui intre paranteze.

Evenimente:
{events_block}

Returneaza EXCLUSIV un array JSON, cate UN obiect per eveniment, cu acelasi id:
[{{"id": <id>,
  "title": "<faptul central, 6-16 cuvinte, strict factual, cu cuvintele tale; la ASSUMED_SILENCE: doar subiectul, fara afirmatie>",
  "epistemic_state": "SYNTHESIS_VALID sau ASSUMED_SILENCE",
  "common_facts": [{{"statement": "<o propozitie, cu cuvintele tale>", "chunk_ids": ["<etichetele exacte, ex. S1.2>", "<ex. S2.1>"], "has_hedging": false}}],
  "divergences": [{{"axis": "<ce difera: cifra, ora, cine, cauza, locul>", "positions": [{{"claim": "<versiunea unei publicatii, cu cuvintele tale>", "chunk_ids": ["<ex. S1.3>"]}}]}}],
  "uncorroborated_claims": [{{"statement": "<detaliu prezent intr-o singura publicatie>", "chunk_ids": ["<ex. S3.4>"]}}],
  "is_milestone": false,
  "category": "<una din: {cats}>",
  "entities": ["<1-4 nume proprii cheie, forma scurta canonica>"],
  "icon": "<UN slug din lista de la final sau null>"}}]
Pictograme permise: {icons}
Reguli absolute:
1. common_facts = DOAR fapte sustinute de propozitii din cel putin DOUA publicatii diferite; citeaza TOATE chunk_ids care le sustin. Ordoneaza-le descrescator dupa importanta: primul se intelege singur, ca lead; urmatoarele adauga detalii fara sa repete subiectul. Maximum 5.
2. Nu netezi: daca o publicatie spune 100 si alta 10, scrii o divergenta cu ambele pozitii, nu „zeci"; nu faci medii, nu scrii „pe de o parte... pe de alta parte". O divergenta exista DOAR cand versiunile nu pot fi adevarate simultan; un detaliu in plus la o publicatie („miercuri" fata de „miercuri, 21 octombrie") NU e divergenta.
3. Nimic din afara propozitiilor primite: niciun fapt, nume, cifra, data sau context din cunostintele tale. Fiecare cifra din afirmatie trebuie sa fie in propozitiile citate.
4. Pastreaza incertitudinea: „ar fi", „este acuzat", „potrivit" raman asa, iar atunci has_hedging=true. Atribuie declaratiile (cine a spus) si estimarile (cine estimeaza: un studiu, cercetatorii, o institutie) — o estimare nu devine fapt constatat.
4b. Scrii despre EVENIMENT, nu despre publicatii: nu scrie cine a preluat, cine a publicat sau ce a „relatat" o publicatie, decat daca publicatia e ea insasi parte din eveniment.
5. Ton de proces-verbal: zero adjective si adverbe de evaluare; verbe neutre de declaratie (a declarat, a anuntat, a precizat). Fara citate intre ghilimele: parafrazeaza si atribuie.
6. Cu cuvintele tale: cel mult 12 cuvinte consecutive identice cu o propozitie primita; titlul nu copiaza niciun titlu de sursa.
7. ASSUMED_SILENCE doar cand publicatiile nu au niciun fapt central comun sau versiunile lor despre faptul central se exclud; atunci common_facts=[] si pozitiile merg in divergences.
8. is_milestone=true DOAR pentru o decizie finala sau un eveniment incheiat (lege promulgata, buget aprobat, hotarare definitiva, dezastru produs); niciodata pentru anchete, acuzatii, propuneri sau declaratii.
9. SCRIE IN ROMANA (tradu daca sursele sunt in alta limba). Copiaza etichetele exact cum apar (ex. S4.2) si foloseste DOAR etichetele din blocul ACELUIASI eveniment; nu amesteca evenimentele, chiar daca par legate.
10. Verifica semantic fiecare verb: nu transforma „au pretins", „s-au dat drept" sau „au oprit" intr-un verb de perceptie precum „au simtit"."""

SYSTEM_BATCH = ("Esti editor de stiri. Pentru FIECARE stire primita, titlul reda ESENTA faptului, "
                "iar teaserul comprima faptele de baza, cu cuvintele tale. Concret, nu vag. "
                "Raspunzi EXCLUSIV cu un array JSON valid.")

# Prompt DEDICAT pentru diacritice pierdute (vezi `diacritice.py`). De ce nu s-a pus regula
# direct in SYSTEM_B/USER_B: orice schimbare de prompt cere bump de `PROMPT_VERSION`, iar un
# bump face ~1100 de articole vechi sa fie reprocesate (vezi `upgradable`), adica exact
# opusul a ce vrem aici — la problema asta raspund ~13 iteme pe zi, nu 11.000.
SYSTEM_DIACRITICE = ("Esti corector de limba romana. Primesti texte deja scrise carora le-au "
                     "lipsit diacriticele. Le rescrii cu diacriticele corecte, fara sa schimbi "
                     "nimic altceva. Raspunzi EXCLUSIV cu un array JSON valid.")

USER_DIACRITICE = """Ai mai multe texte (titlu + rezumat) carora le-au lipsit diacriticele la o reformulare automata.

Texte:
{block}

Pentru FIECARE text, rescrie titlul si rezumatul adaugand DIACRITICELE CORECTE ale limbii romane.
Returneaza EXCLUSIV un array JSON, cate UN obiect per text, cu acelasi id primit:
[{{"id": <id>, "title": "<titlul, cu diacritice>", "teaser": "<rezumatul, cu diacritice>"}}]
Reguli: schimba DOAR diacriticele (a -> ă/â, i -> î, s -> ș, t -> ț unde cuvantul o cere); pastreaza EXACT sensul, cifrele, numele proprii, ordinea cuvintelor si lungimea; nu adaugi si nu scoti nicio informatie; nu reformula propozitiile."""


def repara_diacritice(perechi: list, provider) -> int:
    """Un singur apel AI (in LOT) pentru textele care au pierdut diacriticele fata de sursa.

    `perechi` = [(articol, text_sursa)], asa cum le da `diacritice.de_ne_reparat`. Modifica
    articolul pe loc, doar cand rezultatul e acceptabil, si intoarce cate texte au fost
    reparate. Un esec (apel picat, id nemapat, text tot fara diacritice) NU strica textul
    existent: articolul ramane exact cum era, iar cifra nereparatelor se vede in log.

    Cele trei conditii de acceptare, fiecare pentru alt mod de a strica:
      · textul intors chiar are diacritice (altfel n-are rost sa inlocuim ceva cu la fel);
      · titlul ramane sustinut de context (`_titlu_sustinut_de_context`, aceeasi garda ca la C):
        un corector care „corecteaza" si fapte nu are ce cauta pe site;
      · lungimea nu sare (max(3, 30%) cuvinte in plus/minus): o rescriere care dubleaza textul
        nu mai e corectura de diacritice, e alt articol, si se ignora.
    """
    if not perechi or provider is None:
        return 0
    def _corp(a: dict) -> str:
        # Sinteza dialectica: corpul paginii sunt faptele (rezumatul e derivat din ele), deci
        # se corecteaza faptele, cu separator fix, iar rezumatul se rederiva — altfel cardul
        # ar avea diacritice si pagina nu.
        if a.get("model") == "C" and isinstance(a.get("dialectic"), dict):
            return dialectic.FLAT_SEP.join(dialectic.flat_texts(a["dialectic"]))
        return (a.get("synthesis") if a.get("model") == "C" else a.get("teaser")) or ""

    bloc = "\n".join(
        f"[{i}] Titlu: {a.get('title') or ''} | Rezumat: {_corp(a)}"
        for i, (a, _) in enumerate(perechi))
    try:
        raw = provider.complete(SYSTEM_DIACRITICE, USER_DIACRITICE.format(block=bloc))
        arr = _parse_json_array(raw)
    except Exception:
        return 0                               # corectura e optionala: textul ramane cum era

    by_id = {}
    for obj in arr:
        try:
            by_id[int(obj.get("id"))] = obj
        except (TypeError, ValueError, AttributeError):
            continue

    reparate = 0
    for i, (a, sursa) in enumerate(perechi):
        obj = by_id.get(i)
        if not isinstance(obj, dict):
            continue
        titlu = (obj.get("title") or "").strip()
        corp = (obj.get("teaser") or "").strip()
        if not (titlu and corp) or not diacritice.are_diacritice(f"{titlu} {corp}"):
            continue
        vechi_titlu = a.get("title") or ""
        vechi_corp = _corp(a)
        if (len(titlu.split()) > len(vechi_titlu.split()) + max(3, int(0.3 * len(vechi_titlu.split())))
                or len(corp.split()) > len(vechi_corp.split()) + max(4, int(0.3 * len(vechi_corp.split())))):
            continue
        if not _titlu_sustinut_de_context(titlu, sursa):
            continue
        if a.get("model") == "C" and isinstance(a.get("dialectic"), dict):
            d = a["dialectic"]
            if not dialectic.assign_flat(d, corp.split(dialectic.FLAT_SEP.strip())):
                continue                       # separatorii nu s-au pastrat -> textul ramane cum era
            a["title"] = titlu
            a["synthesis"] = dialectic.derive_synthesis(d, titlu, config.SYNTHESIS_MAX_WORDS)
        elif a.get("model") == "C":
            a["title"] = titlu
            a["synthesis"] = truncate_words(corp, config.SYNTHESIS_MAX_WORDS)
        else:
            a["title"] = titlu
            a["teaser"] = truncate_words(corp, config.TEASER_MAX_WORDS)
        # Textul publicat s-a schimbat DUPA procesare: fara asta, `updated` ar minti despre
        # cand a fost atins articolul (acelasi motiv ca la sinteza care absoarbe o stire noua).
        if not a.get("updated"):
            a["updated"] = datetime.now(timezone.utc).isoformat()
        reparate += 1
    return reparate

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
        return re.sub(r"au\s+(?:simțit|simtit)\s+(?:polițiști|politisti)", "s-au dat drept polițiști", title, flags=re.IGNORECASE)

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
USER_C_DIALECTIC = USER_C_DIALECTIC.replace("{icons}", _ICON_SLUGS).replace("{cats}", _CATS)
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


def _obiecte_de_nivel_unu(text: str) -> list[str]:
    """Textele obiectelor `{...}` de pe primul nivel al unui array, cu adâncimea numărată în
    afara șirurilor — ca un obiect stricat să nu-i ia cu el și pe vecinii lui."""
    out, depth, start, in_str, esc = [], 0, None, False, False
    inside_array = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "[" and not inside_array and depth == 0:
            inside_array = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                out.append(text[start:i + 1])
                start = None
    return out


_REPARATII_JSON = (
    (re.compile(r'^(\s*)-\s+(")', re.M), r"\1\2"),     # „- "entities": [...]" — liniuță rătăcită
    (re.compile(r",(\s*[}\]])"), r"\1"),                  # virgulă înainte de închidere
)


def _parse_json_array_tolerant(text: str) -> list:
    """Ca `_parse_json_array`, dar când array-ul întreg nu se parsează, încearcă fiecare
    obiect separat, cu două reparații mecanice sigure. MĂSURAT 23.10.2026 pe Gemini Flash
    Lite, formatul dialectic: o liniuță rătăcită înaintea unei chei a pierdut toate cele 3
    clustere ale lotului. Un obiect care tot nu se parsează rămâne pierdut SINGUR — clusterul
    lui se amână, ceilalți se publică."""
    arr = _parse_json_array(text)
    if arr:
        return arr
    cleaned = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.MULTILINE)
    out = []
    for frag in _obiecte_de_nivel_unu(cleaned):
        for attempt in (frag, None):
            cand = frag
            if attempt is None:
                for rx, rep in _REPARATII_JSON:
                    cand = rx.sub(rep, cand)
            try:
                obj = json.loads(cand)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
            break
    return out


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
                                   it["teaser"], source_texts[i],
                                   slug_original=slug_din_link(it.get("original_link")))
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
                           f"{item.get('original_title', '')} {item.get('description', '')}",
                           slug_original=slug_din_link(item.get("original_link")))
    return item


def process_cluster(group: list, provider) -> dict | None:
    """Model C. Returneaza un articol-reprezentant cu sinteza + lista de surse.

    Daca providerul exista dar apelul AI esueaza (429/503/etc.), returneaza None:
    item-ul NU se publica brut, ci se reia la rularea urmatoare (regula 'No mangled
    output'). Doar in modul fara cheie (provider None) se face fallback determinist.
    """
    # Aceeasi pregatire ca lotul: members si story_id nu mai depind de calea de apel.
    group, rep = _prep_cluster_rep(group)

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

    # Aceeași cale ca lotul (E2 dialectic): un singur loc unde se decide ce se publică.
    return process_clusters_batch([group], provider)[0]


def repara_identitate_cluster(articles: list) -> int:
    """Umple story_id si members pe sintezele C vechi, fara timeline inventat.

    Un C fara membri primeste un singur membru: el insusi. story_id lipsă se
    deriveaza din articol, cu aceeasi functie ca la formare. Nu redenumeste
    un id deja scris. Intoarce cate campuri a completat.
    """
    n = 0
    for a in articles:
        if not isinstance(a, dict) or a.get("model") != "C":
            continue
        if not a.get("story_id"):
            a["story_id"] = _story_id([a])
            n += 1
        if not a.get("members"):
            membri = _membri_din_grup([a])
            if membri:
                a["members"] = membri
                n += 1
    return n


def _membri_din_grup(group: list) -> list:
    """Schelet de timeline per membru al story-ului (Etapa 1 STORY, IZZ-0418): doar
    {published, title, source, url} — exact campurile de care are nevoie timeline-ul
    determinist, NU articolele intregi (data/articles.json e la 23 MB si se comite de
    ~12 ori/zi). Un membru care e el insusi o sinteza C isi duce propriii membri mai
    departe, deci istoricul evenimentului se acumuleaza la fiecare absorbire."""
    membri: dict = {}
    for a in group:
        propriu = {"published": a.get("published"), "title": a.get("title"),
                   "source": a.get("source_name"), "url": a.get("url")}
        for m in [propriu] + list(a.get("members") or []):
            u = m.get("url")
            if u and u not in membri:
                membri[u] = m
    out = sorted(membri.values(), key=lambda m: m.get("published") or "")
    return out[-config.STORY_MAX_MEMBRI:]


def _story_id(group: list) -> str:
    """Identitate persistenta a evenimentului (Etapa 1 STORY, IZZ-0418): mosteneste
    story_id-ul oricarui membru C deja publicat; la prima formare, id determinist din
    cel mai vechi membru — aceeasi grupare produce acelasi id indiferent de rulare."""
    for a in group:
        if a.get("story_id"):
            return a["story_id"]
    cel_vechi = min(group, key=lambda a: a.get("published") or "")
    sambure = (cel_vechi.get("published") or "") + "|" + \
        (cel_vechi.get("original_link") or cel_vechi.get("url") or "")
    return "st-" + hashlib.sha1(sambure.encode("utf-8")).hexdigest()[:12]


_ROLE_PRIORITY = {
    "ROOT": 5,
    "INDEPENDENT_CONTRIBUTOR": 4,
    "ECHO": 3,
    "CLONE": 2,
    "DERIVED": 1,
}


def _roluri_grup(group: list) -> dict[str, str]:
    """Rolul epistemic per URL. Sursa de adevăr e clasificarea făcută de `fetch_deep` pe
    TEXTUL INTEGRAL (`_epistemic_role`, atașat în memorie în aceeași rulare); doar membrii
    fără el (fetch_deep oprit, item adăugat după) se clasifică aici, pe titlu + descriere.
    O a doua clasificare, independentă, pe text mai sărac, ar putea contrazice prima —
    alt ROOT pe /surse/ decât cel din driftul E1."""
    lipsa = [a for a in group if not a.get("_epistemic_role")]
    calculate = fetch_deep.classify_cluster_epistemic_roles(group) if lipsa else {}
    roluri = {}
    for a in group:
        u = a.get("url") or a.get("original_link") or ""
        roluri[u] = a.get("_epistemic_role") or calculate.get(u, "ECHO")
    return roluri


def _prep_cluster_rep(group: list) -> tuple:
    """Partea din process_cluster care NU cere AI: alege reprezentantul, aduna sursele,
    calculeaza rolurile epistemice E1 si marcheaza actualizarea. Extrasa ca sa fie identica
    intre calea single (process_cluster) si cea in lot (process_clusters_batch) -- doua
    copii ale conditiei „cine e rep-ul" s-ar putea departe fara sa para stricat nimic,
    acelasi risc numit la `upgradable()` mai sus."""
    group = sorted(group, key=lambda a: (not a.get("processed_by"), a.get("published") or ""))
    actualizare = bool(group[0].get("processed_by"))
    rep = dict(group[0])
    rep["model"] = "C"

    roles_by_url = _roluri_grup(group)
    # Rolurile per DOMENIU, unite cu cele din rularea anterioară: membrii vechi ai unei
    # sinteze actualizate nu mai au text în stare, deci rolul lor de atunci e singura memorie.
    epistemic_roles: dict[str, str] = {}
    for a in group:
        for dom_k, r_val in (a.get("epistemic_roles") or {}).items():
            if _ROLE_PRIORITY.get(r_val, 0) > _ROLE_PRIORITY.get(epistemic_roles.get(dom_k, ""), 0):
                epistemic_roles[dom_k] = r_val
    for a in group:
        u = a.get("original_link") or a.get("url") or ""
        dom = domain_of(u)
        role = roles_by_url.get(a.get("url") or a.get("original_link") or "", "ECHO")
        if dom and _ROLE_PRIORITY.get(role, 0) > _ROLE_PRIORITY.get(epistemic_roles.get(dom, ""), 0):
            epistemic_roles[dom] = role

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

    if actualizare and group[0].get("first_source"):
        rep["first_source"] = group[0].get("first_source")
    else:
        root_member = next(
            (a for a in group
             if roles_by_url.get(a.get("url") or a.get("original_link") or "") == "ROOT"),
            group[0],
        )
        rep["first_source"] = root_member.get("source_name")

    rep["epistemic_roles"] = epistemic_roles
    # Confirmările Încrucișate: domeniile ne-derivate, ne-clonate, care coroborează. Setul se
    # UNEȘTE peste rulări (membrii vechi nu mai au text în stare), iar cifra e mărimea lui —
    # deci nu poate crește prin simpla numărare a publicațiilor care repetă același comunicat.
    confirmate = set(group[0].get("cross_confirmed") or []) if actualizare else set()
    confirmate |= fetch_deep.cross_confirmed_domains(group, roles_by_url)
    confirmate -= {d for d, r in epistemic_roles.items() if r in fetch_deep.NON_CONFIRMING_ROLES}
    rep["cross_confirmed"] = sorted(confirmate)
    rep["cross_confirmations"] = max(1, len(confirmate))
    rep["members"] = _membri_din_grup(group)
    rep.setdefault("story_id", _story_id(group))
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

    # E2: fiecare eveniment e un bloc de propoziții numerotate `[S{j}.{k}]` (textul integral din
    # E0, lead-ul RSS doar ca rezervă). Numerotarea e unică în tot lotul, deci o afirmație care
    # citează alt eveniment al lotului e respinsă mecanic în `dialectic.validate`.
    blocks = dialectic.build_blocks([(group, _roluri_grup(group)) for group, _ in preps])
    events_block = "\n\n".join(f"[{b.cid}]\n{b.text}" for b in blocks)
    try:
        raw = provider.complete(SYSTEM_C_DIALECTIC, USER_C_DIALECTIC.format(events_block=events_block))
        arr = _parse_json_array_tolerant(raw)
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
        out.append(_aplica_dialectic(rep, by_id.get(i), blocks[i], provider))
    return out


def _aplica_dialectic(rep: dict, obj, block, provider) -> dict | None:
    """Propunerea modelului pentru UN cluster → reprezentantul publicabil, sau None (amânat).

    Un cluster al cărui JSON e invalid sau nu supraviețuiește verificărilor se amână SINGUR;
    celelalte din lot se publică (Argon R4). Nu există cădere pe vechea sinteză narativă:
    exact când modelul n-a putut separa ce confirmă sursele, un text liber ar reintroduce
    amestecul pe care E2 îl elimină."""
    if not isinstance(obj, dict):
        dialectic.numara("amanate_nemapat")
        return None                            # nemapat -> amanat, ca la esecul unui apel singur
    d = dialectic.validate(obj, block)
    if d is None:
        return None
    context = " ".join(t for _, t in block.chunks.values())
    candidat = _repair_synthesis_title((obj.get("title") or "").strip(), context)
    if not _titlu_sustinut_de_context(candidat, context):
        dialectic.numara("amanate_titlu_deformat")
        return None                            # deformare semantica -> amanat
    if titlu_copiat(candidat, context):
        dialectic.numara("amanate_titlu_copiat")
        return None                            # titlu transcris -> amanat (gate-ul l-ar bloca)
    if cifre_straine(candidat, context):
        dialectic.numara("amanate_titlu_cifra")
        return None                            # cifra fara sursa in titlu -> amanat
    rep["title"] = candidat
    rep["synthesis"] = dialectic.derive_synthesis(d, candidat, config.SYNTHESIS_MAX_WORDS)
    if not rep["synthesis"]:
        return None
    rep["dialectic"] = d
    rep["entities"] = _clean_entities(obj.get("entities"))
    rep["ai_cat"] = obj.get("category", "")
    rep["category"] = _resolve_category(rep, rep["ai_cat"], rep["entities"])
    rep["icon"] = _clean_icon(obj.get("icon"))
    rep["processed_by"] = provider.name
    rep["prompt_version"] = config.PROMPT_VERSION
    # Gate-ul vede TOT textul publicat (rezumatul și fiecare fapt, divergență, afirmație),
    # contra TOT contextul văzut de model — un fapt copiat sau o cifră fără sursă, oriunde
    # pe pagină, amână articolul prin mecanismul existent (`raport_copiere.aplica_defer`).
    raport_copiere.noteaza("C", rep.get("original_link"), rep["title"],
                           f"{rep['synthesis']} {dialectic.all_text_of(d)}", context,
                           slug_original=slug_din_link(rep.get("original_link")))
    return rep
