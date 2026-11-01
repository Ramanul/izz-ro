"""Masurarea oglinzii, rescrierea paginilor si plafonul automat.

Testele de capat la capat ruleaza pe un repo git REAL, cu clona fara fisiere si push obisnuit,
fiindca exact combinatia asta (bare + shallow + partial + fast-import) e partea care nu se
poate dovedi prin citire. Pe `file://` nu exista GitHub, deci retea si autentificare raman
neacoperite aici; ele se verifica la prima rulare reala.
"""
import subprocess
from datetime import date

import pytest

from tools import curata_oglinda as curata
from tools import masoara_oglinda as masurare

AZI = date(2026, 11, 5)
COPERTA = "https://izz.ro/local/a-1/cover.jpg?v=abc123"
PAGINA_CU_IMAGINI = f"""<html><head>
<meta property="og:image" content="{COPERTA}">
<meta name="twitter:image" content="{COPERTA}">
<script type="application/ld+json">{{"datePublished": "2026-09-20T08:00:00+00:00", "image": ["{COPERTA}"]}}</script>
</head><body><article>
  <h1>Titlu</h1>
  <figure class="article-art-fig">
    <picture>
      <source srcset="/local/a-1/photo.webp?v=11" type="image/webp">
      <img class="article-art" src="/local/a-1/photo.jpg?v=22" alt="Nume">
    </picture>
    <figcaption class="art-credit">Foto: Autor · Wikimedia Commons · CC BY 4.0</figcaption>
  </figure>
  <p>Textul articolului.</p>
</article></body></html>
"""
PAGINA_CURATA = """<html><head><meta property="og:image" content="https://izz.ro/og/local.jpg?v=9">
<script type="application/ld+json">{"datePublished": "2026-10-20T08:00:00+00:00"}</script>
</head><body><article><figure class="arhiva-foto"><img src="/portraits/x.webp"></figure></article></body></html>
"""
PAGINARE_VECHE = ('<article class="card"><a class="card-media card-media--fullbleed" href="/local/a-1/" '
                  'tabindex="-1"><picture><source srcset="/local/a-1/photo.webp?v=1"><img src="/local/a-1/photo.jpg?v=2">'
                  '</picture></a>\n  <p class="card-credit">Foto: Autor</p><h3>Titlu</h3></article>')


def test_rescrierea_scoate_toate_referintele():
    noua = curata.rescrie_pagina(PAGINA_CU_IMAGINI)
    assert not curata.REFERINTA.search(noua)
    assert noua.count("https://izz.ro/og/local.jpg") == 3
    assert "art-credit" not in noua and "<figure" not in noua
    assert "<p>Textul articolului.</p>" in noua


def test_pagina_fara_imagini_ramane_identica_la_octet():
    assert curata.rescrie_pagina(PAGINA_CURATA) == PAGINA_CURATA


def test_cardul_vechi_pierde_imaginea_si_creditul():
    noua = curata.rescrie_pagina(PAGINARE_VECHE)
    assert not curata.REFERINTA.search(noua)
    assert "card-credit" not in noua and "<h3>Titlu</h3>" in noua


@pytest.mark.parametrize("cale,e_imagine", [
    ("local/a-1/cover.jpg", True), ("extern/b/photo.webp", True), ("sport/c/art.jpg", True),
    ("leads/x.jpg", False), ("portraits/x.webp", False), ("og/local.jpg", False),
    ("local/a-1/index.html", False), ("static/cover.jpg", False), ("subiect/x/photo.jpg", False),
])
def test_doar_imaginile_de_articol_sunt_vizate(cale, e_imagine):
    assert bool(curata.IMAGINE.fullmatch(cale)) is e_imagine


@pytest.mark.parametrize("cale,e_articol", [
    ("local/a-1/index.html", True), ("local/130/index.html", False),
    ("subiect/x/index.html", False), ("local/index.html", False),
])
def test_plafonul_taie_doar_pagini_de_articol(cale, e_articol):
    assert bool(curata.ARTICOL.fullmatch(cale)) is e_articol


@pytest.mark.parametrize("mb,stare", [(900, "ok"), (901, "avertizare"), (950, "avertizare"),
                                      (951, "taiere"), (980, "taiere"), (981, "rosu")])
