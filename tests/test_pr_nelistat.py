"""Garda inversa a PR-urilor fantoma: deschis de peste 24h => obligatoriu in STATE.md.

Incidentul care a cerut-o: PR #253, verde de 30 de ore, absent din `## Open`. Vezi
`tools/pr_nelistat.py` pentru mecanism si pentru de ce pragul e 24 si nu altceva.
"""
from datetime import datetime, timedelta, timezone

from tools.pr_nelistat import incalcari, sectiune_open

ACUM = datetime(2026, 9, 4, 5, 0, tzinfo=timezone.utc)
STATE_CU_247 = "# STATE\n\n## Open\n\n- **PR-uri deschise:** #247 (prospetime 72h).\n\n## Altceva\n"


def _pr(numar, ore, titlu="ceva"):
    return {"number": numar, "title": titlu,
            "created_at": (ACUM - timedelta(hours=ore)).isoformat().replace("+00:00", "Z")}


def test_pr_vechi_nelistat_e_prins():
    """Cazul real: #253, deschis de 30h, absent din STATE.md."""
    p = incalcari([_pr(253, 30, "fix: fa lucrurile amanate")], STATE_CU_247, ACUM)
    assert len(p) == 1 and "#253" in p[0] and "30h" in p[0], p


def test_pr_listat_nu_e_prins():
    assert incalcari([_pr(247, 200)], STATE_CU_247, ACUM) == []


def test_pr_proaspat_nu_e_prins():
    """Un PR de acum doua ore nu e o omisiune — STATE.md nu avea cum sa il stie."""
    assert incalcari([_pr(999, 2)], STATE_CU_247, ACUM) == []


def test_granita_pragului_in_ambele_directii():
    """Exact 24h = prins (a supravietuit o zi); 23h59 = nu."""
    assert incalcari([_pr(500, 24)], STATE_CU_247, ACUM) != []
    assert incalcari([_pr(500, 23)], STATE_CU_247, ACUM) == []


def test_pr_ul_curent_e_exclus():
    """Un PR nu se poate autodeclara in STATE.md inainte sa existe."""
    assert incalcari([_pr(260, 48)], STATE_CU_247, ACUM, exclude={260}) == []


def test_state_fara_sectiunea_open_e_el_insusi_o_incalcare():
    p = incalcari([], "# STATE\n\nnimic\n", ACUM)
    assert len(p) == 1 and "## Open" in p[0]


def test_sectiunea_open_se_opreste_la_urmatorul_titlu():
    """Altfel un `#253` dintr-o sectiune de istoric ar masca o omisiune reala."""
    md = "## Open\n\n- #247\n\n## Istoric\n\n- #253 a fost candva aici\n"
    assert "#247" in sectiune_open(md) and "#253" not in sectiune_open(md)


def test_pr_de_bot_e_sarit():
    """Dependabot nu intra in STATE.md: 4 din cele 11 PR-uri deschise la prima rulare a
    garzii erau bump-uri, iar STATE.md are plafon de 40 de linii citite la fiecare pornire.
    O garda care suna zilnic pentru bump-uri ajunge dezactivata."""
    bot = _pr(258, 48, "ci: bump actions/checkout") | {"user": {"type": "Bot"}}
    assert incalcari([bot], STATE_CU_247, ACUM) == []


def test_pr_de_om_nu_e_sarit_de_filtrul_de_bot():
    """Granita: filtrul se uita la `type`, si un PR fara camp `user` ramane verificat."""
    om = _pr(261, 48, "fix real") | {"user": {"type": "User"}}
    assert incalcari([om], STATE_CU_247, ACUM) != []
    assert incalcari([_pr(262, 48)], STATE_CU_247, ACUM) != []
