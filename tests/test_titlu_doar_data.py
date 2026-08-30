"""§7 „fara output stricat": un titlu care e DOAR o data calendaristica nu se publica.

DE CE EXISTA (2026-08-30, raportat de proprietar pe site-ul live). Doua iteme erau publicate cu
titlul format exclusiv dintr-o data — `27.08.2026` si `17.08.2026`, ambele CJ Giurgiu, categoria
`judetean`, slug-uri `27-08-2026` / `17-08-2026`. Sursele oficiale locale ocolesc AI-ul
(`specs/local-official-no-ai.md`), deci titlul din feed ajungea pe site fara nicio bara.

Garda e INGUSTA dinadins: prinde titlul care e doar data, nu incearca sa judece calitatea in
general. Un titlu cu eticheta („Anunt 27.08.2026") ramane valid — spune ceva.
"""
from generator.util import fara_titluri_data, titlu_e_doar_o_data


def test_prinde_exact_titlurile_gasite_pe_site():
    assert titlu_e_doar_o_data("27.08.2026")
    assert titlu_e_doar_o_data("17.08.2026")


def test_prinde_si_celelalte_forme_de_data():
    for t in ("2026-08-27", "27-08-2026", "27/08/2026", "nr. 12 27.08.2026"):
        assert titlu_e_doar_o_data(t), t


def test_nu_atinge_un_titlu_care_spune_ceva():
    """Intrarea stricata dinadins in cealalta directie: garda care ar taia astea e mai rea."""
    for t in ("Anunt 27.08.2026",
              "Publicatii casatorii din 27.08.2026",
              "Instiintare trageri 15-18.09.2026",
              "Sedinta extraordinara de indata",
              ""):
        assert not titlu_e_doar_o_data(t), t


def test_curata_si_ce_e_deja_in_stare_nu_doar_itemele_noi():
    """Diferenta care conteaza. Prima versiune filtra doar `processed_new`, deci ar fi oprit
    urmatoarele titluri-data si le-ar fi lasat pe cele DEJA publicate sa se randeze pana la
    expirarea TTL-ului — adica exact cele doua pagini raportate ar fi ramas pe site."""
    stare = [
        {"url": "https://x/1", "title": "27.08.2026"},          # deja publicat, stricat
        {"url": "https://x/2", "title": "Sedinta de indata"},    # deja publicat, valid
        {"url": "https://x/3", "title": "17.08.2026"},           # proaspat, stricat
    ]
    pastrate, sarite = fara_titluri_data(stare)
    assert [a["url"] for a in sarite] == ["https://x/1", "https://x/3"]
    assert [a["url"] for a in pastrate] == ["https://x/2"]


def test_nu_arunca_nimic_cand_starea_e_curata():
    stare = [{"url": "https://x/1", "title": "Anunt 27.08.2026"}]
    pastrate, sarite = fara_titluri_data(stare)
    assert sarite == [] and pastrate == stare
