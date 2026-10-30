"""Tests for the editorial corrections and withdrawals RSS feed (E4)."""
import copy
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import pytest

from generator import editorial, publication, render


@pytest.fixture
def article():
    return {
        "model": "B",
        "category": "local",
        "slug": "synthetic-correction-feed",
        "title": "Primăria Arad anunță lucrări la rețeaua de apă",
        "teaser": "Instituția anunță lucrări la rețeaua de apă din municipiu. Calendarul este disponibil în documentul publicat de instituție.",
        "original_link": "https://institutie.example/anunt/",
        "source_name": "Instituția",
        "url": "https://institutie.example/anunt/",
        "source": "pl_arad_municipiul_arad",
        "processed_by": "official",
        "published": datetime.now(timezone.utc).isoformat(),
    }


def make_record(article, state="corrected", reviewed_at="2026-10-17T18:00:00Z", notice="Eroare localitate corectată"):
    row = {
        "key": editorial.annotation_key(article),
        "public_paths": [editorial.public_path(article)],
        "state": state,
        "notice": notice,
        "evidence_url": "https://institutie.example/corectie/",
        "review": {
            "state": "approved",
            "kind": "documentary",
            "reviewer": "test-only",
            "reviewed_at": reviewed_at,
            "input_fingerprint": editorial.source_fingerprint(article),
        },
        "presentation": {
            "title": "Primăria Timișoara anunță lucrări la rețeaua de apă",
            "county": "TIMIS",
        } if state == "corrected" else {},
    }
    return {row["key"]: row}


def test_corrections_feed_empty_catalog():
    xml_str = publication.corrections_feed({}, site_url="https://izz.ro")
    root = ET.fromstring(xml_str)
    assert root.tag == "rss"
    assert root.attrib.get("version") == "2.0"
    channel = root.find("channel")
    assert channel is not None
    assert channel.find("title").text == "Corecții și retrageri — IZZ.ro"
    assert channel.find("link").text == "https://izz.ro/legal/corrections/"
    assert channel.find("language").text == "ro"
    assert channel.find("lastBuildDate") is not None
    # Empty catalog produces valid RSS with 0 items
    assert len(channel.findall("item")) == 0


def test_corrections_feed_with_corrected_item(article):
    records = make_record(article, state="corrected", reviewed_at="2026-10-25T14:30:00Z", notice="Cifra a fost revizuită conform rectificării oficiale.")
    xml_str = publication.corrections_feed(records, site_url="https://izz.ro")
    root = ET.fromstring(xml_str)
    items = root.findall(".//item")
    assert len(items) == 1
    item = items[0]
    assert item.find("title").text == "Corecție: Primăria Timișoara anunță lucrări la rețeaua de apă"
    assert item.find("link").text == "https://izz.ro/local/synthetic-correction-feed/"
    guid = item.find("guid")
    assert guid is not None
    assert guid.attrib.get("isPermaLink") == "false"
    assert "2026-10-25T14:30:00Z" in guid.text
    assert item.find("pubDate") is not None
    assert item.find("description").text == "Cifra a fost revizuită conform rectificării oficiale."


def test_corrections_feed_with_withdrawn_item(article):
    records = make_record(article, state="withdrawn", reviewed_at="2026-10-26T09:15:00Z", notice="Material retras din cauza unor informații infirmate de emitent.")
    xml_str = publication.corrections_feed(records, site_url="https://izz.ro")
    root = ET.fromstring(xml_str)
    items = root.findall(".//item")
    assert len(items) == 1
    item = items[0]
    assert "Retragere:" in item.find("title").text
    assert item.find("link").text == "https://izz.ro/local/synthetic-correction-feed/"
    guid = item.find("guid")
    assert "retragere-2026-10-26T09:15:00Z" in guid.text
    assert item.find("description").text == "Material retras din cauza unor informații infirmate de emitent."


def test_corrections_feed_ordering_and_deterministic():
    art1 = {
        "model": "B", "category": "economic", "slug": "articol-unu",
        "title": "Titlu 1", "teaser": "Teaser 1", "original_link": "https://sursa1.example/",
        "source_name": "Sursa 1", "url": "https://sursa1.example/",
        "source": "s1", "published": "2026-10-20T10:00:00Z",
    }
    art2 = {
        "model": "B", "category": "politic", "slug": "articol-doi",
        "title": "Titlu 2", "teaser": "Teaser 2", "original_link": "https://sursa2.example/",
        "source_name": "Sursa 2", "url": "https://sursa2.example/",
        "source": "s2", "published": "2026-10-21T10:00:00Z",
    }
    rec1 = make_record(art1, state="corrected", reviewed_at="2026-10-24T12:00:00Z", notice="Corectie 1")
    rec2 = make_record(art2, state="withdrawn", reviewed_at="2026-10-26T18:00:00Z", notice="Retragere 2")
    combined = {**rec1, **rec2}

    now = datetime(2026, 10, 28, tzinfo=timezone.utc)
    xml1 = publication.corrections_feed(combined, site_url="https://izz.ro", now=now)
    xml2 = publication.corrections_feed(copy.deepcopy(combined), site_url="https://izz.ro", now=now)
    # Deterministic output
    assert xml1 == xml2

    root = ET.fromstring(xml1)
    items = root.findall(".//item")
    assert len(items) == 2
    # Newest reviewed_at must come first (2026-10-26 before 2026-10-24)
    assert "Retragere" in items[0].find("title").text
    assert "Corecție" in items[1].find("title").text


@pytest.mark.parametrize("first,second", [
    ("2026-10-28T09:30:00Z", "2026-10-28T10:00:00+02:00"),
    ("2026-10-27T23:30:00-02:00", "2026-10-28T00:30:00Z"),
])
def test_corrections_feed_orders_real_instants_across_timezones(article, first, second):
    a = {**article, "slug": "first-correction"}
    b = {**article, "slug": "second-correction"}
    records = {**make_record(a, reviewed_at=first), **make_record(b, reviewed_at=second)}
    publication.validate(records, [a, b])
    xml = publication.corrections_feed(records, now=datetime(2026, 10, 28, tzinfo=timezone.utc))
    links = [item.findtext("link") for item in ET.fromstring(xml).findall(".//item")]
    assert links == ["https://izz.ro/local/first-correction/",
                     "https://izz.ro/local/second-correction/"]


def test_corrections_feed_equal_instants_have_stable_key_order(article):
    a = {**article, "slug": "a-correction"}
    b = {**article, "slug": "b-correction"}
    records = {**make_record(a, reviewed_at="2026-10-28T09:30:00Z"),
               **make_record(b, reviewed_at="2026-10-28T11:30:00+02:00")}
    now = datetime(2026, 10, 28, tzinfo=timezone.utc)
    xml = publication.corrections_feed(records, now=now)
    reversed_records = dict(reversed(list(records.items())))
    assert publication.corrections_feed(reversed_records, now=now) == xml
    links = [item.findtext("link") for item in ET.fromstring(xml).findall(".//item")]
    assert links[0].endswith("/b-correction/")


def test_render_writes_corrections_feed(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_corrections_feed({})
    feed_path = tmp_path / "corectii" / "feed.xml"
    assert feed_path.exists()
    content = feed_path.read_text(encoding="utf-8")
    assert "<title>Corecții și retrageri — IZZ.ro</title>" in content


def test_redirects_include_corrections_feed(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_redirects()
    redirects_path = tmp_path / "_redirects"
    assert redirects_path.exists()
    content = redirects_path.read_text(encoding="utf-8")
    assert "/legal/corrections/feed.xml /corectii/feed.xml 301" in content

