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


def save(articles: list) -> None:
    articles_sorted = sorted(articles, key=lambda a: a.get("published") or "", reverse=True)
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(articles_sorted, fh, ensure_ascii=False, indent=2)
