"""Parser de sitemap Google News (surse fara RSS, ex. piataauto.md). Verificat pe
fixture XML realist — sandbox-ul n-are internet, dar parserul e Python pur.

Regresie (iulie 2026): sursa raspundea 200 cu <url>-uri valide, dar toate intrarile
erau sarite in tacere -> 0 articole SI 0 erori, deci nu aparea nici in lista surselor
moarte. Un esec tacut e mai rau decat unul zgomotos: degradeaza nevazut."""
from generator import config
from generator.fetch import _parse_sitemap_news

SRC = {"name": "Piata Auto MD", "category": "auto"}

NS = ('xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
      'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"')


def _entry(loc: str, title: str | None = "Titlu", date: str = "2026-07-24") -> str:
    news = "" if title is None else (
        f"<news:news><news:title>{title}</news:title>"
        f"<news:publication_date>{date}</news:publication_date></news:news>")
    return f"<url><loc>{loc}</loc>{news}</url>"


def _doc(entries: str) -> bytes:
    return f'<?xml version="1.0"?><urlset {NS}>{entries}</urlset>'.encode()


def test_parses_valid_entries():
    raw = _doc(_entry("https://piataauto.md/a", "Dacia lansează un model nou")
               + _entry("https://piataauto.md/b", "Test drive electric"))
    items, err = _parse_sitemap_news(raw, "piataauto", SRC)
    assert err is None
    assert [i["title"] for i in items] == ["Dacia lansează un model nou", "Test drive electric"]
    assert items[0]["category"] == "auto"
    assert items[0]["published"].startswith("2026-07-24")


def test_entries_without_title_are_reported_not_silent():
    """Structura schimbata (fara news:title) -> eroare explicita, nu lista goala tacuta."""
    raw = _doc("".join(_entry(f"https://piataauto.md/{i}", None) for i in range(3)))
    items, err = _parse_sitemap_news(raw, "piataauto", SRC)
    assert items == []
    assert err is not None
    assert "0 utilizabile" in err and "3" in err


def test_cap_applies_after_filtering():
    """Plafonul MAX_PER_SOURCE se aplica pe intrarile BUNE, nu pe felia bruta."""
    bad = "".join(_entry(f"https://piataauto.md/x{i}", None) for i in range(config.MAX_PER_SOURCE))
    good = "".join(_entry(f"https://piataauto.md/g{i}", f"Stire {i}") for i in range(3))
    items, err = _parse_sitemap_news(_doc(bad + good), "piataauto", SRC)
    assert err is None
    assert len(items) == 3


def test_cap_is_enforced():
    good = "".join(_entry(f"https://piataauto.md/g{i}", f"Stire {i}") for i in range(20))
    items, _ = _parse_sitemap_news(_doc(good), "piataauto", SRC)
    assert len(items) == config.MAX_PER_SOURCE


def test_empty_sitemap_reports_error():
    items, err = _parse_sitemap_news(_doc(""), "piataauto", SRC)
    assert items == [] and "0 intrari" in err


def test_invalid_xml_reports_error():
    items, err = _parse_sitemap_news(b"<nu-e-xml", "piataauto", SRC)
    assert items == [] and "XML invalid" in err


# --- octeti de control ilegali in XML 1.0 (garda preventiva, 2026-08-06) ---
# NU repara un defect observat: o descarcare a fiecareia din cele doua surse `sitemap_news`
# a dat 0 octeti de control. Un esantion nu poate dovedi absenta, iar consecinta unui singur
# `\x0c` e ca `ET.fromstring` respinge tot documentul si sursa VIE apare in `dead`.

def test_octet_de_control_nu_mai_omoara_tot_documentul():
    raw = _doc(_entry("https://piataauto.md/a", "Titlu\x0ccu control")
               + _entry("https://piataauto.md/b", "Al doilea"))
    items, err = _parse_sitemap_news(raw, "piataauto", SRC)
    assert err is None, f"documentul ar fi trebuit sa treaca, dar: {err}"
    # Octetul dispare; restul textului ramane lipit, nu se pierde niciun cuvant.
    assert [i["title"] for i in items] == ["Titlucu control", "Al doilea"]


def test_control_in_afara_textului_nu_pierde_intrari():
    """Un `\x1f` intre taguri (unde nu e nici macar text) rupea la fel intregul sitemap."""
    raw = _doc(_entry("https://piataauto.md/a") + "\x1f" + _entry("https://piataauto.md/b"))
    items, err = _parse_sitemap_news(raw, "piataauto", SRC)
    assert err is None and len(items) == 2


