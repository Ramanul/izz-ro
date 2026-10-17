"""Agent grafic (HTML/CSS) — compune imaginea articolului din TIPOGRAFIE si GEOMETRIE,
in paleta site-ului. Randata ulterior cu headless Chromium (tools/gen_images.py). Aici doar
construim HTML-ul (pur, testabil, fara Chromium).

De ce HTML/CSS si nu Pillow: gradienturi netede, umbre, blend-modes, tipografie web ->
calitate de design peste ce poate desena Pillow. Chromium nu exista in build-ul Cloudflare,
deci randarea se face in GitHub Actions.

REPROIECTAT 2026-08-05, dupa a treia sesizare a proprietarului ca "desenele arata ca de copii".
Versiunea anterioara avea DOUA defecte de fond, si niciunul nu se putea repara prin rafinare:

  1. PICTOGRAME DE INTERFATA FOLOSITE CA ILUSTRATIE. Iconitele sunt desenate pentru ~24px:
     contur gros, forma schematica, zero detaliu. Exact ce le face bune la 24px le face sa
     arate infantil scalate la 300-620px. Nu exista set de iconite care sa rezolve asta --
     problema e categoria de artefact, nu calitatea lui.
  2. CULOARE ALEATORIE SATURATA. `hsl(seed*360/256, 70%, 92%)` plimba nuanta pe tot cercul
     cromatic, deci pe aceeasi pagina apareau verde crud langa roz langa portocaliu -- in
     timp ce site-ul are o paleta editoriala sobra (cerneala/hartie/auriu, vezi styles.css).
     Coperti care nu apartin site-ului pe care stau.

Acum: zero figurativ, paleta derivata din tokenurile din static/styles.css (§8), diferentiere
prin COMPOZITIE si valoare, nu prin nuanta. Titlul NU se pune pe bannerul de site -- e deja
pe pagina, sub imagine.
"""
import base64
import datetime
import hashlib
import json
import math
import os
import re

from . import config, geo
from .util import url_https

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ART_W, ART_H = 960, 504
COVER_W, COVER_H = 1200, 630
PHI = 1.618

_FONT_B64 = None

# Paleta: derivata din static/styles.css (§8 -- nu inventam culori). Fiecare intrare e
# (accent inchis, fundal deschis). Saturatie joasa deliberat: diferentiaza cardurile intre
# ele fara sa iasa din identitatea editoriala. Aurul ramane constanta care leaga totul.
_PALETE = [
    ("#1f2a44", "#faf5e6"),   # cerneala albastra pe --gold-wash (pana in 2026-10-17: #8b6918, maroniu)
    ("#15171c", "#f6f7f9"),   # --ink pe --paper
    ("#3d4a3a", "#f1f4ee"),   # masliniu
    ("#4a3b32", "#f7f2ed"),   # pamant ars
    ("#2f3d4a", "#eef1f5"),   # ardezie
    ("#4a3244", "#f5f0f4"),   # prun
]
GOLD = "#c9a227"
# Compozitia calma a stirilor locale/judetene (`.art--geo` in styles.css, aceleasi valori):
# cerneala pe hartie calda, forma locului in aur luminos. NU `#8b6918` — tonul acela, pe
# suprafete mari, se citea maroniu (sesizarea proprietarului 2026-10-17). Din aceeasi zi
# arta nu-l mai foloseste deloc: aurul e doar `GOLD` (decor), textul ia accentul paletei —
# un aur care trece 3:1 ca text pe hartie deschisa ajunge inapoi la mustar.
GEO_INK = "#1d1f24"
GEO_BG = "#faf6ec"
GEO_AUR = "#dcb84e"


def _font() -> str:
    global _FONT_B64
    if _FONT_B64 is None:
        p = os.path.join(_ASSETS, "PlayfairDisplay_800ExtraBold.ttf")
        _FONT_B64 = base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else ""
    return _FONT_B64


def _eticheta_categorie(cat: str) -> str:
    """Numele afisat al categoriei, cu diacritice — nu slug-ul URL.

    Coperta e limba cititorului: „Sănătate", nu „sanatate". Caderea pe capitalizat
    pastreaza contractul filtrului `cat_label` (render.py): o categorie noua neconfigurata
    arata decente pana intra in `config.CATEGORY_LABELS`."""
    cat = (cat or "").strip()
    if not cat:
        return ""
    return config.CATEGORY_LABELS.get(cat, cat.capitalize())


def _eticheta(a: dict) -> str:
    """Textul etichetei: locul la stirile de loc, altfel categoria (vezi geo.eticheta_copertei)."""
    return geo.eticheta_copertei(a) or _eticheta_categorie(a.get("category")) or "Știri"


def _subtitlu(a: dict) -> str:
    """A doua linie, discreta. Goala cand ar repeta eticheta (categorie == judet afisat)."""
    cat = (a.get("category") or "").strip()
    if not cat:
        return ""
    sub = _eticheta_categorie(cat)
    if sub.lower() == _eticheta(a).strip().lower():
        return ""
    return sub


# Data publicarii ca ELEMENT DE DESIGN (reproiectare 2026-09-06): coperta clasica era
# diagnosticata "~80% spatiu alb, template gol". Fiecare template umple acum canvasul cu
# tipografie mare si cu DATA stirii — fapt stabil din stare, nu provenienta (sect. 7 nu
# interzice data; numele surselor raman pe card, nu pe imagine).
_ZILE_RO = ("luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică")
_LUNI_RO = ("ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
            "august", "septembrie", "octombrie", "noiembrie", "decembrie")


def _data_copertei(a: dict) -> dict | None:
    """{zi, zi_n, wk, luna, an} din `published`, sau None daca e irecuperabila."""
    pub = (a.get("published") or "")[:10]
    try:
        d = datetime.date.fromisoformat(pub)
    except ValueError:
        return None
    return {"zi": f"{d.day:02d}", "zi_n": str(d.day), "wk": _ZILE_RO[d.weekday()],
            "luna": _LUNI_RO[d.month - 1], "an": str(d.year)}


def _et_px(et: str, trepte: tuple[tuple[int, int], ...], k: float) -> int:
    """Marimea etichetei treptata pe lungime: numele lungi nu se taie din cadru."""
    n = len((et or "").strip())
    for plafon, px in trepte:
        if n <= plafon:
            return int(px * k)
    return int(trepte[-1][1] * k)


def _rand_sub(sb: str, k: float) -> str:
    """Randul de subtitlu cu filet auriu inline; gol cand subtitlul e gol."""
    if not sb:
        return ""
    return (f'<div style="margin-top:{18 * k:.0f}px;display:flex;align-items:center;gap:{14 * k:.0f}px">'
            f'<span style="width:{64 * k:.0f}px;height:{3 * k:.0f}px;background:{GOLD};'
            f'display:inline-block"></span>'
            f'<span class="sub" style="margin-top:0;font-size:{18 * k:.0f}px;'
            f'letter-spacing:{4 * k:.0f}px">{sb}</span></div>')


_GRAIN = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E"
          "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E"
          "%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")")


def _base_css(w: int, h: int) -> str:
    # Tipografia scaleaza cu latimea, ca bannerul (960) si coperta og (1200) sa arate la fel.
    k = w / ART_W
    return (
        "*{margin:0;padding:0;box-sizing:border-box}"
        f"@font-face{{font-family:PF;src:url(data:font/ttf;base64,{_font()})}}"
        f"html,body{{width:{w}px;height:{h}px;overflow:hidden}}"
        f".stage{{position:relative;width:{w}px;height:{h}px;overflow:hidden;font-family:PF}}"
        f".grain{{position:absolute;inset:0;background-image:{_GRAIN};opacity:.05;"
        "mix-blend-mode:multiply;pointer-events:none}"
        # Eticheta: un singur tratament tipografic in tot fisierul. Pana pe 2026-08-05, un
        # template din patru isi desena propria varianta la 64px si aceeasi pagina arata
        # judetul la doua marimi diferite pe carduri alaturate.
        f".eticheta{{font-weight:800;font-size:{44*k:.0f}px;letter-spacing:{5*k:.0f}px;"
        "text-transform:uppercase;line-height:1}"
        f".sub{{font-weight:800;font-size:{15*k:.0f}px;letter-spacing:{4*k:.0f}px;"
        "text-transform:uppercase;opacity:.55;margin-top:" + f"{14*k:.0f}px}}"
        f".filet{{height:{3*k:.0f}px;background:{GOLD};border:0}}"
        f".marca{{position:absolute;font-weight:800;font-size:{13*k:.0f}px;letter-spacing:"
        f"{3*k:.0f}px;text-transform:uppercase;opacity:.4}}"
    )


