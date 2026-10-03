"""Regresie audit extern 2026-10-03: anunțurile oficiale distincte nu se mai suprimă.

Cazurile reale din data/articles.json (starea din 3 oct):
1. „OFERTA VÂNZARE TEREN" — Primăria Călan a publicat oferta de DOUĂ ori (?p=15984,
   ?p=15998), iar Deleni și Dărmănești au oferte cu titlu identic: 4 rânduri cu același
   slug în fereastră. `select._dedup` le unea (tokeni identici), deci trei anunțuri de
   teren dispareau; în stare rămâneau 4 rânduri cu același (category, slug).
2. Primăria Nucet: „Rezultatul final la concursul de recrutare..." vs „Rezultatul probei
   interviu la concursul de recrutare..." — 10 tokeni comuni, două etape diferite ale
   aceleiași selecuții, tăiate la unul.

Precizare de calibrare: exemplul auditului „Primăria Moravița, asistent medical vs
consilier școlar" NU se unea nici înainte — tokenizer-ul real (`util.title_tokens`)
 scoate stopword-urile și dă doar 3 tokeni comuni, sub ambele praguri; testul rămâne
ca pin. Mecanismul real al pierderii sunt titlurile-șablon identice/aproape identice,
pe care garda `e_anunt_oficial` le scoate din unificare în ambele dedup-uri
(`select._dedup`, `moderation._dedup_visible`). Slug-urile dublate din stare istorică
se repară la `assign_slugs`, altfel relaxarea dedup ar transforma pierderea în
suprascriere la aceeași cale de output.
"""
from generator import moderation, render
from generator.select import publicitar_la_sursa
from generator.util import title_tokens

# Perechea reală Călan: același anunț repostat (?) sau două oferte pe același șablon —
# ambele cazuri sunt anunțuri oficiale de instituție, nu evenimente de presă.
_TEREN_CALAN_1 = {
    "title": "OFERTA VÂNZARE TEREN",
    "processed_by": "official",
    "url": "https://www.primariacalan.ro/?p=15984",
    "published": "2026-09-29T10:14:00+00:00",
}
_TEREN_CALAN_2 = {
    "title": "OFERTA VÂNZARE TEREN",
    "processed_by": "official",
    "url": "https://www.primariacalan.ro/?p=15998",
    "published": "2026-09-30T17:19:00+00:00",
}
# Etapele reale Nucet (titlurile exacte din stare); datate la 19h distanță ca să
# treacă și fereastra de 48h din _dedup_visible, care altfel nu era vizată.
_NUCET_FINAL = {
    "title": "Rezultatul final la concursul de recrutare pentru ocuparea, pe perioadă "
             "determinată, a unei funcții de ASISTENT MEDICAL COMUNITAR",
    "processed_by": "official",
    "url": "https://comunanucet.ro/rezultatul-final-la-concursul-de-recrutare",
    "published": "2026-10-02T12:52:00+00:00",
}
_NUCET_INTERVIU = {
    "title": "Rezultatul probei interviu la concursul de recrutare pentru ocuparea, pe "
             "perioadă determinată, a unei funcţii de ASISTENT MEDICAL COMUNITAR",
    "processed_by": "official",
    "url": "https://comunanucet.ro/rezultatul-probei-interviu-la-concursul-de-recrutare",
    "published": "2026-10-01T18:00:00+00:00",
}
_PRESA_A = {
    "title": "Portugalia a învins Danemarca în Liga Națiunilor, 3-2",
    "processed_by": "gemini", "entities": ["Portugalia", "Danemarca"],
    "url": "https://sport.ro/portugalia-danemarca",
    "published": "2026-10-02T10:00:00+00:00",
}
_PRESA_B = {
    "title": "Portugalia a învins Danemarca în Liga Națiunilor după un final nebun",
    "processed_by": "gemini", "entities": ["Portugalia", "Danemarca"],
    "url": "https://gsp.ro/portugalia-danemarca-liga-natiunilor",
    "published": "2026-10-02T12:00:00+00:00",
}


def test_fixtura_calan_si_nucet_depasesc_pragurile_de_dedup():
    """Fără gardă, ambele dedup-uri unesc perechile: dacă fixturile sunt sub prag,
    testele următoare nu măsoară nimic."""
    t1, t2 = title_tokens(_TEREN_CALAN_1["title"]), title_tokens(_TEREN_CALAN_2["title"])
    assert t1 == t2 and len(t1) >= 3, "titlurile Călan trebuie să fie token-identice"
    t3, t4 = title_tokens(_NUCET_FINAL["title"]), title_tokens(_NUCET_INTERVIU["title"])
    assert len(t3 & t4) >= 4, f"Nucet are doar {len(t3 & t4)} tokeni comuni"
    s3 = {t[:6] for t in t3}
    s4 = {t[:6] for t in t4}
    assert len(s3 & s4) >= 3, "Nucet trebuie să treacă și pragul de stems din _dedup_visible"


