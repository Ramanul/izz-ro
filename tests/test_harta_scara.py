"""Scara hărții: praguri absolute, benzi contigue, legenda care nu poate minți.

Defectul apărat aici a fost văzut pe LIVE (/static/harta-stiri/?q=Giroc, 4 oct 2026):
cuartilele unui maxim de 2 ieșeau [1, 1], iar legenda construită din ele afișa
„012-undefinedNaN-undefinedNaN+" — o scară care nu spune niciun număr. Verificarea nu are
nevoie de browser: pragurile ȘI etichetele benzilor sunt scrise în index.html, una lângă
alta, iar testul le pune față în față. Formula din JS e verificată textual pentru că ea
trebuie să fie exact „câte praguri sunt acoperite de număr".

Din 4 oct 2026 (F3) sunt DOUĂ scări, fiecare cu praguri absolute scrise în pagină:
`data-praguri` = volumul (1/6/15/30) și `data-praguri-locuitor` = aceleași știri raportate la
100.000 de locuitori (0,1/1/2/4). A doua are nevoie de un numitor, iar numitorul are sursă și
dată (`data/populatie.json`, INS 2021 agregat) — verificat tot aici, pentru că o scară relativă
cu un numitor inventat mută doar locul unde se minte. Grilele de afișare diferă (1, respectiv
0,1), iar etichetele benzilor trebuie să acopere EXACT grila, altfel un județ cu 0,96 știri la
100.000 ar apărea ca „1,0" colorat în banda „0,1–0,9".
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import geo  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "static", "harta-stiri", "index.html")
JS = os.path.join(ROOT, "static", "harta-stiri", "harta-stiri.js")


def _html() -> str:
    with open(HTML, encoding="utf-8") as fh:
        return fh.read()


def _js() -> str:
    with open(JS, encoding="utf-8") as fh:
        return fh.read()


# Fiecare scara: numele setului de benzi, pragurile, grila de afisare (pasul dintre valorile
# care pot ajunge pe ecran) si forma din JS care produce valoarea afisata.
SCARI = (
    ("volum", (1, 6, 15, 30), 1),
    ("locuitori", (0.1, 1, 2, 4), 0.1),
)


def _legenda() -> str:
    html = _html()
    block = re.search(r'<div id="map-legend".*?\n        </div>', html, re.S)
    assert block, "legenda lipsește din index.html"
    return block.group(0)


def _seturi() -> dict:
    """{nume: (praguri, etichete, clase)} pentru fiecare set de benzi din legendă.

    Seturile sunt secvențiale în pagină, deci fiecare se taie de la marcajul lui până la
    următorul marcaj — fără să se ghicească unde se închid span-urile imbricate.
    """
    text = _legenda()
    marker = '<span class="legend-bands" data-bands="'
    bucati = text.split(marker)[1:]
    seturi = {}
    for bucata in bucati:
        nume = bucata.split('"', 1)[0]
        atribute = text[text.index(marker + nume):]
        sfarsit = len(atribute)
        for alt in SCARI:
            if alt[0] == nume:
                continue
            urm = atribute.find(marker + alt[0])
            if urm != -1:
                sfarsit = min(sfarsit, urm)
        corp = atribute[:sfarsit]
        cells = corp.split('<span class="legend-step">')[1:]
        labels, classes = [], []
        for cell in cells:
            step = re.match(r'<span class="swatch (h\d)"[^>]*></span>([^<]+)</span>', cell.strip())
            assert step, f"bandă de legendă ilizibilă în {nume}: {cell[:80]!r}"
            classes.append(step.group(1))
            labels.append(step.group(2).strip())
        seturi[nume] = (labels, classes)
    assert set(seturi) == {nume for nume, _, _ in SCARI}, f"seturi de benzi: {sorted(seturi)}"
    return seturi


def _praguri(nume: str) -> list[float]:
    atribute = {"volum": "data-praguri", "locuitori": "data-praguri-locuitor"}[nume]
    match = re.search(atribute + r'="([^"]+)"', _legenda())
    assert match, f"legenda nu declară {atribute} — JS-ul ar cădea pe o constantă paralelă"
    return [float(v) for v in match.group(1).split(",")]


def test_pragurile_sunt_absolute_si_crescatoare():
    for nume, _, _ in SCARI:
        praguri = _praguri(nume)
        assert praguri == sorted(set(praguri)), f"{nume}: praguri neordonate sau duplicate: {praguri}"
        assert all(p > 0 for p in praguri), f"{nume}: prag zero sau negativ: {praguri}"
        assert len(praguri) == 4, f"{nume}: scara are 4 praguri (5 benzi, h0..h4), nu {len(praguri)}"


def _text_valoare(valoare: float, grila: float) -> str:
    return f"{valoare:.0f}" if grila == 1 else f"{valoare:.1f}".replace(".", ",")


def test_benzile_legendei_acopera_de_la_0_fara_goluri():
    """Fiecare scară acoperă 0..∞, contiguu, pe PROPRIA grilă de afișare."""
    seturi = _seturi()
    for nume, praguri_decl, grila in SCARI:
        labels, classes = seturi[nume]
        praguri = _praguri(nume)
        assert tuple(praguri) == tuple(float(p) for p in praguri_decl), (
            f"{nume}: pragurile declarate în codul testului nu mai sunt cele din pagină")
        assert classes == ["h0", "h1", "h2", "h3", "h4"], (nume, classes)
        assert labels[0] == "0", (nume, labels[0])
        for i, start in enumerate(praguri, start=1):
            if i < len(praguri):
                end = round(praguri[i] - grila, 6)
                expected = f"{_text_valoare(start, grila)}\u2013{_text_valoare(end, grila)}"
                assert labels[i] == expected, (
                    f"{nume}: banda h{i} ar trebui sa fie {expected}, nu {labels[i]} — "
                    "eticheta si pragul s-au contrazis pe grila de afisare")
                assert end >= start, f"{nume}: banda h{i} e goala ({labels[i]})"
            else:
                # Banda deschisa se scrie scurt („30+", „4+"): acopera tot de la prag in sus,
                # deci zeroul zecimal nu adauga informatie.
                limita = f"{start:g}".replace(".", ",")
                expected = f"{limita}+"
                assert labels[i] == expected, f"{nume}: ultima banda ar trebui {expected}, nu {labels[i]}"


def test_prima_banda_a_ratei_nu_poate_inghiti_o_stire_existenta():
    """Sub pragul de 0,1 nu are ce sa cada: cel mai mic județ are ~193.000 de locuitori, deci
    chiar o singura știre da 0,5 la 100.000, adica peste prag. Altfel un eveniment real ar fi
    colorat ca „zero știri" — exact minciuna pe care o repară scara."""
    prag = _praguri("locuitori")[0]
    with open(os.path.join(ROOT, "static", "harta-stiri", "data", "populatie.json"),
              encoding="utf-8") as fh:
        populatii = json.load(fh)["judete"]
    cel_mai_mic = min(populatii.values())
    rata_minima = 1 / cel_mai_mic * 100000
    assert round(rata_minima, 1) >= prag, (
        f"o știre în cel mai mic județ ({cel_mai_mic:,} loc.) da {rata_minima:.2f}, "
        f"sub primul prag ({prag}) — ar apărea ca zero")


