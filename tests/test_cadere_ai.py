"""`cadere_ai` — cand se considera rularea lipsita de AI in mod sistemic.

DE CE EXISTA (audit 2026-08-20, [C3]): conditia era scrisa inline si incepea cu `bool(provider)`,
deci cazul „nu exista NICIUN provider" intorcea False — adica exact esecul cel mai grav nu aprindea
alarma. Rularea reusea, comitea si publica. Predicatul e acum separat tocmai ca sa fie testabil.
"""
from generator.main import cadere_ai


class _P:
    def __init__(self, calls, failures):
        self.calls = calls
        self.failures = failures


def test_fara_provider_e_cadere():
    """Cazul reparat: niciun provider disponibil (cheie stearsa/expirata)."""
    assert cadere_ai(None) is True


def test_toate_apelurile_esuate_e_cadere():
    assert cadere_ai(_P(calls=7, failures=7)) is True


def test_niciun_apel_NU_e_cadere():
    """„N-a fost nimic nou de procesat" nu e o cadere — nu opri publicarea pentru asta."""
    assert cadere_ai(_P(calls=0, failures=0)) is False


def test_esec_partial_NU_e_cadere():
    """Un 429 tranzitoriu pe cateva apeluri nu justifica inghetarea site-ului."""
    assert cadere_ai(_P(calls=10, failures=3)) is False
