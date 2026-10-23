"""E0 — materia primă: text integral DOAR pentru clusterele selectate pentru sinteza C.

Planul «izz.ro prin prisma cărților» (plan-paradigma-izz.md §3, E0, validat de Argon
21.10.2026): fetch-ul rămâne ușor (RSS + meta-description) pentru tot fluxul; pentru
clusterele selectate se trage textul integral al articolelor, cu gărzi — timeout 3,5 s/URL,
validator anti-paywall/consent/mismatch, cădere instantanee pe descrierea RSS.

Textul integral NU se persistează NICĂIERI: dreptul de autor (vezi `state._scrub_processed`,
care șterge texte brute din repo din același motiv). Se păstrează doar amprenta SHA-256 și
ancorele (cifre + entități), în `data/deep_meta.json`, prune la TTL — baza pentru E1
(modificări tăcute → cluster dirty) și pentru E2 (propozițiile numerotate S1.1 intră în
promptul sintezei dialectice; aici doar se produc și se măsoară, consumul vine cu E2).

Adaptare după artefactul Gemini Argon «e0_fetch_and_split.py» (21 oct 2026): algoritmii
sunt ai lui (mascarea punctelor protejate, validatorul, ancorele, driftul Jaccard);
transportul e rescris pe idiomul repo-ului — urllib prin `fetch._deschide` (UNICA ieșire
în rețea, cu gărzi SSRF testate de `test_fetch_redirect_ssrf`) + ThreadPoolExecutor, nu
httpx/asyncio, ca orice cerere nouă să moștenească automat garda existentă. Două defecte
din artefact sunt reparate aici: `_ACRONYM_PATTERN` avea `+{2,}` (regex invalid în Python —
„multiple repeat”), iar extracția pe thread-uri înlocuiește `asyncio.to_thread`.
"""
import collections
import hashlib
import html
import json
import os
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from . import config
from . import fetch
from .util import domain_of

FETCH_TIMEOUT_S = 3.5          # Argon R3: dur, conectare + citire, ca rularea orară să încapă în fereastră
MAX_CONCURRENT = int(os.environ.get("DEEP_WORKERS", "15"))
MAX_PER_DOMAIN = 2             # politețe per redacție — evită 429/ban la re-fetch
DEEP_BATCH_TIMEOUT_S = float(os.environ.get("DEEP_BATCH_TIMEOUT_S", "120"))
MIN_FULL_TEXT_CHARS = 280      # sub asta, pagina e ciot, paywall sau consent — nu articol
MIN_TITLE_OVERLAP_RATIO = 0.25 # măcar 25% din cuvintele lungi ale titlului trebuie să apară în corp
ANCHOR_DRIFT_THRESHOLD = 0.20  # E1: peste 20% diferență pe ancore la re-fetch → cluster dirty
MAX_SENTENCES = 25            # buget de context per sursă ROOT/INDEPENDENT în promptul E2
MAX_SENTENCES_ECHO = 4        # Argon calib.: sursele ECHO/DERIVED rămân scurte în promptul E2
MIN_SENTENCE_CHARS = 18       # fragmentele mai scurte (cioate de titlu) se lipesc de următoarea
MAX_ANCHORS_STORED = 80       # plafon de stocare per articol; Jaccard-ul e stabil mult sub atât

# E1-core & E3 (plan-paradigma-izz.md §3): graful de noutate și first-publisher după densitate
FIRST_PUBLISHER_WINDOW_MIN = 15      # fereastră glisantă 15 min pentru promovarea investigației dense peste alertă
FIRST_PUBLISHER_DENSITY_RATIO = 1.5  # prag 1,5× numărul de ancore față de primul alert scurt
NOVELTY_MIN_ANCHORS = 2              # minimum 2 ancore noi pentru INDEPENDENT_CONTRIBUTOR
NOVELTY_MIN_RATIO = 0.30             # și minimum 30% rată de noutate în propriul set de ancore
# Clonă = același text (comunicat, depeșă) rescris minimal, FĂRĂ atribuire explicită. Se
# măsoară prin conținerea shingle-urilor de 4 cuvinte de conținut (fără cuvinte de legătură):
# |A∩B| / min(|A|,|B|). Conținerea, nu Jaccard-ul: un lead RSS scurt copiat dintr-un articol
# lung are Jaccard mic, dar e integral conținut în el; iar un paragraf de context adăugat de
# redacție deasupra comunicatului nu „diluează” copia (Argon, review 23.10.2026). Sub
# CLONE_MIN_WORDS cuvinte de conținut nu există destule shingle-uri ca măsura să însemne
# ceva, deci nu se declară nicio clonă — prezumția e de independență.
CLONE_SHINGLE_N = 4
CLONE_CONTAINMENT = 0.65
CLONE_MIN_WORDS = 10
_STOPWORDS_RO = frozenset("""
a ai al ale am ar are as asta acest aceasta aceste acesti acum ar au ca cand care cat ce cea
cei cel cele cu cum da dar de deci din dintre doar dupa e ea ei el este eu fi fie fost iar
il in inca intr intre ii isi la le li lui mai ma mi ne nici nu o or ori pe pentru prin sa sau
se si sunt te tot toti un una unei unor unui va vor
""".split())

META_PATH = os.path.join(config.ROOT, "data", "deep_meta.json")

# Contoarele rulării curente — idiomul `fetch._SARITE`: vizibilitate în raport fără să
# schimbe semnăturile prin pipeline. Se golesc la începutul fiecărei rulări.
_STATISTICI = collections.Counter()


def stats() -> dict:
    """Ce a făcut E0 în rularea curentă. Se citește din `main.run()`, pentru build.json."""
    return dict(_STATISTICI)


