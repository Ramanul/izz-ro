"""Rubrica `ai`, scara geografica din bara si traducerea surselor non-romanesti.

Cerinte owner 2026-08-21:
  (a) rubrica noua pentru stirile de inteligenta artificiala;
  (b) in bara de stiri sa apara EXPLICIT national / regional / judetean / local;
  (c) sursele in alta limba sa fie traduse pe site, nu publicate in original.
"""
import os
import re

from generator import config, process, render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_rubrica_ai_exista_si_are_eticheta_lizibila():
    assert "ai" in config.CATEGORIES
    assert config.CATEGORY_LABELS["ai"] == "Inteligență artificială"


def test_rubrica_ai_intra_automat_in_prompturile_AI():
    cats = "|".join(config.CATEGORIES)
    assert "|ai|" in cats
    for nume, prompt in (("USER_B", process.USER_B), ("USER_BATCH", process.USER_BATCH),
                         ("USER_C", process.USER_C), ("USER_C_BATCH", process.USER_C_BATCH)):
        assert cats in prompt, f"{nume} nu contine lista de categorii cu rubrica noua"


def test_rubrica_ai_poate_fi_goala_fara_sa_pice_qa():
    assert "ai" in config.SEED_CATEGORIES


def test_ai_nu_e_pe_axa_geografica():
    assert "ai" not in config.PINNED_CATEGORIES


def _bara_inline() -> list:
    html = open(os.path.join(ROOT, "templates", "base.html"), encoding="utf-8").read()
    m = re.search(r"categories\[:(\d+)\]", html)
    assert m, "subnav-ul nu mai taie lista de categorii — testul trebuie actualizat"
    return config.CATEGORIES[:int(m.group(1))]


def test_cele_patru_trepte_geografice_sunt_vizibile_in_bara():
    inline = _bara_inline()
    for cat in ("general", "regional", "judetean", "local"):
        assert cat in inline, f"{cat} nu apare in bara, ci sub „mai multe”"


def test_nicio_rubrica_nu_a_fost_impinsa_afara_din_bara():
    vizibile_inainte = {"general", "politic", "economic", "extern", "tech", "sport", "auto"}
    inline = set(_bara_inline())
    lipsa = vizibile_inainte - inline
    assert not lipsa, f"rubrici scoase din bara fara decizie explicita: {sorted(lipsa)}"


def test_treptele_geografice_sunt_numite_explicit():
    assert config.CATEGORY_LABELS["general"] == "Național"
    assert config.CATEGORY_LABELS["regional"] == "Regional"
    assert config.CATEGORY_LABELS["judetean"] == "Județean"
    assert config.CATEGORY_LABELS["local"] == "Local"


def test_scara_geografica_e_in_ordine_descrescatoare():
    idx = [config.CATEGORIES.index(c) for c in ("general", "regional", "judetean", "local")]
    assert idx == sorted(idx)


def test_slugul_general_nu_s_a_schimbat():
    assert "general" in config.CATEGORIES and "national" not in config.CATEGORIES


def _item(lang):
    return {"source_lang": lang, "original_title": "Inter wins", "description": "x",
            "title": "", "teaser": ""}


def test_fara_provider_o_sursa_in_alta_limba_nu_se_publica_bruta():
    for lang in ("en", "it", "de", "fr"):
        out = process.process_single(_item(lang), None)
        assert out.get("skip") is True, f"{lang} nu a fost sarit"


def test_fara_provider_sursele_romanesti_trec_ca_pana_acum():
    out = process.process_single(_item("ro"), None)
    assert not out.get("skip")
    assert out["title"] == "Inter wins"


def test_sursa_fara_lang_e_tratata_ca_romaneasca():
    out = process.process_single({"original_title": "Ceva", "description": "x",
                                  "title": "", "teaser": ""}, None)
    assert not out.get("skip")


def test_toate_prompturile_cer_explicit_romana():
    for nume, prompt in (("USER_B", process.USER_B), ("USER_BATCH", process.USER_BATCH),
                         ("USER_C", process.USER_C), ("USER_C_BATCH", process.USER_C_BATCH)):
        assert re.search(r"[Ii]N ROMANA|in romana", prompt), f"{nume} nu cere romana"


def test_sursele_straine_isi_declara_limba():
    straine = {"bbc_europe", "guardian_eu", "politico_eu", "dw_europe",
               "fcinter1908", "gazzetta", "xda", "thenewstack", "kitguru", "marktechpost"}
    for cheie in straine & set(config.SOURCES):
        assert config.SOURCES[cheie].get("lang"), cheie


def test_articolele_mutate_pe_ai_au_301_de_pe_url_ul_vechi():
    """Doar redirecturile care muta articole in rubrica AI sunt verificate aici.

    `redirects_migrare.tsv` este registru comun si poate contine legitim si migrari pentru
    alte zone, precum România Utilă. Testul vechi trata fiecare linie ca pe un redirect AI
    si astfel a inceput sa pice imediat ce registrul a primit prima migrare ne-AI.
    """
    linii = render._redirects_migrare()
    ai_linii = [ln for ln in linii.strip().split("\n") if ln.split(" ")[1].startswith("/ai/")]
    assert ai_linii, "nu s-a generat niciun redirect catre rubrica AI"
    for ln in ai_linii:
        vechi, nou, cod = ln.split(" ")
        assert cod == "301"
        assert nou.startswith("/ai/")
        assert not vechi.startswith("/ai/"), "redirect catre el insusi"


def test_redirecturile_de_migrare_intra_in_fisierul_final():
    tsv = os.path.join(ROOT, "data", "redirects_migrare.tsv")
    assert os.path.exists(tsv), "migrarea nu si-a lasat urma pe disc"
    with open(tsv, encoding="utf-8") as f:
        perechi = [ln for ln in f if ln.strip()]
    assert len(render._redirects_migrare().strip().split("\n")) == len(perechi)


def test_fara_fisier_de_migrare_nu_se_arunca():
    """Pe o clona fara migrari, lipsa fisierului nu e eroare."""
