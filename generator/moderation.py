"""Om in bucla: aplica moderation.yaml peste lista de articole.

Fisierul lipsa = configurare goala (nicio filtrare). Toleranta deliberat.
"""
import os
from datetime import datetime, timezone, timedelta

import yaml

from . import config, guard, cluster
from .util import normalize_url, title_tokens

MOD_PATH = os.path.join(config.ROOT, "moderation.yaml")

DEFAULTS = {
    "blocklist_urls": [],
    "blocklist_keywords": [],
    "suppress_sources": [],
    "corrections": {},
    "featured": [],
    "hold_important": False,
    "approved": [],
}


def load() -> dict:
    mod = dict(DEFAULTS)
    if os.path.exists(MOD_PATH):
        try:
            with open(MOD_PATH, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for key in DEFAULTS:
                if key in data and data[key] is not None:
                    mod[key] = data[key]
        except (yaml.YAMLError, OSError):
            pass
    return mod


def _article_url(a: dict) -> str:
    return a.get("url") or a.get("original_link") or ""


def _article_time(a: dict) -> datetime:
    try:
        value = a.get("published") or ""
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def _event_stems(a: dict) -> set:
    """Semnatura textuala pentru dedup-ul evenimentelor deja procesate."""
    text = a.get("original_title") or a.get("title") or ""
    return {t[:6] for t in title_tokens(text)}


def _entity_stems(a: dict) -> set:
    return {t[:6] for e in (a.get("entities") or []) for t in title_tokens(e)}


def _same_event(a: dict, b: dict) -> bool:
    """Dedup conservator intre doua pagini care descriu acelasi eveniment.

    URL identic = duplicat sigur. Pentru URL-uri diferite cerem aceeasi fereastra de timp,
    cel putin 3 tokeni semnificativi + pragul strict din cluster.py si, daca ambele articole
    au entitati, cel putin o entitate comuna. Nu unim doua articole doar fiindca au acelasi
    loc sau aceleasi cuvinte generice.
    """
    ua = normalize_url(_article_url(a))
    ub = normalize_url(_article_url(b))
    if ua and ub and ua == ub:
        return True

    ta, tb = _event_stems(a), _event_stems(b)
    if not ta or not tb:
        return False
    if abs(_article_time(a) - _article_time(b)) > timedelta(hours=48):
        return False

    inter = len(ta & tb)
    union = len(ta | tb)
    if not cluster._strict_match(inter, union):
        return False

    ea, eb = _entity_stems(a), _entity_stems(b)
    if ea and eb and not (ea & eb):
        return False
    return True


def _dedup_visible(articles: list) -> list:
    """Elimina duplicatele la ultimul punct inainte de publicare.

    Ingestia elimina URL-uri identice, iar clustering-ul rezolva multe cazuri inainte de AI.
    Garda aceasta este necesara pentru duplicatele cu URL diferit si pentru duplicatele deja
    existente in state. Se aplica si la `render_only()`, deci curata si stocul vechi fara fetch.

    Ordinea de pastrare este deliberata: sinteza C castiga fata de B, iar dintre doua sinteze
    castiga cea cu mai multe surse. Pentru egalitate, articolul mai nou castiga. Asta face
    rezultatul determinist si pastreaza varianta editorial mai bogata.
    """
    ordered = sorted(
        articles,
        key=lambda a: (
            a.get("model") == "C",
            len(a.get("sources") or []),
            a.get("published") or "",
        ),
        reverse=True,
    )
    kept = []
    # `_same_event` is intentionally conservative, but calling it against every previous
    # article makes moderation O(n^2). In the Windows dry-run this became visible after
    # 892 articles reached moderation. Every non-URL duplicate must share at least one
    # six-character title stem, so use that as a lossless candidate index and keep the
    # exact predicate below as the authority.
    seen_urls = set()
    by_stem: dict[str, list[dict]] = {}
    for article in ordered:
        norm_url = normalize_url(_article_url(article))
        if norm_url and norm_url in seen_urls:
            continue
        candidates: list[dict] = []
        candidate_ids = set()
        for stem in _event_stems(article):
            for old in by_stem.get(stem, ()):
                marker = id(old)
                if marker not in candidate_ids:
                    candidate_ids.add(marker)
                    candidates.append(old)
        if any(_same_event(article, old) for old in candidates):
            continue
        kept.append(article)
        if norm_url:
            seen_urls.add(norm_url)
        for stem in _event_stems(article):
            by_stem.setdefault(stem, []).append(article)
    kept.sort(key=lambda a: a.get("published") or "", reverse=True)
    return kept


def apply(articles: list, mod: dict) -> list:
    block_urls = {normalize_url(u) for u in mod["blocklist_urls"]}
    keywords = [k.lower() for k in mod["blocklist_keywords"]]
    suppress = set(mod["suppress_sources"])
    corrections = {normalize_url(u): c for u, c in mod["corrections"].items()}
    featured = {normalize_url(u) for u in mod["featured"]}
    # Poarta de aprobare (AI Act art. 50). Pana la 2026-08-15 `hold_important` era un steag
    # mincinos: `main.py` tiparea "asteapta aprobare" si publica exact ca inainte. Acum retine
    # efectiv sintezele C — singurul loc unde se poate face asta o data pentru toate caile,
    # fiindca `apply()` ruleaza si pe build complet si pe `--render-only`.
    hold = bool(mod.get("hold_important"))
    approved = {normalize_url(u) for u in (mod.get("approved") or [])}

    out = []
    held = []
    for a in articles:
        url = a.get("url", "")
        if normalize_url(url) in block_urls or a.get("source") in suppress:
            continue
        motiv = (guard.verdict(a.get("title") or "",
                               a.get("teaser") or a.get("synthesis") or a.get("description") or "")
                 or guard.url_ostil(a.get("original_link") or "")
                 or next((m for s in (a.get("sources") or [])
                          if (m := guard.url_ostil(s.get("url") or ""))), None)
                 or guard.anomalie(a.get("original_title") or a.get("title") or "",
                                   a.get("source_lang") or "ro"))
        if motiv:
            print(f"   !! garda moderare: ascund {(a.get('title') or '')[:60]!r} — {motiv}")
            continue
        title_l = (a.get("title", "") + " " + a.get("original_title", "")).lower()
        if any(kw in title_l for kw in keywords):
            continue
        norm_url = normalize_url(url)
        if norm_url in corrections:
            for field in ("title", "teaser", "synthesis"):
                if field in corrections[norm_url]:
                    a[field] = corrections[norm_url][field]
        a["featured"] = norm_url in featured
        # Retinerea vine ULTIMA: un articol blocat, spam sau prins de garda nu e "in asteptare
        # de aprobare", e respins. Altfel coada de revizuire s-ar umple cu gunoi.
        if hold and a.get("model") == "C" and norm_url not in approved:
            held.append(a)
            continue
        out.append(a)

    if held:
        print(f"   >> hold_important: {len(held)} sinteze C RETINUTE, nepublicate. "
              "Aproba adaugand URL-ul in lista `approved` din moderation.yaml:")
        for a in held:
            print(f"      - {(a.get('title') or '')[:70]!r} | {_article_url(a)}")

    deduped = _dedup_visible(out)
    removed = len(out) - len(deduped)
    if removed:
        print(f"   >> dedup editorial: eliminate {removed} duplicate de eveniment inainte de publicare: {removed}")
    return deduped