def _t_editorial(a, acc, bg, k):
    """Pagina intai: bara de sus cu data, tipografie mare centrate vertical, filet dublu."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    et_px = _et_px(et, ((8, 128), (13, 102), (18, 82), (99, 60)), k)
    # Fara data, bara de sus ramane doar cu marca din stanga. Inainte punea tot "izz.ro" si
    # in dreapta, deci coperta de categorie (care n-are data) scria brandul de doua ori
    # pe acelasi rand.
    sus = f"{dt['wk']} {dt['zi_n']} {dt['luna']} {dt['an']}" if dt else ""
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:{56 * k:.0f}px;right:{56 * k:.0f}px;top:{30 * k:.0f}px;'
        f'display:flex;justify-content:space-between;align-items:baseline">'
        f'<span class="marca" style="position:static;font-size:{15 * k:.0f}px;opacity:.65">izz.ro</span>'
        f'<span class="marca" style="position:static;font-size:{13 * k:.0f}px">{sus}</span></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;right:{56 * k:.0f}px;top:{68 * k:.0f}px;'
        f'height:{3 * k:.0f}px;background:{GOLD}"></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;top:{92 * k:.0f}px;bottom:{96 * k:.0f}px;'
        f'display:flex;flex-direction:column;justify-content:center;max-width:{660 * k:.0f}px">'
        f'<div class="eticheta" style="font-size:{et_px}px;letter-spacing:{2 * k:.0f}px;'
        f'line-height:1.04">{et}</div>{_rand_sub(sb, k)}</div>'
        f'<div style="position:absolute;right:{-150 * k:.0f}px;bottom:{-190 * k:.0f}px;'
        f'width:{430 * k:.0f}px;height:{430 * k:.0f}px;border-radius:50%;'
        f'border:{2 * k:.0f}px solid {acc};opacity:.10"></div>'
        f'<div style="position:absolute;right:{-60 * k:.0f}px;bottom:{-260 * k:.0f}px;'
        f'width:{300 * k:.0f}px;height:{300 * k:.0f}px;border-radius:50%;'
        f'background:{acc};opacity:.05"></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;right:{56 * k:.0f}px;bottom:{34 * k:.0f}px;'
        f'display:flex;justify-content:space-between;align-items:baseline">'
        f'<span class="marca" style="position:static;font-size:{11 * k:.0f}px;opacity:.5">Portalul știrilor tale</span>'
        f'<span class="marca" style="position:static;font-size:{11 * k:.0f}px;opacity:.5">{sb}</span></div>'
        f'<div class="grain"></div></div>'
    )


def _t_inversat(a, acc, bg, k):
    """Noaptea: fond inchis, cifra zilei uriasa in aur — contrastul maxim din set."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    et_px = _et_px(et, ((8, 84), (13, 68), (18, 54), (99, 42)), k)
    numeral = (f'<div style="position:absolute;right:{56 * k:.0f}px;bottom:{34 * k:.0f}px;'
               f'text-align:right;line-height:1">'
               f'<div class="marca" style="position:static;font-size:{16 * k:.0f}px;opacity:.6">{dt["wk"]}</div>'
               f'<div style="font-weight:800;font-size:{232 * k:.0f}px;color:{GOLD};line-height:.92">{dt["zi"]}</div>'
               f'<div style="font-weight:800;font-size:{20 * k:.0f}px;letter-spacing:{7 * k:.0f}px;'
               f'text-transform:uppercase;opacity:.85">{dt["luna"]}</div></div>') if dt else ""
    return (
        f'<div class="stage" style="background:{acc};color:{bg}">'
        f'<div style="position:absolute;inset:{18 * k:.0f}px;border:{2 * k:.0f}px solid {GOLD};opacity:.5"></div>'
        f'<div style="position:absolute;left:{64 * k:.0f}px;top:{0};bottom:{0};'
        f'display:flex;flex-direction:column;justify-content:center;max-width:{500 * k:.0f}px">'
        f'<div class="eticheta" style="font-size:{et_px}px;letter-spacing:{2 * k:.0f}px;'
        f'line-height:1.06">{et}</div>'
        f'<div style="width:{190 * k:.0f}px;height:{3 * k:.0f}px;background:{GOLD};margin:{22 * k:.0f}px 0 0"></div>'
        f'<div class="sub" style="font-size:{18 * k:.0f}px;margin-top:{16 * k:.0f}px">{sb}</div></div>'
        f'<div style="position:absolute;left:{-90 * k:.0f}px;top:50%;transform:translateY(-50%) '
        f'rotate(45deg);width:{380 * k:.0f}px;height:{380 * k:.0f}px;border:{1 * k:.0f}px solid {bg};'
        f'opacity:.14"></div>{numeral}'
        f'<div class="marca" style="left:{64 * k:.0f}px;bottom:{40 * k:.0f}px">izz.ro</div>'
        f'<div class="grain"></div></div>'
    )


def _t_banda(a, acc, bg, k):
    """Coltul: banda inchisa la stanga cu eticheta; in dreapta, categoria-fantomă si data."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    et_px = _et_px(et, ((8, 42), (13, 34), (18, 28), (99, 22)), k)
    banda_jos = (f'<div style="position:absolute;left:{40 * k:.0f}px;bottom:{38 * k:.0f}px;'
                 f'opacity:.7;font-weight:800;font-size:{14 * k:.0f}px;letter-spacing:{3 * k:.0f}px;'
                 f'text-transform:uppercase;line-height:1.6">{dt["wk"]},<br>{dt["zi_n"]} {dt["luna"]}</div>'
                 ) if dt else ""
    data_dr = (f'<div style="position:absolute;right:{64 * k:.0f}px;top:{56 * k:.0f}px;text-align:right">'
               f'<div class="eticheta" style="font-size:{72 * k:.0f}px">{dt["zi_n"]}</div>'
               f'<div class="sub" style="margin-top:{8 * k:.0f}px;font-size:{17 * k:.0f}px">{dt["luna"]}</div>'
               f'<div style="width:{64 * k:.0f}px;height:{3 * k:.0f}px;background:{GOLD};'
               f'margin:{14 * k:.0f}px 0 0 auto"></div></div>') if dt else ""
    fantoma = sb or "stiri"
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:0;top:0;bottom:0;width:{300 * k:.0f}px;background:{acc}"></div>'
        f'<div style="position:absolute;left:{300 * k:.0f}px;top:0;bottom:0;width:{3 * k:.0f}px;background:{GOLD}"></div>'
        f'<div style="position:absolute;left:{40 * k:.0f}px;top:{56 * k:.0f}px;bottom:{110 * k:.0f}px;'
        f'display:flex;flex-direction:column;justify-content:center;max-width:{220 * k:.0f}px">'
        f'<div class="eticheta" style="font-size:{et_px}px;color:{bg};letter-spacing:{2 * k:.0f}px;'
        f'line-height:1.08">{et}</div></div>'
        f'<div style="position:absolute;left:{40 * k:.0f}px;width:{190 * k:.0f}px;height:{2 * k:.0f}px;'
        f'background:{GOLD};top:50%"></div>{banda_jos}{data_dr}'
        f'<div style="position:absolute;right:{-12 * k:.0f}px;bottom:{-34 * k:.0f}px;font-weight:800;'
        f'font-size:{168 * k:.0f}px;letter-spacing:{2 * k:.0f}px;text-transform:uppercase;'
        f'opacity:.06;white-space:nowrap">{fantoma}</div>'
        f'<div class="marca" style="right:{24 * k:.0f}px;bottom:{34 * k:.0f}px;color:{acc};opacity:.6">izz.ro</div>'
        f'<div class="grain"></div></div>'
    )


def _t_arc(a, acc, bg, k):
    """Sigiliul: cerc dublu auriu cu cifra zilei; eticheta mare ancorata la stanga."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    et_px = _et_px(et, ((8, 92), (13, 74), (18, 60), (99, 46)), k)
    cx, cy, r = int(764 * k), int(252 * k), int(168 * k)
    sigiliu = (f'<div style="position:absolute;left:{cx - r}px;top:{cy - r}px;width:{2 * r}px;height:{2 * r}px;'
               f'border-radius:50%;border:{2 * k:.0f}px solid {GOLD};opacity:.6"></div>'
               f'<div style="position:absolute;left:{cx - r + int(14 * k)}px;top:{cy - r + int(14 * k)}px;'
               f'width:{2 * r - int(28 * k)}px;height:{2 * r - int(28 * k)}px;border-radius:50%;'
               f'border:{1 * k:.0f}px solid {GOLD};opacity:.35"></div>'
               f'<div style="position:absolute;left:{cx - r}px;top:{cy - int(58 * k)}px;width:{2 * r}px;'
               f'text-align:center;line-height:1">'
               f'<div style="font-weight:800;font-size:{96 * k:.0f}px;color:{acc}">{dt["zi"]}</div>'
               f'<div style="font-weight:800;font-size:{15 * k:.0f}px;letter-spacing:{5 * k:.0f}px;'
               f'text-transform:uppercase;opacity:.55;margin-top:{6 * k:.0f}px">{dt["wk"]}</div>'
               f'<div style="font-weight:800;font-size:{13 * k:.0f}px;letter-spacing:{4 * k:.0f}px;'
               f'text-transform:uppercase;opacity:.55">{dt["luna"]}</div></div>') if dt else ""
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:{56 * k:.0f}px;top:{56 * k:.0f}px;'
        f'width:{int(120 * k)}px" class="filet"></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;top:{96 * k:.0f}px;bottom:{64 * k:.0f}px;'
        f'display:flex;flex-direction:column;justify-content:center;max-width:{470 * k:.0f}px">'
        f'<div class="eticheta" style="font-size:{et_px}px;letter-spacing:{2 * k:.0f}px;'
        f'line-height:1.05">{et}</div>{_rand_sub(sb, k)}</div>'
        f'<div style="position:absolute;left:{540 * k:.0f}px;top:{cy}px;width:{cx - r - int(540 * k)}px;'
        f'height:{1 * k:.0f}px;background:{acc};opacity:.2"></div>'
        f'<div style="position:absolute;left:{cx + r - int(7 * k)}px;top:{cy - int(7 * k)}px;'
        f'width:{14 * k:.0f}px;height:{14 * k:.0f}px;border-radius:50%;background:{GOLD}"></div>{sigiliu}'
        f'<div class="marca" style="left:{56 * k:.0f}px;bottom:{34 * k:.0f}px">izz.ro</div>'
        f'<div class="grain"></div></div>'
    )


