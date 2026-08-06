"""Validitatea feedului RSS 2.0 — `pubDate` per item si `atom:link rel=self` in channel.

Feedul n-avea niciun test. Ce lipsea, masurat pe `_feed_xml` inainte de fix: zero `<pubDate>`,
deci un cititor RSS nu putea nici sa dateze, nici sa ordoneze intrarile (le arata in ordinea
din fisier, fara vechime), si zero `atom:link rel=self`, pe care validatoarele o cer si
agregatoarele o folosesc ca sa recunoasca acelasi flux servit de pe doua origini — iar noi
chiar servim de pe doua (Cloudflare Pages + mirror GitHub Pages).
"""
import locale
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import pytest

from generator import render

ATOM = "{http://www.w3.org/2005/Atom}link"


def _art(slug: str, published: str, cat: str = "extern") -> dict:
    return {"title": f"Titlu {slug}", "slug": slug, "category": cat,
            "published": published, "teaser": "corp", "model": "B",
            "url": f"https://exemplu.ro/{slug}"}


def _channel(xml: str):
    return ET.fromstring(xml).find("channel")


def test_fiecare_item_are_pubdate_parsabil_si_corect():
    arts = [_art("a", "2026-08-06T07:30:00+00:00"), _art("b", "2026-07-01T23:15:00+00:00")]
    ch = _channel(render._feed_xml(arts, "T", "https://izz.ro", "D"))
    items = ch.findall("item")
    assert len(items) == 2
    for a, item in zip(arts, items):
        raw = item.findtext("pubDate")
        assert raw, f"item fara pubDate: {item.findtext('title')}"
        # RFC 2822 real, nu un sir care seamana: se parseaza inapoi si trebuie sa dea
        # exact momentul din stare.
        assert parsedate_to_datetime(raw) == datetime.fromisoformat(a["published"])


def test_pubdate_nu_depinde_de_locale():
    """Ziua si luna raman in engleza chiar SUB un locale non-englez.

    Prima varianta a testului doar verifica apartenenta la setul englezesc, sub locale-ul
    curent — si ar fi trecut identic cu `strftime("%a, %d %b")`, fiindca Python porneste pe
    locale-ul "C". Adica un test care nu putea distinge cele doua implementari, deci nu era
    dovada pentru nimic. Aici se SCHIMBA efectiv LC_TIME: sub `strftime` ar iesi „Joi"/„aug.",
    sub `format_datetime` iese „Thu"/„Aug".

    Skip explicit daca niciun locale non-englez nu e instalat (runnerele minimale au doar C):
    un skip vizibil e onest, o trecere care nu masoara nimic nu e. `finally` restaureaza —
    altfel, cu ordinea aleatoare a suitei, testul ar contamina pe oricine ruleaza dupa el.
    """
    anterior = locale.setlocale(locale.LC_TIME)
    for candidat in ("ro_RO.UTF-8", "Romanian_Romania.1250", "ro_RO",
                     "de_DE.UTF-8", "German_Germany.1252", "fr_FR.UTF-8"):
        try:
            locale.setlocale(locale.LC_TIME, candidat)
        except locale.Error:
            continue
        try:
            raw = render._rfc2822("2026-08-06T07:30:00+00:00")
        finally:
            locale.setlocale(locale.LC_TIME, anterior)
        zi, luna = raw.split()[0].rstrip(","), raw.split()[2]
        assert zi == "Thu", f"sub locale {candidat}: {raw!r} — ziua s-a tradus"
        assert luna == "Aug", f"sub locale {candidat}: {raw!r} — luna s-a tradus"
        return
    pytest.skip("niciun locale non-englez instalat: testul nu poate distinge nimic aici")


def test_data_naiva_e_tratata_ca_utc():
    """`published` fara fus (stare veche) nu trebuie sa alunece cu ore intregi."""
    assert parsedate_to_datetime(render._rfc2822("2026-08-06T07:30:00")) == \
        datetime(2026, 8, 6, 7, 30, tzinfo=timezone.utc)


def test_data_neparsabila_omite_pubdate_in_loc_sa_inventeze(caplog):
    """O data stricata NU devine "acum": ar urca articolul in capul oricarui cititor care
    sorteaza pe pubDate. Se omite — si se logheaza, altfel pierderea e invizibila."""
    ch = _channel(render._feed_xml([_art("x", "maine-cândva")], "T", "https://izz.ro", "D"))
    assert ch.find("item").find("pubDate") is None
    # `getMessage()`, nu `r.message % r.args`: `caplog` a formatat deja mesajul, iar o a doua
    # interpolare arunca TypeError si testul ar pica pe el, nu pe absenta logului.
    assert any("pubDate" in r.getMessage() for r in caplog.records), \
        "data neparsabila trebuie sa lase o urma in log"


def test_self_link_pe_feedul_principal_si_pe_cel_de_subiect():
    principal = _channel(render._feed_xml([_art("a", "2026-08-06T07:30:00+00:00")], "T",
                                          "https://izz.ro", "D",
                                          feed_url="https://izz.ro/feed.xml"))
    self_el = principal.find(ATOM)
    assert self_el is not None and self_el.get("rel") == "self"
    assert self_el.get("href") == "https://izz.ro/feed.xml"
    assert self_el.get("type") == "application/rss+xml"

    # Feedul de subiect isi declara PROPRIA adresa, nu pe a celui principal — altfel doua
    # fluxuri diferite s-ar prezenta agregatoarelor cu aceeasi identitate.
    subiect = _channel(render._feed_xml([_art("a", "2026-08-06T07:30:00+00:00")], "T",
                                        "https://izz.ro/subiect/x/", "D",
                                        feed_url="https://izz.ro/subiect/x/feed.xml"))
    assert subiect.find(ATOM).get("href") == "https://izz.ro/subiect/x/feed.xml"


def test_feedul_ramane_xml_valid_cu_titluri_care_cer_escapare():
    arts = [_art("a", "2026-08-06T07:30:00+00:00")]
    arts[0]["title"] = 'Ceva & <altceva> "citat"'
    ch = _channel(render._feed_xml(arts, "T & U", "https://izz.ro", "D",
                                   feed_url="https://izz.ro/feed.xml"))
    assert ch.find("item").findtext("title") == 'Ceva & <altceva> "citat"'
