"""Om in bucla: aplica moderation.yaml peste lista de articole.

Fisierul lipsa = configurare goala (nicio filtrare). Toleranta deliberat.
"""
import os
from datetime import datetime, timezone, timedelta

import yaml

from . import config, guard, cluster
from .util import normalize_url, title_tokens, domain_of

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
    cel putin 3 tokeni semnificativi + Jaccard strict si, daca ambele articole au entitati,
    cel putin o entitate comuna. Nu unim doua articole doar fiindca au acelasi loc sau aceleasi
    cuvinte generice. Regula este aceeasi familie de praguri calibrata in cluster.py.
    """
    ua, ub = normalize_url(_article_url(a)), normalize_url(_article_url(b))
    if ua and ub and ua == ub:
        return True
    da, db = domain_of(ua), domain_of(ub)
    if da == db and da:
        # Doua URL-uri distincte de pe acelasi domeniu pot fi articole diferite/actualizari.
        # Le deduplicam numai pe dovada textuala, nu pe domeniu.
        pass
    ta, tb = _event_stems(a), _event_stems(b)
    if not ta or not tb:
        return False
    dt = abs(_article_time(a) - _article_time(b))
    if dt > timedelta(hours=48):
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
    """Elimina duplicatele la ULTIMUL punct inainte de publicare.

    Este intentionat aici: dedup-ul din ingestie prinde duplicatele cu acelasi URL, iar
    clustering-ul prinde multe duplicate noi. Dar un duplicat cu URL diferit poate exista
    deja in state sau poate aparea dupa procesarea simultana a doua feeduri. Acest punct este
    singurul comun si pentru `run()` si pentru `render_only()`, deci nu mai exista o cale prin
    care doua pagini despre acelasi eveniment sa ajunga simultan pe site.
    """
    ordered = sorted(articles, key=lambda a: (
        0 if a.get("model") == "C" else 1,
        -len(a.get("sources") or []),
        -(a.get("published") or "" == "") if False else 0,
    ))
    # Sortare explicita separata pentru a evita comparatii datetime/string amestecate.
    ordered.sort(key=lambda a: (a.get("model") == "C", len(a.get("sources") or []),
                                a.get("published") or ""), reverse=True)
    kept = []
    for article in ordered:
        if any(_same_event(article, old) for old in kept):
            continue
        kept.append(article)
    # Restabilim ordinea editoriala existenta (published desc), fara sa schimbam ce a fost pastrat.
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
        if url in block_urls or a.get("source") in suppress:
            continue
        # Garda de continut, a doua oara. Nu e redundanta cu cea din `fetch.py`: aici trec si
        # articolele DEJA din `articles.json`, ingerate inainte ca garda sa existe sau printr-o
        # versiune mai slaba a ei. `render_only()` chema `apply()` la FIECARE build, deci asta
        # e singurul punct prin care curatarea ajunge pe site fara sa astepte un fetch nou.
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
        if normalize_url(url) in corrections:
            for field in ("title", "teaser", "synthesis"):
                if field in corrections[normalize_url(url)]:
                    a[field] = corrections[normalize_url(url)][field]
        a["featured"] = normalize_url(url) in featured
        out.append(a)

    deduped = _dedup_visible(out)
    removed = len(out) - len(deduped)
    if removed:
        print(f"   >> dedup editorial: eliminate {removed} duplicat(e) de eveniment inainte de publicare")
    return deduped
