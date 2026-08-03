"""Rezerva de buget AI trebuie sa fie plafonata de cati candidati exista.

MASURAT 2026-08-03 pe logurile `build.yml`, trei rulari consecutive:

    03:49  noi 94   B 70  C 3   amanate  20   ai_calls 10
    23:06  noi 119  B 90  C 1   amanate  27   ai_calls 10
    21:07  noi 185  B 50  C 4   amanate 127   ai_calls 10

`MAX_AI_CALLS_PER_RUN=18`, `UPGRADE_RESERVE=8`, deci `process_new` primea 10. `ai_calls 10`
pe toate trei = rezerva de 8 nu s-a cheltuit niciodata. Numarat pe starea reala:

    1117 (B, gemini, v2-esenta)  386 (C, gemini, v2-esenta)  233 (B, official, None)
    fallback ramase: 0           ELIGIBILE pentru upgrade: 0

Cele 233 oficiale nu califica prin constructie — sunt procesate determinist si n-au
`original_title` (0 din 233 il au). Deci 44% din buget statea deoparte pentru o coada goala
in timp ce fiecare rulare amana iteme noi.

Testul care conteaza cel mai mult NU e aritmetica plafonului, ci `test_predicatul_e_acelasi`:
daca `upgradable()` si bucla din `upgrade_fallbacks` se despart, rezerva redevine tacut
gresita — aceeasi clasa de defect, doar mai greu de vazut. De aia predicatul e o functie, si
de aia e testat prin CE APELEAZA upgrade-ul, nu prin re-scrierea conditiei in test.
"""
import pytest

from generator import config, main


def _art(**kw) -> dict:
    """Un articol B sanatos, procesat cu versiunea curenta — deci NEeligibil implicit."""
    a = {"url": "https://ex.ro/a", "model": "B", "original_title": "Titlu brut",
         "title": "Titlu", "processed_by": "gemini", "prompt_version": config.PROMPT_VERSION}
    a.update(kw)
    return a


class _Provider:
    name = "fake"
    calls = 0
    failures = 0
    last_error = None


@pytest.fixture(autouse=True)
def reserve_env(monkeypatch):
    monkeypatch.setenv("UPGRADE_RESERVE", "8")


# --- plafonul ---------------------------------------------------------------

def test_rezerva_e_zero_cand_nu_exista_nimic_de_upgradat():
    """Cazul masurat in productie: buget 18, rezerva ceruta 8, zero candidati -> 0 retinut,
    deci `process_new` primeste toate cele 18 apeluri in loc de 10."""
    stare = [_art(url=f"https://ex.ro/{i}") for i in range(50)]
    assert main.upgradable(stare) == []
    assert main.ai_reserve(stare, 18) == 0


def test_rezerva_e_plafonata_de_cati_sunt_eligibili():
    stare = [_art(url="https://ex.ro/1", processed_by="fallback"),
             _art(url="https://ex.ro/2", prompt_version="v1-vechi"),
             _art(url="https://ex.ro/3")]
    assert main.ai_reserve(stare, 18) == 2


def test_rezerva_ramane_intreaga_cand_restanta_o_depaseste():
    """Motivul pentru care rezerva exista: un bump de PROMPT_VERSION face toata baza
    eligibila deodata, si fara ea fluxul de stiri noi ar infometa upgrade-urile la infinit."""
    stare = [_art(url=f"https://ex.ro/{i}", prompt_version="v1-vechi") for i in range(1100)]
    assert main.ai_reserve(stare, 18) == 8


def test_rezerva_nu_depaseste_bugetul():
    stare = [_art(url=f"https://ex.ro/{i}", processed_by="fallback") for i in range(20)]
    assert main.ai_reserve(stare, 5) == 5


def test_rezerva_nu_e_negativa_pe_buget_zero():
    stare = [_art(url="https://ex.ro/1", processed_by="fallback")]
    assert main.ai_reserve(stare, 0) == 0


def test_upgrade_reserve_din_mediu_e_respectat(monkeypatch):
    monkeypatch.setenv("UPGRADE_RESERVE", "2")
    stare = [_art(url=f"https://ex.ro/{i}", processed_by="fallback") for i in range(20)]
    assert main.ai_reserve(stare, 18) == 2


# --- predicatul -------------------------------------------------------------

def test_articolele_oficiale_nu_sunt_eligibile():
    """Cazul care a produs cifra falsa: 233 de articole cu `prompt_version` None, deci
    diferit de cel curent — dar fara `original_title`, deci fara text brut de reprocesat."""
    oficiale = [{"url": f"https://pl.ro/{i}", "model": "B", "processed_by": "official",
                 "prompt_version": None, "title": "Anunt"} for i in range(233)]
    assert main.upgradable(oficiale) == []


def test_clusterele_c_nu_sunt_eligibile():
    """C nu se reproceseaza — grupul sursa nu mai exista in stare."""
    assert main.upgradable([_art(model="C", processed_by="fallback")]) == []


