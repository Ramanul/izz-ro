"""Garda pentru cele trei surse de nedeterminism reparate pe 2026-09-04.

DE CE EXISTA, si de ce arata asa. `izz.ro` e un generator static: output-ul e o functie de
(cod + date), iar `tools/echivalenta.py` (`IZZ-0271`) se bazeaza pe asta ca sa dovedeasca o
refactorizare NEUTRA. Masurat pe 2026-09-04, prima oara cand unealta a fost intoarsa asupra
propriei premise: doua randari ale ACELUIASI commit, pe aceleasi date, au dat 953 de fisiere
diferite din 47.222. Cat timp asta era adevarat, `compara` nu putea raporta „IDENTIC"
niciodata, deci plasa care apara refactorizarile era decor.

Trei cauze, toate din acelasi tipar — un `set` de siruri (ordine dependenta de
PYTHONHASHSEED, randomizat la fiecare proces) al carui rezultat ajunge intr-o taietura:

  1. „Conexiuni": `sorted(co.items(), key=-count)` e STABIL, deci egalitatile pastrau ordinea
     de iterare a setului, iar `[:6]` schimba COMPONENTA listei. 945 din 4.307 pagini.
  2. „Articole conectate": `scored.sort` pe (comune, idf, published), acelasi mecanism,
     `[:3]`. 8 pagini din 8.350 — egalitatea pe toate trei cheile e rara.
  3. `weight = sum(idf[s] for s in common)`: adunarea in virgula mobila NU e asociativa, deci
     aceiasi termeni insumati in alta ordine dau alt ULP (masurat: 23.80437088061844 vs
     23.804370880618443). Un bit ajunge ca sortarea sa inverseze doi candidati.

DE CE O GARDA PE SURSA SI NU UN TEST DE COMPORTAMENT, spus pe fata ca sa nu para mai mult
decat e: singura verificare comportamentala reala e randarea de doua ori si compararea
amprentelor — ~50 de minute, deci nu incape in CI. `OUT_DIR` si calea starii sunt hardcodate
in `generator/render.py` / `state.py`, deci nu se poate randa un corpus mic intr-un tmp_path
fara sa modific codul de productie mai mult decat fixul insusi. Garda de aici e deci un
compromis declarat: apara cele TREI constructe cunoscute, prin forma lor, si NU generalizeaza
la o a patra sursa. Un audit AST al intregului pachet `generator/` a aratat pe 2026-09-04 ca
nu exista o a patra (fiecare `set` ajunge intr-un `len()`, un `bool()`, un test de apartenenta
sau un `sorted()`), dar auditul ala a fost o masuratoare de moment, nu o garda.

Daca refactorizezi zona si garda pica pe nume: NU sterge verificarea. Muta-i tinta. Ce apara
ea nu e forma expresiei, ci proprietatea „ordinea nu poate intra in output".
"""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "generator" / "render.py"


def _lambde_cu_cheie(arbore: ast.AST, este_tinta) -> list[ast.Lambda]:
    """Lambdele date ca `key=` apelurilor pentru care `este_tinta(call)` e adevarat."""
    gasite = []
    for n in ast.walk(arbore):
        if not isinstance(n, ast.Call) or not este_tinta(n):
            continue
        for kw in n.keywords:
            if kw.arg == "key" and isinstance(kw.value, ast.Lambda):
                gasite.append(kw.value)
    return gasite


def _componente(lam: ast.Lambda) -> int:
    """Cate componente are cheia. 1 daca nu e tuplu — adica nu departajeaza nimic."""
    return len(lam.body.elts) if isinstance(lam.body, ast.Tuple) else 1


