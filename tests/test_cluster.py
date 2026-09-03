"""Teste pentru clustering (over-merge si under-merge) din generator/cluster.py."""
from datetime import datetime, timedelta, timezone

from generator import cluster


def _a(title, url, link=None, entities=None):
    return {"title": title, "original_title": title, "url": url,
            "original_link": link or url, "entities": entities or [],
            "published": datetime.now(timezone.utc).isoformat()}


def test_cluster_groups_same_event():
    arts = [_a("Guvernul aprobă bugetul apărării pentru 2027", "u1"),
            _a("Bugetul apărării pe 2027, aprobat de guvern", "u2")]
    groups = cluster.cluster(arts)
    assert any(len(g) == 2 for g in groups)


def test_cluster_does_not_merge_different_events():
    arts = [_a("Inundații puternice în Moldova, sate evacuate", "u1"),
            _a("Victorie pentru națională la handbal feminin", "u2")]
    groups = cluster.cluster(arts)
    assert all(len(g) == 1 for g in groups)


def test_attach_recent_entity_guard_blocks_template_matches():
    # cronici-sablon: text asemanator, entitati disjuncte -> NU se unesc
    g = [_a("Echipa învinge rivala și avansează în optimile cupei", "u1", entities=["Steaua"])]
    cand = _a("Echipa învinge rivala și avansează în optimile cupei", "u2", entities=["Rapid"])
    out = cluster.attach_recent([g], [cand])
    assert len(out[0]) == 1


def test_is_synthesis_candidate_needs_distinct_domains():
    same = [_a("t", "u1", "https://digi24.ro/a"), _a("t", "u2", "https://www.digi24.ro/b")]
    diff = [_a("t", "u3", "https://digi24.ro/a"), _a("t", "u4", "https://hotnews.ro/b")]
    assert not cluster.is_synthesis_candidate(same)
    assert cluster.is_synthesis_candidate(diff)


# ---------------------------------------------------------------------------
# Garzile de mai jos apara CONJUNCTIA din `_similar`, nu comportamentul general.
#
# DE CE EXISTA (masurat 2026-09-02, prin mutation testing): docstring-ul lui `_similar`
# argumenteaza explicit „Conditie AND (nu OR) -> evita lipirea a doua titluri lungi cu 3
# cuvinte generice comune". Decizia era scrisa, dar NEPAZITA: schimband `and` in `or` pe
# linia 40, INTREAGA suita trecea. Cu `or`, termenul `union > 0` e adevarat pentru orice
# pereche de titluri nevide, deci `_similar` ar returna True aproape mereu — over-merge
# total, toate articolele intr-un cluster.
#
# Sect. 7 cere ca schimbarile de clustering sa fie verificate pe AMBELE cazuri, over-merge
# SI under-merge. `test_cluster_does_not_merge_different_events` acoperea under-merge pe
# titluri fara legatura; ce lipsea era cazul GREU: titluri care CHIAR au tokeni comuni, dar
# nu suficient de proportional ca sa fie acelasi eveniment.


def test_similar_cere_AMBELE_praguri_nu_doar_unul():
    """Tokeni comuni PESTE prag, dar proportie SUB prag -> NU e acelasi eveniment.

    Ucide mutantul `and` -> `or`: cu `or`, primul termen singur ar decide."""
    from generator.cluster import _similar, SHARED_TOKENS_MIN, JACCARD_MIN
    comune = {f"cuvant{i}" for i in range(SHARED_TOKENS_MIN)}
    # doua titluri lungi care impart exact pragul de tokeni, dar sunt altfel diferite
    t1 = comune | {f"a{i}" for i in range(20)}
    t2 = comune | {f"b{i}" for i in range(20)}
    inter, union = len(t1 & t2), len(t1 | t2)
    assert inter >= SHARED_TOKENS_MIN, "fixtura trebuie sa treaca pragul de tokeni"
    assert inter / union < JACCARD_MIN, "fixtura trebuie sa PICE pragul de proportie"
    assert _similar(t1, t2) is False, (
        f"{inter} tokeni comuni din {union} (Jaccard {inter/union:.2f}) NU e acelasi eveniment; "
        "daca asta trece, conjunctia din _similar a devenit disjunctie")


