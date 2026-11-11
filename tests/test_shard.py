"""Impartirea in cioburi (`generator/shard.py`) -- regula de fisiere = regula de rutare.

Felia 0 (IZZ-0455) a masurat pe live: ruta mai specifica castiga, iar un fisier lipsa din ciob
NU cade pe Workerul principal. Deci orice nepotrivire intre unde punem fisierul si unde trimite
Cloudflare cererea devine un 404 pe o pagina care exista. Testele de aici apara exact asta.
"""
import json
import os

import pytest

from generator import config, shard


def _scrie(root, rel, text="x"):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


@pytest.fixture
def plan():
    return shard.plan()


@pytest.mark.parametrize("rel,asteptat", [
    ("index.html", "main"),
    ("static/styles.css", "main"),
    ("sitemap.xml", "main"),
    ("sport/index.html", "cat-sport"),            # /sport/ -> izz.ro/sport/*
    ("sport/2/index.html", "cat-sport"),
    ("sport/un-titlu/index.html", "cat-sport"),
    ("sport/un-titlu/photo.jpg", "cat-sport"),    # imaginea sta langa articol
    ("subiect/nicusor-dan/index.html", "subiect"),
    ("local/index.html", "main"),                 # /local/ nu intra pe izz.ro/local/i*
    ("local/10/index.html", "local-cifre"),       # paginarea e numerica
    ("local/accident-pe-dn1/index.html", "local-a"),
    ("local/primaria-cluj/index.html", "local-p"),
    ("local/cluj-arena/index.html", "local-bc"),
    ("local/zbor/index.html", "local-stuvwxyz"),
    ("local/feed.xml", "local-defghi"),           # izz.ro/local/f* o prinde, deci ciobul f
    ("local/_ceva/index.html", "main"),           # niciun grup -> ramane unde merge si cererea
    ("local/Accident/index.html", "main"),        # rutele sunt sensibile la majuscule
])
def test_assign_urmeaza_rutarea(plan, rel, asteptat):
    assert shard.assign(rel, plan) == asteptat


def test_fiecare_categorie_si_caracter_au_casa(plan):
    nume = {s["name"] for s in plan}
    for cat in config.CATEGORIES:
        if cat != "local":
            assert f"cat-{cat}" in nume, cat
    litere = "".join(config.LOCAL_SHARD_GROUPS)
    assert len(litere) == len(set(litere)), "un caracter e in doua grupuri de local/"
    assert set("abcdefghijklmnopqrstuvwxyz0123456789") <= set(litere)


def test_rutele_nu_se_suprapun(plan):
    prefixe = [p for s in plan for p in s["prefixes"]]
    assert len(prefixe) == len(set(prefixe))


def test_partition_nu_pierde_si_nu_dubleaza(tmp_path):
    src, dest = tmp_path / "output", tmp_path / "dist"
    fisiere = ["index.html", "404.html", "static/styles.css", "sport/index.html",
               "sport/a/index.html", "local/index.html", "local/arad/index.html",
               "local/3/index.html", "subiect/x/index.html"]
    for rel in fisiere:
        _scrie(str(src), rel, rel)
    man = shard.partition(str(src), str(dest))

    gasite = {}
    for s in man["shards"]:
        baza = dest / s["name"]
        for root, _, fs in os.walk(baza):
            for f in fs:
                rel = os.path.relpath(os.path.join(root, f), baza).replace(os.sep, "/")
                gasite.setdefault(rel, []).append(s["name"])
    # Fiecare fisier sursa exista exact o data; exceptiile sunt intentionate: 404.html in
    # fiecare ciob si `local/index.html`, care raspunde si la `/local/index.html` (ruta `local/i*`).
    for rel in fisiere:
        if rel not in ("404.html", "local/index.html"):
            assert len(gasite[rel]) == 1, (rel, gasite[rel])
    assert sorted(gasite["local/index.html"]) == ["local-defghi", "main"]
    assert (dest / "cat-sport" / "sport" / "a" / "index.html").read_text() == "sport/a/index.html"
    assert (dest / "local-a" / "local" / "arad" / "index.html").exists()
    # Fiecare ciob, chiar si gol, are propria pagina 404: ratarile nu cad pe principal, iar
    # setul de rute ramane stabil cand o categorie in insamantare e goala.
    for s in man["shards"]:
        if s["name"] != "main":
            assert (dest / s["name"] / "404.html").exists(), s["name"]
    auto = next(s for s in man["shards"] if s["name"] == "cat-auto")
    assert auto["file_count"] == 1

    scris = json.loads((dest / "shards.json").read_text(encoding="utf-8"))
    assert scris == man
    sport = next(s for s in man["shards"] if s["name"] == "cat-sport")
    # Fara ruta exacta, `izz.ro/sport` (fara bara) ar cadea pe principal, care nu are pagina.
    assert sport["routes"] == ["izz.ro/sport", "izz.ro/sport/*"]
    assert sport["file_count"] == 3   # index, a/index, 404
    cifre = next(s for s in man["shards"] if s["name"] == "local-cifre")
    assert "izz.ro/local/3*" in cifre["routes"] and "izz.ro/local/3" not in cifre["routes"]


