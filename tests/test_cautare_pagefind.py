"""Cautarea: indexul Pagefind construit in pipeline + mapa de rezultate.

De ce exista testele astea. Cautarea are doua bucati care se pot rupe TACUT, amandoua
observabile abia de un cititor care cauta ceva si nu gaseste:

  1. semnalele din `templates/article.html` (`data-pagefind-body`, filtre, sortare). Daca
     dispar, Pagefind nu mai stie ce sa indexeze: build-ul ramane verde, indexul iese gol,
     iar /cauta/ intoarce „Niciun rezultat" la orice termen. Verificat pe randarea reala:
     fara `data-pagefind-body` Pagefind indexeaza tot `<body>`, cu tot cu nav si subsol,
     iar „Rezumat" se potriveste pe fiecare pagina (eticheta de incredere) — adica zgomot.
  2. legatura id Pagefind -> articol din `search-index.json`. Fara ea, rezultatele n-ar
     avea nici titlu, nici link, fiindca fragmentele (care le poarta) sunt sterse la build
     ca sa incapa in plafonul de fisiere al gazdei.

Fiecare garda are si un caz negativ: o garda care nu poate pica e mai rea decat niciuna.
"""
import gzip
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config, pagefind_index, render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- formatul fragmentului Pagefind -------------------------------------------------
def _scrie_fragment(out_dir: str, id_pagina: str, url: str, semnatura=None) -> None:
    """Un fragment exact cum il scrie Pagefind: gzip, semnatura, JSON."""
    director = os.path.join(out_dir, pagefind_index.SUBDIR, "fragment")
    os.makedirs(director, exist_ok=True)
    corp = json.dumps({"url": url, "content": "text de test"}).encode("utf-8")
    semnatura = pagefind_index.SEMANTURA if semnatura is None else semnatura
    with open(os.path.join(director, f"{id_pagina}.pf_fragment"), "wb") as fh:
        fh.write(gzip.compress(semnatura + corp))


def test_harta_leaga_idul_pagefind_de_url(tmp_path):
    """Id-ul din mapa e numele fisierului de fragment — asta il intoarce si `search()`."""
    _scrie_fragment(str(tmp_path), "ro_abc1234", "/local/un-slug/")
    _scrie_fragment(str(tmp_path), "ro_def5678", "/sport/alt-slug/")
    assert pagefind_index.harta_url_id(str(tmp_path)) == {
        "/local/un-slug/": "ro_abc1234",
        "/sport/alt-slug/": "ro_def5678",
    }


def test_harta_e_goala_cand_nu_exista_index(tmp_path):
    """Cazul „build fara Pagefind": nicio harta, dar nici eroare — cautarea cade pe titluri."""
    assert pagefind_index.harta_url_id(str(tmp_path)) == {}


def test_harta_pica_daca_formatul_se_schimba(tmp_path):
    """Cazul negativ. O mapa goala ar trece testele si ar lasa /cauta/ fara rezultate.

    Pagefind isi schimba formatul intre versiuni majore, iar versiunea e fixata in
    `requirements.txt`; daca intr-o zi nu mai corespunde, esecul trebuie sa fie aici.
    """
    _scrie_fragment(str(tmp_path), "ro_abc1234", "/local/un-slug/", semnatura=b"alt_format!")
    with pytest.raises(RuntimeError, match="formatul Pagefind s-a schimbat"):
        pagefind_index.harta_url_id(str(tmp_path))


def test_harta_pica_daca_fragmentul_nu_e_gzip(tmp_path):
    director = os.path.join(str(tmp_path), pagefind_index.SUBDIR, "fragment")
    os.makedirs(director)
    with open(os.path.join(director, "ro_abc1234.pf_fragment"), "wb") as fh:
        fh.write(b"nu e gzip")
    with pytest.raises(RuntimeError, match="nu e gzip valid"):
        pagefind_index.harta_url_id(str(tmp_path))


