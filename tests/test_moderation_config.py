from __future__ import annotations

import pytest

from generator import moderation


def test_validate_rejects_unknown_key():
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._validate({**moderation.DEFAULTS, "unexpected": True})


def test_validate_rejects_wrong_types():
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._validate({**moderation.DEFAULTS, "hold_important": "true"})
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._validate({**moderation.DEFAULTS, "blocklist_keywords": ["ok", 1]})


def test_validate_accepts_repo_shape():
    value = moderation._validate({
        "blocklist_urls": [],
        "blocklist_keywords": ["torrent"],
        "suppress_sources": ["example"],
        "corrections": {"https://example.test/a": {"title": "Corect"}},
        "featured": [],
        "hold_important": False,
        "approved": [],
    })
    assert value["blocklist_keywords"] == ["torrent"]


def test_human_gate_env_invalid_is_fail_closed(monkeypatch):
    monkeypatch.setenv(moderation.REQUIRE_HUMAN_GATE_ENV, "yes")
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._human_gate_required()


def test_human_gate_env_true_requires_approval_for_model_c(monkeypatch):
    monkeypatch.setenv(moderation.REQUIRE_HUMAN_GATE_ENV, "true")
    article = {
        "url": "https://example.test/c",
        "original_title": "Alfa Beta Gamma",
        "title": "Alfa Beta Gamma",
        "model": "C",
        "published": "2026-09-05T08:00:00+00:00",
        "sources": [{"url": "https://example.test/source"}],
    }
    result = moderation.apply([article.copy()], moderation.DEFAULTS)
    assert result == []


def test_human_gate_env_true_allows_explicit_approval(monkeypatch):
    monkeypatch.setenv(moderation.REQUIRE_HUMAN_GATE_ENV, "true")
    url = "https://example.test/c"
    article = {
        "url": url,
        "original_title": "Alfa Beta Gamma",
        "title": "Alfa Beta Gamma",
        "model": "C",
        "published": "2026-09-05T08:00:00+00:00",
        "sources": [{"url": "https://example.test/source"}],
    }
    result = moderation.apply([article.copy()], {**moderation.DEFAULTS, "approved": [url]})
    assert len(result) == 1
    assert result[0]["url"] == url


# --- Takedown registry (PLAN UNIFICAT #8) ----------------------------------------

def test_takedown_fara_motiv_e_respins():
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._validate({**moderation.DEFAULTS, "takedowns": {"https://example.test/a": "  "}})
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._validate({**moderation.DEFAULTS, "takedowns": ["https://example.test/a"]})


def _articol(url):
    return {"url": url, "title": "Titlu publicat", "model": "B"}


def test_takedown_retrage_articolul_si_scrie_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(moderation.config, "ROOT", str(tmp_path))
    url = "https://example.test/a"
    mod = {**moderation.DEFAULTS, "takedowns": {url: "cerere de retragere a materialului"}}
    rezultat = moderation.apply([_articol(url)], mod)
    assert rezultat == []
    jurnal = (tmp_path / "data" / "takedown_log.jsonl").read_text(encoding="utf-8")
    assert '"url": "https://example.test/a"' in jurnal
    assert '"motiv": "cerere de retragere a materialului"' in jurnal


def test_takedown_idempotent_pe_rulari_repetate(tmp_path, monkeypatch):
    monkeypatch.setattr(moderation.config, "ROOT", str(tmp_path))
    url = "https://example.test/a"
    mod = {**moderation.DEFAULTS, "takedowns": {url: "cerere de retragere a materialului"}}
    moderation.apply([_articol(url)], mod)
    moderation.apply([_articol(url)], mod)
    linii = [l for l in (tmp_path / "data" / "takedown_log.jsonl")
             .read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(linii) == 1


def test_takedown_castiga_in_fata_aprobarii(tmp_path, monkeypatch):
    monkeypatch.setattr(moderation.config, "ROOT", str(tmp_path))
    url = "https://example.test/c"
    mod = {**moderation.DEFAULTS, "approved": [url], "takedowns": {url: "retragere confirmata legal"}}
    assert moderation.apply([_articol(url)], mod) == []
