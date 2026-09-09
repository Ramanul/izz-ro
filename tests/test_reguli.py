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

import functools
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
MARCAJ_BUGET = re.compile(r"\*\*Buget de pornire: (\d+) KB\.\*\*")
MARCAJ_FAPTE = re.compile(r"\*\*Plafon: (\d+) linii de fapt\.\*\*")
# Un fapt din specs/infrastructura.md trebuie sa fie TRASABIL la registru. Fara asta ar fi doar
# proza injectata la fiecare pornire, adica exact felul in care s-a nascut IZZ-0257: o afirmatie
# lasata intr-un fisier normativ fara data si fara dovada, pe care nimeni n-a mai putut-o data.
CITARE_IZZ = re.compile(r"IZZ-(\d{4})")
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


def incalcari_plafon_fapte(text: str) -> list[str]:
    potrivire = MARCAJ_FAPTE.search(text)
    if not potrivire:
        return ["nu declara niciun plafon in linii de fapt"]
    plafon = int(potrivire.group(1))
    real = len(linii_de_continut(text))
    if real > plafon:
        return [f"{real} linii de fapt > plafonul declarat de {plafon}"]
    return []


def incalcari_trasabilitate(text: str, ids_cunoscute: set[str]) -> list[str]:
    """Fiecare fapt injectat trebuie sa poata fi verificat inapoi in registru.

    Se verifica pe BULLET, nu pe linie: un fapt se intinde pe mai multe linii, iar citarea sta
    la sfarsit. Impartind pe linii, continuarile ar cadea toate ca 'fara citare'.
    """
    incalcari: list[str] = []
    fapt: list[str] = []
    for linie in linii_de_continut(text) + ["- "]:   # santinela: inchide ultimul bullet
        if linie.startswith("- ") and fapt:
            incalcari += _verifica_fapt(" ".join(fapt), ids_cunoscute)
            fapt = []
        fapt.append(linie.strip())
    return incalcari


def _verifica_fapt(fapt: str, ids_cunoscute: set[str]) -> list[str]:
    citate = set(CITARE_IZZ.findall(fapt))
    scurt = fapt[:60]
    if not citate:
        return [f"fapt fara citare de registru: {scurt}"]
    lipsa = sorted(i for i in citate if i not in ids_cunoscute)
    if lipsa:
        return [f"fapt care citeaza ID inexistent in registru ({', '.join(lipsa)}): {scurt}"]
    return []


def ids_din_registru() -> set[str]:
    cale = ROOT / "specs" / "registru.tsv"
    return {linie.split("\t")[0].removeprefix("IZZ-")
            for linie in cale.read_text(encoding="utf-8").splitlines()[1:]
            if linie.startswith("IZZ-")}


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


# --- bugetul de pornire: plafonul se pune pe SUPRAFATA, nu pe un fisier ----------------------
#
# DE CE EXISTA (2026-09-02). Plafonul de KB pazea `CLAUDE.md` — 23.835 din 24.576 de octeti — in
# timp ce inca 12.443 de octeti la fel de scumpi intrau in aceeasi sesiune fara sa-i numere
# nimeni: iesirea hook-ului `SessionStart` (8.829, din care registrul 3.712) si frontmatter-ul
# agentilor si comenzilor (1.925 + 1.689), injectat la FIECARE tura.
#
# Consecinta masurata, si motivul pentru care garda asta nu e cosmetica: mutarea unui text din
# `CLAUDE.md` in hook SCADE cifra pazita si nu schimba NIMIC in context — ambele intra la
# pornire si raman acolo toata sesiunea. Cu o singura garda pe un singur fisier, o astfel de
# mutare se raporteaza ca economie si trece verde. Economiseste doar ce nu mai intra deloc:
# stergerea unui duplicat, compresia, sau declansatorul `PostToolUse` (stratul L1).

COMPONENTE_BUGET = (".claude/agents", ".claude/commands")


def _frontmatter(text: str) -> int:
    """Octetii dintre cele doua `---` — singura parte injectata la fiecare tura."""
    potrivire = re.match(r"^---\n(.*?)\n---", text, re.S)
    return len(potrivire.group(1).encode("utf-8")) if potrivire else 0