def incalcari_determinism(sursa: str) -> list[str]:
    """Cele trei constructe, verificate prin forma. Lista goala = toate in regula."""
    arbore = ast.parse(sursa)
    rele: list[str] = []

    # (1) `sorted(co.items(), key=...)` — co e construit iterand un set, deci cheia trebuie
    # sa duca pana la o ordine TOTALA: numar de co-ocurente, IDF, si slug-ul la final.
    def e_sorted_pe_co(c: ast.Call) -> bool:
        return (getattr(c.func, "id", "") == "sorted" and c.args
                and isinstance(c.args[0], ast.Call)
                and getattr(c.args[0].func, "attr", "") == "items"
                and getattr(getattr(c.args[0].func, "value", None), "id", "") == "co")

    chei = _lambde_cu_cheie(arbore, e_sorted_pe_co)
    if not chei:
        rele.append("nu am gasit `sorted(co.items(), key=...)` — s-a mutat sau redenumit; "
                    "muta tinta garzii, nu sterge verificarea")
    for lam in chei:
        if _componente(lam) < 3:
            rele.append(f"cheia lui `sorted(co.items())` are {_componente(lam)} componente, "
                        "sub 3: la egalitate de co-ocurente ordinea redevine cea de iterare a "
                        "unui `set`, iar `[:6]` schimba componenta listei „Conexiuni\"")

    # (2) `scored.sort(key=...)` — `mine` e un set; fara URL-ul la final, egalitatea pe
    # (comune, idf, published) lasa ordinea de iterare sa decida ce taie `[:3]`.
    def e_sort_pe_scored(c: ast.Call) -> bool:
        return (getattr(c.func, "attr", "") == "sort"
                and getattr(getattr(c.func, "value", None), "id", "") == "scored")

    chei = _lambde_cu_cheie(arbore, e_sort_pe_scored)
    if not chei:
        rele.append("nu am gasit `scored.sort(key=...)` — s-a mutat sau redenumit")
    for lam in chei:
        if _componente(lam) < 4:
            rele.append(f"cheia lui `scored.sort` are {_componente(lam)} componente, sub 4: "
                        "fara o cheie unica la final (URL-ul) ordinea „Articole conectate\" "
                        "depinde de iterarea unui `set`")

    # (3) `weight = sum(... for s in sorted(common))` — fara `sorted`, non-asociativitatea
    # adunarii in virgula mobila face suma dependenta de ordine.
    gasit_weight = False
    for n in ast.walk(arbore):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1
                and getattr(n.targets[0], "id", "") == "weight"):
            continue
        gasit_weight = True
        v = n.value
        if not (isinstance(v, ast.Call) and getattr(v.func, "id", "") == "sum"
                and v.args and isinstance(v.args[0], ast.GeneratorExp)):
            rele.append("`weight` nu mai e un `sum(<generator>)` — reverifica determinismul")
            continue
        iterabil = v.args[0].generators[0].iter
        if not (isinstance(iterabil, ast.Call) and getattr(iterabil.func, "id", "") == "sorted"):
            rele.append("`weight = sum(...)` itereaza direct un `set`, nu `sorted(...)`: "
                        "adunarea in virgula mobila nu e asociativa, deci suma depinde de "
                        "ordine (masurat 23.80437088061844 vs 23.804370880618443)")
    if not gasit_weight:
        rele.append("nu am gasit atribuirea lui `weight` — s-a mutat sau redenumit")

    return rele


def test_render_pastreaza_cele_trei_departajari():
    incalcari = incalcari_determinism(RENDER.read_text(encoding="utf-8"))
    assert not incalcari, "determinismul randarii e din nou rupt:\n  - " + "\n  - ".join(incalcari)


# --- garda poate pica: fiecare din cele trei, rupta deliberat ---

_SCHELET = """
co, scored, common, idf, mine = {{}}, [], set(), {{}}, set()
connections = sorted(co.items(), key=lambda kv: {cheie_co})[:6]
scored.sort(key=lambda t: {cheie_scored}, reverse=True)
weight = sum(idf.get(s, 0.0) for s in {iterabil})
"""
_BUN = dict(cheie_co="(-kv[1], -idf.get(kv[0], 0.0), kv[0])",
            cheie_scored="(t[0], t[1], t[2], t[3])", iterabil="sorted(common)")


def test_scheletul_de_referinta_trece():
    """Fara asta, testele negative de mai jos ar putea pica din alt motiv decat cel testat."""
    assert incalcari_determinism(_SCHELET.format(**_BUN)) == []


@pytest.mark.parametrize("camp,rupt,asteptat", [
    ("cheie_co", "-kv[1]", "componente, sub 3"),
    ("cheie_co", "(-kv[1], kv[0])", "componente, sub 3"),
    ("cheie_scored", "(t[0], t[1], t[2])", "componente, sub 4"),
    ("iterabil", "common", "nu e asociativa"),
])
def test_garda_pica_pe_fiecare_departajare_rupta(camp, rupt, asteptat):
    incalcari = incalcari_determinism(_SCHELET.format(**{**_BUN, camp: rupt}))
    assert any(asteptat in x for x in incalcari), \
        f"garda NU a prins `{camp}={rupt}` — deci nu apara nimic. Incalcari: {incalcari}"


def test_garda_pica_daca_expresiile_dispar():
    """Redenumirea nu are voie sa faca garda sa treaca in gol — asta a fost defectul original."""
    incalcari = incalcari_determinism("x = 1\n")
    assert len(incalcari) == 3, f"asteptam trei constructe lipsa, am primit: {incalcari}"
