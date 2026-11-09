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
