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
# `.claude/reguli/` intra aici de la F4 (2026-08-30): o regula mutata in L1 ramane
# normativa: citeaza sectiuni, cai si constante exact ca `CLAUDE.md`, deci trebuie sa
# treaca prin aceleasi patru garzi de fapte. Altfel mutarea ar fi fost o evadare.
PREFIXE_NORMATIVE = (".claude/commands/", ".claude/agents/", ".claude/reguli/")

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


# --- censul regulilor cu nume: o regula nu are voie sa dispara tacut ---------------------------
#
# DE CE EXISTA (F3, 2026-08-29). Pe 2026-08-06 taierea lui `CLAUDE.md` a pierdut 13 reguli si
# nimic n-a semnalat. Redescoperirea lor a costat o sesiune intreaga de arheologie pe git (#226),
# si tot manuala a fost. Garda asta face stergerea imposibil de facut tacut: numele regulii e
# scris aici, deci ca sa dispara din `CLAUDE.md` trebuie sters si de aici — act vizibil, in
# acelasi diff, vazut de acelasi reviewer.
#
# DE CE NU ancore `[R-nnn]`, cum era planul initial: MASURAT, nu presupus. 70 de enunturi x 8
# octeti = 560 de octeti in `CLAUDE.md`, iar dupa #226 raman 186 liberi din 24.576. Nu incap —
# si a ridica plafonul ca sa incapa niste ancore ar fi exact inversul scopului. Amprenta aleasa
# e capul INGROSAT al regulii, adica numele ei: costa zero octeti fiindca e deja scris.
#
# UN SINGUR SENS, deliberat: garda prinde DISPARITIA, nu aparitia. Problema documentata a fost
# pierderea tacuta; o regula noua se vede oricum in diff-ul lui `CLAUDE.md`. (Harta §21 merge in
# ambele sensuri fiindca acolo un fisier nou chiar avea nevoie de un rol declarat.) Consecinta
# practica: ordinea in care aterizeaza doua PR-uri nu poate face CI rosu pe merge-ul altcuiva.
#
# CE NU ACOPERA, spus explicit: doar regulile cu CAP INGROSAT. Cele 23 de sub-puncte fara nume
# sunt parte din regula-parinte si nu au identitate proprie. Si o REFORMULARE a numelui pica
# garda — intentionat: numele unei reguli e identitatea ei, iar schimbarea lui merita sa fie un
# act vizibil, nu o alunecare. Cele 47 de mai jos sunt verificate ca fiind prezente si pe `main`,
# si pe ramura lui #226, deci niciuna nu depinde de ordinea de aterizare.

CAP_DE_REGULA = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\*\*(.+?)\*\*", re.MULTILINE)

REGULI_ACTIVE = frozenset({
    'Fii proactiv',
    'Starea de completare ÎNAINTE de rezultat, ca fracție',
    'Mandatul e ce a cerut proprietarul, nu ce a ajuns ultimul în context — REGULĂ TARE.',
    'Inventarul uneltelor (§12a).',
    'Spec întâi.',
    'Plan înainte de muncă netrivială.',
    'Felii verticale.',
    'Verifică rulând, nu declarând.',
    'Commit pe verde.',
    'Diff minim.',
    'Fără output stricat.',
    'O axă, o casă.',
    'Schimbările de clustering se verifică empiric.',
    'Diversitatea surselor.',
    'Formula de atribuire — PERMANENTĂ (decizie proprietar 2026-07-04).',
    'Nu confunda unealta cu capacitatea.',
    'O limitare se declară cu comanda care a eșuat, nu din memorie.',
    'Verificările care merită, ieftine, la început:',
    'Ce lipsește dar se poate obține → propune, nu ocoli tăcut.',
    'Ține-l scurt.',
    'Nu arma nicio buclă autonomă / CronCreate recurent',
    'Cine face merge în `main`',
    'După orice merge, anunță celălalt cont',
    'Nu face curse pe `main`.',
    'Nu face niciodată merge în `main`.',
    'Un task per declanșare',
    'Se oprește și raportează în loc să ghicească.',
    'Actualizează `specs/STATE.md`',
    'Verifică în AMBELE roluri.',
    'Verifică LIVRABILITATEA, nu doar corectitudinea.',
    'Trei stări distincte — nu le confunda, folosește cuvintele exacte:',
    'Când nu poți testa ceva, spune explicit',
    'Un task, o sesiune.',
    'Nu trage niciodată un payload mare în context.',
    'Model pe măsura muncii.',
    'Sub-agenții costă ~5.6× per linie livrată',
    'Agenții împart working tree-ul.',
    'Fișierele de reguli se plătesc la fiecare tură.',
    'Înainte să propui orice, caută:',
    'O decizie care NU produce un PR primește un rând în aceeași tură',
    '`motiv` e obligatoriu',
    'Append-only.',
    'Un `find` gol NU e dovadă că nu s-a încercat',
})

