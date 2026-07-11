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