# ---- silueta judetului -----------------------------------------------------
# Geometria vine din `data/harta_judete.json`, al carui antet isi declara sursa: Natural Earth,
# DOMENIU PUBLIC. Deci zero cerere de retea la randare, zero licenta de tert, zero termeni de
# serviciu de respectat. Alternativa evidenta — tile-uri raster de la OpenStreetMap — ar fi
# insemnat cereri automate catre serverul lor la fiecare rulare, pe care politica lor de tile-uri
# o interzice; aici nu se pune problema, fisierul e deja in repo si e deja folosit de harta
# stirilor (`render.py:590`).
#
# De ce asta NU incalca „zero figurativ" din reproiectarea 2026-08-05: critica de atunci tintea
# PICTOGRAMELE DE INTERFATA scalate de la 24px la 300px+ — contur gros, forma schematica, zero
# detaliu. Silueta unui judet e opusul: contur cartografic real, cu zeci de vertexuri, care
# CASTIGA detaliu la marime mare in loc sa-l piarda. Si, spre deosebire de eticheta „ECONOMIC"
# scrisa pe coperta unui articol economic, spune ceva adevarat si specific despre articol.
_HARTA_PATH = os.path.join(_ROOT, "data", "harta_judete.json")
_HARTA = None
_HARTA_INLINE_CACHE: dict[str, dict | None] = {}
_NUM = re.compile(r"-?\d+(?:\.\d+)?")

_PORTRAITS_PATH = os.path.join(_ROOT, "data", "portraits.json")
_INCADRARE_PATH = os.path.join(_ROOT, "data", "portrete_incadrare.json")
_INCADRARE: dict[str, dict] | None = None
_PORTRETE_LIBERE: dict[str, dict] | None = None


def incadrare_portrete() -> dict[str, dict]:
    """Unde e fata in fiecare portret (`tools/incadrare_portrete.py`), cheiat pe `img`.

    Lipsa fisierului nu opreste nimic: fara incadrare, medalionul cade pe `center 20%` din
    CSS — comportamentul de dinainte de 2026-10-16, deci o degradare, nu o pagina stricata."""
    global _INCADRARE
    if _INCADRARE is None:
        try:
            with open(_INCADRARE_PATH, encoding="utf-8") as f:
                _INCADRARE = json.load(f) or {}
        except (OSError, ValueError):
            _INCADRARE = {}
    return _INCADRARE
_PORTRETE_CERUTE: set[str] = set()
_CREDIT_FREE_RE = re.compile(r"^(cc0|cc[ -]?zero|public domain|pd([ -]|$))", re.I)


def _portrete_libere() -> dict[str, dict]:
    """Portretele din `data/portraits.json` cu licenta fara obligatie de credit (Public domain / CC0).

    Doar activele `Public domain` si `CC0` pot aparea pe carduri si pe prima pagina, unde nu
    exista legenda de atribuire (`content/legal/images.md`, `tests/test_image_policy.py`).

    Fisierul NU e copiat aici: `_portret_liber` il inscrie in `_PORTRETE_CERUTE`, iar
    `render.build()` copiaza exact ce s-a cerut, la finalul randarii. Invariantul vechi
    („portretele sunt deja in output, copytree-ul le-a adus pe toate") a fost inlocuit
    pentru ca publica 1.789 de fisiere din care doar 661 erau referite — 1.128 de fisiere
    (6,3% din plafonul Workers Free de 20.000) platite pentru nimic.
    """
    global _PORTRETE_LIBERE
    if _PORTRETE_LIBERE is None:
        out: dict[str, dict] = {}
        incadrare = incadrare_portrete()
        try:
            with open(_PORTRAITS_PATH, encoding="utf-8") as f:
                raw = json.load(f) or {}
            for k, v in raw.items():
                if not isinstance(v, dict) or v.get("miss"):
                    continue
                img = (v.get("img") or "").strip()
                lic = (v.get("license") or "").strip()
                if not img or not _CREDIT_FREE_RE.match(lic):
                    continue
                inc = incadrare.get(img) or {}
                if inc.get("respins"):
                    # poza de grup / fata de cativa pixeli: coperta generata e mai onesta
                    continue
                if os.path.exists(os.path.join(_ROOT, "media", img)):
                    out[k] = {"img": img, "name": (v.get("name") or k).strip(),
                              "taiere": inc.get("taiere")}
        except (OSError, ValueError):
            out = {}
        _PORTRETE_LIBERE = out
    return _PORTRETE_LIBERE


# ---- persoana potrivita stirii --------------------------------------------------
# Sesizarea proprietarului 2026-10-16 pe /extern/: copertile purtau chipul primei entitati
# care avea portret, oricat de marginala. Masurat pe `data/articles.json`, in aceeasi zi:
# Trump pe „Ucraina ar fi epuizat stocul de rachete Patriot…” (numit doar in rezumat), Trump
# pe „Presedintele Zelenski cere sprijin…” (alt om in titlu), Jair Bolsonaro pe o stire despre
# FIUL lui, Flavio. O fotografie pe coperta spune „despre EL e vorba"; daca nu e adevarat,
# minte mai tare decat orice eticheta. Regula de mai jos poate doar SCOATE portrete — eroarea
# ei cade pe coperta generata, niciodata pe o fata gresita.
_PARTICULE = frozenset({"da", "de", "del", "der", "di", "dos", "du", "la", "le", "van", "von", "bin", "al", "el"})
# Cuvinte care stau cu majuscula inaintea unui nume fara sa fie prenumele altcuiva: functii
# si substantive la inceput de propozitie („Administratia Trump…"). Inceputul de propozitie
# NU e scutit altfel: masurat pe titlurile din `data/articles.json` (2026-10-16), cuvintele cu
# majuscula din fata unui nume de familie, la inceput de titlu, erau „Administratia" (6) si
# prenumele ALTOR oameni — „Cristela Georgescu", „North West", „Flavio Bolsonaro".
_FUNCTII = frozenset({
    "presedintele", "presedinta", "premierul", "premiera", "liderul", "lidera", "ministrul",
    "ministra", "fostul", "fosta", "regele", "regina", "printul", "printesa", "papa",
    "cancelarul", "senatorul", "senatoarea", "generalul", "miliardarul", "antrenorul",
    "jucatorul", "jucatoarea", "candidatul", "candidata", "ambasadorul", "secretarul",
    "guvernatorul", "primarul", "primarita", "deputatul", "deputata", "comisarul", "seful",
    "sefa", "directorul", "fondatorul", "actorul", "actrita", "cantaretul", "cantareata",
    "liderii", "omul", "afaceristul", "magnatul", "oligarhul", "dictatorul", "vicepresedintele",
    "purtatorul", "sportivul", "tenismanul", "tenismena", "atacantul", "portarul", "pilotul",
    "administratia", "guvernul", "regimul", "echipa", "clubul", "familia", "era", "epoca",
})
_CUV = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")
# `portraits.json` tine si entitati NEUMANE (SAFE_TYPES din tools/fetch_portraits.py: tari,
# companii, aeroporturi). Pentru ele „numele de familie" nu exista: „Transilvania" dintr-un
# titlu despre vreme nu e Banca Transilvania. Un nume care incepe cu un substantiv comun de
# institutie sau de stat se cere INTREG, contiguu.
_PREFIX_NEUMAN = frozenset({
    "banca", "aeroportul", "organizatia", "universitatea", "partidul", "ministerul", "muzeul",
    "compania", "grupul", "uniunea", "consiliul", "curtea", "fundatia", "institutul",
    "agentia", "republica", "regatul", "federatia", "asociatia", "spitalul", "teatrul",
    "primaria", "guvernul", "parlamentul", "biserica", "catedrala", "palatul", "castelul",
    "stadionul", "clubul", "liga", "academia", "colegiul", "liceul", "societatea", "fondul",
    "comisia", "autoritatea", "inspectoratul", "politia", "jandarmeria", "statele",
    "emiratele", "arabia", "noua", "marea", "insulele", "orasul", "municipiul", "comuna",
})
_GEO_CATEGORII = frozenset({"local", "judetean", "regional"})
# Numele unui om pus pe un loc sau o institutie: „strada Maica Domnului", „Liceul Mihai
# Viteazul", „Aeroportul Henri Coanda". Stirea e despre loc — chipul omului ar minti.
_MARCAJ_LOC = frozenset({
    "strada", "str", "strazii", "bulevardul", "bd", "bdul", "calea", "aleea", "piata", "soseaua",
    "intrarea", "splaiul", "cartierul", "comuna", "comunei", "satul", "orasul", "orasului",
    "municipiul", "liceul", "liceului", "colegiul", "colegiului", "scoala", "scolii",
    "universitatea", "universitatii", "spitalul", "spitalului", "parcul", "parcului",
    "aeroportul", "aeroportului", "stadionul", "stadionului", "biserica", "catedrala",
    "manastirea", "fundatia", "baza", "portul", "statia", "statiei", "podul", "sala",
})


