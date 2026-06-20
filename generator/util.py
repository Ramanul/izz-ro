"""Utilitare comune: normalizare URL, text fara diacritice, taiere la N cuvinte."""
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# Parametri de tracking eliminati la normalizarea URL-ului (pentru dedup stabil)
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref", "ref_src"}

_STOPWORDS_RO = {
    "si", "sau", "dar", "insa", "ca", "ce", "cu", "de", "din", "in", "intr", "intre",
    "la", "pe", "pentru", "prin", "spre", "sub", "un", "una", "unui", "unei", "o",
    "este", "sunt", "era", "fost", "fi", "are", "au", "avea", "va", "vor", "fie",
    "se", "sa", "isi", "lui", "ei", "lor", "cel", "cea", "cei", "cele", "acest",
    "acesta", "aceasta", "acestei", "acestui", "dupa", "fara", "mai", "mult", "foarte",
    "care", "cand", "cum", "unde", "nu", "da", "the", "a", "an", "of", "to", "in",
}


def strip_diacritics(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_url(url: str) -> str:
    """Cheie de dedup: scheme+host lowercase, fara query de tracking, fara fragment, fara '/' final."""
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    query_pairs = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not k.lower().startswith(_TRACKING_PREFIXES) and k.lower() not in _TRACKING_KEYS
    ]
    query = urlencode(query_pairs)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, query, ""))


def domain_of(url: str) -> str:
    try:
        netloc = urlsplit(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except ValueError:
        return ""


def truncate_words(text: str, max_words: int) -> str:
    """Taie la max_words cuvinte (apararea in adancime daca AI depaseste limita)."""
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).rstrip(",.;:") + "..."


def title_tokens(title: str) -> set:
    """Tokeni semnificativi dintr-un titlu, pentru clustering: lowercase, fara diacritice, fara stopwords."""
    norm = strip_diacritics(title.lower())
    words = re.findall(r"[a-z0-9]+", norm)
    return {w for w in words if len(w) > 3 and w not in _STOPWORDS_RO}
