"""`ai_cat` — tema BRUTA aleasa de model, salvata langa categoria rezolvata.

De ce exista testul: `_resolve_category` primea categoria AI, o folosea si o arunca. In
`data/articles.json` ramanea doar REZULTATUL, deci intrarea nu mai putea fi reconstruita.
Masurat pe corpusul real (2026-08-07): **0 din 2766** de articole aveau campul, in timp ce
`entities` era prezent la 2550. Consecinta practica: nicio schimbare de clasificare nu putea
fi rejucata pe corpus fara sa platesti apelurile AI din nou. Limitarea e consemnata in
registru la WS-0026 — „nemasurabil retroactiv: ai_cat nu se salveaza in articles.json".

Contrastul care explica de ce merita cele trei linii: `entities` SE salva, si exact de-aia
#156 a putut fi masurat retroactiv pe 1075 de articole, fara buget si fara prompt nou.
`ai_cat` e cealalta jumatate a intrarii aceleiasi functii.

Ce apara testele de mai jos, concret:
  1. campul e scris pe TOATE cele trei cai AI (lot, individual, cluster) — o cale uitata
     inseamna o gaura tacuta in corpus, exact felul de defect care se descopera peste o luna;
  2. valoarea e cea BRUTA, nu cea rezolvata — daca ar fi egale prin constructie, campul
     n-ar adauga nicio informatie si masuratoarea retroactiva ar fi o iluzie;
  3. supravietuieste lui `state.save()`. Azi `_scrub_processed` e o lista NEAGRA (sterge
     `original_title` si `description`), deci trece orice camp nou. Daca cineva o converteste
     vreodata in lista alba, `ai_cat` ar disparea in tacere si nimeni n-ar afla decat cand
     urmatoarea masuratoare ar da din nou zero.
"""
import json

import pytest

from generator import process, state


class _Provider:
    """Provider fals: nu cheama nimic, intoarce raspunsul JSON dat la construire."""
    name = "fake"

    def __init__(self, payload):
        self._payload = payload

    def complete(self, system, user):
        return json.dumps(self._payload)


# Articolul e VERBATIM din corpus (vezi tests/test_category_pin.py, aceeasi stire). Conteaza
# ca e un caz in care modelul zice o tema, iar `_resolve_category` intoarce altceva: e singurul
# fel in care se poate arata ca `ai_cat` NU e o copie a lui `category`.
_TITLU = "Polițiștii brașoveni au cumpărat limonadă de la un stand infantil"
_TEASER = ("O patrulă de poliție din Brașov s-a oprit pentru a sprijini inițiativa unor copii "
           "care deschiseseră un punct de vânzare a limonadei.")
_GEOGRAFICE = {"local", "zonal", "regional"}


def _item():
    return {"source": "bizbrasov", "source_name": "BizBrasov", "category": "local",
            "original_link": "https://bizbrasov.ro/a", "url": "https://bizbrasov.ro/a",
            "original_title": _TITLU, "description": _TEASER, "published": "2026-08-07T09:00:00+00:00"}


def _raspuns(cat="social"):
    return {"title": _TITLU, "teaser": _TEASER, "category": cat, "entities": ["Brasov"],
            "icon": "shield"}


# --- campul exista pe toate cele trei cai AI ---------------------------------------------

def test_process_single_salveaza_tema_bruta():
    out = process.process_single(_item(), _Provider(_raspuns()))
    assert out is not None
    assert out["ai_cat"] == "social"


def test_process_batch_salveaza_tema_bruta():
    payload = dict(_raspuns(), id=0)
    out = process.process_batch([_item()], _Provider([payload]))
    assert len(out) == 1
    assert out[0]["ai_cat"] == "social"


def test_process_cluster_salveaza_tema_bruta():
    grup = [_item(), dict(_item(), url="https://alt.ro/b", original_link="https://alt.ro/b",
                          source="zcj", source_name="Ziar de Cluj")]
    payload = dict(_raspuns())
    payload["synthesis"] = "Sinteza pe doua surse."
    out = process.process_cluster(grup, _Provider(payload))
    assert out is not None
    assert out["ai_cat"] == "social"


