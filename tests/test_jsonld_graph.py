"""JSON-LD: UN document per pagina, cu `@graph` si `@id`-uri stabile.

Inainte, fiecare `<script type="application/ld+json">` era un document independent, cu
`@context` propriu si fara niciun `@id`. Pe o pagina de articol asta insemna ca `Organization`
aparea de trei ori — nodul din `base.html`, `author`, `publisher` — ca trei entitati fara
legatura intre ele, si nimic nu spunea ca articolul si pagina sunt acelasi lucru.

Ce apara testele astea sunt exact cele patru feluri in care consolidarea poate esua TACUT
(HTML valid, pagina se randeaza, nimeni nu se plange, dar graful e stricat):
  1. doua blocuri raman pe pagina -> doua grafuri disjuncte, adica problema initiala
  2. o referinta `{"@id": X}` fara nod X in graf -> nod orfan, pe care validatoarele il ignora
  3. `@id`-uri derivate din pozitie in loc de URL -> alta entitate la fiecare randare
  4. `SearchAction` reintrodus (WS-0019: Google a scos sitelinks searchbox pe 21 nov. 2024)

Distinctia care conteaza la punctul 2, si care e usor de gresit: un obiect cu DOAR `@id` e o
REFERINTA si cere un nod cu acel id; un obiect cu `@id` plus alte chei e o DEFINITIE inline si
e perfect valid. Prima versiune a acestei verificari nu le distingea si raporta 2997 de
referinte „nerezolvate" care erau, toate, nodul `logo` definit inline.
"""
import glob
import json
import os
import re

import pytest

BLOC = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _blocuri(html: str) -> list:
    return BLOC.findall(html)


def _referinte(o, out: set) -> None:
    """Obiectele care au EXCLUSIV `@id`. Alea cer un nod cu acelasi id undeva in graf."""
    if isinstance(o, dict):
        if list(o.keys()) == ["@id"]:
            out.add(o["@id"])
        else:
            for v in o.values():
                _referinte(v, out)
    elif isinstance(o, list):
        for v in o:
            _referinte(v, out)


def _definitii(o, out: set) -> None:
    """`@id` insotit de alte chei = nodul e definit aici (fie in `@graph`, fie inline)."""
    if isinstance(o, dict):
        if "@id" in o and len(o) > 1:
            out.add(o["@id"])
        for v in o.values():
            _definitii(v, out)
    elif isinstance(o, list):
        for v in o:
            _definitii(v, out)


@pytest.fixture(scope="module")
def pagini(output_randat):
    """(cale, document JSON-LD) pentru fiecare pagina care emite JSON-LD."""
    out = []
    for f in glob.glob(os.path.join(output_randat, "**", "index.html"), recursive=True):
        with open(f, encoding="utf-8") as fh:
            blocuri = _blocuri(fh.read())
        if blocuri:
            out.append((f, blocuri))
    assert len(out) > 100, f"prea putine pagini cu JSON-LD ({len(out)}) — randarea a esuat?"
    return out


def test_un_singur_bloc_pe_pagina(pagini):
    """Doua blocuri = doua grafuri disjuncte, adica exact starea de dinainte de felie."""
    rele = [f for f, b in pagini if len(b) != 1]
    assert not rele, f"{len(rele)} pagini cu != 1 bloc, prima: {rele[:1]}"


def test_fiecare_bloc_parseaza_si_are_graph(pagini):
    for f, b in pagini:
        d = json.loads(b[0])          # ridica, cu calea in mesaj, daca e stricat
        assert d.get("@context") == "https://schema.org", f"{f}: @context lipsa sau gresit"
        assert isinstance(d.get("@graph"), list) and d["@graph"], f"{f}: @graph gol"


def test_nicio_referinta_orfana(pagini):
    """Un `{"@id": X}` fara nod X e invizibil pentru un validator: HTML-ul e valid, graful nu."""
    orfane = {}
    for f, b in pagini:
        d = json.loads(b[0])
        r, dd = set(), set()
        _referinte(d, r)
        _definitii(d, dd)
        lipsa = r - dd
        if lipsa:
            orfane[f] = lipsa
    assert not orfane, f"{len(orfane)} pagini cu referinte orfane, prima: {list(orfane.items())[:1]}"


def test_idurile_sunt_url_uri_absolute_nu_pozitii(pagini):
    """Un `@id` ca `#node-3` descrie alta entitate la fiecare randare in care ordinea difera."""
    rele = []
    for f, b in pagini[:200]:
        for nod in json.loads(b[0])["@graph"]:
            i = nod.get("@id", "")
            if not i.startswith("https://"):
                rele.append((f, i))
    assert not rele, f"@id-uri care nu sunt URL absolut: {rele[:3]}"


def test_pagina_e_legata_de_site(pagini):
    """`WebPage` fara `isPartOf` e o pagina care nu apartine niciunui site — nodul exista, dar
    nu spune nimic. Verificat pe toate paginile, nu pe un esantion: felia asta il introduce."""
    for f, b in pagini:
        g = json.loads(b[0])["@graph"]
        wp = [n for n in g if "WebPage" in str(n.get("@type", ""))]
        assert len(wp) == 1, f"{f}: {len(wp)} noduri WebPage, asteptat 1"
        assert "isPartOf" in wp[0], f"{f}: WebPage fara isPartOf"


def test_organizatia_e_declarata_o_data_si_referita(pagini):
    """Scopul intregii felii: `author` si `publisher` sunt REFERINTE la nodul unic, nu copii.
    Daca ar fi copii, testul de mai jos ar gasi Organization de mai multe ori in acelasi graf."""
    for f, b in pagini:
        g = json.loads(b[0])["@graph"]
        orgs = [n for n in g if n.get("@type") == "Organization"]
        assert len(orgs) == 1, f"{f}: {len(orgs)} noduri Organization in acelasi graf"
        art = next((n for n in g if n.get("@type") == "NewsArticle"), None)
        if art:
            for camp in ("author", "publisher"):
                assert list(art[camp].keys()) == ["@id"], \
                    f"{f}: NewsArticle.{camp} e copie, nu referinta"


def test_fara_searchaction(pagini):
    """WS-0019: Google a scos sitelinks searchbox pe 21 nov. 2024. Marcajul n-are consumator,
    iar reintroducerea lui ar fi re-litigare a unei decizii deja documentate cu sursa."""
    rele = [f for f, b in pagini if "SearchAction" in b[0]]
    assert not rele, f"SearchAction reintrodus in {len(rele)} pagini: {rele[:2]}"
