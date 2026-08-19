from __future__ import annotations

from tools import title_quality_audit


def _official(title: str, source_name: str = "Primăria exemplu") -> dict:
    return {
        "id": "test-1",
        "url": "https://exemplu.ro/anunt",
        "processed_by": "official",
        "source_name": source_name,
        "title": title,
    }


def test_audit_trece_pentru_titlu_oficial_lung_care_este_afisat_scurt():
    title = "Anunț nr. 7505 privind " + "servicii administrative și tehnice " * 12

    result = title_quality_audit.audit([_official(title)])

    assert result["contract"]["status"] == "pass"
    assert result["raw_titles_over_limit"] == 1
    assert result["display_titles_over_limit"] == 0
    assert result["titles_changed"] == 1
    assert result["longest_display_titles"][0]["display"].endswith("…")


def test_audit_semnaleaza_orice_titlu_afisat_peste_limita(monkeypatch):
    article = _official("Anunț administrativ " + "lung " * 30)
    monkeypatch.setattr(title_quality_audit, "titlu_afisare", lambda _: "x" * 111)

    result = title_quality_audit.audit([article])

    assert result["contract"]["status"] == "fail"
    assert result["display_titles_over_limit"] == 1
    assert result["violations"][0]["display_characters"] == 111


def test_regula_universala_scurteaza_si_denumirea_foarte_lunga_a_emitentului():
    title = "Concurs de recrutare " + "pentru funcții administrative " * 8
    source_name = "Instituția publică cu denumire administrativă neobișnuit de lungă " * 3

    display = title_quality_audit.titlu_afisare(_official(title, source_name))

    assert len(display) <= 110
    assert display.endswith("…")


def test_filtrele_rapide_grupeaza_anunturile_dupa_intentia_de_cautare():
    from generator.select import filtru_cautare_rapida

    classify = filtru_cautare_rapida

    assert classify(_official("Concurs pentru ocuparea unui post vacant " + "detalii " * 15)) == "concursuri"
    assert classify(_official("Proiect de hotărâre nr. 15 privind modernizarea pieței " + "detalii " * 12)) == "hotarari"
    assert classify(_official("Anunț privind achiziția de echipamente IT " + "detalii " * 15)) == "achizitii"
    assert classify(_official("Anunț instituțional privind programul de lucru " + "detalii " * 15)) == "oficiale"
    assert classify({"processed_by": "fallback", "title": "Concurs local"}) == ""
