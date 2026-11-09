"""Culoarea semantică: măsurată pe contrast, cu un singur înțeles per token.

DE CE EXISTĂ. Pe 2026-11-08 s-a propus o paletă „epistemică" (verde = consens, albastru =
traseul sursei, ocru = divergență, indigo = incertitudine) cu valori luate din paletare
web uzuale: #4E9F6E, #3B82F6, #D97706, #6366F1. Trei dintre ele nu trec AA ca text pe
fundalul de hârtie al site-ului (3,09:1 / 3,52:1 / 3,05:1 față de pragul 4,5:1), iar
albastrul ar fi intrat în conflict cu `--navy`, care e deja culoarea de ACȚIUNE — un link
și o etichetă epistemică ar fi arătat la fel.

Testul ăsta nu e o părere despre estetică: calculează raportul de contrast WCAG pe valorile
din `styles.css` și verifică două lucruri care se strică tăcut:
  1. fiecare token semantic are contrast AA și în tema deschisă, și în cea întunecată;
  2. nu există o culoare „de emoție" — un token folosit pentru tragedii/alerte de presă.

Ce NU poate spune: contrastul real după antialiasing și fonturi (cere browser, vezi
`.claude/reguli/13-frontend.md`). Cifra de aici e limita superioară a încrederii.
"""
from __future__ import annotations

import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(ROOT, "static", "styles.css")

# Prag AA pentru text normal. Etichetele semantice sunt text mic (11-13px), deci NU li se
# aplică pragul relaxat de 3:1 pentru text mare — verificarea e intenționat mai strictă.
PRAG_AA = 4.5

SEMANTICE = ("--ok", "--warn", "--live", "--infer")


def _css() -> str:
    with open(CSS_PATH, encoding="utf-8") as fh:
        return fh.read()


def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _luminanta(culoare: str) -> float:
    canale = []
    for v in _hex(culoare):
        c = v / 255
        canale.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = canale
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = _luminanta(a), _luminanta(b)
    deschis, inchis = max(la, lb), min(la, lb)
    return round((deschis + 0.05) / (inchis + 0.05), 2)


def _tema(bloc: str | None) -> dict[str, str]:
    """Tokenii `--x: #hex` dintr-un bloc al foii de stil (None = `:root`)."""
    css = _css()
    if bloc is None:
        sursa = css.split(":root {", 1)[1].split("\n}", 1)[0]
    else:
        sursa = css.split(f'[data-theme="{bloc}"]', 1)[1].split("\n}", 1)[0]
    return {m.group(1): m.group(2) for m in re.finditer(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})", sursa)}


@pytest.mark.parametrize("token", SEMANTICE)
def test_tokenul_are_contrast_aa_pe_tema_deschisa(token):
    t = _tema(None)
    assert token in t, f"{token} lipsește din :root — un `var()` fără definiție se aruncă tăcut"
    raport = contrast(t[token], t["--paper"])
    assert raport >= PRAG_AA, (
        f"{token} = {t[token]} are {raport}:1 pe --paper ({t['--paper']}); pragul e {PRAG_AA}:1. "
        "Nu coborî pragul: coboară nuanța până trece (adică închide culoarea, nu o face mai vie).")


@pytest.mark.parametrize("token", SEMANTICE)
def test_tokenul_are_contrast_aa_pe_tema_intunecata(token):
    t = _tema("dark")
    assert token in t, f"{token} nu are variantă pentru tema întunecată (punctul ar deveni invizibil)"
    raport = contrast(t[token], t["--paper"])
    assert raport >= PRAG_AA, f"{token} în dark = {t[token]} are {raport}:1 pe --paper dark"


def test_cele_patru_semnale_sunt_distincte_intre_ele():
    """Două stări epistemice diferite nu au voie să arate aproape la fel.

    Pragul de 20/255 per canal e deliberat larg: nu verifică „se văd diferit" (lucru de
    ochi), ci prinde cazul real în care cineva pune două variante de verde pentru două
    înțelesuri diferite.
    """
    t = _tema(None)
    perechi = [(a, b) for i, a in enumerate(SEMANTICE) for b in SEMANTICE[i + 1:]]
    for a, b in perechi:
        ca, cb = _hex(t[a]), _hex(t[b])
        distanta = max(abs(x - y) for x, y in zip(ca, cb))
        assert distanta >= 20, (
            f"{a} ({t[a]}) și {b} ({t[b]}) sunt prea apropiate (delta max {distanta}/255): "
            "doi semantici diferiți trebuie să se poată distinge fără efort.")


def test_nu_exista_culoare_marcata_pentru_emotia_stirii():
    """Regula de aur, verificată pe numele tokenilor, nu pe promisiuni.

    Un token nou numit `--breaking`, `--urgent`, `--tragedie`, `--criza` ar însemna că
    culoarea răspunde la gravitatea știrii. Aceeași informație cu aceeași bază epistemică
    trebuie să arate identic, fie că e un deces, fie că e un meci.
    """
    interzise = ("--breaking", "--urgent", "--urgenta", "--tragedie", "--criza", "--crisis",
                 "--alert", "--alarm", "--panic", "--danger-emotion")
    css = _css()
    gasite = [t for t in interzise if re.search(rf"{re.escape(t)}\s*:", css)]
    assert not gasite, (
        f"token(i) de emoție în paletă: {gasite}. Culoarea semantică răspunde doar la "
        "„cât de verificată e informația\", niciodată la „cât de gravă e știrea\".")