def test_amprenta_se_schimba_doar_cu_continutul(tmp_path):
    src = tmp_path / "output"
    _scrie(str(src), "index.html")
    _scrie(str(src), "sport/a/index.html", "v1")
    _scrie(str(src), "auto/b/index.html", "v1")
    m1 = {s["name"]: s["tree_sha256"] for s in shard.partition(str(src), str(tmp_path / "d1"))["shards"]}
    _scrie(str(src), "sport/a/index.html", "v2")
    m2 = {s["name"]: s["tree_sha256"] for s in shard.partition(str(src), str(tmp_path / "d2"))["shards"]}
    assert m1["cat-sport"] != m2["cat-sport"]
    assert m1["cat-auto"] == m2["cat-auto"]   # ciobul neschimbat nu se republica (felia 2)


def test_plafonul_per_ciob_opreste_zgomotos(tmp_path):
    src = tmp_path / "output"
    _scrie(str(src), "index.html")
    for i in range(4):
        _scrie(str(src), f"sport/a{i}/index.html")
    with pytest.raises(RuntimeError, match="cat-sport=4"):   # fara 404.html in sursa
        shard.partition(str(src), str(tmp_path / "dist"), ceiling=3)
    # Manifestul pe disc inseamna impartire publicabila; la esec nu se scrie.
    assert not (tmp_path / "dist" / "shards.json").exists()


def test_dest_nu_poate_inghiti_sursa(tmp_path):
    src = tmp_path / "output"
    _scrie(str(src), "index.html")
    for dest in (src, src / "dist", tmp_path):
        with pytest.raises(ValueError):
            shard.partition(str(src), str(dest))
    assert (src / "index.html").exists()


def test_numele_cioburilor_sunt_unice(plan):
    nume = [s["name"] for s in plan]
    assert len(nume) == len(set(nume))


def test_radacina_se_replica_si_redirectele_se_filtreaza(tmp_path):
    src, dest = tmp_path / "output", tmp_path / "dist"
    for rel in ("index.html", "404.html", "build.json", "auto/a/index.html", "sport/b/index.html"):
        _scrie(str(src), rel, rel)
    _scrie(str(src), "_headers", "/*\n  X-Test: 1\n")
    _scrie(str(src), "_redirects",
           "# comentariu\n/auto/vechi /auto/a/ 301\n/tech/x /tech/y 301\n\n/sport/z /sport/b/ 301\n"
           "/sport /sport/ 301\n/zonal/* /judetean/:splat 301\n")
    man = shard.partition(str(src), str(dest))
    for nume in ("cat-auto", "cat-sport", "cat-tech"):
        for f in shard.REPLICATE:
            assert (dest / nume / f).exists(), (nume, f)
    assert (dest / "cat-auto" / "_redirects").read_text() == "/auto/vechi /auto/a/ 301\n"
    # `/sport` fara bara merge pe ruta exacta `izz.ro/sport`, deci regula e a ciobului.
    assert (dest / "cat-sport" / "_redirects").read_text() == "/sport/z /sport/b/ 301\n/sport /sport/ 301\n"
    assert not (dest / "cat-politic" / "_redirects").exists()
    # Principalul pastreaza doar regulile a caror sursa ramane pe `main` (ex. `/zonal/*`).
    assert (dest / "main" / "_redirects").read_text() == "/zonal/* /judetean/:splat 301\n"
    auto = next(s for s in man["shards"] if s["name"] == "cat-auto")
    assert auto["file_count"] == 5   # a/index, 404, _headers, build.json, _redirects


