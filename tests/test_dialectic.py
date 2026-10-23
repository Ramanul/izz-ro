"""E2 — sinteza dialectică: modelul propune, Python decide (`generator/dialectic.py`).

Fiecare test fixează o regulă din `specs/plan-paradigma-izz.md` §3 E2 / §5 care, altfel, ar trăi
doar în prompt: citarea trebuie să existe și să fie a acestui eveniment; cifrele trebuie să fie
în propozițiile citate; „comun" înseamnă două ORIGINI (o clonă nu e a doua origine); rezerva de
la sursă nu dispare tăcut; Tăcerea Asumată nu ascunde un miez cert.
"""
from __future__ import annotations

import json

import dialectic_fake

from generator import dialectic, process


def _m(url, name, published, title, desc, role=None, sents=None):
    it = {"url": url, "original_link": url, "source_name": name, "published": published,
          "original_title": title, "description": desc}
    if role:
        it["_epistemic_role"] = role
    if sents is not None:
        it["_deep_sentences"] = {f"S1.{k}": s for k, s in enumerate(sents, start=1)}
        it["_deep_mode"] = "FULL_TEXT"
    return it


A = _m("https://a.ro/1", "Alfa", "2026-10-22T10:00:00+00:00", "x", "x", "ROOT",
       ["Consiliul Județean Bihor a aprobat bugetul de 820 de milioane de lei.",
        "Votul a avut loc joi, cu 21 de voturi pentru.",
        "Opoziția a cerut o rectificare în martie."])
B = _m("https://b.ro/1", "Beta", "2026-10-22T10:20:00+00:00", "x", "x", "INDEPENDENT_CONTRIBUTOR",
       ["Bugetul Bihorului pentru anul viitor este de 820 de milioane de lei.",
        "Consilierii au votat joi, iar 19 consilieri au fost pentru.",
        "Din buget, 120 de milioane merg la drumuri."])
C = _m("https://c.ro/1", "Gama", "2026-10-22T10:40:00+00:00", "x", "x", "CLONE",
       ["Consiliul Județean Bihor a aprobat bugetul de 820 de milioane de lei."])


def _block(*items, cid=0):
    return dialectic.build_block(cid, list(items))


def _ids(block, name):
    src = next(s for s in block.sources if s.name == name)
    return [k for k in block.chunks if k.startswith(f"S{src.idx}.")]


# --- 1. contextul -------------------------------------------------------------------------

def test_blocul_ordoneaza_dupa_rol_si_numeroteaza_unic_in_lot():
    b = _block(C, B, A, cid=2)
    assert [s.name for s in b.sources] == ["Alfa", "Beta", "Gama"]    # ROOT, IC, CLONE
    assert "[S1] Alfa" in b.text and "prima relatare" in b.text
    b0, b1 = dialectic.build_blocks([([A, B], {}), ([A, C], {})])
    assert {k.split(".")[0] for k in b0.chunks} == {"S1", "S2"}
    assert {k.split(".")[0] for k in b1.chunks} == {"S3", "S4"}      # continuă, nu repornește
    assert not set(b0.chunks) & set(b1.chunks)


def test_plafonul_ia_propozitii_intregi_round_robin_si_prima_mereu():
    lung = _m("https://l.ro/1", "Lung", "2026-10-22T09:00:00+00:00", "x", "x", "ROOT",
              [f"Propoziția numărul {i} are destule cuvinte ca să conteze în plafon." for i in range(40)])
    b = dialectic.build_block(0, [lung, B], char_budget=400)
    # sursa scurtă nu e înghițită de cea lungă: are cel puțin prima propoziție
    assert _ids(b, "Beta")
    total = sum(len(t) for _, t in b.chunks.values())
    assert total <= 400 + 200        # doar primele propoziții pot depăși plafonul
    assert all(t.endswith(".") for _, t in b.chunks.values())