def test_legenda_traduce_fiecare_semnal_in_cuvinte():
    """Un punct colorat fără legendă e decor. Legenda trebuie să acopere tokenii folosiți.

    Se citesc ȘABLONUL, nu CSS-ul: `--live` poate exista ca token fără să apară în legendă
    (divergența e condiționată), dar `--ok`, `--warn` și `--infer` apar pe orice sinteză.
    """
    with open(os.path.join(ROOT, "templates", "article.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    legenda = tpl.split('class="trust-key"', 1)
    assert len(legenda) == 2, "legenda marcajelor a dispărut din pagina de articol"
    bloc = legenda[1].split("</p>", 1)[0]
    for clasa in ("trust--ok", "trust--single", "trust--infer"):
        assert clasa in bloc, f"legenda nu explică {clasa}"


def test_rezerva_la_sursa_e_marcata_vizual_nu_doar_tipografic():
    """„cu rezervă la sursă" era un <em> fără culoare — adică invizibil ca stare.

    Marca trebuie să poarte clasa semantică, altfel cititorul vede un accent de stil, nu
    un grad de certitudine.
    """
    with open(os.path.join(ROOT, "templates", "article.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    assert tpl.count('class="dialectic-hedge"') >= 2, (
        "marca de rezervă lipsește din una dintre listele dialectice (comun/unică)")
    assert "trust--infer" in tpl.split('class="dialectic-hedge"', 1)[1][:120], (
        "marca de rezervă nu poartă clasa semantică indigo")


def test_cardul_poarta_marca_de_rezerva_cand_sinteza_o_are():
    """Amprenta epistemica trebuie sa fie vizibila din prima pagina, nu la al doilea clic.

    Cardul spune cate confirmari are sinteza, dar nu spunea daca o afirmatie din ea si-a
    pierdut rezerva sursei. Verificat pe datele reale (8 nov): 437 articole cu dialectic,
    157 cu cel putin un fapt cu rezerva — deci semnalul are unde sa apara.
    """
    from generator import render
    from tests.test_render_dialectic import _articol

    card = render._env().get_template("_card.html").module.card
    cu_rezerva = str(card(_articol("SYNTHESIS_VALID")))   # fixture-ul are un fapt hedged
    assert "trust--infer" in cu_rezerva and "cu rezervă" in cu_rezerva

    # Fara fapt cu rezerva, marca NU apare: un punct care apărea pe toate cardurile ar
    # deveni decor, exact ce legenda conditionata evita.
    fara = _articol("SYNTHESIS_VALID")
    for f in fara["dialectic"]["common"] + fara["dialectic"]["single"]:
        f["hedged"] = False
    assert "cu rezervă" not in str(card(fara))


def test_cardul_nu_schimba_textul_de_stare_editorial():
    """Marca e un element NOU, nu o rescriere: contractul de text ramane cel testat.

    `test_render_dialectic::test_cardul_spune_cate_confirmari_nu_doar_ca_e_multi_sursa`
    fixeaza formularea. Aici se verifica doar ca adaugarea nu a atins-o.
    """
    from generator import render
    from tests.test_render_dialectic import _articol

    card = render._env().get_template("_card.html").module.card
    html = str(card(_articol("SYNTHESIS_VALID")))
    assert "Sinteză din 3 publicații · 2 confirmări încrucișate · generată automat" in html


def test_numele_publicatiei_duce_la_sursa_fara_link_extern_in_corp():
    """Provenienta rămâne UN element (CLAUDE.md §7), dar trebuie să fie accesibilă din propoziție.

    Inainte: ca sa verifici o afirmatie, cautai publicatia intr-o lista la coada paginii.
    Acum: numele duce la ea prin ancoră internă. Linkul extern rămâne doar în `sources-box`.
    """
    from tests.test_render_dialectic import _articol, _articol_html, _pagina

    html = _articol_html(_pagina(_articol("SYNTHESIS_VALID")))
    sec = html[html.find('<section class="dialectic"'):]
    sec = sec[:sec.find("</section>")]
    assert 'class="sursa-link"' in sec, "numele publicațiilor nu mai sunt navigabile"
    assert 'href="#sursa-' in sec
    assert not [a for a in re.findall(r'<a [^>]*href="(?!#)[^"]*"', sec)]
    assert 'id="sursa-' in html, "ținta ancorei (rândul sursei) lipsește din pagina"


def test_textul_de_atribuire_ramane_propozitie():
    """Ancora nu are voie să spargă textul: „— Alfa, Beta" se citește, nu se compilează."""
    from tests.test_render_dialectic import _articol, _articol_html, _pagina

    html = _articol_html(_pagina(_articol("SYNTHESIS_VALID")))
    sec = html[html.find('<section class="dialectic"'):]
    curat = re.sub(r'<a class="sursa-link"[^>]*></a>', "", sec)
    assert "— Alfa, Beta" in curat


def test_rezerva_pierduta_este_spusa_in_cifre_pe_pagina():
    """Cea mai onesta informatie din tot lantul: cate afirmatii sunt mai sigure decat sursa.

    `forced` e determinist (propozitiile citate aveau marcator de incertitudine, formularea nu),
    deci nu e o euristica pe care s-o tinem in log. Masurat 2026-11-08: 112 din 1921 de fapte
    publicate (5,8%), in 88 de articole (20,1%).
    """
    from tests.test_render_dialectic import _articol, _pagina

    fara = _pagina(_articol("SYNTHESIS_VALID"))
    assert "dialectic-pierdute" not in fara, "cifra apare si cand nu exista fapte fara rezerva"

    a = _articol("SYNTHESIS_VALID")
    a["dialectic"]["common"][1]["forced"] = True
    cu = _pagina(a)
    assert "dialectic-pierdute" in cu
    assert "1 afirmație are la sursă o rezervă" in cu
    # pluralul e o regula de limba, nu un detaliu: „2 afirmație are" ar arata ca un bug
    a["dialectic"]["single"][0]["forced"] = True
    assert "2 afirmații au la sursă o rezervă" in _pagina(a)
