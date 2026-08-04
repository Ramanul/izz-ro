"""Anunturile oficiale se publica fara teaser: titlul original + link.

Decizie proprietar 2026-08-04, varianta (b) din `specs/sinteza-fara-substanta.md`. Pana acum
anunturile de primarie fara descriere se pierdeau TACUT: `process_official` le punea teaserul
"Detalii pe sursa.", care e in `_BODY_PLACEHOLDERS`, deci `_quality_gate` le respingea.

Intrari/iesiri: un item `official` real (masurat in `data/articles.json`, sursa
`pl_neamt_municipiul_roman`, `description` goala) intra in `process_official`; iese un articol
care TREBUIE sa treaca poarta, sa nu aiba teaser fabricat, si sa se randeze fara `<p>` gol.

Acceptare — cele patru lucruri care se pot strica independent:
1. anuntul oficial fara corp AJUNGE publicat (bug-ul reparat aici);
2. nu i se fabrica niciun teaser pe drum;
3. un item NEoficial fara substanta tot NU se publica (regresie directa la #130 — daca poarta
   ar fi fost slabita global in loc de punctual, testul asta pica);
4. cardul randat nu are gaura: `<p class="summary">` nu se emite deloc, nu se emite gol.
"""
from generator import config, render
from generator.process import process_official
from generator.select import anunt_oficial_fara_corp

LINK = ("https://primariaroman.ro/"
        "festivalul-international-de-folclor-ceahlaul-revine-la-roman/")
TITLU = "Festivalul Internațional de Folclor „Ceahlăul” revine la Roman!"


def _item_oficial(**kw):
    """Itemul asa cum iese din fetch pentru o sursa `pl_`: descriere GOALA, nimic de sintetizat.

    `src_extra` = 0 e pus de `fetch_all` (felia 1) si e chiar capcana: garda de substanta din
    poarta l-ar respinge daca n-ar excepta explicit sursele oficiale.
    """
    base = {"source": "pl_neamt_municipiul_roman", "source_name": "Primăria Municipiul Roman",
            "source_lang": "ro", "original_title": TITLU, "title": TITLU,
            "description": "", "src_extra": 0, "category": "local",
            "url": LINK, "original_link": LINK,
            "published": "2026-08-03T09:00:00+00:00", "model": None}
    base.update(kw)
    return base


def _neoficial(**kw):
    """Itemul din raportul care a declansat felia 1: descriere identica cu titlul, sursa de presa.
    Teaserul e cel pe care AI-ul chiar l-a scris — fluent, diferit de titlu, deci INVIZIBIL
    pentru orice verificare de forma."""
    base = {"source": "digisport", "source_name": "Digi Sport", "model": "B",
            "title": "Gestul neobișnuit al unui portar în minutul 90+3 a uimit asistența",
            "teaser": "Finalul meciului disputat la scorul de 2-2 a fost marcat de un moment "
                      "neobișnuit și spectaculos al portarului.",
            "src_extra": 0, "category": "sport", "processed_by": "gemini",
            "original_link": "https://digisport.ro/x", "published": "2026-08-03T09:00:00+00:00"}
    base.update(kw)
    return base


# --- 1. anuntul ajunge publicat ----------------------------------------------

def test_anunt_oficial_fara_descriere_trece_poarta():
    a = process_official([_item_oficial()])[0]
    assert a["processed_by"] == "official"
    assert a["title"] == TITLU, "titlul original ramane NEATINS"
    assert render._quality_gate(a), "anuntul oficial fara corp trebuie sa se publice"


def test_anunt_oficial_cu_descriere_repetand_titlul_trece_la_fel():
    """A doua forma de „fara corp": feed-ul repeta titlul in `description` (10 cazuri masurate
    in state). Fara asta, poarta le-ar taia pe ruta `body == title`."""
    a = process_official([_item_oficial(description=TITLU)])[0]
    assert anunt_oficial_fara_corp(a)
    assert render._quality_gate(a)


# --- 2. niciun teaser fabricat ------------------------------------------------

def test_anuntul_publicat_nu_are_teaser_fabricat():
    a = process_official([_item_oficial()])[0]
    assert anunt_oficial_fara_corp(a)
    # nimic din textul publicat nu adauga fapte peste titlul sursei
    assert (a.get("teaser") or "").strip() in {"", "Detalii pe sursa.", "Detalii pe surse."}


