"""Carduri: portret real per entitate + marcajul AI Act la prima expunere (IZZ-0416).

P1 — homepage-ul avea 0 <img> masurat (IZZ-0403), desi 73% din articole au portret deja
in output/portraits. IZZ-0416 leaga potrivirea existenta (pagini /subiect/) de carduri:
zero fisiere noi, zero cereri AI, media reala in locul artei desenate.
"""
import os
import re

import pytest


def _index(output_randat) -> str:
    with open(os.path.join(output_randat, "index.html"), encoding="utf-8") as fh:
        return fh.read()


def test_homepageul_afiseaza_fotografii_reale_pe_carduri(output_randat):
    html = _index(output_randat)
    poze = re.findall(r'<img src="[^"]*?/portraits/[^"]+?"', html)
    assert poze, (
        "homepage-ul nu afiseaza nicio fotografie reala — regresia IZZ-0403 e inca vie. "
        "Daca starea comisa chiar nu are NICIUN portret in primele 200 de articole, "
        "starea s-a schimbat calitativ: remasoara si reevalueaza regula, nu sterge testul.")


def test_trust_labelul_numeste_generarea_automata(output_randat):
    # Dezvaluirea AI Act la prima expunere (REGULI-SINTEZA §4.3): pe card, eticheta
    # trebuie sa spuna explicit ca textul e generat automat, nu doar de unde vine.
    html = _index(output_randat)
    assert ("generat automat" in html) or ("generată automat" in html), (
        "trust-label-ul nu mai dezvaluie generarea automata pe card — obligatie "
        "art. 50(4) AI Act, obligatorie de la 2026-08-02.")


def test_meta_digital_source_type_pe_paginile_de_articol(output_randat):
    gasite = 0
    for radacina, _dosare, fisiere in os.walk(output_randat):
        for f in fisiere:
            if not f.endswith(".html") or f != "index.html":
                continue
            cale = os.path.join(radacina, f)
            with open(cale, encoding="utf-8") as fh:
                html = fh.read()
            assert 'name="digitalSourceType"' not in html or (
                'content="trainedAlgorithmicMedia"' in html), (
                    f"meta digitalSourceType fara valoarea IPTC in {cale}")
            if 'name="digitalSourceType"' in html:
                gasite += 1
    assert gasite > 0, (
        "niciun articol nu poarta meta digitalSourceType — marcajul machine-readable "
        "(art. 50(2), text INCLUS) a disparut din randare.")


def test_pictograma_oficiala_UE_e_comisa_si_referita(output_randat):
    cale = os.path.join(output_randat, "static", "icons", "ai-generated.svg")
    assert os.path.isfile(cale), "static/icons/ai-generated.svg nu a ajuns in output/"
    gasita = False
    for radacina, _dosare, fisiere in os.walk(output_randat):
        if gasita:
            break
        for f in fisiere:
            if not f.endswith(".html"):
                continue
            with open(os.path.join(radacina, f), encoding="utf-8") as fh:
                if "static/icons/ai-generated.svg" in fh.read():
                    gasita = True
                    break
    assert gasita, "pictograma UE e comisa dar nicio pagina nu o refera"


@pytest.mark.parametrize(
    "entitati,are_portret",
    [
        (["Lionel Messi", "FC Barcelona"], True),
        ([], False),
        (["Entitate Fara Portret Niciodata"], False),
    ],
)
def test_primul_portret_gasit_castiga_inline(entitati, are_portret):
    # Contractul buclei din render.build: prima entitate cu portret din lista decide.
    # Mentine sincronizat cu portretele.json comise (cheie = nume normalizat).
    from generator.render import _load_portraits, _norm_name

    portraits = _load_portraits()
    gasit = any(portraits.get(_norm_name(e)) for e in entitati)
    assert gasit is are_portret, (
        f"entitatile {entitati} -> portret={gasit}; daca 'Lionel Messi' nu mai are "
        "portret in portraits.json, datele s-au schimbat — actualizeaza cazul de test.")
