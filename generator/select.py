"""Logica editoriala PURA: ce se publica, in ce ordine, ce se arunca.

Extras din `render.py` (1001 linii, 52 de revizii, 4 responsabilitati amestecate). Linia de
taiere e „pur vs. cu efecte": aici intra dict/lista si iese bool/lista — fara disk, fara
retea, fara Jinja, fara config. Restul randarii ramane in `render.py`.

De ce contine exact functiile astea: ele decid CE APARE PE SITE (regula „Zero Zgomot",
CLAUDE.md §7), deci sunt cele care merita testate izolat. Acoperirea lor e in
`tests/test_render_editorial.py`, scrisa INAINTE de mutare tocmai ca sa dovedeasca faptul
ca mutarea n-a schimbat comportament.

NU s-a mutat `assign_slugs`, desi atribuie sloguri: cheama `_human_date`, deci amesteca
identitatea articolului cu formatarea pentru afisare. Ar trage randarea dupa el aici.
"""
import re

from slugify import slugify

from . import config
from .util import title_tokens, domain_of

def _dedup(articles: list) -> list:
    """Elimina articolele despre acelasi eveniment (titluri foarte asemanatoare).

    Pastreaza varianta cea mai bogata: C inaintea B, mai multe surse, mai recent.
    """
    ordered = sorted(articles, key=lambda a: a.get("published") or "", reverse=True)
    ordered.sort(key=lambda a: (0 if a.get("model") == "C" else 1, -len(a.get("sources") or [])))
    kept, kept_tok = [], []
    for a in ordered:
        tok = title_tokens(a.get("title") or a.get("original_title") or "")
        is_dup = False
        for kt in kept_tok:
            if not tok or not kt:
                continue
            inter = len(tok & kt)
            if inter >= 4 or inter / len(tok | kt) >= 0.55:
                is_dup = True
                break
        if not is_dup:
            kept.append(a)
            kept_tok.append(tok)
    return kept

def _diversify(items: list, max_run: int = 2) -> list:
    """Reordonare blanda anti-monotonie (regula 'source diversity'): pastreaza
    ordinea cronologica, dar acelasi domeniu-sursa nu apare mai mult de `max_run`
    ori consecutiv -- urmatorul articol de la alta sursa e tras in fata.
    Nu elimina nimic; sursele vorbarete (ex. Digi24 Extern, 53% din extern) doar
    se intretes cu restul in loc sa monopolizeze vizual sectiunea.
    """
    def dom(a: dict) -> str:
        return domain_of(a.get("original_link") or "") or a.get("source_name", "")

    pool, out = list(items), []
    while pool:
        tail = [dom(x) for x in out[-max_run:]]
        idx = 0
        if len(tail) == max_run and len(set(tail)) == 1:
            idx = next((i for i, a in enumerate(pool) if dom(a) != tail[0]), 0)
        out.append(pool.pop(idx))
    return out

def _entity_index(articles: list) -> dict:
    """Slug -> {name, articles} pentru entitatile AI cu >=2 aparitii publicate.
    Grauntele grafului cunoasterii: pagini statice /subiect/<slug>/."""
    idx: dict = {}
    for a in articles:
        for e in a.get("entities") or []:
            s = slugify(e)[:60]
            if not s:
                continue
            d = idx.setdefault(s, {"name": e, "articles": []})
            d["articles"].append(a)
    return {s: d for s, d in idx.items() if len(d["articles"]) >= 2}

def _pick_hero(articles: list) -> list:
    featured = [a for a in articles if a.get("featured")]
    rest = [a for a in articles if not a.get("featured")]
    # prioritate: AI (gemini) inaintea fallback, apoi clustere C, apoi cele mai recente
    rest_sorted = sorted(rest, key=lambda a: a.get("published") or "", reverse=True)
    rest_sorted.sort(key=lambda a: (a.get("processed_by") != "gemini", a.get("model") != "C"))
    return (featured + rest_sorted)[:6]

def _dedup_sources(a: dict) -> None:
    """Surse unice dupa domeniu (evita 'Digi24' + 'Digi24 Extern' duplicate pe acelasi card,
    inclusiv pentru clustere C deja salvate in state inainte de acest fix)."""
    seen, out = set(), []
    for s in a.get("sources") or []:
        d = domain_of(s.get("url", ""))
        if d in seen:
            continue
        seen.add(d)
        out.append(s)
    if out:
        a["sources"] = out

_BODY_PLACEHOLDERS = {"Detalii pe sursa.", "Detalii pe surse.", ""}
_OFFICIAL_DISPLAY_TITLE_MAX = 110


