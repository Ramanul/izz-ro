"""Cine consuma bugetul AI cand nu ajunge pentru toti.

Masurat 2026-08-02 pe logurile `build.yml`: bugetul (18 apeluri, 8 rezervate upgrade-urilor)
e consumat INTEGRAL la fiecare rulare — 10/10 in trei rulari consecutive — in timp ce intra
244-261 de iteme noi. Ordinea de consum era ordinea din `config.SOURCES`, pastrata deliberat
de fetch (`fetch.py`: „ce ajunge la coada e infometat"). Sub saturatie permanenta, pozitia in
config decide ce se publica.

Testele apara ordinea noua — coroborare, apoi prospetime — si contorul care face presiunea
vizibila. Fara contor, raportul spunea doar cate articole au iesit, niciodata cate au ramas
afara. Spec: specs/ai-budget-ordering.md
"""
from datetime import datetime, timedelta, timezone

import pytest

from generator import main, state


def _iso(minutes_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _item(url: str, titlu: str, minutes_ago: float, sursa: str = "test_src") -> dict:
    return {
        "url": url, "original_link": url, "source": sursa, "source_name": sursa,
        "title": titlu, "original_title": titlu, "description": "",
        "category": "extern", "model": None, "published": _iso(minutes_ago),
    }


class _Provider:
    """Provider fals: nu cheama nimic, doar noteaza ce i s-a cerut, in ordine."""
    name = "fake"
    calls = 0
    failures = 0
    last_error = None


def _fals_ai(monkeypatch, vazute: list):
    """Inlocuieste caile AI cu functii care doar inregistreaza si intorc un rezultat valid.

    `_cluster_batch` inlocuieste `process_clusters_batch` (2026-08-16, batching Model C):
    UN apel poate acoperi mai multe clustere deodata, deci inregistreaza cate o intrare "C"
    per APEL, cu tuplul de urluri per cluster din lot -- nu mai e 1:1 apel<->cluster."""
    def _cluster_batch(groups, provider):
        vazute.append(("C", tuple(tuple(a["url"] for a in g) for g in groups)))
        out = []
        for g in groups:
            rep = dict(g[0])
            rep.update(model="C", synthesis="sinteza", processed_by="fake")
            out.append(rep)
        return out

    def _batch(items, provider):
        vazute.append(("B", tuple(i["url"] for i in items)))
        out = []
        for i in items:
            a = dict(i)
            a.update(model="B", teaser="teaser", processed_by="fake")
            out.append(a)
        return out

    monkeypatch.setattr(main, "process_clusters_batch", _cluster_batch)
    monkeypatch.setattr(main, "process_batch", _batch)


def test_clusterul_cu_mai_multe_surse_intra_primul(monkeypatch):
    """Coroborarea bate ordinea de intrare: doua domenii independente pe acelasi eveniment
    sunt semnal de eveniment real, unul singur poate fi doar un titlu care se repeta."""
    vazute: list = []
    _fals_ai(monkeypatch, vazute)
    # CLUSTER_BATCH_SIZE=1: testul verifica ORDINEA de selectie, nu batching-ul (are testul lui
    # separat, test_lotul_de_clustere_consuma_un_singur_apel) -- cu latimea implicita (3), un
    # buget de 1 apel ar acoperi ambele clustere din exemplu si ordinea n-ar mai fi observabila.
    monkeypatch.setattr(main.config, "CLUSTER_BATCH_SIZE", 1)
    slab = [_item("https://a.ro/1", "guvernul a aprobat ordonanta despre pensii", 10),
            _item("https://a.ro/2", "guvernul a aprobat ordonanta despre pensii azi", 11)]
    tare = [_item("https://b.ro/1", "incendiu puternic la depozitul din constanta", 30),
            _item("https://c.ro/1", "incendiu puternic la depozitul din constanta azi", 31)]
    monkeypatch.setattr(main.cluster, "cluster", lambda items: [slab, tare])
    monkeypatch.setattr(main.cluster, "attach_recent", lambda groups, rec: groups)
    monkeypatch.setattr(main.cluster, "is_synthesis_candidate", lambda g: True)

    main.process_new(slab + tare, _Provider(), budget=1)

    assert len(vazute) == 1, "bugetul de 1 apel a fost depasit"
    tip, loturi = vazute[0]
    assert tip == "C" and loturi == (("https://b.ro/1", "https://c.ro/1"),), \
        "a intrat clusterul cu un singur domeniu, desi exista unul coroborat de doua"


def test_la_egalitate_de_surse_intra_cel_mai_proaspat(monkeypatch):
    vazute: list = []
    _fals_ai(monkeypatch, vazute)
    monkeypatch.setattr(main.config, "CLUSTER_BATCH_SIZE", 1)  # vezi nota din testul anterior
    vechi = [_item("https://a.ro/1", "sedinta de guvern amanata pentru saptamana viitoare", 300),
             _item("https://b.ro/1", "sedinta de guvern amanata pentru saptamana asta", 310)]
    proaspat = [_item("https://c.ro/1", "explozie la o conducta de gaz din prahova", 5),
                _item("https://d.ro/1", "explozie la o conducta de gaz in prahova", 6)]
    monkeypatch.setattr(main.cluster, "cluster", lambda items: [vechi, proaspat])
    monkeypatch.setattr(main.cluster, "attach_recent", lambda groups, rec: groups)
    monkeypatch.setattr(main.cluster, "is_synthesis_candidate", lambda g: True)

    main.process_new(vechi + proaspat, _Provider(), budget=1)

    assert vazute[0][1] == (("https://c.ro/1", "https://d.ro/1"),)


def test_articolele_individuale_merg_dupa_prospetime_nu_dupa_ordinea_din_config(monkeypatch):
    """Cazul care motiveaza slice-ul: itemul proaspat al unei surse de la COADA listei
    trebuie sa intre inaintea unuia vechi al unei surse din CAPUL ei."""
    vazute: list = []
    _fals_ai(monkeypatch, vazute)
    monkeypatch.setattr(main.config, "BATCH_SIZE", 1)
    vechi = _item("https://cap.ro/1", "articol vechi din capul listei", 400, sursa="prima")
    nou = _item("https://coada.ro/1", "articol proaspat din coada listei", 2, sursa="ultima")
    monkeypatch.setattr(main.cluster, "cluster", lambda items: [[vechi], [nou]])
    monkeypatch.setattr(main.cluster, "attach_recent", lambda groups, rec: groups)

    main.process_new([vechi, nou], _Provider(), budget=1)

    assert vazute == [("B", ("https://coada.ro/1",))]


def test_la_scor_egal_selectia_nu_depinde_de_ordinea_de_intrare(monkeypatch):
    """Egalitatile nu sunt teoretice: sursele cu data fara ora primesc toate miezul noptii
    UTC. `sort` fiind stabil, fara departajare acele iteme ar cadea inapoi pe ordinea de
    intrare — adica pe ordinea din config, exact ce elimina slice-ul asta."""
    aceeasi_ora = _iso(60)
    iteme = []
    for n in range(1, 6):
        it = _item(f"https://egal{n}.ro/1", f"titlu identic ca vechime numarul {n}", 60,
                   sursa=f"sursa{n}")
        it["published"] = aceeasi_ora
        iteme.append(it)

    def _selectie(ordine):
        vazute: list = []
        _fals_ai(monkeypatch, vazute)
        monkeypatch.setattr(main.config, "BATCH_SIZE", 1)
        monkeypatch.setattr(main.cluster, "cluster", lambda items: [[i] for i in items])
        monkeypatch.setattr(main.cluster, "attach_recent", lambda groups, rec: groups)
        main.process_new(list(ordine), _Provider(), budget=2)
        return [urls for _, urls in vazute]

    assert _selectie(iteme) == _selectie(list(reversed(iteme))), \
        "cu timpi egali, selectia s-a schimbat odata cu ordinea de intrare"


def test_ordinea_nu_schimba_ce_se_publica_la_buget_nelimitat(monkeypatch):
    """Sortarea e o politica de RATIONALIZARE. Cand nu se rationalizeaza nimic,
    multimea publicata trebuie sa fie identica — altfel am schimbat continutul, nu ordinea."""
    vazute: list = []
    _fals_ai(monkeypatch, vazute)
    iteme = [_item(f"https://x.ro/{n}", f"titlu numarul {n}", n * 3) for n in range(1, 8)]
    monkeypatch.setattr(main.cluster, "cluster", lambda items: [[i] for i in iteme])
    monkeypatch.setattr(main.cluster, "attach_recent", lambda groups, rec: groups)

    procesate, _, _ = main.process_new(iteme, _Provider(), budget=999)

    assert {a["url"] for a in procesate} == {i["url"] for i in iteme}


def test_lotul_de_clustere_consuma_un_singur_apel(monkeypatch):
    """Fixul de batching (2026-08-16): CLUSTER_BATCH_SIZE clustere intra intr-UN apel, nu
    unul per apel -- masurat pe build.yml, 17-18 clustere/rulare epuizau tot bugetul si
    lasau 0 pentru model B. Cu latimea implicita (3) si 5 clustere, bugetul de 2 apeluri
    trebuie sa acopere toate cinci (2 loturi: 3 + 2), nu doar 2 cate unul."""
    vazute: list = []
    _fals_ai(monkeypatch, vazute)
    grupuri = [[_item(f"https://ev{n}a.ro/1", f"eveniment {n} sursa a", n),
                _item(f"https://ev{n}b.ro/1", f"eveniment {n} sursa b", n)]
               for n in range(1, 6)]
    monkeypatch.setattr(main.cluster, "cluster", lambda items: grupuri)
    monkeypatch.setattr(main.cluster, "attach_recent", lambda groups, rec: groups)
    monkeypatch.setattr(main.cluster, "is_synthesis_candidate", lambda g: True)

    procesate, _, folosite = main.process_new(
        [it for g in grupuri for it in g], _Provider(), budget=2)

    assert folosite == 2, "5 clustere la latime 3 trebuie sa incapa in 2 apeluri (3+2)"
    assert len(procesate) == 5, "toate cele 5 clustere trebuiau procesate, niciunul amanat"
    apeluri_c = [v for v in vazute if v[0] == "C"]
    assert len(apeluri_c) == 2
    assert [len(lot) for _, lot in apeluri_c] == [3, 2]


@pytest.fixture
def ruleaza(tmp_path, monkeypatch):
    def _run(items, budget):
        p = tmp_path / "articles.json"
        p.write_text("[]", encoding="utf-8")
        monkeypatch.setattr(state, "STATE_PATH", str(p))
        monkeypatch.setattr(main.fetch, "fetch_all", lambda: (items, []))
        monkeypatch.setattr(main, "get_provider", lambda: _Provider())
        monkeypatch.setenv("MAX_AI_CALLS_PER_RUN", str(budget))
        monkeypatch.setenv("UPGRADE_RESERVE", "0")
        return main.run(dry_run=True)
    return _run


def test_stats_numara_itemele_lasate_fara_AI(ruleaza, monkeypatch):
    vazute: list = []
    _fals_ai(monkeypatch, vazute)
    monkeypatch.setattr(main.config, "BATCH_SIZE", 1)
    iteme = [_item(f"https://x.ro/{n}", f"titlu unic numarul {n}", n) for n in range(1, 6)]
    monkeypatch.setattr(main.cluster, "cluster", lambda items: [[i] for i in iteme])
    monkeypatch.setattr(main.cluster, "attach_recent", lambda groups, rec: groups)

    stats = ruleaza(iteme, budget=2)

    assert stats["new"] == 5
    assert stats["deferred"] == 3, "contorul nu reflecta itemele ramase fara buget"


def test_deferred_e_zero_cand_bugetul_ajunge(ruleaza, monkeypatch):
    vazute: list = []
    _fals_ai(monkeypatch, vazute)
    iteme = [_item(f"https://y.ro/{n}", f"alt titlu unic numarul {n}", n) for n in range(1, 4)]
    monkeypatch.setattr(main.cluster, "cluster", lambda items: [[i] for i in iteme])
    monkeypatch.setattr(main.cluster, "attach_recent", lambda groups, rec: groups)

    stats = ruleaza(iteme, budget=50)

    assert stats["deferred"] == 0