def _cuvinte(text: str) -> list[tuple[str, int, int]]:
    """(cuvant, start, end) pe textul fara diacritice — pozitii in acelasi sir."""
    return [(m.group(0), m.start(), m.end()) for m in _CUV.finditer(text)]


def _inceput_de_propozitie(text: str, start: int) -> bool:
    prefix = text[:start].rstrip(" \t ")
    return not prefix or prefix[-1] in ".!?:;\"«„“”—–(\n"


def _tokeni_nume(nume: str) -> tuple[set[str], set[str]]:
    """(tot numele, partea care il identifica in text). Prenumele singur NU identifica
    („Donald" nu e Trump), deci pentru 2+ tokeni identificatorii sunt cei de dupa primul."""
    from .util import strip_diacritics
    tok = [t for t in _CUV.findall(strip_diacritics(nume or "")) if t]
    toti = {t.lower() for t in tok}
    sens = [t for t in tok if t.lower() not in _PARTICULE]
    ident = sens[1:] if len(sens) >= 2 else sens
    return toti, {t.lower() for t in ident if len(t) >= 3}


def persoana_potrivita(a: dict, nume: str, *, in_titlu: bool) -> bool:
    """`nume` e chiar persoana despre care e stirea `a`?

    `in_titlu=True` (coperta): numele trebuie sa fie in TITLU — persoana pomenita doar in
    rezumat e context, nu subiect. `in_titlu=False` (caseta „In imagini" de pe articol):
    ajunge sa fie in titlu sau in corp.

    In ambele cazuri, un nume de familie lipit de ALT prenume („Flavio Bolsonaro" pentru
    entitatea Jair Bolsonaro) sau urmat de alt nume („Dan Barna" pentru Nicusor Dan,
    „Trump Jr." pentru Donald Trump) inseamna omonim: niciun portret, nu o ghicire.
    """
    from .util import strip_diacritics
    toti, ident = _tokeni_nume(nume)
    if not ident:
        return False
    titlu = strip_diacritics(a.get("display_title") or a.get("title") or "")
    corp = strip_diacritics(" ".join(x for x in (a.get("teaser"), a.get("synthesis")) if x))
    plin = " ".join(_CUV.findall(strip_diacritics(nume or "")))
    # Omonim geografic: „Mihail Kogalniceanu", „Avram Iancu", „Nicolae Balcescu" sunt si
    # comune. Pe o stire locala/judeteana numele e, practic mereu, localitatea.
    if (a.get("category") in _GEO_CATEGORII or a.get("judet")) \
            and geo._index().get(plin.upper()) == "local":
        return False
    if plin.split(" ", 1)[0].lower() in _PREFIX_NEUMAN:
        tipar = re.compile(r"\b" + r"\s+".join(map(re.escape, plin.split())) + r"\b", re.I)
        return bool(tipar.search(titlu) or (not in_titlu and tipar.search(corp)))
    gasit_in_titlu = False
    gasit = False
    for camp, text in (("titlu", titlu), ("corp", corp)):
        cuv = _cuvinte(text)
        for i, (w, st, _en) in enumerate(cuv):
            if w.lower() not in ident:
                continue
            # inceputul numelui (primul token al lui, daca e lipit inainte): cine sta in fata lui?
            j = i
            while j > 0 and cuv[j - 1][0].lower() in toti:
                j -= 1
            if j > 0 and cuv[j - 1][0].lower() in _MARCAJ_LOC:
                return False
            # vecinul din stanga: alt prenume = alt om
            if i > 0:
                pw, _pst, pen = cuv[i - 1]
                lipit = text[pen:st].strip() == ""
                if lipit and pw[:1].isupper() and pw.lower() not in toti and pw.lower() not in _FUNCTII:
                    return False
            # vecinul din dreapta: „Dan Barna", „Trump Jr"
            if i + 1 < len(cuv):
                nw, nst, _nen = cuv[i + 1]
                lipit = text[_en:nst].strip() == ""
                if (lipit and nw[:1].isupper() and nw.lower() not in toti
                        and not _inceput_de_propozitie(text, nst)):
                    return False
            gasit = True
            if camp == "titlu":
                gasit_in_titlu = True
    return gasit_in_titlu if in_titlu else gasit


def _cheie_nume(s: str) -> str:
    from .util import strip_diacritics
    return re.sub(r"\s+", " ", strip_diacritics((s or "").strip().lower()))


def _pozitie_in_titlu(a: dict, *nume: str) -> int:
    """Indexul primului cuvant identificator al numelui in titlu; foarte mare daca lipseste."""
    from .util import strip_diacritics
    titlu = strip_diacritics(a.get("display_title") or a.get("title") or "").lower()
    poz = 10 ** 6
    for n in nume:
        _toti, ident = _tokeni_nume(n)
        for t in ident:
            m = re.search(r"\b" + re.escape(t) + r"\b", titlu)
            if m:
                poz = min(poz, m.start())
    return poz


def subiect_titlu(a: dict, *registre: dict) -> tuple[str, dict] | None:
    """(cheie, inregistrare) pentru persoana despre care e stirea, sau None.

    Dintre entitatile cu portret (cautate in `registre`, in ordine) care trec
    `persoana_potrivita(in_titlu=True)`, castiga cea numita PRIMA in titlu — subiectul
    gramatical, nu ordinea extragerii AI. Inainte se lua prima entitate cu portret LIBER:
    pe „Volodimir Zelenski îi răspunde Marinei Le Pen…" coperta purta chipul lui Le Pen,
    fiindca doar ea avea portret Public domain (masurat pe randarea locala, 2026-10-17).
    """
    best: tuple[int, int, str, dict] | None = None
    for i, e in enumerate(a.get("entities") or []):
        key = _cheie_nume(e)
        rec = next((r[key] for r in registre if r and key in r), None)
        if not rec:
            continue
        nume_rec = rec.get("name") or ""
        # Entitatea AI e scrisa ca in articolul romanesc („Zelenski"), numele din Wikidata
        # adesea altfel („Zelensky") — oricare din doua identifica persoana in text.
        if not (persoana_potrivita(a, e, in_titlu=True)
                or persoana_potrivita(a, nume_rec, in_titlu=True)):
            continue
        cand = (_pozitie_in_titlu(a, e, nume_rec), i, key, rec)
        if best is None or cand[:2] < best[:2]:
            best = cand
    return (best[2], best[3]) if best else None


# CC BY / CC BY-SA cu versiune — aceeasi allowlist POZITIVA ca `render._CREDIT_REQUIRED_LICENSE`
# (paritatea e verificata in tests/test_foto_arhiva.py). Duplicata, nu importata: modulul asta
# ruleaza si fara render (tools/gen_images.py).
_CREDIT_REQ_RE = re.compile(r"^cc[ -]?by(?:[ -]sa)?[ -](\d)\.(\d)(?:[ -](\w+))?", re.I)
_PORTRETE_TOATE: dict[str, dict] | None = None


