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


# --- fapte canonice: ce spune regula despre proiect trebuie sa fie ce e in proiect ------------
#
# DE CE EXISTA (F2, 2026-08-29). Auditul din `specs/regim-reguli.md` a gasit sapte corectii de
# fapt, si patru sunt aceeasi greseala: un fisier de reguli CITEAZA ceva din cod — o sectiune, o
# cifra de config, un cron, o cale — si codul s-a mutat de sub citat.
#   · K2: arhiva scria cron `13 */2` dupa ce `build.yml` trecuse la `13 * * * *`.
#   · K4: `REGULI-SINTEZA.md` trimitea la `config.py:230`; valoarea era la `:306`.
#   · K8: `/audit` trimitea la un baseline mutat cu trei saptamani inainte.
#   · K9: `/slice` punea clustering-ul in §10; clustering e §7.
# Toate patru au fost reparate MANUAL in F1 (#226). Manual inseamna ca se intorc: nimic nu le
# opreste sa drifteze din nou. De-aia F1 nu e suficient si de-aia astea sunt teste, nu inca un
# paragraf care cere atentie.
#
# CE E „NORMATIV" si de ce nu tot repo-ul: normative sunt fisierele care spun ce SA FACI.
# Arhivele (`specs/istoric-*.md`, `sessions/`, `notes/`) sunt dinadins in afara — ele consemneaza
# cifre vechi ca istorie, si a le cere sa fie curente ar insemna sa le stergem exact ce au de
# spus. E aceeasi taietura pe care o face deja `test_marcajul_nu_confunda_istoria_cu_o_declaratie`
# intre „plafonul e 24 KB" si „pana azi erau doua cifre".
#
# CE NU ACOPERA, spus explicit: garzile prind CITATE cu sintaxa proprie — `§7`, `NUME = 22`, un
# cron in backtick-uri, o cale in backtick-uri. Nu pot prinde proza libera („cadenta e la doua
# ore", „constanta aia e douazeci si doi"), care e cealalta jumatate a driftului. Limita e reala
# si stiuta, ca la garda de TTL — nu o scapare.

NORMATIVE = frozenset({"CLAUDE.md", "AGENTS.md", "REGULI-SINTEZA.md", "README.md", "REVIEW.md"})
PREFIXE_NORMATIVE = (".claude/commands/", ".claude/agents/")

SECTIUNE_DEF = re.compile(r"^##+\s*(\d+[a-z]?)\.", re.MULTILINE)
SECTIUNE_REF = re.compile(r"§\s?(\d+[a-z]?)")
# `§N` e un spatiu de nume folosit de DOUA documente (K3 din audit): `CLAUDE.md` numeroteaza
# §0-§21, iar `REGULI-SINTEZA.md` isi numeroteaza propriile §1-§6. Harta e scrisa explicit, nu
# dedusa din „fisierul isi are propriile sectiuni": `.claude/commands/handoff.md` isi numeroteaza
# pasii `## 1.`..`## 8.`, dar `§15` de acolo e al lui CLAUDE.md, nu al lui.
PROPRIETAR_SECTIUNI = {"REGULI-SINTEZA.md": "REGULI-SINTEZA.md"}
DOCUMENT_IMPLICIT = "CLAUDE.md"

CONST_DEFINITA = re.compile(r"^([A-Z][A-Z0-9_]{3,})\s*=\s*(\d+)", re.MULTILINE)
CONST_CITATA = re.compile(r"`?([A-Z][A-Z0-9_]{3,})`?\s*=\s*`?(\d+)`?")

CRON_REAL = re.compile(r"cron:\s*[\"']([^\"']+)[\"']")
CRON_CITAT = re.compile(r"`([-\d*/,]+(?: [-\d*/,]+){4})`")

