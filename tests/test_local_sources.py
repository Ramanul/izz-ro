from generator.local_sources import load_gold_sources


def _write_csv(tmp_path, lines):
    path = tmp_path / "test.csv"
    path.write_text("\n".join(lines), encoding="utf-8-sig")
    return str(path)


CSV_HEADER = "judet,localitate,url,dns_ok,http_status,final_url,https_ok,is_primarie,cms,rss_url,rss_ok,last_signal_date,copyright_year,error"


def test_limit_respected(tmp_path):
    lines = [CSV_HEADER]
    for i in range(10):
        lines.append(f"ALBA,Local{i},http://example.com,yes,200,,,,,http://ex{i}.ro/feed/,yes,2026-06-15,,")
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 3)
    assert len(result) == 3


def test_limit_zero_returns_empty(tmp_path):
    lines = [CSV_HEADER, "ALBA,Local,http://example.com,yes,200,,,,,http://ex.ro/feed/,yes,2026-06-15,,"]
    path = _write_csv(tmp_path, lines)
    assert load_gold_sources(path, 0) == {}


def test_limit_negative_returns_empty(tmp_path):
    lines = [CSV_HEADER, "ALBA,Local,http://example.com,yes,200,,,,,http://ex.ro/feed/,yes,2026-06-15,,"]
    path = _write_csv(tmp_path, lines)
    assert load_gold_sources(path, -1) == {}


