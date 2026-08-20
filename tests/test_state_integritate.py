"""Integritatea lui `data/articles.json` — scriere atomica, stare corupta, garda de colaps.

DE CE EXISTA (audit 2026-08-20, [P1]): fisierul are 5,6 MB si 4616 articole, si ESTE site-ul.
Trei defecte se compuneau intr-un drum catre pierderea arhivei:
  (a) scriere directa peste fisier -> o rulare oprita la jumatate lasa JSON trunchiat;
  (b) `load()` inghitea `JSONDecodeError` si intorcea `[]` -> stare corupta indistingibila
      de prima rulare, deci pipeline-ul pornea pe gol;
  (c) nimic nu compara „cate articole aveam" cu „cate salvez" inainte de commit.
`qa_check.py` ar fi prins rezultatul, dar ruleaza DUPA commit si deploy.
"""
import json
import pytest

from generator import state


@pytest.fixture
def stare(tmp_path, monkeypatch):
    p = tmp_path / "articles.json"
    monkeypatch.setattr(state, "STATE_PATH", str(p))
    return p


def _articole(n, prefix="a"):
    return [{"url": f"https://x.ro/{prefix}{i}", "published": "2026-08-20T00:00:00+00:00"}
            for i in range(n)]


# --- (a) scriere atomica -------------------------------------------------------------------

def test_salvarea_nu_lasa_fisier_temporar(stare):
    state.save(_articole(5))
    assert stare.exists()
    assert not stare.with_suffix(".json.tmp").exists()
    assert len(json.loads(stare.read_text(encoding="utf-8"))) == 5


def test_scrierea_esuata_NU_distruge_starea_veche(stare, monkeypatch):
    """Miezul atomicitatii: daca serializarea crapa, pe disc ramane versiunea INTREAGA veche."""
    state.save(_articole(200))
    vechi = stare.read_text(encoding="utf-8")

    def _crapa(*a, **k):
        raise OSError("disc plin")
    monkeypatch.setattr(state.json, "dump", _crapa)
    with pytest.raises(OSError):
        state.save(_articole(200, prefix="b"))
    assert stare.read_text(encoding="utf-8") == vechi, "starea veche a fost stricata"


# --- (b) stare corupta ---------------------------------------------------------------------

def test_fisier_lipsa_e_prima_rulare_nu_eroare(stare):
    assert state.load() == []


def test_stare_corupta_OPRESTE_rularea(stare):
    stare.write_text('[{"url": "https://x.ro/1"}, {"url": "trun', encoding="utf-8")
    with pytest.raises(state.StareCorupta) as e:
        state.load()
    assert "articles.json" in str(e.value)
    assert "git checkout" in str(e.value), "mesajul trebuie sa spuna si cum se repara"


def test_json_valid_dar_nu_lista_OPRESTE_rularea(stare):
    stare.write_text('{"articole": []}', encoding="utf-8")
    with pytest.raises(state.StareCorupta):
        state.load()


# --- (c) garda de colaps -------------------------------------------------------------------

def test_colapsul_e_refuzat(stare):
    state.save(_articole(1000))
    with pytest.raises(state.StareCorupta) as e:
        state.save(_articole(50))
    assert "1000" in str(e.value) and "50" in str(e.value)


def test_scadere_normala_prin_expirare_trece(stare):
    """Cu TTL de 7 zile si rulari orare, o rulare pierde ~1%. 900 din 1000 nu e colaps."""
    state.save(_articole(1000))
    state.save(_articole(900))
    assert len(json.loads(stare.read_text(encoding="utf-8"))) == 900


def test_corpus_mic_nu_declanseaza_garda(stare):
    """Sub 100 de articole fractia nu inseamna nimic — repopularea trebuie sa fie posibila."""
    state.save(_articole(40))
    state.save(_articole(3))
    assert len(json.loads(stare.read_text(encoding="utf-8"))) == 3


def test_colapsul_se_poate_permite_explicit(stare, monkeypatch):
    state.save(_articole(1000))
    monkeypatch.setenv("IZZ_PERMITE_COLAPS", "1")
    state.save(_articole(10))
    assert len(json.loads(stare.read_text(encoding="utf-8"))) == 10