# ---------------------------------------------------------------------------
# 1. SPLITTER DETERMINIST DE PROPOZIȚII ROMÂNEȘTI (FORMAT S1.1)
# ---------------------------------------------------------------------------

_PROTECTED_DOT = "\uE000"  # Private Use Area: nu apare în texte reale

RO_ABBREVIATIONS = (
    # Juridic / administrativ
    "art", "alin", "lit", "nr", "op", "cit", "hg", "oug", "og", "dec", "ord",
    "dos", "pen", "civ", "proc", "const", "urm", "fila", "vol", "pag", "cap",
    # Geografic / localizare
    "jud", "mun", "loc", "com", "sat", "str", "bd", "sos", "al",
    "intr", "bl", "sc", "et", "ap", "sect", "km",
    # Titluri / funcții / instituții
    "dr", "prof", "univ", "ing", "av", "ec", "arh", "gen", "col", "lt", "mr",
    "cpt", "plut", "chest", "comis", "insp", "min", "secr", "dep", "sen",
    "pres", "guv", "amb", "acad", "sf", "pr", "ep", "mitr",
    # Uzuale / timp / măsuri / companii
    "ex", "cca", "aprox", "conf", "potr", "obs", "pct", "fig", "tab", "ed",
    "trad", "red", "coord", "etc", "vs", "dl", "dna",
    "d-l", "d-na", "dnei", "dlui", "ian", "feb", "febr", "mart", "apr", "iun",
    "iul", "aug", "sept", "oct", "nov", "dec", "mil", "mld", "mii", "sec",
    "min", "st", "srl", "sa", "pfa", "ong", "ra",
)

_ABBR_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in RO_ABBREVIATIONS) + r")\.",
    re.IGNORECASE,
)
# Acronime cu puncte interne: M.Ap.N., B.N.R., S.U.A. — 2+ secvențe «literă.»
# (reparat din artefact: `+{2,}` acolo era regex invalid — „multiple repeat”).
_ACRONYM_PATTERN = re.compile(r"\b(?:[A-ZĂÂÎȘȚ][a-zăâîșț]?\.){2,}")
_INITIALS_PATTERN = re.compile(r"\b([A-ZĂÂÎȘȚ])\.(?=\s+[A-ZĂÂÎȘȚ])")
_NUMERIC_DOT_PATTERN = re.compile(r"(?<=\d)\.(?=\d)")
_LEADING_LIST_NUM_PATTERN = re.compile(r"(?:^|\n)\s*(\d{1,2})\.(?=\s+[A-ZĂÂÎȘȚ])")
_DOMAIN_PATTERN = re.compile(
    r"\b([a-zA-Z0-9\-]+)\.(ro|com|eu|org|net|gov|edu|info|md)\b",
    re.IGNORECASE,
)
_ELLIPSIS_PATTERN = re.compile(r"\.{2,}")
_SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ0-9„”\"'\u2014\u2013-])"
)


def normalize_whitespace(text: str) -> str:
    """Curăță entități HTML reziduale și normalizează paragrafele într-un flux unic."""
    text = html.unescape(text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned = []
    for line in lines:
        if line and line[-1] not in ".!?\"\u201e\u201d':;":
            line += "."
        cleaned.append(line)
    return re.sub(r"\s+", " ", " ".join(cleaned)).strip()


def split_romanian_sentences(text: str, source_id: str,
                             max_sentences: int = MAX_SENTENCES,
                             min_sentence_chars: int = MIN_SENTENCE_CHARS) -> dict:
    """Sparge textul în propoziții indexate {"S1.1": ...}, protejând abrevierile
    românești, numerele cu punct (1.000), acronimele (M.Ap.N.), inițialele (I. L.
    Popescu) și domeniile (izz.ro). Punctele protejate se maschează cu un caracter
    din Private Use Area, NU cu negative lookbehind de lungime variabilă — `re` nu
    îl suportă, iar variantele parțiale erau fragile (punctul orb semnalat de Argon).
    """
    clean_text = normalize_whitespace(text)
    if not clean_text:
        return {}

    masked = _ELLIPSIS_PATTERN.sub(_PROTECTED_DOT * 3, clean_text)
    masked = _NUMERIC_DOT_PATTERN.sub(_PROTECTED_DOT, masked)
    masked = _DOMAIN_PATTERN.sub(rf"\1{_PROTECTED_DOT}\2", masked)
    masked = _ACRONYM_PATTERN.sub(lambda m: m.group(0).replace(".", _PROTECTED_DOT), masked)
    masked = _ABBR_PATTERN.sub(rf"\1{_PROTECTED_DOT}", masked)
    masked = _INITIALS_PATTERN.sub(rf"\1{_PROTECTED_DOT}", masked)
    masked = _LEADING_LIST_NUM_PATTERN.sub(rf" \1{_PROTECTED_DOT}", masked)

    raw_parts = _SENTENCE_SPLIT_PATTERN.split(masked)

    restored_sentences: list[str] = []
    buffer = ""
    for part in raw_parts:
        restored = part.replace(_PROTECTED_DOT, ".").strip()
        if not restored:
            continue
        if buffer:
            restored = f"{buffer} {restored}"
            buffer = ""
        if len(restored) < min_sentence_chars:
            buffer = restored
        else:
            restored_sentences.append(restored)
    if buffer:
        if restored_sentences:
            restored_sentences[-1] = f"{restored_sentences[-1]} {buffer}"
        else:
            restored_sentences.append(buffer)

    result: dict[str, str] = {}
    for idx, sent in enumerate(restored_sentences[:max_sentences], start=1):
        result[f"{source_id}.{idx}"] = sent
    return result


# ---------------------------------------------------------------------------
# 2. ANCORE, SHA-256, DRIFT ȘI GRAFUL DE NOUTATE E1-CORE
# ---------------------------------------------------------------------------

_NUM_ANCHOR_RE = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")
_MID_CAPS_RE = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-ZĂÂÎȘȚ][a-zăâîșț][a-zăâîșțA-ZĂÂÎȘȚ]{2,}\b")
_ACRONYM_ANCHOR_RE = re.compile(r"\b(?:[A-ZĂÂÎȘȚ]{3,10}|(?:[A-ZĂÂÎȘȚ][a-zăâîșț]?\.){2,})\b")
_NOISE_ACRONYMS = frozenset({
    "UPDATE", "VIDEO", "FOTO", "LIVE", "BREAKING", "EXCLUSIV", "ALERTA", "ALERTE", "SURSE",
    "ULTIMA", "URGENT", "OFICIAL", "GALERIE", "INTERVIU", "AUDIO", "DOCUMENT", "CITESTE",
})

