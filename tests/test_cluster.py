"""Teste pentru clustering (over-merge si under-merge) din generator/cluster.py."""
from datetime import datetime, timezone

from generator import cluster


def _a(title, url, link=None, entities=None):
    return {"title": title, "original_title": title, "url": url,
            "original_link": link or url, "entities": entities or [],
            "published": datetime.now(timezone.utc).isoformat()}


def test_cluster_groups_same_event():
    arts = [_a("Guvernul aprobă bugetul apărării pentru 2027", "u1"),
            _a("Bugetul apărării pe 2027, aprobat de guvern", "u2")]
    groups = cluster.cluster(arts)
    assert any(len(g) == 2 for g in groups)


def test_cluster_does_not_merge_different_events():
    arts = [_a("Inundații puternice în Moldova, sate evacuate", "u1"),
            _a("Victorie pentru națională la handbal feminin", "u2")]
    groups = cluster.cluster(arts)
    assert all(len(g) == 1 for g in groups)


def test_attach_recent_entity_guard_blocks_template_matches():
    # cronici-sablon: text asemanator, entitati disjuncte -> NU se unesc
    g = [_a("Echipa învinge rivala și avansează în optimile cupei", "u1", entities=["Steaua"])]
    cand = _a("Echipa învinge rivala și avansează în optimile cupei", "u2", entities=["Rapid"])
    out = cluster.attach_recent([g], [cand])
    assert len(out[0]) == 1


def test_is_synthesis_candidate_needs_distinct_domains():
    same = [_a("t", "u1", "https://digi24.ro/a"), _a("t", "u2", "https://www.digi24.ro/b")]
    diff = [_a("t", "u3", "https://digi24.ro/a"), _a("t", "u4", "https://hotnews.ro/b")]
    assert not cluster.is_synthesis_candidate(same)
    assert cluster.is_synthesis_candidate(diff)


# ---------------------------------------------------------------------------
# Garzile de mai jos apara CONJUNCTIA din `_similar`, nu comportamentul general.
#
# DE CE EXISTA (masurat 2026-09-02, prin mutation testing): docstring-ul lui `_similar`
# argumenteaza explicit „Conditie AND (nu OR) -> evita lipirea a doua titluri lungi cu 3
# cuvinte generice comune". Decizia era scrisa, dar NEPAZITA: schimband `and` in `or` pe
# linia 40, INTREAGA suita trecea. Cu `or`, termenul `union > 0` e adevarat pentru orice
# pereche de titluri nevide, deci `_similar` ar returna True aproape mereu — over-merge
# total, toate articolele intr-un cluster.
#
# Sect. 7 cere ca schimbarile de clustering sa fie verificate pe AMBELE cazuri, over-merge
# SI under-merge. `test_cluster_does_not_merge_different_events` acoperea under-merge pe
# titluri fara legatura; ce lipsea era cazul GREU: titluri care CHIAR au tokeni comuni, dar
# nu suficient de proportional ca sa fie acelasi eveniment.


def test_similar_cere_AMBELE_praguri_nu_doar_unul():
    """Tokeni comuni PESTE prag, dar proportie SUB prag -> NU e acelasi eveniment.

    Ucide mutantul `and` -> `or`: cu `or`, primul termen singur ar decide."""
    from generator.cluster import _similar, SHARED_TOKENS_MIN, JACCARD_MIN
    comune = {f"cuvant{i}" for i in range(SHARED_TOKENS_MIN)}
    # doua titluri lungi care impart exact pragul de tokeni, dar sunt altfel diferite
    t1 = comune | {f"a{i}" for i in range(20)}
    t2 = comune | {f"b{i}" for i in range(20)}
    inter, union = len(t1 & t2), len(t1 | t2)
    assert inter >= SHARED_TOKENS_MIN, "fixtura trebuie sa treaca pragul de tokeni"
    assert inter / union < JACCARD_MIN, "fixtura trebuie sa PICE pragul de proportie"
    assert _similar(t1, t2) is False, (
        f"{inter} tokeni comuni din {union} (Jaccard {inter/union:.2f}) NU e acelasi eveniment; "
        "daca asta trece, conjunctia din _similar a devenit disjunctie")


def test_similar_cere_AMBELE_praguri_si_invers():
    """Proportie PESTE prag, dar prea putini tokeni -> tot NU.

    Cazul simetric: doua titluri foarte scurte si aproape identice trec usor de Jaccard,
    dar `SHARED_TOKENS_MIN` exista tocmai ca sa nu lipeasca stiri pe doua cuvinte. Fixtura
    se CONSTRUIESTE din constanta, ca sa nu devina tacut inaplicabila daca pragul se schimba.
    """
    from generator.cluster import _similar, SHARED_TOKENS_MIN, JACCARD_MIN
    comune = {f"cuvant{i}" for i in range(SHARED_TOKENS_MIN - 1)}   # exact UNUL sub prag
    t1, t2 = set(comune), comune | {"in_plus"}
    inter, union = len(t1 & t2), len(t1 | t2)
    assert inter / union >= JACCARD_MIN, "fixtura trebuie sa treaca pragul de proportie"
    assert inter < SHARED_TOKENS_MIN, "fixtura trebuie sa PICE pragul de tokeni"
    assert _similar(t1, t2) is False, (
        f"doar {inter} tokeni comuni, sub pragul de {SHARED_TOKENS_MIN}; "
        "daca asta trece, conjunctia din _similar a devenit disjunctie")