def test_pragurile_garzii(mb, stare):
    assert masurare.verdict(mb * masurare.MB) == stare


def test_masurarea_nu_are_voie_sa_ramana_trunchiata():
    def api(cale):
        if cale.endswith(f"trees/{masurare.RAMURA}"):
            return {"truncated": False, "tree": [{"path": "a.txt", "type": "blob", "size": 5, "sha": "1"},
                                                 {"path": "local", "type": "tree", "sha": "2"}]}
        if cale.endswith("trees/2?recursive=1"):
            return {"truncated": True, "tree": []}
        if cale.endswith("trees/2"):
            return {"truncated": False, "tree": [{"path": "b.html", "type": "blob", "size": 7, "sha": "3"},
                                                 {"path": "x", "type": "tree", "sha": "4"}]}
        return {"truncated": False, "tree": [{"path": "c.html", "type": "blob", "size": 11, "sha": "5"}]}

    assert masurare.arbore(api) == {"a.txt": 5, "local/b.html": 7, "local/x/c.html": 11}


def test_slugul_neobisnuit_nu_scapa_de_verificare():
    html = '<img src="/local/Slug_Vechi/photo.jpg">'
    assert curata.IMAGINE.fullmatch("local/Slug_Vechi/photo.jpg") and curata.REFERINTA.search(html)


def test_masurarea_refuza_o_coborare_fara_sfarsit(monkeypatch):
    monkeypatch.setattr(masurare, "MAX_APELURI", 3)
    fiu = {"truncated": False, "tree": [{"path": f"d{i}", "type": "tree", "sha": str(i)} for i in range(9)]}

    def api(cale):
        return {"truncated": True, "tree": []} if cale.endswith("recursive=1") else fiu

    with pytest.raises(RuntimeError, match="peste 3"):
        masurare.arbore(api)


def test_masurarea_refuza_o_radacina_trunchiata():
    with pytest.raises(RuntimeError):
        masurare.arbore(lambda _cale: {"truncated": True, "tree": []})


def test_taierea_incepe_cu_cele_mai_vechi():
    pagini = [("2026-10-01", "local/c/index.html", 10), ("2026-09-01", "local/a/index.html", 10),
              ("2026-09-02", "local/b/index.html", 10), *[("2026-10-02", f"local/p{i}/index.html", 1)
                                                          for i in range(5)]]
    assert curata.alege_de_taiat(pagini, 15, AZI) == (["local/a/index.html", "local/b/index.html"], 20)


def test_taierea_refuza_paginile_recente():
    with pytest.raises(curata.Refuz, match="ultimele 21 zile"):
        curata.alege_de_taiat([("2026-10-20", "local/a/index.html", 10)], 5, AZI)


def test_taierea_refuza_cand_nu_ajunge():
    with pytest.raises(curata.Refuz, match="elibereaza doar"):
        curata.alege_de_taiat([("2026-09-01", "local/a/index.html", 10)], 50, AZI)


def test_taierea_refuza_o_arhiva_golita():
    pagini = [(f"2026-09-{i + 1:02d}", f"local/p{i}/index.html", 10) for i in range(10)]
    with pytest.raises(curata.Refuz, match="peste 30%"):
        curata.alege_de_taiat(pagini, 40, AZI)


def _git(cwd, *argumente):
    return subprocess.run(["git", *argumente], cwd=cwd, check=True, capture_output=True).stdout.decode().strip()