def test_tab_newline_cr_raman_neatinse():
    """#x9/#xA/#xD sunt LEGALE in XML 1.0 — filtrarea nu are voie sa le scoata.

    Se verifica pe `_curata_control` direct, nu pe titlul parsat: `clean_html` normalizeaza
    oricum spatiile, deci un test pe iesirea finala ar trece si daca filtrarea le-ar manca
    pe toate trei — adica exact un test care nu poate distinge.
    """
    from generator.fetch import _curata_control
    assert _curata_control(b"a\tb\nc\rd") == b"a\tb\nc\rd"
    assert _curata_control(b"a\x0bb\x0cc") == b"abc"


def test_diacriticele_utf8_supravietuiesc_filtrarii():
    """Filtrarea lucreaza pe octeti: continuarile UTF-8 (>= #x80) nu au voie sa fie atinse."""
    from generator.fetch import _curata_control
    text = "Timișoara — știri".encode("utf-8")
    assert _curata_control(text).decode("utf-8") == "Timișoara — știri"


def test_documentul_utf16_ramane_neatins():
    """In UTF-16 octetul #x00 face parte din fiecare caracter ASCII: a-l filtra ar distruge
    un document VALID. Se recunoaste dupa BOM si se lasa in pace."""
    from generator.fetch import _curata_control
    doc = ('<?xml version="1.0" encoding="UTF-16"?><urlset/>').encode("utf-16")
    assert doc[:2] in (b"\xff\xfe", b"\xfe\xff")
    assert _curata_control(doc) == doc


def test_xml_chiar_stricat_ramane_eroare():
    """Filtrarea nu are voie sa mascheze un document genuin invalid."""
    items, err = _parse_sitemap_news(b"<urlset><url>", "piataauto", SRC)
    assert items == [] and err and "XML invalid" in err


# --- intarire XML: defusedxml pe calea de sitemap (2026-08-06) ---
# Masurat INAINTE de schimbare, pe stack-ul de atunci (Python 3.11.15, expat 2.7.4): billion
# laughs pica deja cu `limit on input amplification factor breached`, iar entitatea externa
# `file:///` pica cu `undefined entity`. Deci `defusedxml` NU repara o gaura deschisa — el scoate
# apararea din mainile lui expat, care o are doar de la 2.4.0 si o poate pierde pe alt runner.
#
# Ce chiar era un defect: `DefusedXmlException` nu e subclasa de `ParseError` (mro-ul ei trece
# prin ValueError), deci `except ParseError` singur ar fi lasat exceptia sa iasa din functie si
# sa omoare ciclul de fetch — un mod de esec NOU, introdus chiar de intarire. Testele de mai jos
# apara exact granita aia: se verifica ca functia INTOARCE, nu ca arunca frumos.

def _bomba_entitati() -> bytes:
    ent = "".join('<!ENTITY e%d "%s">' % (i, "&e%d;" % (i - 1) * 10) for i in range(1, 8))
    return ('<?xml version="1.0"?><!DOCTYPE urlset [<!ENTITY e0 "AAAAAAAAAA">%s]>'
            '<urlset %s><url><loc>&e7;</loc></url></urlset>' % (ent, NS)).encode()


def test_bomba_de_entitati_nu_omoara_ciclul_de_fetch():
    """Fara `DefusedXmlException` in `except`, apelul asta ARUNCA in loc sa intoarca."""
    items, err = _parse_sitemap_news(_bomba_entitati(), "piataauto", SRC)
    assert items == []
    assert err and "piataauto" in err


def test_documentul_respins_de_politica_se_distinge_de_cel_stricat():
    """Doua diagnostice diferite: unul se repara la sursa, celalalt e regula noastra.
    Daca ambele scriu „XML invalid", cine citeste raportul de surse nu poate sti care e care."""
    _, err_respins = _parse_sitemap_news(_bomba_entitati(), "piataauto", SRC)
    _, err_stricat = _parse_sitemap_news(b"<nu-e-xml", "piataauto", SRC)
    assert "respins" in err_respins and "EntitiesForbidden" in err_respins
    assert "invalid" in err_stricat and "respins" not in err_stricat


def test_sitemapul_valid_trece_neatins_dupa_intarire():
    """Control pozitiv: intarirea nu are voie sa strice cazul normal."""
    items, err = _parse_sitemap_news(_doc(_entry("https://x.md/a", "Titlu")), "piataauto", SRC)
    assert err is None and len(items) == 1