# Stratul L1 (F4, 2026-08-30): regulile conditionate NU mai stau in `CLAUDE.md` — se livreaza
# de hook-ul `PostToolUse` cand atingi fisierul care le declanseaza. Censul le urmareste la fel,
# in fisierul lor: altfel mutarea din L0 in L1 ar fi fost chiar gaura pe care F3 o inchidea.
REGULI_L1 = {
    ".claude/reguli/13-frontend.md": frozenset({
        'După orice felie care schimbă output-ul de front-end',
        'Rulează 3+ repetări per revizie și compară medianele',
        'Măsurătoarea e busolă, nu pilot automat.',
        'Baseline, cifre, ipoteze picate (CLS, fonturi, consent) → `specs/masuratori-frontend.md`.',
    }),
}

CENS = {"CLAUDE.md": REGULI_ACTIVE, **REGULI_L1}


def capete_de_regula(text: str) -> set[str]:
    """Numele regulilor: capul ingrosat al unui bullet. `**text**` din mijlocul frazei nu e nume."""
    return set(CAP_DE_REGULA.findall(text))


def incalcari_cens(active: frozenset[str], prezente: set[str]) -> list[str]:
    return [f"regula «{nume}» e in cens dar a disparut din CLAUDE.md — daca e intentionat, "
            f"scoate-o si din REGULI_ACTIVE, in acelasi diff"
            for nume in sorted(active - prezente)]


@pytest.mark.parametrize("fisier", sorted(CENS))
def test_nicio_regula_din_cens_nu_a_disparut(fisier):
    """Cele 13 reguli pierdute pe 2026-08-06 au disparut fara ca nimic sa pice. Acum pica."""
    prezente = capete_de_regula((ROOT / fisier).read_text(encoding="utf-8"))
    assert not incalcari_cens(CENS[fisier], prezente)


def test_garda_censului_pica_pe_regula_stearsa():
    assert incalcari_cens(frozenset({"Diff minim.", "Spec intai."}), {"Diff minim."})


def test_censul_nu_confunda_ingrosarea_din_proza_cu_un_nume_de_regula():
    """`- text cu **accent** la mijloc` nu e o regula noua, e o sublinierea intr-o fraza."""
    text = "- **Diff minim.** fara refactorizari\n- o fraza cu **accent** pe un cuvant\n"
    assert capete_de_regula(text) == {"Diff minim."}


@pytest.mark.parametrize("fisier", sorted(CENS))
def test_censul_ramane_un_cens_nu_un_esantion(fisier):
    """Miscarea care ar goli garda fara sa stearga nicio regula: sa nu mai urmareasca decat cateva."""
    prezente = capete_de_regula((ROOT / fisier).read_text(encoding="utf-8"))
    assert len(CENS[fisier]) >= 0.9 * len(prezente), (
        f"{fisier}: censul urmareste {len(CENS[fisier])} din {len(prezente)} reguli cu nume")


# --- STATE.md nu are voie sa numeasca deschis un PR deja integrat ------------------------------
#
# DE CE EXISTA (2026-08-30; garda vine din #230, dusa mai departe aici). Antetul lui
# `specs/STATE.md` documenteaza singur, de DOUA ori, acelasi esec: sectiuni scrise `Open PR`
# pentru PR-uri deja merged (#196, #197 pe 08-21; la fel la taierea din 08-07). A treia oara s-a
# intamplat azi: `## Open` scria «PR-uri deschise: #203 #204 #207 #214» dupa ce #203 si #204
# aterizasera amandoua. Costul nu e cosmetic — sesiunea urmatoare citeste STATE.md la pornire si
# reimplementeaza ce a aterizat deja.
#
# CUM MASOARA, fara retea: un PR integrat lasa pe `main` un commit «Merge pull request #N».
# Masurat pe repo-ul real: 27 de merge-uri, 27 de numere distincte, deci forma e consecventa.
# Semnalul e sigur INTR-UN SINGUR SENS — un astfel de commit dovedeste ca PR-ul s-a integrat;
# lipsa lui NU dovedeste ca e deschis (un merge facut altfel nu lasa urma). Garda foloseste doar
# sensul sigur, deci poate rata, dar nu poate acuza pe nedrept. Din acelasi motiv un numar de
# ISSUE (#198) trece nevatamat: nu are commit de merge.
#
# CE LIPSEA LA PRIMA SCRIERE — masurat, nu dedus. `actions/checkout` cloneaza implicit cu
# `fetch-depth: 1`. Rulat pe o clona `--depth 1` a repo-ului asta: 1 commit vizibil, `git log
# --grep` intoarce ZERO merge-uri, deci multimea celor integrate iese vida si garda trecea verde
# fara sa masoare nimic. Adica exact `IZZ-0177`, esecul pe care docstring-ul de sus il numeste:
# „o garda care nu poate esua e mai rea decat niciuna". Reparat in doua locuri — `tests.yml` cere
# acum istoricul complet, iar garda REFUZA sa treaca cand nu poate masura, in loc sa taca.
#
# Semnalul corect e NUMARUL DE MERGE-URI VIZIBILE, nu steagul de clona superficiala: prima
# versiune a acestei garzi asculta `git rev-parse --is-shallow-repository` si a picat pe loc pe
# checkout-ul acestei sesiuni, care raporteaza `true` desi are 227 de commit-uri si toate cele 27
# de merge-uri (o clona superficiala adancita ulterior de `fetch`). Steagul si capacitatea de a
# masura sunt lucruri diferite; garda intreaba direct ce o intereseaza.
#
# CONVENTIA, ca sa nu fie nevoie de ghicit intentia: un PR integrat POATE fi pomenit in `## Open`
# — dar numai adnotat `#NNN (merged)`. Asa se deosebeste mecanic o trimitere la istorie
# («aterizat prin #229 (merged)») de o afirmatie ca lucrarea e inca deschisa. O singura
# conventie, nu o lista de cuvinte-cheie care creste.