def test_select_dedup_pastreaza_ofertele_de_teren_calan():
    assert len(render._dedup([dict(_TEREN_CALAN_1), dict(_TEREN_CALAN_2)])) == 2


def test_select_dedup_pastreaza_etapele_nucet():
    assert len(render._dedup([dict(_NUCET_FINAL), dict(_NUCET_INTERVIU)])) == 2


def test_select_dedup_moravita_ramane_integrala_pin():
    """Pin, nu regresie: exemplul auditului (asistent medical vs consilier școlar) avea
    doar 3 tokeni comuni cu tokenizer-ul nostru și nu se unea nici înainte de gardă."""
    a = {"title": "Rezultatul selectiei dosarelor la concursul de asistent medical comunitar",
         "processed_by": "official",
         "url": "https://comunamoravita.ro/rezultatul-selectiei-dosarelor-a"}
    b = {"title": "Rezultatul selectiei dosarelor la concurs de consilier scolar",
         "processed_by": "official",
         "url": "https://comunamoravita.ro/rezultatul-selectiei-dosarelor-b"}
    assert len(title_tokens(a["title"]) & title_tokens(b["title"])) == 3
    assert len(render._dedup([a, b])) == 2


def test_select_dedup_continua_sa_uneste_presa_despre_acelasi_eveniment():
    """Direcția cealaltă (sect. 7 cere ambele): presa despre același meci SE unește
    în continuare — garda nu trebuie să dizolve dedup-ul legitime."""
    assert len(title_tokens(_PRESA_A["title"]) & title_tokens(_PRESA_B["title"])) >= 4
    assert len(render._dedup([dict(_PRESA_A), dict(_PRESA_B)])) == 1


def test_moderation_dedup_visible_pastreaza_anunturile_oficiale_distincte():
    """Fereastra de 48h nu salva clasa: perechile Călan e la 31h, Nucet la 19h, iar
    poarta de entități era goală (anunțurile oficiale au entities=None)."""
    perechi = [[dict(_TEREN_CALAN_1), dict(_TEREN_CALAN_2)],
               [dict(_NUCET_FINAL), dict(_NUCET_INTERVIU)]]
    for pereche in perechi:
        assert len(moderation._dedup_visible(pereche)) == 2, pereche


def test_moderation_dedup_visible_continua_sa_uneste_non_oficial():
    assert len(moderation._dedup_visible([dict(_PRESA_A), dict(_PRESA_B)])) == 1


def test_assign_slugs_repara_permalinkuri_dublate_din_stare():
    """Două articole care poartă ACELAȘI slug istoric (cazul real: 4 rânduri
    „oferta-vanzare-teren"): primul îl păstrează, restul primesc sufix numeric —
    altfel fiecare se scria peste primul la aceeași cale."""
    a = {"title": "Titlu vechi unu", "category": "local", "slug": "oferta-vanzare-teren"}
    b = {"title": "Titlu vechi doi", "category": "local", "slug": "oferta-vanzare-teren"}
    c = {"title": "Titlu vechi trei", "category": "local", "slug": "oferta-vanzare-teren"}
    render.assign_slugs([a, b, c])
    assert a["slug"] == "oferta-vanzare-teren"
    assert b["slug"] == "oferta-vanzare-teren-2"
    assert c["slug"] == "oferta-vanzare-teren-3"


def test_assign_slugs_articol_nou_ia_sufix_peste_rezervari():
    a = {"title": "Titlu vechi unu", "category": "local", "slug": "oferta-vanzare-teren"}
    b = {"title": "Titlu vechi doi", "category": "local", "slug": "oferta-vanzare-teren"}
    c = {"title": "Oferta vanzare teren", "category": "local"}
    render.assign_slugs([a, b, c])
    assert a["slug"] == "oferta-vanzare-teren"
    # articolul nou (fără slug) intră prin trecerea 2, din titlu, peste rezervările curente
    assert c["slug"] == "oferta-vanzare-teren-2"
    # repararea dublurilor istorice vine după și respectă ce s-a rezervat între timp
    assert b["slug"] == "oferta-vanzare-teren-3"


def test_publicitar_la_sursa_marcaj_din_url_original_sau_din_surse():
    assert publicitar_la_sursa(
        {"original_link": "https://www.elle.ro/advertorial/fashion-week-ghid/"})
    assert publicitar_la_sursa({"sources": [{"url": "https://elle.ro/advertorial/x/"}]})
    assert not publicitar_la_sursa(
        {"original_link": "https://www.digi24.ro/stiri/externe/o-stire"})
    assert not publicitar_la_sursa({})
