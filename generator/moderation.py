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
    for article in ordered:
        if any(_same_event(article, old) for old in kept):
            continue
        kept.append(article)
    kept.sort(key=lambda a: a.get("published") or "", reverse=True)
    return kept


def apply(articles: list, mod: dict) -> list:
    block_urls = {normalize_url(u) for u in mod["blocklist_urls"]}
    keywords = [k.lower() for k in mod["blocklist_keywords"]]
    suppress = set(mod["suppress_sources"])
    corrections = {normalize_url(u): c for u, c in mod["corrections"].items()}
    featured = {normalize_url(u) for u in mod["featured"]}

    out = []
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
        out.append(a)

    deduped = _dedup_visible(out)
    removed = len(out) - len(deduped)
    if removed:
        print(f"   >> dedup editorial: eliminate {removed} duplicate de eveniment inainte de publicare: {removed}")
    return deduped