def test_faptele_versiunii_anterioare_intra_ca_P_cu_publicatiile_lor():
    vechi = dict(_m("https://a.ro/1", "Alfa", "2026-10-22T08:00:00+00:00", "x", "x", "ROOT", None))
    vechi.update(processed_by="gemini", model="C", members=[{"url": "https://a.ro/1", "title": "Bugetul aprobat"}],
                 dialectic={"common": [{"text": "Bugetul este de 820 de milioane de lei.", "src": ["Alfa", "Delta"]}],
                            "single": [], "diverg": []})
    b = dialectic.build_block(0, [vechi, B])
    assert "P0.1" in b.chunks
    assert b.chunks["P0.1"][0] == frozenset({"Alfa", "Delta"})
    # sinteza noastră veche NU devine „textul sursei": sursa fără text integral are titlul ei
    assert any(t == "Bugetul aprobat" for _, t in b.chunks.values())


# --- 2. validarea -------------------------------------------------------------------------

def _obj(**kw):
    base = {"id": 0, "title": "t", "epistemic_state": "SYNTHESIS_VALID", "common_facts": [],
            "divergences": [], "uncorroborated_claims": [], "is_milestone": False}
    base.update(kw)
    return base


def test_fapt_comun_din_doua_origini_e_valid():
    b = _block(A, B)
    d = dialectic.validate(_obj(common_facts=[{
        "statement": "Bugetul Bihorului a fost aprobat la 820 de milioane de lei.",
        "chunk_ids": [_ids(b, "Alfa")[0], _ids(b, "Beta")[0]]}]), b)
    assert d["state"] == dialectic.STATE_VALID
    assert d["common"][0]["src"] == ["Alfa", "Beta"]
    assert d["rejected"] == 0


def test_clona_nu_e_a_doua_origine_faptul_e_retrogradat_nu_respins():
    b = _block(A, C)
    d = dialectic.validate(_obj(common_facts=[{
        "statement": "Bugetul Bihorului a fost aprobat la 820 de milioane de lei.",
        "chunk_ids": [_ids(b, "Alfa")[0], _ids(b, "Gama")[0]]}]), b)
    assert d["state"] == dialectic.STATE_SINGLE
    assert not d["common"] and d["single"]
    assert d["rejected"] == 0


def _bune(b, n=3):
    """n fapte comune valide, ca o singură respingere să rămână sub pragul de Tăcere."""
    texte = ["Bugetul Bihorului este de 820 de milioane de lei.",
             "Votul pe buget a avut loc joi.",
             "Bugetul județului Bihor a fost votat în consiliu."]
    perechi = [(0, 0), (1, 1), (0, 1)]
    return [{"statement": texte[i], "chunk_ids": [_ids(b, "Alfa")[x], _ids(b, "Beta")[y]]}
            for i, (x, y) in enumerate(perechi[:n])]


def test_citarea_inexistenta_sau_din_alt_cluster_e_respinsa():
    b0, b1 = dialectic.build_blocks([([A, B], {}), ([dict(A), dict(B)], {})])
    strain = sorted(b0.chunks)[:2]                         # etichete ale evenimentului 0
    d = dialectic.validate(_obj(common_facts=_bune(b1) + [
        {"statement": "Bugetul este de 820 de milioane de lei.", "chunk_ids": strain},
    ]), b1)
    assert d["rejected"] == 1 and d["total"] == 4
    assert d["state"] == dialectic.STATE_VALID
    d = dialectic.validate(_obj(common_facts=_bune(b1) + [
        {"statement": "Bugetul este de 820 de milioane de lei.", "chunk_ids": ["S99.9"]},
    ]), b1)
    assert d["rejected"] == 1
    # prefixul „C1" adăugat de model din obișnuință nu strică o etichetă corectă
    ok = dialectic.validate(_obj(common_facts=[
        {"statement": "Bugetul Bihorului este de 820 de milioane de lei.",
         "chunk_ids": ["C1" + k for k in (_ids(b1, "Alfa")[0], _ids(b1, "Beta")[0])]}]), b1)
    assert ok["rejected"] == 0 and ok["state"] == dialectic.STATE_VALID