def _portrete_toate() -> dict[str, dict]:
    """Toate portretele publicabile: fara credit (PD/CC0) SI cu credit (CC BY / CC BY-SA).

    Serveste DOAR alegerii subiectului (`subiect_titlu`): cine e omul din titlu nu depinde de
    licenta pozei lui. Ce se afiseaza unde decide in continuare licenta (`_portret_liber`)."""
    global _PORTRETE_TOATE
    if _PORTRETE_TOATE is None:
        out: dict[str, dict] = {}
        incadrare = incadrare_portrete()
        try:
            with open(_PORTRAITS_PATH, encoding="utf-8") as f:
                raw = json.load(f) or {}
            for k, v in raw.items():
                if not isinstance(v, dict) or v.get("miss"):
                    continue
                img, lic = (v.get("img") or "").strip(), (v.get("license") or "").strip()
                if not img or not (_CREDIT_FREE_RE.match(lic) or _CREDIT_REQ_RE.match(lic)):
                    continue
                if (incadrare.get(img) or {}).get("respins"):
                    continue
                if os.path.exists(os.path.join(_ROOT, "media", img)):
                    rec = {"img": img, "name": (v.get("name") or k).strip(),
                           "taiere": (incadrare.get(img) or {}).get("taiere"),
                           "credit_required": not _CREDIT_FREE_RE.match(lic)}
                    if rec["credit_required"]:
                        page = url_https(v.get("page"))
                        if not page:
                            continue   # fara pagina-sursa https creditul ar fi incomplet sau nesigur
                        rec["credit"] = {"artist": (v.get("artist") or "").strip(), "page": page,
                                         "license": lic, "license_url": license_url_cc(lic)}
                    out[k] = rec
        except (OSError, ValueError):
            out = {}
        _PORTRETE_TOATE = out
    return _PORTRETE_TOATE


def license_url_cc(license_name: str | None) -> str | None:
    """URI-ul licentei CC BY / CC BY-SA, ca `render._license_url` (paritate testata)."""
    m = _CREDIT_REQ_RE.match((license_name or "").strip())
    if not m:
        return None
    sa = "-sa" if re.search(r"[ -]sa[ -]", " " + (license_name or "").strip().lower() + " ") else ""
    url = f"https://creativecommons.org/licenses/by{sa}/{m.group(1)}.{m.group(2)}/"
    return f"{url}{m.group(3).lower()}/" if m.group(3) else url


def _portret_card(a: dict) -> dict | None:
    """Portretul omului din titlu pentru CARD si hero, sau None.

    Domeniu public / CC0 ca pana acum, plus CC BY / CC BY-SA DOAR cu creditul complet atasat
    (`rec["credit"]`): cardul il afiseaza vizibil sub imagine (`_card.html`, `.card-credit`), deci
    imaginea nu ajunge niciodata intr-o zona fara legenda (`content/legal/images.md`). Coperta og
    (previzualizarea sociala) nu foloseste functia asta: acolo nu exista loc de credit.
    """
    if not (a.get("entities") or []):
        return None
    libere, toate = _portrete_libere(), _portrete_toate()
    ales = subiect_titlu(a, libere, toate)
    if not ales:
        return None
    rec = libere.get(ales[0]) or toate.get(ales[0])
    if not rec or (rec.get("credit_required") and not rec.get("credit")):
        return None
    _PORTRETE_CERUTE.add(rec["img"])
    return rec


def _portret_liber(a: dict) -> dict | None:
    """Portretul Public domain / CC0 al persoanei despre care e stirea, sau None.

    Nu „prima entitate cu portret": entitatile vin in ordinea extragerii AI, nu a importantei,
    iar o persoana pomenita in treacat nu are ce cauta pe coperta (`persoana_potrivita`).
    Subiectul se alege intai (`subiect_titlu`, peste TOATE portretele), apoi licenta: daca omul
    din titlu are doar poza cu credit obligatoriu, cardul ramane fara chip — nu primeste chipul
    altcuiva care se intampla sa aiba poza libera."""
    if not (a.get("entities") or []):
        return None
    libere = _portrete_libere()
    if not libere:
        return None
    ales = subiect_titlu(a, libere, _portrete_toate())
    if not ales or ales[0] not in libere:
        return None
    rec = libere[ales[0]]
    # Inscriere, nu copiere: acest modul nu stie OUT_DIR-ul randarii.
    _PORTRETE_CERUTE.add(rec["img"])
    return rec


def portrete_cerute() -> set[str]:
    """Caile relative (sub `media/`) ale portretelor pe care arta inline le afiseaza.

    Le citeste `render.build()` la finalul randarii ca sa copieze in `output/portraits/`
    EXACT atat. Fara asta, un `<img class="art-portret">` desenat de `_art.html` ar arata
    o imagine sparta — portretul e referit din grafica, nu din sablonul de articol.
    """
    return set(_PORTRETE_CERUTE)


def reset_portrete_cerute() -> None:
    """Goleste registrul la inceputul unei randari.

    Necesar pentru ca a doua randare din acelasi proces (teste, sau `--render-only` dupa
    pipeline) sa nu copieze portretele cerute de randarea anterioara: ar ramane fisiere
    nereferite in output, exact risipa pe care registrul o elimina.
    """
    _PORTRETE_CERUTE.clear()


def _harta_inline(cod: str | None, d: str | None = None) -> dict | None:
    """Geometria scalata pentru cutia 330x300 din `_art.html` (cache per forma).

    Implicit e judetul `cod`; cu `d` dat (conturul unei localitati, vezi `_uat_path`) se scaleaza
    acel contur, dupa bbox-ul LUI — o comuna cat un punct pe harta judetului umple acum cutia.
    """
    if not cod:
        return None
    key = f"{cod}|{d}" if d else cod   # calea insasi e cheia: fara hash, fara coliziuni
    if key not in _HARTA_INLINE_CACHE:
        d = d or _harta().get(cod)
        b = _bbox(d) if d else None
        if not b:
            _HARTA_INLINE_CACHE[key] = None
        else:
            x0, y0, x1, y1 = b
            lw, lh = max(x1 - x0, 0.01), max(y1 - y0, 0.01)
            s = min(330.0 / lw, 300.0 / lh)
            tx, ty = (330.0 - lw * s) / 2 - x0 * s, (300.0 - lh * s) / 2 - y0 * s
            _HARTA_INLINE_CACHE[key] = {
                "d": d,
                "transform": f"translate({tx:.2f} {ty:.2f}) scale({s:.4f})",
                "sw": f"{2.2 / s:.2f}",
            }
    return _HARTA_INLINE_CACHE[key]


# ---- conturul LOCALITATII (UAT) pentru stirile primariilor -----------------------
# Cerere proprietar 2026-10-17: pe stirile locale/judetene ramane FORMA locului, nu data.
# Conturul UAT-ului e mai precis decat judetul, dar il folosim DOAR unde e sigur: sursa e
# primaria acelei localitati (`pl_<judet>_<localitate>`), deci cheia sursei numeste locul in
# clar. Orice altceva (nume negasit, sursa de presa) cade pe silueta judetului, ca pana acum —
# o forma gresita e mai rea decat una mai larga (§7).
_UAT_DIR = os.path.join(_ROOT, "static", "harta-stiri", "data", "uat")
_UAT_CACHE: dict[str, dict[str, str]] = {}


def _uat_nume(s: str) -> str:
    from .util import strip_diacritics
    return re.sub(r"[\s-]+", " ", strip_diacritics(s or "").upper()).strip()


def _uat_judet(cod: str) -> dict[str, str]:
    """`{NUME UAT: path}` pentru judetul `cod`, citit o data. Lipsa fisierului -> `{}`."""
    if cod not in _UAT_CACHE:
        out: dict[str, str] = {}
        try:
            with open(os.path.join(_UAT_DIR, f"{cod}.json"), encoding="utf-8") as f:
                for u in json.load(f).get("uats") or []:
                    nume, d = _uat_nume(u.get("name") or ""), u.get("path") or ""
                    if nume and d:
                        # nume dublat in acelasi judet -> ambiguu, deci nefolosibil
                        out[nume] = "" if nume in out else d
        except (OSError, ValueError):
            out = {}
        _UAT_CACHE[cod] = out
    return _UAT_CACHE[cod]


def _uat_path(a: dict, cod: str | None) -> str | None:
    """Conturul localitatii a carei primarie a publicat stirea `a`, sau None."""
    if not cod:
        return None
    from .localities import parse_source_slug
    parsed = parse_source_slug(a.get("source") or "")
    if not parsed:
        return None
    return _uat_judet(cod).get(_uat_nume(parsed[1])) or None


# Localitati al caror nume, intr-o sursa care NU e din judetul lor, inseamna aproape mereu
# altceva: o capitala straina sau un prenume. Masurat 2026-10-17 pe ultimele 400 de stiri
# locale/judetene: „Roma" (2 stiri despre Italia -> comuna Roma, BT), „Matei" (actorul Matei
# Dima -> comuna Matei, BN). O sursa din judetul lor le deseneaza in continuare.
_OMONIME_STRAINE = frozenset({"ROMA", "MATEI"})


