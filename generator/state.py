"""Starea fara server: data/articles.json. Dedup pe URL normalizat + expirare la TTL."""
import json
import os
from datetime import datetime, timezone, timedelta

from . import config

STATE_PATH = os.path.join(config.ROOT, "data", "articles.json")


def load() -> list:
    if not os.path.exists(STATE_PATH):
        return []
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
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
    articles_sorted = sorted(articles, key=lambda a: a.get("published") or "", reverse=True)
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(articles_sorted, fh, ensure_ascii=False, indent=2)
