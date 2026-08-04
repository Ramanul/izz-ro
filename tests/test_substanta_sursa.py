"""Poarta de SUBSTANTA: un item fara fapte peste titlu nu se sintetizeaza si nu se publica.

Cazul care a generat regula e raportat de proprietar pe 2026-08-04, de pe live: titlul
„Gestul neobisnuit al unui portar in minutul 90+3 a uimit asistenta" si teaserul
„Finalul meciului disputat la scorul de 2-2 a fost marcat de un moment neobisnuit...".
Nu spun cine, ce meci, ce gest — fiindca sursa trimisese `description` IDENTICA cu `title`.

Ce e important de inteles daca modifici asta: AI-ul NU a halucinat. A primit un titlu clickbait
si i s-a cerut un rezumat, iar promptul ii spunea explicit „daca descrierea e saraca, extrage
esenta din titlul original". Defectul e ca itemul a ajuns la AI si de acolo pe site.
"""
import pytest

from generator import config, select
from generator.util import cuvinte_adaugate

# Itemul REAL, copiat din feedul digisport (fetch._fetch_one_guarded, 2026-08-04).
TITLU_DIGISPORT = ('”Sigur nu ai mai văzut așa ceva!” Toată lumea a rămas ”mască”, '
                   'după gestul portarului la 2-2, în minutul 90+3')


def test_cazul_raportat_are_zero_substanta():
    """Sursa trimite descrierea identica cu titlul. Asta e intrarea, nu o reconstructie."""
    assert cuvinte_adaugate(TITLU_DIGISPORT, TITLU_DIGISPORT) == 0


def test_descrierea_care_repeta_titlul_si_adauga_fapte_trece():
    """Contra-exemplu care apara masura: multe surse REPETA titlul si apoi continua.
    O regula bazata pe „descrierea contine titlul" le-ar fi taiat pe toate — prima varianta a
    masuratorii chiar a facut asta si a raportat 44% in loc de 23%."""
    titlu = "Guvernul a aprobat bugetul"
    desc = ("Guvernul a aprobat bugetul pe 2027, cu un deficit de 4,4% din PIB, "
            "dupa trei runde de negocieri cu Comisia Europeana")
    assert cuvinte_adaugate(titlu, desc) >= config.MIN_SUBSTANTA_CUVINTE


@pytest.mark.parametrize("desc", ["", "   ", TITLU_DIGISPORT])
def test_descriere_goala_sau_egala_nu_are_substanta(desc):
    assert cuvinte_adaugate(TITLU_DIGISPORT, desc) < config.MIN_SUBSTANTA_CUVINTE


def _articol(**kw):
    baza = {"title": "Un titlu oarecare", "teaser": "Un teaser diferit si plauzibil de lung.",
            "model": "B", "processed_by": "gemini", "original_link": "https://x.ro/a"}
    baza.update(kw)
    return baza


def test_poarta_respinge_articolul_sintetizat_dintr_o_sursa_fara_substanta():
    """Exact gaura: teaserul E nevid, E diferit de titlu, NU e trunchiat, NU e fallback —
    deci toate verificarile de FORMA trec. Doar `src_extra` se uita la ce a trimis sursa."""
    assert select._quality_gate(_articol(src_extra=0)) is False
    assert select._quality_gate(_articol(src_extra=config.MIN_SUBSTANTA_CUVINTE - 1)) is False


def test_poarta_lasa_sa_treaca_articolul_cu_substanta():
    assert select._quality_gate(_articol(src_extra=config.MIN_SUBSTANTA_CUVINTE)) is True
    assert select._quality_gate(_articol(src_extra=40)) is True


def test_articolele_vechi_fara_campul_src_extra_nu_sunt_respinse():
    """Starea comisa in repo are ~2130 de articole scrise inainte de campul asta. Absenta lui
    inseamna „nu stiu", nu „fara substanta" — altfel un deploy ar goli feedul dintr-o data."""
    assert select._quality_gate(_articol()) is True


def test_sursele_oficiale_nu_sunt_atinse_de_poarta_de_substanta():
    """Primariile (pl_/cj_/pr_) nu trec prin AI deloc (`process_official` cheama providerul None),
    deci nu pot fabrica nimic, iar anunturile lor cu descriere goala sunt exact continutul pentru
    care exista rubrica `local`. Decizie de proprietar, 2026-08-04."""
    assert select._quality_gate(_articol(processed_by="official", src_extra=0)) is True
