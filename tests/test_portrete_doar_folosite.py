"""Portretele: in output ajung DOAR cele pe care o pagina le arata.

DE CE EXISTA. `_load_portraits()` facea `shutil.copytree(media/portraits -> output/portraits)`
la fiecare randare, deci publica intregul cache comis. Masurat 2026-10-03 pe o randare reala
(`python -m generator.main --render-only` + scan pe tot `output/`):

    portrete copiate in output/ : 1789
    portrete REFERITE in HTML   :  661   (din 11.114 pagini)
    diferenta                   : 1128   = 6,3% din plafonul Workers Free de 20.000

Plafonul ala e resursa care tine `ARTICLE_TTL_DAYS` la 12 (vezi comentariul din
`generator/config.py` de langa cifra): fiecare fisier eliberat e arhiva care poate trai.
Deci asta nu e curatenie cosmetica, e buget de publicare.

Ce apara testele de aici:
  1. bijectia — fiecare `<img>` de portret are fisier, fiecare fisier e referit;
  2. forma sursei — `copytree` pe directorul de portrete nu se intoarce;
  3. cazul negativ — un portret al carui fisier lipseste NU produce un `<img>` care da 404.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER_PY = os.path.join(ROOT, "generator", "render.py")


def test_copytree_pe_portrete_nu_se_intoarce():
    """Garda pe FORMA, ca `test_determinism_render`: copytree-ul e sursa risipei."""
    with open(RENDER_PY, encoding="utf-8") as fh:
        sursa = fh.read()
    assert 'copytree(src, os.path.join(OUT_DIR, "portraits")' not in sursa, (
        "portretele s-au intors la copytree: output-ul publica din nou intregul cache "
        "(1.128 de fisiere nefolosite masurate). Copia se face la cerere, in `_portret`.")
    # Functia care copiaza la cerere trebuie sa existe — altfel garda de sus trece
    # trivial prin stergerea feature-ului.
    assert "def _portret(" in sursa
    assert sursa.count("_portret(portraits, ") == 2, (
        "ambele locuri care folosesc portrete (pagina de subiect + 'In imagini' pe articol) "
        "trebuie sa treaca prin `_portret`, altfel unul dintre ele publica portretul "
        "fara sa-i copieze fisierul")


def test_portret_copiaza_doar_fisierul_cerut(tmp_path, monkeypatch):
    """Un singur portret cerut => un singur fisier in OUT_DIR, nu tot directorul."""
    media = tmp_path / "media"
    (media / "portraits").mkdir(parents=True)
    for i in range(4):
        # > 3000 octeti: `_use_media` refuza fisierele sub prag ca fiind trunchiate.
        (media / "portraits" / f"pers-{i}.jpg").write_bytes(b"x" * 4000)
    out = tmp_path / "output"
    out.mkdir()
    monkeypatch.setattr(render, "MEDIA_DIR", str(media))
    monkeypatch.setattr(render, "OUT_DIR", str(out))

    cache = {f"persoana {i}": {"name": f"Persoana {i}", "img": f"portraits/pers-{i}.jpg"}
             for i in range(4)}
    rec = render._portret(cache, "Persoana 2")

    assert rec is not None
    assert (out / "portraits" / "pers-2.jpg").exists()
    copiate = sorted(p.name for p in (out / "portraits").iterdir())
    assert copiate == ["pers-2.jpg"], (
        f"s-au copiat {copiate} — astept doar fisierul cerut; restul sunt exact "
        "fisierele care umflau plafonul gazdei")


def test_portret_fara_fisier_nu_da_img_spat():
    """Cazul negativ: portret in cache, fisier lipsa pe disc => None, nu `<img>` 404.

    Fara asta, „copiem doar ce e cerut" ar putea publica o trimitere spre un fisier care
    nu exista — o regresie vizibila pentru cititor in locul uneia de buget.
    """
    rec = render._portret({"nimeni": {"name": "Nimeni", "img": "portraits/nimeni.jpg"}},
                          "Nimeni")
    assert rec is None


def test_portret_cache_fara_img_e_refuzat():
    """`img` lipsa/vid in cache nu trebuie sa ceara o copie si nu trebuie sa dea exceptie."""
    assert render._portret({"x": {"name": "X"}}, "X") is None
    assert render._portret({"x": {"name": "X", "img": ""}}, "X") is None


def test_portret_necunoscut_intoarce_none():
    assert render._portret({}, "Cineva") is None


def test_bijectie_portrete_referite_vs_fisiere():
    """Pe output-ul RANDAT: referinte == fisiere, in ambele directii.

    Test conditionat de existenta `output/` (randarea dureaza ~30 s si nu ruleaza in CI la
    fiecare rulare); cand lipseste, se sare — dar cand exista, verifica exact proprietatea
    care a fost masurata manual la reparatie.
    """
    out = os.path.join(ROOT, "output")
    dir_portrete = os.path.join(out, "portraits")
    if not os.path.isdir(out) or not os.path.isdir(dir_portrete):
        pytest.skip("output/ nu e randat — ruleaza `python -m generator.main --render-only`")
    referite = set()
    tipar = re.compile(r"/portraits/([^\"'?\s]+)")
    for dirpath, _, files in os.walk(out):
        for f in files:
            if not f.endswith(".html"):
                continue
            with open(os.path.join(dirpath, f), encoding="utf-8", errors="replace") as fh:
                referite.update(tipar.findall(fh.read()))
    pe_disc = set()
    for dirpath, _, files in os.walk(dir_portrete):
        for f in files:
            pe_disc.add(os.path.relpath(os.path.join(dirpath, f), dir_portrete)
                        .replace(os.sep, "/"))
    assert not (referite - pe_disc), (
        f"{len(referite - pe_disc)} portrete referite in HTML nu au fisier — cititorul "
        "vede o imagine sparta")
    assert not (pe_disc - referite), (
        f"{len(pe_disc - referite)} portrete publicate fara nicio referinta — exact risipa "
        "de plafon pe care a reparat-o `_portret`")
