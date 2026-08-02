"""Logica editoriala din render.py — cea care decide CE APARE PE SITE.

Din 39 de functii, doar `_dedup` si `_grupeaza_pe_regiuni` aveau teste; `_quality_gate`,
`_diversify`, `_pick_hero` si `sources_coherent` decid ce se publica si ce se arunca (regula
„Zero Zgomot", CLAUDE.md §7) si nu erau acoperite deloc.
Intrari/iesiri: functii pure — dict/lista in, bool/lista out. Zero disk, zero retea.
Acceptare: testele INGHEATA comportamentul actual. Daca unul pica dupa un refactor,
comportament vizibil s-a schimbat — asta e o decizie, nu un detaliu.
"""
from generator import render


def _ok(**over):
    """Articol care trece gate-ul; testele il strica pe cate un camp o data."""
    a = {
        "title": "Primaria a aprobat bugetul",
        "teaser": "Consiliul local a votat bugetul pe 2026 in sedinta de joi.",
        "original_link": "https://ex.ro/buget-2026",
        "processed_by": "gemini",
        "model": "A",
    }
    a.update(over)
    return a


# --- _quality_gate: ce se publica --------------------------------------------

def test_gate_passes_a_complete_article():
    assert render._quality_gate(_ok())


def test_gate_rejects_an_empty_or_whitespace_title():
    assert not render._quality_gate(_ok(title=""))
    assert not render._quality_gate(_ok(title="   "))


def test_gate_reads_synthesis_for_model_c_and_teaser_otherwise():
    # Un cluster C are `synthesis`; `teaser` nu-l salveaza daca sinteza lipseste.
    assert render._quality_gate(_ok(model="C", synthesis="Sinteza din trei surse.",
                                    sources=[{"url": "https://a.ro/x-buget"},
                                             {"url": "https://b.ro/y-buget"}]))
    assert not render._quality_gate(_ok(model="C", synthesis="",
                                        teaser="teaser bun dar irelevant aici"))


def test_gate_rejects_placeholder_bodies():
    # Astea sunt exact textele de umplutura; publicarea lor e output degradat.
    for ph in ("Detalii pe sursa.", "Detalii pe surse.", ""):
        assert not render._quality_gate(_ok(teaser=ph)), ph


def test_gate_rejects_a_body_identical_to_the_title():
    t = "Primaria a aprobat bugetul"
    assert not render._quality_gate(_ok(title=t, teaser=t))


def test_gate_requires_at_least_one_source():
    assert not render._quality_gate(_ok(original_link="", sources=[]))
    # oricare dintre cele doua e de ajuns
    assert render._quality_gate(_ok(original_link="", sources=[{"url": "https://a.ro/x"}]))


def test_gate_rejects_fallback_processing_in_any_language():
    # Fallback = titlu/body brut din RSS, fara sinteza AI. Ramane in state si se reia.
    assert not render._quality_gate(_ok(processed_by="fallback"))


def test_gate_rejects_a_truncated_title():
    assert not render._quality_gate(_ok(title="Primaria a aprobat..."))
    assert not render._quality_gate(_ok(title="Primaria a aprobat…"))   # elipsa unicode


def test_gate_rejects_model_c_with_incoherent_sources():
    a = _ok(model="C", synthesis="Sinteza.",
            sources=[{"url": "https://a.ro/buget-local-aprobat"},
                     {"url": "https://b.ro/meteo-vremea-maine"}])
    assert not render.sources_coherent(a)
    assert not render._quality_gate(a)


def test_gate_does_not_apply_source_coherence_outside_model_c():
    # Un articol cu o singura sursa nu are ce sa fie „incoerent".
    assert render._quality_gate(_ok(model="A",
                                    sources=[{"url": "https://a.ro/buget"},
                                             {"url": "https://b.ro/cu-totul-altceva"}]))


# --- sources_coherent: prinde mis-clustering ---------------------------------

def test_coherence_is_vacuous_below_two_sources():
    assert render.sources_coherent({"sources": []})
    assert render.sources_coherent({"sources": [{"url": "https://a.ro/x"}]})
    assert render.sources_coherent({})


def test_coherence_accepts_sources_sharing_a_word():
    assert render.sources_coherent({"sources": [
        {"url": "https://a.ro/buget-local-aprobat"},
        {"url": "https://b.ro/aprobat-bugetul-local"},
    ]})


def test_coherence_rejects_one_unrelated_source_among_related_ones():
    assert not render.sources_coherent({"sources": [
        {"url": "https://a.ro/incendiu-depozit-vaslui"},
        {"url": "https://b.ro/incendiu-depozit-vaslui-pompieri"},
        {"url": "https://c.ro/campionatul-national-scrima"},
    ]})


