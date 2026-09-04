"""Un rand `propus` pe care mi-l propun MIE nu are voie sa imbatraneasca la nesfarsit.

DE CE EXISTA (2026-09-03, cerut de proprietar dupa ce a numit tiparul): registrul din
sect. 20 exista ca sa previna RE-LITIGAREA. Dar starea `propus` nu cere nimic — nici
`motiv`, nici termen — deci a devenit locul unde ajunge munca pe care n-am facut-o.
Un rand scris seamana cu livrare: e ieftin, e articulat, si nu poate pica in CI.

Masurat in ziua in care s-a scris garda: 19 randuri `propus`, din care **12 cu
`decident=claude`** — adica propuse de mine, mie, fara ca nimeni sa le blocheze. Sapte
aveau `decident=Ramanul` si asteptau legitim.

Distinctia care conteaza si pe care garda o citeste: **cine blocheaza rândul.**

  decident=Ramanul (sau alt om)  -> asteptare legitima, garda NU se atinge de el
  decident=claude                -> munca amanata catre mine; expira

PRAGUL E DERIVAT DIN INCIDENT, nu inventat: `generator/agents.py` a stat mort si
documentat ca mort din 2026-08-20 pana pe 2026-09-03 — **14 zile** — fiindca amanarea
unei sesiuni a fost citita de urmatoarea ca blocaj. Atat dureaza pana cand o amanare
devine invizibila, deci atat dureaza pana expira.

CUM SE STINGE un rand pe care garda il semnaleaza — trei cai, toate oneste:
  1. FA-L. Randul devine `implementat` (sau apare in `sync` ca PR).
  2. Trece-l pe om: `decident=Ramanul`, daca decizia chiar e a lui.
  3. Inchide-l: `respins` / `abandonat` cu `motiv` — CLI-ul refuza randul fara motiv.

Ce NU e o cale: sa-i schimbi data. Registrul e append-only (sect. 20).
"""
import csv
import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRU = ROOT / "specs" / "registru.tsv"

# 14 zile: cat a stat `agents.py` mort si necurat, din auditul care l-a gasit pana la
# stergere. Vezi antetul pentru de ce nu e o cifra rotunda aleasa la intamplare.
ZILE_PANA_EXPIRA = 14

# Cine nu e om: un rand pe care il "decide" un agent se blocheaza pe el insusi.
DECIDENTI_NEUMANI = {"claude", "codex", "devin", "jules", "opencode", "mistral", "gemini"}


def randuri(text: str) -> list[dict]:
    return list(csv.DictReader(text.splitlines(), delimiter="\t"))


def amanari_expirate(text: str, azi: datetime.date, zile: int = ZILE_PANA_EXPIRA) -> list[str]:
    """Randurile `propus` pe care si le-a asignat un agent si care au trecut de prag.

    Un rand INLOCUIT nu mai conteaza. Registrul e append-only (sect. 20): nu rescrii un
    rand, ii pui altul si le legi prin `leaga`. Fara regula asta garda ar suna pentru
    randuri deja rezolvate — si o garda care da alarme false se dezactiveaza, ceea ce ar
    fi exact esecul pe care il apara.
    """
    inlocuite = {(r.get("leaga") or "").strip()
                 for r in randuri(text) if (r.get("leaga") or "").strip()}
    expirate = []
    for r in randuri(text):
        if r.get("stare") != "propus":
            continue
        if r.get("id") in inlocuite:
            continue                                  # are un rand mai nou care il inchide
        if (r.get("decident") or "").strip().lower() not in DECIDENTI_NEUMANI:
            continue                                  # asteapta un om — legitim
        try:
            data = datetime.date.fromisoformat((r.get("data") or "").strip())
        except ValueError:
            continue                                  # data stricata e alta problema
        vechime = (azi - data).days
        if vechime > zile:
            expirate.append(
                f"{r['id']} ({vechime} zile, decident={r['decident']}): "
                f"{(r.get('titlu') or '')[:70]}")
    return expirate


# --- garda pe repo-ul real --------------------------------------------------------

