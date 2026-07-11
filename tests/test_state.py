"""Teste pentru merge/expire/scrub din generator/state.py (fara I/O)."""
from datetime import datetime, timedelta, timezone

from generator import config, state


def _iso(**delta):
    return (datetime.now(timezone.utc) - timedelta(**delta)).isoformat()


def test_merge_dedups_by_url_and_keeps_existing():
    existing = [{"url": "u1", "title": "procesat deja", "processed_by": "gemini"}]
    new = [{"url": "u1", "title": "duplicat"}, {"url": "u2", "title": "nou"}]
    out = state.merge(existing, new)
    by = {a["url"]: a for a in out}
    assert len(out) == 2
    assert by["u1"]["title"] == "procesat deja"      # nu suprascrie procesarea
    assert by["u2"]["first_seen"]                     # first_seen setat pe cele noi


def test_expire_drops_old_keeps_fresh():
    arts = [{"url": "old", "published": _iso(days=config.ARTICLE_TTL_DAYS + 2)},
            {"url": "new", "published": _iso(hours=1)},
            {"url": "fallback-first-seen", "first_seen": _iso(hours=2)}]
    kept = {a["url"] for a in state.expire(arts)}
    assert kept == {"new", "fallback-first-seen"}


def test_scrub_removes_raw_text_only_on_processed():
    arts = [{"url": "p", "processed_by": "gemini", "original_title": "T", "description": "D"},
            {"url": "f", "processed_by": "fallback", "original_title": "T", "description": "D"}]
    state._scrub_processed(arts)
    assert "original_title" not in arts[0] and "description" not in arts[0]
    assert arts[1]["original_title"] == "T"           # fallback pastreaza pt. upgrade AI
