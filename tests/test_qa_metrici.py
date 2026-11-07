"""Cele doua masuratori de „dublura" din `qa_check.py`, dupa separarea din 7 nov 2026.

DE CE. Pana atunci o singura linie — „posibile duplicate de eveniment" (titluri cu ≥4 stem-uri
comune) — raporta 17% si dadea AVERTISMENT la fiecare rulare. Masurat pe stare: din 1100 de
articole flagate, **0** perechi aveau acelasi `url` (dedup-ul de stare le prinsese deja) si
doar 40 (0,6%) erau aceeasi sursa cu titlu identic in 7 zile; restul erau subiecte recurente
(„Black Friday", „Cernavoda", congres PNL) reluate legitim saptamani la rand. O poarta pe
cifra aceea ar fi cerut sub-unirea unor stiri care nu sunt aceeasi stire — adica exact
decizia editoriala pe care un instrument de masura n-are voie s-o ia singur.

Acum: suprapunerea de subiect ramane afisata, fara poarta; poarta sta pe republicare
(aceeasi sursa + titlu identic + fereastra scurta), singura clasa care e defect prin constructie.
"""
from datetime import datetime, timedelta, timezone

from tools import qa_check


def _art(sursa: str, titlu: str, ore_in_urma: float, slug: str | None = None) -> dict:
    return {
        "source_name": sursa,
        "title": titlu,
        "slug": slug or f"{sursa}-{abs(hash((sursa, titlu, ore_in_urma)))}",
        "published": (datetime.now(timezone.utc) - timedelta(hours=ore_in_urma)).isoformat(),
        "model": "B",
    }


def test_republicarea_in_aceeasi_saptamana_e_prinsa():
    a = _art("Primăria Slobozia", "Listă titluri executorii", 30)
    b = _art("Primăria Slobozia", "listă titluri executorii", 2)   # cazul real: majuscule diferite
    assert len(qa_check._republicari([a, b])) == 1


def test_aceeasi_stire_din_surse_diferite_nu_e_republicare():
    a = _art("Digi24", "Guvernul a adoptat bugetul", 5)
    b = _art("HotNews", "Guvernul a adoptat bugetul", 4)
    assert qa_check._republicari([a, b]) == []


def test_titluri_identice_la_o_luna_distanta_nu_sunt_dublura():
    """Anunturile lunare ale aceleiasi institutii revin legitim cu acelasi titlu."""
    a = _art("Primăria Roman", "Listă titluri executorii", 24 * 35)
    b = _art("Primăria Roman", "Listă titluri executorii", 2)
    assert qa_check._republicari([a, b]) == []


def test_republicarile_numara_articolele_implicate_nu_perechile():
    """Trei publicari ale aceluiasi anunt = 3 articole in raport, nu 2 perechi."""
    arts = [_art("Primăria X", "Anunţ concurs", 50),
            _art("Primăria X", "Anunţ concurs", 20),
            _art("Primăria X", "Anunţ concurs", 1)]
    perechi = qa_check._republicari(arts)
    assert len(perechi) == 2
    assert len({a["slug"] for p in perechi for a in p}) == 3


def test_pragul_de_republicare_e_sub_masuratoarea_din_productie():
    """0,6% masurat pe 7 nov 2026 — pragul trebuie sa fie peste zgomotul de baza."""
    assert qa_check.REPUBLICARE_WARN_RATE > 0.006
