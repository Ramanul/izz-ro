"""Garda de diacritice: prinde reformularile AI care pierd diacriticele sursei.

DE CE EXISTA TESTELE, SI CE PRIND. Trei lucruri se pot strica independent, si niciunul nu se
vede in productie ca o eroare — doar ca text scris de mana:

  · un predicat prea larg care semnaleaza titluri corecte („Cancelarul german a vizitat
    Kievul" n-are nevoie de nicio diacritica) — ar consuma un apel AI si ar raporta fals;
  · un predicat prea ingust, care nu prinde exact cazul masurat pe 2026-10-04 („brand
    romanesc de cosmetice pe baza de apa termala", sursa cu diacritice) — garda de decor;
  · o „reparatie" care inlocuieste textul publicat cu ceva ce nu mai e acelasi text: modelul
    e liber sa raspunda orice, iar conditiile de acceptare sunt singurul gard intre raspunsul
    lui si site.

Corpusul de mai jos e luat din datele reale ale pipeline-ului (masurat pe `data/articles.json`,
24h, 2026-10-04), nu inventat: perechile sursa -> text generat sunt chiar cele publicate.
"""
from generator import diacritice
from generator.process import repara_diacritice

# --- 1. predicatul: cand semnaleaza si cand NU ---------------------------------------------

# Cazul real (Profit.ro): sursa are diacritice, textul publicat le-a pierdut pe toate.
SURSA = ("Afacerile unui brand românesc de cosmetice pe bază de apă termală au crescut "
         "semnificativ. O afacere locală pornită de la valorificarea apei termale din "
         "stațiunea Băile Felix a ajuns la o cifră de afaceri record.")
GENERAT_STRICAT = ("Afacerile unui brand romanesc de cosmetice pe baza de apa termala au "
                   "crescut semnificativ")
GENERAT_BUN = ("Afacerile unui brand românesc de cosmetice pe bază de apă termală au crescut "
               "semnificativ")


def test_predicatul_prinde_cazul_real_din_productie():
    assert diacritice.lipsesc_diacriticele(SURSA, GENERAT_STRICAT)


def test_predicatul_tace_cand_textul_are_diacritice():
    assert not diacritice.lipsesc_diacriticele(SURSA, GENERAT_BUN)


def test_titlurile_care_nu_au_nevoie_de_diacritice_nu_se_semnalaza():
    """Capcana de baza: jumatate din stirile romanesti n-au ce diacritici sa poarte."""
    sursa = ("Cancelarul german Friedrich Merz a vizitat Kievul, unde a discutat despre "
             "ajutoare. Delegatia a fost primita de oficiali ucraineni.")
    generat = "Cancelarul german Friedrich Merz a vizitat Kievul cu ajutoare"
    assert not diacritice.lipsesc_diacriticele(sursa, generat)


def test_o_singura_coincidenta_nu_e_destul():
    """In romana, formele cu si fara diacritica pot fi amandoua corecte („casă"/„casa",
    „cursă"/„cursa"): o singura potrivire poate fi intamplare, doua nu mai sunt zgomot."""
    sursa = "Era o zi obișnuită, dar primarul a venit la ședință."
    assert not diacritice.lipsesc_diacriticele(sursa, "Era o zi obisnuita, dar primarul a venit")
    assert diacritice.lipsesc_diacriticele(
        sursa, "Era o zi obisnuita, dar primarul a venit la sedinta primariei")


def test_cazul_loteriei_are_doua_potriviri_desi_singurul_cuvant_lung_e_unul():
    """Caz real (Digi24, 4 oct): „Loteria Romana pune in joc reporturi..." — cuvintele lungi
    cu diacritice lipsa sunt putine, dar „in" (sursa: „în") e al doilea semnal, iar pragul
    de doua cuvinte e chiar ce face diferenta intre o garda utila si una care tace."""
    sursa = ("Loteria Română pune în joc reporturi de milioane de euro la tragerea din "
             "4 octombrie. Duminică au loc noi extrageri la Loto 6/49.")
    generat = "Loteria Romana pune in joc reporturi de milioane de euro la tragerea din 4 octombrie"
    assert diacritice.lipsesc_diacriticele(sursa, generat)


def test_sursa_fara_diacritice_nu_produce_semnal():
    """Fara forme diacritice in sursa nu exista pierdere — nu e o problema de diacritice."""
    sursa = "Un accident a avut loc pe DN1, iar politistii au deschis o ancheta."
    assert not diacritice.lipsesc_diacriticele(sursa, "Un accident a avut loc pe DN1")