def test_js_foloseste_pragurile_din_pagina_nu_alternative():
    js = _js()
    assert "praguriDinPagina(" in js, "JS-ul nu citește pragurile din legendă"
    assert '"praguri"' in js and '"praguriLocuitor"' in js, (
        "JS-ul nu citește AMBELE seturi de praguri (volum + pe locuitor)")
    assert "praguriFor" not in js, (
        "cuartilele per filtru au revenit — scara nu mai e comparabilă între ecrane")
    # clasa = câte praguri sunt acoperite (>=), nu câte sunt strict sub
    assert "praguri.filter((p) => valoare >= p).length" in js
    assert "valoare > p" not in js
    # grila de afișare a ratei (o zecimală) e chiar cea pe care o descriu etichetele
    assert "Math.round((count / pop) * 100000 * 10) / 10" in js, (
        "valoarea afișată a ratei nu mai e rotunjită la grila din legendă (0,1)")


def test_legenda_nu_construieste_text_in_js():
    # Orice text de bandă compus în JS poate produce din nou „undefined"/„NaN"; legenda e
    # conținut static, iar JS-ul doar o arată sau o ascunde (alege titlul și setul de benzi).
    js = _js()
    assert "function updateLegend({ show = true, variant = \"volum\" } = {})" in js
    assert "legend-step" not in js
    assert "swatch" not in js
    assert "createTextNode(step" not in js


def test_etichetele_de_judet_din_pagina_sunt_cele_oficiale():
    """Tabelul de nume afișate (Timiș, nu TIMIS) trebuie să fie exact geo.eticheta_judet."""
    html = _html()
    match = re.search(r'id="judete-etichete" data-etichete=\'([^\']+)\'', html)
    assert match, "tabelul de etichete lipsește din pagină — selectorul ar tipări coduri"
    table = json.loads(match.group(1))
    with open(os.path.join(ROOT, "data", "harta_judete.json"), encoding="utf-8") as fh:
        judete = json.load(fh)["judete"]
    expected = {code: geo.eticheta_judet(code) for code in judete}
    assert table == expected, (
        "etichetele din pagină diferă de geo.eticheta_judet: "
        f"{sorted(set(expected.items()) ^ set(table.items()))[:5]}")