def _forma_loc(a: dict) -> tuple[str | None, str | None, str]:
    """(judet, contur de localitate sau None, subtitlu) pentru arta unei stiri locale/judetene.

    Forma urmeaza ETICHETA afisata (`geo.eticheta_copertei`), nu alt semnal: cardul care scrie
    „IAȘI" desenează Iasiul. Pana acum silueta venea doar din cheia sursei, deci 13 din 20 de
    carduri locale (masurat pe /local/, 2026-10-17) aratau numele locului langa o cutie goala,
    iar eticheta si forma puteau sa nu spuna acelasi lucru. Riscul de eroare e al etichetei, nu
    unul nou: forma doar il face vizibil, nu il adauga.

    Ordinea, de la sigur la mai putin sigur:
      1. eticheta e un judet -> silueta judetului;
      2. eticheta e o localitate dintr-un singur judet (sau din judetul sursei, la omonime) ->
         conturul UAT-ului, cand localitatea e chiar un UAT; altfel silueta judetului ei;
      3. altfel judetul sursei, ca inainte (`_judet`), cu UAT-ul primariei daca sursa e una.
    La o stire LOCALA, pasul 1 deseneaza UAT-ul resedintei (`geo.RESEDINTE`): „IAȘI" pe /local/
    e orasul; doar /judetean/ pastreaza conturul judetului (sesizarea proprietarului 2026-10-17:
    105 din 159 de carduri locale cu eticheta-judet aratau judetul).
    Subtitlul e judetul cand eticheta e o localitate, si nimic cand eticheta e chiar judetul:
    „LOCAL" sub nume repeta badge-ul cardului (auditul din 2026-10-17, sect. 5.2).
    """
    et = _eticheta(a).strip()
    cheie = _uat_nume(et)
    sursa = _judet(a)
    cod = d = None
    judete = _harta()
    for c in judete:
        if _uat_nume(geo.eticheta_judet(c)) == cheie:
            cod = c
            break
    if cod and a.get("category") == "local" and cod in geo.RESEDINTE:
        # stire LOCALA cu eticheta = numele judetului: e orasul, nu judetul -> UAT-ul resedintei
        d = _uat_judet(cod).get(_uat_nume(geo.RESEDINTE[cod])) or None
    if not cod and cheie:
        cand = {j for j in geo.judetele_localitatii(cheie) if j in judete}
        if sursa in cand:
            cod = sursa
        elif cheie in _OMONIME_STRAINE:
            pass   # „Roma" dintr-o sursa nationala e Italia, nu comuna din Botosani
        elif len(cand) == 1:
            cod = next(iter(cand))
        if cod:
            d = _uat_judet(cod).get(cheie) or None
    if not cod and sursa:
        cod, d = sursa, _uat_path(a, sursa)
    if not cod:
        return None, None, ""
    jud = geo.eticheta_judet(cod) or ""
    sub = "" if _uat_nume(jud) == cheie else jud
    return cod, d, sub


def _harta() -> dict:
    """`{cod judet: path SVG}`. Citit o data si tinut pe modul — randam mii de imagini per rulare.

    Orice esec de citire da `{}`, nu exceptie: coperta cade pe template-urile vechi. Un fisier
    de date lipsa nu are voie sa opreasca pipeline-ul (§7 — mai bine sobru decat stricat).
    """
    global _HARTA
    if _HARTA is None:
        try:
            with open(_HARTA_PATH, encoding="utf-8") as f:
                _HARTA = json.load(f).get("judete") or {}
        except (OSError, ValueError):
            _HARTA = {}
    return _HARTA


def _bbox(d: str):
    """Cutia de incadrare a unui path. Fisierul foloseste DOAR M/L/Z (verificat pe toate cele 42),
    deci numerele sunt perechi x,y in ordine si nu e nevoie de un parser de path."""
    n = [float(x) for x in _NUM.findall(d)]
    if len(n) < 4:
        return None
    xs, ys = n[0::2], n[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _silueta(cod: str | None, latime: float, inaltime: float, culoare: str, op: float) -> str:
    """SVG cu judetul scalat sa umple cutia data, pastrand proportia. "" cand lipseste geometria.

    Silueta intra INTREAGA in cutie: un judet taiat de margine nu se mai citeste ca judet, ci ca
    o pata (masurat vizual 2026-09-04, prima varianta o ancora la -110px si o taia pe trei parti).
    Judetele au forme foarte diferite (Constanta e alungita, Ilfov e compact), deci se scaleaza
    dupa bbox-ul PROPRIU, nu dupa viewbox-ul comun al tarii — altfel Ilfov ar aparea ca un punct.
    Grosimea conturului se imparte la scara, ca sa ramana constanta in pixeli pe toate judetele.
    """
    d = _harta().get(cod or "")
    return _silueta_d(d, latime, inaltime, culoare, op)


def _silueta_d(d: str | None, latime: float, inaltime: float, culoare: str, op: float,
               contur_op: float = .5) -> str:
    """Ca `_silueta`, pentru un path dat (judet sau localitate)."""
    b = _bbox(d) if d else None
    if not b:
        return ""
    x0, y0, x1, y1 = b
    lw, lh = max(x1 - x0, 0.01), max(y1 - y0, 0.01)
    s = min(latime / lw, inaltime / lh)
    tx, ty = (latime - lw * s) / 2 - x0 * s, (inaltime - lh * s) / 2 - y0 * s
    return (f'<svg width="{latime:.0f}" height="{inaltime:.0f}" '
            f'viewBox="0 0 {latime:.0f} {inaltime:.0f}" aria-hidden="true" focusable="false">'
            f'<g transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})">'
            f'<path d="{d}" fill="{culoare}" fill-opacity="{op}" stroke="{GOLD}" '
            f'stroke-opacity="{contur_op}" stroke-width="{2.2 / s:.2f}" stroke-linejoin="round"/>'
            f'</g></svg>')


def _judet(a: dict) -> str | None:
    """Codul judetului pe care coperta il poate desena, sau None.

    DOAR din cheia sursei (`geo.judet_sursa`), care il codeaza in clar (`pl_vrancea_...`, `cj_cluj`)
    — determinist, fara euristica. Titlul e refuzat deliberat ca sursa: o stire locala poate numi
    alt judet decat cel despre care e vorba, iar o silueta GRESITA e mai rea decat niciuna (§7).
    `regional` e exclus din acelasi motiv: acopera mai multe judete, deci oricare ar fi o minciuna.
    Masurat 2026-09-04 pe `data/articles.json`: 2.923 din cele 5.264 de articole cu axa geografica.
    """
    if (a.get("category") or "") not in ("local", "judetean"):
        return None
    cod = geo.judet_sursa(a.get("source"))
    return cod if cod and cod in _harta() else None


def _sub_harta(a: dict, cod: str) -> str:
    """Sub eticheta sta JUDETUL, nu categoria: el explica silueta si adauga ceva ce cardul nu are.
    Cade pe categorie cand eticheta E deja judetul — „CLUJ / CLUJ" n-ar spune nimic in plus.

    NU e inclusa in `gen_images._semnatura()`, si asta e deliberat: semnatura decide ce imagine se
    REGENEREAZA, iar adaugarea judetului acolo ar invalida-o pentru toate cele ~2.900 de articole
    locale deodata. Exact regenerarea in masa refuzata de proprietar (`IZZ-0163`) si exact modul in
    care `IZZ-0162` era pe cale sa stearga ~8.900 de imagini intr-o rulare. Consecinta acceptata:
    silueta apare pe copertile generate DE ACUM INCOLO, nu retroactiv; `FORCE_REGEN=1` le aduce
    pe cele vechi cand proprietarul decide asta.
    """
    nume = geo.eticheta_judet(cod) or ""
    return nume if nume.strip().lower() != _eticheta(a).strip().lower() else _subtitlu(a)


def _t_harta(a, acc, bg, k):
    """Silueta reala a judetului in dreapta, tipografia in stanga, in limbajul reproiectarii
    din 2026-09-06: bara de sus cu data si filet auriu, eticheta treptata, filet inline la
    subtitlu, bara de jos. Se alege doar cand judetul e cunoscut (vezi `_judet`).

    Alinierea la limbajul ala NU e cosmetica: dupa merge-ul cu main, un `_t_harta` ramas in
    stilul vechi ar fi dat articolelor locale exact coperta criticata acolo ca „~80% spatiu
    alb", pe langa carduri care poarta data. Latimea tipografiei e plafonata la 520px (fata de
    660 la `editorial`), ca numele lungi sa nu intre peste silueta (masurat: la 520px si 104px, „FLOREȘTI"
    ajungea la 14px de ea).
    """
    cod, d, sb = _forma_loc(a)
    et = _eticheta(a)
    et_px = _et_px(et, ((8, 92), (13, 76), (18, 62), (99, 48)), k)
    # Fara data (cerere proprietar 2026-10-17: pe local/judetean ramane forma locului) si cu
    # forma in AUR, nu in culoarea textului: aceeasi compozitie ca arta din pagina (`.art--geo`).
    acc, bg = GEO_INK, GEO_BG
    forma = _silueta_d(d or _harta().get(cod or ""), 330 * k, 300 * k, GEO_AUR, 1, contur_op=1)
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;right:{40 * k:.0f}px;top:{104 * k:.0f}px;'
        f'bottom:{72 * k:.0f}px;display:flex;align-items:center;line-height:0">'
        f'{forma}</div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;right:{56 * k:.0f}px;top:{30 * k:.0f}px;'
        f'display:flex;justify-content:space-between;align-items:baseline">'
        f'<span class="marca" style="position:static;font-size:{15 * k:.0f}px;opacity:.65">izz.ro</span></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;right:{56 * k:.0f}px;top:{68 * k:.0f}px;'
        f'height:{3 * k:.0f}px;background:{GOLD}"></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;top:{92 * k:.0f}px;bottom:{96 * k:.0f}px;'
        f'display:flex;flex-direction:column;justify-content:center;max-width:{470 * k:.0f}px">'
        f'<div class="eticheta" style="font-size:{et_px}px;letter-spacing:{2 * k:.0f}px;'
        f'line-height:1.04">{et}</div>{_rand_sub(sb, k)}</div>'
        f'<div class="grain"></div></div>'
    )


