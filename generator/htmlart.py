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
import hashlib
import json
import os
import re

from . import geo

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
    ("#8b6918", "#faf5e6"),   # --gold-strong pe --gold-wash
    ("#15171c", "#f6f7f9"),   # --ink pe --paper
    ("#3d4a3a", "#f1f4ee"),   # masliniu
    ("#4a3b32", "#f7f2ed"),   # pamant ars
    ("#2f3d4a", "#eef1f5"),   # ardezie
    ("#4a3244", "#f5f0f4"),   # prun
]
GOLD = "#c9a227"


def _font() -> str:
    global _FONT_B64
    if _FONT_B64 is None:
        p = os.path.join(_ASSETS, "PlayfairDisplay_800ExtraBold.ttf")
        _FONT_B64 = base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else ""
    return _FONT_B64


def _eticheta(a: dict) -> str:
    """Textul etichetei: locul la stirile de loc, altfel categoria (vezi geo.eticheta_copertei)."""
    return geo.eticheta_copertei(a) or (a.get("category") or "").strip() or "stiri"


def _subtitlu(a: dict) -> str:
    """A doua linie, discreta. Goala cand ar repeta eticheta (categorie == judet afisat)."""
    cat = (a.get("category") or "").strip()
    if not cat or cat.lower() == _eticheta(a).strip().lower():
        return ""
    return cat


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
    """Hartie, filet auriu, tipografie asezata pe verticala de aur. Cel mai sobru."""
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:{56*k:.0f}px;top:{56*k:.0f}px;'
        f'width:{int((ART_W-112)/PHI*k)}px" class="filet"></div>'
        f'<div style="position:absolute;left:{56*k:.0f}px;top:{int(ART_H/PHI*k)}px;'
        f'transform:translateY(-50%)">'
        f'<div class="eticheta">{_eticheta(a)}</div>'
        f'<div class="sub">{_subtitlu(a)}</div></div>'
        f'<div style="position:absolute;right:{-120*k:.0f}px;bottom:{-160*k:.0f}px;'
        f'width:{440*k:.0f}px;height:{440*k:.0f}px;border-radius:50%;'
        f'border:{2*k:.0f}px solid {acc};opacity:.10"></div>'
        f'<div class="marca" style="left:{56*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
        f'<div class="grain"></div></div>'
    )


def _t_inversat(a, acc, bg, k):
    """Fundal de accent, tipografie deschisa. Contrastul cel mai puternic din set."""
    return (
        f'<div class="stage" style="background:{acc};color:{bg}">'
        f'<div style="position:absolute;inset:{18*k:.0f}px;border:{1*k:.0f}px solid {GOLD};'
        f'opacity:.45"></div>'
        f'<div style="position:absolute;left:{64*k:.0f}px;top:50%;transform:translateY(-50%)">'
        f'<div class="eticheta">{_eticheta(a)}</div>'
        f'<div style="width:{int(190*k)}px;margin-top:{20*k:.0f}px" class="filet"></div>'
        f'<div class="sub">{_subtitlu(a)}</div></div>'
        f'<div style="position:absolute;right:{-90*k:.0f}px;top:50%;transform:translateY(-50%) '
        f'rotate(45deg);width:{380*k:.0f}px;height:{380*k:.0f}px;border:{1*k:.0f}px solid {bg};'
        f'opacity:.14"></div>'
        f'<div class="marca" style="right:{40*k:.0f}px;bottom:{34*k:.0f}px">izz.ro</div>'
        f'<div class="grain"></div></div>'
    )


