"""Corpul articolului se citeste si din `<content:encoded>`, nu doar din `<description>`.

Spec: `specs/fetch-content-encoded.md`. Defectul reparat aici: `feedparser` pune
`<content:encoded>` in `entry.content[0].value`, iar `_fetch_one` citea doar
`summary`/`description` — deci la sursele care trimit corpul acolo itemul iesea fara substanta si
`_quality_gate` il respingea tacut. Masurat 2026-08-04 pe feeduri live: 9 din 12 surse dintre cele
care produceau anunturi „fara corp" trimit un corp real in `content:encoded`.

Testele lucreaza pe `feedparser.parse()` peste XML real, nu pe dicturi construite de mana: exact
maparea `content:encoded -> entry.content[0].value` e lucrul care se putea schimba sub noi, iar un
fake ar fi afirmat-o in loc s-o verifice.
"""
import feedparser

from generator.fetch import _entry_body

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel><title>Primaria X</title><link>https://ex.ro</link><description>feed</description>
    <item>
      <title>{title}</title><link>https://ex.ro/a/</link>
      {description}
      {content}
    </item>
  </channel>
</rss>"""


def _entry(title="Anunt public", description="", content=""):
    xml = RSS.format(
        title=title,
        description=f"<description>{description}</description>" if description else "",
        content=f"<content:encoded><![CDATA[{content}]]></content:encoded>" if content else "",
    )
    return feedparser.parse(xml).entries[0]


def test_content_encoded_e_luat_cand_description_lipseste():
    """Forma masurata la `pl_neamt_municipiul_roman`: description gol, content de ~1700 caractere."""
    corp = ("Festivalul se desfasoara in perioada 8-10 august in Piata Roman Voda, cu ansambluri "
            "din Romania, Republica Moldova si Ucraina. Intrarea este libera.")
    e = _entry(description="", content=f"<p>{corp}</p>")
    assert _entry_body(e) == corp


def test_content_encoded_castiga_cand_e_mai_bogat_decat_description():
    """Cazul general: feedul pune un rezumat de o linie in description si articolul in content."""
    e = _entry(description="Anunt de la primarie.",
               content="<p>Consiliul local a aprobat bugetul rectificat pentru anul in curs, "
                       "cu 2,1 milioane lei alocati reabilitarii scolii gimnaziale.</p>")
    corp = _entry_body(e)
    assert corp.startswith("Consiliul local a aprobat")
    assert "Anunt de la primarie." not in corp


def test_description_ramane_cand_content_curata_mai_scurt():
    """Regresia inversa, si motivul pentru care comparatia se face DUPA `clean_html`.

    `content` e mai lung ca HTML brut (89 de caractere de markup), dar curatat ramane un cuvant.
    O comparatie pe brut ar alege varianta saraca si ar SCADEA substanta fata de azi.
    """
    bogat = "Sedinta ordinara a consiliului local are loc joi, 7 august, ora 16:00, in sala mare."
    e = _entry(description=bogat,
               content='<div class="wrap"><span class="ico"></span><a href="#" rel="tag">Stiri</a></div>')
    assert _entry_body(e) == bogat


def test_feed_fara_content_se_comporta_ca_inainte():
    """Majoritatea surselor: nu exista `content:encoded`, deci nimic nu se schimba pentru ele."""
    e = _entry(description="Text simplu din description.")
    assert not e.get("content")
    assert _entry_body(e) == "Text simplu din description."


def test_entry_gol_da_string_gol_nu_exceptie():
    """`max()` pe o lista goala arunca — de aia exista `default`. Un feed fara nimic nu e o eroare."""
    e = _entry(description="", content="")
    assert _entry_body(e) == ""


def test_html_si_entitatile_sunt_curatate_din_content():
    """`content:encoded` e HTML aproape mereu; ce ajunge in `description` trebuie sa fie text."""
    e = _entry(content="<p>Primaria &#8222;Roman&#8221; anunta&nbsp;licitatia.</p><script>x()</script>")
    corp = _entry_body(e)
    assert "<p>" not in corp and "&#8222;" not in corp and "&nbsp;" not in corp
    assert "Primaria" in corp and "licitatia" in corp