_TEMPLATES = [_t_editorial, _t_inversat, _t_banda, _t_arc]
# Numele compozitiilor, in ACEEASI ordine: `stil_inline` le trimite in clasa CSS
# `art--<nume>`, iar `build_html(sablon=...)` le cauta dupa nume. Perechea e verificata
# imediat mai jos, nu prin convenite: desincronizata, ar da tacut alta compozitie decat
# arata rasterul pentru acelasi articol.
_NUME_TEMPLATE = ("editorial", "inversat", "banda", "arc")
assert len(_NUME_TEMPLATE) == len(_TEMPLATES)


def _tile_xt_yt(lat: float, lon: float, z: int) -> tuple[float, float]:
    """Coordonatele FRACTIONARE de dala Web Mercator pentru (lat, lon)."""
    n = 2 ** z
    xt = (lon + 180) / 360 * n
    lat_r = math.radians(lat)
    yt = (1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n
    return xt, yt


def _t_cutremur(a, ch, acc, bg, k):
    """Coperta din date: harta OSM cu epicentrul (sursa EMSC) si panou editorial.

    Dalile vin de la tile.openstreetmap.org randate de Chromium in Actions
    (atribuirea obligatorie e tiparita pe imagine). Epicentrul cade la ~62% din
    latimea hartii, cu inele aurii concentrice — figura intreaga e geometrica,
    nu figurativa (regula din docstringul modulului).
    """
    et = ch.get("loc") or _eticheta(a)
    dt = _data_copertei(a)
    mag_ro = f'M {ch["mag"]:.1f}'.replace(".", ",")
    panel_w = 300
    cw = ART_W - panel_w
    epi_x, epi_y = (panel_w + int(cw * 0.62)) * k, int(ART_H * 0.5) * k
    xt, yt = _tile_xt_yt(ch["lat"], ch["lon"], 8)
    x0, y0 = int(xt) - 1, int(yt) - 1
    px, py = (xt - x0) * 256, (yt - y0) * 256
    grid_left, grid_top = epi_x - px * k, epi_y - py * k
    dale = "".join(
        f'<img src="https://tile.openstreetmap.org/8/{x0 + c}/{y0 + r}.png" '
        f'style="position:absolute;left:{grid_left + c * 256 * k:.0f}px;'
        f'top:{grid_top + r * 256 * k:.0f}px;width:{256 * k:.0f}px;height:{256 * k:.0f}px;'
        f'filter:grayscale(1) sepia(.14) brightness(1.05) contrast(.92)">'
        for c in range(4) for r in range(3))
    inele = "".join(
        f'<div style="position:absolute;left:{epi_x - r * k:.0f}px;top:{epi_y - r * k:.0f}px;'
        f'width:{2 * r * k:.0f}px;height:{2 * r * k:.0f}px;border-radius:50%;'
        f'border:{3 * k:.0f}px solid {GOLD};opacity:{op}"></div>'
        for r, op in ((52, ".9"), (34, ".65"), (18, "1")))
    data_txt = f'{dt["zi_n"]} {dt["luna"]} {dt["an"]}' if dt else ""
    adanc = f' · adâncime {ch["adancime"]} km' if ch.get("adancime") else ""
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:0;top:0;bottom:0;width:{panel_w * k:.0f}px;'
        f'background:{bg}"></div>{dale}{inele}'
        f'<div style="position:absolute;left:{epi_x - 9 * k:.0f}px;top:{epi_y - 9 * k:.0f}px;'
        f'width:{18 * k:.0f}px;height:{18 * k:.0f}px;border-radius:50%;background:{GOLD};'
        f'outline:{3 * k:.0f}px solid {bg}"></div>'
        f'<div style="position:absolute;left:{panel_w * k:.0f}px;top:0;bottom:0;'
        f'width:{3 * k:.0f}px;background:{GOLD}"></div>'
        f'<div style="position:absolute;left:{44 * k:.0f}px;top:{52 * k:.0f}px">'
        f'<div style="width:{96 * k:.0f}px;height:{3 * k:.0f}px;background:{GOLD}"></div>'
        f'<div class="eticheta" style="font-size:{40 * k:.0f}px;margin-top:{26 * k:.0f}px">{et}</div>'
        f'<div class="sub" style="margin-top:{10 * k:.0f}px">CUTREMUR</div></div>'
        f'<div style="position:absolute;left:{44 * k:.0f}px;bottom:{96 * k:.0f}px;line-height:1">'
        f'<div style="font-weight:800;font-size:{84 * k:.0f}px;color:{acc}">{mag_ro}</div>'
        f'<div style="font-weight:800;font-size:{16 * k:.0f}px;opacity:.7;margin-top:{10 * k:.0f}px">'
        f'{data_txt}{adanc}</div></div>'
        f'<div class="marca" style="left:{44 * k:.0f}px;bottom:{34 * k:.0f}px">izz.ro</div>'
        f'<div style="position:absolute;right:{12 * k:.0f}px;bottom:{10 * k:.0f}px;'
        f'background:{bg};opacity:.85;padding:{4 * k:.0f}px {8 * k:.0f}px">'
        f'<span class="marca" style="position:static;opacity:.65">'
        f'Hartă © OpenStreetMap · Seisme: EMSC</span></div>'
        f'<div class="grain"></div></div>'
    )


def _t_meteo(a, ch, acc, bg, k):
    """Coperta din date: prognoza pe 7 zile pentru localitatea stirii.

    Apare doar cand `eventdata.attach` a atasat `event_chart` (fail-safe la
    sursa: datele vin din api.open-meteo.com, etichetate pe imagine). Cifrele
    NU se recomputa aici — desenam exact ce e in stare.
    """
    zile = ch["zile"]
    lo = min(z["min"] for z in zile) - 2
    hi = max(z["max"] for z in zile) + 2
    x0, x1, y0, y1 = 350 * k, 920 * k, 150 * k, 390 * k
    step = (x1 - x0) / len(zile)
    bw = step * 0.5
    cols = []
    for i, z in enumerate(zile):
        cx = x0 + (i + .5) * step
        hmax = (z["max"] - lo) / (hi - lo) * (y1 - y0)
        hmin = (z["min"] - lo) / (hi - lo) * (y1 - y0)
        cols.append(
            f'<div style="position:absolute;left:{cx - bw / 2:.0f}px;width:{bw:.0f}px;'
            f'top:{y1 - hmax:.0f}px;height:{hmax - hmin:.0f}px;background:{GOLD};'
            f'border-radius:{9 * k:.0f}px"></div>'
            f'<div style="position:absolute;left:{cx:.0f}px;top:{y1 - hmax - 30 * k:.0f}px;'
            f'transform:translateX(-50%);font-weight:800;font-size:{22 * k:.0f}px">{z["max"]}°</div>'
            f'<div style="position:absolute;left:{cx:.0f}px;top:{y1 - hmin + 6 * k:.0f}px;'
            f'transform:translateX(-50%);font-weight:800;font-size:{15 * k:.0f}px;'
            f'opacity:.5">{z["min"]}°</div>'
            f'<div style="position:absolute;left:{cx:.0f}px;top:{y1 + 16 * k:.0f}px;'
            f'transform:translateX(-50%);font-weight:800;font-size:{20 * k:.0f}px">{z["lit"]}</div>'
            f'<div style="position:absolute;left:{cx:.0f}px;top:{y1 + 42 * k:.0f}px;'
            f'transform:translateX(-50%);font-weight:800;font-size:{13 * k:.0f}px;'
            f'opacity:.5">{z["zi"]}</div>')
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:{56 * k:.0f}px;top:{56 * k:.0f}px;'
        f'width:{int(120 * k)}px" class="filet"></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;top:{78 * k:.0f}px">'
        f'<div class="eticheta">{ch.get("localitate") or _eticheta(a)}</div>'
        f'<div class="sub">Prognoză · 7 zile</div></div>'
        f'<div style="position:absolute;left:{x0 - 10 * k:.0f}px;top:{y1 + 4 * k:.0f}px;'
        f'width:{x1 - x0 + 10 * k:.0f}px;height:{2 * k:.0f}px;opacity:.25;background:{acc}"></div>'
        f'{"".join(cols)}'
        f'<div class="marca" style="left:{56 * k:.0f}px;bottom:{44 * k:.0f}px">izz.ro</div>'
        f'<div class="marca" style="right:{20 * k:.0f}px;bottom:{28 * k:.0f}px">'
        f'Sursa datelor: {ch.get("sursa") or "open-meteo.com"}</div>'
        f'<div class="grain"></div></div>'
    )


