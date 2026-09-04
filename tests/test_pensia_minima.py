"""Regresii pentru datele despre indemnizația socială pentru pensionari."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pensia_minima_are_valoarea_cnpp_si_sursa_oficiala():
    text = (ROOT / "data/entities/pensia-minima.yaml").read_text(encoding="utf-8")
    assert "brut: 1281" in text
    assert "ultima_verificare: \"2026-09-04\"" in text
    assert "https://www.cnpp.ro/statistici/evolutia-indemnizatiei-sociale/" in text
    assert "verificat: true" in text
    assert "stagiul minim de cotizare realizat: 15 ani" not in text
