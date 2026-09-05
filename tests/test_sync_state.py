"""Garzi pentru `tools/sync_state.py` — adnotarea automata a lui STATE.md.

DE CE EXISTA, masurat 2026-09-04: prima versiune a uneltei detecta PR-urile aterizate DOAR
prin `git log --merges`. PR-ul #247 a fost aterizat prin rebase — fara commit de merge, fara
sufixul de squash `(#247)`, si cu head-ul PR-ului nemaifiind stramos al lui `main`. Unealta
nu-l vedea si tiparea „este deja sincronizat", adica raporta certitudine unde n-avea nici
informatie. Intr-un fisier care e memoria comuna a mai multor agenti care lucreaza in
paralel, un fals negativ TACUT e mai rau decat un semn de intrebare vizibil.

Testele de aici NU ating git: `merged_prs()` e injectata. Ce se verifica e logica de decizie
— ce se adnoteaza, ce se lasa in pace si, mai ales, ce se RAPORTEAZA ca nedecis.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("sync_state", ROOT / "tools" / "sync_state.py")
sync_state = importlib.util.module_from_spec(_spec)
sys.modules["sync_state"] = sync_state
_spec.loader.exec_module(sync_state)


STATE_EXEMPLU = """# STATE

## Open

- **PR-uri deschise:** #247 prospetime 72h. Owner: #207.
- **Alta linie:** #248 ceva.

## Standing rules

- Linia asta e in ALTA sectiune si contine #999 — nu trebuie atinsa.
"""


@pytest.fixture
def state(tmp_path, monkeypatch):
    """Un STATE.md izolat, cu directorul curent mutat peste el."""
    (tmp_path / "STATE.md").write_text(STATE_EXEMPLU, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path / "STATE.md"


def test_adnoteaza_doar_ce_git_poate_dovedi(state, monkeypatch):
    monkeypatch.setattr(sync_state, "merged_prs", lambda: {"248"})
    sync_state.reconcile()
    text = state.read_text(encoding="utf-8")
    assert "#248 ceva. (merged)" in text, "PR-ul dovedit nu a primit adnotarea"
    assert "#247 prospetime 72h. Owner: #207." in text, "PR-ul nedovedit a fost adnotat gresit"


def test_nu_atinge_sectiunile_din_afara_lui_open(state, monkeypatch):
    monkeypatch.setattr(sync_state, "merged_prs", lambda: {"999"})
    sync_state.reconcile()
    assert "#999 — nu trebuie atinsa." in state.read_text(encoding="utf-8")


def test_raporteaza_explicit_ce_nu_poate_decide(state, monkeypatch, capsys):
    """Regresia care a motivat fisierul: #247 nu mai are voie sa dispara in tacere."""
    monkeypatch.setattr(sync_state, "merged_prs", lambda: {"248"})
    sync_state.reconcile()
    iesire = capsys.readouterr().out
    assert "NU POT DECIDE" in iesire
    assert "#247" in iesire.split("NU POT DECIDE")[1], "#247 lipseste din lista de nedecise"


STATE_CU_PARANTEZA_ISTORICA = """# STATE

## Open

- **Regula care doar CITEAZA #248**: nu pretinde ca ar fi deschis.
- **Istoric pe aceeasi linie:** (#253 merged; #248 merged; #244 merged).
- **Aterizat prin rebase:** #247, declarat merged chiar aici.

## Standing rules
"""


@pytest.fixture
def state_paranteza(tmp_path, monkeypatch):
    (tmp_path / "STATE.md").write_text(STATE_CU_PARANTEZA_ISTORICA, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path / "STATE.md"


def test_nu_adnoteaza_de_doua_ori_un_pr_declarat_deja_altundeva(state_paranteza, monkeypatch, capsys):
    """Divergenta masurata 2026-09-04 intre unealta asta si `tests/test_pr_fantoma.py`.

    Garda scaneaza TOT blocul `## Open` dupa `#N ... merged`, deci pentru ea `#248` e deja
    adnotat prin linia-paranteza si trece. Unealta lucra pe linie si voia sa mai adauge un
    `(merged)` pe bullet-ul de regula care doar il citeaza — zgomot, si crestere spre
    plafonul de 40 de linii pe care il pazeste ALTA garda. Autoritatea e garda din CI.
    """
    monkeypatch.setattr(sync_state, "merged_prs", lambda: {"248", "253", "244"})
    sync_state.reconcile()
    text = state_paranteza.read_text(encoding="utf-8")
    assert "#248**: nu pretinde ca ar fi deschis." in text, \
        f"bullet-ul de regula a fost adnotat inutil:\n{text}"
    assert text == STATE_CU_PARANTEZA_ISTORICA, "fisierul nu trebuia atins deloc"
    assert "adnotate (merged)" not in capsys.readouterr().out


def test_nu_mai_raporteaza_nedecis_un_pr_declarat_merged_in_text(state_paranteza, monkeypatch, capsys):
    """`#247` e nedovedibil din git la infinit (rebase). Odata declarat in text, tace.

    Fara asta, avertismentul s-ar repeta la fiecare rulare pentru totdeauna, iar unul care
    nu se stinge niciodata e zgomot pe care cititorul invata sa-l sara.
    """
    monkeypatch.setattr(sync_state, "merged_prs", lambda: set())
    sync_state.reconcile()
    iesire = capsys.readouterr().out
    assert "#247" not in iesire, f"#247 e declarat merged in text, nu mai e nedecis:\n{iesire}"


def test_declaratia_merged_se_citeste_pe_tot_blocul_nu_pe_linie():
    """Aceeasi semantica cu `PR_MERGED_ANNOT` din garda — daca diverg, se contrazic din nou."""
    declarate = sync_state.deja_declarate_merged(STATE_CU_PARANTEZA_ISTORICA)
    assert {"253", "248", "244", "247"} <= declarate, declarate
    assert sync_state.deja_declarate_merged("## Open\n\n- doar #99 fara nimic\n") == set()


def test_dry_run_nu_scrie(state, monkeypatch):
    monkeypatch.setattr(sync_state, "merged_prs", lambda: {"248"})
    inainte = state.read_text(encoding="utf-8")
    sync_state.reconcile(dry_run=True)
    assert state.read_text(encoding="utf-8") == inainte


@pytest.mark.parametrize("subiect,asteptat", [
    ("feat(home): prospetime 72h (#247)", "247"),
    ("Merge pull request #248 from x", None),      # alt tipar, prins de cealalta cale
    ("chore: ceva (#123) si text dupa", None),     # sufixul trebuie sa fie la FINAL
])
def test_tiparul_de_squash(subiect, asteptat):
    m = sync_state._SQUASH.search(subiect)
    assert (m.group(1) if m else None) == asteptat