def test_text_generat_alege_corpul_dupa_model():
    assert diacritice.text_generat({"model": "B", "title": "T", "teaser": "te"}) == "T te"
    assert diacritice.text_generat({"model": "C", "title": "T", "synthesis": "si"}) == "T si"


def test_text_sursa_si_text_grup():
    item = {"title": "Titlu AI", "teaser": "rezumat AI",
            "original_title": "Titlul sursei, cu diacritice", "description": "Descrierea sursei."}
    assert diacritice.text_sursa(item) == "Titlul sursei, cu diacritice Descrierea sursei."
    # rep C fara text brut (articol deja procesat): cade pe textul publicat, nu pe gol
    fara_brut = {"model": "C", "title": "Titlu", "synthesis": "sinteza"}
    assert diacritice.text_sursa(fara_brut) == ""
    assert diacritice.text_grup([item, fara_brut]).startswith("Titlul sursei")


def test_contoarele_numara_si_raportul_tace_cand_nu_e_nimic():
    diacritice.goleste()
    assert diacritice.raport() == ""
    diacritice.noteaza_verificate(10)
    diacritice.noteaza_semnalate(2)
    diacritice.noteaza_reparate(1)
    linie = diacritice.raport()
    assert "2/10" in linie and "1 reparate" in linie
    diacritice.goleste()
    assert diacritice.statistici()["semnalate"] == 0


# --- 2. reparatia: un apel AI, cu trei conditii de acceptare -------------------------------

class _Provider:
    """Provider fals: raspunde cu ce i se da, si numara apelurile."""

    name = "fake"
    calls = 0

    def __init__(self, raspuns):
        self.raspuns = raspuns

    def complete(self, system, user):
        self.calls += 1
        return self.raspuns(self, user)


def _articol(model="B", title="Titlu romanesc fara diacritice", teaser="Rezumat fara diacritice"):
    a = {"model": model, "title": title, "teaser": teaser,
         "synthesis": teaser if model == "C" else None,
         "url": "https://exemplu.ro/x", "original_title": "Titlu românesc cu diacritice",
         "description": "Descriere cu diacritice, șiruri și alte cuvinte."}
    return a


def test_reparatia_inlocuieste_textul_cand_raspunsul_e_curat():
    a = _articol()
    p = _Provider(lambda self, u: '[{"id": 0, "title": "Titlu românesc fără diacritice", '
                                  '"teaser": "Rezumat fără diacritice"}]')
    n = repara_diacritice([(a, diacritice.text_sursa(a))], p)
    assert n == 1
    assert a["title"] == "Titlu românesc fără diacritice"
    assert a["teaser"] == "Rezumat fără diacritice"
    assert p.calls == 1


def test_reparatia_nu_accepta_un_raspuns_tot_fara_diacritice():
    a = _articol()
    p = _Provider(lambda self, u: '[{"id": 0, "title": "Titlu romanesc", "teaser": "Rezumat"}]')
    assert repara_diacritice([(a, diacritice.text_sursa(a))], p) == 0
    assert a["title"] == "Titlu romanesc fara diacritice"       # textul vechi, neatins


def test_reparatia_respinge_o_rescriere_care_schimba_lungimea():
    """Un raspuns care dubleaza titlul nu mai e corectura de diacritice, e alt articol."""
    a = _articol()
    p = _Provider(lambda self, u: '[{"id": 0, "title": "Titlu românesc fără diacritice, '
                                  'complet rescris și lungit mult peste limita acceptată", '
                                  '"teaser": "Rezumat fără diacritice"}]')
    assert repara_diacritice([(a, diacritice.text_sursa(a))], p) == 0
    assert a["title"] == "Titlu romanesc fara diacritice"


def test_reparatia_nu_fabric_o_identitate_falsa():
    """Aceeasi garda ca la sinteza C: daca sursa spune „s-au dat drept politisti", titlul
    „au simtit politisti" nu are voie sa treaca, oricat de curate ar fi diacriticele."""
    a = _articol(title="Suspectii au simtit politisti la poarta")
    sursa = "Doi bărbați s-au dat drept polițiști și au pătruns în curtea imobilului."
    p = _Provider(lambda self, u: '[{"id": 0, "title": "Suspecții au simțit polițiști la '
                                  'poartă", "teaser": "Rezumat fără diacritice"}]')
    assert repara_diacritice([(a, sursa)], p) == 0
    assert a["title"] == "Suspectii au simtit politisti la poarta"


def test_un_esec_de_provider_nu_strica_textul():
    a = _articol()

    def _boom(self, u):
        raise RuntimeError("429")

    p = _Provider(_boom)
    assert repara_diacritice([(a, diacritice.text_sursa(a))], p) == 0
    assert a["title"] == "Titlu romanesc fara diacritice"


