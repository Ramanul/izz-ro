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


def test_pipe_in_notes_escaped_so_markdown_table_survives(sandbox):
    log_slice.append(_Args(notes="a | b"))
    log_slice.report()
    text = open(log_slice.REPORT, encoding="utf-8").read()
    assert "a \\| b" in text
