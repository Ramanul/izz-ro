"""Catalogul /surse/ trebuie sa acopere TOATE sursele din config.SOURCES, nu doar cele
cu statistici de originalitate (bug raportat: 29 din 189, lipseau toate cele ~121 de
primarii -- o sursa care nu intra niciodata intr-un cluster multi-sursa nu avea cum sa
apara daca pagina lista doar sintezele C cu first_source)."""
from generator import config, render


def _all_sources(group: dict) -> list:
    """Toate sursele unui grup, ORIUNDE ar sta.

    Din 2026-08-02 sursele institutionale nu mai stau in listele plate ale grupului, ci in
    arborele `regions > counties`. Invariantele de mai jos raman aceleasi — doar parcurgerea
    trebuie sa urmeze structura, altfel un test verde ar ascunde surse pierdute.
    """
    out = list(group["with_stats"]) + list(group["without_stats"])
    for region in group.get("regions", []):
        for county in region["counties"]:
            out += list(county["with_stats"]) + list(county["without_stats"])
    return out


def test_catalog_covers_every_configured_source():
    catalog, total_sources, stats_sources = render._source_catalog([])
    assert total_sources == len(config.SOURCES)

    listed_names = {s["name"] for group in catalog for s in _all_sources(group)}
    configured_names = {v["name"] for v in config.SOURCES.values()}
    assert listed_names == configured_names
    assert sum(g["count"] for g in catalog) == total_sources


def test_catalog_includes_all_local_town_halls():
    catalog, _, _ = render._source_catalog([])
    local = next(g for g in catalog if g["key"] == "local")
    configured_local = [v for v in config.SOURCES.values() if v["category"] == "local"]
    assert local["count"] == len(configured_local)
    # regressie directa la bug-ul raportat: primariile (majoritatea sursei "local")
    # trebuie sa fie prezente, nu doar cele cateva aparute in sinteze multi-sursa.
    assert local["count"] >= 100


def test_sources_without_synthesis_are_not_shown_with_misleading_zero_stats():
    """O sursa care n-a intrat inca intr-un cluster multi-sursa NU trebuie sa apara cu
    first=0/total=0/rate=0% (ar parea ca a participat si a performat prost)."""
    catalog, _, _ = render._source_catalog([])
    for group in catalog:
        without = list(group["without_stats"])
        for region in group.get("regions", []):
            for county in region["counties"]:
                without += county["without_stats"]
        for s in without:
            assert "first" not in s and "total" not in s and "rate" not in s


def test_catalog_respects_one_axis_one_home():
    """Fiecare sursa apare intr-un singur grup de categorie (nicio duplicare intre axe)."""
    catalog, _, _ = render._source_catalog([])
    seen = []
    for group in catalog:
        for s in _all_sources(group):
            seen.append(s["name"])
    assert len(seen) == len(set(seen))


def test_source_links_point_to_the_source_site_with_https():
    catalog, _, _ = render._source_catalog([])
    for group in catalog:
        for s in _all_sources(group):
            assert s["url"].startswith("https://")


def test_stats_are_preserved_when_present():
    """Sursele cu statistici de originalitate (din sinteze C reale) trebuie sa le pastreze,
    nu doar sa fie inghitite in catalogul complet."""
    fake_articles = [
        {"model": "C", "first_source": "HotNews",
         "sources": [{"name": "HotNews", "url": "https://hotnews.ro/x"},
                     {"name": "Digi24", "url": "https://digi24.ro/y"}]},
        {"model": "C", "first_source": "HotNews",
         "sources": [{"name": "HotNews", "url": "https://hotnews.ro/z"},
                     {"name": "Digi24", "url": "https://digi24.ro/w"}]},
    ]
    catalog, total_sources, stats_sources = render._source_catalog(fake_articles)
    assert stats_sources == 2
    general = next(g for g in catalog if g["key"] == "general")
    with_stats_names = {s["name"]: s for s in general["with_stats"]}
    assert with_stats_names["HotNews"]["first"] == 2
    assert with_stats_names["HotNews"]["total"] == 2
    assert with_stats_names["HotNews"]["rate"] == 100
    assert with_stats_names["Digi24"]["first"] == 0
    # inca acopera si sursele fara statistici din acelasi grup
    assert total_sources == len(config.SOURCES)