def test_fara_provider_sau_fara_perechi_nu_se_cheama_nimic():
    a = _articol()
    assert repara_diacritice([], None) == 0
    assert repara_diacritice([(a, "x")], None) == 0


def test_marcajul_de_actualizare_se_pune_dupa_reparatie():
    """Textul publicat s-a schimbat dupa procesare: `updated` e singurul semnal onest."""
    a = _articol()
    p = _Provider(lambda self, u: '[{"id": 0, "title": "Titlu românesc fără diacritice", '
                                  '"teaser": "Rezumat fără diacritice"}]')
    assert not a.get("updated")
    repara_diacritice([(a, diacritice.text_sursa(a))], p)
    assert a.get("updated")


# --- 3. integrare: garda chiar ruleaza in pipeline, si consuma din buget -------------------

class _ProviderPipeline:
    """B: pierde diacriticele. D: (reparatia) le pune la loc. Numara apelurile per prompt."""

    name = "fake"

    def __init__(self):
        self.calls = []

    def complete(self, system, user):
        self.calls.append(system.split(".")[0])
        if system.startswith("Esti corector"):
            import re
            ids = re.findall(r"^\[(\d+)\] Titlu: (.*?) \| Rezumat:", user, re.M)
            import json
            return json.dumps([{"id": int(i), "title": t.replace("romanesc", "românesc")
                                                    .replace("fara", "fără"),
                                "teaser": "Rezumat fără diacritice"}
                               for i, t in ids])
        import json
        return json.dumps([{"id": i, "title": f"Titlu {i} romanesc fara diacritice",
                            "teaser": "Rezumat fara diacritice si cuvinte",
                            "category": "extern", "entities": [], "icon": None}
                           for i in range(len(user.split("[")) - 1)])


def _item_diacritice():
    return {"url": "https://sursa.ro/stire-diacritice", "original_link": "",
            "source": "sursa", "source_name": "Sursa",
            "title": "", "original_title": "Titlu românesc, cu diacritice și șiruri",
            "description": "Descriere cu diacritice, fără explicații.",
            "category": "extern", "model": None,
            "published": "2026-10-04T05:00:00+00:00"}


def test_pipeline_repara_diacriticele_si_plateste_un_apel_in_plus(monkeypatch):
    from generator import main
    p = _ProviderPipeline()
    out, _, used = main.process_new([_item_diacritice()], p, budget=5)
    assert used == 2                                   # lotul B + corectura
    a = [x for x in out if x.get("model") == "B"][0]
    assert "românesc" in a["title"], a
    assert diacritice.statistici()["reparate"] == 1


def test_pipeline_nu_plateste_corectura_cand_nu_e_nevoie():
    from generator import main
    diacritice.goleste()

    class _Curat(_ProviderPipeline):
        def complete(self, system, user):
            import json
            self.calls.append(system)
            return json.dumps([{"id": i, "title": "Titlu românesc fără diacritice",
                                "teaser": "Rezumat fără diacritice",
                                "category": "extern", "entities": [], "icon": None}
                               for i in range(len(user.split("[")) - 1)])

    p = _Curat()
    out, _, used = main.process_new([_item_diacritice()], p, budget=5)
    assert used == 1                                   # un singur apel: nimic de corectat
    assert diacritice.statistici()["semnalate"] == 0
    assert out and out[0]["title"] == "Titlu românesc fără diacritice"


def test_pipeline_nu_arunca_articolul_cand_corectura_esueaza():
    """Decizie asumata: un provider degradat NU are voie sa goleasca site-ul. Textul ramane,
    dar cifra nereparatelor se vede in log (`raport()`)."""
    from generator import main
    diacritice.goleste()

    class _NuRepara(_ProviderPipeline):
        def complete(self, system, user):
            import json
            self.calls.append(system)
            if system.startswith("Esti corector"):
                return "[]"                            # nu repara nimic
            return json.dumps([{"id": i, "title": "Titlu romanesc fara diacritice",
                                "teaser": "Rezumat fara diacritice si cuvinte",
                                "category": "extern", "entities": [], "icon": None}
                               for i in range(len(user.split("[")) - 1)])

    p = _NuRepara()
    out, _, used = main.process_new([_item_diacritice()], p, budget=5)
    assert used == 2
    publicate = [x for x in out if x.get("model") == "B"]
    assert len(publicate) == 1                         # articolul NU dispare
    assert "diacritice" in diacritice.raport()
    assert diacritice.statistici()["reparate"] == 0
