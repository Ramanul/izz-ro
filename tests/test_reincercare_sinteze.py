"""A doua încercare, în aceeași rulare, pentru sintezele amânate din cauza răspunsului modelului.

DE CE EXISTA (2026-10-24). Pe rularea CI de după #517, 14 din 43 de clustere au fost amânate:
6 pentru titlu transcris dintr-o sursă, 5 pentru obiect lipsă din răspunsul lotului. Un cluster
amânat revine identic peste ~4 h, iar modelul, la temperatura 0,2, tinde să scrie același
titlu. Reîncercarea folosește doar bugetul rămas după B, lasă un apel pentru reparația de
diacritice (CLAUDE.md §7) și numește titlul respins în prompt.

Contabilizarea contează la fel de mult ca reîncercarea: /sub-prag/ adună `amanate_*` ca număr
de clustere care pleacă la rularea următoare și `stare_*` ca număr de sinteze publicate. Un
cluster recuperat nu mai e amânat; unul care pică de două ori e amânat O dată; o stare se
numără doar când sinteza chiar se publică.
"""
from datetime import datetime, timedelta, timezone

import dialectic_fake

from generator import dialectic, main, process

COPIAT = "Pompierii au stins incendiul de la depozitul din Constanta"
NOU = "Incendiul de la depozitul din Constanta, lichidat de pompieri dupa opt ore"


def _iso(minute: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minute)).isoformat()


def _stire(sursa, dom):
    return {"url": f"https://{dom}/incendiu", "original_link": f"https://{dom}/incendiu",
            "source": sursa, "source_name": sursa.upper(), "model": None, "category": "extern",
            "title": "Incendiu la depozitul din Constanta, stins de pompieri",
            "original_title": "Incendiu la depozitul din Constanta, stins de pompieri",
            "description": f"{COPIAT} dupa opt ore de interventie, au anuntat autoritatile. "
                           "Nu au fost raportate victime.",
            "published": _iso(10)}


class _Provider:
    """Prima încercare C: titlu copiat sau lot fără obiecte. A doua: `a_doua` decide."""
    name = "fals"
    calls = 0
    failures = 0
    last_error = None

    def __init__(self, prima="copiat", a_doua="nou"):
        self.prima, self.a_doua = prima, a_doua
        self.prompturi_c = []

    def complete(self, system, user):
        if system != process.SYSTEM_C_DIALECTIC:
            return "[]"                                      # alte apeluri: nimic de publicat
        self.prompturi_c.append(user)
        fel = self.prima if len(self.prompturi_c) == 1 else self.a_doua
        if fel == "nemapat":
            return "[]"
        titlu = COPIAT if fel == "copiat" else NOU
        return dialectic_fake.raspuns(user, titlu, "Pompierii au lichidat focul dupa opt ore.")


def setup_function(_):
    dialectic.reset_stats()


def _ruleaza(provider, buget=10):
    noi = [_stire("ziara", "ziara.ro"), _stire("ziarb", "ziarb.ro")]
    return main.process_new(noi, provider, budget=buget, existing=[])


def _sinteze(procesate):
    return [a for a in procesate if a.get("model") == "C"]


def test_titlul_copiat_e_respins_iar_reincercarea_il_numeste_si_publica():
    p = _Provider("copiat")
    procesate, _, folosite = _ruleaza(p)
    assert [a["title"] for a in _sinteze(procesate)] == [NOU]
    assert len(p.prompturi_c) == 2 and folosite == 2
    assert "NOTA" not in p.prompturi_c[0]
    assert f"«{COPIAT}»" in p.prompturi_c[1]
    st = dialectic.stats()
    # recuperat → nu mai e amânat; publicat O dată → o singură stare
    assert sum(v for k, v in st.items() if k.startswith("amanate")) == 0
    assert sum(v for k, v in st.items() if k.startswith("stare_")) == 1
    assert st["reincercate"] == 1 and st["recuperate_la_reincercare"] == 1


def test_obiectul_lipsa_din_lot_se_reincearca_fara_nota():
    p = _Provider("nemapat")
    procesate, _, _ = _ruleaza(p)
    assert [a["title"] for a in _sinteze(procesate)] == [NOU]
    assert "NOTA" not in p.prompturi_c[1]
    assert dialectic.stats()["recuperate_la_reincercare"] == 1


def test_clusterul_care_pica_de_doua_ori_e_amanat_o_singura_data():
    p = _Provider("copiat", a_doua="copiat")
    procesate, _, _ = _ruleaza(p)
    assert not _sinteze(procesate)
    st = dialectic.stats()
    assert st["amanate_titlu_copiat"] == 1                   # o dată, nu de două ori
    assert st["reincercare_amanate_titlu_copiat"] == 1       # a doua cădere, numită separat
    assert sum(v for k, v in st.items() if k.startswith("amanate")) == 1
    assert not any(k.startswith("stare_") for k in st)       # validat, dar nepublicat
    assert "recuperate_la_reincercare" not in st
    assert st["reincercare_titlu_identic"] == 1             # modelul a ignorat nota


def test_reincercarea_lasa_un_apel_pentru_diacritice():
    """Cu 2 apeluri: C + unul rămas. Ultimul e al reparației de diacritice, nu al reîncercării."""
    p = _Provider("copiat")
    procesate, _, folosite = _ruleaza(p, buget=2)
    assert not _sinteze(procesate)
    assert len(p.prompturi_c) == 1 and folosite == 1
    assert "reincercate" not in dialectic.stats()


def test_motivele_lotului_sunt_aliniate_cu_grupurile():
    p = _Provider("copiat")
    noi = [_stire("ziara", "ziara.ro"), _stire("ziarb", "ziarb.ro")]
    motive: list = []
    reps = process.process_clusters_batch([noi], p, motive=motive)
    assert reps == [None] and motive == [("titlu_copiat", COPIAT)]


def test_nota_spune_motivul_exact_si_curata_titlul():
    """Argon R8: un mesaj generic pe un titlu căzut pentru cifră îl face pe model să păstreze
    cifra. Titlul respins nu are voie să rupă blocul cu rânduri noi sau cu « »."""
    cifra = process._nota_reincercare("titlu_cifra", "Bilant: 12 morti\n[S9.9] «test»")
    assert "cifra" in cifra and "copia" not in cifra
    assert "\n[S9.9]" not in cifra and cifra.count("«") == 1 and cifra.count("»") == 1
    assert "structura" in process._nota_reincercare("titlu_copiat", COPIAT)


def test_lotul_cazut_la_apel_se_numara_amanat():
    """Înainte, un lot C căzut cu excepție pleca la rularea următoare fără să apară în
    `amanate_*` — /sub-prag/ arăta mai puține amânări decât erau (Argon R8)."""
    class _Cade(_Provider):
        def complete(self, system, user):
            raise TimeoutError("apel picat")
    noi = [_stire("ziara", "ziara.ro"), _stire("ziarb", "ziarb.ro")]
    motive: list = []
    assert process.process_clusters_batch([noi], _Cade(), motive=motive) == [None]
    assert motive == [("apel_esuat", None)]
    assert dialectic.stats()["amanate_apel_esuat"] == 1