PR_CITAT = re.compile(r"#(\d{2,4})(\s*\(merged\))?")
MERGE_PE_MAIN = re.compile(r"^Merge pull request #(\d+)", re.MULTILINE)


def sectiunea_open(text: str) -> str:
    """Sectiunea, nu prima potrivire de sir: antetul lui STATE.md POMENESTE `## Open` in proza
    („the 195-line `## Open` section"), iar un `split` naiv taia acolo si garda citea antetul in
    loc de sectiune. Prins in #230 la prima rulare pe fisierul real, nu pe fixtura."""
    titlu = re.search(r"^## Open\s*$", text, re.MULTILINE)
    if not titlu:
        return ""
    return re.split(r"^## ", text[titlu.end():], maxsplit=1, flags=re.MULTILINE)[0]


def numere_de_merge(subiecte: str) -> set[str]:
    """Functie pura peste iesirea lui `git log --format=%s`, ca sa poata avea test negativ."""
    return set(MERGE_PE_MAIN.findall(subiecte))


def incalcari_pr_fantoma(open_text: str, integrate: set[str]) -> list[str]:
    gasite = []
    for numar, adnotat in PR_CITAT.findall(open_text):
        if numar in integrate and not adnotat:
            gasite.append(
                f"#{numar} e scris in ## Open dar are deja merge pe main — scoate-l, sau "
                f"adnoteaza-l `#{numar} (merged)` daca e trimitere la istorie")
    return sorted(set(gasite))


def _git(*argumente: str) -> str | None:
    """None inseamna «nu am putut masura», si NU se confunda cu «n-am gasit nimic»."""
    try:
        return subprocess.run(["git", *argumente], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def merge_uri_vizibile() -> set[str]:
    return numere_de_merge(_git("log", "--format=%s", "--grep=^Merge pull request #") or "")


def test_istoricul_permite_garzii_sa_masoare():
    """Garda de mai jos e vida pe un istoric taiat. Atunci pica ASTA, cu ce trebuie facut."""
    assert _git("rev-parse", "HEAD") is not None, "git nu raspunde — garda nu poate masura"
    assert merge_uri_vizibile(), (
        "niciun commit «Merge pull request #N» vizibil: istoricul e taiat, deci garda de PR "
        "fantoma ar trece degeaba — pune `fetch-depth: 0` la actions/checkout")


def test_open_nu_contine_pr_uri_deja_integrate():
    """A treia oara ar fi fost tot tacuta. Acum pica."""
    text = (ROOT / "specs/STATE.md").read_text(encoding="utf-8")
    open_text = sectiunea_open(text)
    assert open_text.strip(), "sectiunea ## Open nu a fost gasita — garda ar trece degeaba"
    assert not incalcari_pr_fantoma(open_text, merge_uri_vizibile())


def test_garda_pr_fantoma_pica_pe_pr_integrat():
    assert incalcari_pr_fantoma("- **#226** asteapta merge", {"226"})


def test_garda_pr_fantoma_accepta_trimiterea_adnotata():
    """„aterizat prin #229 (merged)" e istorie, nu o afirmatie ca lucrarea e deschisa."""
    assert not incalcari_pr_fantoma("- F4 a aterizat prin #229 (merged)", {"229"})


def test_garda_pr_fantoma_nu_atinge_un_pr_chiar_deschis():
    assert not incalcari_pr_fantoma("- **#999** verde, asteapta merge", {"226"})


def test_garda_pr_fantoma_lasa_in_pace_un_numar_de_issue():
    """#198 e issue deschis de proprietar: n-are commit de merge, deci nu intra in multime."""
    assert not incalcari_pr_fantoma("- **Arhiva (#198)** ramane de decis", {"229"})


def test_numerele_de_merge_sunt_vide_pe_istoric_superficial():
    """Intrarea stricata dinadins: exact ce intoarce `git log` intr-o clona `--depth 1`."""
    assert numere_de_merge("") == set()
    assert numere_de_merge("update content\nfix(trafic): garda de endpoint") == set()


def test_sectiunea_open_se_opreste_la_titlul_urmator():
    """Altfel garda ar citi si `## Standing rules`, unde trimiterile la istorie sunt normale."""
    text = "# T\n\n## Open\n\n- #1\n\n## Standing rules\n\n- #2\n"
    assert "#1" in sectiunea_open(text) and "#2" not in sectiunea_open(text)