@pytest.fixture
def oglinda(tmp_path):
    """Un `gh-pages` adevarat, servit ca remote `file://`, cu filtrare permisa ca pe GitHub."""
    lucru = tmp_path / "lucru"
    lucru.mkdir()
    _git(lucru, "init", "-q", "-b", masurare.RAMURA)
    _git(lucru, "config", "user.email", "t@example.org")
    _git(lucru, "config", "user.name", "t")
    fisiere = {
        "og/local.jpg": "o", "leads/x.jpg": "l", "portraits/x.webp": "p",
        "local/a-1/index.html": PAGINA_CU_IMAGINI, "local/a-1/cover.jpg": "c" * 500,
        "local/a-1/photo.jpg": "f" * 500, "local/a-1/photo.webp": "w" * 500,
        "local/orfan/cover.jpg": "x" * 500, "local/b-2/index.html": PAGINA_CURATA,
        "local/130/index.html": PAGINARE_VECHE,
    }
    for cale, continut in fisiere.items():
        tinta = lucru / cale
        tinta.parent.mkdir(parents=True, exist_ok=True)
        tinta.write_text(continut, encoding="utf-8", newline="\n")
    _git(lucru, "add", "-A")
    _git(lucru, "commit", "-qm", "deploy")
    goala = tmp_path / "oglinda.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(lucru), str(goala)], check=True)
    _git(goala, "config", "uploadpack.allowFilter", "true")
    _git(goala, "config", "uploadpack.allowAnySHA1InWant", "true")
    return goala


def test_curatarea_publica_un_commit_normal(oglinda):
    inainte = _git(oglinda, "rev-parse", masurare.RAMURA)
    uri = oglinda.as_uri()
    rezultat = curata.curata_imagini(uri, aplica=True, tinta=uri)
    assert (rezultat["imagini"], rezultat["pagini"]) == (4, 2)

    assert _git(oglinda, "rev-parse", f"{masurare.RAMURA}~1") == inainte   # fara rescriere de istoric
    ramase = _git(oglinda, "ls-tree", "-r", "--name-only", masurare.RAMURA).splitlines()
    assert not [c for c in ramase if curata.IMAGINE.fullmatch(c)]
    assert {"og/local.jpg", "leads/x.jpg", "portraits/x.webp"} <= set(ramase)
    assert not curata.REFERINTA.search(_git(oglinda, "show", f"{masurare.RAMURA}:local/a-1/index.html"))
    assert not curata.REFERINTA.search(_git(oglinda, "show", f"{masurare.RAMURA}:local/130/index.html"))

    # A doua rulare nu mai are ce face, deci nu adauga un commit gol.
    assert curata.curata_imagini(uri, aplica=True, tinta=uri)["commit"] is None


def test_simularea_nu_publica_nimic(oglinda):
    inainte = _git(oglinda, "rev-parse", masurare.RAMURA)
    uri = oglinda.as_uri()
    assert curata.curata_imagini(uri, aplica=False, tinta=uri)["imagini"] == 4
    assert _git(oglinda, "rev-parse", masurare.RAMURA) == inainte


def test_refuza_daca_ramane_o_referinta_necunoscuta(oglinda, tmp_path):
    lucru = tmp_path / "al-doilea"
    subprocess.run(["git", "clone", "-q", str(oglinda), str(lucru)], check=True)
    _git(lucru, "config", "user.email", "t@example.org")
    _git(lucru, "config", "user.name", "t")
    (lucru / "local" / "c-3").mkdir()
    (lucru / "local" / "c-3" / "index.html").write_text(
        '<img src="/local/a-1/photo.jpg">', encoding="utf-8")
    _git(lucru, "add", "-A")
    _git(lucru, "commit", "-qm", "sablon necunoscut")
    _git(lucru, "push", "-q", "origin", masurare.RAMURA)
    inainte = _git(oglinda, "rev-parse", masurare.RAMURA)
    uri = oglinda.as_uri()
    with pytest.raises(curata.Refuz, match="dupa rescriere"):
        curata.curata_imagini(uri, aplica=True, tinta=uri)
    assert _git(oglinda, "rev-parse", masurare.RAMURA) == inainte


def test_plafonul_sterge_directorul_paginii_vechi(oglinda, monkeypatch):
    monkeypatch.setattr(curata, "MAX_FRACTIE", 1.0)
    lucru = oglinda.parent / "lucru"
    (lucru / "local/130/index.html").write_text("<p>Arhiva fara linkuri catre pagina taiata</p>")
    _git(lucru, "add", "-A")
    _git(lucru, "commit", "-qm", "paginare independenta")
    _git(lucru, "push", "-q", str(oglinda), masurare.RAMURA)
    uri = oglinda.as_uri()
    marimi = {"local/a-1/index.html": 130 * masurare.MB, "local/b-2/index.html": 40 * masurare.MB,
              "portraits/x.webp": 780 * masurare.MB}
    rezultat = curata.taie_la_plafon(uri, True, marimi, AZI.replace(month=12), tinta=uri)
    assert rezultat["sterse"] == ["local/a-1"]
    ramase = _git(oglinda, "ls-tree", "-r", "--name-only", masurare.RAMURA).splitlines()
    assert "local/b-2/index.html" in ramase and not [c for c in ramase if c.startswith("local/a-1/")]
    assert "local/130/index.html" in ramase    # paginarea nu e arhiva, nu se taie


