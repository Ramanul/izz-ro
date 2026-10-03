"""Scheletul de membri + story_id pe sinteza C (Etapa 1 STORY, IZZ-0418).

Membrii absorbiti de o sinteza C erau ARSI din stare (main.py, `folded`): istoricul
"cine a relatat ce si cand" se pierdea, iar doar 16,1% din referintele-sursa mai existau
ca articole (proba-structura, 1 oct). In loc sa pastram articole intregi in stare
(23 MB deja), sinteza C poarta acum un schelet de timeline {published, title, source,
url} per membru, plus un story_id persistent mostenit la fiecare absorbire.
"""
from generator import process


def _item(url, published, title="Titlu", source="A", **kw) -> dict:
    baza = {"url": url, "original_link": url, "source": source.lower(),
            "source_name": source, "title": title, "published": published,
            "model": "B", "category": "extern"}
    baza.update(kw)
    return baza


def test_schelet_membri_si_story_id_la_creare():
    grup = [
        _item("https://a.ro/nou", "2026-10-01T10:00:00+00:00", source="A"),
        _item("https://b.ro/vechi", "2026-10-01T09:00:00+00:00", source="B"),
    ]
    _grup, rep = process._prep_cluster_rep(grup)
    assert rep["model"] == "C"
    membri = rep["members"]
    # timeline ascendent, o intrare per membru, doar cele 4 campuri ale scheletului
    assert [m["url"] for m in membri] == ["https://b.ro/vechi", "https://a.ro/nou"]
    assert set(membri[0]) == {"published", "title", "source", "url"}
    assert membri[0]["source"] == "B"
    assert rep["story_id"].startswith("st-")


def test_absorbtia_mosteneste_story_id_si_acumuleaza_membrii():
    vechi_c = _item("https://a.ro/incendiu", "2026-10-01T08:00:00+00:00",
                    model="C", processed_by="gemini", story_id="st-abc123",
                    members=[
                        {"published": "2026-10-01T07:30:00+00:00",
                         "title": "Prima stire", "source": "X",
                         "url": "https://x.ro/prima"},
                    ])
    nou = _item("https://c.ro/actualizare", "2026-10-01T11:00:00+00:00", source="C")
    _grup, rep = process._prep_cluster_rep([nou, vechi_c])
    # story_id-ul NU se re-minte la absorbire: evenimentul ramane acelasi
    assert rep["story_id"] == "st-abc123"
    urls = [m["url"] for m in rep["members"]]
    assert urls == ["https://x.ro/prima", "https://a.ro/incendiu", "https://c.ro/actualizare"]


def test_plafonul_de_membri_taie_din_cele_vechi():
    grup = []
    for i in range(50):
        grup.append(_item(f"https://s.ro/{i}",
                          f"2026-09-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00",
                          source=f"S{i}"))
    _grup, rep = process._prep_cluster_rep(grup)
    assert len(rep["members"]) == 40
    urls = [m["url"] for m in rep["members"]]
    # taierile cad pe arhiva timeline-ului (cele mai vechi 10 ies), capatul recent rămâne
    assert "https://s.ro/0" not in urls
    assert "https://s.ro/49" in urls


def test_story_id_determinist_la_aceeasi_grupare():
    grup = [_item("https://a.ro/x", "2026-10-01T09:00:00+00:00"),
            _item("https://b.ro/y", "2026-10-01T08:00:00+00:00", source="B")]
    _g1, rep1 = process._prep_cluster_rep(grup)
    _g2, rep2 = process._prep_cluster_rep(list(reversed(grup)))
    assert rep1["story_id"] == rep2["story_id"], (
        "aceeasi grupare in alta ordine trebuie sa dea acelasi story_id")