# --- ce ramane in bundle -----------------------------------------------------------
def test_curata_bundle_scoate_fragmentele_si_pastreaza_indexul(tmp_path):
    """Bugetul gazdei: un fragment per pagina ar trece plafonul de 20.000 de fisiere."""
    radacina = tmp_path / pagefind_index.SUBDIR
    (radacina / "index").mkdir(parents=True)
    (radacina / "index" / "ro_1.pf_index").write_bytes(b"index")
    (radacina / "pagefind.js").write_text("// modul")
    (radacina / "pagefind-ui.js").write_text("// UI nefolosit")
    (radacina / "pagefind-highlight.js").write_text("// highlight nefolosit")
    _scrie_fragment(str(tmp_path), "ro_abc1234", "/local/un-slug/")
    _scrie_fragment(str(tmp_path), "ro_def5678", "/sport/alt-slug/")

    assert pagefind_index.curata_bundle(str(tmp_path)) == 4
    assert not (radacina / "fragment").exists()
    assert not (radacina / "pagefind-ui.js").exists()
    assert (radacina / "index" / "ro_1.pf_index").exists()
    assert (radacina / "pagefind.js").exists()
    assert pagefind_index.numara_fisiere(str(tmp_path)) == 2


# --- mapa de rezultate -------------------------------------------------------------
def _articol(slug, categorie="local", titlu="Un titlu de test"):
    return {"category": categorie, "slug": slug, "title": titlu, "display_title": titlu,
            "published_human": "3 octombrie 2026, 14:06", "tip_anunt": ""}


