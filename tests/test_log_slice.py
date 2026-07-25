"""Jurnalul de munca/consum: scriere sigura si raport corect. Fara retea, fara efecte."""
import csv
import importlib

import pytest

log_slice = importlib.import_module("tools.log_slice")


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirecteaza jurnalul si raportul in tmp, ca testele sa nu atinga fisierele reale."""
    monkeypatch.setattr(log_slice, "LOG", str(tmp_path / "specs" / "metrics.csv"))
    monkeypatch.setattr(log_slice, "REPORT", str(tmp_path / "COORD-DASHBOARD.md"))
    return tmp_path


class _Args:
    def __init__(self, **kw):
        d = dict(account="B", slice="s", approach="solo", executor_branch="",
                 diff_lines=10, duration_min=None, tokens_k=5, notes="")
        d.update(kw)
        self.__dict__.update(d)


def test_creates_header_once_then_appends(sandbox, capsys):
    log_slice.append(_Args(slice="unu"))
    log_slice.append(_Args(slice="doi"))
    with open(log_slice.LOG, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == log_slice.COLUMNS          # antet o singura data
    assert len(rows) == 3                        # antet + 2 randuri
    assert rows[1][2] == "unu" and rows[2][2] == "doi"


def test_formula_injection_is_neutralised(sandbox):
    log_slice.append(_Args(notes="=SUM(A1:A9)"))
    with open(log_slice.LOG, encoding="utf-8") as fh:
        row = list(csv.DictReader(fh))[0]
    assert row["notes"].startswith("'="), "celula ar fi interpretata ca formula"


def test_notes_with_commas_survive_roundtrip(sandbox):
    log_slice.append(_Args(notes="a, b, c"))
    with open(log_slice.LOG, encoding="utf-8") as fh:
        assert list(csv.DictReader(fh))[0]["notes"] == "a, b, c"


def test_report_totals_and_per_account_split(sandbox):
    log_slice.append(_Args(account="A", diff_lines=100, tokens_k=10))
    log_slice.append(_Args(account="B", diff_lines=50, tokens_k=40, approach="agent"))
    log_slice.report()
    text = open(log_slice.REPORT, encoding="utf-8").read()
    assert "**2 slice-uri**" in text and "150 linii" in text and "~50k tokeni" in text
    assert "| A | 1 | 100 | 10 |" in text
    assert "| B | 1 | 50 | 40 |" in text


def test_report_on_empty_log_does_not_crash(sandbox, capsys):
    assert log_slice.report() == 0
    assert "gol" in capsys.readouterr().out


def test_empty_report_overwrites_stale_dashboard(sandbox):
    """Jurnal sters => raportul se rescrie gol. Altfel dashboard-ul de coordonare
    arata slice-uri care nu mai exista si minte pe cine se bazeaza pe el."""
    log_slice.append(_Args(slice="dispare"))
    log_slice.report()
    assert "dispare" in open(log_slice.REPORT, encoding="utf-8").read()
    import os
    os.remove(log_slice.LOG)
    log_slice.report()
    assert "dispare" not in open(log_slice.REPORT, encoding="utf-8").read()


def test_header_written_for_precreated_empty_file(sandbox):
    """Un `touch` sau un checkout care lasa fisierul vid nu trebuie sa produca un rand
    fara antet — DictReader ar lua primul rand drept antet si jurnalul ar disparea tacit."""
    import os
    os.makedirs(os.path.dirname(log_slice.LOG), exist_ok=True)
    open(log_slice.LOG, "w").close()          # fisier pre-creat, gol
    log_slice.append(_Args(slice="primul"))
    with open(log_slice.LOG, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == log_slice.COLUMNS
    assert len(list(csv.DictReader(open(log_slice.LOG, encoding="utf-8")))) == 1


def test_same_day_rows_are_newest_first(sandbox):
    """Se logheaza doar ziua, deci randurile din aceeasi zi sunt la egalitate; fara
    departajare dupa pozitie, tabelul „cele mai recente primele" le da pe dos."""
    for name in ("vechi", "mijloc", "nou"):
        log_slice.append(_Args(slice=name))
    log_slice.report()
    text = open(log_slice.REPORT, encoding="utf-8").read()
    assert text.index("| nou ") < text.index("| mijloc ") < text.index("| vechi ")


def test_long_notes_are_cut_at_a_word_boundary(sandbox):
    """Trunchierea oarba lasa cioburi de tip „datele Actio" si raportul pare stricat."""
    log_slice.append(_Args(notes="cuvant " * 20 + "coada"))
    log_slice.report()
    rand = [ln for ln in open(log_slice.REPORT, encoding="utf-8") if ln.startswith("| 2")][0]
    nota = rand.split("|")[-2].strip()
    assert nota.endswith("…")
    assert not nota[:-1].rstrip().endswith("cuv"), "taiat prin mijlocul cuvantului"
    assert len(nota) <= 70          # _scurt(..., n=70) — 71 ar lasa sa treaca o regresie


def test_short_notes_are_left_alone(sandbox):
    log_slice.append(_Args(notes="scurt si intreg"))
    log_slice.report()
    assert "| scurt si intreg |" in open(log_slice.REPORT, encoding="utf-8").read()


def test_multiline_notes_do_not_break_the_table(sandbox):
    log_slice.append(_Args(notes="prima linie\na doua linie"))
    log_slice.report()
    body = open(log_slice.REPORT, encoding="utf-8").read()
    table = [ln for ln in body.splitlines() if ln.startswith("| 2")]
    assert len(table) == 1, "o valoare multilinie a produs randuri suplimentare"
    assert "prima linie a doua linie" in table[0]


def test_pipe_in_notes_escaped_so_markdown_table_survives(sandbox):
    log_slice.append(_Args(notes="a | b"))
    log_slice.report()
    text = open(log_slice.REPORT, encoding="utf-8").read()
    assert "a \\| b" in text


def test_report_carries_generation_timestamp(sandbox):
    """Fara marca de timp, un raport de acum trei zile arata identic cu unul regenerat acum —
    exact reclamatia proprietarului („nu e live, datele sunt de ieri"), imposibil de verificat."""
    from datetime import datetime, timezone
    log_slice.append(_Args())
    log_slice.report()
    text = open(log_slice.REPORT, encoding="utf-8").read()
    assert "Generat:" in text and "UTC" in text
    assert datetime.now(timezone.utc).strftime("%Y-%m-%d") in text
    assert "ultimul slice raportat:" in text
