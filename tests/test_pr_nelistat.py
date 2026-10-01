"""Garda inversa a PR-urilor fantoma: deschis de peste 24h => obligatoriu in STATE.md.

Incidentul care a cerut-o: PR #253, verde de 30 de ore, absent din `## Open`. Vezi
`tools/pr_nelistat.py` pentru mecanism si pentru de ce pragul e 24 si nu altceva.
"""
from datetime import datetime, timedelta, timezone

import tools.pr_nelistat as mod
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


def test_repo_ostil_e_respins_inainte_de_orice_cerere():
    """Semgrep finding 96 pe #260: `urllib` onoreaza `file://`, iar `repo` vine din mediu.

    Schema era deja scrisa in cod, deci exploatarea prin schema nu era posibila — dar
    constrangerea era adevarata din intamplare, nu exprimata. Testul o exprima: orice forma
    care nu e `owner/nume` pica INAINTE de orice acces la retea.
    """
    import pytest as _p

    from tools.pr_nelistat import _pr_deschise_din_api
    for ostil in ("../../etc/passwd", "a/b/../..", "evil.com/x:1", "owner", "a b/c",
                  "file:///etc/passwd", "owner/repo?x=1"):
        with _p.raises(ValueError, match="owner/nume"):
            _pr_deschise_din_api(ostil, "token-fals")


def test_repo_valid_trece_de_validare():
    """Granita cealalta: numele reale nu sunt respinse."""
    from tools.pr_nelistat import REPO_VALID
    for bun in ("Ramanul/izz-ro", "a/b", "org.x/repo-1_2", "OWNER/REPO.md"):
        assert REPO_VALID.match(bun), bun


# --- plafonul cozii si termenul de stagnare -------------------------------------------
#
# Cerere de proprietar 2026-09-15: „fa o regula sa nu mai ramana PR-uri si issues".
# Masurat in ziua cererii: 9 PR-uri deschise, 3 issue-uri; 7 din 9 PR-uri erau munca de META,
# iar singurul de SITE (#297) statea de 9 zile cu 175 de commituri de drift adunate peste el.
# Mecanismul acumularii nu e uitarea — aia e pazita mai sus — ci absenta unei forte de iesire.

def _pr_coada(numar, *, zile_de_la_atingere=0, bot=False, titlu="x"):
    cand = (ACUM - timedelta(days=zile_de_la_atingere)).isoformat().replace("+00:00", "Z")
    return {"number": numar, "title": titlu, "created_at": cand, "updated_at": cand,
            "user": {"type": "Bot" if bot else "User"}}


def test_plafonul_cozii_suna_cand_e_depasit():
    peste = [_pr_coada(i) for i in range(1, mod.PLAFON_COADA + 2)]
    incalcari = mod.incalcari_coada(peste, ACUM)
    assert any("peste plafonul" in i for i in incalcari)


def test_NEGATIV_exact_pe_plafon_nu_suna():
    """Granita se verifica in ambele directii, altfel garda ar fi cu o unitate gresita."""
    fix = [_pr_coada(i) for i in range(1, mod.PLAFON_COADA + 1)]
    assert not [i for i in mod.incalcari_coada(fix, ACUM) if "plafonul" in i]


def test_botii_nu_umplu_coada():
    """Un val de Dependabot ar declansa alarma zilnic si garda ar fi dezactivata."""
    boti = [_pr_coada(i, bot=True) for i in range(1, mod.PLAFON_COADA + 5)]
    assert mod.incalcari_coada(boti, ACUM) == []


def test_pr_stagnant_e_numit_cu_varsta_lui():
    vechi = _pr_coada(42, zile_de_la_atingere=mod.PRAG_STAGNARE_ZILE + 3, titlu="uitat")
    incalcari = mod.incalcari_coada([vechi], ACUM)
    assert len(incalcari) == 1 and "#42" in incalcari[0] and "stagneaza" in incalcari[0]


def test_NEGATIV_un_pr_atins_ieri_nu_e_stagnant():
    assert mod.incalcari_coada([_pr_coada(42, zile_de_la_atingere=1)], ACUM) == []


def test_stagnarea_se_masoara_pe_ULTIMA_atingere_nu_pe_deschidere():
    """Un PR vechi dar lucrat ieri e viu. Altfel garda ar pedepsi munca in curs."""
    viu = _pr_coada(42, zile_de_la_atingere=0)
    viu["created_at"] = (ACUM - timedelta(days=90)).isoformat().replace("+00:00", "Z")
    assert mod.incalcari_coada([viu], ACUM) == []


def test_issue_nenumit_in_state_e_prins():
    state = "## Open\n\n- nimic despre issue-uri\n\n## Altceva\n"
    incalcari = mod.incalcari_issue_fara_motiv([{"number": 198, "title": "arhiva",
                                                 "user": {"type": "User"}}], state)
    assert len(incalcari) == 1 and "#198" in incalcari[0]


def test_issue_numit_in_state_e_acceptat_fara_termen():
    """Deliberat FARA termen: un issue poate fi o decizie care asteapta luni (#198, IZZ-0383)."""
    state = "## Open\n\n- **#198 arhiva rămâne decizie de proprietar.**\n\n## Altceva\n"
    assert mod.incalcari_issue_fara_motiv([{"number": 198, "title": "arhiva",
                                            "user": {"type": "User"}}], state) == []


def test_state_fara_open_e_el_insusi_o_incalcare_si_la_issue_uri():
    assert mod.incalcari_issue_fara_motiv([], "fara sectiune") == ["specs/STATE.md nu are sectiunea ## Open"]
