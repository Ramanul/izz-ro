"""Regulile despre proiect trebuie sa fie adevarate DESPRE proiect.

DE CE EXISTA (2026-08-21). Fisierele de reguli erau, pana azi, 100% persuasiune si 0% mecanica:
cautarea in `tests/` dupa `CLAUDE.md` / `specs/STATE.md` gasea doar CITARI in docstring-uri,
nicio aserttiune. Singurul hook din repo e `session-start.sh`; garzile reale (`ritm-gate`,
`comunicare-gate`) stau pe masina proprietarului, deci nu se aplica sesiunilor care ruleaza
altundeva. Rezultatul, masurat in aceeasi zi:

  · `specs/STATE.md` avea 656 de linii cu plafonul de ~40 scris in propriul lui antet — a doua
    oara, dupa ce antetul documenta deja prima data.
  · `CLAUDE.md` se descria „slabit la ~11 KB" avand 21 KB, si dadea pentru STATE.md un plafon
    de ~30 de linii cat timp STATE.md scria ~40. Doua cifre pentru o regula.
  · `ARTICLE_TTL_DAYS` a trecut 7 -> 30 in #197, dar CINCI fisiere si-au pastrat rationamentul
    pe 7. Al cincilea (`tests/test_pagina_404.py`) a fost gasit de garda asta, nu de citit.

Stratul ales e `tests/`, fiindca `tests.yml` ruleaza la fiecare PR pe ORICE masina — spre
deosebire de hook-uri. Aici stau doar regulile care se pot NUMARA. §7 sau §16 cer judecata si
raman scrise; nu tot ce conteaza e cablabil, si a pretinde altfel ar fi tot o minciuna.

CE NU ACOPERA, spus explicit: garda de TTL prinde o cifra lipita de identificator
(`ARTICLE_TTL_DAYS = 7`, `ARTICLE_TTL_DAYS (7)`). Nu poate prinde proza libera de tipul „un
articol traieste 7 zile", care e exact cealalta jumatate a driftului reparat azi in `arhiva.py`.
Limita e reala si stiuta, nu o scapare.

Fiecare garda e o functie pura care intoarce lista de incalcari, iar fiecare are test NEGATIV
pe intrare stricata dinadins. O garda care nu poate esua e mai rea decat niciuna: `IZZ-0177`
a fost fix asta — teste pe identificatori inexistenti in codul livrat, deci „verificarea nu a
rulat niciodata cu adevarat, de-aia fix-urile pareau confirmate si nu erau".
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Un PLAFON e o declaratie cu sintaxa proprie, nu proza. Asa poate garda sa deosebeasca
# „plafonul e 40" de „pana azi erau doua cifre, ~30 aici si ~40 acolo" — a doua e istorie si
# nu are voie sa declanseze nimic.
MARCAJ_KB = re.compile(r"\*\*Plafon: (\d+) KB\.\*\*")
MARCAJ_LINII = re.compile(r"\*\*Hard cap: ~(\d+) lines of content\.\*\*")
TTL_LIPIT = re.compile(r"ARTICLE_TTL_DAYS\s*(?:=|\()\s*(\d+)")
# Un nume de fisier din harta e ghilimelat si NU contine cale — asa se deosebeste
# `TASKS-B.md` (intrare in harta) de `specs/STATE.md` sau `tools/log_slice.py` (trimiteri).
NUME_MD = re.compile(r"`([A-Za-z0-9._-]+\.md)`")
TITLU_HARTA = "## 21. Harta fișierelor"
# Valoarea de referinta se CITESTE din config.py, nu se importa: garda compara declaratii de
# text, nu valori la rulare, iar `from generator import config` depinde de cwd — masurat, pica
# din alt director cu ModuleNotFoundError. Un test despre reguli n-are voie sa cada fiindca
# pipeline-ul nu s-a putut importa.
TTL_DECLARAT = re.compile(r"^ARTICLE_TTL_DAYS\s*=\s*(\d+)", re.MULTILINE)

# Fisierul asta e SINGURA exceptie de la garda de TTL, si e o exceptie de CATEGORIE, nu de
# comoditate: fixturile lui contin dinadins cifre gresite, fiindca altfel testele negative n-ar
# putea dovedi ca garda poate esua. Scanandu-se pe sine, garda si-ar raporta propriile momeli
# drept drift.
#
# CUM S-A DESCOPERIT, 2026-08-21: local a trecut fiindca fisierul era inca NEURMARIT, deci
# `git ls-files` nu-l vedea. Commit-ul insusi i-a schimbat intrarea, si CI a picat. O verificare
# facuta inainte de commit nu acopera automat starea de dupa commit — pentru orice garda care
# citeste din git, asta e o capcana permanenta, nu un accident.
SCUTITE_TTL = frozenset({"tests/test_reguli.py"})


def fisiere_urmarite(*sufixe: str) -> dict[str, str]:
    """Doar ce e in git — evita `output/`, `__pycache__` si copiile de lucru."""
    iesire = subprocess.run(["git", "ls-files", *sufixe], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout
    citite = {}
    for cale in filter(None, iesire.split("\n")):
        try:
            citite[cale] = (ROOT / cale).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return citite


def linii_de_continut(text: str) -> list[str]:
    """Liniile de dupa titlu si blocul de antet, fara cele goale."""
    linii = text.split("\n")
    i = 0
    while i < len(linii) and (not linii[i].strip()
                              or linii[i].startswith("#")
                              or linii[i].startswith(">")):
        i += 1
    return [linie for linie in linii[i:] if linie.strip()]


# --- garzile, ca functii pure -----------------------------------------------------

def incalcari_plafon_kb(text: str, octeti: int) -> list[str]:
    potrivire = MARCAJ_KB.search(text)
    if not potrivire:
        return ["nu declara niciun plafon in KB"]
    plafon = int(potrivire.group(1)) * 1024
    if octeti > plafon:
        return [f"{octeti} octeti > plafonul declarat de {plafon} ({potrivire.group(1)} KB)"]
    return []


def incalcari_plafon_linii(text: str) -> list[str]:
    potrivire = MARCAJ_LINII.search(text)
    if not potrivire:
        return ["nu declara niciun plafon in linii"]
    plafon = int(potrivire.group(1))
    real = len(linii_de_continut(text))
    if real > plafon:
        return [f"{real} linii de continut > plafonul declarat de {plafon}"]
    return []


def incalcari_ttl(fisiere: dict[str, str], asteptat: int) -> list[str]:
    gasite = []
    for cale, text in fisiere.items():
        for linie_nr, linie in enumerate(text.split("\n"), 1):
            for cifra in TTL_LIPIT.findall(linie):
                if int(cifra) != asteptat:
                    gasite.append(f"{cale}:{linie_nr} spune {cifra}, config spune {asteptat}")
    return gasite


def incalcari_unicitate(fisiere: dict[str, str], marcaj: re.Pattern, unde: str) -> list[str]:
    declara = [cale for cale, text in fisiere.items() if marcaj.search(text)]
    if declara == [unde]:
        return []
    return [f"plafonul e declarat in {declara or 'niciun fisier'}, asteptat exact in ['{unde}']"]


# --- garzile, pe repo-ul real -----------------------------------------------------

def test_claude_md_sub_plafonul_pe_care_il_declara():
    cale = ROOT / "CLAUDE.md"
    assert not incalcari_plafon_kb(cale.read_text(encoding="utf-8"), cale.stat().st_size)


def test_state_md_sub_plafonul_pe_care_il_declara():
    cale = ROOT / "specs" / "STATE.md"
    assert not incalcari_plafon_linii(cale.read_text(encoding="utf-8"))


def test_ttl_citat_in_text_e_cel_din_config():
    config_py = (ROOT / "generator" / "config.py").read_text(encoding="utf-8")
    declarat = TTL_DECLARAT.search(config_py)
    assert declarat, "generator/config.py nu declara ARTICLE_TTL_DAYS"
    fisiere = {cale: text for cale, text in fisiere_urmarite("*.py", "*.md", "*.yml").items()
               if cale not in SCUTITE_TTL}
    incalcari = incalcari_ttl(fisiere, int(declarat.group(1)))
    assert not incalcari, "rationamentul a ramas in urma constantei:\n  " + "\n  ".join(incalcari)


@pytest.mark.parametrize("marcaj,unde", [
    (MARCAJ_KB, "CLAUDE.md"),
    (MARCAJ_LINII, "specs/STATE.md"),
])
def test_fiecare_plafon_e_declarat_intr_un_singur_loc(marcaj, unde):
    """O regula, o cifra. Doua locuri inseamna ca niciuna nu se tine."""
    assert not incalcari_unicitate(fisiere_urmarite("*.md"), marcaj, unde)


# --- testele NEGATIVE: fiecare garda trebuie sa POATA esua -------------------------

def test_garda_kb_pica_pe_fisier_prea_mare():
    assert incalcari_plafon_kb("> **Plafon: 1 KB.**", 2048)


def test_garda_kb_pica_pe_fisier_fara_plafon_declarat():
    assert incalcari_plafon_kb("fara niciun marcaj", 10)


def test_garda_linii_pica_pe_fisier_prea_lung():
    antet = "# T\n> **Hard cap: ~2 lines of content.**\n\n"
    assert incalcari_plafon_linii(antet + "a\nb\nc\n")
    assert not incalcari_plafon_linii(antet + "a\nb\n")


def test_garda_ttl_pica_pe_cifra_veche():
    assert incalcari_ttl({"x.py": "# `ARTICLE_TTL_DAYS = 7`"}, 30)
    assert incalcari_ttl({"x.py": "ARTICLE_TTL_DAYS (7)"}, 30)
    assert not incalcari_ttl({"x.py": "ARTICLE_TTL_DAYS = 30"}, 30)


def test_garda_unicitate_pica_pe_cifra_declarata_de_doua_ori():
    doua = {"CLAUDE.md": "**Plafon: 24 KB.**", "ALT.md": "**Plafon: 30 KB.**"}
    assert incalcari_unicitate(doua, MARCAJ_KB, "CLAUDE.md")


def test_marcajul_nu_confunda_istoria_cu_o_declaratie():
    """Proza care POMENESTE cifre vechi nu are voie sa treaca drept declaratie de plafon."""
    istorie = {"CLAUDE.md": "pana azi erau doua cifre, ~30 aici si ~40 acolo; plafon 24 KB"}
    assert incalcari_unicitate(istorie, MARCAJ_KB, "CLAUDE.md")


# --- harta fisierelor de la radacina ---------------------------------------------

def declarate_in_harta(claude_md: str) -> set[str]:
    """Numele de .md ghilimelate in sectiunea §21, fara cele cu cale."""
    if TITLU_HARTA not in claude_md:
        return set()
    bloc = claude_md.split(TITLU_HARTA, 1)[1]
    bloc = re.split(r"\n## ", bloc, maxsplit=1)[0]
    return set(NUME_MD.findall(bloc))


def incalcari_harta(declarate: set[str], reale: set[str]) -> list[str]:
    nedeclarate = sorted(reale - declarate)
    fantome = sorted(declarate - reale)
    incalcari = []
    if nedeclarate:
        incalcari.append(f"la radacina dar nedeclarate in §21: {nedeclarate}")
    if fantome:
        incalcari.append(f"declarate in §21 dar inexistente: {fantome}")
    return incalcari


def test_harta_acopera_exact_fisierele_de_la_radacina():
    """Un .md nou la radacina pica CI-ul pana primeste un rol scris. Asa nu se intoarce sprawl-ul."""
    urmarite = fisiere_urmarite("*.md")
    reale = {cale for cale in urmarite if "/" not in cale}
    declarate = declarate_in_harta((ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
    assert not incalcari_harta(declarate, reale)


def test_garda_hartii_pica_pe_fisier_nedeclarat():
    assert incalcari_harta({"CLAUDE.md"}, {"CLAUDE.md", "REGULI-NOI.md"})


def test_garda_hartii_pica_pe_intrare_fantoma():
    assert incalcari_harta({"CLAUDE.md", "STERS.md"}, {"CLAUDE.md"})


def test_harta_nu_confunda_o_cale_cu_o_intrare():
    """`specs/STATE.md` sau `tools/log_slice.py` sunt trimiteri, nu intrari in harta."""
    text = TITLU_HARTA + "\n- `A.md` — rol\n- vezi `specs/STATE.md` si `tools/log_slice.py`\n"
    assert declarate_in_harta(text) == {"A.md"}


def test_scutirea_ramane_o_exceptie_de_categorie_nu_o_lista_care_creste():
    """O scutire e o gaura in garda. Una singura, numita, si care chiar exista."""
    assert len(SCUTITE_TTL) == 1
    for cale in SCUTITE_TTL:
        assert (ROOT / cale).exists(), f"scutire pentru un fisier inexistent: {cale}"


# --- unicitatea ID-urilor din registru --------------------------------------------
#
# De ce EXISTA garda asta si de ce sta AICI, nu in `tools/registru.py`:
#
# `registru.py add` calculeaza „ultimul + 1" pe fisierul din ramura curenta. O verificare
# acolo n-ar prinde nimic — o ramura vede doar `main` plus pe ea insasi, deci fiecare sesiune
# paralela nimereste aceeasi cifra fara sa aiba cum sa afle. Coliziunea nu se NASTE la
# scriere; se naste la MERGE. Deci acolo trebuie prinsa, adica intr-un test care ruleaza pe
# rezultatul fuziunii.
#
# Masurat pe 2026-08-22, cu `main` la IZZ-0236 si cinci ramuri deschise: IZZ-0237 revendicat
# de #204, #205 si #210; IZZ-0238 de #204 si #210; IZZ-0239 de #203 si #210; IZZ-0240 de #206
# si #210. Doua decizii diferite sub acelasi ID rup `registru.py find` si trimiterile prin
# campul `leaga`, adica exact mecanismul pe care §20 se bazeaza ca sa opreasca re-litigarea.
# Mesajele de commit de pe #203 si #204 arata ca doua sesiuni mutasera deja randuri („second
# collision round") si coliziunea a supravietuit — fiindca fiecare fix muta o singura ramura.

REGISTRU = ROOT / "specs" / "registru.tsv"


def id_uri_registru(text: str) -> list[str]:
    """ID-urile, in ordinea din fisier. Randul de antet si liniile goale nu conteaza."""
    out = []
    for linie in text.split("\n"):
        cap = linie.split("\t", 1)[0].strip()
        if re.fullmatch(r"IZZ-\d{4}", cap):
            out.append(cap)
    return out


def incalcari_id_unic(text: str) -> list[str]:
    vazute, duble = set(), []
    for cod in id_uri_registru(text):
        if cod in vazute:
            duble.append(cod)
        else:
            vazute.add(cod)
    return [f"ID folosit de mai multe ori: {cod}" for cod in sorted(set(duble))]


def test_fiecare_id_din_registru_apare_o_singura_data():
    assert not incalcari_id_unic(REGISTRU.read_text(encoding="utf-8"))


def test_garda_id_pica_pe_acelasi_id_de_doua_ori():
    """Testul negativ: exact tiparul care se produce cand doua ramuri fuzioneaza."""
    doua = "IZZ-0237\t2026-08-22\tzona\tun titlu\tblocat\n" \
           "IZZ-0237\t2026-08-22\talta\talt titlu\trespins\n"
    assert incalcari_id_unic(doua) == ["ID folosit de mai multe ori: IZZ-0237"]


def test_garda_id_nu_confunda_o_trimitere_din_text_cu_un_rand():
    """`IZZ-0177` citat in campul `motiv` al altui rand nu e un ID revendicat."""
    text = "IZZ-0240\t2026-08-22\tzona\ttitlu\tblocat\tclaude\tdovada\tvezi IZZ-0240 si IZZ-0177\n"
    assert id_uri_registru(text) == ["IZZ-0240"]
    assert not incalcari_id_unic(text)
