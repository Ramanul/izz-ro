"""Marcajul AI Act la prima expunere (IZZ-0420, REGULI-SINTEZA §4.3 amendat).

Media cardurilor (portrete PD/CC0 + siluete) e partea #414; aici se verifica DOAR
dezvaluirea generarii automate: trust-label pe card (art. 50(4)), meta machine-readable
pe articol (art. 50(2) — text INCLUS) si pictograma oficiala UE comisa + referita.
"""
import os


def _index(output_randat) -> str:
    with open(os.path.join(output_randat, "index.html"), encoding="utf-8") as fh:
        return fh.read()


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
            if not f.endswith(".html"):
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