@functools.lru_cache(maxsize=1)
def iesirea_hookului() -> bytes:
    """Ce tipareste EFECTIV hook-ul SessionStart. Rulat o singura data pe sesiune de teste.

    Cachat fiindca il folosesc doua garzi (bugetul si injectia faptelor), iar hook-ul
    instaleaza dependente — a doua rulare ar fi minute pierdute pentru acelasi rezultat.
    """
    hook = ROOT / ".claude/hooks/session-start.sh"
    iesire = subprocess.run(["bash", str(hook)], cwd=ROOT, capture_output=True,
                            timeout=600, check=False)
    assert iesire.returncode == 0, f"hook-ul SessionStart a esuat: {iesire.stderr[:200]!r}"
    return iesire.stdout


def buget_de_pornire() -> dict[str, int]:
    """Tot ce intra in context la pornirea unei sesiuni, masurat — nu dedus.

    Hook-ul se RULEAZA, nu se aproximeaza din marimea fisierelor pe care le citeste: iesirea
    lui depinde de `tail -24` din registru si de STATE.md, deci o suma statica ar minti.
    """
    masurat = {"CLAUDE.md": (ROOT / "CLAUDE.md").stat().st_size}
    masurat["hook SessionStart"] = len(iesirea_hookului())
    for director in COMPONENTE_BUGET:
        masurat[director] = sum(_frontmatter((ROOT / cale).read_text(encoding="utf-8"))
                                for cale in fisiere_urmarite(f"{director}/*.md"))
    return masurat


def incalcari_buget(text: str, masurat: dict[str, int]) -> list[str]:
    potrivire = MARCAJ_BUGET.search(text)
    if not potrivire:
        return ["CLAUDE.md nu declara un buget de pornire — garda n-are contra ce sa masoare"]
    plafon = int(potrivire.group(1)) * 1024
    total = sum(masurat.values())
    if total <= plafon:
        return []
    defalcare = ", ".join(f"{nume} {octeti}" for nume, octeti in sorted(masurat.items()))
    return [f"bugetul de pornire e {total} octeti, peste plafonul declarat de {plafon}"
            f" ({defalcare}). Mutarea intre straturi NU ajuta: toate intra in aceeasi sesiune."]

# --- garzile, pe repo-ul real -----------------------------------------------------

def test_claude_md_sub_plafonul_pe_care_il_declara():
    cale = ROOT / "CLAUDE.md"
    assert not incalcari_plafon_kb(cale.read_text(encoding="utf-8"), cale.stat().st_size)


def test_state_md_sub_plafonul_pe_care_il_declara():
    cale = ROOT / "specs" / "STATE.md"
    assert not incalcari_plafon_linii(cale.read_text(encoding="utf-8"))


def test_infrastructura_md_sub_plafonul_pe_care_il_declara():
    cale = ROOT / "specs" / "infrastructura.md"
    assert not incalcari_plafon_fapte(cale.read_text(encoding="utf-8"))


def test_fiecare_fapt_de_infrastructura_e_trasabil_la_registru():
    """Injectat la fiecare pornire => trebuie sa poata fi verificat, nu doar crezut."""
    cale = ROOT / "specs" / "infrastructura.md"
    incalcari = incalcari_trasabilitate(cale.read_text(encoding="utf-8"), ids_din_registru())
    assert not incalcari, "\n  ".join(incalcari)