def test_etichetele_nu_intra_in_url():
    """Adresa rămâne pe coduri (compatibilă cu linkurile partajate), doar afișarea e tradusă."""
    js = _js()
    assert 'params.set("judet", state.selectedCounty)' in js


# --- numitorul (F3): populația cu sursă și dată ----------------------------------------------

POPULATIE = os.path.join(ROOT, "static", "harta-stiri", "data", "populatie.json")
MAP_JSON = os.path.join(ROOT, "static", "harta-stiri", "data", "map.json")


def _populatie() -> dict:
    with open(POPULATIE, encoding="utf-8") as fh:
        return json.load(fh)


def test_numitorul_acopera_exact_judetele_hartii():
    """Fără acoperire completă, modul „pe locuitor" ar colora județele lipsă cu null."""
    with open(MAP_JSON, encoding="utf-8") as fh:
        coduri = set((json.load(fh).get("map") or {}).get("judete") or {})
    date = _populatie()
    assert set(date["judete"]) == coduri, (
        f"populație pentru alte județe decât harta: {sorted(set(date['judete']) ^ coduri)[:5]}")
    assert all(isinstance(v, int) and v > 0 for v in date["judete"].values())
    assert date["total"] == sum(date["judete"].values())
    assert date["sursa"] and date["referinta"], "numitorul nu are sursă și dată"


def test_numitorul_e_plauzibil_fata_de_ins():
    """Totalul agregat trebuie să fie aproape de recensământ: e un raport, nu o cifră scoasă
    din aer. Pragul de 2 % e cel din instrumentul de build (tools/build_harta_populatie.py)."""
    date = _populatie()
    abatere = abs(date["total"] - date["total_ins_2021"]) / date["total_ins_2021"]
    assert abatere < 0.02, f"total agregat la {abatere:+.1%} de INS 2021"


def _text_pagina() -> str:
    """HTML-ul cu spațiile normalizate: textele din pagină sunt împachetate pe rânduri, iar
    un test care ar cere o propoziție întreagă pe un rând ar pica la prima rearanjare."""
    return re.sub(r"\s+", " ", _html())


def test_footnote_ul_spune_ce_e_numaratorul_si_ce_e_numitorul():
    html = _text_pagina()
    assert "map-footnote" in html, "pagina nu are footnote-ul cu numitorul"
    for bucata in ("numărătorul", "numitorul", "INS 2021", "nu o ierarhie",
                   "nu e o statistică oficială"):
        assert bucata in html, f"footnote-ul nu spune „{bucata}”"


def test_cifrele_din_footnote_sunt_chiar_cele_din_date():
    """Cifrele scrise static în pagină nu au voie să divergă de fișierul de populație."""
    date = _populatie()
    html = _html()
    total = f"{date['total']:,}".replace(",", ".")
    ins = f"{date['total_ins_2021']:,}".replace(",", ".")
    assert total in html, f"totalul din footnote nu e cel din populatie.json ({total})"
    assert ins in html, f"totalul INS din footnote nu e cel din populatie.json ({ins})"


def test_modul_de_scara_este_stare_din_adresa():
    js = _js()
    assert 'params.get("scara") === "locuitori"' in js, "modul nu se citește din adresă"
    assert 'params.set("scara", "locuitori")' in js, "modul nu intră în adresă (link nepartajabil)"


def test_numitorul_se_incarca_lene_si_o_singura_data():
    js = _js()
    assert js.count('fetch("/static/harta-stiri/data/populatie.json")') == 1
    assert "function incarcaPopulatii()" in js
    assert "if (state.populatii) return Promise.resolve(state.populatii);" in js, (
        "lipsa memoizării: fiecare comutare ar cere din nou fișierul")
    # Eșecul are cale proprie: modul revine pe volum și spune de ce.
    assert "Populația pe județe nu a putut fi încărcată" in js


def test_uat_urile_rămân_pe_volum_si_o_spun():
    """Nu există populație pe orașe și comune în datele publicate, deci acolo scara rămâne
    volumul — iar legenda o spune, în loc să lase cititorul să creadă că sunt rate."""
    html = _html()
    js = _js()
    assert 'data-title="uat"' in html and "pe orașe și comune" in html
    assert "rampClassFor(uat.count, PRAGURI)" in js, "UAT-urile nu mai sunt legate explicit de volum"


def test_tool_ul_numitorului_este_sincron_cu_fisierul_comis():
    import subprocess
    rezultat = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "build_harta_populatie.py"), "--check"],
        capture_output=True, text=True, encoding="utf-8")
    assert rezultat.returncode == 0, (
        "populatie.json comis nu mai corespunde gazetteer-ului: "
        f"{rezultat.stdout.strip()} {rezultat.stderr.strip()}")
