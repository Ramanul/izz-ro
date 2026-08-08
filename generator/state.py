"""Starea fara server: data/articles.json. Dedup pe URL normalizat + expirare la TTL."""
import json
import os
from datetime import datetime, timezone, timedelta

from . import config, geo

STATE_PATH = os.path.join(config.ROOT, "data", "articles.json")


def _text_articol(art: dict) -> str:
    """Textul pe care il vede clasificarea: titlu + teaser + synthesis.

    Duplicat DELIBERAT fata de `process._text_clasificabil`, ca `state` sa nu importe
    `process` (care isi construieste prompturile la import, doar ca sa incarcam starea).
    `test_state_resync.py` le tine legate: daca una se schimba fara cealalta, pica.
    """
    return " ".join(filter(None, (art.get("title"), art.get("teaser"),
                                  art.get("synthesis"))))


def _resync_pinned(articles: list) -> list:
    """Readuce pe rubrica sursei articolele vechi pe care TEXTUL lor nu le sustine.

    Categoria unui articol deja procesat e inghetata in stare si se recalculeaza doar la
    bump de PROMPT_VERSION. Deci o rearanjare de config -- mutarea ziarelor judetene din
    'local' in 'zonal' -- lasa in urma articole pe rubrica veche, care nu se repara singure
    niciodata: 131 de articole stateau asa la 2026-07-25.
    Sursele scoase din config isi pastreaza categoria; nu avem de unde sti alta.

    **Garda din 2026-08-08, si de ce exista.** Pana atunci functia rescria categoria fara sa
    se uite la articol, deci ANULA la fiecare `load()` clasificarea din text pe care
    `process._resolve_category` o face la ingestie. Cele doua implementau reguli opuse:
    aici „axa geografica e decisa de SURSA", acolo regula proprietarului din 2026-08-02,
    „LOCAL inseamna UNDE se intampla, nu CINE publica". Functia asta e mai VECHE (2026-07-25)
    si a ramas nerevizitata cand regula a aterizat; rula ultima, deci castiga ea.
    Masurat pe corpus (2962 articole, 2026-08-08): **663 din 1247** de articole de la surse cu
    rubrica geografica fixata erau impinse inapoi pe rubrica sursei -- 390 `local`->`zonal`,
    229 `local`->`regional`, 36 `zonal`->`regional`. Efect secundar: articolul aparea un build
    la `/local/<slug>/`, iar la urmatorul se muta definitiv la `/zonal/<slug>/`, fiindca
    permalinkul contine categoria (`render.py:295`) -- verificat live pe un articol eMaramures,
    `/local/` da 404 si `/zonal/` da 200.

    Garda: daca textul articolului sustine EXACT categoria stocata, articolul nu se atinge.
    Nu „orice nivel" -- exact ala: un articol pus pe `local` al carui text numeste doar judetul
    trebuie in continuare readus pe `zonal`, care e chiar scenariul pentru care s-a scris
    functia. Nu se face migrare retroactiva: cele 663 deja rescrise isi pastreaza categoria si
    permalinkul, si expira in 7 zile.
    """
    pinned = getattr(config, "PINNED_CATEGORIES", set())
    for art in articles:
        # `load()` accepta orice lista JSON, iar un `null` sau o valoare de tip lista in
        # stare ar arunca AttributeError/TypeError de aici -- pe langa `except` din load(),
        # care prinde doar erori de fisier si de parsare. Ar opri tot pipeline-ul in loc sa
        # cada pe starea goala. Inainte de resync, load() returna orice forma neatinsa.
        if not isinstance(art, dict):
            continue
        sid, cat = art.get("source"), art.get("category")
        if not isinstance(sid, str) or not isinstance(cat, str):
            continue
        sursa = config.SOURCES.get(sid)
        if not sursa:
            continue
        actuala = sursa.get("category")
        # Doar in interiorul axei geografice: un articol pe care AI-ul l-a pus pe o tema
        # (sport, politic) de la o sursa netematica nu e treaba acestei functii.
        if actuala in pinned and cat in pinned and cat != actuala:
            # Textul bate sursa. `judet_sursa` e acelasi argument ca la ingestie: deschide
            # potrivirea pe satele judetului respectiv, altfel „Dezmir" nu inseamna nimic.
            if geo.clasifica(_text_articol(art), geo.judet_sursa(sid)) == cat:
                continue
            art["category"] = actuala
    return articles


def load() -> list:
    if not os.path.exists(STATE_PATH):
        return []
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return _resync_pinned(data) if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _parse_iso(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def merge(existing: list, new_items: list) -> list:
    """Adauga doar URL-urile nevazute; pastreaza cele existente (cu procesarea lor)."""
    by_url = {a["url"]: a for a in existing if a.get("url")}
    now_iso = datetime.now(timezone.utc).isoformat()
    for item in new_items:
        url = item.get("url")
        if not url or url in by_url:
            continue
        item.setdefault("first_seen", now_iso)
        by_url[url] = item
    return list(by_url.values())


def expire(articles: list) -> list:
    """Elimina ce e mai vechi de ARTICLE_TTL_DAYS (dupa published, fallback first_seen)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.ARTICLE_TTL_DAYS)
    kept = []
    for a in articles:
        ts = _parse_iso(a.get("published") or a.get("first_seen") or "")
        if ts >= cutoff:
            kept.append(a)
    return kept


def _scrub_processed(articles: list) -> None:
    """Dupa procesarea AI, textele brute preluate din surse (titlu original,
    descriere) nu mai sunt necesare si NU trebuie sa ramana intr-un repo public:
    dreptul editorilor de presa (L8/1996 mod. L69/2022) permite doar 'extrase
    foarte scurte'. Se pastreaza DOAR pe itemele fallback/neprocesate, unde sunt
    necesare pentru upgrade-ul la AI."""
    for a in articles:
        if a.get("processed_by") and a.get("processed_by") != "fallback":
            a.pop("original_title", None)
            a.pop("description", None)


def save(articles: list) -> None:
    _scrub_processed(articles)
    # Sortare pe SIR, nu pe datetime: corecta doar cat timp `published` e uniform `+00:00`.
    # Tine (masurat: 1736/1736 la 2026-08-03), fiindca `_parse_w3c_date` si `_parse_ro_date`
    # inchid amandoua cu `astimezone(timezone.utc)`. Apucata de tests/test_published_is_utc.py —
    # daca acela pica, aici si in cele doua locuri din render.py trebuie trecut pe datetime.
    articles_sorted = sorted(articles, key=lambda a: a.get("published") or "", reverse=True)
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(articles_sorted, fh, ensure_ascii=False, indent=2)