def _titlu_scurt(text: str, limit: int = 84) -> str:
    """Taie la cuvânt și normalizează titlurile scrise integral cu majuscule."""
    text = " ".join(text.split()).strip(" ,;:–—-")
    letters = [char for char in text if char.isalpha()]
    if letters and sum(char.isupper() for char in letters) / len(letters) > .8:
        text = text.lower().capitalize()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:–—-")
    return f"{cut}…" if cut else text[:limit - 1].rstrip(" ,;:–—-") + "…"


def _dupa_indicator(title: str, pattern: str) -> str:
    match = re.search(pattern, title, flags=re.I)
    return match.group(1).strip() if match else ""


def titlu_afisare(a: dict) -> str:
    """Întoarce titlul destinat citirii, fără a rescrie titlul sursei din date.

    Anunțurile instituțiilor sunt adesea titluri juridice de sute de caractere. Pentru
    categoriile repetitive — recrutare, promovare, hotărâri, consultări și achiziții —
    se extrage subiectul util pentru cititor. Titlul integral rămâne în date și este
    disponibil ca detaliu secundar pe pagină. Orice alt titlu oficial foarte lung are
    o limită de siguranță la cuvânt, ca să nu rupă ierarhia mobilă.
    """
    title = " ".join((a.get("title") or "").split())
    if a.get("processed_by") != "official" or len(title) <= _OFFICIAL_DISPLAY_TITLE_MAX:
        return title

    source = " ".join((a.get("source_name") or "instituția emitentă").split())
    low = title.casefold()

    if re.search(r"\bconcurs(?:ul)?\b", title, flags=re.I):
        job = re.search(
            r"post(?:\s+vacant)?(?:,\s*contractual\s+de\s+execuție)?"
            r"(?:,\s*cu)?\s+normă\s+(?:întreagă|parțială)\s+de\s+(.+?)"
            r"(?=\s+(?:la|în\s+cadrul)\b|,|$)",
            title,
            flags=re.I,
        )
        if job:
            display = f"Concurs pentru {_titlu_scurt(job.group(1).strip(), 76)} la {source}"
        else:
            display = f"Concurs de recrutare la {source}"
    elif "examenul de promovare" in low or "concursul de promovare" in low:
        display = f"Examen de promovare la {source}"
    elif "proiect de hotărâre" in low or "proiectului de act normativ" in low:
        number = _dupa_indicator(title, r"proiect\s+de\s+hotărâre\s*(?:nr\.?\s*)?([\d]+(?:/[\d]+)?)")
        subject = _dupa_indicator(title, r"\bprivind\s+(.+)") or _dupa_indicator(title, r"\bcu\s+scopul\s+(.+)")
        label = f"Proiect de hotărâre nr. {number}" if number else "Proiect de hotărâre"
        display = f"{label}: {_titlu_scurt(subject, 76)}" if subject else f"{label} la {source}"
    elif re.search(r"\bhotărâr|\bhotarar|\bhcl\b", low):
        number = _dupa_indicator(title, r"(?:hotărârea|hotararea|hotărâre|hotarare)\s*(?:nr\.?\s*)?([\d]+(?:/[\d]+)?)")
        subject = _dupa_indicator(title, r"\bprivind\s+(.+)") or _dupa_indicator(title, r"\bpentru\s+(.+)")
        label = f"Hotărârea nr. {number}" if number else "Hotărâre de consiliu"
        display = f"{label}: {_titlu_scurt(subject, 78)}" if subject else f"{label} la {source}"
    elif any(marker in low for marker in ("achizi", "catalogul electronic", "ofertelor", "seap", "sicap")):
        subject = _dupa_indicator(title, r"\bpentru\s*:\s*(.+)") or _dupa_indicator(title, r"\bprivind\s+(.+)")
        display = f"Achiziție: {_titlu_scurt(subject, 78)}" if subject else f"Achiziție publică la {source}"
    else:
        display = title

    # Ultima barieră este intenționat comună tuturor regulilor. O denumire de instituție
    # foarte lungă sau o expresie nouă nu poate depăși limita de citire pe mobil.
    return _titlu_scurt(display, _OFFICIAL_DISPLAY_TITLE_MAX)


def filtru_cautare_rapida(a: dict) -> str:
    """Întoarce filtrul compact de căutare pentru un anunț oficial sau șirul gol.

    Etichetele sunt deliberat puține și orientate pe intenția de căutare mobilă. Nu
    înlocuiesc categoria editorială, care rămâne disponibilă în selectorul clasic.
    """
    if a.get("processed_by") != "official":
        return ""
    low = " ".join((a.get("title") or "").split()).casefold()
    if "examenul de promovare" in low or "concursul de promovare" in low or \
            re.search(r"\bconcurs(?:ul)?\b", low):
        return "concursuri"
    if "proiect de hotărâre" in low or "proiectului de act normativ" in low or \
            re.search(r"\bhotărâr|\bhotarar|\bhcl\b", low):
        return "hotarari"
    if any(marker in low for marker in ("achizi", "catalogul electronic", "ofertelor", "seap", "sicap")):
        return "achizitii"
    return "oficiale"


