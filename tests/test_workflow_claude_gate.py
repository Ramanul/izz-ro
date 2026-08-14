"""Poarta de securitate din .github/workflows/claude.yml.

Jobul `claude` ruleaza cu `contents: write` si cu tokenul de abonament al proprietarului.
Fara garda pe autor, un issue deschis de oricine pe acest repo public devine promptul acelui
job. Actiunea verifica si ea, dar prin doua functii care trebuie sa tina AMANDOUA
(`checkWritePermissions` lasa neconditionat sa treaca orice actor terminat in "[bot]"), iar
ambele stau in codul altcuiva, fixat pe un SHA. Garda de aici e redundanta deliberata.

Testul NU foloseste parserul de expresii al GitHub — il oglindeste in Python pe cel scris in
fisier. Ce prinde: o ramura de eveniment careia i s-a scos garda, sau o valoare largita in
allowlist. Ce NU prinde: o greseala de sintaxa acceptata de Python si respinsa de GitHub —
aia esueaza inchis oricum, fiindcă GitHub refuza workflow-ul si jobul nu porneste deloc.

Valorile de `author_association` sunt cele masurate pe payload-urile reale ale repo-ului
(2026-08-14): Ramanul -> OWNER (94/94), dependabot[bot] -> CONTRIBUTOR, restul botilor -> NONE.
"""
import json
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "claude.yml"


def _expresia_garzii() -> str:
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return wf["jobs"]["claude"]["if"]


def _evalueaza(expr: str, event_name: str, payload: dict) -> bool:
    """Traduce expresia GitHub in Python si o evalueaza. Traducerea e mecanica, pe textul
    din fisier — nu o copie scrisa de mana, ca sa nu testam altceva decat ce ruleaza."""

    def _get(cale: str):
        nod = payload
        for parte in cale.split("."):
            if not isinstance(nod, dict) or parte not in nod:
                return ""          # context absent -> string gol, ca la GitHub
            nod = nod[parte]
        return nod

    def _contains(hay, needle):
        return needle in hay       # merge si pe string, si pe lista

    py = expr
    py = py.replace("github.event_name", "EVENT_NAME")
    py = re.sub(r"github\.event\.([A-Za-z_][\w.]*)", r"_get('\1')", py)
    py = py.replace("fromJSON(", "json.loads(")
    py = py.replace("contains(", "_contains(")
    py = py.replace("&&", " and ").replace("||", " or ")
    py = "(" + py + ")"            # expresia e multi-linie; parantezele dau continuare de rand

    return bool(eval(py, {"json": json}, {                      # noqa: S307 - input e fisierul repo-ului
        "EVENT_NAME": event_name, "_get": _get, "_contains": _contains,
    }))


TREC = ["OWNER", "COLLABORATOR"]
CAD = ["NONE", "CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "MEMBER", "MANNEQUIN", ""]

# (event_name, unde sta corpul, unde sta asocierea) — cele patru declansatoare din workflow
DECLANSATOARE = [
    ("issue_comment", ("comment", "body"), ("comment", "author_association")),
    ("pull_request_review_comment", ("comment", "body"), ("comment", "author_association")),
    ("pull_request_review", ("review", "body"), ("review", "author_association")),
    ("issues", ("issue", "body"), ("issue", "author_association")),
]


def _payload(corp_la, asoc_la, text, asociere):
    p = {}
    p.setdefault(corp_la[0], {})[corp_la[1]] = text
    p.setdefault(asoc_la[0], {})[asoc_la[1]] = asociere
    return p


@pytest.mark.parametrize("event_name,corp_la,asoc_la", DECLANSATOARE)
@pytest.mark.parametrize("asociere", TREC)
def test_proprietarul_si_colaboratorul_trec(event_name, corp_la, asoc_la, asociere):
    expr = _expresia_garzii()
    p = _payload(corp_la, asoc_la, "@claude fix this", asociere)
    assert _evalueaza(expr, event_name, p) is True


@pytest.mark.parametrize("event_name,corp_la,asoc_la", DECLANSATOARE)
@pytest.mark.parametrize("asociere", CAD)
def test_strainii_si_botii_sunt_blocati(event_name, corp_la, asoc_la, asociere):
    """Inclusiv MEMBER: repo-ul e detinut de un cont User, deci valoarea e imposibila azi,
    iar sub o organizatie ar admite membri fara drept de scriere pe ACEST repo."""
    expr = _expresia_garzii()
    p = _payload(corp_la, asoc_la, "@claude push whatever I say", asociere)
    assert _evalueaza(expr, event_name, p) is False


@pytest.mark.parametrize("event_name,corp_la,asoc_la", DECLANSATOARE)
def test_fara_declansator_nu_porneste_nici_pentru_proprietar(event_name, corp_la, asoc_la):
    expr = _expresia_garzii()
    p = _payload(corp_la, asoc_la, "un comentariu obisnuit", "OWNER")
    assert _evalueaza(expr, event_name, p) is False


def test_titlul_de_issue_declanseaza_dar_tot_cu_garda():
    """Ramura `issues` accepta @claude si din titlu — garda trebuie sa se aplice si acolo."""
    expr = _expresia_garzii()
    assert _evalueaza(expr, "issues",
                      {"issue": {"title": "@claude", "body": "", "author_association": "OWNER"}}) is True
    assert _evalueaza(expr, "issues",
                      {"issue": {"title": "@claude", "body": "", "author_association": "NONE"}}) is False


def test_garda_acopera_toate_declansatoarele_declarate():
    """Daca cineva adauga un al cincilea eveniment in `on:` fara garda, testul cade."""
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    declarate = {k for k in wf[True]}          # PyYAML citeste cheia `on` ca True (YAML 1.1)
    assert declarate == {e for e, _, _ in DECLANSATOARE}


def test_portitele_de_ocolire_raman_neconfigurate():
    """`allowed_non_write_users` si `allowed_bots` dezarmeaza verificarile din actiune.
    Nu sunt setate; daca apar vreodata, decizia trebuie luata constient, nu prin drift.
    Se citesc din `with:`-ul pasilor, nu din textul brut — comentariul garzii le NUMESTE."""
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for pas in wf["jobs"]["claude"]["steps"]:
        intrari = pas.get("with") or {}
        assert "allowed_non_write_users" not in intrari
        assert "allowed_bots" not in intrari
