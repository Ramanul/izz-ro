"""Logica editoriala PURA: ce se publica, in ce ordine, ce se arunca.

Extras din `render.py` (1001 linii, 52 de revizii, 4 responsabilitati amestecate). Linia de
taiere e „pur vs. cu efecte": aici intra dict/lista si iese bool/lista — fara disk, fara
retea, fara Jinja, fara config. Restul randarii ramane in `render.py`.

De ce contine exact functiile astea: ele decid CE APARE PE SITE (regula „Zero Zgomot",
CLAUDE.md §7), deci sunt cele care merita testate izolat. Acoperirea lor e in
`tests/test_render_editorial.py`, scrisa INAINTE de mutare tocmai ca sa dovedeasca faptul
ca mutarea n-a schimbat comportament.

NU s-a mutat `_assign_slugs`, desi atribuie sloguri: cheama `_human_date`, deci amesteca
identitatea articolului cu formatarea pentru afisare. Ar trage randarea dupa el aici.
"""
import re

from slugify import slugify

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

def _slug_stems(url: str) -> set:
    """Cuvinte-cheie (stem 6 litere) din ultima bucata a URL-ului = subiectul articolului-sursa."""
    slug = re.sub(r"[?#].*$", "", url or "").rstrip("/").split("/")[-1]
    return {t[:6] for t in title_tokens(slug.replace("-", " ").replace("_", " "))}

def sources_coherent(a: dict) -> bool:
    """False daca o sursa a unui cluster C nu imparte NICIUN cuvant cu restul (mis-clustering)."""
    srcs = a.get("sources") or []
    if len(srcs) < 2:
        return True
    toks = [_slug_stems(s.get("url", "")) for s in srcs]
    for i, t in enumerate(toks):
        if not t:
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

    if not body or body in _BODY_PLACEHOLDERS:
        return False
    if body == title:
        return False

    # sursa minima
    has_source = bool(a.get("sources")) or bool(a.get("original_link"))
    if not has_source:
        return False

    # fallback = titlu/body brut din RSS, fara sinteza AI -> zgomot, NU se publica
    # (indiferent de limba). Item-ul ramane in state si se reia/upgrade-eaza la AI.
    if a.get("processed_by") == "fallback":
        return False

    # cluster C cu surse incoerente (linkuri spre articole fara legatura) -> nu se publica
    if a.get("model") == "C" and not sources_coherent(a):
        return False

    # titlu brut trunchiat ("...") = output degradat
    if title.endswith("...") or title.endswith("…"):
        return False

    return True