CALE_CITATA = re.compile(
    r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|sh|yml|yaml|md|css|html|json|tsv|svg))`")


def fisiere_normative() -> dict[str, str]:
    """Doar fisierele care spun ce sa faci. Arhivele si notele raman in afara, deliberat."""
    return {cale: text for cale, text in fisiere_urmarite("*.md").items()
            if cale in NORMATIVE or cale.startswith(PREFIXE_NORMATIVE)}


def incalcari_sectiuni(fisiere: dict[str, str], sectiuni: dict[str, set[str]],
                       proprietari: dict[str, str], implicit: str) -> list[str]:
    """Orice §N citat in proza normativa trebuie sa existe in documentul care detine numarul.

    Antetul unui fisier e PROVENIENTA, nu trimitere: „istoric §9/§11 → arhiva" spune unde a
    PLECAT o sectiune, deci n-are voie sa ceara ca ea sa mai existe. De-aia se citesc doar
    `linii_de_continut`, aceeasi taietura folosita de garda de plafoane.
    """
    gasite = []
    for cale, text in sorted(fisiere.items()):
        document = proprietari.get(cale, implicit)
        exista = sectiuni.get(document, set())
        for linie in linii_de_continut(text):
            for referinta in SECTIUNE_REF.findall(linie):
                if referinta not in exista:
                    gasite.append(f"{cale} trimite la §{referinta}, inexistenta in {document}")
    return gasite


def incalcari_constante(fisiere: dict[str, str], definite: dict[str, str]) -> list[str]:
    """O constanta de config citata cu valoare trebuie sa aiba valoarea din `config.py`."""
    gasite = []
    for cale, text in sorted(fisiere.items()):
        for linie_nr, linie in enumerate(text.split("\n"), 1):
            for nume, cifra in CONST_CITATA.findall(linie):
                if nume in definite and definite[nume] != cifra:
                    gasite.append(
                        f"{cale}:{linie_nr} spune {nume} = {cifra}, config.py spune {definite[nume]}")
    return gasite


def incalcari_cron(fisiere: dict[str, str], reale: set[str]) -> list[str]:
    """Un cron citat intr-un fisier normativ trebuie sa fie unul care chiar ruleaza."""
    gasite = []
    for cale, text in sorted(fisiere.items()):
        for linie_nr, linie in enumerate(text.split("\n"), 1):
            for citat in CRON_CITAT.findall(linie):
                if citat not in reale:
                    gasite.append(f"{cale}:{linie_nr} citeaza cron `{citat}`, care nu e in niciun workflow")
    return gasite


def incalcari_cai(fisiere: dict[str, str], urmarite: set[str]) -> list[str]:
    """O cale citata intr-un fisier normativ trebuie sa existe.

    Rezolvarea, in trei categorii — nu o lista de scutiri:
      · nume simplu (`gemini.py`) → trece daca exista undeva in repo. E prescurtarea folosita
        dupa ce calea intreaga a fost scrisa o data in acelasi paragraf.
      · cale al carei prim segment NU e un director din repo (`izz/CLAUDE.md`) → in afara
        scopului: `/handoff` coordoneaza cu alt arbore, de pe masina proprietarului.
      · restul → trebuie sa existe exact cum e scrisa.
    """
    nume_simple = {cale.rsplit("/", 1)[-1] for cale in urmarite}
    directoare = {cale.split("/", 1)[0] for cale in urmarite if "/" in cale}
    gasite = []
    for cale, text in sorted(fisiere.items()):
        for linie_nr, linie in enumerate(text.split("\n"), 1):
            for citata in CALE_CITATA.findall(linie):
                if "/" not in citata:
                    if citata not in nume_simple:
                        gasite.append(f"{cale}:{linie_nr} citeaza `{citata}`, inexistent in repo")
                    continue
                if citata.split("/", 1)[0] not in directoare:
                    continue
                if citata not in urmarite:
                    gasite.append(f"{cale}:{linie_nr} citeaza `{citata}`, care nu exista")
    return gasite


# --- garzile de fapte canonice, pe repo-ul real ----------------------------------------------

def test_fiecare_trimitere_la_sectiune_are_tinta():
    """K8/K9: o comanda care trimite la o sectiune mutata inventeaza o regula inexistenta."""
    fisiere = fisiere_normative()
    sectiuni = {document: set(SECTIUNE_DEF.findall((ROOT / document).read_text(encoding="utf-8")))
                for document in {DOCUMENT_IMPLICIT, *PROPRIETAR_SECTIUNI.values()}}
    assert not incalcari_sectiuni(fisiere, sectiuni, PROPRIETAR_SECTIUNI, DOCUMENT_IMPLICIT)


def test_fiecare_constanta_citata_are_valoarea_din_config():
    """K4: `TITLE_MAX_WORDS = 22` scris intr-o regula trebuie sa fie 22 si in `config.py`."""
    definite = dict(CONST_DEFINITA.findall(
        (ROOT / "generator/config.py").read_text(encoding="utf-8")))
    assert not incalcari_constante(fisiere_normative(), definite)


def test_fiecare_cron_citat_e_unul_care_ruleaza():
    """K2: cadenta scrisa in reguli trebuie sa fie cea din `.github/workflows/`."""
    reale = set()
    for workflow in sorted((ROOT / ".github/workflows").glob("*.yml")):
        reale |= set(CRON_REAL.findall(workflow.read_text(encoding="utf-8")))
    assert reale, "niciun cron gasit in workflows — garda ar trece degeaba"
    assert not incalcari_cron(fisiere_normative(), reale)


def test_fiecare_cale_citata_exista():
    """K8: un fisier mutat lasa in urma comenzi care trimit in gol."""
    urmarite = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                                  text=True, check=True).stdout.split("\n")) - {""}
    assert not incalcari_cai(fisiere_normative(), urmarite)


# --- fiecare garda de fapte trebuie sa poata ESUA --------------------------------------------

def test_garda_sectiunilor_pica_pe_trimitere_moarta():
    stricat = {"x.md": "prima linie\nvezi §99 pentru detalii"}
    assert incalcari_sectiuni(stricat, {"CLAUDE.md": {"7"}}, {}, "CLAUDE.md")


def test_garda_sectiunilor_respecta_proprietarul_numarului():
    """§6 exista in REGULI-SINTEZA dar nu in CLAUDE.md — harta decide, nu norocul."""
    fisiere = {"REGULI-SINTEZA.md": "prima linie\nvezi §6"}
    sectiuni = {"CLAUDE.md": {"7"}, "REGULI-SINTEZA.md": {"6"}}
    assert not incalcari_sectiuni(fisiere, sectiuni, {"REGULI-SINTEZA.md": "REGULI-SINTEZA.md"},
                                  "CLAUDE.md")
    assert incalcari_sectiuni(fisiere, sectiuni, {}, "CLAUDE.md")


def test_garda_sectiunilor_nu_confunda_antetul_cu_o_trimitere():
    """„istoric §9 → arhiva" spune unde a plecat sectiunea, nu ca ea mai exista."""
    antet = "# Titlu\n> istoric §9/§11 → `specs/istoric-operational.md`\n\ncorp fara trimiteri\n"
    assert not incalcari_sectiuni({"CLAUDE.md": antet}, {"CLAUDE.md": {"7"}}, {}, "CLAUDE.md")


def test_garda_constantelor_pica_pe_cifra_veche():
    stricat = {"x.md": "`TITLE_MAX_WORDS = 12` e plasa de siguranta"}
    assert incalcari_constante(stricat, {"TITLE_MAX_WORDS": "22"})


def test_garda_constantelor_ignora_ce_nu_e_in_config():
    """O constanta care nu e din `config.py` nu e treaba garzii — altfel raporteaza zgomot."""
    assert not incalcari_constante({"x.md": "`HTTP_TIMEOUT = 5`"}, {"TITLE_MAX_WORDS": "22"})


def test_garda_cronului_pica_pe_cadenta_veche():
    assert incalcari_cron({"x.md": "`build.yml` are cron `13 */2 * * *`"}, {"13 * * * *"})


def test_garda_cailor_pica_pe_fisier_mutat():
    assert incalcari_cai({"x.md": "vezi `specs/mutat.md`"}, {"specs/registru.tsv"})


def test_garda_cailor_accepta_prescurtarea_si_ignora_alt_arbore():
    """`gemini.py` dupa calea intreaga e prescurtare; `izz/CLAUDE.md` e alt arbore, nu drift."""
    urmarite = {"generator/providers/gemini.py", "CLAUDE.md"}
    assert not incalcari_cai({"x.md": "`gemini.py` si `izz/CLAUDE.md`"}, urmarite)
    assert incalcari_cai({"x.md": "`lipsa.py`"}, urmarite)


def test_harta_sectiunilor_ramane_o_categorie_nu_o_lista_care_creste():
    """Un al treilea document care isi revendica §N inseamna ca `§` a incetat sa mai spuna ceva."""
    assert len(PROPRIETAR_SECTIUNI) == 1
    for cale, document in PROPRIETAR_SECTIUNI.items():
        assert (ROOT / cale).exists(), f"proprietar pentru un fisier inexistent: {cale}"
        assert cale == document, "un fisier isi detine propriile sectiuni sau deloc"