def anunt_oficial_fara_corp(a: dict) -> bool:
    """True daca articolul e un anunt oficial (pl_/cj_/pr_) care nu are corp de text.

    Decizie proprietar 2026-08-04 (specs/sinteza-fara-substanta.md): anunturile de primarie se
    publica cu titlul original NEATINS + link, fara teaser inventat. Pana acum se pierdeau tacut:
    `process_official` le punea "Detalii pe sursa.", care e in `_BODY_PLACEHOLDERS`, deci poarta
    le respingea.

    „Fara corp" acopera DOUA forme, pentru ca ambele inseamna acelasi lucru — sursa n-a trimis
    nimic peste titlu: (1) placeholder-ul, cand feed-ul n-are `description`; (2) teaser identic cu
    titlul, cand feed-ul repeta titlul in `description` (masurat 2026-08-04 pe `data/articles.json`:
    69 din prima forma, 10 din a doua, 79 in total, toate `local`, toate cu link).

    Predicat SINGUR, folosit si de poarta si de randare, ca cele doua sa nu se poata departa:
    daca poarta publica un articol pe care randarea nu-l stie fara corp, iese cardul cu gaura.
    """
    if a.get("processed_by") != "official":
        return False
    body = (a.get("teaser") or "").strip()
    return body in _BODY_PLACEHOLDERS or body == (a.get("title") or "").strip()

_TITLU_URL = re.compile(r"^(https?://|www\.)\S*$", re.I)
_TITLU_FISIER = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|jpe?g|png|zip)$", re.I)
# Cuvant = secventa de LITERE, nu ce da `.split()`: „41 mana+fainare+putregai" are 2 bucati
# separate de spatiu, dar 3 cuvinte reale. Masurat: e singurul fals-pozitiv pe care il face
# `.split()` pe corpusul de azi. NU se foloseste `util.title_tokens`, care taie stopwords si
# cuvintele de ≤3 litere — ar respinge „43 Afide la pomi" si „Anunț PUZ" din motive gresite.
_TITLU_CUVANT = re.compile(r"[a-zA-ZăâîșşțţĂÂÎȘŞȚŢ]{2,}")
_TITLU_GENERIC = {
    "anunt", "anunț", "anunturi", "anunțuri", "public", "publica", "publică",
    "publicitate", "publicitar", "publicitara", "publicitară", "comunicat", "comunicare",
    "informare", "publicatie", "publicație", "document", "documente", "fisier", "fișier",
    "atasament", "atașament", "pdf", "doc", "docx", "stire", "știre",
}

def titlu_fara_informatie(title: str) -> bool:
    """True daca titlul singur nu spune cititorului NIMIC despre subiect.

    Se aplica DOAR anunturilor oficiale fara corp (vezi `anunt_oficial_fara_corp`): acolo titlul
    e tot ce se publica, deci un titlu gol de informatie da un card care nu comunica nimic.
    Restul articolelor au corp si nu trec pe aici.

    Cele patru forme, in ordinea in care apar in feeduri (masurat 2026-08-04 pe cele 69 de
    anunturi fara corp de pe `main`; respinge 5, zero fals-pozitive):
      1. URL pus ca titlu;
      2. nume de fisier — extensie, sau ≥2 underscore-uri (`CP_Renta viagera_C2025_29.07.2026`).
         Pragul e ≥2, nu ≥1, tocmai ca `SITUATII FINANCIARE TRIM II_2026` sa ramana publicabil;
      3. titlu format DOAR din cuvinte generice de anunt (`ANUNȚ PUBLIC`, `Publicitate`);
      4. sub 3 cuvinte (`Anunț PUZ`). Pragul de 4 ar arunca gresit `Concurs Functii publice`.

    Respinsa dupa masurare: regula „titlul incepe cu numar de ordine" (`^\\d{1,4}\\s`) — prinde 5
    iteme, din care 4 sunt buletinele fitosanitare de la Urlati (`43 Afide la pomi`), care au
    prefix numeric legitim.

    Limita cunoscuta, neacoperita deliberat: `DEMETER JOZSEF NIMROD – 27.07.2026` trece — nu e URL,
    nu e fisier, nu e generic, are 3 cuvinte. Nicio regula mecanica nu-l prinde fara sa arunce si
    publicatiile de casatorie legitime, care au exact acelasi tipar nume+data.
    """
    t = (title or "").strip()
    if not t:
        return True
    if _TITLU_URL.match(t):
        return True
    if _TITLU_FISIER.search(t) or t.count("_") >= 2:
        return True
    cuvinte = _TITLU_CUVANT.findall(t)
    if len(cuvinte) < 3:
        return True
    return all(c.lower() in _TITLU_GENERIC for c in cuvinte)