def test_configul_workerului_de_ciob(tmp_path):
    src, dest = tmp_path / "output", tmp_path / "dist"
    _scrie(str(src), "index.html")
    _scrie(str(src), "auto/a/index.html")
    shard.partition(str(src), str(dest))
    cfg = json.loads((dest / "izz-ro-cat-auto.config.json").read_text(encoding="utf-8"))
    assert cfg["name"] == "izz-ro-cat-auto"
    # Caile se rezolva fata de dist/, unde sta configul: `dist/../infra/...` e scriptul din repo.
    assert cfg["main"] == "../infra/worker-404-mirror.js"
    assert os.path.isfile(os.path.join("infra", "worker-404-mirror.js"))
    assert (dest / cfg["assets"]["directory"]).is_dir()
    assert cfg["assets"]["binding"] == "ASSETS"     # fallback-ul cheama env.ASSETS
    assert "not_found_handling" not in cfg["assets"]  # altfel ratarea nu invoca scriptul
    assert cfg["routes"] == [{"pattern": "izz.ro/auto", "zone_name": "izz.ro"},
                             {"pattern": "izz.ro/auto/*", "zone_name": "izz.ro"}]
    assert not (dest / "izz-ro-main.config.json").exists()


def test_compat_date_ca_la_principal():
    import re
    with open("wrangler.jsonc", encoding="utf-8") as fh:
        text = fh.read()
    assert re.search(r'"compatibility_date":\s*"([^"]+)"', text).group(1) == shard.COMPAT_DATE


def test_cioburile_live_exista_in_plan(plan):
    nume = {s["name"] for s in plan}
    # Lista goala e valida: e exact starea dupa o revenire.
    assert set(config.SHARDS_LIVE) <= nume
    assert len(config.SHARDS_LIVE) == len(set(config.SHARDS_LIVE))


def test_cli_refuza_fara_randare(tmp_path, capsys):
    assert shard.main(["--src", str(tmp_path / "gol"), "--dest", str(tmp_path / "d")]) == 1


def test_live_only_pastreaza_cioburile_neactivate_in_main(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SHARDS_LIVE", ["cat-auto"])
    src, dest = tmp_path / "output", tmp_path / "dist"
    for rel in ("index.html", "auto/a/index.html", "sport/b/index.html", "subiect/x/index.html"):
        _scrie(str(src), rel, rel)
    assert shard.main(["--src", str(src), "--dest", str(dest), "--live-only"]) == 0
    assert (dest / "cat-auto" / "auto" / "a" / "index.html").exists()
    # `sport` si `subiect` nu sunt in SHARDS_LIVE -> raman in `main`, unde merge cererea pe izz.ro.
    assert (dest / "main" / "sport" / "b" / "index.html").exists()
    assert (dest / "main" / "subiect" / "x" / "index.html").exists()
    assert not (dest / "cat-sport").exists()
    assert not (dest / "subiect").exists()


def test_workers_origin_for_comuta_doar_pe_workers_dev():
    shards = [{"name": "cat-sport", "prefixes": ["sport/"]},
              {"name": "local-a", "prefixes": ["local/a"]}]
    baza = "https://izz-ro.andifreelancer2.workers.dev"
    assert shard.workers_origin_for(baza, "/", shards) == baza
    assert shard.workers_origin_for(baza, "/static/styles.css?v=1", shards) == baza
    assert shard.workers_origin_for(baza, "/subiect/romania/", shards) == baza
    assert shard.workers_origin_for(baza, "/local/", shards) == baza
    assert (shard.workers_origin_for(baza, "/sport/meci/photo.jpg?v=2", shards)
            == "https://izz-ro-cat-sport.andifreelancer2.workers.dev")
    assert (shard.workers_origin_for(baza, "/local/arad/", shards)
            == "https://izz-ro-local-a.andifreelancer2.workers.dev")
    # Pe domeniul public sau alt host, rutarea Cloudflare face singura treaba.
    assert shard.workers_origin_for("https://izz.ro", "/sport/meci/", shards) == "https://izz.ro"
