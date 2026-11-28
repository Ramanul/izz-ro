"""Teste pentru `generator.ton`: subiectul greu se recunoaște literal, metaforele nu declanșează."""
import pytest

from generator import ton


@pytest.mark.parametrize("titlu", [
    "Un bărbat din Galați și-a ucis ambii părinți",
    "Doi tineri au murit într-un accident la Arad",
    "Femeie găsită moartă într-un apartament din Cluj",
    "Procurorii cer arestarea unui bărbat acuzat de omor",
    "Bărbat înjunghiat în fața unui bar",          # cu diacritice
    "Barbat injunghiat in fata unui bar",           # fără diacritice
    "Tânăr acuzat de viol, reținut de polițiști",
    "Adolescentă, victimă a unei agresiuni sexuale",
    "Trei morți și cinci răniți după o explozie",
    "Cadavrul unui bărbat a fost găsit în râu",
    "Încercare de sinucidere, salvat de un polițist",
])
def test_subiect_greu_recunoaste_literal(titlu):
    assert ton.subiect_greu(titlu, "local")


@pytest.mark.parametrize("titlu", [
    "Violet Evergarden revine pe ecrane",
    "Concert de violoncel la Ateneu",
    "Amortizor nou pentru tramvaiele din Iași",
    "Un comic mort de râs pe scenă",
    "Punct mort în negocierile de la Bruxelles",
    "Expoziție de natură moartă la muzeu",
    "Călătorie la Marea Moartă",
    "Prețul inviolabil al pâinii crește",
    "Incendiu a distrus 50 de tone de fân",         # fără oameni: nu e semn
])
def test_nu_declanseaza_pe_cuvinte_asemanatoare(titlu):
    assert not ton.subiect_greu(titlu, "local")


def test_strat_2_nu_se_aplica_in_sport_economie_cultura():
    assert not ton.subiect_greu("Masacru pe bursă după raportul băncii", "economic")
    assert not ton.subiect_greu("Victimă a unui penalty controversat", "sport")
    assert not ton.subiect_greu("Crima perfectă, thriller nou la Hollywood", "cultura")


def test_strat_2_se_aplica_in_rubricile_de_stiri():
    assert ton.subiect_greu("Masacrul de la Jilava, comemorat azi", "local")
    assert ton.subiect_greu("Victimele inundațiilor, despăgubite", "extern")
    assert ton.subiect_greu("Atac armat într-o școală din SUA", "extern")


def test_strat_1_se_aplica_si_in_sport():
    assert ton.subiect_greu("Fost fotbalist, găsit mort acasă", "sport")
    assert ton.subiect_greu("Antrenorul a murit la 61 de ani", "sport")


def test_rubrica_lipsa_sau_titlu_gol_nu_strica():
    assert ton.subiect_greu("Un șofer a decedat la spital", "")
    assert not ton.subiect_greu("", "")
    assert not ton.subiect_greu(None, None)


@pytest.mark.parametrize("titlu", [
    "Accident rutier între două autoturisme, fără victime spitalizate",
    "Incendiu în Cluj, nicio victimă",
    "Explozie la o fabrică, nu s-au înregistrat morți",
    "Cutremur de 4,2 grade, nu au existat victime",
])
def test_negatia_scoate_cuvantul(titlu):
    assert not ton.subiect_greu(titlu, "local")


def test_negatia_nu_ascunde_o_a_doua_mentiune_reala():
    assert ton.subiect_greu("Fără victime la Cluj, dar un bărbat a murit la Arad", "local")


def test_normalizare_cedila_si_virgula_identice():
    assert ton.normalizeaza("ŞTIRI ţară Înjunghiat") == "stiri tara injunghiat"
    assert ton.normalizeaza("ștefan țară") == "stefan tara"


def test_metafore_si_intensificatori_sunt_numarate():
    assert ton.violenta_in_titlu("Como a spulberat-o pe Lens cu 9-1") == ["spulberat"]
    assert ton.violenta_in_titlu("Incendiu devastator a lăsat o familie fără casă") == ["devastator"]
    assert ton.violenta_in_titlu("Vești șocante din Parlament") == ["socante"]


def test_verbele_literale_nu_sunt_metafore():
    assert ton.violenta_in_titlu("Un incendiu a distrus 50 de tone de fân") == []
    assert ton.violenta_in_titlu("Un bărbat a ucis un om") == []
    assert ton.violenta_in_titlu("") == []