def test_filters_rss_ok_not_yes(tmp_path):
    lines = [
        CSV_HEADER,
        "ALBA,Ok,http://a.ro,yes,200,,,,,http://a.ro/feed/,yes,2026-06-15,,",
        "ALBA,No,http://b.ro,yes,200,,,,,http://b.ro/feed/,no,,,,",
        "ALBA,Empty,http://c.ro,yes,200,,,,,http://c.ro/feed/,,,,,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    assert len(result) == 1
    assert "pl_alba_ok" in result


def test_filters_empty_rss_url(tmp_path):
    lines = [
        CSV_HEADER,
        "ALBA,HasFeed,http://a.ro,yes,200,,,,,http://a.ro/feed/,yes,2026-06-15,,",
        "ALBA,NoFeed,http://b.ro,yes,200,,,,,,yes,,,,",
        "ALBA,Blank,http://c.ro,yes,200,,,,, ,yes,,,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    assert len(result) == 1
    assert "pl_alba_hasfeed" in result


def test_keys_start_with_pl(tmp_path):
    lines = [
        CSV_HEADER,
        "ALBA,CityA,http://a.ro,yes,200,,,,,http://a.ro/feed/,yes,2026-06-15,,",
        "ALBA,CityB,http://b.ro,yes,200,,,,,http://b.ro/feed/,yes,2026-06-15,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    for k in result:
        assert k.startswith("pl_"), f"key {k} does not start with pl_"


def test_value_shape(tmp_path):
    lines = [
        CSV_HEADER,
        "ALBA,TestCity,http://t.ro,yes,200,,,,,http://t.ro/feed/,yes,2026-06-15,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    entry = result["pl_alba_testcity"]
    assert entry["name"] == "Primăria Testcity"
    assert entry["url"] == "http://t.ro/feed/"
    assert entry["category"] == "local"


def test_deterministic_order(tmp_path):
    lines = [
        CSV_HEADER,
        "SIBIU,Z,http://z.ro,yes,200,,,,,http://z.ro/feed/,yes,2026-06-10,,",
        "ALBA,A,http://a.ro,yes,200,,,,,http://a.ro/feed/,yes,2026-06-10,,",
        "SIBIU,A,http://sa.ro,yes,200,,,,,http://sa.ro/feed/,yes,2026-06-05,,",
        "ALBA,Z,http://az.ro,yes,200,,,,,http://az.ro/feed/,yes,2026-06-15,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    keys = list(result.keys())
    assert keys == ["pl_alba_z", "pl_alba_a", "pl_sibiu_z", "pl_sibiu_a"]


def test_missing_file_returns_empty():
    assert load_gold_sources("/nonexistent/path.csv", 10) == {}


def test_duplicate_keys_keep_first(tmp_path):
    lines = [
        CSV_HEADER,
        "ALBA,City,http://first.ro,yes,200,,,,,http://first.ro/feed/,yes,2026-06-20,,",
        "ALBA,City,http://second.ro,yes,200,,,,,http://second.ro/feed/,yes,2026-06-15,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    assert len(result) == 1
    assert result["pl_alba_city"]["url"] == "http://first.ro/feed/"


def test_slug_special_chars(tmp_path):
    lines = [
        CSV_HEADER,
        "MUREȘ,Herești,http://m.ro,yes,200,,,,,http://m.ro/feed/,yes,2026-06-15,,",
        "BUCUREȘTI,Sector 1,http://b.ro,yes,200,,,,,http://b.ro/feed/,yes,2026-06-15,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    assert "pl_mure_here_ti" in result
    assert "pl_bucure_ti_sector_1" in result


def test_filters_old_date(tmp_path):
    lines = [
        CSV_HEADER,
        "ALBA,Fresh,http://f.ro,yes,200,,,,,http://f.ro/feed/,yes,2026-06-15,,",
        "ALBA,Old,http://o.ro,yes,200,,,,,http://o.ro/feed/,yes,2025-12-31,,",
        "ALBA,EmptyDate,http://e.ro,yes,200,,,,,http://e.ro/feed/,yes,,,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    assert "pl_alba_fresh" in result
    assert "pl_alba_old" not in result
    assert "pl_alba_emptydate" not in result


def test_order_desc_by_date(tmp_path):
    lines = [
        CSV_HEADER,
        "ZZZ,Oldest,http://z_old.ro,yes,200,,,,,http://z_old.ro/feed/,yes,2026-01-01,,",
        "AAA,Freshest,http://a_fresh.ro,yes,200,,,,,http://a_fresh.ro/feed/,yes,2026-06-15,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    keys = list(result.keys())
    assert keys[0] == "pl_aaa_freshest"
    assert keys[1] == "pl_zzz_oldest"


def test_tie_break_asc_judet_localitate(tmp_path):
    lines = [
        CSV_HEADER,
        "SIBIU,Z,http://sz.ro,yes,200,,,,,http://sz.ro/feed/,yes,2026-06-10,,",
        "ALBA,A,http://aa.ro,yes,200,,,,,http://aa.ro/feed/,yes,2026-06-10,,",
        "ALBA,Z,http://az.ro,yes,200,,,,,http://az.ro/feed/,yes,2026-06-10,,",
        "SIBIU,A,http://sa.ro,yes,200,,,,,http://sa.ro/feed/,yes,2026-06-10,,",
    ]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 10)
    keys = list(result.keys())
    assert keys == ["pl_alba_a", "pl_alba_z", "pl_sibiu_a", "pl_sibiu_z"]


def test_integration_pl_sources_count():
    from generator import config
    count = sum(1 for k in config.SOURCES if k.startswith("pl_"))
    assert 0 < count <= 120  # LOCAL_GOLD_LIMIT default (impact-first: municipii/orase intai)


def test_pl_sources_ordered_before_gsp():
    from generator import config
    keys = list(config.SOURCES)
    pl_indices = [i for i, k in enumerate(keys) if k.startswith("pl_")]
    gsp_idx = keys.index("gsp")
    assert len(pl_indices) > 0            # loaded (exact count depends on LOCAL_GOLD_LIMIT)
    assert max(pl_indices) < gsp_idx      # invariant: gold block stays before gsp
    first_pl_idx = pl_indices[0]
    assert config.SOURCES[keys[first_pl_idx - 1]]["category"] == "local"


def test_impact_tier_orders_municipiu_before_oras_before_comuna(tmp_path):
    # regula statica: municipiu > oras > comuna, chiar daca o comuna e mai proaspata
    lines = [CSV_HEADER,
             "ALBA,Comuna Fresh,http://a,yes,200,,,,,http://c.ro/feed/,yes,2026-07-20,,",
             "ALBA,Oras Mijloc,http://b,yes,200,,,,,http://o.ro/feed/,yes,2026-05-01,,",
             "ALBA,Municipiul Mare,http://c,yes,200,,,,,http://m.ro/feed/,yes,2026-01-15,,"]
    path = _write_csv(tmp_path, lines)
    names = [v["name"] for v in load_gold_sources(path, 10).values()]
    # municipiul (cel mai vechi) trebuie sa fie PRIMUL, comuna proaspata ULTIMA
    assert "Municipiul Mare" in names[0]
    assert "Oras Mijloc" in names[1]
    assert "Comuna Fresh" in names[2]


def test_impact_tier_word_boundary_not_substring():
    """Regresie (review cont A, 2026-07-24): potrivirea pe substring clasifica gresit.
    'ORASTIOARA DE SUS' e o COMUNA dar contine 'ORAS'; forma 'MUNICIPIU' fara -L cadea la comuna."""
    from generator.local_sources import _impact_tier
    assert _impact_tier("ORASTIOARA DE SUS") == 2      # comuna, NU oras
    assert _impact_tier("MUNICIPIU TEST") == 0         # fara -L, tot municipiu
    assert _impact_tier("ORAS SOVATA") == 1
    assert _impact_tier("ORASUL VICTORIA") == 1
    assert _impact_tier("ORAȘ TEST") == 1              # cu diacritic
    assert _impact_tier("MUNICIPIUL BRAILA") == 0
    assert _impact_tier("VALEA LUNGA") == 2


def test_dead_slugs_excluded_and_slot_reused(tmp_path):
    """Sursele moarte cunoscute (feedcheck 30121199000) nu ocupa sloturi: sunt scoase
    INAINTE de taierea la limita, deci slotul se duce la urmatorul candidat viu."""
    from generator.local_sources import _DEAD_SLUGS
    dead = "dolj_oras_segarcea"
    assert dead in _DEAD_SLUGS, "fixture-ul presupune ca acest slug e pe lista"
    lines = [CSV_HEADER,
             # cea moarta e prima ca prospetime, deci fara excludere ar lua slotul
             "DOLJ,Oras Segarcea,http://d,yes,200,,,,,http://d.ro/feed/,yes,2026-07-24,,",
             "ALBA,Oras Viu,http://a,yes,200,,,,,http://a.ro/feed/,yes,2026-07-01,,"]
    path = _write_csv(tmp_path, lines)
    result = load_gold_sources(path, 1)          # UN singur slot
    assert "pl_dolj_oras_segarcea" not in result  # exclusa
    assert "pl_alba_oras_viu" in result           # slotul a mers mai departe, nu s-a pierdut
    assert len(result) == 1


def test_dead_slugs_are_slugs_not_keys():
    """Lista contine slug-uri fara prefixul pl_ — altfel filtrul n-ar potrivi nimic."""
    from generator.local_sources import _DEAD_SLUGS
    assert all(not s.startswith("pl_") for s in _DEAD_SLUGS)