def test_similar_cere_AMBELE_praguri_si_invers():
    """Proportie PESTE prag, dar prea putini tokeni -> tot NU.

    Cazul simetric: doua titluri foarte scurte si aproape identice trec usor de Jaccard,
    dar `SHARED_TOKENS_MIN` exista tocmai ca sa nu lipeasca stiri pe doua cuvinte. Fixtura
    se CONSTRUIESTE din constanta, ca sa nu devina tacut inaplicabila daca pragul se schimba.
    """
    from generator.cluster import _similar, SHARED_TOKENS_MIN, JACCARD_MIN
    comune = {f"cuvant{i}" for i in range(SHARED_TOKENS_MIN - 1)}   # exact UNUL sub prag
    t1, t2 = set(comune), comune | {"in_plus"}
    inter, union = len(t1 & t2), len(t1 | t2)
    assert inter / union >= JACCARD_MIN, "fixtura trebuie sa treaca pragul de proportie"
    assert inter < SHARED_TOKENS_MIN, "fixtura trebuie sa PICE pragul de tokeni"
    assert _similar(t1, t2) is False, (
        f"doar {inter} tokeni comuni, sub pragul de {SHARED_TOKENS_MIN}; "
        "daca asta trece, conjunctia din _similar a devenit disjunctie")


# ---------------------------------------------------------------------------
# `_strict_match` si garda pe entitati din `attach_recent`: doua decizii SCRISE si
# ARGUMENTATE, dar nepazite pana la 2026-09-02.
#
# `_strict_match` isi poarta calibrarea in docstring — trei perechi reale, cu cifrele lor:
# CFR/Ceara (3 tokeni / jac 0.50 -> DA), Messi vs Ronaldo (3 / 0.43 -> NU), Ormuz (5 / 0.63
# -> DA). Datele existau, testul nu. Mutantare: `and` -> `or` si ambele `>=` -> `>` de pe
# linia 75 treceau nevazute. Cu `or`, „inter >= 4" singur decide -> absorbtie cross-run
# pentru orice doua titluri cu 4 cuvinte comune, adica exact over-merge-ul din sect. 7.
#
# Garda pe entitati (`if ge and ce and not (ge & ce)`) apara cazul pentru care a fost
# scrisa: cronicile sportive-sablon („X invinge Y si avanseaza in optimi") se potrivesc
# textual desi sunt meciuri diferite. Si ea trecea nevazuta la `and` -> `or`.
#
# Testele de mai jos folosesc DOAR cifrele deja calibrate — nu inventeaza praguri noi.

def _acum(minute_in_urma=10):
    return (datetime.now(timezone.utc) - timedelta(minutes=minute_in_urma)).isoformat()


def test_strict_match_reproduce_calibrarea_din_docstring():
    """Cele trei perechi reale pe care pragul a fost calibrat, ca test executabil."""
    assert cluster._strict_match(3, 6) is True,  "CFR/Ceara: 3 tokeni, jac 0.50 -> duplicat"
    assert cluster._strict_match(3, 7) is False, "Messi vs Ronaldo: 3 tokeni, jac 0.43 -> NU"
    assert cluster._strict_match(5, 8) is True,  "Ormuz: 5 tokeni, jac 0.63 -> duplicat"


def test_strict_match_pe_ambele_granite_exacte():
    """Cele doua praguri, atinse exact. Ucide ambii mutanti `>=` -> `>` de pe linia 75."""
    assert cluster._strict_match(4, 10) is True,  "inter=4, jac fix 0.40 -> intra"
    assert cluster._strict_match(3, 6) is True,   "inter=3, jac fix 0.50 -> intra"
    assert cluster._strict_match(4, 11) is False, "inter=4, jac 0.36 -> sub prag"
    assert cluster._strict_match(3, 7) is False,  "inter=3, jac 0.43 -> sub prag"


def test_strict_match_cere_AMBII_termeni_ai_fiecarei_ramuri():
    """Ucide `and` -> `or`: multi tokeni comuni cu proportie mica NU e absorbtie.

    Cazul concret pe care il apara: doua stiri lungi si nelegate care impart patru cuvinte
    generice. Cu `or`, primul termen singur ar decide si s-ar lipi.
    """
    assert cluster._strict_match(4, 40) is False, "4 tokeni din 40 (jac 0.10) nu e acelasi eveniment"
    assert cluster._strict_match(2, 3) is False,  "jac 0.67 dar doar 2 tokeni comuni -> prea putin"
    assert cluster._strict_match(0, 0) is False,  "union gol -> niciodata"


def _stire(url, titlu, entitati=None):
    a = {"url": url, "title": titlu, "original_title": titlu, "published": _acum()}
    if entitati is not None:
        a["entities"] = entitati
    return a