# Glosar de entități frecvente RO (plan-paradigma-izz.md §3 E3): extrase ca ancore chiar și
# când stau la început de propoziție — remediul punctului orb al `_MID_CAPS_RE`, care sare
# peste primul cuvânt al frazei ca să nu prindă majuscula gramaticală.
#
# DOUĂ clase, deliberat separate (review 23.10.2026): o rădăcină scurtă potrivită pe PREFIX
# prinde cuvinte de început de frază — „pot” → „Potrivit…”, „Poate…”; „mai” → „Mai mult…”;
# „sens” → „Sensul…”. Acele „ancore” ar fi comune aproape tuturor articolelor și ar umfla
# suprapunerea pe care se calculează noutatea și confirmările. Deci: rădăcinile de ≥5 litere
# se potrivesc pe prefix (flexiunea românească: Guvernul/Guvernului), iar acronimele și
# numele scurte se potrivesc DOAR pe cuvânt exact (sunt oricum prinse și de `_ACRONYM_ANCHOR_RE`
# când apar cu majuscule).
_GLOSSARY_PREFIX_STEMS = frozenset({
    "guvern", "parlament", "senatul", "presedint", "minister", "ministr", "primar", "consiliu",
    "premier", "prefect", "procuror",
    "curtea", "inalta", "tribunal", "parchet", "politia", "jandarmeri", "pompieri",
    "spital", "universitat", "inspectorat", "directia", "agentia", "autoritat",
    "comisia", "banca", "bugetul", "coalitia", "opozitia", "camera", "deputat", "senator",
    "bucurest", "timis", "constant", "brasov", "craiova", "galati", "ploiest", "oradea",
    "braila", "pitest", "sibiu", "bacau", "mures", "buzau", "botosan", "ramnicu", "drobeta",
    "suceava", "piatra", "targovist", "focsan", "bistrit", "resita", "tulcea", "calarasi",
    "giurgiu", "hunedoar", "zalau", "sfantu", "slatina", "vaslui", "slobozia", "alexandria",
    "miercurea", "ilfov", "prahova", "bihor", "arges", "neamt", "maramures", "vrancea",
    "teleorman", "ialomita", "covasna", "harghita", "salaj", "mehedint", "dambovit",
    "valcea", "romania", "moldov", "ucrain", "rusia", "bruxelles", "europe",
})
_GLOSSARY_EXACT = frozenset({
    "psd", "pnl", "usr", "aur", "udmr", "sos", "pot", "reper", "pmp", "bnr", "anaf", "dna",
    "diicot", "ccr", "csat", "csm", "cnair", "anpc", "anre", "igsu", "smurd", "isu", "mai",
    "mapn", "mae", "ms", "mec", "mipe", "madr", "cnas", "ins", "bec", "aep", "cna", "ancom",
    "asf", "nato", "ue", "onu", "fmi", "cluj", "iasi", "arad", "alba", "deva", "gorj",
    "olt", "dolj", "satu", "baia", "caras", "senat",
})
# Compatibilitate: numele vechi rămâne valabil pentru importuri (uniunea celor două clase).
KNOWN_RO_ENTITIES = _GLOSSARY_PREFIX_STEMS | _GLOSSARY_EXACT

_QUOTE_ANCHOR_RE = re.compile(r"[„\"«]([^”\"»]{12,120})[”\"»]")

# Citări explicite către agenții de presă sau alte publicații (plan-paradigma-izz.md §3 E3: DERIVED)
_DERIVED_ATTRIBUTION_RE = re.compile(
    r"\b(?:potrivit|conform|transmite|informeaza|scrie|citeaza|relat(?:eaza|at\s+de)|"
    r"dupa\s+cum\s+(?:arata|scrie)|sursa\s*:)\s+"
    r"(agerpres|mediafax|news\.ro|reuters|afp|efe|associated\s+press|dpa|bloomberg|"
    r"hotnews(?:\.ro)?|g4media(?:\.ro)?|digi24(?:\.ro)?|profit(?:\.ro)?|"
    r"zf(?:\.ro)?|ziarul\s+financiar|libertatea(?:\.ro)?|adevarul(?:\.ro)?|"
    r"euronews|europa\s+libera|spotmedia|golazo|fanatik|gsp|prosport|stirileprotv|"
    r"observatornews|antena3|romaniatv|b1tv|cotidianul|economica(?:\.net)?|"
    r"cursdeguvernare|edupedu|economedia|defenseromania|turnulsfatului|ziaruldeiasi|"
    r"monitorulcj|bihon|tion|aradon|ebihoreanul|gazetadesud|vremeanoastra)\b",
    re.IGNORECASE,
)


def strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _stem_ro(word: str) -> str:
    norm = strip_diacritics(word.lower()).strip(".")
    if len(norm) >= 6:
        norm = re.sub(r"(?:ului|ilor|lor|ul|le)$", "", norm)
    return norm[:8]


def _glossary_hit(norm: str, raw: str) -> bool:
    """Cuvântul de început de frază e o entitate din glosar? Exact pentru scurte, prefix
    pentru rădăcinile de ≥5 litere. Acronimele exacte cer forma cu majusculă inițială
    („PSD”, „Psd”), nu verbul omograf la început de frază („Pot”, „Mai”): acolo acceptăm
    doar forma integral majusculă."""
    if norm in _GLOSSARY_EXACT:
        return len(norm) > 3 or raw.isupper()
    return any(norm.startswith(p) for p in _GLOSSARY_PREFIX_STEMS)


def _hash_quote(q_norm: str) -> str:
    """Ancora de citat se stochează ca hash: `data/deep_meta.json` e comis într-un repo
    PUBLIC, iar comparația (drift, noutate) e oricum pe egalitate exactă — deci textul
    citatului nu trebuie să existe nicăieri în stare (aceeași regulă ca `_scrub_processed`)."""
    return hashlib.sha256(q_norm[:64].encode("utf-8")).hexdigest()[:12]


def extract_quick_anchors(text: str) -> set:
    """Ancore factuale (cifre, entități la mijloc sau din glosar la început de frază,
    acronime și citate scurte) pentru calculul de drift și graful de noutate E1/E3."""
    if not text:
        return set()
    anchors: set = set()
    for num in _NUM_ANCHOR_RE.findall(text):
        anchors.add(f"NUM:{num.replace(',', '.')}")
    for ent in _MID_CAPS_RE.findall(text):
        anchors.add(f"ENT:{_stem_ro(ent)}")
    for acr in _ACRONYM_ANCHOR_RE.findall(text):
        clean_acr = acr.replace(".", "").upper()
        if clean_acr not in _NOISE_ACRONYMS and len(clean_acr) >= 3:
            anchors.add(f"ACR:{strip_diacritics(clean_acr.lower())}")
    # Entitățile din glosar sunt recunoscute și la început de propoziție (ex. „Guvernul a aprobat...”)
    for word in re.findall(r"\b[A-ZĂÂÎȘȚ][a-zăâîșțA-ZĂÂÎȘȚ]{1,}\b", text):
        norm = strip_diacritics(word.lower()).strip(".")
        if _glossary_hit(norm, word):
            if norm in _GLOSSARY_EXACT and word.isupper():
                anchors.add(f"ACR:{norm}")
            else:
                anchors.add(f"ENT:{_stem_ro(word)}")
    for q in _QUOTE_ANCHOR_RE.findall(text):
        # normalizare agresivă înainte de hash: o virgulă sau un spațiu în plus între două
        # redacții nu trebuie să facă din același citat două ancore diferite
        q_norm = " ".join(re.findall(r"\w+", strip_diacritics(q.lower())))
        if len(q_norm) >= 8:
            anchors.add(f"Q:{_hash_quote(q_norm)}")
    return anchors


def anchor_sample(anchors: set) -> list:
    """Eșantionul stocat al ancorelor: cele MAX_ANCHORS_STORED cu cel mai mic hash (bottom-k),
    sortate. NU primele în ordine alfabetică: trunchierea alfabetică ținea doar ACR:/ENT: și
    pierdea NUM:/Q:, iar driftul compara un set trunchiat (cel stocat) cu unul întreg (cel
    proaspăt) — orice articol cu peste 80 de ancore ieșea „modificat tăcut” la prima
    schimbare de SHA (un widget, un contor), deși faptele erau aceleași. Bottom-k pe hash e
    un eșantion stabil: aceleași ancore produc același eșantion, iar Jaccard-ul pe eșantioane
    estimează Jaccard-ul pe seturile întregi."""
    return sorted(sorted(anchors, key=lambda a: hashlib.sha256(a.encode("utf-8")).hexdigest())
                  [:MAX_ANCHORS_STORED])


def compute_sha256(text: str) -> str:
    """Hash determinist pe textul normalizat (ignoră variații de whitespace)."""
    norm = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def check_if_silent_edit_causes_dirty(role: str, old_sha: str | None, new_sha: str,
                                      old_anchors: set | None, new_anchors: set) -> bool:
    """O sursă cu rol epistemic greu (ROOT / INDEPENDENT_CONTRIBUTOR) care își schimbă
    conținutul cu peste 20% drift pe ancore, după ce a fost procesată, murdărește
    clusterul — sinteza înghețată ar publica minciuna veche (Argon, «Silent Edit
    Desync»).
    """
    if role not in ("ROOT", "INDEPENDENT_CONTRIBUTOR"):
        return False
    if not old_sha or old_sha == new_sha:
        return False
    if not old_anchors:
        return True
    union_len = len(old_anchors | new_anchors)
    if union_len == 0:
        return False
    return len(old_anchors ^ new_anchors) / union_len >= ANCHOR_DRIFT_THRESHOLD


def is_derived_attribution(text: str, own_domain: str = "", own_source_name: str = "") -> bool:
    """Detectează dacă textul își atribuie explicit informația unei agenții de presă
    sau altei publicații decât propria redacție (rol epistemic DERIVED în E1/E3)."""
    if not text:
        return False
    norm_text = strip_diacritics(text.lower())
    own_norm = strip_diacritics(f"{own_domain} {own_source_name}".lower())
    for m in _DERIVED_ATTRIBUTION_RE.finditer(norm_text):
        cited = re.sub(r"\s+", "", m.group(1).lower().split(".")[0])
        if cited and cited not in own_norm:
            return True
    return False