def test_peste_prag_de_respingeri_se_amana_nu_se_declara_tacere():
    """2 din 3 afirmații fără temei: problema e a modelului, nu a surselor. A publica
    „datele sunt ireconciliabile" ar fi o afirmație falsă despre presă (măsurat 23.10:
    un meci relatat identic de toate sursele, declarat astfel)."""
    b = _block(A, B, cid=1)
    obj = _obj(epistemic_state="ASSUMED_SILENCE", common_facts=_bune(b, 1) + [
        {"statement": "Bugetul este de 820 de milioane de lei.", "chunk_ids": ["S98.1", "S99.1"]},
        {"statement": "Bugetul este de 820 de milioane de lei.", "chunk_ids": ["S99.9"]},
    ])
    assert dialectic.validate(obj, b) is None


def test_declaratia_de_tacere_a_modelului_nu_decide_starea():
    b = _block(A, B)
    d = dialectic.validate(_obj(epistemic_state="ASSUMED_SILENCE", common_facts=_bune(b, 1)), b)
    assert d["state"] == dialectic.STATE_VALID


def test_cifra_absenta_din_propozitiile_citate_e_respinsa():
    """120 există în cluster (la Beta), dar NU în propozițiile citate: asocierea falsă."""
    b = _block(A, B)
    d = dialectic.validate(_obj(common_facts=_bune(b) + [
        {"statement": "Bugetul de 820 de milioane alocă 120 de milioane pentru drumuri.",
         "chunk_ids": [_ids(b, "Alfa")[0], _ids(b, "Beta")[0]]},
    ]), b)
    assert d["rejected"] == 1
    assert not any("120" in f["text"] for f in d["common"])


def test_afirmatia_copiata_e_respinsa_inainte_de_gate():
    lung = _m("https://l.ro/1", "Alfa", "2026-10-22T09:00:00+00:00", "x", "x", "ROOT",
              ["Consiliul Județean Bihor a aprobat în ședința de joi bugetul general al județului "
               "pentru anul viitor în valoare de 820 de milioane de lei.",
               "Votul a avut loc joi, cu 21 de voturi pentru."])
    b = _block(lung, B)
    copiat = ("Consiliul Județean Bihor a aprobat în ședința de joi bugetul general al județului "
              "pentru anul viitor în valoare de 820 de milioane de lei.")
    d = dialectic.validate(_obj(common_facts=_bune(b) + [
        {"statement": copiat, "chunk_ids": [_ids(b, "Alfa")[0], _ids(b, "Beta")[0]]},
    ]), b)
    assert d["rejected"] == 1
    assert all(copiat != f["text"] for f in d["common"])


def test_rezerva_de_la_sursa_nu_dispare_tacut():
    s1 = _m("https://s.ro/1", "Sigma", "2026-10-22T10:00:00+00:00", "x", "x", "ROOT",
            ["Primarul ar fi semnat contractul fără licitație, potrivit unor surse."])
    s2 = _m("https://t.ro/1", "Tau", "2026-10-22T10:10:00+00:00", "x", "x", "ECHO",
            ["Contractul ar fi fost semnat de primar fără licitație."])
    s1b = dict(s1)
    s1b["_deep_sentences"] = {**s1["_deep_sentences"], "S1.2": "Primăria a publicat lista proiectelor."}
    s2b = dict(s2)
    s2b["_deep_sentences"] = {**s2["_deep_sentences"], "S1.2": "Lista proiectelor a fost publicată de primărie."}
    b = _block(s1b, s2b)
    d = dialectic.validate(_obj(common_facts=[
        {"statement": "Primarul a semnat contractul fără licitație.",   # rezerva pierdută
         "chunk_ids": [_ids(b, "Sigma")[0], _ids(b, "Tau")[0]]},
        {"statement": "Primăria a publicat lista proiectelor.",
         "chunk_ids": [_ids(b, "Sigma")[1], _ids(b, "Tau")[1]]},
    ]), b)
    f0 = d["common"][0]
    assert f0["hedged"] and f0["forced"]
    syn = dialectic.derive_synthesis(d, "Titlu", 90)
    assert "fără licitație" not in syn            # nu intră în textul scurt de pe card
    assert "lista proiectelor" in syn