def test_attach_recent_absoarbe_o_stire_veche_care_chiar_e_acelasi_eveniment():
    """Fara asta, testele urmatoare ar trece si daca `attach_recent` n-ar atasa nimic —
    sect. 7 cere ambele directii, nu doar apararea impotriva over-merge-ului."""
    grup = [_stire("https://a.ro/1", "Incendiu puternic la depozitul din Otopeni evacuati locatari")]
    vechi = _stire("https://b.ro/2", "Incendiu puternic depozitul Otopeni locatari evacuati pompieri")
    rezultat = cluster.attach_recent([grup], [vechi])
    assert len(rezultat[0]) == 2, "aceeasi stire din doua rulari trebuie sa se uneasca"


def test_attach_recent_nu_uneste_meciuri_diferite_cu_acelasi_sablon():
    """Garda pe entitati, cazul pentru care a fost scrisa. Ucide `and` -> `or` pe linia 110."""
    grup = [_stire("https://a.ro/1", "Simona Halep invinge adversara si avanseaza in optimile turneului",
                   entitati=["Simona Halep"])]
    vechi = _stire("https://b.ro/2", "Sorana Cirstea invinge adversara si avanseaza in optimile turneului",
                   entitati=["Sorana Cirstea"])
    rezultat = cluster.attach_recent([grup], [vechi])
    assert len(rezultat[0]) == 1, (
        "titluri-sablon cu entitati DISJUNCTE sunt meciuri diferite, nu acelasi eveniment")


def test_attach_recent_uneste_cand_entitatile_se_suprapun():
    """Cealalta parte a garzii: entitati comune -> potrivirea textuala se pastreaza."""
    grup = [_stire("https://a.ro/1", "Simona Halep invinge adversara si avanseaza in optimile turneului",
                   entitati=["Simona Halep"])]
    vechi = _stire("https://b.ro/2", "Simona Halep invinge adversara si avanseaza in optimile turneului",
                   entitati=["Simona Halep"])
    rezultat = cluster.attach_recent([grup], [vechi])
    assert len(rezultat[0]) == 2, "aceleasi entitati -> garda nu trebuie sa blocheze"


def test_attach_recent_nu_blocheaza_itemele_fara_entitati():
    """Regula tranzitorie scrisa in docstring: itemele dinainte de extractia de entitati nu
    au garda. Daca cineva o scoate, testul asta pica si decizia redevine vizibila."""
    grup = [_stire("https://a.ro/1", "Simona Halep invinge adversara si avanseaza in optimile turneului",
                   entitati=["Simona Halep"])]
    vechi = _stire("https://b.ro/2", "Simona Halep invinge adversara si avanseaza in optimile turneului")
    rezultat = cluster.attach_recent([grup], [vechi])
    assert len(rezultat[0]) == 2, "fara entitati pe o parte -> garda nu se aplica"


def test_similar_accepta_exact_ambele_praguri_atinse():
    """Cazul POZITIV de pe granita: fix `SHARED_TOKENS_MIN` tokeni comuni si Jaccard fix
    `JACCARD_MIN` -> DA, e acelasi eveniment.

    Ucide cei doi mutanti `>=` -> `>` de pe linia 40. Testele negative de mai sus nu-i puteau
    ucide: ele apara marginea de jos, iar `>` inaspreste pragul, deci raspunsul negativ nu se
    schimba. O granita cere ambele raspunsuri, nu doar pe cel care confirma regula.
    """
    from generator.cluster import _similar, SHARED_TOKENS_MIN, JACCARD_MIN
    union_tinta = round(SHARED_TOKENS_MIN / JACCARD_MIN)          # 3 / 0.30 -> 10
    comune = {f"comun{i}" for i in range(SHARED_TOKENS_MIN)}
    restul = union_tinta - SHARED_TOKENS_MIN
    t1 = comune | {f"a{i}" for i in range(restul // 2)}
    t2 = comune | {f"b{i}" for i in range(restul - restul // 2)}
    inter, union = len(t1 & t2), len(t1 | t2)
    assert inter == SHARED_TOKENS_MIN and union == union_tinta, (inter, union)
    assert inter / union >= JACCARD_MIN, (
        f"fixtura trebuie sa atinga pragul exact; {inter}/{union} = {inter/union!r} "
        f"vs {JACCARD_MIN!r} — daca pica aici, e rotunjire in virgula mobila, nu un bug de cod")
    assert _similar(t1, t2) is True, "pragurile atinse exact TREBUIE sa fie acceptate"