def _parse_pub_ts(value: str | None) -> datetime:
    try:
        dt = datetime.fromisoformat(value or "")
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.max.replace(tzinfo=timezone.utc)


def _item_text_and_anchors(it: dict, results_by_url: dict | None = None) -> tuple[str, set]:
    url = it.get("url") or it.get("original_link") or ""
    if results_by_url and url in results_by_url:
        r = results_by_url[url]
        return r.raw_text, set(r.anchors)
    if it.get("_deep_anchors") is not None:
        txt = " ".join(filter(None, (
            it.get("original_title") or it.get("title"),
            it.get("description") or it.get("teaser") or it.get("synthesis"),
        )))
        return txt, set(it.get("_deep_anchors") or [])
    txt = " ".join(filter(None, (
        it.get("original_title") or it.get("title"),
        it.get("description") or it.get("teaser") or it.get("synthesis"),
    )))
    return txt, extract_quick_anchors(txt)


def _shingles(text: str, n: int = CLONE_SHINGLE_N) -> set:
    words = [w for w in re.findall(r"\w+", strip_diacritics((text or "").lower()))
             if w not in _STOPWORDS_RO]
    if len(words) < max(n, CLONE_MIN_WORDS):
        return set()
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def shingle_containment(a: set, b: set) -> float:
    """Cât din textul mai scurt se regăsește, ca secvențe de 5 cuvinte, în celălalt."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def classify_cluster_epistemic_roles(group: list,
                                     results_by_url: dict | None = None) -> dict[str, str]:
    """Graful determinist de noutate (plan-paradigma-izz.md §3, E1 & E3, 0 apeluri AI):
    clasifică fiecare articol din `group` ca ROOT, INDEPENDENT_CONTRIBUTOR, ECHO, CLONE
    sau DERIVED.

    - DERIVED: atribuire explicită către agenție sau altă publicație;
    - CLONE: textul e conținut în proporție ≥60% (shingle-uri de 5 cuvinte) într-un text
      deja clasificat al altei publicații — aceeași origine, fără atribuire declarată;
    - ROOT: primul publicant ne-derivat, dar cu fereastră glisantă de 15 minute în care
      un articol cu ≥1,5× (și cel puțin +2) mai multe ancore factuale câștigă ROOT în
      fața unui alert scurt de 2 rânduri;
    - INDEPENDENT_CONTRIBUTOR: aduce ≥2 ancore noi ȘI ≥30% rată de noutate față de
      ancorele deja acoperite în cluster;
    - ECHO: relatează aceleași fapte, fără prag de noutate proprie și fără să fie clonă.

    CLONE și DERIVED nu se numără niciodată drept confirmări (`cluster_cross_confirmations`):
    trei publicații care preiau același comunicat sunt o singură origine, nu trei.
    """
    if not group:
        return {}

    entries = []
    for idx, it in enumerate(group):
        url = it.get("url") or it.get("original_link") or f"__idx_{idx}"
        dom = domain_of(it.get("original_link") or url)
        sname = it.get("source_name") or it.get("source") or ""
        txt, anchors = _item_text_and_anchors(it, results_by_url)
        derived = is_derived_attribution(txt, own_domain=dom, own_source_name=sname)
        entries.append({
            "idx": idx,
            "url": url,
            "domain": dom,
            "published_dt": _parse_pub_ts(it.get("published")),
            "anchors": anchors,
            "derived": derived,
            "shingles": _shingles(txt),
        })

    roles: dict[str, str] = {}
    non_derived = [e for e in entries if not e["derived"]]
    pool = non_derived if non_derived else entries
    for e in entries:
        if e["derived"] and non_derived:
            roles[e["url"]] = "DERIVED"

    # Sortare cronologică stabilă pentru alegerea ROOT în fereastra de 15 minute
    pool_chrono = sorted(pool, key=lambda e: (e["published_dt"], e["idx"]))
    earliest = pool_chrono[0]
    t0 = earliest["published_dt"]
    n0 = len(earliest["anchors"])
    root_entry = earliest

    if t0 != datetime.max.replace(tzinfo=timezone.utc):
        window_end = t0 + timedelta(minutes=FIRST_PUBLISHER_WINDOW_MIN)
        in_window = [e for e in pool_chrono if e["published_dt"] <= window_end]
        best_in_window = max(in_window, key=lambda e: (len(e["anchors"]), -e["idx"]))
        if (best_in_window["url"] != earliest["url"]
                and len(best_in_window["anchors"]) >= max(n0 + 2, int(n0 * FIRST_PUBLISHER_DENSITY_RATIO + 0.9999))):
            root_entry = best_in_window

    roles[root_entry["url"]] = "ROOT"
    seen_anchors = set(root_entry["anchors"])
    seen_domains = {root_entry["domain"]} if root_entry["domain"] else set()
    originals = [root_entry]          # textele față de care se măsoară clonarea

    # Greedy set cover pe restul candidaților ne-derivați (cei mai bogați în ancore întâi).
    # Clonarea se verifică ÎNAINTEA noutății: un comunicat rescris poate aduce „ancore noi”
    # doar prin zgomot de formatare, iar originea lui rămâne aceeași.
    remaining = [e for e in pool if e["url"] != root_entry["url"]]
    remaining.sort(key=lambda e: (-len(e["anchors"]), e["published_dt"], e["idx"]))
    for e in remaining:
        if any(o["domain"] != e["domain"]
               and shingle_containment(e["shingles"], o["shingles"]) >= CLONE_CONTAINMENT
               for o in originals):
            roles[e["url"]] = "CLONE"
            continue
        anc = e["anchors"]
        new_anc = anc - seen_anchors
        novelty_ratio = (len(new_anc) / len(anc)) if anc else 0.0
        is_new_domain = not e["domain"] or e["domain"] not in seen_domains
        if (is_new_domain
                and len(new_anc) >= NOVELTY_MIN_ANCHORS
                and novelty_ratio >= NOVELTY_MIN_RATIO):
            roles[e["url"]] = "INDEPENDENT_CONTRIBUTOR"
            seen_anchors |= new_anc
            if e["domain"]:
                seen_domains.add(e["domain"])
        else:
            roles[e["url"]] = "ECHO"
        originals.append(e)

    return roles


NON_CONFIRMING_ROLES = frozenset({"DERIVED", "CLONE"})


def cross_confirmed_domains(group: list,
                            roles_by_url: dict[str, str] | None = None,
                            results_by_url: dict | None = None) -> set:
    """Domeniile care contează ca Confirmări Încrucișate (plan-paradigma-izz.md §3 E3):
    publicații distincte, ne-derivate și ne-clonate, care fie aduc contribuție proprie
    (ROOT / INDEPENDENT_CONTRIBUTOR), fie coroborează cel puțin 2 ancore factuale comune
    cu ROOT (ECHO). Întoarce setul, ca apelantul să-l poată uni peste rulări."""
    if not group:
        return set()
    roles = roles_by_url or classify_cluster_epistemic_roles(group, results_by_url)
    root_anchors: set = set()
    for it in group:
        url = it.get("url") or it.get("original_link") or ""
        if roles.get(url) == "ROOT":
            _, root_anchors = _item_text_and_anchors(it, results_by_url)
            break

    confirmed: set[str] = set()
    for idx, it in enumerate(group):
        url = it.get("url") or it.get("original_link") or f"__idx_{idx}"
        role = roles.get(url, "ECHO")
        if role in NON_CONFIRMING_ROLES:
            continue
        dom = domain_of(it.get("original_link") or url) or url
        if role in ("ROOT", "INDEPENDENT_CONTRIBUTOR"):
            confirmed.add(dom)
        elif root_anchors:
            _, anc = _item_text_and_anchors(it, results_by_url)
            if len(anc & root_anchors) >= 2:
                confirmed.add(dom)
    return confirmed


def cluster_cross_confirmations(group: list,
                                roles_by_url: dict[str, str] | None = None,
                                results_by_url: dict | None = None) -> int:
    """Numărul de Confirmări Încrucișate pentru `group` (minimum 1 — prima relatare)."""
    if not group:
        return 0
    return max(1, len(cross_confirmed_domains(group, roles_by_url, results_by_url)))


# ---------------------------------------------------------------------------
# 3. EXTRACȚIA HTML → TEXT ȘI VALIDATORUL ANTI-PARAZIT
# ---------------------------------------------------------------------------

# Semnături de pagini parazite servite cu HTTP 200: cookie-wall, Cloudflare, paywall.
BOILERPLATE_POISON_PATTERNS = re.compile(
    r"(partenerii noștri prelucrează date|acceptă toate modulele cookie|"
    r"checking your browser before accessing|enable javascript and cookies|"
    r"abonament digital pentru a citi|conținut disponibil doar abonaților)",
    re.IGNORECASE,
)

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False


def _extract_body_sync(html_bytes: bytes, url: str) -> str:
    """HTML → text curat. trafilatura dacă e instalată (local); altfel extractorul
    nativ pe paragrafe <p> — aceeași degradare curată ca la `crawl4ai` (opțional,
    deliberately NEîn requirements: CI rulează calea nativă, care e cea pusă
    la încercare în producție).
    """
    if HAS_TRAFILATURA:
        extracted = trafilatura.extract(
            html_bytes, url=url, include_comments=False,
            include_tables=True, no_fallback=False, favor_precision=True,
        )
        if extracted:
            return extracted.strip()
    decoded = html_bytes.decode("utf-8", errors="replace")
    cleaned = re.sub(r"<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>",
                     " ", decoded, flags=re.DOTALL | re.IGNORECASE)
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", cleaned, flags=re.DOTALL | re.IGNORECASE)
    text_blocks = []
    for p in paragraphs:
        strip_tags = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p))).strip()
        if len(strip_tags) >= 45:
            text_blocks.append(strip_tags)
    return "\n".join(text_blocks)


def validate_extracted_body(body: str, rss_title: str) -> tuple[bool, str | None]:
    """Textul extras e articolul real, nu un cookie-wall/paywall/ciot?

    Trei verificări (Argon): lungimea minimă, semnăturile de paraziți în capul
    textului, suprapunerea lexicală cu titlul RSS. Peste ele, interstitialul
    openresty „One moment, please" — măsurat pe 66 de surse RO (fetch.CHALLENGE_MARK).
    """
    if not body or len(body) < MIN_FULL_TEXT_CHARS:
        return False, f"SHORT_BODY ({len(body) if body else 0} chars)"
    if BOILERPLATE_POISON_PATTERNS.search(body[:600]):
        return False, "COOKIE_OR_PAYWALL_DETECTED"
    title_words = [
        strip_diacritics(w.lower())
        for w in re.findall(r"[a-zA-ZăâîșțĂÂÎȘȚ]{4,}", rss_title)
    ]
    if not title_words:
        return True, None
    body_norm = strip_diacritics(body.lower())
    overlap = sum(1 for w in title_words if w[:5] in body_norm) / len(title_words)
    if overlap < MIN_TITLE_OVERLAP_RATIO:
        return False, f"TITLE_MISMATCH (overlap={overlap:.2f})"
    return True, None


# ---------------------------------------------------------------------------
# 4. MOTORUL FETCH_DEEP: 3,5 s/URL, POLITELY PER DOMENIU, FALLBACK INSTANT
# ---------------------------------------------------------------------------

@dataclass
class DeepResult:
    """Rezultatul E0/E1 pentru un articol membru al unui cluster selectat."""
    url: str
    domain: str
    published: str
    extraction_mode: str                  # FULL_TEXT sau RSS_FALLBACK
    fallback_reason: str | None
    raw_text: str                         # doar în memoria rulării — nu se persistă
    content_sha256: str
    anchors: set = field(default_factory=set)
    sentences: dict = field(default_factory=dict)   # {"S1.1": ...} — consumate de E2
    epistemic_role: str = "ROOT"                    # ROOT | INDEPENDENT_CONTRIBUTOR | ECHO | DERIVED
    caused_dirty: bool = False


def _fetch_single(item: dict, prev: dict | None, domain_sems: dict, sems_lock: threading.Lock) -> DeepResult:
    """Un articol: fetch hard-bounded sau fallback instant pe descrierea RSS.

    Fără headere condiționale (If-None-Match/If-Modified-Since): fetch_deep rulează
    doar pe clusterele active selectate, iar pe un 304 codul lui Argon ar fi rămas
    pe descrierea RSS în loc să folosească textul din tura anterioară — rezoluția
    lui proprie: pur și simplu nu trimite headerele.
    """
    title = (item.get("original_title") or item.get("title") or "").strip()
    description = (item.get("description") or "").strip()
    rss_fallback = f"{title}. {description}".strip()
    mode, reason, usable = "RSS_FALLBACK", None, rss_fallback
    url = item.get("original_link") or item.get("url") or ""
    dom = domain_of(url)
    new_sha = ""
    anchors: set = set()

    try:
        req = fetch.urllib.request.Request(url, headers={
            "User-Agent": fetch.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        })
        with sems_lock:
            sem = domain_sems.setdefault(dom, threading.Semaphore(MAX_PER_DOMAIN))
        with sem:
            with fetch._deschide(req, timeout=FETCH_TIMEOUT_S) as resp:
                raw = fetch._read_limitat(resp)
        if fetch._is_challenge(raw):
            reason = "CHALLENGE_INTERSTITIAL"
        else:
            body = _extract_body_sync(raw, url)
            valid, why = validate_extracted_body(body, title)
            if valid:
                mode = "FULL_TEXT"
                # garda de dublare a titlului (nota de integrare Argon): dacă extractorul
                # a inclus deja titlul în prima linie, nu-l lipim din nou.
                usable = body if body.startswith(title[:30]) else f"{title}. {body}"
            else:
                reason = why
    except (fetch.urllib.error.HTTPError, fetch.urllib.error.URLError,
            fetch.socket.timeout, ValueError, OSError, TimeoutError) as exc:
        reason = f"{type(exc).__name__}"
    except Exception as exc:                     # o sursă stricată nu pică rularea
        reason = f"UNEXPECTED_{type(exc).__name__}"

    new_sha = compute_sha256(usable)
    anchors = extract_quick_anchors(usable)
    prev_meta = prev or {}
    dirty = check_if_silent_edit_causes_dirty(
        "ROOT",
        prev_meta.get("sha256"), new_sha,
        set(prev_meta.get("anchors") or []), set(anchor_sample(anchors)),
    )
    return DeepResult(
        url=item.get("url") or url, domain=dom,
        published=item.get("published") or datetime.now(timezone.utc).isoformat(),
        extraction_mode=mode, fallback_reason=reason,
        raw_text=usable, content_sha256=new_sha, anchors=anchors,
        caused_dirty=dirty,
    )


def fetch_deep(groups: list, meta_path: str | None = None, persist: bool = True) -> dict:
    """E0 + E1-core pe clusterele selectate. `groups` = clusterele `syn` din `process_new`
    (liste de articole). Returnează rezultatele per URL — propozițiile S1.1 pentru
    promptul E2 + rolurile epistemice + contorii în `stats()`. Atașează pe fiecare item
    în memorie câmpurile temporare `_deep_*` (curățate de `state._scrub_processed`).
    Meta (sha + ancore) se salvează în `data/deep_meta.json` doar când `persist`.
    """
    _STATISTICI.clear()
    meta_path = meta_path or META_PATH
    meta = _meta_load(meta_path)
    meta = _prune(meta)

    # articole unice prin URL — un articol absorbit cross-run nu se re-fetch-ează de două ori
    uniq: dict[str, dict] = {}
    for g in groups:
        for it in g:
            uniq.setdefault(it.get("url"), it)
    if not uniq:
        if persist:
            _meta_save(meta, meta_path)   # prune-ul se perpetuă chiar și fără clustere noi
        return {}

    prev_snapshot = {u: dict(meta[u]) for u in uniq if u in meta}

    domain_sems: dict[str, threading.Semaphore] = {}
    sems_lock = threading.Lock()
    results: dict[str, DeepResult] = {}
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = {
            pool.submit(_fetch_single, item, prev_snapshot.get(item.get("url")), domain_sems, sems_lock):
                item.get("url")
            for item in uniq.values()
        }
        try:
            for future in as_completed(futures, timeout=DEEP_BATCH_TIMEOUT_S):
                r: DeepResult = future.result()
                results[r.url] = r
        except TimeoutError:
            # restul devin fallback instant — rularea orară nu așteaptă după surse moarte
            for url in futures.values():
                if url not in results:
                    results[url] = _fallback_result(uniq[url])

    # E1-core: clasificarea rolurilor epistemice per cluster (ROOT / INDEPENDENT_CONTRIBUTOR /
    # ECHO / DERIVED), evaluarea driftului pe rolul real și numerotarea propozițiilor S1..Sn.
    for g in groups:
        roles = classify_cluster_epistemic_roles(g, results)
        for idx, it in enumerate(g, start=1):
            url = it.get("url")
            r = results.get(url)
            if r is None:
                continue
            role = roles.get(url, "ROOT")
            r.epistemic_role = role
            prev_meta = prev_snapshot.get(url) or {}
            role_for_dirty = prev_meta.get("role") or role
            r.caused_dirty = check_if_silent_edit_causes_dirty(
                role_for_dirty,
                prev_meta.get("sha256"), r.content_sha256,
                set(prev_meta.get("anchors") or []), set(anchor_sample(r.anchors)),
            )
            max_sents = MAX_SENTENCES if role in ("ROOT", "INDEPENDENT_CONTRIBUTOR") else MAX_SENTENCES_ECHO
            r.sentences = split_romanian_sentences(
                r.raw_text, source_id=f"S{idx}", max_sentences=max_sents
            )
            # Atașare temporară în memorie pentru consumatorii din aceeași rulare (E1/E2);
            # `state._scrub_processed` le șterge înainte de scrierea în `data/articles.json`.
            it["_deep_sentences"] = dict(r.sentences)
            it["_deep_mode"] = r.extraction_mode
            it["_deep_anchors"] = anchor_sample(r.anchors)
            it["_epistemic_role"] = role
            it["_caused_dirty"] = r.caused_dirty

    for r in results.values():
        _STATISTICI[r.extraction_mode] += 1
        if r.caused_dirty:
            _STATISTICI["SILENT_EDIT_DIRTY"] += 1
        meta[r.url] = {
            "sha256": r.content_sha256,
            "anchors": anchor_sample(r.anchors),
            "mode": r.extraction_mode,
            "role": r.epistemic_role,
            "published": r.published,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    if persist:
        _meta_save(meta, meta_path)

    full = _STATISTICI.get("FULL_TEXT", 0)
    fb = _STATISTICI.get("RSS_FALLBACK", 0)
    print(f">> E0 fetch_deep: {len(results)} articole în {len(groups)} clustere selectate — "
          f"{full} text integral, {fb} fallback RSS")
    return results


def format_cluster_for_llm_prompt(cluster_id: str, group: list,
                                  results_by_url: dict | None = None) -> str:
    """Generează blocul indexat `[S1] Dom: ... | Ora: ... | Rol: ... | Mod: ...` cu
    propozițiile `[S1.1] ...` pentru promptul sintezei dialectice (E2)."""
    roles = classify_cluster_epistemic_roles(group, results_by_url)
    lines = [
        f"CLUSTER_ID: {cluster_id}",
        f"SURSE ÎN CLUSTER ({len(group)}):",
        "",
    ]
    for idx, it in enumerate(group, start=1):
        url = it.get("url") or it.get("original_link") or ""
        dom = domain_of(it.get("original_link") or url)
        pub = (it.get("published") or "")[:16]
        r = (results_by_url or {}).get(url)
        role = (r.epistemic_role if r else None) or it.get("_epistemic_role") or roles.get(url, "ECHO")
        mode = (r.extraction_mode if r else None) or it.get("_deep_mode") or "RSS_FALLBACK"
        sents = (r.sentences if r and r.sentences else None) or it.get("_deep_sentences")
        if not sents:
            txt, _ = _item_text_and_anchors(it, results_by_url)
            max_s = MAX_SENTENCES if role in ("ROOT", "INDEPENDENT_CONTRIBUTOR") else MAX_SENTENCES_ECHO
            sents = split_romanian_sentences(txt, source_id=f"S{idx}", max_sentences=max_s)
        lines.append(f"[S{idx}] Dom: {dom} | Ora: {pub} | Rol: {role} | Mod: {mode}")
        for chunk_id, sentence_text in sents.items():
            lines.append(f"  [{chunk_id}] {sentence_text}")
        lines.append("")
    return "\n".join(lines).strip()


def _fallback_result(item: dict) -> DeepResult:
    """Fallback-ul de timp: nici măcar descrierea RSS nu se mai așteaptă de la rețea
    când fereastra batch-ului s-a închis — textul de rezervă e deja în item."""
    title = (item.get("original_title") or item.get("title") or "").strip()
    usable = f"{title}. {item.get('description') or ''}".strip()
    return DeepResult(
        url=item.get("url"), domain=domain_of(item.get("original_link") or item.get("url") or ""),
        published=item.get("published") or datetime.now(timezone.utc).isoformat(),
        extraction_mode="RSS_FALLBACK", fallback_reason="BATCH_TIMEOUT",
        raw_text=usable, content_sha256=compute_sha256(usable),
        anchors=extract_quick_anchors(usable),
    )


# ---------------------------------------------------------------------------
# 5. MAGAZINUL META (sha + ancore) — oglinda state.expire pe TTL
# ---------------------------------------------------------------------------

def _meta_load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _meta_save(meta: dict, path: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=1)
    except OSError:
        pass


def _prune(meta: dict) -> dict:
    """Aceleași 12 zile ca `state.expire`: intrările fără articol viu în fereastra
    TTL dispar, ca meta să nu crească nesfârșit (cheile sunt URL-uri de articole,
    iar articolele expiră prin exact acest cutoff)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.ARTICLE_TTL_DAYS)
    kept = {}
    for url, entry in meta.items():
        try:
            ts = datetime.fromisoformat(entry.get("published") or "")
        except (ValueError, TypeError):
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            kept[url] = entry
    return kept
