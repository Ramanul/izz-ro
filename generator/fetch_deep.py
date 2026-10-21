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
MAX_SENTENCES = 25            # buget de context per sursă în promptul E2
MIN_SENTENCE_CHARS = 18       # fragmentele mai scurte (cioate de titlu) se lipesc de următoarea
MAX_ANCHORS_STORED = 80       # plafon de stocare per articol; Jaccard-ul e stabil mult sub atât

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
# 2. ANCORE, SHA-256 ȘI DRIFT (baza pentru E1: modificările tăcute)
# ---------------------------------------------------------------------------

_NUM_ANCHOR_RE = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")
_MID_CAPS_RE = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-ZĂÂÎȘȚ][a-zăâîșțA-ZĂÂÎȘȚ]{3,}\b")


def strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def extract_quick_anchors(text: str) -> set:
    """Ancore factuale (cifre + entități cu majusculă) pentru calculul de drift."""
    anchors: set = set()
    for num in _NUM_ANCHOR_RE.findall(text):
        anchors.add(f"NUM:{num.replace(',', '.')}")
    for ent in _MID_CAPS_RE.findall(text):
        norm = strip_diacritics(ent.lower())
        stem = norm[:-2] if len(norm) > 6 else norm   # pseudo-stemming RO (Guvernului -> guvern)
        anchors.add(f"ENT:{stem}")
    return anchors


def compute_sha256(text: str) -> str:
    """Hash determinist pe textul normalizat (ignoră variații de whitespace)."""
    norm = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def check_if_silent_edit_causes_dirty(role: str, old_sha: str | None, new_sha: str,
                                      old_anchors: set | None, new_anchors: set) -> bool:
    """O sursă cu rol epistemic greu (ROOT / INDEPENDENT_CONTRIBUTOR) care își schimbă
    conținutul cu peste 20% drift pe ancore, după ce a fost procesată, murdărește
    clusterul — sinteza înghecată ar publica minciuna veche (Argon, «Silent Edit
    Desync»). Rolul vine de la E1; până atunci apelantul E0 trece „ROOT" pentru
    toate — conservator, iar flagul nu e consumat încă de nicio decizie.
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
    """Rezultatul E0 pentru un articol membru al unui cluster selectat."""
    url: str
    domain: str
    published: str
    extraction_mode: str                  # FULL_TEXT sau RSS_FALLBACK
    fallback_reason: str | None
    raw_text: str                         # doar în memoria rulării — nu se persistă
    content_sha256: str
    anchors: set = field(default_factory=set)
    sentences: dict = field(default_factory=dict)   # {"S1.1": ...} — consumate de E2
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
        "ROOT",                            # E1 va trece rolul epistemic real
        prev_meta.get("sha256"), new_sha,
        set(prev_meta.get("anchors") or []), anchors,
    )
    return DeepResult(
        url=item.get("url") or url, domain=dom,
        published=item.get("published") or datetime.now(timezone.utc).isoformat(),
        extraction_mode=mode, fallback_reason=reason,
        raw_text=usable, content_sha256=new_sha, anchors=anchors,
        caused_dirty=dirty,
    )


def fetch_deep(groups: list, meta_path: str | None = None, persist: bool = True) -> dict:
    """E0 pe clusterele selectate. `groups` = clusterele `syn` din `process_new`
    (liste de articole). Returnează rezultatele per URL — propozițiile S1.1 pentru
    promptul E2 + contorii în `stats()`. Meta (sha + ancore) se salvează în
    `data/deep_meta.json` doar când `persist` (dry-run nu scrie stare).
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

    domain_sems: dict[str, threading.Semaphore] = {}
    sems_lock = threading.Lock()
    results: dict[str, DeepResult] = {}
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = {
            pool.submit(_fetch_single, item, meta.get(item.get("url")), domain_sems, sems_lock):
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

    # numerotarea S1..Sn e PER CLUSTER (formatul promptului E2), deci propozițiile
    # se calculează după fetch, în contextul clusterului.
    for g in groups:
        for idx, it in enumerate(g, start=1):
            r = results.get(it.get("url"))
            if r is not None:
                r.sentences = split_romanian_sentences(r.raw_text, source_id=f"S{idx}")

    for r in results.values():
        _STATISTICI[r.extraction_mode] += 1
        if r.caused_dirty:
            _STATISTICI["SILENT_EDIT_DIRTY"] += 1
        meta[r.url] = {
            "sha256": r.content_sha256,
            "anchors": sorted(r.anchors)[:MAX_ANCHORS_STORED],
            "mode": r.extraction_mode,
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