def test_nicio_amanare_catre_mine_mai_veche_de_prag():
    text = REGISTRU.read_text(encoding="utf-8")
    azi = datetime.datetime.now(tz=datetime.timezone.utc).date()   # DTZ011: fus explicit
    expirate = amanari_expirate(text, azi)
    assert not expirate, (
        f"{len(expirate)} randuri `propus` asignate unui agent au trecut de "
        f"{ZILE_PANA_EXPIRA} zile. Fa-le, treci-le pe om (decident=Ramanul), sau inchide-le "
        f"cu motiv — dar nu le lasa sa imbatraneasca:\n  " + "\n  ".join(expirate))


# --- garda pe garda ---------------------------------------------------------------

_ANTET = "id\tdata\tzona\ttitlu\tstare\tdecident\tdovada\tmotiv\tleaga\n"


def _tsv(*linii: str) -> str:
    return _ANTET + "".join(linii)


def test_garda_prinde_amanarea_catre_agent():
    text = _tsv("IZZ-9001\t2026-08-01\tteste\tceva\tpropus\tclaude\t\t\t\n")
    assert amanari_expirate(text, datetime.date(2026, 9, 3))


def test_garda_ignora_asteptarea_pe_om():
    """Cazul care NU trebuie sa pice: proprietarul chiar are de decis ceva."""
    text = _tsv("IZZ-9002\t2026-07-01\tteste\tceva\tpropus\tRamanul\t\t\t\n")
    assert not amanari_expirate(text, datetime.date(2026, 9, 3))


def test_garda_ignora_randul_proaspat():
    """O propunere de azi nu e o amanare — devine una daca ramane asa."""
    text = _tsv("IZZ-9003\t2026-09-02\tteste\tceva\tpropus\tclaude\t\t\t\n")
    assert not amanari_expirate(text, datetime.date(2026, 9, 3))


def test_garda_ignora_starile_inchise():
    """`respins` si `implementat` sunt terminale — nu mai sunt datorii."""
    text = _tsv("IZZ-9004\t2026-07-01\tteste\tceva\trespins\tclaude\t\tmotiv scris\t\n",
                "IZZ-9005\t2026-07-01\tteste\tceva\timplementat\tclaude\t\t\t\n")
    assert not amanari_expirate(text, datetime.date(2026, 9, 3))


def test_garda_e_pe_ZI_nu_pe_luna():
    """Fix la prag inca trece; o zi peste, nu. Granita, testata in ambele directii —
    exact lectia din dimensiunea 4."""
    rand = "IZZ-9006\t2026-08-20\tteste\tceva\tpropus\tclaude\t\t\t\n"
    assert not amanari_expirate(_tsv(rand), datetime.date(2026, 9, 3))   # 14 zile fix
    assert amanari_expirate(_tsv(rand), datetime.date(2026, 9, 4))       # 15 zile


def test_garda_ignora_randul_inlocuit_printr_unul_mai_nou():
    """Sect. 20 e append-only: un rand se inchide punand altul care il leaga. Garda
    trebuie sa vada legatura, altfel ar suna pentru munca deja facuta."""
    text = _tsv("IZZ-9007\t2026-07-01\tteste\tvechi\tpropus\tclaude\t\t\t\n",
                "IZZ-9008\t2026-09-03\tteste\tnou\timplementat\tclaude\t\t\tIZZ-9007\n")
    assert not amanari_expirate(text, datetime.date(2026, 9, 3))


def test_garda_suna_daca_randul_nou_leaga_ALTCEVA():
    """Cazul-limita care ar face regula de mai sus o portita: un rand nou care leaga alt
    rand nu inchide amanarea noastra."""
    text = _tsv("IZZ-9009\t2026-07-01\tteste\tvechi\tpropus\tclaude\t\t\t\n",
                "IZZ-9010\t2026-09-03\tteste\tnou\timplementat\tclaude\t\t\tIZZ-9999\n")
    assert amanari_expirate(text, datetime.date(2026, 9, 3))
