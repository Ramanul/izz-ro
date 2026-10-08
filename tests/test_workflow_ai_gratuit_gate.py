"""Poarta din .github/workflows/ai-gratuit.yml.

Jobul primește OPENROUTER_API_KEY și poate comenta ca github-actions[bot] pe un repo
public. Aliasurile (@qwen, @kimi, …) sunt preferințe de model, nu niveluri de încredere.

&& leagă mai strâns decât ||. Un lanț scris ca
`eveniment && contains('@ai') || contains('@qwen') && autor`
pornește jobul pentru oricine scrie @qwen. Testul evaluează expresia din fișier,
nu o copie de mână, ca să prindă exact regresia asta.
"""
import json
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ai-gratuit.yml"
ALIASURI = (
    "ai", "deepseek", "qwen", "kimi", "glm", "grok", "nemotron", "gemma", "inkling",
)
TREC = ["OWNER", "COLLABORATOR"]
CAD = ["NONE", "CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "MEMBER", "MANNEQUIN", ""]
DECLANSATOARE = [
    ("issue_comment", ("comment", "body"), ("comment", "author_association")),
    ("pull_request_review_comment", ("comment", "body"), ("comment", "author_association")),
    ("issues", ("issue", "body"), ("issue", "author_association")),
]


def _expresia_garzii() -> str:
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return wf["jobs"]["ai"]["if"]


def _evalueaza(expr: str, event_name: str, payload: dict) -> bool:
    def _get(cale: str):
        nod = payload
        for parte in cale.split("."):
            if not isinstance(nod, dict) or parte not in nod:
                return ""
            nod = nod[parte]
        return nod

    def _contains(hay, needle):
        return needle in hay

    py = expr
    py = py.replace("github.event_name", "EVENT_NAME")
    py = re.sub(r"github\.event\.([A-Za-z_][\w.]*)", r"_get('\1')", py)
    py = py.replace("fromJSON(", "json.loads(")
    py = py.replace("contains(", "_contains(")
    py = py.replace("&&", " and ").replace("||", " or ")
    py = "(" + py + ")"
    return bool(eval(py, {"json": json}, {  # noqa: S307 - expresia e fișierul repo-ului
        "EVENT_NAME": event_name, "_get": _get, "_contains": _contains,
    }))


def _payload(corp_la, asoc_la, text, asociere):
    p = {}
    p.setdefault(corp_la[0], {})[corp_la[1]] = text
    p.setdefault(asoc_la[0], {})[asoc_la[1]] = asociere
    return p


@pytest.mark.parametrize("event_name,corp_la,asoc_la", DECLANSATOARE)
@pytest.mark.parametrize("alias", ALIASURI)
@pytest.mark.parametrize("asociere", TREC)
def test_fiecare_alias_trece_doar_pentru_autor_autorizat(event_name, corp_la, asoc_la, alias, asociere):
    expr = _expresia_garzii()
    p = _payload(corp_la, asoc_la, f"@{alias} explică pe scurt", asociere)
    assert _evalueaza(expr, event_name, p) is True


@pytest.mark.parametrize("event_name,corp_la,asoc_la", DECLANSATOARE)
@pytest.mark.parametrize("alias", ALIASURI)
@pytest.mark.parametrize("asociere", CAD)
def test_niciun_alias_nu_trece_fara_autor(event_name, corp_la, asoc_la, alias, asociere):
    expr = _expresia_garzii()
    p = _payload(corp_la, asoc_la, f"te rog @{alias} ceva", asociere)
    assert _evalueaza(expr, event_name, p) is False


@pytest.mark.parametrize("event_name,corp_la,asoc_la", DECLANSATOARE)
def test_fara_alias_nu_porneste_nici_pentru_proprietar(event_name, corp_la, asoc_la):
    expr = _expresia_garzii()
    p = _payload(corp_la, asoc_la, "un comentariu obișnuit, fără apel", "OWNER")
    assert _evalueaza(expr, event_name, p) is False


def test_aliasul_de_pe_alt_eveniment_nu_se_scurge():
    """@qwen într-un comentariu nu aprinde ramura `issues`, și invers."""
    expr = _expresia_garzii()
    assert _evalueaza(
        expr, "issues",
        {"comment": {"body": "@qwen", "author_association": "OWNER"},
         "issue": {"body": "", "author_association": "OWNER"}},
    ) is False
    assert _evalueaza(
        expr, "issue_comment",
        {"issue": {"body": "@kimi", "author_association": "OWNER"}},
    ) is False


def test_garda_acopera_evenimentele_declarate():
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    declarate = {k for k in wf[True]}
    assert declarate == {e for e, _, _ in DECLANSATOARE}


def test_stratul_din_shell_refuza_autorul_neautorizat_inainte_de_cheie():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "AUTHOR_ASSOCIATION" in text
    assert "OWNER|COLLABORATOR" in text
    # Cheia nu e în pasul de poartă.
    poarta = text.split("- name: Declanșator valid?", 1)[1].split("- name:", 1)[0]
    assert "OPENROUTER_API_KEY" not in poarta