def test_doar_fapte_cu_rezerva_pierduta_amana_clusterul():
    s1 = _m("https://s.ro/1", "Sigma", "2026-10-22T10:00:00+00:00", "x", "x", "ROOT",
            ["Primarul ar fi semnat contractul fără licitație."])
    s2 = _m("https://t.ro/1", "Tau", "2026-10-22T10:10:00+00:00", "x", "x", "ECHO",
            ["Contractul ar fi fost semnat de primar fără licitație."])
    b = _block(s1, s2)
    assert dialectic.validate(_obj(common_facts=[
        {"statement": "Primarul a semnat contractul fără licitație.",
         "chunk_ids": [_ids(b, "Sigma")[0], _ids(b, "Tau")[0]]}]), b) is None


def test_un_fapt_cert_si_doua_divergente_nu_inseamna_tacere():
    """Argon R4: ora și numărul diferă, dar votul e cert — miezul nu se ascunde."""
    b = _block(A, B)
    d = dialectic.validate(_obj(
        common_facts=[{"statement": "Bugetul Bihorului este de 820 de milioane de lei.",
                       "chunk_ids": [_ids(b, "Alfa")[0], _ids(b, "Beta")[0]]}],
        divergences=[{"axis": "numărul voturilor pentru", "positions": [
            {"claim": "Alfa scrie că 21 de consilieri au votat pentru.", "chunk_ids": [_ids(b, "Alfa")[1]]},
            {"claim": "Beta scrie că 19 consilieri au votat pentru.", "chunk_ids": [_ids(b, "Beta")[1]]}]}]), b)
    assert d["state"] == dialectic.STATE_VALID
    assert len(d["diverg"]) == 1 and len(d["diverg"][0]["pos"]) == 2


def test_fara_fapt_comun_dar_cu_divergenta_e_tacere_asumata():
    b = _block(A, B)
    d = dialectic.validate(_obj(
        epistemic_state="SYNTHESIS_VALID",
        divergences=[{"axis": "numărul voturilor pentru", "positions": [
            {"claim": "Alfa: 21 de voturi pentru.", "chunk_ids": [_ids(b, "Alfa")[1]]},
            {"claim": "Beta: 19 consilieri pentru.", "chunk_ids": [_ids(b, "Beta")[1]]}]}]), b)
    assert d["state"] == dialectic.STATE_SILENCE
    syn = dialectic.derive_synthesis(d, "Votul pe bugetul Bihorului", 90)
    assert syn.startswith("Votul pe bugetul Bihorului:") and "ireconciliabile" in syn


def test_divergenta_cu_o_singura_publicatie_se_ignora():
    b = _block(A, B)
    d = dialectic.validate(_obj(
        common_facts=[{"statement": "Bugetul Bihorului este de 820 de milioane de lei.",
                       "chunk_ids": [_ids(b, "Alfa")[0], _ids(b, "Beta")[0]]}],
        divergences=[{"axis": "voturi", "positions": [
            {"claim": "21 de voturi.", "chunk_ids": [_ids(b, "Alfa")[1]]},
            {"claim": "Votul a fost joi.", "chunk_ids": [_ids(b, "Alfa")[1]]}]}]), b)
    assert d["diverg"] == []


def test_nimic_valid_inseamna_amanare():
    b = _block(A, B)
    assert dialectic.validate(_obj(), b) is None
    assert dialectic.validate("nu e obiect", b) is None


