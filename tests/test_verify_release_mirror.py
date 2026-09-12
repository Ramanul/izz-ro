"""Garda prospetimii MIRROR-ului in sonda de release (`IZZ-0370`).

DE CE EXISTA. Pana pe 2026-09-12, prospetimea mirror-ului nu era verificata de nimeni:
`monitor.yml` il probeaza la fiecare 10 minute dar compara doar codul HTTP, iar
`tools/verify_release.py` — singura sonda care CHIAR compara continutul servit cu release-ul
asteptat — ii sarea peste el. Adica exact originea pe care comutam cand primarul cade era
singura despre care nu stiam daca serveste continut vechi.

Testele de aici apara doua proprietati care se pot strica independent: ca sonda distinge
proaspat de vechi, si ca NU blocheaza publicarea cand mirror-ul e in urma.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import verify_release as vr  # noqa: E402


def _manifest(minute_in_urma: float, cheie: str = "generated_at") -> dict:
    momentul = datetime.now(timezone.utc) - timedelta(minutes=minute_in_urma)
    return {cheie: momentul.isoformat(), "commit": "a" * 40, "branch": "main",
            "article_count": 42}


@pytest.fixture
def manifest(monkeypatch):
    """Inlocuieste ADUCEREA, nu calculul: testul masoara logica, nu reteaua."""
    def _set(valoare):
        def fals(_url):
            if isinstance(valoare, Exception):
                raise valoare
            return valoare
        monkeypatch.setattr(vr, "_get_json", fals)
    return _set


def test_mirror_proaspat_trece(manifest):
    manifest(_manifest(10))
    ok, detaliu = vr.verifica_mirror("https://exemplu.test", max_age_min=360)
    assert ok and "10 min" in detaliu


def test_mirror_vechi_pica(manifest):
    manifest(_manifest(400))
    ok, detaliu = vr.verifica_mirror("https://exemplu.test", max_age_min=360)
    assert not ok and "400 min" in detaliu


def test_pragul_e_inclusiv_la_limita(manifest):
    """Un gol exact cat pragul nu e o regresie: cadenta masurata are maxim 369 min."""
    manifest(_manifest(360))
    assert vr.verifica_mirror("https://exemplu.test", max_age_min=361)[0]


def test_mirror_inaccesibil_NU_trece_tacut(manifest):
    """„Sonda verde-pe-nimic" e chiar esecul din 2026-08-21: necunoscutul se raporteaza."""
    from urllib.error import URLError
    manifest(URLError("Tunnel connection failed: 403 Forbidden"))
    ok, detaliu = vr.verifica_mirror("https://exemplu.test")
    assert not ok and "indisponibil" in detaliu


def test_manifest_fara_generated_at_nu_trece(manifest):
    manifest({"commit": "b" * 40, "branch": "main"})
    ok, detaliu = vr.verifica_mirror("https://exemplu.test")
    assert not ok and "generated_at" in detaliu


def test_timestamp_neinterpretabil_nu_trece(manifest):
    manifest({"generated_at": "acum doua zile"})
    ok, detaliu = vr.verifica_mirror("https://exemplu.test")
    assert not ok and "neinterpretabil" in detaliu


def test_timestamp_fara_fus_e_citit_ca_UTC(manifest):
    """Aceeasi clasa de bug ca IZZ-0356: un timestamp naiv nu se compara cu unul cu fus."""
    fara_fus = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(tzinfo=None)
    manifest({"generated_at": fara_fus.isoformat()})
    ok, detaliu = vr.verifica_mirror("https://exemplu.test", max_age_min=60)
    assert ok, detaliu


def test_mirror_neconfigurat_e_sarit_nu_raportat_ca_defect(manifest, monkeypatch):
    monkeypatch.setattr(vr, "MIRROR_URL", "")
    assert vr.verifica_mirror("")[0]


def test_mirror_in_urma_NU_blocheaza_publicarea(monkeypatch, capsys):
    """Proprietatea care conteaza cel mai mult: plasa degradata nu opreste stirile.

    Cand sonda ruleaza, primarul a servit deja release-ul cerut. Un mirror vechi degradeaza
    redundanta, nu publicarea; a face pipeline-ul rosu pentru asta ar opri site-ul din cauza
    plasei de siguranta.
    """
    monkeypatch.setattr(vr, "EXPECTED", "c" * 40)
    monkeypatch.setattr(vr, "BASE_URLS", ("https://primar.test",))
    monkeypatch.setattr(vr, "_probe", lambda _b: (True, "ok"))
    monkeypatch.setattr(vr, "verifica_mirror", lambda: (False, "generat acum 999 min"))
    assert vr.main() == 0
    iesire = capsys.readouterr().out
    assert "ATENTIE" in iesire
    assert "::warning::" in iesire
    assert "publicarea NU e afectată" in iesire


def test_mirror_proaspat_nu_produce_avertisment(monkeypatch, capsys):
    monkeypatch.setattr(vr, "EXPECTED", "c" * 40)
    monkeypatch.setattr(vr, "BASE_URLS", ("https://primar.test",))
    monkeypatch.setattr(vr, "_probe", lambda _b: (True, "ok"))
    monkeypatch.setattr(vr, "verifica_mirror", lambda: (True, "generat acum 3 min"))
    assert vr.main() == 0
    assert "::warning::" not in capsys.readouterr().out


def test_originile_primare_raman_blocante(monkeypatch, capsys):
    """Garda pe garda: mirror-ul e neblocant, primarul NU trebuie sa devina la fel."""
    monkeypatch.setattr(vr, "EXPECTED", "c" * 40)
    monkeypatch.setattr(vr, "BASE_URLS", ("https://primar.test",))
    monkeypatch.setattr(vr, "TIMEOUT_SECONDS", 0)
    monkeypatch.setattr(vr, "_probe", lambda _b: (False, "serveste altceva"))
    assert vr.main() == 1


# --- constatarile Codex pe PR #334 -----------------------------------------------------


def test_manifest_care_nu_e_obiect_NU_crapa(manifest):
    """P2 Codex: JSON valid dar care nu e obiect dadea AttributeError pe `.get`.

    Adica traceback si cod de iesire nenul TOCMAI in bucata proiectata sa fie neblocanta —
    plasa de siguranta s-ar fi transformat in blocaj. Cazul real: `[]` dupa o publicare
    stricata a oglinzii.
    """
    for valoare in ([], "text", 42, None):
        manifest(valoare)
        ok, detaliu = vr.verifica_mirror("https://exemplu.test")
        assert not ok and "nu e obiect JSON" in detaliu, valoare


def test_manifest_nedict_nu_blocheaza_publicarea(monkeypatch, capsys):
    """Acelasi caz, pe calea completa: trebuie sa ramana avertisment, nu esec."""
    monkeypatch.setattr(vr, "EXPECTED", "c" * 40)
    monkeypatch.setattr(vr, "BASE_URLS", ("https://primar.test",))
    monkeypatch.setattr(vr, "_probe", lambda _b: (True, "ok"))
    monkeypatch.setattr(vr, "_get_json", lambda _u: [])
    assert vr.main() == 0
    assert "::warning::" in capsys.readouterr().out


def test_si_originile_primare_supravietuiesc_unui_manifest_nedict(manifest):
    """Aceeasi clasa de defect exista si pe calea blocanta: un traceback e mai rau decat
    un mesaj clar, fiindca ascunde ce anume serveste originea."""
    monkey = vr._probe
    assert callable(monkey)
    manifest([])
    ok, detaliu = vr._probe("https://primar.test")
    assert not ok and "nu e obiect JSON" in detaliu
