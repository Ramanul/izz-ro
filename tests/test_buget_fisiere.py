"""Bugetul de fisiere al output-ului (`render._articole_publicabile` + plafonul dur).

De ce exista testul: pe 2026-08-21 output-ul a trecut plafonul de fisiere al gazdei,
deploy-ul a inceput sa fie refuzat si site-ul a stat 21 de ore pe un release vechi, fara ca
nimic din pipeline sa raporteze rosu la timp -- jobul de continut trecea verde, iar
`release-probe` pica 25 de minute mai tarziu cu "izz.ro serveste 63bcc9bd0965, care nu
include 51fe7790c026".

Din 2026-09-22 contul e pe Workers FREE, deci plafonul e 20.000, nu 100.000: aceeasi
greseala costa acum de cinci ori mai repede.

Fiecare garda de aici are si un caz NEGATIV: o garda care nu poate pica e mai rea decat
niciuna (IZZ-0177).
"""
import datetime
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config          # noqa: E402
from generator.render import _articole_publicabile  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Plafonul real al gazdei. Contul se intoarce pe Workers FREE din 2026-09-22 (decizie
# proprietar 2026-09-09), unde plafonul e 20.000 de fisiere per versiune de Worker. Citit din
# documentatia Cloudflare pe 2026-09-09, prin conectorul Cloudflare al sesiunii:
# developers.cloudflare.com/workers/platform/limits/#static-assets
# Cifra de 100.000 era a planului PAID si NU mai descrie gazda.
PLAFON_GAZDA = 20000


# Fractia din stare care ajunge chiar PUBLICATA: dedup-ul de eveniment si poarta de calitate
# scot restul inainte de randare. MASURAT 2026-09-09 pe o randare completa: 12.475 de pagini
# scrise din 14.821 de articole incarcate din stare = 0,842. Se remasoara cand se schimba
# dedup-ul sau poarta -- fara ea, gardele de mai jos ar compara plafonul cu un numar cu 18%
# mai mare decat ce se scrie efectiv pe disc, adica ar pica pe o randare perfect sanatoasa.
FRACTIA_PUBLICATA = 0.842


def _stare() -> list:
    with open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _in_fereastra_ttl(articole: list) -> int:
    """Cate articole ar ramane publicate dupa `state.expire()` la TTL-ul configurat.

    Fereastra se masoara fata de cel mai recent articol din stare, nu fata de ceasul de
    azi: altfel testul ar deveni verde prin simpla trecere a timpului pe o stare inghetata,
    ceea ce e exact opusul unui tripwire.
    """
    date = [(a.get("published") or "")[:10] for a in articole]
    date = [d for d in date if d]
    if not date:
        return 0
    ultima = datetime.date.fromisoformat(max(date))
    prag = (ultima - datetime.timedelta(days=config.ARTICLE_TTL_DAYS)).isoformat()
    return sum(1 for d in date if d > prag)


def test_bugetul_configurat_sta_sub_plafonul_gazdei():
    """Bugetul trebuie sa lase marja sub plafonul gazdei."""
    assert config.OUTPUT_FILE_BUDGET < PLAFON_GAZDA, (
        f"OUTPUT_FILE_BUDGET={config.OUTPUT_FILE_BUDGET} nu lasa marja sub plafonul "
        f"gazdei ({PLAFON_GAZDA}). Ridica-l doar odata cu plafonul, nu ca sa incapa.")


def test_cand_incape_tot_nu_se_taie_niciun_articol():
    assert _articole_publicabile(1000, budget=10_000, reserve=1_000) == 1000


def test_NEGATIV_peste_buget_se_taie_pana_intra():
    """Cazul negativ: bugetul mic taie articole, si taie EXACT cat trebuie."""
    # buget 5.000, rezerva 1.000 -> 4.000 libere; 1.200 dintre articole platesc si coperta
    n = _articole_publicabile(10_000, budget=5_000, reserve=1_000)
    assert n == 4_000 - config.OG_COVER_MAX_ARTICLES
    assert n + min(config.OG_COVER_MAX_ARTICLES, n) <= 4_000


def test_NEGATIV_cand_nici_copertile_nu_incap_fiecare_articol_plateste_doua_fisiere():
    """Sub dublul ferestrei de coperti, fiecare articol publicat costa pagina + coperta."""
    n = _articole_publicabile(10_000, budget=1_500, reserve=1_000)
    assert n == 250, "500 de fisiere libere / 2 = 250 de articole"
    assert n + min(config.OG_COVER_MAX_ARTICLES, n) <= 500


def test_NEGATIV_rezerva_mai_mare_decat_bugetul_nu_devine_negativa():
    assert _articole_publicabile(500, budget=100, reserve=9_000) == 0


@pytest.mark.parametrize("n", [0, 1, 10, 500, 3000, 6000, 9000, 20_000])
def test_invariantul_tine_pe_tot_domeniul(n):
    """Nu se promite niciodata mai mult decat incape, si niciodata mai mult decat exista."""
    k = _articole_publicabile(n)
    assert 0 <= k <= n
    total = config.OUTPUT_NON_ARTICLE_RESERVE + k + min(config.OG_COVER_MAX_ARTICLES, k)
    assert total <= max(config.OUTPUT_FILE_BUDGET, config.OUTPUT_NON_ARTICLE_RESERVE)


def test_fereastra_TTL_incape_fara_sa_intervina_supapa():
    """Tripwire pe starea REALA: supapa e pentru accidente, nu pentru regimul normal.

    Cand pica, ingestul a crescut peste ce a fost masurat si fereastra publicata devine
    mai scurta decat `ARTICLE_TTL_DAYS` fara ca nimeni sa fi decis asta. Raspunsul e sa
    cobori TTL-ul (o decizie), nu sa ridici bugetul (o minciuna despre plafonul gazdei).
    """
    n = int(_in_fereastra_ttl(_stare()) * FRACTIA_PUBLICATA)
    assert _articole_publicabile(n) == n, (
        f"la TTL={config.ARTICLE_TTL_DAYS} s-ar publica {n} articole, dar in "
        f"OUTPUT_FILE_BUDGET={config.OUTPUT_FILE_BUDGET} cu rezerva "
        f"{config.OUTPUT_NON_ARTICLE_RESERVE} incap doar {_articole_publicabile(n)}. "
        f"Vezi specs/cloudflare-free-2026-09.md.")


def test_podeaua_absoluta_ramane_deasupra_ferestrei_TTL():
    """Chiar si fara nicio coperta, paginile trebuie sa incapa. Asta e limita dura."""
    n = _in_fereastra_ttl(_stare())
    maxim_pagini = config.OUTPUT_FILE_BUDGET - config.OUTPUT_NON_ARTICLE_RESERVE
    assert n <= maxim_pagini, (
        f"{n} articole in fereastra TTL, dar sub buget incap doar {maxim_pagini} pagini. "
        f"Aici nicio optimizare de imagini nu mai ajuta: trebuie TTL mai mic.")


def test_fereastra_de_coperti_nu_inghite_bugetul():
    """og:image propriu e un lux marginit: sub un sfert din ce ramane dupa rezerva."""
    liber = config.OUTPUT_FILE_BUDGET - config.OUTPUT_NON_ARTICLE_RESERVE
    assert 0 < config.OG_COVER_MAX_ARTICLES <= liber // 4, (
        f"OG_COVER_MAX_ARTICLES={config.OG_COVER_MAX_ARTICLES} din {liber} fisiere libere: "
        f"copertile incep sa concureze cu paginile de articol.")