def _slug_stems(url: str) -> set:
    """Cuvinte-cheie (stem 6 litere) din ultima bucata a URL-ului = subiectul articolului-sursa."""
    slug = re.sub(r"[?#].*$", "", url or "").rstrip("/").split("/")[-1]
    return {t[:6] for t in title_tokens(slug.replace("-", " ").replace("_", " "))}

def sources_coherent(a: dict) -> bool:
    """False daca o sursa a unui cluster C nu imparte NICIUN cuvant cu restul (mis-clustering).

    O sursa al carei slug nu contine macar doua cuvinte nu poate dovedi NICI coerenta, nici
    incoerenta: e un identificator opac, nu un subiect. Masurat pe arhiva (7443 articole,
    2026-08-05): din 3511 surse de sinteza, 47 (1.3%) dau un singur token si TOATE sunt id-uri
    — bbc.co.uk `c8j2vmzxezro` (30), dw.com `a-77798543` (16), un hotnews numeric. Niciun slug
    cu cuvinte reale nu cade acolo; urmatoarea treapta, 2 tokeni, are 44 de surse normale.
    Cat timp erau judecate, orice sinteza care citeaza BBC sau DW pica garda si NU se publica:
    10 din cele 67 de sinteze respinse pe arhiva erau stiri corroborate real (BBC + Guardian +
    Politico pe atacul asupra Kievului). Ramura `if not t` de dedesubt afirma deja principiul
    — fara dovada nu condamn — dar 0 din 3511 slug-uri sunt complet goale, deci nu se activa
    niciodata. Verificat ca varianta e strict mai permisiva: nicio sinteza acceptata inainte
    nu e respinsa acum.
    """
    srcs = a.get("sources") or []
    if len(srcs) < 2:
        return True
    toks = [_slug_stems(s.get("url", "")) for s in srcs]
    for i, t in enumerate(toks):
        if len(t) < 2:
            continue
        others = set().union(*[toks[j] for j in range(len(toks)) if j != i]) if len(toks) > 1 else set()
        if others and not (t & others):
            return False
    return True

def _quality_gate(a: dict) -> bool:
    """Contract de date: un articol trece gate-ul daca satisface toate conditiile.

    Returneaza True = publicabil. False = exclus din feed (zero output degradat).
    """
    title = (a.get("title") or "").strip()
    if not title:
        return False

    if a.get("model") == "C":
        body = (a.get("synthesis") or "").strip()
    else:
        body = (a.get("teaser") or "").strip()

    # Anuntul oficial fara corp e SINGURA forma publicabila fara body: titlu original + link.
    # Exceptia e strict pe `processed_by == "official"`, adica pe itemele care nu trec prin AI
    # deloc — nu exista text sintetizat care sa poata fi fabricat. Pentru orice alta sursa
    # conditiile de mai jos raman intacte: slabirea lor ar readuce exact bug-ul reparat de #130.
    if not anunt_oficial_fara_corp(a):
        if not body or body in _BODY_PLACEHOLDERS:
            return False
        if body == title:
            return False
    elif titlu_fara_informatie(title):
        # Fara corp SI fara informatie in titlu: n-a mai ramas nimic de comunicat, iar cardul ar
        # spune doar „Anunț oficial". Aici se opreste exceptia de mai sus — publicam titlul
        # original, dar numai cand titlul chiar e o informatie.
        return False

    # sursa minima
    has_source = bool(a.get("sources")) or bool(a.get("original_link"))
    if not has_source:
        return False

    # fallback = titlu/body brut din RSS, fara sinteza AI -> zgomot, NU se publica
    # (indiferent de limba). Item-ul ramane in state si se reia/upgrade-eaza la AI.
    if a.get("processed_by") == "fallback":
        return False

    # Sursa n-a trimis fapte peste titlu -> ce s-a sintetizat e o parafraza a titlului, oricat de
    # fluent ar suna. Verificarile de mai sus se uita toate la FORMA IESIRII si nu pot vedea asta:
    # teaserul E diferit de titlu, E nevid, NU e trunchiat. Asta e singura care se uita la INTRARE.
    # `main.py` opreste itemele astea inainte de AI; garda de aici prinde ce e deja in state.
    # Oficialele (pl_/cj_/pr_) nu trec pe aici cu sinteza AI si au propria cale.
    if (a.get("processed_by") != "official"
            and a.get("src_extra") is not None
            and a["src_extra"] < config.MIN_SUBSTANTA_CUVINTE):
        return False

    # cluster C cu surse incoerente (linkuri spre articole fara legatura) -> nu se publica
    if a.get("model") == "C" and not sources_coherent(a):
        return False

    # titlu brut trunchiat ("...") = output degradat
    if title.endswith("...") or title.endswith("…"):
        return False

    return True
