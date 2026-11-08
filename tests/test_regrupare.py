"""Regruparea post-AI a articolelor deja publicate (generator/cluster.py, 8.11.2026).

Cazurile vin din proba pe 3 zile de stare reala: ce trebuia sa se lipeasca (BCE x4) si ce
s-a lipit gresit la prima versiune (Tezaur/FIDELIS, Reghecampf/Becali)."""
from datetime import datetime, timedelta, timezone

from generator import cluster


def _a(url, title, ents, dom, model="B", ore=1, **kw):
    pub = (datetime.now(timezone.utc) - timedelta(hours=ore)).isoformat()
    d = {"url": url, "title": title, "entities": ents, "model": model, "published": pub,
         "original_link": f"https://{dom}/x"}
    d.update(kw)
    return d


BCE = ["Spania", "Olanda", "Banca Centrala Europeana"]


def _bce():
    return [
        _a("/1", "Spania și Olanda candidează pentru șefia Băncii Centrale Europene", BCE, "politico.eu"),
        _a("/2", "Spania și Țările de Jos candidează pentru șefia Băncii Centrale Europene", BCE, "g4media.ro"),
        _a("/3", "Spania și Olanda au nominalizat candidați pentru șefia Băncii Centrale Europene", BCE, "hotnews.ro"),
        _a("/4", "Spania și Olanda candidează pentru șefia Băncii Centrale Europene", BCE, "stirileprotv.ro"),
    ]


def test_acelasi_eveniment_in_patru_publicatii_se_regrupeaza():
    g = cluster.regrupeaza_publicate(_bce())
    assert len(g) == 1 and len(g[0]) == 4


def test_doar_numele_produsului_difera_nu_se_lipeste():
    mf = ["Ministerul Finantelor"]
    arts = [_a("/t", "Ministerul Finanțelor lansează o nouă ediție a titlurilor de stat Tezaur", mf, "hotnews.ro"),
            _a("/f", "Ministerul Finanțelor lansează o nouă ediție a titlurilor de stat FIDELIS", mf, "gorjeanul.ro")]
    assert cluster.regrupeaza_publicate(arts) == []


def test_alt_vorbitor_in_zona_gri_nu_se_lipeste():
    a = _a("/r", "Laurențiu Reghecampf și-a criticat dur jucătorii după eșecul cu Corvinul",
           ["Laurentiu Reghecampf", "Corvinul Hunedoara", "FCSB"], "gsp.ro")
    b = _a("/b", "Gigi Becali îl critică pe antrenorul Laurențiu Reghecampf după eșecul cu Corvinul Hunedoara",
           ["Gigi Becali", "Laurentiu Reghecampf", "Corvinul Hunedoara"], "sport.ro")
    assert not cluster._potrivire_regrupare(a, b)


def test_fara_entitati_comune_sau_aceeasi_publicatie_sau_vechi_nu_se_lipeste():
    x = _bce()[:2]
    x[1]["entities"] = ["Altceva"]
    assert cluster.regrupeaza_publicate(x) == []
    y = _bce()[:2]
    y[1]["original_link"] = "https://politico.eu/alt"
    assert cluster.regrupeaza_publicate(y) == []
    z = _bce()[:2]
    z[1]["published"] = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    assert cluster.regrupeaza_publicate(z) == []


def test_cifre_disjuncte_veto():
    e = ["DIICOT"]
    arts = [_a("/1", "DIICOT face 15 percheziții într-un dosar de evaziune fiscală", e, "a.ro"),
            _a("/2", "DIICOT face 55 percheziții într-un dosar de evaziune fiscală", e, "b.ro")]
    assert cluster.regrupeaza_publicate(arts) == []


def test_sinteza_c_e_lider_si_cel_mult_una_pe_grup():
    arts = _bce()
    arts[2]["model"] = "C"
    arts[3]["model"] = "C"
    g = cluster.regrupeaza_publicate(arts)
    assert g and all(sum(m["model"] == "C" for m in grp) <= 1 for grp in g)
    assert all(grp[0]["model"] == "C" for grp in g if any(m["model"] == "C" for m in grp))


def test_grup_esuat_nu_se_reia_pana_nu_se_schimba_componenta():
    arts = _bce()
    g = cluster.regrupeaza_publicate(arts)[0]
    cluster.marcheaza_esec_regrupare(g)
    assert cluster.regrupeaza_publicate(arts) == []
    arts.append(_a("/5", "Spania și Olanda candidează pentru șefia Băncii Centrale Europene", BCE, "digi24.ro"))
    assert len(cluster.regrupeaza_publicate(arts)) == 1


def test_anunt_fara_corp_si_single_nu_intra():
    arts = _bce()[:2]
    arts[1]["anunt_fara_corp"] = True
    assert cluster.regrupeaza_publicate(arts) == []