# --- plafonul dur al gazdei -------------------------------------------------------
# Bugetul e tinta la care randarea taie; plafonul e punctul de la care Cloudflare refuza
# deploy-ul. Un `logging.error` NU opreste nimic: randarea iese cu cod 0, jobul de continut
# ramane verde si esecul reapare in `release-probe` 25 de minute mai tarziu. Peste plafon
# randarea trebuie sa moara zgomotos.

def test_bugetul_sta_sub_plafonul_dur():
    assert config.OUTPUT_FILE_BUDGET < config.OUTPUT_FILE_CEILING
    assert config.OUTPUT_FILE_CEILING <= PLAFON_GAZDA


def _scrie_fisiere(d, cate):
    for i in range(cate):
        (d / f"f{i}.html").write_text("x", encoding="utf-8")


def test_NEGATIV_peste_plafonul_gazdei_randarea_moare_zgomotos(tmp_path, monkeypatch):
    """Cazul negativ care conteaza: peste plafon NU se iese cu cod 0."""
    from generator import render
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "OUTPUT_FILE_CEILING", 3)
    monkeypatch.setattr(config, "OUTPUT_FILE_BUDGET", 2)
    _scrie_fisiere(tmp_path, 5)
    with pytest.raises(RuntimeError, match="peste plafonul gazdei"):
        render._write_build_metadata(0)


def test_diagnosticul_supravietuieste_esecului(tmp_path, monkeypatch):
    """build.json se scrie INAINTE de verdict, altfel esecul isi ascunde propria dovada."""
    from generator import render
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "OUTPUT_FILE_CEILING", 3)
    monkeypatch.setattr(config, "OUTPUT_FILE_BUDGET", 2)
    _scrie_fisiere(tmp_path, 5)
    with pytest.raises(RuntimeError):
        render._write_build_metadata(0)
    scris = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert scris["file_count"] == 6, "numarul care a declansat esecul trebuie sa ramana citibil"


def test_intre_buget_si_plafon_publicarea_merge_mai_departe(tmp_path, monkeypatch):
    """Marja stramta nu trebuie sa doboare publicarea cand deploy-ul ar trece oricum."""
    from generator import render
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "OUTPUT_FILE_BUDGET", 3)
    monkeypatch.setattr(config, "OUTPUT_FILE_CEILING", 50)
    _scrie_fisiere(tmp_path, 5)
    render._write_build_metadata(0)   # avertizeaza, dar nu ridica
    assert (tmp_path / "build.json").exists()
