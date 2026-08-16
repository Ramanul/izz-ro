"""O sinteza publicata ABSOARBE stirea noua despre acelasi eveniment, la acelasi permalink.

Decizia IZZ-0151. Pana acum `main.process_new` lua drept candidati la clustering cross-run
doar articolele `model == "B"` din stare, deci o sinteza C deja publicata era invizibila: se
forma un cluster nou si aparea A DOUA sinteza langa prima.

Masurat pe arhiva reconstruita, 7443 de articole (2026-08-05): din 623 de perechi duplicate
(aceeasi rubrica, <=6h, Jaccard>=0.5) — pragurile metricii din 2026-08-04 — 183 sunt C/C si
145 sunt B/C, adica 328 (53%) contin o sinteza. TOATE trec pragul `_strict_match`, deci s-ar
fi unit daca ar fi fost eligibile. Pragul NU s-a atins: se schimba doar cine e candidat.

Costul masurat pe aceeasi arhiva: +1.1 apeluri AI pe rulare (buget 12-18), fiindca 182 din
cele 470 de atasari cad in grupuri care erau deja candidat de sinteza, deci apelul e platit.
"""
import json
from datetime import datetime, timedelta, timezone

from generator import main, process, render


def _iso(minutes_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


class _Provider:
    """Nu cheama nimic: intoarce un raspuns C minim valid.

    Impachetat intr-o lista cu `id: 0` (2026-08-16, batching Model C): `process_cluster`
    (calea singulara, folosita direct de restul testelor din fisier) accepta si lista --
    `_parse_json` ia primul obiect din ea -- iar `process_clusters_batch` (calea prin
    `main.process_new`, exercitata de testul de mai jos) cere exact formatul asta, cu id
    per cluster. Un singur fake, ambele cai."""
    name = "fals"
    calls = 0
    failures = 0
    last_error = None

    def complete(self, system, user):
        return json.dumps([{"id": 0,
                            "title": "Incendiul de la depozitul din Constanta, stins dupa opt ore",
                            "synthesis": "Pompierii au stins incendiul dupa opt ore de interventie.",
                            "category": "extern"}])


def _sinteza_publicata(**kw) -> dict:
    """O sinteza C asa cum arata in `data/articles.json`: fara `original_title` (scrub juridic),
    cu `slug` persistat si cu lista ei de surse."""
    baza = {
        "url": "https://a.ro/incendiu", "original_link": "https://a.ro/incendiu",
        "source": "a", "source_name": "A", "model": "C", "processed_by": "gemini",
        "slug": "incendiu-puternic-la-depozitul-din-constanta",
        "title": "Incendiu puternic la depozitul din Constanta",
        "synthesis": "Un incendiu a izbucnit la un depozit din Constanta.",
        "category": "extern", "published": _iso(120),
        "sources": [{"name": "A", "url": "https://a.ro/incendiu"},
                    {"name": "B", "url": "https://b.ro/incendiu"}],
    }
    baza.update(kw)
    return baza


def _stire_noua(**kw) -> dict:
    baza = {
        "url": "https://c.ro/stins", "original_link": "https://c.ro/stins",
        "source": "c", "source_name": "C", "model": None,
        "title": "Incendiul de la depozitul din Constanta a fost stins",
        "original_title": "Incendiul de la depozitul din Constanta a fost stins",
        "description": "Pompierii au anuntat ca focul a fost lichidat dupa opt ore de lupta.",
        "category": "extern", "published": _iso(5),
    }
    baza.update(kw)
    return baza


def test_sinteza_publicata_absoarbe_stirea_noua_in_loc_sa_apara_a_doua():
    """Traseul complet prin `process_new`, cu clustering-ul REAL — asta e ce s-a schimbat."""
    veche = _sinteza_publicata()
    noua = _stire_noua()
    procesate, folded, _ = main.process_new([noua], _Provider(), budget=5, existing=[veche])

    assert len(procesate) == 1, "a doua sinteza nu mai are voie sa apara"
    rep = procesate[0]
    assert rep["url"] == veche["url"]
    assert rep["slug"] == veche["slug"], "permalink-ul deja indexat trebuie sa supravietuiasca"
    assert rep["title"] != veche["title"], "continutul se ACTUALIZEAZA, doar slug-ul e fix"
    assert noua["url"] in folded


def test_reprezentantul_e_articolul_deja_publicat_chiar_daca_stirea_noua_e_mai_veche():
    """Ordinea cronologica singura ar fi dat rep-ul itemului nou — si atunci pagina deja
    indexata ar fi fost inlocuita cu alta, exact ce interzice IZZ-0151."""
    veche = _sinteza_publicata(published=_iso(10))
    noua = _stire_noua(published=_iso(300))       # publicata INAINTEA sintezei
    rep = process.process_cluster([noua, veche], _Provider())
    assert rep["url"] == veche["url"] and rep["slug"] == veche["slug"]


def test_sursele_sintezei_absorbite_nu_se_pierd():
    """Sinteza absorbita are 2 surse; itemul nou aduce un al treilea domeniu. Fara unire,
    coroborarea deja publicata s-ar reduce la un singur link la prima actualizare."""
    rep = process.process_cluster([_stire_noua(), _sinteza_publicata()], _Provider())
    assert [s["url"] for s in rep["sources"]] == [
        "https://a.ro/incendiu", "https://b.ro/incendiu", "https://c.ro/stins"]


def test_actualizarea_marcheaza_updated_iar_prima_publicare_nu():
    actualizata = process.process_cluster([_stire_noua(), _sinteza_publicata()], _Provider())
    assert actualizata.get("updated")

    prima = process.process_cluster(
        [_stire_noua(), _stire_noua(url="https://d.ro/x", original_link="https://d.ro/x")],
        _Provider())
    assert not prima.get("updated"), "un cluster numai din iteme noi e prima publicare"


def test_datemodified_urmeaza_updated_cand_sinteza_s_a_actualizat():
    a = {"model": "C", "title": "T", "synthesis": "S", "category": "extern", "slug": "s",
         "published": "2026-08-05T06:00:00+00:00", "updated": "2026-08-05T11:00:00+00:00"}
    ld = render._article_jsonld(a)
    assert ld["datePublished"] == a["published"]
    assert ld["dateModified"] == a["updated"]


def test_calea_fara_ai_nu_lasa_titlul_gol_cand_repul_e_deja_publicat():
    """Membrii publicati nu mai au `original_title` (scrub L8/1996). Pe calea fara cheie,
    rep-ul ar fi ramas cu titlu gol — adica exact „mangled output"-ul interzis de §7."""
    rep = process.process_cluster([_stire_noua(), _sinteza_publicata()], None)
    assert rep["title"] == "Incendiu puternic la depozitul din Constanta"
    assert rep["synthesis"]
