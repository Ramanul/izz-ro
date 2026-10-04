"""Bugetul de apeluri AI cand exista mai multi provideri gratuiti.

DE CE EXISTA. `MAX_AI_CALLS_PER_RUN` era o cifra globala. Cascada multi-provider
(`AI_ROUTER_MODE=multi` + `AI_FALLBACK_PROVIDERS=groq,cerebras`) exista deja in cod, dar cu
bugetul global ea adauga doar REZILIENTA (cand Gemini da 429, preia Groq) — nu si CAPACITATE.
Iar bugetul e saturat la fiecare rulare: `specs/ai-budget-ordering.md` masoara ca ordinea din
`config.SOURCES` functioneaza ca politica editoriala nedeclarata, pentru ca „ce ajunge la
coada e infometat". Fiecare provider free are cota proprie si niciunul nu factureaza
depasirea (`ai_gateway/registry.yaml`), deci bugetul real al unei rulari e suma cotelor.

Ce apara testele: valoarea calculata, faptul ca fara `AI_CALLS_PER_PROVIDER` comportamentul
vechi e intact (activare explicita, reversibila din mediu), si cazul negativ — un provider
fara cheie nu are voie sa umfle bugetul.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator.main import FARA_BUGET, buget_apeluri_ai  # noqa: E402
from generator.providers.base import Provider  # noqa: E402
from generator.providers.cascade import CascadeProvider  # noqa: E402


class _ProviderFals(Provider):
    """Un provider care nu vorbeste cu nimeni — doar numara."""

    def __init__(self, name: str):
        self.name = name

    def available(self) -> bool:
        return True

    def _complete(self, system: str, user: str) -> str:
        raise NotImplementedError


def _cascada(n: int) -> CascadeProvider:
    return CascadeProvider([_ProviderFals(f"p{i}") for i in range(n)])


def test_fara_per_provider_comportamentul_e_cel_vechi(monkeypatch):
    """O cifra globala, exact ca inainte — activarea ramane explicita."""
    monkeypatch.delenv("AI_CALLS_PER_PROVIDER", raising=False)
    monkeypatch.setenv("MAX_AI_CALLS_PER_RUN", "40")
    assert buget_apeluri_ai(_ProviderFals("gemini")) == 40
    # si cu o cascada de trei, tot 40: fara comutatorul nou nimic nu se inmulteste
    assert buget_apeluri_ai(_cascada(3)) == 40


def test_per_provider_inmulteste_cu_numarul_de_cote(monkeypatch):
    """Trei provideri × 40 = 120. Asta e ×3 capacitate pe aceeasi cheie Gemini."""
    monkeypatch.setenv("AI_CALLS_PER_PROVIDER", "40")
    assert buget_apeluri_ai(_ProviderFals("gemini")) == 40
    assert buget_apeluri_ai(_cascada(2)) == 80
    assert buget_apeluri_ai(_cascada(3)) == 120


def test_fara_provider_bugetul_ramane_nelimitat(monkeypatch):
    """Fara nicio cheie nu exista cota de epuizat: fallback-ul determinist e gratuit."""
    monkeypatch.setenv("AI_CALLS_PER_PROVIDER", "40")
    assert buget_apeluri_ai(None) == FARA_BUGET


def test_cascada_goala_nu_da_buget_zero(monkeypatch):
    """Caz negativ: o cascada fara membri nu trebuie sa opreasca rularea (buget 0)."""
    monkeypatch.setenv("AI_CALLS_PER_PROVIDER", "40")
    assert buget_apeluri_ai(CascadeProvider([])) == 40


def test_per_provider_gol_inseamna_neactivat(monkeypatch):
    """`AI_CALLS_PER_PROVIDER=""` (forma in care build.yml il paseaza cand cheia lipseste)
    nu trebuie sa inmulteasca nimic."""
    monkeypatch.setenv("AI_CALLS_PER_PROVIDER", "   ")
    monkeypatch.setenv("MAX_AI_CALLS_PER_RUN", "40")
    assert buget_apeluri_ai(_cascada(3)) == 40


def test_un_provider_are_o_cota():
    """Contractul de baza: `numar_provideri()` e 1 pentru un provider singur."""
    assert _ProviderFals("x").numar_provideri() == 1
    assert _cascada(4).numar_provideri() == 4


def test_provideri_duplicati_nu_umfla_bugetul(monkeypatch):
    """`get_provider()` deduplica dupa nume inainte sa construiasca cascada; verificam ca
    bugetul numara ce a ramas, nu ce s-a cerut in `AI_FALLBACK_PROVIDERS`."""
    monkeypatch.setenv("AI_CALLS_PER_PROVIDER", "40")
    acelasi = _ProviderFals("gemini")
    assert CascadeProvider([acelasi]).numar_provideri() == 1
    assert buget_apeluri_ai(CascadeProvider([acelasi])) == 40


def test_build_yml_are_comutatorul():
    """Garda de cablaj: workflow-ul de productie trebuie sa paseze comutatorul, altfel
    functia de mai sus ramane cod mort in CI (singurul loc unde ruleaza pipeline-ul)."""
    cu_open = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           ".github", "workflows", "build.yml")
    with open(cu_open, encoding="utf-8") as fh:
        yml = fh.read()
    assert "AI_CALLS_PER_PROVIDER" in yml, (
        "build.yml nu paseaza AI_CALLS_PER_PROVIDER — bugetul pe provideri nu e activ in CI")
    assert "AI_FALLBACK_PROVIDERS" in yml, (
        "build.yml nu declara providerii de rezerva — cascada ar ramane pe un singur provider")


def test_cheile_noi_chiar_construiesc_cascada(monkeypatch):
    """Cablaj real, nu doar aritmetica: cu chei de Groq+Cerebras, `get_provider()` intoarce o
    cascada cu doua cote, deci bugetul chiar se dubleaza.

    Fara testul asta, `buget_apeluri_ai` ar putea fi corect si totusi inutil — de exemplu daca
    `AI_ROUTER_MODE` n-ar mai ajunge la `process.get_provider()`, cascada ar ramane pe un
    singur provider iar inmultirea ar intoarce mereu 1. Cheile sunt false: niciun apel nu
    pleaca nicaieri, `available()` verifica doar prezenta cheii si a endpointului.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_ROUTER_MODE", "multi")
    monkeypatch.setenv("AI_FALLBACK_PROVIDERS", "groq,cerebras")
    monkeypatch.setenv("GROQ_API_KEY", "cheie-falsa-groq")
    monkeypatch.setenv("CEREBRAS_API_KEY", "cheie-falsa-cerebras")
    monkeypatch.setenv("AI_FALLBACK_OLLAMA", "0")   # Ollama nu ruleaza in CI
    monkeypatch.setenv("AI_CALLS_PER_PROVIDER", "40")
    monkeypatch.setenv("MAX_AI_CALLS_PER_RUN", "40")

    import importlib

    from generator import config, process
    importlib.reload(config)
    importlib.reload(process)
    try:
        p = process.get_provider()
        assert p is not None, "nicio cheie n-a produs un provider disponibil"
        assert p.numar_provideri() == 2, (
            f"cascada are {p.numar_provideri()} cote, astept 2 (groq+cerebras); "
            f"nume construit: {p.name}")
        from generator.main import buget_apeluri_ai as _b
        assert _b(p) == 80
    finally:
        importlib.reload(config)
        importlib.reload(process)
