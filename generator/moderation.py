"""Om in bucla: aplica moderation.yaml peste lista de articole.

Fisierul de control-plane este obligatoriu. Lipsa, YAML invalid sau schema invalida
opreste pipeline-ul inainte de publicare, pentru ca o eroare de configurare critica
nu trebuie confundata cu „configurare goala".
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


class ModerationConfigCorrupt(RuntimeError):
    """Control-plane moderation lipsa/corupta; publicarea nu este permisa."""


def _valid_string_list(value, key: str) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _validate(mod: dict) -> dict:
    if not isinstance(mod, dict):
        raise ModerationConfigCorrupt(
            f"{MOD_PATH} trebuie sa contina un obiect YAML, nu {type(mod).__name__}."
        )
    unknown = set(mod) - set(DEFAULTS)
    if unknown:
        raise ModerationConfigCorrupt(
            f"{MOD_PATH} contine chei necunoscute: {', '.join(sorted(unknown))}."
        )
    for key in ("blocklist_urls", "blocklist_keywords", "suppress_sources", "featured", "approved"):
        value = mod.get(key, DEFAULTS[key])
        if not _valid_string_list(value, key):
            raise ModerationConfigCorrupt(
                f"{MOD_PATH}:{key} trebuie sa fie lista de siruri ne-goale."
            )
    corrections = mod.get("corrections", DEFAULTS["corrections"])
    if not isinstance(corrections, dict):
        raise ModerationConfigCorrupt(f"{MOD_PATH}:corrections trebuie sa fie obiect/map.")
    for url, change in corrections.items():
        if not isinstance(url, str) or not url.strip() or not isinstance(change, dict):
            raise ModerationConfigCorrupt(
                f"{MOD_PATH}: fiecare entry din corrections trebuie sa fie URL -> obiect."
            )
        for field in change:
            if field not in {"title", "teaser", "synthesis"} or not isinstance(change[field], str):
                raise ModerationConfigCorrupt(
                    f"{MOD_PATH}: corrections[{url!r}] are un camp invalid: {field!r}."
                )
    hold = mod.get("hold_important", DEFAULTS["hold_important"])
    if not isinstance(hold, bool):
        raise ModerationConfigCorrupt(f"{MOD_PATH}:hold_important trebuie sa fie boolean.")

    normalized = dict(DEFAULTS)
    normalized.update(mod)
    # Copii separate ca sa nu existe efecte secundare intre teste si rularea curenta.
    for key in ("blocklist_urls", "blocklist_keywords", "suppress_sources", "featured", "approved"):
        normalized[key] = list(normalized[key])
    normalized["corrections"] = dict(normalized["corrections"])
    return normalized


def load() -> dict:
    """Citeste control-plane-ul si esueaza CLOSED la orice problema.

    `moderation.yaml` exista in repo si este parte din contractul de release. Lipsa lui
    nu mai inseamna „nicio filtrare": inseamna stare necunoscuta, deci pipeline-ul se opreste.
    """
    if not os.path.exists(MOD_PATH):
        raise ModerationConfigCorrupt(
            f"Lipseste {MOD_PATH}; refuz publicarea deoarece control-plane-ul de moderare nu poate fi determinat."
        )
    try:
        with open(MOD_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (yaml.YAMLError, OSError) as exc:
        raise ModerationConfigCorrupt(
            f"Nu pot citi {MOD_PATH}: {type(exc).__name__}: {exc}. Publicarea este blocata."
        ) from exc
    return _validate(data or {})


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
    """Elimina duplicatele la ultimul punct inainte de publicare."""
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
    mod = _validate(mod)
    block_urls = {normalize_url(u) for u in mod["blocklist_urls"]}
    keywords = [k.lower() for k in mod["blocklist_keywords"]]
    suppress = set(mod["suppress_sources"])
    corrections = {normalize_url(u): c for u, c in mod["corrections"].items()}
    featured = {normalize_url(u) for u in mod["featured"]}
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
        print(f"   >> dedup editorial: eliminate {removed} duplicate de eveniment inainte de publicare")
    return deduped
