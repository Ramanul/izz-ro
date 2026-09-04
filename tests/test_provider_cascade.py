"""`CascadeProvider` decide CINE raspunde cand primul provider cade. Avea 0% coverage.

DE CE EXISTA (`IZZ-0282`, masurat 2026-09-02 pe suita completa): `providers/cascade.py`
avea 18 instructiuni si 18 neatinse. Zero pe wrapper-ele de retea (gemini, anthropic,
ollama) e o alegere aparabila — sunt I/O. Zero aici nu e: modulul e logica pura si
decide comportamentul pe care nu-l vezi pana in ziua in care conteaza.

Ce apara testele, in ordinea gravitatii daca s-ar strica:

  1. ORDINEA. Docstring-ul modulului promite explicit „Niciodata invers: Gemini/Anthropic
     raman intai in lista, Ollama e completarea, nu inlocuirea". O inversare ar muta tot
     traficul pe modelul local — mai lent, alta calitate — fara sa pice nimic.
  2. TRECEREA LA URMATORUL doar la ESEC, nu la fiecare apel.
  3. EXCEPTIA PASTRATA: cand toti cad, se re-arunca ULTIMA eroare reala, nu una generica.
     Altfel `ai_last_error` din build.json (`main.py:466`) devine inutil pentru diagnostic.
"""
import pytest

from generator.providers.base import Provider
from generator.providers.cascade import CascadeProvider


class _Fals(Provider):
    """Provider de test: raspunde, cade, sau se declara indisponibil."""

    def __init__(self, nume, raspuns=None, exceptie=None, disponibil=True):
        self.name = nume
        self._raspuns = raspuns
        self._exceptie = exceptie
        self._disponibil = disponibil
        self.apeluri = 0

    def available(self):
        return self._disponibil

    def _complete(self, system, user):
        self.apeluri += 1
        if self._exceptie:
            raise self._exceptie
        return self._raspuns


def test_primul_disponibil_raspunde_si_restul_nu_sunt_atinsi():
    a, b = _Fals("a", raspuns="din a"), _Fals("b", raspuns="din b")
    assert CascadeProvider([a, b])._complete("s", "u") == "din a"
    assert (a.apeluri, b.apeluri) == (1, 0), "al doilea provider nu se apeleaza degeaba"


def test_ordinea_din_lista_e_respectata_nu_cea_mai_rapida():
    """Promisiunea din docstring: cloud-ul intai, local-ul ca al doilea. Daca cineva
    reordoneaza lista, tot traficul se muta tacut pe modelul local."""
    cloud = _Fals("gemini", raspuns="cloud")
    local = _Fals("ollama", raspuns="local")
    assert CascadeProvider([cloud, local])._complete("s", "u") == "cloud"
    assert local.apeluri == 0


def test_esecul_primului_trece_la_al_doilea():
    cazut = _Fals("gemini", exceptie=RuntimeError("429 quota"))
    salvator = _Fals("ollama", raspuns="din ollama")
    assert CascadeProvider([cazut, salvator])._complete("s", "u") == "din ollama"
    assert (cazut.apeluri, salvator.apeluri) == (1, 1)


def test_providerul_indisponibil_e_sarit_fara_sa_fie_apelat():
    """`available()` False inseamna cheie lipsa — apelarea lui ar fi o eroare inutila."""
    fara_cheie = _Fals("gemini", raspuns="nu ar trebui", disponibil=False)
    bun = _Fals("ollama", raspuns="din ollama")
    assert CascadeProvider([fara_cheie, bun])._complete("s", "u") == "din ollama"
    assert fara_cheie.apeluri == 0


def test_cand_toti_cad_se_rearunca_ULTIMA_eroare_reala():
    """Nu una generica: `ai_last_error` din build.json e singura urma de diagnostic."""
    prim = _Fals("gemini", exceptie=RuntimeError("429 quota epuizata"))
    ultim = _Fals("ollama", exceptie=ConnectionError("ollama nu raspunde pe 11434"))
    with pytest.raises(ConnectionError, match="11434"):
        CascadeProvider([prim, ultim])._complete("s", "u")


def test_fara_niciun_provider_disponibil_eroarea_spune_de_ce():
    cascada = CascadeProvider([_Fals("gemini", disponibil=False),
                               _Fals("ollama", disponibil=False)])
    assert cascada.available() is False
    with pytest.raises(RuntimeError, match="niciun provider"):
        cascada._complete("s", "u")


def test_available_e_adevarat_daca_MACAR_unul_e_disponibil():
    cascada = CascadeProvider([_Fals("gemini", disponibil=False),
                               _Fals("ollama", disponibil=True)])
    assert cascada.available() is True


def test_numele_arata_lantul_intreg():
    """`build.json` scrie numele providerului; „gemini" singur ar ascunde ca a raspuns Ollama."""
    assert CascadeProvider([_Fals("gemini"), _Fals("ollama")]).name == "gemini+ollama"


# --- observabilitatea caderii partiale --------------------------------------------
#
# Gaura gasita scriind testele de mai sus, nu dedusa: `CascadeProvider._complete` cheama
# `p._complete(...)`, deci OCOLESTE `Provider.complete`, adica exact wrapper-ul care
# numara `calls`/`failures`. Consecinta masurata mai jos: daca Gemini cade la fiecare apel
# si Ollama salveaza fiecare articol, `provider.failures` ramane 0 si `ai_last_error`
# ramane None — iar garda de cadere sistemica din `main.py:82` (`failures >= calls`) nu se
# atinge, corect, fiindca articolele CHIAR s-au procesat.
#
# Corect pentru publicare, orb pentru operare: providerul principal poate fi mort de zile
# intregi fara nicio urma. De-aia `caderi_pe_provider()` — nu schimba nimic din ce se
# publica, doar face numarabil ce era invizibil. Aceeasi forma cu contorul de pierderi la
# ingestie (`IZZ-0272`).


def test_caderea_primului_provider_lasa_urma_chiar_daca_al_doilea_salveaza():
    cazut = _Fals("gemini", exceptie=RuntimeError("429 quota epuizata"))
    salvator = _Fals("ollama", raspuns="ok")
    cascada = CascadeProvider([cazut, salvator])
    cascada._complete("s", "u")
    cascada._complete("s", "u")
    assert cascada.caderi_pe_provider() == {"gemini": 2}, (
        "doua articole salvate de Ollama inseamna doua caderi Gemini, nu zero")


def test_fara_caderi_raportul_e_gol():
    cascada = CascadeProvider([_Fals("gemini", raspuns="ok")])
    cascada._complete("s", "u")
    assert cascada.caderi_pe_provider() == {}


def test_raportul_de_caderi_e_o_copie_nu_referinta():
    cascada = CascadeProvider([_Fals("gemini", exceptie=RuntimeError("x")),
                               _Fals("ollama", raspuns="ok")])
    cascada._complete("s", "u")
    raport = cascada.caderi_pe_provider()
    raport["gemini"] = 999
    assert cascada.caderi_pe_provider()["gemini"] == 1
