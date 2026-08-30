"""Utilitare comune: normalizare URL, text fara diacritice, taiere la N cuvinte."""
import re
import html as _html
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

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
    # temporal: false-pozitive la _dedup (expresii de timp generice)
    "pana", "sfarsitul", "inceputul", "luna", "lunii", "anul", "anului", "saptamana",
    "saptamanii", "astazi", "maine", "ieri", "data", "ora", "orei", "zile", "zilei",
    # luni (creeaza falsa similaritate intre stiri diferite)
    "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
    "august", "septembrie", "octombrie", "noiembrie", "decembrie",
    # cantitati generice
    "milioane", "miliarde", "mii", "sute", "aproximativ", "circa",
}


def strip_diacritics(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_url(url: str) -> str:
    """Cheie de dedup: scheme+host lowercase, fara query de tracking, fara fragment, fara '/' final."""
    if not url:
        return ""
    try:
        url_stripped = url.strip()
        if url_stripped and "://" not in url_stripped and not url_stripped.startswith("//"):
            url_stripped = "https://" + url_stripped
        parts = urlsplit(url_stripped)
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


def clean_html(text: str) -> str:
    """Scoate tagurile HTML, decodeaza entitatile, normalizeaza spatiile.

    Necesar fiindca multe feeduri RSS pun HTML + footer ('(c) Sursa') in <description>.
    """
    if not text:
        return ""
    # ORDINEA CONTEAZA, si a fost gresita pana pe 2026-08-09: se taiau tagurile si ABIA APOI
    # se decodau entitatile, deci `&lt;img onload=...&gt;` trecea intreg de taiere (nu e tag
    # inca) si REDEVENEA markup dupa decodare. Asa a ajuns un payload de script, ca text
    # vizibil, in teaserele de pe izz.ro — evaziune clasica prin dubla codare.
    # Se itereaza pana la punct fix fiindca si codarea poate fi dubla (`&amp;lt;img`).
    for _ in range(3):
        nou = _TAG_RE.sub(" ", _html.unescape(text))
        if nou == text:
            break
        text = nou
    # taie footerele RSS boilerplate de la coada
    text = re.sub(r"\[\s*[….]+\s*\]", " ", text)               # [...] / […]
    text = re.sub(r"[\(\[]?\s*(?:\(c\)|©)[^.]*\.?\s*$", "", text, flags=re.IGNORECASE)
    # WordPress footer: "The post ..." (cu sau fara "appeared first on")
    text = re.sub(r"\s*The post\b.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    # Romanian footer oriunde in text
    text = re.sub(r"\s*apare prima dat[aă]\s+[îi]n\s+\S+.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\s*appeared first on\s+\S+.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\s*Cite[șs]te\s+mai\s+mult.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*Read more.*$", "", text, flags=re.IGNORECASE)
    # markeri de lista (•, ‣, ●, ▪, –/- la inceput de fapt) -> proza curgatoare
    text = re.sub(r"^\s*[•‣●▪]\s*", "", text)          # bullet la inceput
    text = re.sub(r"\s*[•‣●▪]\s*", " ", text)          # bullet ca separator
    return _WS_RE.sub(" ", text).strip()


#: Plafonul pe caractere se DERIVA din cel pe cuvinte, nu e o constanta fixa: un plafon fix
#: ar fi taiat sintezele (SYNTHESIS_MAX_WORDS=90) sau ar fi lasat teaserele nepazite.
#: Masurat pe 6714 campuri reale din corpusul de 3380 de articole (2026-08-09):
#:   teaser    mediana 6.85, p99 8.67, MAXIM 11.60 car/cuvant
#:   synthesis mediana 6.82, p99 8.18, MAXIM  8.64
#:   title     mediana 6.64, p99 9.25, MAXIM 11.00
#: Continutul otravit de pe feedul compromis: 32.4-47.8 car/cuvant.
#: 16 sta la 38% peste maximul legitim observat si la jumatate din cel mai BLAND atac —
#: margine in ambele directii, nu o cifra aleasa din intuitie.
MAX_CHARS_PER_WORD = 16


def truncate_words(text: str, max_words: int, max_chars: int | None = None) -> str:
    """Taie la max_words cuvinte SI la un plafon de caractere (aparare in adancime).

    Plafonul pe caractere a fost adaugat pe 2026-08-09, dupa ce feedul primariei Rovinari
    (compromis) a livrat un teaser de 1913 caractere in doar 40 de cuvinte: JavaScript
    comprimat nu are spatii, deci un singur „cuvant" avea 866 de caractere. Plafonul pe
    cuvinte a tinut perfect — numara unitatea gresita. Un jeton pe care browserul nu-l poate
    rupe in randuri umfla cardul si il suprapune peste vecin, deci a fost si un defect de
    LAYOUT, nu doar de continut; partea de CSS e `overflow-wrap` in `static/styles.css`.
    """
    if not text:
        return ""
    if max_chars is None:
        max_chars = max_words * MAX_CHARS_PER_WORD
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip(",.;:") + "..."
    text = text.strip()
    if len(text) > max_chars:
        # taie pe ultima granita de cuvant dinainte de plafon; daca nu exista niciuna in
        # jumatatea a doua (un singur jeton urias), taie brutal — un teaser stalcit e mai
        # ieftin decat o pagina stricata
        taiat = text[:max_chars]
        spatiu = taiat.rfind(" ")
        text = (taiat[:spatiu] if spatiu > max_chars // 2 else taiat).rstrip(",.;:") + "..."
    return text


def title_tokens(title: str) -> set:
    """Tokeni semnificativi dintr-un titlu, pentru clustering: lowercase, fara diacritice, fara stopwords."""
    norm = strip_diacritics(title.lower())
    words = re.findall(r"[a-z0-9]+", norm)
    return {w for w in words if len(w) > 3 and w not in _STOPWORDS_RO}


def cuvinte_adaugate(title: str, description: str) -> int:
    """Cate cuvinte aduce descrierea PESTE cele din titlu.

    Masura substantei unui item de RSS. Multe surse trimit `description` identica cu `title`
    (masurat 2026-08-04: 58 din 256 de iteme au 0-4 cuvinte in plus, iar sase surse sunt 100%
    asa) — pentru alea nu exista NIMIC de sintetizat, iar un model caruia i se cere totusi un
    rezumat nu poate produce decat o parafraza a titlului. Daca titlul e clickbait, iese
    clickbait fluent, care trece de orice verificare de forma. Vezi specs/sinteza-fara-substanta.md.

    Se numara cuvinte, nu caractere, si se ignora ordinea: o descriere care REPETA titlul si
    apoi adauga fapte trebuie sa treaca. Fara stopwords-uri scoase — la 25 de cuvinte,
    prepozitiile chiar diferentiaza o propozitie noua de una repetata.
    """
    def _cuv(s: str) -> list:
        return re.findall(r"[a-z0-9]+", strip_diacritics((s or "").lower()))

    din_titlu = set(_cuv(title))
    return sum(1 for w in _cuv(description) if w not in din_titlu)


# --- titlu care nu e titlu ------------------------------------------------------------------
#
# DE CE (masurat 2026-08-30, raportat de proprietar). Doua iteme au ajuns publicate cu titlul
# format EXCLUSIV dintr-o data calendaristica: `27.08.2026` si `17.08.2026`, ambele de la
# CJ Giurgiu, categoria `judetean`. §7 e explicit — pipeline-ul nu publica niciodata titluri
# brute sau stricate; daca o cale de fallback nu atinge bara, SARE itemul. Sursele oficiale
# locale ocolesc AI-ul (`specs/local-official-no-ai.md`), deci titlul din feed ajunge nefiltrat
# pe site si nimic nu-l oprea.
#
# CE PRINDE, ingust dinadins: titlul e DOAR o data, eventual cu un cuvant-eticheta lipit
# („Anunt 27.08.2026" ramane titlu valid — spune ceva). Nu incearca sa judece calitatea in
# general; aia cere AI si e alta discutie.
DOAR_O_DATA = re.compile(
    r"^\s*(?:nr\.?\s*\d+\s*)?"                              # „nr. 12" optional in fata
    r"\d{1,2}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{2,4}"       # 27.08.2026 / 27-08-26
    r"\s*$"
)
DOAR_O_DATA_ISO = re.compile(r"^\s*\d{4}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}\s*$")


def titlu_e_doar_o_data(title: str) -> bool:
    """True daca tot titlul e o data calendaristica, deci nu spune nimic despre stire."""
    if not title:
        return False
    return bool(DOAR_O_DATA.match(title) or DOAR_O_DATA_ISO.match(title))
