"""Rezumatul zilnic de revizuire — detectoarele, cu perechea negativa pentru fiecare.

Proprietatea cea mai importanta e testata explicit: o zi FARA exceptii produce un rezumat
scurt. Daca se pierde, mecanismul esueaza exact ca rutina pe care o inlocuieste.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("revizuire_zilnica", ROOT / "tools" / "revizuire_zilnica.py")
rz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rz)


def _a(sursa, zi, model="B", titlu="Consiliul local a aprobat bugetul"):
    return {"source": sursa, "published": f"{zi}T08:00:00", "model": model,
            "title": titlu, "source_lang": "ro", "original_link": f"https://{sursa}.ro/x"}


# --- surse noi -----------------------------------------------------------------------

def test_o_sursa_aparuta_azi_prima_oara_e_semnalata():
    arts = [_a("veche", "2026-08-01"), _a("veche", "2026-08-02"), _a("noua", "2026-08-02")]
    assert rz.surse_noi(arts, "2026-08-02") == ["noua"]


def test_o_sursa_cu_istoric_NU_e_semnalata_ca_noua():
    """Negativul: fara el, garda ar semnala toate sursele in fiecare zi si ar fi ignorata."""
    arts = [_a("veche", "2026-08-01"), _a("veche", "2026-08-02")]
    assert rz.surse_noi(arts, "2026-08-02") == []


# --- volum neobisnuit ----------------------------------------------------------------

def test_un_salt_peste_mediana_proprie_e_semnalat():
    arts = ([_a("s", f"2026-08-0{z}") for z in (1, 2, 3)]
            + [_a("s", "2026-08-04") for _ in range(9)])
    gasite = rz.volum_neobisnuit(arts, "2026-08-04")
    assert gasite and gasite[0][0] == "s" and gasite[0][1] == 9 and gasite[0][2] == 1.0


def test_o_sursa_mare_care_publica_normal_NU_e_semnalata():
    """Comparatia e cu mediana SURSEI, nu cu un prag global: altfel sursele mari ar fi
    semnalate in fiecare zi, iar anomalia reala s-ar pierde in zgomot."""
    arts = [_a("mare", f"2026-08-0{z}") for z in (1, 2, 3, 4) for _ in range(30)]
    assert rz.volum_neobisnuit(arts, "2026-08-04") == []


def test_fara_istoric_suficient_nu_se_pronunta():
    """O sursa cu doua zile de istoric n-are mediana care sa insemne ceva."""
    arts = [_a("s", "2026-08-03")] + [_a("s", "2026-08-04") for _ in range(9)]
    assert rz.volum_neobisnuit(arts, "2026-08-04") == []


# --- titluri care au trecut de garda -------------------------------------------------

def test_un_titlu_ostil_ajuns_in_stare_e_semnalat():
    arts = [_a("pl_x", "2026-08-04", titlu="Hacked by Chinafans")]
    gasite = rz.titluri_suspecte(arts, "2026-08-04")
    assert gasite and gasite[0][1] == "Hacked by Chinafans"


def test_un_titlu_romanesc_normal_nu_e_semnalat():
    assert rz.titluri_suspecte([_a("pl_x", "2026-08-04")], "2026-08-04") == []


# --- forma rezumatului ---------------------------------------------------------------

def test_o_zi_fara_exceptii_incape_in_cateva_randuri():
    """PROPRIETATEA CARE TINE MECANISMUL VIU. Daca se pierde, rezumatul nu mai e citit,
    si atunci esecul lui `REVIEW.md` s-a mutat doar in alt fisier."""
    arts = [_a("veche", "2026-08-01"), _a("veche", "2026-08-02"), _a("veche", "2026-08-03"),
            _a("veche", "2026-08-04")]
    text = rz.rezumat(arts, "2026-08-04")
    assert "Nimic de facut" in text
    assert len(text.splitlines()) <= 6, text


def test_o_zi_cu_exceptii_spune_unde_se_actioneaza():
    arts = [_a("veche", "2026-08-01"), _a("veche", "2026-08-02"), _a("noua", "2026-08-02")]
    text = rz.rezumat(arts, "2026-08-02")
    assert "Surse noi" in text and "moderation.yaml" in text
    assert "Nimic de facut" not in text


def test_rezumatul_numara_sintezele_C_separat():
    arts = [_a("s", "2026-08-04"), _a("s", "2026-08-04", model="C")]
    assert "**1 sinteze C**" in rz.rezumat(arts, "2026-08-04")


def test_argumentul_gol_cade_pe_ziua_implicita(monkeypatch, capsys):
    """Workflow-ul trimite `"$ZI"` citat, iar la rularile programate e gol. Fara verificarea
    asta ziua ar fi sirul vid si rezumatul ar iesi mereu „0 articole" — esec TACUT."""
    monkeypatch.setattr(rz.Path, "read_text", lambda *a, **k: "[]")
    rz.main(["posteaza", ""])
    assert "Revizuire 20" in capsys.readouterr().out


# --- postarea pe issue: URL construit din bucati validate, nu din interpolare ----------

_spec_p = importlib.util.spec_from_file_location("posteaza_rezumat", ROOT / "tools" / "posteaza_rezumat.py")
pr = importlib.util.module_from_spec(_spec_p)
_spec_p.loader.exec_module(pr)


def test_url_ul_de_comentarii_e_construit_corect():
    assert pr.url_comentarii("Ramanul/izz-ro", "233") == \
        "https://api.github.com/repos/Ramanul/izz-ro/issues/233/comments"


@pytest.mark.parametrize("depozit,issue", [
    ("fara-slash", "233"),
    ("a/b/c", "233"),
    ("", "233"),
    ("Ramanul/izz-ro", "233; rm -rf /"),
    ("Ramanul/izz-ro", "../../altceva"),
])
def test_bucatile_stricate_opresc_apelul(depozit, issue):
    """Negativul: tiparul din #177 a fost interpolarea in bash. Aici nu se interpoleaza
    nimic, dar validarea exista ca sa nu se poata reintroduce prin alta usa."""
    with pytest.raises(ValueError):
        pr.url_comentarii(depozit, issue)