def test_hookul_chiar_injecteaza_faptele_de_infrastructura():
    """Garda pe LEGATURA, nu pe fisier.

    Un fisier de fapte pe care hook-ul nu-l citeste e mai rau decat niciunul: pare ca informatia
    ajunge in context si nu ajunge. Exact asa a fost pierdut faptul 'Workers Paid' — statea intr-un
    COMENTARIU al hook-ului, adica nicaieri din punctul de vedere al unei sesiuni.

    Verifica IESIREA, nu textul hook-ului. Versiunea de dinainte cauta doar calea intr-o linie
    executabila, si ar fi trecut si daca hook-ul tiparea literalmente calea fara sa deschida
    fisierul (semnalat de CodeRabbit pe PR #254). Un test care nu poate distinge cele doua
    cazuri e chiar defectul pe care garda il pazeste, mutat cu un nivel mai sus.
    """
    fapte = linii_de_continut((ROOT / "specs" / "infrastructura.md").read_text(encoding="utf-8"))
    bullets = [linie[2:].strip() for linie in fapte if linie.startswith("- ")]
    assert bullets, "specs/infrastructura.md nu contine niciun fapt de verificat"
    iesire = iesirea_hookului().decode("utf-8", errors="replace")
    lipsa = [b[:60] for b in bullets if b not in iesire]
    assert not lipsa, ("faptele astea nu ajung in contextul sesiunii, desi sunt in fisier:\n  "
                       + "\n  ".join(lipsa))


def test_bugetul_de_pornire_sub_plafonul_declarat():
    """Plafonul pe suprafata, nu pe fisier: altfel o mutare in hook trece ca economie."""
    incalcari = incalcari_buget((ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
                                buget_de_pornire())
    assert not incalcari, incalcari[0]

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
    (MARCAJ_BUGET, "CLAUDE.md"),
    (MARCAJ_FAPTE, "specs/infrastructura.md"),
])
def test_fiecare_plafon_e_declarat_intr_un_singur_loc(marcaj, unde):
    """O regula, o cifra. Doua locuri inseamna ca niciuna nu se tine."""
    assert not incalcari_unicitate(fisiere_urmarite("*.md"), marcaj, unde)


# --- testele NEGATIVE: fiecare garda trebuie sa POATA esua -------------------------

def test_garda_faptelor_pica_pe_fisier_peste_plafon():
    assert incalcari_plafon_fapte("# t\n\n> **Plafon: 1 linii de fapt.**\n\n- a\n- b\n")


def test_garda_faptelor_pica_pe_fisier_fara_plafon_declarat():
    assert incalcari_plafon_fapte("# t\n\n- un fapt fara marcaj de plafon\n")


def test_garda_trasabilitatii_pica_pe_fapt_fara_citare():
    assert incalcari_trasabilitate("# t\n\n- fapt fara nicio dovada\n", {"0001"})


def test_garda_trasabilitatii_pica_pe_id_inexistent():
    assert incalcari_trasabilitate("# t\n\n- fapt cu dovada moarta [IZZ-9999]\n", {"0001"})


def test_garda_trasabilitatii_accepta_fapt_pe_mai_multe_linii():
    """Citarea sta la sfarsitul faptului; impartind pe linii, continuarile ar cadea toate."""
    text = "# t\n\n- inceputul unui fapt\n  care continua pe randul urmator [IZZ-0001]\n"
    assert not incalcari_trasabilitate(text, {"0001"})


def test_garda_kb_pica_pe_fisier_prea_mare():
    assert incalcari_plafon_kb("> **Plafon: 1 KB.**", 2048)


def test_garda_kb_pica_pe_fisier_fara_plafon_declarat():
    assert incalcari_plafon_kb("fara niciun marcaj", 10)



def test_garda_bugetului_pica_pe_suprafata_prea_mare():
    assert incalcari_buget("> **Buget de pornire: 1 KB.**", {"CLAUDE.md": 2048})


def test_garda_bugetului_pica_pe_fisier_fara_buget_declarat():
    assert incalcari_buget("fara niciun marcaj", {"CLAUDE.md": 10})


def test_garda_bugetului_numara_TOATE_straturile_nu_doar_fisierul():
    """Regresia pe care o previne: mutarea din CLAUDE.md in hook, raportata ca economie."""
    antet = "> **Buget de pornire: 1 KB.**"
    assert not incalcari_buget(antet, {"CLAUDE.md": 1000})
    assert incalcari_buget(antet, {"CLAUDE.md": 600, "hook SessionStart": 500})

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