def test_predicatul_e_acelasi_pentru_rezerva_si_pentru_upgrade(monkeypatch):
    """Garda impotriva derivei. Rezerva e utila DOAR daca numara exact ce va consuma
    upgrade-ul. Nu rescriem conditia aici: comparam ce a intors `upgradable()` cu ce a
    primit efectiv `process_single`."""
    stare = [
        _art(url="https://ex.ro/ok"),                                   # curent -> nu
        _art(url="https://ex.ro/fb", processed_by="fallback"),          # fallback -> da
        _art(url="https://ex.ro/old", prompt_version="v0"),             # prompt vechi -> da
        _art(url="https://ex.ro/nobrut", original_title=None,
             processed_by="fallback"),                                  # fara brut -> nu
        _art(url="https://ex.ro/c", model="C", processed_by="fallback"),  # C -> nu
    ]
    vazute = []
    monkeypatch.setattr(main, "process_single",
                        lambda a, p: vazute.append(a["url"]) or a)

    facute = main.upgrade_fallbacks(stare, _Provider(), remaining=99)

    assert vazute == [a["url"] for a in main.upgradable(stare)]
    assert vazute == ["https://ex.ro/fb", "https://ex.ro/old"]
    assert facute == 2


# --- comportamentul upgrade-ului ramane neschimbat ---------------------------

def test_upgradeul_respecta_bugetul_ramas(monkeypatch):
    stare = [_art(url=f"https://ex.ro/{i}", processed_by="fallback") for i in range(10)]
    vazute = []
    monkeypatch.setattr(main, "process_single",
                        lambda a, p: vazute.append(a["url"]) or a)
    assert main.upgrade_fallbacks(stare, _Provider(), remaining=3) == 3
    assert len(vazute) == 3


def test_upgradeul_se_opreste_la_primul_esec(monkeypatch):
    """Neschimbat de felia asta, dar e invariantul care protejeaza un API cazut: la primul
    None se opreste runda, nu se incearca urmatoarele."""
    stare = [_art(url=f"https://ex.ro/{i}", processed_by="fallback") for i in range(5)]
    vazute = []

    def _esec(a, p):
        vazute.append(a["url"])
        return None if len(vazute) == 2 else a

    monkeypatch.setattr(main, "process_single", _esec)
    assert main.upgrade_fallbacks(stare, _Provider(), remaining=99) == 1
    assert len(vazute) == 2


def test_fara_provider_upgradeul_nu_face_nimic(monkeypatch):
    monkeypatch.setattr(main, "process_single",
                        lambda a, p: pytest.fail("nu trebuia apelat fara provider"))
    assert main.upgrade_fallbacks([_art(processed_by="fallback")], None, remaining=9) == 0


# --- cablarea in run(): aici s-ar ascunde o greseala de racordare -------------

def _run_cu_stare(monkeypatch, stare: list) -> tuple:
    """Ruleaza `run()` cu fetch/provider/AI inlocuite. Intoarce (bugetul primit de
    process_new, stats). Nimic nu iese in retea si nu se salveaza nimic."""
    monkeypatch.setenv("MAX_AI_CALLS_PER_RUN", "18")
    monkeypatch.setattr(main.fetch, "fetch_all", lambda: ([], []))
    monkeypatch.setattr(main.state, "load", lambda: stare)
    monkeypatch.setattr(main, "get_provider", lambda: _Provider())
    monkeypatch.setattr(main, "process_single", lambda a, p: a)
    primit = []

    def _fals_process_new(items, provider, budget, existing=None):
        primit.append(budget)
        return [], set(), 0

    monkeypatch.setattr(main, "process_new", _fals_process_new)
    stats = main.run(dry_run=True)
    return primit, stats


def test_run_da_tot_bugetul_itemelor_noi_cand_nu_e_nimic_de_upgradat(monkeypatch):
    """Cazul de productie. Inainte: 10 din 18. Acum: 18 din 18."""
    primit, stats = _run_cu_stare(monkeypatch, [_art(url=f"https://ex.ro/{i}") for i in range(5)])
    assert primit == [18], "process_new n-a primit tot bugetul desi coada de upgrade e goala"
    assert stats["upgrade_reserve"] == 0
    assert stats["upgradable"] == 0
    assert stats["ai_budget"] == 18


def test_run_pastreaza_rezerva_cand_exista_restanta(monkeypatch):
    """Contra-proba: rezerva nu e desfiintata, doar plafonata. Cu 1100 de eligibili
    (scenariul unui bump de PROMPT_VERSION) se retin tot 8, deci process_new primeste 10."""
    stare = [_art(url=f"https://ex.ro/{i}", prompt_version="v1-vechi") for i in range(1100)]
    primit, stats = _run_cu_stare(monkeypatch, stare)
    assert primit == [10]
    assert stats["upgrade_reserve"] == 8
    assert stats["upgradable"] == 1100