def _seed(a: dict) -> bytes:
    """Semintele de compozitie ale articolului `a` — sursa unica pentru raster si pentru
    arta desenata in pagina.

    UN SINGUR LOC, fiindca e o invarianta: `build_html` si `stil_inline` TREBUIE sa aleaga
    aceeasi paleta si acelasi sablon pentru acelasi articol, altfel og:image-ul arata altfel
    decat pagina pe care o anunta. Cu doua copii ale expresiei, invarianta tinea prin
    coincidenta (`tests/test_arta_inline.py` o verifica — dar un test prinde, nu previne).

    SHA-256, nu SHA-1, si nu din superstitie. Aici digestul nu apara nimic: din el ies un
    index de paleta si unul de sablon, deci o coliziune inseamna „doua stiri seamana", nu o
    semnatura falsificata. Prima incercare a fost tocmai asta, scrisa ca `# nosemgrep` cu
    justificarea alaturi — si a esuat MASURAT: semgrep chiar recunoaste suprimarea (SARIF:
    `suppressions: [{kind: inSource}]`, constatarea iese din numarul de blocking), dar
    pastreaza rezultatul in SARIF, iar GitHub ridica alerta oricum si botul o re-posteaza pe
    PR la fiecare atingere a liniei. Reparatia adevarata e in poarta care nu citeste
    `suppressions` — cale protejata (§10), deci nu a mea (IZZ-0316). Ce ramane sub controlul
    codului e algoritmul, iar aici nu costa nimic sa fie cel pe care nimeni nu-l discuta.

    Ce a costat schimbarea, ca sa nu se re-deschida: semintele noi remixeaza paletele si
    sabloanele, deci copertile `media/<aid>.c.jpg` desenate inainte nu se mai potrivesc cu
    arta din pagina. Tranzitoriu si autovindecator: fereastra og e de ~1.200 de articole
    (~2 zile), iar `tools/gen_images.py` prune-uieste copertile iesite din ea si le deseneaza
    din nou pe cele intrate. Dupa o rotatie completa a ferestrei, nimic nu mai difera.

    `art_id()` de mai jos ramane pe SHA-1 DELIBERAT: acolo digestul e NUMELE FISIERULUI din
    `media/`. Schimbat, ar redenumi peste 12.000 de fisiere comise si ar rupe fiecare imagine
    deja publicata. Alt uz, alt calcul — nu-l „repara" la pachet cu asta.
    """
    return hashlib.sha256((a.get("title") or "x").encode()).digest()


def build_html(a: dict, cover: bool = False, sablon: str | None = None) -> str:
    """HTML pentru imaginea articolului. cover=True -> 1200x630 (og); altfel 960x504 (banner).

    `sablon` forteaza o compozitie anume, dupa numele ei din `_NUME_TEMPLATE`. Exista pentru
    copertile de CATEGORIE (`tools/gen_images.py`), care n-au data publicarii: trei din cele
    patru compozitii isi construiesc jumatatea dreapta din cifra zilei, iar fara ea raman
    aproape goale -- exact critica „~80% spatiu alb" din reproiectarea 2026-09-06. `editorial`
    e singura care se inchide corect fara data. Pentru articole ramane seed-ul: acolo data
    exista intotdeauna, iar variatia e chiar scopul.
    """
    seed = _seed(a)
    acc, bg = _PALETE[seed[0] % len(_PALETE)]
    w, h = (COVER_W, COVER_H) if cover else (ART_W, ART_H)
    ch = a.get("event_chart") or {}
    if ch.get("tip") == "meteo" and ch.get("zile"):
        body = _t_meteo(a, ch, acc, bg, w / ART_W)
    elif ch.get("tip") == "cutremur" and ch.get("lat") is not None:
        body = _t_cutremur(a, ch, acc, bg, w / ART_W)
    elif sablon:
        body = _TEMPLATES[_NUME_TEMPLATE.index(sablon)](a, acc, bg, w / ART_W)
    # Silueta judetului sta SUB graficele de eveniment si SUB sablonul fortat: meteo si
    # cutremur spun ce s-a intamplat, harta spune doar unde, iar copertile de categorie
    # (`sablon`) n-au judet prin constructie. Peste rotatia generica trece insa, fiindca e
    # singurul strat ramas care spune ceva despre ARTICOL, nu despre rubrica.
    elif (a.get("category") or "") in _GEO_CALM:
        # local/judetean fara judet cunoscut primeste aceeasi compozitie calma, doar fara forma
        body = _t_harta(a, acc, bg, w / ART_W)
    else:
        body = _TEMPLATES[seed[4] % len(_TEMPLATES)](a, acc, bg, w / ART_W)
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{_base_css(w, h)}</style></head>"
            f"<body>{body}</body></html>")


def art_id(a: dict) -> str:
    """ID stabil (din URL/titlu) — numele imaginii comise, independent de slug-ul de render."""
    key = a.get("url") or a.get("original_link") or a.get("title") or ""
    return hashlib.sha1(key.encode()).hexdigest()[:16]


# ---- arta DESENATA IN PAGINA (Workers Free, 2026-09-09) --------------------
# Compozitiile de mai sus sunt tipografie si geometrie: fond plat, eticheta majuscula,
# filete aurii, cercuri, cifra zilei. Nimic figurativ, nimic fotografic. Un browser le
# deseneaza direct, vectorial, fara sa descarce 960x504 de pixeli — deci pe planul gratuit
# Cloudflare (20.000 de fisiere/versiune) nu mai are rost sa existe fisierul.
#
# Ce intoarce `stil_inline` NU e HTML: e DESCRIEREA compozitiei. Culorile si marimile stau
# in `static/styles.css` (§8: template-urile nu hardcodeaza culori), iar `templates/_art.html`
# le pune pe DOM. Semintele sunt aceleasi ca in `build_html`, deci un articol pastreaza exact
# compozitia si paleta pe care le avea ca raster. (`_NUME_TEMPLATE` sta langa `_TEMPLATES`.)
#
# Praguri WEB, calibrate 2026-10-01 pe metricile reale ale Playfair 800 (sonda
# notes/sonda_latime_etichete_2026-10-01.py): cel mai lat cuvant simplu al fiecarei
# trepte trebuie sa incapa pe un singur rand in coloana oricarei compozitii. Diverg de
# tabelele raster `_et_px` (8/13/18) INTENTIONAT: rasterul lasa cuvintele prea lungi sa
# depaseasca incet caseta (nu le taie niciodata), pe web insa `overflow-wrap: anywhere`
# taie prin cuvant („DÂMBOVIȚ / A”), deci pragurile web sunt mai stranse. Coeficientii
# per treapta si per compozitie stau in `static/styles.css`, langa `.art-label`.
_ET_TREPTE = (8, 11, 14)


def _treapta_eticheta(et: str) -> int:
    n = len((et or "").strip())
    for i, plafon in enumerate(_ET_TREPTE):
        if n <= plafon:
            return i
    return len(_ET_TREPTE)


def stil_inline(a: dict) -> dict:
    """Descrierea artei desenate in pagina pentru `a` (compozitie, paleta, texte, data, harta/portret)."""
    seed = _seed(a)
    et = _eticheta(a)
    # Local/judetean: forma si subtitlul urmeaza eticheta afisata (`_forma_loc`).
    geo_cat = (a.get("category") or "") in _GEO_CALM
    if geo_cat:
        cod, d, sub = _forma_loc(a)
        harta = _harta_inline(cod, d) if cod else None
    else:
        sub, harta = _subtitlu(a), None
    # Local/judetean: o singura compozitie calma, fara data (cerere proprietar 2026-10-17;
    # auditul din aceeasi zi, sect. 5.2 — ziua lunii repeta meta-ul, iar patru compozitii
    # alternate faceau din lista un colaj). `arc` e baza fiindca, fara sigiliu, ramane exact
    # eticheta + forma; calibrarea treptelor de eticheta se pastreaza.
    geo = geo_cat
    portret = None if (harta or geo) else _portret_card(a)
    res = {
        "tpl": "arc" if geo else _NUME_TEMPLATE[seed[4] % len(_NUME_TEMPLATE)],
        "pal": seed[0] % len(_PALETE),
        "eticheta": et,
        "sub": sub,
        "treapta": _treapta_eticheta(et),
        "data": None if geo else _data_copertei(a),
    }
    if geo:
        res["geo"] = True
    if harta:
        res["harta"] = harta
    elif portret:
        res["portret"] = portret
    return res


# Categoriile cu compozitia calma (`.art--geo`). Aceleasi doua ca la `_judet`: sunt stirile
# a caror imagine spune UNDE, nu ziua.
_GEO_CALM = frozenset({"local", "judetean"})