def test_plafonul_refuza_linkurile_ramase_fara_sa_publice(oglinda, monkeypatch):
    monkeypatch.setattr(curata, "MAX_FRACTIE", 1.0)
    inainte = _git(oglinda, "rev-parse", masurare.RAMURA)
    uri = oglinda.as_uri()
    marimi = {"local/a-1/index.html": 130 * masurare.MB, "portraits/x.webp": 780 * masurare.MB}
    with pytest.raises(curata.Refuz, match="referinta locala ramasa in local/130/index.html"):
        curata.taie_la_plafon(uri, True, marimi, AZI.replace(month=12), tinta=uri)
    assert _git(oglinda, "rev-parse", masurare.RAMURA) == inainte


@pytest.mark.parametrize("cale,html", [
    ("index.html", '<a href=/local/a-1/?x=1#sus>Articol</a>'),
    ("local/130/index.html", '<a href="../a-1/">Articol</a>'),
    ("index.html", '<img srcset="/og/local.jpg 1x, /local/a-1/photo.webp 2x">'),
    ("sitemap.xml", '<url><loc>https://ramanul.github.io/local/a-1/</loc></url>'),
])
def test_verifica_legaturi_refuza_tinte_locale(cale, html):
    with pytest.raises(curata.Refuz, match="referinta locala ramasa"):
        curata.verifica_legaturi(html.encode(), cale, {"local/a-1"})


def test_legaturile_canonice_si_articolele_ramase_nu_sunt_sterse():
    curata.verifica_legaturi(
        b'<a href="https://izz.ro/local/a-1/">Original</a><a href="/local/b-2/">Ramas</a>',
        "index.html", {"local/a-1"})


def test_masurarea_poate_fixa_versiunea():
    cereri = []

    def api(cale):
        cereri.append(cale)
        return {"tree": [{"path": "index.html", "type": "blob", "size": 12}]}

    assert masurare.arbore(api, ref="versiune-fixa") == {"index.html": 12}
    assert cereri == [f"repos/{masurare.REPO}/git/trees/versiune-fixa"]


def test_plafonul_refuza_masurarea_altei_versiuni(oglinda):
    inainte = _git(oglinda, "rev-parse", masurare.RAMURA)
    uri = oglinda.as_uri()
    with pytest.raises(curata.Refuz, match="dupa masurare"):
        curata.taie_la_plafon(uri, True, {"local/a-1/index.html": 960 * masurare.MB},
                             AZI, tinta=uri, parinte_asteptat="0" * 40)
    assert _git(oglinda, "rev-parse", masurare.RAMURA) == inainte


def test_comanda_plafon_transmite_versiunea_masurata(monkeypatch):
    cereri = []
    taieri = []
    marimi = {"local/a/index.html": 960 * masurare.MB}

    def arbore(*, ref):
        cereri.append(ref)
        return marimi

    def taie(sursa, aplica, masurate, azi, *, parinte_asteptat):
        taieri.append((sursa, aplica, masurate, parinte_asteptat))
        return {"eliberat": 120 * masurare.MB, "pagini": 1}

    monkeypatch.setattr(masurare, "cere_api", lambda cale: {"sha": "fix", "size": 100})
    monkeypatch.setattr(masurare, "arbore", arbore)
    monkeypatch.setattr(masurare, "publica_raport", lambda text: None)
    monkeypatch.setattr(curata, "taie_la_plafon", taie)
    assert curata.comanda_plafon(True) == 0
    assert cereri == ["fix"]
    assert taieri == [(curata.URL_CITIRE, True, marimi, "fix")]
