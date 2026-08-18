from generator.local_sources import _DEAD_SLUGS, load_gold_sources


def test_luncavita_is_quarantined():
    assert "tulcea_luncavita" in _DEAD_SLUGS


def test_luncavita_does_not_consume_gold_slot(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "judet,localitate,site_url,site_ok,http_status,homepage_url,homepage_ok,has_rss,cms,rss_url,rss_ok,last_signal_date,notes,extra\n"
        "TULCEA,LUNCAVITA,https://www.comunaluncavita.ro,yes,200,https://www.comunaluncavita.ro,yes,yes,other,https://www.comunaluncavita.ro/rss.xml,yes,2026-07-17,,\n"
        "ALBA,Oras Viu,https://example.com,yes,200,https://example.com,yes,yes,other,https://example.com/feed,yes,2026-07-16,,\n",
        encoding="utf-8",
    )
    result = load_gold_sources(str(path), 1)
    assert "pl_tulcea_luncavita" not in result
    assert "pl_alba_oras_viu" in result