def test_coherence_ignores_a_source_whose_url_yields_no_tokens():
    # Un URL fara slug util nu are voie sa condamne clusterul.
    assert render.sources_coherent({"sources": [
        {"url": "https://a.ro/buget-local"},
        {"url": "https://b.ro/"},
        {"url": "https://c.ro/buget-local-vot"},
    ]})


def test_slug_stems_strips_query_and_fragment():
    assert render._slug_stems("https://a.ro/buget-local?utm=x#top") == \
           render._slug_stems("https://a.ro/buget-local")


# --- _diversify: nu monopoliza vizual ----------------------------------------

def _art(dom, i):
    return {"original_link": f"https://{dom}/stire-{i}", "source_name": dom}


def test_diversify_never_drops_or_duplicates_items():
    items = [_art("digi24.ro", i) for i in range(4)] + [_art("hotnews.ro", i) for i in range(2)]
    out = render._diversify(list(items))
    assert len(out) == len(items)
    assert {id(x) for x in out} == {id(x) for x in items}


def test_diversify_breaks_a_run_longer_than_max_run():
    items = [_art("digi24.ro", i) for i in range(4)] + [_art("hotnews.ro", 0)]
    doms = [render.domain_of(a["original_link"]) for a in render._diversify(items, max_run=2)]
    # nicaieri trei la rand de la aceeasi sursa, desi intrarea avea patru
    assert not any(doms[i] == doms[i + 1] == doms[i + 2] for i in range(len(doms) - 2))


def test_diversify_leaves_an_already_varied_list_in_order():
    items = [_art("a.ro", 0), _art("b.ro", 0), _art("a.ro", 1), _art("b.ro", 1)]
    assert render._diversify(list(items), max_run=2) == items


def test_diversify_tolerates_a_single_source_list():
    # Nu exista alta sursa spre care sa comute; nu trebuie sa se blocheze.
    items = [_art("a.ro", i) for i in range(5)]
    assert len(render._diversify(list(items), max_run=2)) == 5


# --- _pick_hero: ce ajunge sus pe prima pagina -------------------------------

def _hero(pb="gemini", model="A", pub="2026-08-01", featured=False, tag=""):
    return {"processed_by": pb, "model": model, "published": pub,
            "featured": featured, "title": tag}


def test_hero_caps_at_six():
    assert len(render._pick_hero([_hero(tag=str(i)) for i in range(20)])) == 6


def test_hero_puts_featured_first_regardless_of_the_rest():
    featured = _hero(featured=True, pb="fallback", pub="2020-01-01", tag="F")
    fresh = _hero(pub="2026-08-02", tag="N")
    assert [a["title"] for a in render._pick_hero([fresh, featured])] == ["F", "N"]


def test_hero_prefers_ai_processed_over_fallback():
    out = render._pick_hero([_hero(pb="fallback", pub="2026-08-02", tag="FB"),
                             _hero(pb="gemini", pub="2026-01-01", tag="AI")])
    assert [a["title"] for a in out] == ["AI", "FB"]


def test_hero_prefers_cluster_c_within_the_same_processing():
    out = render._pick_hero([_hero(model="A", pub="2026-08-02", tag="A"),
                             _hero(model="C", pub="2026-01-01", tag="C")])
    assert [a["title"] for a in out] == ["C", "A"]


def test_hero_falls_back_to_recency_when_rank_ties():
    out = render._pick_hero([_hero(pub="2026-01-01", tag="vechi"),
                             _hero(pub="2026-08-02", tag="nou")])
    assert [a["title"] for a in out] == ["nou", "vechi"]


def test_hero_tolerates_a_missing_published_field():
    out = render._pick_hero([_hero(pub=None, tag="fara-data"), _hero(pub="2026-08-02", tag="cu")])
    assert [a["title"] for a in out] == ["cu", "fara-data"]


# --- _entity_index: pragul de 2 aparitii -------------------------------------

def test_entity_index_keeps_only_entities_seen_at_least_twice():
    arts = [{"entities": ["Klaus Iohannis", "Cluj"]},
            {"entities": ["Klaus Iohannis"]},
            {"entities": ["Timisoara"]}]
    idx = render._entity_index(arts)
    assert set(idx) == {render.slugify("Klaus Iohannis")[:60]}
    assert len(idx[render.slugify("Klaus Iohannis")[:60]]["articles"]) == 2


def test_entity_index_skips_entities_that_slugify_to_nothing():
    assert render._entity_index([{"entities": ["!!!"]}, {"entities": ["!!!"]}]) == {}
