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


# ---------------------------------------------------------------- rubrica AI ---
def test_rubrica_ai_exista_si_are_eticheta_lizibila():
    assert "ai" in config.CATEGORIES
    # slugul e scurt, dar eticheta afisata nu are voie sa fie doua litere: cititorul
    # nu trebuie sa ghiceasca ce inseamna „AI" intr-o bara de navigare.
    assert config.CATEGORY_LABELS["ai"] == "Inteligență artificială"


def test_rubrica_ai_intra_automat_in_prompturile_AI():
    """`_CATS` se construieste din config.CATEGORIES — o rubrica noua trebuie sa ajunga
    in lista din care modelul alege, altfel n-ar clasifica nimic acolo niciodata."""
    cats = "|".join(config.CATEGORIES)
    assert "|ai|" in cats, "„ai” nu e inconjurat de alte categorii — lista s-a schimbat"
    for nume, prompt in (("USER_B", process.USER_B), ("USER_BATCH", process.USER_BATCH),
                         ("USER_C", process.USER_C), ("USER_C_BATCH", process.USER_C_BATCH)):
        assert cats in prompt, f"{nume} nu contine lista de categorii cu rubrica noua"


def test_rubrica_ai_poate_fi_goala_fara_sa_pice_qa():
    """E nou-adaugata: la prima rulare poate avea 0 articole din surse proprii."""
    assert "ai" in config.SEED_CATEGORIES


def test_ai_nu_e_pe_axa_geografica():
    """`ai` e o rubrica de TEMA. Daca ar fi pinned, `_resolve_category` ar refuza-o ca
    rubrica finala pentru un articol fara nume de loc in text."""
    assert "ai" not in config.PINNED_CATEGORIES


# ------------------------------------------------------ scara geografica in bara ---
def _bara_inline() -> list:
    """Rubricile afisate INLINE in subnav, exact cum le taie templates/base.html."""
    html = open(os.path.join(ROOT, "templates", "base.html"), encoding="utf-8").read()
    m = re.search(r"categories\[:(\d+)\]", html)
    assert m, "subnav-ul nu mai taie lista de categorii — testul trebuie actualizat"
    return config.CATEGORIES[:int(m.group(1))]


def test_cele_patru_trepte_geografice_sunt_vizibile_in_bara():
    """Regresie directa la cerinta owner: stateau pe pozitiile 12-14, adica in dropdown.
    Comentariul de la `.subnav` din static/styles.css masurase deja ca „exact categoriile
    geografice ramaneau nedescoperite" pe telefon."""
    inline = _bara_inline()
    for cat in ("general", "regional", "judetean", "local"):
        assert cat in inline, f"{cat} nu apare in bara, ci sub „mai multe”"


def test_nicio_rubrica_nu_a_fost_impinsa_afara_din_bara():
    """Regresie prinsa la review pe PR #201, nu de mine.

    Reordonarea a bagat 4 trepte geografice + `ai` in fata, dar cutoff-ul a crescut doar
    7 -> 9. Rezultat: `tech` si `auto` — vizibile inainte, ~90 de articole fiecare — au
    cazut tacut in dropdown. Nimeni n-a cerut asta, si nu scria nicaieri in PR.
    Setul vizibil de dinainte e un contract cu cititorul: se poate ADAUGA la el, nu se
    scoate din el fara o decizie explicita a owner-ului."""
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
    """National -> Regional -> Judetean -> Local. Ordinea E informatia: o scara amestecata
    nu se citeste ca o scara."""
    idx = [config.CATEGORIES.index(c) for c in ("general", "regional", "judetean", "local")]
    assert idx == sorted(idx)


def test_slugul_general_nu_s_a_schimbat():
    """Eticheta s-a schimbat, slugul NU: /general/ e indexat. Regula din CATEGORY_LABELS."""
    assert "general" in config.CATEGORIES and "national" not in config.CATEGORIES


# ------------------------------------------------------------------ traducere ---
def _item(lang):
    return {"source_lang": lang, "original_title": "Inter wins", "description": "x",
            "title": "", "teaser": ""}


def test_fara_provider_o_sursa_in_alta_limba_nu_se_publica_bruta():
    """Fara cheie AI nu exista cine sa traduca. Garda era cablata pe „en", deci o sursa
    italiana (fcinter1908, gazzetta) ar fi ajuns pe site in original."""
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
    """USER_BATCH avea instructiunea; celelalte trei nu. Un item care ajunge pe calea B
    ne-batch, sau orice sinteza C dintr-un cluster cu surse straine, ramanea netradus."""
    for nume, prompt in (("USER_B", process.USER_B), ("USER_BATCH", process.USER_BATCH),
                         ("USER_C", process.USER_C), ("USER_C_BATCH", process.USER_C_BATCH)):
        assert re.search(r"[Ii]N ROMANA|in romana", prompt), f"{nume} nu cere romana"


def test_sursele_straine_isi_declara_limba():
    """Fara `lang`, `fetch` pune „ro" implicit si garda de mai sus nu se declanseaza."""
    straine = {"bbc_europe", "guardian_eu", "politico_eu", "dw_europe",
               "fcinter1908", "gazzetta", "xda", "thenewstack", "kitguru", "marktechpost"}
    for cheie in straine & set(config.SOURCES):
        assert config.SOURCES[cheie].get("lang"), cheie


# ------------------------------------------------------------------ redirecturi ---
def test_articolele_mutate_pe_ai_au_301_de_pe_url_ul_vechi():
    """Redirecturile sunt un registru comun: aici verificam numai migrarile catre AI.
    Migrarile legitime catre alte zone, inclusiv România Utilă, nu apartin acestui contract."""
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
    real = render._MIGRARE_TSV
    try:
        render._MIGRARE_TSV = os.path.join(ROOT, "data", "nu-exista-nicaieri.tsv")
        assert render._redirects_migrare() == ""
    finally:
        render._MIGRARE_TSV = real


def test_o_linie_tsv_malformata_nu_dispare_in_tacere(tmp_path, capsys):
    """Un rand sarit = un articol fara 301 = un URL indexat care da 404. Trebuie sa se vada."""
    f = tmp_path / "stricat.tsv"
    f.write_text("/tech/bun/\t/ai/bun/\nrand-fara-taburi\n/tech/x/\tfara-slash\n",
                 encoding="utf-8")
    real = render._MIGRARE_TSV
    try:
        render._MIGRARE_TSV = str(f)
        out = render._redirects_migrare()
    finally:
        render._MIGRARE_TSV = real
    assert out.strip() == "/tech/bun/ /ai/bun/ 301"
    err = capsys.readouterr().err
    assert "2 linii ignorate" in err
