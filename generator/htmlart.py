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
import os

from . import geo

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
GOLD_INCHIS = "#8b6918"  # --gold-strong din static/styles.css (§8)


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
    sus = f"{dt['wk']} {dt['zi_n']} {dt['luna']} {dt['an']}" if dt else "izz.ro"
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
               f'<div style="font-weight:800;font-size:{96 * k:.0f}px;color:{GOLD_INCHIS}">{dt["zi"]}</div>'
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


_TEMPLATES = [_t_editorial, _t_inversat, _t_banda, _t_arc]


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


def build_html(a: dict, cover: bool = False) -> str:
    """HTML pentru imaginea articolului. cover=True -> 1200x630 (og); altfel 960x504 (banner)."""
    seed = hashlib.sha1((a.get("title") or "x").encode()).digest()
    acc, bg = _PALETE[seed[0] % len(_PALETE)]
    w, h = (COVER_W, COVER_H) if cover else (ART_W, ART_H)
    ch = a.get("event_chart") or {}
    if ch.get("tip") == "meteo" and ch.get("zile"):
        body = _t_meteo(a, ch, acc, bg, w / ART_W)
    else:
        body = _TEMPLATES[seed[4] % len(_TEMPLATES)](a, acc, bg, w / ART_W)
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{_base_css(w, h)}</style></head>"
            f"<body>{body}</body></html>")


def art_id(a: dict) -> str:
    """ID stabil (din URL/titlu) — numele imaginii comise, independent de slug-ul de render."""
    key = a.get("url") or a.get("original_link") or a.get("title") or ""
    return hashlib.sha1(key.encode()).hexdigest()[:16]