def _t_banda(a, acc, bg, k):
    """Banda de accent taiata la φ; tipografia sta pe hartie, langa ea."""
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:0;top:0;bottom:0;width:{int(ART_W/PHI/PHI*k)}px;'
        f'background:{acc}"></div>'
        f'<div style="position:absolute;left:{int(ART_W/PHI/PHI*k)}px;top:0;bottom:0;'
        f'width:{3*k:.0f}px;background:{GOLD}"></div>'
        f'<div style="position:absolute;left:{int(ART_W/PHI/PHI*k)+int(52*k)}px;top:50%;'
        f'transform:translateY(-50%)">'
        f'<div class="eticheta">{_eticheta(a)}</div>'
        f'<div class="sub">{_subtitlu(a)}</div></div>'
        f'<div style="position:absolute;left:{34*k:.0f}px;bottom:{34*k:.0f}px;color:{bg};'
        f'font-weight:800;font-size:{13*k:.0f}px;letter-spacing:{3*k:.0f}px;'
        f'text-transform:uppercase;opacity:.55">izz.ro</div>'
        f'<div class="grain"></div></div>'
    )


def _t_arc(a, acc, bg, k):
    """Arc mare de accent taiat de margine — singura forma din set, geometrica, nu figurativa."""
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;right:{-200*k:.0f}px;top:50%;transform:translateY(-50%);'
        f'width:{620*k:.0f}px;height:{620*k:.0f}px;border-radius:50%;background:{acc};'
        f'opacity:.09"></div>'
        f'<div style="position:absolute;right:{-150*k:.0f}px;top:50%;transform:translateY(-50%);'
        f'width:{480*k:.0f}px;height:{480*k:.0f}px;border-radius:50%;'
        f'border:{2*k:.0f}px solid {GOLD};opacity:.5"></div>'
        f'<div style="position:absolute;left:{56*k:.0f}px;top:{56*k:.0f}px">'
        f'<div style="width:{int(120*k)}px;margin-bottom:{22*k:.0f}px" class="filet"></div>'
        f'<div class="eticheta">{_eticheta(a)}</div>'
        f'<div class="sub">{_subtitlu(a)}</div></div>'
        f'<div class="marca" style="left:{56*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
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
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


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
            f'stroke-opacity=".5" stroke-width="{2.2 / s:.2f}" stroke-linejoin="round"/>'
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
    """Silueta reala a judetului, ancorata dreapta si taiata de margine; tipografia pe verticala
    de aur. Se alege in locul rotatiei de patru doar cand judetul e cunoscut (vezi `_judet`)."""
    cod = _judet(a)
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;right:{44 * k:.0f}px;top:50%;'
        f'transform:translateY(-50%);line-height:0">'
        f'{_silueta(cod, 360 * k, 364 * k, acc, 0.15)}</div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;top:{56 * k:.0f}px;'
        f'width:{int((ART_W - 112) / PHI * k)}px" class="filet"></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;top:{int(ART_H / PHI * k)}px;'
        f'transform:translateY(-50%)">'
        f'<div class="eticheta">{_eticheta(a)}</div>'
        f'<div class="sub">{_sub_harta(a, cod)}</div></div>'
        f'<div class="marca" style="left:{56 * k:.0f}px;bottom:{44 * k:.0f}px">izz.ro</div>'
        f'<div class="grain"></div></div>'
    )


_TEMPLATES = [_t_editorial, _t_inversat, _t_banda, _t_arc]


def build_html(a: dict, cover: bool = False) -> str:
    """HTML pentru imaginea articolului. cover=True -> 1200x630 (og); altfel 960x504 (banner)."""
    seed = hashlib.sha1((a.get("title") or "x").encode()).digest()
    acc, bg = _PALETE[seed[0] % len(_PALETE)]
    w, h = (COVER_W, COVER_H) if cover else (ART_W, ART_H)
    # Harta bate rotatia cand judetul e cunoscut: e singurul strat din set care spune ceva
    # despre ARTICOL, nu despre rubrica. Paleta ramane derivata din titlu, deci doua stiri din
    # acelasi judet nu ies identice.
    sablon = _t_harta if _judet(a) else _TEMPLATES[seed[4] % len(_TEMPLATES)]
    body = sablon(a, acc, bg, w / ART_W)
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{_base_css(w, h)}</style></head>"
            f"<body>{body}</body></html>")


def art_id(a: dict) -> str:
    """ID stabil (din URL/titlu) — numele imaginii comise, independent de slug-ul de render."""
    key = a.get("url") or a.get("original_link") or a.get("title") or ""
    return hashlib.sha1(key.encode()).hexdigest()[:16]