# O trimitere poate cita si ANCORA din documentul tinta: `§13 ("Current scores")`. Sectiunea
# poate exista in timp ce titlul citat s-a mutat — atunci trimiterea pare valida si duce in gol.
# Masurat 2026-09-02: exact asa a supravietuit `frontend-auditor.md:23` gardii de sectiuni, care
# vedea ca §13 exista si se oprea acolo. E cea mai ingusta bucata de „proza libera" care are
# totusi sintaxa proprie, deci se poate pazi.
ANCORA_CITATA = re.compile(
    r"(§\s?\d+[a-z]?|`[^`]+\.md`)\s*\(\s*[„\"\u201c]([^\"\u201d\u201c]{2,60})[\"\u201d]\s*\)")

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


def incalcari_ancore(fisiere: dict[str, str], texte: dict[str, str],
                     proprietari: dict[str, str], implicit: str) -> list[str]:
    """Titlul citat intre paranteze dupa o trimitere trebuie sa existe in documentul tinta."""
    gasite = []
    for cale, text in sorted(fisiere.items()):
        for linie_nr, linie in enumerate(text.split("\n"), 1):
            for tinta, ancora in ANCORA_CITATA.findall(linie):
                document = (tinta.strip("`") if tinta.startswith("`")
                            else proprietari.get(cale, implicit))
                continut = texte.get(document)
                if continut is None or ancora in continut:
                    continue
                gasite.append(f"{cale}:{linie_nr} citeaza ancora «{ancora}», "
                              f"inexistenta in {document}")
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


def test_fiecare_ancora_citata_exista():
    """K8, a doua jumatate: §N poate exista in timp ce titlul citat din el s-a mutat."""
    fisiere = fisiere_normative()
    texte = {document: (ROOT / document).read_text(encoding="utf-8")
             for document in {DOCUMENT_IMPLICIT, *PROPRIETAR_SECTIUNI.values()}}
    texte.update({cale: text for cale, text in fisiere.items()})
    assert not incalcari_ancore(fisiere, texte, PROPRIETAR_SECTIUNI, DOCUMENT_IMPLICIT)

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



def test_garda_ancorelor_pica_pe_titlu_mutat():
    stricat = {"x.md": "prima linie\nvezi §13 („Current scores\u201d) pentru baseline"}
    assert incalcari_ancore(stricat, {"CLAUDE.md": "## 13. Verificare"}, {}, "CLAUDE.md")


def test_garda_ancorelor_accepta_titlul_care_chiar_exista():
    ok = {"x.md": "prima linie\nvezi §13 („Verificare front-end\u201d)"}
    assert not incalcari_ancore(ok, {"CLAUDE.md": "## 13. Verificare front-end — masoara"},
                                {}, "CLAUDE.md")

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
# act vizibil, nu o alunecare. Cele 49 de mai jos sunt capete bold din `CLAUDE.md`: 43 existau
# si pe `main`, 6 au intrat cu PR #282 (audit 2026-09-05); niciuna nu depinde de ordinea de aterizare.

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
    'Un task per declanșare.',
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
    'O decizie care NU produce un PR primește un rând în aceeași tură.',
    '`motiv` e obligatoriu',
    'Append-only.',
    'Un `find` gol NU e dovadă că nu s-a încercat.',
    'O limită se declară mecanic, nu prin impresie.',
    'Atribuire și legalitate.',
    'Titluri: 6–16 cuvinte este ținta editorială.',
    'Programator:',
    'Utilizator:',
    'Livrabilitate:',
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
    ".claude/reguli/18-imagini.md": frozenset({
        'Finanțarea din taxe NU pune fotografiile unei instituții în domeniul public.',
        'O poză făcută de un angajat al primăriei e opera INSTITUȚIEI:',
        'Nu improviza fapte juridice.',
        'Trei căi, oricare, verificată și CONSEMNATĂ (link + citat):',
        'Prezența unui ales reduce *dreptul lui la imagine*, nu *dreptul de autor al fotografului*.',
        'Fără scraping în bloc pe site-uri de instituții.',
        'Dovada se strânge într-un whitelist pe care proprietarul (sau juristul) îl aprobă ÎNAINTE',
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