# --- si e BRUTA, adica poate sa difere de categoria finala --------------------------------

def test_tema_bruta_difera_de_categoria_rezolvata():
    """Inima felii. Modelul zice `social`, gazetteer-ul + `entities` trimit stirea pe axa
    geografica. Daca cele doua campuri ar fi mereu egale, `ai_cat` n-ar valora nimic."""
    out = process.process_single(_item(), _Provider(_raspuns("social")))
    assert out["category"] in _GEOGRAFICE
    assert out["ai_cat"] == "social"
    assert out["ai_cat"] != out["category"]


def test_tema_invalida_se_salveaza_nenormalizata():
    """Cazul care face campul util la diagnostic: cand modelul intoarce o categorie
    inexistenta, `category` cade pe fallback si urma disparea. Acum ramane exact ce a zis
    modelul — inclusiv spatiile — altfel rejucarea offline ar minti fata de ce a primit
    `_resolve_category` la ingestie."""
    out = process.process_single(_item(), _Provider(_raspuns(" inexistent ")))
    assert out["ai_cat"] == " inexistent "
    assert out["category"] not in {" inexistent ", "inexistent"}


def test_tema_lipsa_din_raspuns_nu_arunca():
    """Fara `category` in JSON, campul devine sirul gol — nu `None`, nu KeyError. Contractul
    conteaza fiindca o masuratoare viitoare va filtra pe el."""
    raspuns = _raspuns()
    del raspuns["category"]
    out = process.process_single(_item(), _Provider(raspuns))
    assert out["ai_cat"] == ""


# --- si ajunge efectiv in fisier ----------------------------------------------------------

def test_campul_supravietuieste_salvarii(tmp_path, monkeypatch):
    """`state.save()` ruleaza `_scrub_processed` peste articole inainte sa scrie. Testul
    apara campul de o eventuala trecere a scrub-ului pe lista alba."""
    p = tmp_path / "articles.json"
    monkeypatch.setattr(state, "STATE_PATH", str(p))
    out = process.process_single(_item(), _Provider(_raspuns()))
    state.save([out])
    salvate = json.loads(p.read_text(encoding="utf-8"))
    assert salvate[0]["ai_cat"] == "social"


def test_scrubul_taie_in_continuare_textele_brute(tmp_path, monkeypatch):
    """Contra-proba a testului de mai sus: nu am slabit scrub-ul juridic ca sa treaca campul
    nou. `original_title` si `description` trebuie sa dispara in continuare (L8/1996)."""
    p = tmp_path / "articles.json"
    monkeypatch.setattr(state, "STATE_PATH", str(p))
    out = process.process_single(_item(), _Provider(_raspuns()))
    state.save([out])
    salvate = json.loads(p.read_text(encoding="utf-8"))
    assert "original_title" not in salvate[0]
    assert "description" not in salvate[0]


# --- si nu strica articolele deja existente, care n-au campul -----------------------------

@pytest.mark.parametrize("vechi", [
    {"title": "Stire veche", "category": "economic", "processed_by": "gemini"},
    {"title": "Anunt oficial", "category": "local", "processed_by": "official"},
])
def test_articolele_fara_camp_raman_valide(tmp_path, monkeypatch, vechi):
    """Cele 2766 de articole din stare n-au `ai_cat` si nu-l vor capata niciodata — categoria
    se calculeaza o singura data, la ingestie. Nimic nu are voie sa-l ceara obligatoriu."""
    p = tmp_path / "articles.json"
    monkeypatch.setattr(state, "STATE_PATH", str(p))
    state.save([dict(vechi, published="2026-08-01T00:00:00+00:00")])
    salvate = json.loads(p.read_text(encoding="utf-8"))
    assert salvate[0].get("ai_cat") is None
