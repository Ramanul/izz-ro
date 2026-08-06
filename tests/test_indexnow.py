"""IndexNow anunta ce s-a SCHIMBAT, nu ce e recent.

Defectul reparat, gasit la gap-check pe 2026-08-06: filtrul era `published >= now-3h`, deci o
sinteza care absoarbe o stire noua la acelasi permalink (IZZ-0151) nu era anuntata daca
evenimentul era mai vechi de trei ore — iar un bump de `PROMPT_VERSION`, care rescrie ~1100 de
articole fara sa le atinga `published`, nu anunta niciunul.

Testele nu ating reteaua: verifica `plan()`, adica manifestul si coada. `send()` e o singura
cerere HTTP peste coada si e best-effort prin design.
"""
import importlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

# `tools/` nu e pachet si nu are `__init__.py`. Merge fara linia asta doar fiindca CI cheama
# `python -m pytest` (care pune cwd in sys.path) — dar un `pytest tests/` simplu ar pica pe
# ImportError, iar asta ar arata ca un test stricat, nu ca o invocare diferita.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
indexnow = importlib.import_module("tools.indexnow_submit")


@pytest.fixture
def izolat(tmp_path, monkeypatch):
    """Redirecteaza starea, manifestul si coada in tmp — nimic din `data/` real nu e atins."""
    monkeypatch.setattr(indexnow, "STATE", str(tmp_path / "articles.json"))
    monkeypatch.setattr(indexnow, "MANIFEST", str(tmp_path / "indexnow_seen.json"))
    monkeypatch.setattr(indexnow, "QUEUE", str(tmp_path / "queue.json"))
    return tmp_path


def _scrie(cale, obiect):
    with open(cale, "w", encoding="utf-8") as fh:
        json.dump(obiect, fh)


def _art(slug, titlu="Titlu", corp="corp", ore_in_urma=1.0, cat="extern"):
    pub = datetime.now(timezone.utc) - timedelta(hours=ore_in_urma)
    return {"slug": slug, "category": cat, "title": titlu, "teaser": corp,
            "model": "B", "published": pub.isoformat()}


def _coada(izolat) -> list:
    with open(indexnow.QUEUE, encoding="utf-8") as fh:
        return json.load(fh)


def _manifest() -> dict:
    with open(indexnow.MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def test_prima_rulare_insamanteaza_si_nu_trimite_tot_corpusul(izolat):
    """Manifest absent: se marcheaza tot, dar se anunta doar ce e proaspat — altfel prima
    rulare de dupa deploy ar arunca ~2600 de URL-uri la motoare fara nicio informatie noua."""
    _scrie(indexnow.STATE, [_art("proaspat", ore_in_urma=1),
                            _art("vechi", ore_in_urma=50)])
    indexnow.plan()
    assert _coada(izolat) == ["https://izz.ro/extern/proaspat/"]
    assert len(_manifest()) == 2, "manifestul insamanteaza TOT, inclusiv ce nu s-a trimis"


def test_a_doua_rulare_fara_schimbari_nu_trimite_nimic(izolat):
    _scrie(indexnow.STATE, [_art("a", ore_in_urma=1)])
    indexnow.plan()
    indexnow.plan()
    assert _coada(izolat) == []


def test_sinteza_actualizata_la_acelasi_permalink_e_reanuntata(izolat):
    """Cazul care motiveaza tot fixul: acelasi URL, acelasi `published` vechi, corp nou."""
    vechi = _art("eveniment", titlu="Trei raniti", corp="Trei persoane ranite.", ore_in_urma=30)
    _scrie(indexnow.STATE, [vechi])
    indexnow.plan()
    assert _coada(izolat) == [], "seed: articolul e vechi, deci nu se anunta acum"

    actualizat = dict(vechi, title="Cinci raniti", teaser="Bilantul a urcat la cinci.")
    _scrie(indexnow.STATE, [actualizat])
    indexnow.plan()
    assert _coada(izolat) == ["https://izz.ro/extern/eveniment/"], \
        "continut schimbat la acelasi permalink -> trebuie reanuntat, indiferent de published"


def test_publicarea_unui_articol_nou_intra_in_coada(izolat):
    _scrie(indexnow.STATE, [_art("a", ore_in_urma=1)])
    indexnow.plan()
    _scrie(indexnow.STATE, [_art("a", ore_in_urma=1), _art("b", ore_in_urma=0.2)])
    indexnow.plan()
    assert _coada(izolat) == ["https://izz.ro/extern/b/"]


def test_peste_plafon_restul_revine_la_rularea_urmatoare(izolat, monkeypatch):
    """Un bump de PROMPT_VERSION face mii de articole eligibile deodata. Ce nu incape in
    transa NU are voie sa fie marcat ca vazut — altfel se pierde definitiv."""
    monkeypatch.setattr(indexnow, "BATCH_MAX", 2)
    arts = [_art(f"a{i}", ore_in_urma=50) for i in range(5)]
    _scrie(indexnow.STATE, arts)
    indexnow.plan()                                   # seed: nimic proaspat, manifest plin
    rescrise = [dict(a, title=f"nou {i}") for i, a in enumerate(arts)]
    _scrie(indexnow.STATE, rescrise)

    indexnow.plan()
    prima = _coada(izolat)
    assert len(prima) == 2
    indexnow.plan()
    a_doua = _coada(izolat)
    assert len(a_doua) == 2
    assert not set(prima) & set(a_doua), "transa a doua repeta URL-uri deja trimise"
    indexnow.plan()
    assert len(_coada(izolat)) == 1, "ultimul ramas trebuie sa iasa, nu sa se piarda"


def test_seed_peste_plafon_nu_pierde_proaspetele_care_nu_incap(izolat, monkeypatch):
    """La insamantare, ce a intrat in coada dar n-a incaput in transa NU are voie sa fie
    marcat ca vazut — altfel o prima rulare cu multe articole proaspete (recuperare cu buget
    marit) le-ar anunta pe primele si le-ar ingropa tacut pe restul."""
    monkeypatch.setattr(indexnow, "BATCH_MAX", 2)
    _scrie(indexnow.STATE, [_art(f"p{i}", ore_in_urma=0.5) for i in range(5)])
    indexnow.plan()
    prima = _coada(izolat)
    assert len(prima) == 2
    indexnow.plan()
    a_doua = _coada(izolat)
    assert len(a_doua) == 2 and not set(prima) & set(a_doua)
    indexnow.plan()
    assert len(_coada(izolat)) == 1, "ultimul proaspat trebuie sa iasa, nu sa se piarda"


def test_manifestul_nu_creste_la_nesfarsit(izolat):
    """Articolele expira la TTL; intrarile lor trebuie sa iasa din manifest."""
    _scrie(indexnow.STATE, [_art("a"), _art("b")])
    indexnow.plan()
    _scrie(indexnow.STATE, [_art("b")])
    indexnow.plan()
    assert set(_manifest()) == {"https://izz.ro/extern/b/"}


def test_hash_ul_ignora_campurile_interne(izolat):
    """O reorganizare de stare (categorie repinata, camp nou) nu e o schimbare de continut
    pentru cititor — cu o exceptie: categoria e in URL, deci acolo se schimba URL-ul, nu hash-ul."""
    a = _art("x")
    assert indexnow._hash(a) == indexnow._hash(dict(a, first_seen="2026-01-01", prompt_version="v9"))
    assert indexnow._hash(a) != indexnow._hash(dict(a, teaser="alt corp"))
