"""Regresii pentru auditul extern de încredere din 7 noiembrie 2026.

Datele istorice sunt păstrate ca Doveadă în raport, nu rescrise în stare. Aici folosim
forme sintetice echivalente pentru a verifica mecanismul, fără să inventăm o corecție
editorială sau să pretindem că am verificat live sursele TVR/Opta.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from generator import editorial, process, publication, raport_copiere, render
from generator.home_fresh import home_fresh
from generator.verifica_sinteza import rezultat_penalty_inversat, verifica
from tools.public_probe import Observation, classify_response, content_freshness


class Provider:
    name = "test"

    def __init__(self, payload):
        self.payload = payload

    def complete(self, system, user):
        return json.dumps(self.payload)


def _item():
    return {"original_title": "TITLU BRUT CARE NU TREBUIE PUBLICAT",
            "description": "Descriere originală.", "title": "TITLU BRUT CARE NU TREBUIE PUBLICAT",
            "teaser": "", "url": "https://sursa.example/articol",
            "original_link": "https://sursa.example/articol", "source_lang": "ro"}


@pytest.mark.parametrize("payload", [
    {}, {"title": "Titlu valid"}, {"teaser": "Rezumat valid"},
    {"title": "", "teaser": "Rezumat"}, {"title": "Titlu", "teaser": "   "},
    {"title": 7, "teaser": "Rezumat"}, {"title": "Titlu", "teaser": ["nu e șir"]},
])
def test_model_b_incomplet_nu_publica_brut_sau_placeholder(payload):
    item = _item()
    before = deepcopy(item)
    assert process.process_single(item, Provider(payload)) is None
    assert item == before


def test_model_b_valid_ramane_functional():
    out = process.process_single(_item(), Provider({"title": "Titlu reformulat", "teaser": "Rezumat factual."}))
    assert out["title"] == "Titlu reformulat"
    assert out["teaser"] == "Rezumat factual."


@pytest.mark.parametrize("source,output", [
    ("Mbappe a ratat penalty-ul în meciul Franța Maroc.", "Kylian Mbappe a transformat lovitura."),
    ("Mbappe a transformat penalty-ul.", "Mbappe a ratat lovitura de la 11 metri."),
    ("Mbappe nu a ratat penalty-ul.", "Mbappe a ratat penalty-ul."),
])
def test_penalty_inversat_explicit(source, output):
    assert rezultat_penalty_inversat(output, source) is True
    assert any(p.cod == "rezultat_penalty_inversat" for p in verifica("", output, source))


@pytest.mark.parametrize("source,output", [
    ("Mbappe a ratat penalty-ul în minutul 28 și a transformat penalty-ul în minutul 70.", "Mbappe a transformat penalty-ul în minutul 70."),
    ("Mbappe a ratat penalty-ul în minutul 28.", "Mbappe a transformat penalty-ul în minutul 70."),
    ("Mbappe a ratat penalty-ul.", "Portarul a apărat penalty-ul."),
    ("Mbappe a ratat penalty-ul.", "Mbappe a transformat lovitura liberă."),
    ("Mbappe a ratat un penalty.", "Mbappe a transformat un alt penalty."),
    ("Jucătorul a ratat penalty-ul.", "Mbappe a transformat penalty-ul."),
    ("Mbappe a participat la meci.", "Mbappe a transformat penalty-ul."),
])
def test_penalty_ambiguu_sau_diferit_nu_blocat_heuristic(source, output):
    assert rezultat_penalty_inversat(output, source) is False


def test_penalty_inversat_ajunge_in_gate_blocant(tmp_path, monkeypatch):
    report = tmp_path / "gate.jsonl"
    monkeypatch.setattr(raport_copiere, "CALE", tmp_path / "observational.jsonl")
    monkeypatch.setenv("IZZ_RAPORT_COPIERE_GATE", str(report))
    item = _item()
    item.update(original_title="Mbappe a ratat penalty-ul",
                description="Mbappe a ratat penalty-ul în meciul Franța Maroc.")
    out = process.process_single(item, Provider({"title": "Mbappe și penalty-ul", "teaser": "Mbappe a transformat penalty-ul."}))
    assert out is not None  # defer-ul decide publicarea, nu process_single
    row = json.loads(report.read_text(encoding="utf-8").splitlines()[0])
    assert any(issue["cod"] == "rezultat_penalty_inversat" for issue in row["blocking_issues"])
    assert raport_copiere.url_uri_blocate(str(report)) == {item["original_link"]}


def test_home_fresh_refuza_data_necunoscuta_si_viitoare():
    now = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    assert home_fresh({"published": (now + timedelta(hours=1)).isoformat()}, now=now) is False
    assert home_fresh({"published": 123}, now=now) is False
    assert home_fresh({"published": (now - timedelta(hours=71)).isoformat()}, now=now) is True


def _correction(article, state="corrected", notice="Eroare corectată conform documentului."):
    row = {"key": editorial.annotation_key(article), "public_paths": [editorial.public_path(article)],
           "state": state, "notice": notice, "evidence_url": "https://sursa.example/rectificare/",
           "review": {"state": "approved", "kind": "documentary", "reviewer": "test-only",
                      "reviewed_at": "2026-11-07T10:00:00Z",
                      "input_fingerprint": editorial.source_fingerprint(article)},
           "presentation": {"title": "Titlu corect"} if state == "corrected" else {}}
    return {row["key"]: row}


def _article():
    return {"model": "B", "category": "local", "slug": "test-corectie",
            "title": "Titlu inițial", "teaser": "Rezumat inițial sufficiently long for the publication gate.",
            "original_link": "https://sursa.example/anunt/", "url": "https://sursa.example/anunt/",
            "source_name": "Sursa", "source": "pl_timis_timisoara", "processed_by": "official",
            "published": datetime.now(timezone.utc).isoformat()}


def test_jurnal_corectii_gol_si_aprobat(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    env = render._env()
    render._render_legal(env, {})
    page = (tmp_path / "legal/corrections/index.html").read_text(encoding="utf-8")
    assert "Nu există intrări publicate" in page
    assert "IZZ_CORRECTIONS_JOURNAL" not in page
    article = _article()
    rows = _correction(article, notice="Eroare corectată conform documentului.")
    publication.validate(rows, [article])
    # Template-ul primește doar catalog validat; autoescape rămâne o a doua barieră.
    fragment = render._corrections_journal_html(env, rows)
    assert "Titlu corect" in fragment and "/local/test-corectie/" in fragment
    rows[next(iter(rows))]["notice"] = "<script>alert(1)</script>"
    escaped = render._corrections_journal_html(env, rows)
    assert "&lt;script&gt;" in escaped and "<script>alert(1)" not in escaped
    render._render_legal(env, _correction(article))
    page = (tmp_path / "legal/corrections/index.html").read_text(encoding="utf-8")
    assert "Titlu corect" in page and "/local/test-corectie/" in page
    rows = _correction(article, state="withdrawn")
    render._render_legal(env, rows)
    page = (tmp_path / "legal/corrections/index.html").read_text(encoding="utf-8")
    assert "Retragere" in page and "Material retras" in page


def test_home_renderarată_stare_explicită_când_conținutul_e_înghețat(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(publication, "load", lambda: {})
    monkeypatch.setattr(editorial, "load_annotations", lambda: {})
    monkeypatch.setattr(render.config, "ARTICLE_IMAGE_FILES", False)
    monkeypatch.setenv("PAGEFIND_ENABLED", "0")
    old = _article()
    old["published"] = "2026-07-10T12:00:00+00:00"
    render.build([old])
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Nu există știri proaspete în fereastra de 72 de ore" in index
    assert "Ultima publicare rămasă în arhivă" in index
    assert 'class="lead-feature"' not in index
    manifest = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert manifest["latest_article"] == old["published"]


@pytest.mark.parametrize("status,headers,body,expected", [
    (200, {}, b"<html>IZZ.ro</html>", "ok"),
    (200, {}, b"<html>Just a moment</html>", "unknown"),
    (200, {"cf-mitigated": "challenge"}, b"<html>IZZ.ro</html>", "unknown"),
    (403, {"cf-mitigated": "challenge"}, b"blocked", "unknown"),
    (403, {}, b"Forbidden", "unknown"),
    (500, {}, b"oops", "error"),
    (503, {}, b"unavailable", "error"),
    (200, {}, b"alt site", "error"),
])
def test_sonda_publica_nu_minte(status, headers, body, expected):
    assert classify_response(status, headers, body, expect="IZZ.ro").state == expected


def test_prospetime_manifest_separata_de_build():
    now = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    fresh = {"generated_at": now.isoformat(), "latest_article": (now - timedelta(hours=2)).isoformat()}
    stale = {"generated_at": now.isoformat(), "latest_article": "2026-07-10T12:00:00+00:00"}
    assert content_freshness(fresh, now=now).state == "ok"
    assert content_freshness(stale, now=now).state == "error"
    assert content_freshness({"generated_at": now.isoformat()}, now=now).state == "error"
    assert Observation("unknown", "").exit_code == 2