def test_anunt_oficial_cu_descriere_reala_isi_pastreaza_teaserul():
    """Contra-exemplu: 173 din cele 242 de anunturi oficiale din state CHIAR au descriere.
    Alea nu sunt „fara corp" si nu trebuie sa piarda teaserul."""
    a = process_official([_item_oficial(
        description="Editia a 30-a se desfasoara intre 8 si 10 august in Piata Rosetti.")])[0]
    assert not anunt_oficial_fara_corp(a)
    assert a["teaser"].startswith("Editia a 30-a")
    assert render._quality_gate(a)


# --- 3. regresie #130: neoficialul fara substanta tot NU se publica -----------

def test_item_neoficial_fara_substanta_tot_nu_se_publica():
    assert not render._quality_gate(_neoficial()), \
        "exceptia trebuie sa fie strict pentru `official`, nu o slabire a portii"


def test_poarta_ramane_stricta_pentru_neoficiali_pe_toate_rutele():
    assert not render._quality_gate(_neoficial(teaser="Detalii pe sursa.", src_extra=None))
    assert not render._quality_gate(_neoficial(teaser="", src_extra=None))
    t = "Gestul neobișnuit al unui portar în minutul 90+3 a uimit asistența"
    assert not render._quality_gate(_neoficial(teaser=t, src_extra=None))


def test_fara_corp_nu_se_aplica_altui_processed_by():
    assert not anunt_oficial_fara_corp(_neoficial(teaser="Detalii pe sursa."))
    assert not anunt_oficial_fara_corp(_neoficial(teaser="", processed_by="fallback"))


def test_anuntul_oficial_are_nevoie_de_link_ca_oricare_altul():
    """Fara link, forma „titlu + link" n-are ce oferi cititorului — poarta ramane in picioare."""
    a = process_official([_item_oficial()])[0]
    a["original_link"] = ""
    a["sources"] = []
    assert not render._quality_gate(a)


# --- 4. randarea: fara gaura in card -----------------------------------------

def _card_html(a: dict) -> str:
    """Randeaza macro-ul `card` singur — fara `base.html`, deci fara restul contextului sitului."""
    env = render._env()
    tpl = env.from_string("{% from '_card.html' import card with context %}{{ card(a) }}")
    return tpl.render(a=a, base="")


def _pregatit_pentru_randare(a: dict) -> dict:
    """Exact normalizarea din `render.build`: marcajul + golirea placeholder-ului."""
    a["anunt_fara_corp"] = anunt_oficial_fara_corp(a)
    if a["anunt_fara_corp"]:
        a["teaser"] = ""
    a.setdefault("slug", "festival-folclor-ceahlaul")
    a.setdefault("published_human", "3 august 2026, 09:00")
    return a


def test_cardul_anuntului_nu_emite_paragraf_gol():
    html = _card_html(_pregatit_pentru_randare(process_official([_item_oficial()])[0]))
    assert "summary" not in html, "elementul nu se emite deloc, nu se emite gol"
    assert "<p></p>" not in html
    assert "Detalii pe sursa" not in html, "placeholder-ul nu ajunge niciodata pe pagina"
    assert "reading-time" not in html, "timp de citire pentru un articol fara corp = zgomot"


def test_cardul_anuntului_e_marcat_si_duce_la_sursa():
    html = _card_html(_pregatit_pentru_randare(process_official([_item_oficial()])[0]))
    assert "Anunț oficial" in html, "cititorul trebuie sa vada de ce nu exista rezumat"
    assert TITLU in html
    assert LINK in html and "Primăria Municipiul Roman" in html


def test_cardul_obisnuit_isi_pastreaza_rezumatul():
    """Contra-proba pe acelasi macro: fara marcaj, cardul arata exact ca inainte."""
    a = _pregatit_pentru_randare(_neoficial(source_name="Digi Sport"))
    html = _card_html(a)
    assert 'class="summary"' in html and "reading-time" in html
    assert "Anunț oficial" not in html


def test_placeholderul_ramane_interzis_in_config():
    """Daca cineva scoate placeholder-ul din `_BODY_PLACEHOLDERS`, exceptia de mai sus s-ar
    aplica peste tot — testul asta ii spune de ce nu e o curatenie inofensiva."""
    from generator.select import _BODY_PLACEHOLDERS
    assert "Detalii pe sursa." in _BODY_PLACEHOLDERS
    assert config.MIN_SUBSTANTA_CUVINTE >= 1
