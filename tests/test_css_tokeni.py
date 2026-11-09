"""Tokenii din CSS: numele trebuie să existe, să nu mintă și să fie chiar folosiți.

Trei bug-uri reale găsite la inventarul din 2026-11-07 (faza 7), toate tăcute — un
`var(--x)` fără definiție nu dă eroare, declarația se aruncă și elementul rămâne fără
stil, ceea ce în producție arată ca „așa a fost gândit":

  --ok / --warn   punctul de încredere din card (`background: var(--ok)`) rămânea
                  transparent: verde = confirmat / ocru = o singură origine erau invizibile;
  --font-title    un nume de dinainte de rebranding: cifra din callout-ul financiar se
                  desena cu Inter, deși codul cerea seriful de titluri;
  --s-4           pas de spațiere scris greșit (seria veche era 5/8/13/21/…): marginea
                  dispărea cu totul.

Testele de mai jos sunt garda: orice token nou folosit fără definiție pică, iar numele
vechi (--gold*, --font-mono, --s-*) nu au voie să reapară.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = [os.path.join(ROOT, "static", "styles.css"),
       os.path.join(ROOT, "static", "harta-stiri", "harta-stiri.css")]

# Proprietăți puse din JavaScript sau din atributul `style` al șablonului: nu pot fi
# definite în foaia de stil, deci nu sunt orfane. Fiecare e verificată mai jos că e chiar
# setată de cineva — altfel whitelist-ul ar deveni o pubelă.
RUNTIME = {"--pw": "templates/_art.html", "--px": "templates/_art.html",
           "--py": "templates/_art.html",
           "--map-ar": "static/harta-stiri/harta-stiri.js",
           "--map-aspect": "static/harta-stiri/harta-stiri.js"}


def _citeste(cale: str) -> str:
    with open(cale, encoding="utf-8") as fh:
        return fh.read()


def _definitii(css: str) -> set[str]:
    return set(re.findall(r"(--[\w-]+)\s*:", css))


def _folosinte(css: str) -> set[str]:
    return set(re.findall(r"var\((--[\w-]+)", css))


@pytest.mark.parametrize("cale", CSS, ids=lambda p: os.path.basename(p))
def test_niciun_var_fara_definitie(cale):
    css = _citeste(cale)
    orfane = sorted(_folosinte(css) - _definitii(css) - set(RUNTIME))
    assert not orfane, (f"{os.path.basename(cale)}: var() fără definiție (declarația se "
                        f"aruncă tăcut): {orfane}")


@pytest.mark.parametrize("token,fisier", sorted(RUNTIME.items()))
def test_tokenii_de_runtime_sunt_chiar_setati(token, fisier):
    """Fiecare excepție din `RUNTIME` trebuie dovedită: cineva chiar scrie tokenul."""
    assert token in _citeste(os.path.join(ROOT, fisier)), \
        f"{token} e în whitelist, dar {fisier} nu îl setează — scoate-l din listă"


def test_numele_vechi_din_css_au_disparut():
    """--gold*, --font-mono și --s-<număr> erau aliasuri; rebrandingul s-a încheiat."""
    vechi = re.compile(r"--(?:gold[\w-]*|font-mono|s-\d+)\b")
    for cale in CSS:
        gasite = sorted(set(vechi.findall(_citeste(cale))))
        assert not gasite, (f"{os.path.basename(cale)} încă folosește numele vechi: "
                            f"{gasite}")


def test_numele_de_spatiere_isi_spun_valoarea():
    """`--sp-12` trebuie să fie 12px. Numele care mint costă la fiecare componentă nouă."""
    css = _citeste(CSS[0])
    perechi = re.findall(r"--sp-(\d+):\s*(\d+)px", css)
    assert len(perechi) >= 6, "scara de spațiere a dispărut din :root"
    rele = [(n, v) for n, v in perechi if n != v]
    assert not rele, f"nume de spațiere care nu corespund valorii (--sp-N = Mpx): {rele}"


def test_paleta_are_culorile_semantice_complet_definite():
    """Verde/ocru/roșu + variantele de temă întunecată, altfel un punct dispare din nou."""
    css = _citeste(CSS[0])
    for token in ("--ok", "--warn", "--live", "--infer"):
        assert re.search(rf"{token}:\s*#", css), f"{token} lipsește din :root"
    intunecat = css.split('[data-theme="dark"]', 1)[1]
    for token in ("--ok", "--warn", "--live", "--infer"):
        assert re.search(rf"{token}:\s*#", intunecat), \
            f"{token} nu are variantă pentru tema întunecată"