def test_mapa_de_rezultate_leaga_articolul_de_id(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    hartie = {"/local/un-slug/": "ro_abc1234"}
    indexate = render._write_search_index([_articol("un-slug")], hartie)
    date = json.loads((tmp_path / "search-index.json").read_text(encoding="utf-8"))
    assert indexate == 1
    assert date["v"] == 2
    assert date["a"] == [["/local/un-slug/", "Un titlu de test", "local",
                          "3 octombrie 2026, 14:06", "", "ro_abc1234"]]


def test_articolul_neindexat_ramane_cu_id_nul(tmp_path, monkeypatch):
    """Cazul negativ: fara id, clientul nu-l poate afisa ca rezultat Pagefind.

    Nu e un accident de ignorat — e semnul ca pagina n-a fost scrisa sau ca indexul n-a
    putut fi construit, iar `build.json` poarta `search.pagini` ca sa se vada diferenta.
    """
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    assert render._write_search_index([_articol("un-slug")], {}) == 0
    date = json.loads((tmp_path / "search-index.json").read_text(encoding="utf-8"))
    assert date["a"][0][5] is None


# --- semnalele din sablon ----------------------------------------------------------
def test_pagina_de_articol_poarta_semnalele_pagefind():
    """Daca dispar, indexul iese gol sau plin de zgomot — build-ul ramane verde in ambele cazuri."""
    articol = _articol("un-slug", categorie="politic", titlu="Guvernul a aprobat bugetul")
    articol.update({
        "model": "B", "teaser": "Rezumatul scris de noi despre buget.", "synthesis": "",
        "source_name": "Sursa A", "original_link": "https://example.test/a", "sources": [],
        "first_source": None, "anunt_fara_corp": False, "ai_generat": True, "art_path": None,
        "art_webp": None, "lead_credit": None, "photo_path": None, "photo_webp": None,
        "art_style": None, "published": "2026-10-03T14:06:00+00:00", "tip_anunt": "",
        "publicitar_la_sursa": False, "updated_human": "",
    })
    html = render._env().get_template("article.html").render(**render._base_ctx(
        "/politic/un-slug/", a=articol, active_cat="politic", topics=[], people=[], related=[]))
    assert 'data-pagefind-filter="categorie: politic"' in html
    assert 'data-pagefind-sort="data: 2026-10-03T14:06:00"' in html
    # titlul si rezumatul sunt indexate; etichetele de incredere si meta NU (ar da zgomot)
    assert '<h1 data-pagefind-body data-pagefind-weight="3">Guvernul a aprobat bugetul</h1>' in html
    assert '<p class="body" data-pagefind-body>Rezumatul scris de noi despre buget.</p>' in html
    assert 'data-pagefind-body' not in html.split('<h1 data-pagefind-body')[0]


def test_anuntul_oficial_primeste_filtrele_de_cautare_rapida():
    """Butoanele „Concursuri/Hotărâri/Achiziții/Toate oficiale" citesc filtrele astea."""
    articol = _articol("anunt", categorie="local", titlu="Concurs de recrutare")
    articol.update({
        "model": "B", "teaser": "", "synthesis": "", "source_name": "Primăria X",
        "original_link": "https://example.test/a", "sources": [], "first_source": None,
        "anunt_fara_corp": True, "ai_generat": False, "art_path": None, "art_webp": None,
        "lead_credit": None, "photo_path": None, "photo_webp": None, "art_style": None,
        "published": "2026-10-03T14:06:00+00:00", "tip_anunt": "concursuri",
        "publicitar_la_sursa": False, "updated_human": "",
    })
    html = render._env().get_template("article.html").render(**render._base_ctx(
        "/local/anunt/", a=articol, active_cat="local", topics=[], people=[], related=[]))
    assert 'data-pagefind-filter="tip: concursuri"' in html
    assert 'data-pagefind-filter="oficial: da"' in html


def test_pagina_de_cautare_arata_spre_indexul_generat_de_pipeline():
    """Sablonul si modulul Python trebuie sa cada la nume de director; altfel 404 pe live."""
    html = render._env().get_template("search.html").render(**render._base_ctx(
        "/cauta/", search_count=1200, search_days=config.ARTICLE_TTL_DAYS))
    assert f'data-pagefind="/{pagefind_index.SUBDIR}/"' in html
    assert 'data-index="/search-index.json"' in html
    assert 'data-result-limit="50"' in html
    assert "static/search.js" in html
    # promisiunea publica: aria acoperita si regula „fara rezultate umplutura"
    assert "1200 știri păstrate în ultimele" in html
    assert "nu completăm lista cu rezultate aproximative" in html
    assert "JavaScript" in html   # <noscript>: cautarea e client-side, o spunem, nu ascundem


# --- poarta de build ---------------------------------------------------------------
def test_verifica_pica_daca_bundleul_e_incomplet(tmp_path):
    """Cazul negativ al portii din `tests.yml`: un index gol nu are voie sa treaca."""
    assert pagefind_index.verifica(str(tmp_path)) == 1
    (tmp_path / pagefind_index.SUBDIR).mkdir()
    assert pagefind_index.verifica(str(tmp_path)) == 1


def test_verifica_pica_daca_fragmentele_raman(tmp_path):
    """Exact regresia pe care o apara bugetul: fragmente uitate in bundle."""
    radacina = tmp_path / pagefind_index.SUBDIR
    (radacina / "index").mkdir(parents=True)
    for nume in ("pagefind.js", "pagefind-entry.json", "pagefind-worker.js"):
        (radacina / nume).write_text("x")
    (radacina / "pagefind-entry.json").write_text(
        json.dumps({"languages": {"ro": {"page_count": 10}}}))
    _scrie_fragment(str(tmp_path), "ro_abc1234", "/local/un-slug/")
    assert pagefind_index.verifica(str(tmp_path)) == 1


# --- cap la cap, pe output-ul real -------------------------------------------------
@pytest.mark.skipif(pagefind_index.binar() is None,
                    reason="binarul Pagefind nu e instalat (pip install pagefind-bin)")
def test_randarea_reala_produce_index_fara_fragmente(output_randat):
    """End-to-end pe fixtura de randare: ce scrie pipeline-ul chiar se poate verifica.

    Nu e o reimplementare a logicii — e `output/` produs de `generator.main --render-only`,
    adica exact ce publica Cloudflare.
    """
    radacina = os.path.join(output_randat, pagefind_index.SUBDIR)
    assert os.path.isfile(os.path.join(radacina, "pagefind.js"))
    assert os.path.isfile(os.path.join(radacina, "pagefind-entry.json"))
    assert not os.path.isdir(os.path.join(radacina, "fragment")), (
        "fragmentele au ramas in bundle: ar sparge plafonul de fisiere al gazdei")
    assert pagefind_index.verifica(output_randat) == 0

    # Indexul nu e gol si acopera articolele publicate, nu sablonul de pagina.
    pagini = pagefind_index._pagini_indexate(output_randat)
    assert pagini >= 100, f"indexul are doar {pagini} pagini"

    with open(os.path.join(output_randat, "search-index.json"), encoding="utf-8") as fh:
        intrari = json.load(fh)["a"]
    assert intrari, "mapa de rezultate e goala"
    cu_id = [e for e in intrari if e[5]]
    # Fiecare articol publicat are pagina si deci fragment la indexare; un id lipsa inseamna
    # ca URL-ul calculat aici nu mai e cel scris pe disc (regresie de slug/categorie).
    assert len(cu_id) == len(intrari), (
        f"{len(intrari) - len(cu_id)} articole fara id Pagefind")
    assert len({e[5] for e in cu_id}) == len(cu_id), "id-uri duplicate in mapa"
