"""Prospețime pe homepage: secțiunile nu arată știri mai vechi de HOME_MAX_AGE.

Arhiva completă rămâne pe paginile de categorie. Fail-open dacă data lipsește
sau nu e parseable — mai bine un item vechi pe home decât să pierzi totul.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# 72h: regional stale (zile) pe home arăta abandon; național/județean de azi trec.
HOME_MAX_AGE = timedelta(hours=72)


def home_fresh(a: dict, *, now: datetime | None = None, max_age: timedelta = HOME_MAX_AGE) -> bool:
    raw = (a.get("published") or "").strip()
    if not raw:
        return True
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ref = now or datetime.now(timezone.utc)
    return (ref - dt) <= max_age