def test_milestone_doar_pe_sinteza_valida_fara_rezerva():
    b = _block(A, B)
    d = dialectic.validate(_obj(is_milestone=True, common_facts=[
        {"statement": "Bugetul Bihorului este de 820 de milioane de lei.",
         "chunk_ids": [_ids(b, "Alfa")[0], _ids(b, "Beta")[0]]}]), b)
    assert d["milestone"] is True


def test_corectura_plata_dus_intors():
    d = {"common": [{"text": "a"}], "single": [{"text": "b"}],
         "diverg": [{"axis": "c", "pos": [{"text": "d"}, {"text": "e"}]}]}
    assert dialectic.flat_texts(d) == ["a", "b", "c", "d", "e"]
    assert dialectic.assign_flat(d, ["ă", "b", "c", "d", "ț"])
    assert d["common"][0]["text"] == "ă" and d["diverg"][0]["pos"][1]["text"] == "ț"
    assert not dialectic.assign_flat(d, ["prea", "putine"])
    assert d["common"][0]["text"] == "ă"


# --- 3. calea completă prin process --------------------------------------------------------

class _Lot:
    """Răspunde valid pentru evenimentul 0 și cu JSON dialectic inutilizabil pentru 1."""
    name = "fals"

    def complete(self, system, user):
        valid = json.loads(dialectic_fake.raspuns(user, "Bihorul are buget aprobat pentru anul viitor",
                                                  "Bugetul Bihorului este de 820 de milioane de lei."))
        valid[1]["common_facts"] = [{"statement": "Altceva.", "chunk_ids": ["S77.1"]}]
        return json.dumps(valid)


def test_lotul_publica_clusterul_valid_si_amana_doar_pe_cel_stricat():
    out = process.process_clusters_batch([[dict(A), dict(B)], [dict(A), dict(B)]], _Lot())
    assert out[0] is not None and out[1] is None
    rep = out[0]
    assert rep["dialectic"]["state"] == dialectic.STATE_VALID
    assert rep["synthesis"] == "Bugetul Bihorului este de 820 de milioane de lei."
    assert rep["title"] == "Bihorul are buget aprobat pentru anul viitor"


def test_promptul_dialectic_poarta_propozitiile_si_regulile():
    seen = {}

    class _Spion:
        name = "spion"

        def complete(self, system, user):
            seen["user"] = user
            return "[]"

    process.process_clusters_batch([[dict(A), dict(B)]], _Spion())
    assert "[S1.1] Consiliul Județean Bihor a aprobat" in seen["user"]
    assert "cel putin DOUA publicatii" in seen["user"]
    assert "SCRIE IN ROMANA" in seen["user"]


def test_loturile_separa_clusterele_vecine_si_pastreaza_ordinea():
    def meci(n):
        return [{"original_title": f"Universitatea Craiova a învins Inter Escaldes în Andorra, {n}"}]
    buget = [{"original_title": "Bugetul Bihorului aprobat în consiliu"}]
    alt = [{"original_title": "Tom Skerritt a murit la 93 de ani"}]
    g = [meci(1), meci(2), buget, meci(3), alt]
    lots = dialectic.loturi(g, 3)
    for lot in lots:
        assert sum(1 for x in lot if "Craiova" in x[0]["original_title"]) <= 1
    assert lots[0][0] is g[0]                              # prioritatea primului se păstrează
    assert sorted(id(x) for lot in lots for x in lot) == sorted(id(x) for x in g)
    # titluri fără entități comune nu sunt vecine: lotul rămâne plin (bugetul nu se sparge)
    generice = [[{"original_title": f"eveniment {n} pentru anul acesta"}] for n in range(5)]
    assert [len(x) for x in dialectic.loturi(generice, 3)] == [3, 2]


def test_parsarea_tolerata_pierde_doar_obiectul_stricat():
    text = '[{"id": 0, "title": "a",\n  - "entities": []},\n {"id": 1, "title": "b",},\n {"id": 2 "x"}]'
    arr = process._parse_json_array_tolerant(text)
    assert [o["id"] for o in arr] == [0, 1]
