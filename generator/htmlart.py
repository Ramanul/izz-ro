"""Agent grafic (HTML/CSS) — compune imaginea articolului din TIPOGRAFIE si GEOMETRIE,
in paleta site-ului. Randata ulterior cu headless Chromium (tools/gen_images.py). Aici doar
construim HTML-ul (pur, testabil, fara Chromium).

De ce HTML/CSS si nu Pillow: gradienturi netede, umbre, blend-modes, tipografie web ->
calitate de design peste ce poate desena Pillow. Chromium nu exista in build-ul Cloudflare,
deci randarea se face in GitHub Actions.

V2 — „CRONICA VIE" (2026-09-05). A treia iteratie: prima generation arata „ca de copii"
(pictograme scalate + culori aleatorii), a doua (2026-08-05) a reparat categoria dar a ramas
SARACA — dreptunghi bej cu o eticheta mica si mult spatiu mort, vazuta de proprietar ca
„placeholder neterminat". V2 pastreaza TOATE constrangerile din v1 (non-figurativ, paleta
derivata din tokenuri, diferentiere prin compozitie si valoare, nu nuanta, contract identic
de fisiere in media/) si schimba doar compozitia:

  1. TIPOGRAFIE MARE CA FORMA: eticheta devine element compozitional (90-130px, taiata de
     margine sau pe doua randuri), nu un citat discret. Marimea se calculeaza din lungimea
     textului (_fit_linii), ca „INTELIGENȚĂ ARTIFICIALĂ" sa nu revarse.
  2. STRUCTURA DE VALOARE PE TOT CANVASUL: campuri de puncte (halftone), arce concentric,
     banda verticala cu tipografie rotita — fondul nu mai e gol.
  3. VIGNETE + GRAIN ca strat comun, ca hartia sa aiba greutate.

Contractul de fisiere NU s-a schimbat (media/{aid}.jpg + .webp + .c.jpg), deci render.py si
bugetul de fisiere Pages raman neatinse. Variantele dark (fisier suplimentar per articol) au
fost evaluate si AMANATE: ar dubla imaginile per articol si sparge plafonul de fisiere;
orbitura pe tema inchisa se rezolva in CSS (styles.css, filtru pe img in dark).
"""
import base64
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

# Vigneta: intunecare usoara catre colturile opuse punctului focal (φ, φ/2). Da hartiei
# adancime fara sa introduca o culoare noua — e doar cerneala existenta, diluata.
_VIGNETE = ("radial-gradient(140% 120% at 61.8% 38.2%, rgba(0,0,0,0) 55%, rgba(0,0,0,.07) 100%)")

# Camp de puncte (halftone editorial): cercuri mici pe grila patrata. Doua straturi —
# accent si auriu — ca densitatea sa aiba doua valori, nu una.
def _dots(color: str, size: int, dot: float, opacity: float) -> str:
    return (f"background-image:radial-gradient(circle,{color} {dot}px,transparent {dot}px);"
            f"background-size:{size}px {size}px;opacity:{opacity}")


def _base_css(w: int, h: int) -> str:
    # Tipografia scaleaza cu latimea, ca bannerul (960) si coperta og (1200) sa arate la fel.
    k = w / ART_W
    return (
        "*{margin:0;padding:0;box-sizing:border-box}"
        f"@font-face{{font-family:PF;src:url(data:font/ttf;base64,{_font()})}}"
        f"html,body{{width:{w}px;height:{h}px;overflow:hidden}}"
        f".stage{{position:relative;width:{w}px;height:{h}px;overflow:hidden;font-family:PF}}"
        f".grain{{position:absolute;inset:0;background-image:{_GRAIN};opacity:.06;"
        "mix-blend-mode:multiply;pointer-events:none}"
        f".vig{{position:absolute;inset:0;background:{_VIGNETE};pointer-events:none}}"
        # Eticheta: UN singur tratament tipografic per fisier (invatamant 2026-08-05:
        # acelasi judet la doua marimi pe carduri alaturate). Marimea de baza e comuna;
        # template-urile gigant o cresc prin _fit_linii, nu prin CSS ad-hoc.
        f".eticheta{{font-weight:800;font-size:{30*k:.0f}px;letter-spacing:{5*k:.0f}px;"
        "text-transform:uppercase;line-height:1}"
        f".sub{{font-weight:800;font-size:{15*k:.0f}px;letter-spacing:{4*k:.0f}px;"
        "text-transform:uppercase;opacity:.55;margin-top:" + f"{14*k:.0f}px}}"
        f".filet{{height:{3*k:.0f}px;background:{GOLD};border:0}}"
        f".marca{{position:absolute;font-weight:800;font-size:{13*k:.0f}px;letter-spacing:"
        f"{3*k:.0f}px;text-transform:uppercase;opacity:.4}}"
    )


def _fit_linii(text: str, max_linie: int) -> tuple[int, list[str]]:
    """Imparte textul in randuri care incap la tipografie gigant si calculeaza marimea.

    Playfair 800 uppercase: latimea medie a unui glif ≈ 0.62 * fs (masurat pe mostre);
    marimea = latimea disponibila / (0.62 * cel mai lung rand), plafonata la 132px si la
    3 randuri. Determinist: acelasi text -> aceeasi compozitie, pe orice masina.
    """
    cuvinte = text.split()
    linii, curent = [], ""
    for c in cuvinte:
        proba = f"{curent} {c}".strip()
        if len(proba) <= max_linie or not curent:
            curent = proba
        else:
            linii.append(curent)
            curent = c
    if curent:
        linii.append(curent)
    if len(linii) > 3:  # etichete patologice: taiem, nu revarsam (regula Zero Zgomot)
        linii = linii[:3]
        linii[-1] = linii[-1][:max_linie].rstrip() + "…"
    cel_mai_lung = max(len(l) for l in linii) if linii else 1
    # Plafon pe INALTIME: blocul de tip nu are voie sa depaseasca ~42% din canvas, oricâte
    # randuri — altfel 3 randuri gigante revarsa sub subtitlu (vazut la mostre).
    fs = min(132, int(760 / (0.62 * max(cel_mai_lung, 4))),
             int(ART_H * 0.42 / max(len(linii), 1)))
    return fs, linii


def _t_presara(a, acc, bg, k):
    """„PRESĂRA" — eticheta gigant taiata de marginea dreapta, camp de puncte φ² jos."""
    fs, linii = _fit_linii(_eticheta(a), 16)
    tip = "".join(f"<div style=\"font-weight:800;font-size:{fs*k:.0f}px;letter-spacing:{-fs*0.01*k:.0f}px;"
                  f"line-height:.95;text-transform:uppercase\">{l}</div>" for l in linii)
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:{56*k:.0f}px;top:{56*k:.0f}px;width:{190*k:.0f}px" class="filet"></div>'
        f'<div style="position:absolute;left:{56*k:.0f}px;top:{int(ART_H*0.34)*k:.0f}px;'
        f'white-space:nowrap">{tip}</div>'
        f'<div class="sub" style="position:absolute;left:{58*k:.0f}px;top:{int(ART_H*0.34)*k + fs*len(linii)*0.95*k + 24*k:.0f}px">{_subtitlu(a)}</div>'
        f'<div style="position:absolute;right:{-30*k:.0f}px;bottom:{-40*k:.0f}px;'
        f'width:{int(ART_W/PHI/PHI)*k:.0f}px;height:{int(ART_H/PHI/PHI)*k:.0f}px;{_dots(acc, 13*k, 2.0*k, .34)}"></div>'
        f'<div style="position:absolute;right:{int(ART_W/PHI/PHI)*k - 20*k:.0f}px;bottom:{-40*k:.0f}px;'
        f'width:{int(ART_W/PHI/PHI)*k:.0f}px;height:{int(ART_H/PHI/PHI)*k:.0f}px;{_dots(GOLD, 13*k, 2.0*k, .28)}"></div>'
        f'<div class="marca" style="left:{56*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
        f'<div class="vig"></div><div class="grain"></div></div>'
    )


def _t_plenar(a, acc, bg, k):
    """„PLENAR" — fond de accent, tipografia ocupand latimea; contrastul maxim din set."""
    fs, linii = _fit_linii(_eticheta(a), 13)
    tip = "".join(f"<div style=\"font-weight:800;font-size:{fs*k:.0f}px;letter-spacing:{-fs*0.008*k:.0f}px;"
                  f"line-height:1.02;text-transform:uppercase\">{l}</div>" for l in linii)
    return (
        f'<div class="stage" style="background:{acc};color:{bg}">'
        f'<div style="position:absolute;inset:{18*k:.0f}px;border:{1*k:.0f}px solid {GOLD};opacity:.5"></div>'
        f'<div style="position:absolute;left:{64*k:.0f}px;top:50%;transform:translateY(-50%)">{tip}</div>'
        f'<div style="position:absolute;left:{64*k:.0f}px;bottom:{int(ART_H*0.18)*k:.0f}px;'
        f'width:{int(ART_W/PHI)*k - 64*k:.0f}px" class="filet"></div>'
        f'<div class="sub" style="position:absolute;left:{64*k:.0f}px;bottom:{int(ART_H*0.11)*k:.0f}px;'
        f'color:{bg};opacity:.7">{_subtitlu(a)}</div>'
        f'<div style="position:absolute;right:{-90*k:.0f}px;top:{-120*k:.0f}px;'
        f'width:{420*k:.0f}px;height:{420*k:.0f}px;border-radius:50%;border:{1.5*k:.0f}px solid {GOLD};opacity:.35"></div>'
        f'<div class="marca" style="right:{40*k:.0f}px;bottom:{34*k:.0f}px;color:{bg};opacity:.6">izz.ro</div>'
        f'<div class="vig"></div><div class="grain" style="opacity:.09;mix-blend-mode:screen"></div></div>'
    )


def _t_coloana(a, acc, bg, k):
    """„COLOANĂ" — banda verticala ingusta cu eticheta rotita + camp de puncte generos."""
    banda_w = int(ART_W / PHI / PHI / PHI)          # ~226px: banda de fails, nu jumatate de panza
    et = _eticheta(a)
    # Marimea rotitei e plafonata si de INALTIMEA canvasului: textul vertical trebuie sa
    # incapa intreg, nu sa fie taiat (fs <= ~90% din inaltime / lungime).
    fs_banda = min(38, max(18, int(banda_w / (0.72 * len(et)) * 1.3)),
                   int(ART_H * 0.9 / max(len(et) * 1.3, 1)))
    sub = _subtitlu(a)
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:0;top:0;bottom:0;width:{banda_w*k:.0f}px;background:{acc}"></div>'
        f'<div style="position:absolute;left:{banda_w*k:.0f}px;top:0;bottom:0;width:{3*k:.0f}px;background:{GOLD}"></div>'
        f'<div style="position:absolute;left:0;top:0;bottom:0;width:{banda_w*k:.0f}px;display:flex;'
        f'align-items:center;justify-content:center">'
        f'<div style="writing-mode:vertical-rl;transform:rotate(180deg);color:{bg};font-weight:800;'
        f'font-size:{fs_banda*k:.0f}px;letter-spacing:{fs_banda*0.22*k:.0f}px;'
        f'text-transform:uppercase;white-space:nowrap">{et}</div></div>'
        # camp de puncte pe hartie, in dreapta: dublu strat, accente la doua scari
        f'<div style="position:absolute;right:0;top:0;width:{int(ART_W - banda_w)*k:.0f}px;height:{int(ART_H*0.62)*k:.0f}px;'
        f'{_dots(acc, 22*k, 2.2*k, .22)}"></div>'
        f'<div style="position:absolute;right:0;top:0;width:{int((ART_W - banda_w)/PHI)*k:.0f}px;height:{int(ART_H*0.62)*k:.0f}px;'
        f'{_dots(GOLD, 12*k, 2.0*k, .42)}"></div>'
        + (f'<div style="position:absolute;left:{banda_w*k + 52*k:.0f}px;bottom:{int(ART_H*0.16)*k:.0f}px">'
           f'<div class="eticheta" style="font-size:{22*k:.0f}px">{sub}</div>'
           f'<div style="width:{120*k:.0f}px;margin-top:{18*k:.0f}px" class="filet"></div></div>'
           if sub else
           f'<div style="position:absolute;left:{banda_w*k + 52*k:.0f}px;bottom:{int(ART_H*0.16)*k:.0f}px">'
           f'<div style="width:{160*k:.0f}px" class="filet"></div></div>')
        + f'<div class="marca" style="right:{56*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
        f'<div class="vig"></div><div class="grain"></div></div>'
    )


def _t_arc(a, acc, bg, k):
    """„ARC" — trei inele concentric taiate de margine; tipografia sta in spațiul calm."""
    fs, linii = _fit_linii(_eticheta(a), 14)
    tip = "".join(f"<div style=\"font-weight:800;font-size:{fs*k:.0f}px;line-height:1;"
                  f"text-transform:uppercase;letter-spacing:{-fs*0.01*k:.0f}px\">{l}</div>" for l in linii)
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;right:{-230*k:.0f}px;top:50%;transform:translateY(-50%);'
        f'width:{660*k:.0f}px;height:{660*k:.0f}px;border-radius:50%;background:{acc};opacity:.12"></div>'
        f'<div style="position:absolute;right:{-170*k:.0f}px;top:50%;transform:translateY(-50%);'
        f'width:{520*k:.0f}px;height:{520*k:.0f}px;border-radius:50%;border:{2*k:.0f}px solid {GOLD};opacity:.55"></div>'
        f'<div style="position:absolute;right:{-100*k:.0f}px;top:50%;transform:translateY(-50%);'
        f'width:{380*k:.0f}px;height:{380*k:.0f}px;border-radius:50%;border:{1*k:.0f}px solid {acc};opacity:.3"></div>'
        f'<div style="position:absolute;left:{56*k:.0f}px;top:{int(ART_H*0.30)*k:.0f}px;max-width:{int(ART_W*0.52)*k:.0f}px">{tip}</div>'
        f'<div style="position:absolute;left:{56*k:.0f}px;top:{56*k:.0f}px;width:{160*k:.0f}px" class="filet"></div>'
        f'<div class="sub" style="position:absolute;left:{58*k:.0f}px;top:{int(ART_H*0.30)*k + fs*len(linii)*k + 18*k:.0f}px">{_subtitlu(a)}</div>'
        f'<div class="marca" style="left:{56*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
        f'<div class="vig"></div><div class="grain"></div></div>'
    )


def _t_retea(a, acc, bg, k):
    """„REȚEA" — camp de puncte pe tot canvasul, doua densitati; eticheta in bloc solid."""
    fs, linii = _fit_linii(_eticheta(a), 14)
    tip = "".join(f"<div style=\"font-weight:800;font-size:{fs*0.55*k:.0f}px;letter-spacing:{3*k:.0f}px;"
                  f"line-height:1.18;text-transform:uppercase\">{l}</div>" for l in linii)
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        # strat de baza, rar si discret, peste tot
        f'<div style="position:absolute;inset:0;{_dots(acc, 24*k, 2.2*k, .20)}"></div>'
        # strat de aur, gros, decalat — da densitate zonei din dreapta-sus
        f'<div style="position:absolute;right:0;top:0;width:{int(ART_W/PHI)*k:.0f}px;height:{int(ART_H/PHI)*k:.0f}px;'
        f'{_dots(GOLD, 14*k, 2.4*k, .5)}"></div>'
        f'<div style="position:absolute;left:0;bottom:0;background:{acc};color:{bg};'
        f'padding:{42*k:.0f}px {52*k:.0f}px {46*k:.0f}px;'
        f'max-width:{int(ART_W*0.66)*k:.0f}px">{tip}</div>'
        + (f'<div class="sub" style="position:absolute;left:{52*k:.0f}px;bottom:{16*k:.0f}px;color:{bg};opacity:.75">{_subtitlu(a)}</div>'
           if _subtitlu(a) else "")
        + f'<div class="marca" style="right:{44*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
        f'<div class="vig"></div><div class="grain"></div></div>'
    )


_TEMPLATES = [_t_presara, _t_plenar, _t_coloana, _t_arc, _t_retea]


def build_html(a: dict, cover: bool = False) -> str:
    """HTML pentru imaginea articolului. cover=True -> 1200x630 (og); altfel 960x504 (banner)."""
    seed = hashlib.sha1((a.get("title") or "x").encode()).digest()
    acc, bg = _PALETE[seed[0] % len(_PALETE)]
    w, h = (COVER_W, COVER_H) if cover else (ART_W, ART_H)
    body = _TEMPLATES[seed[4] % len(_TEMPLATES)](a, acc, bg, w / ART_W)
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{_base_css(w, h)}</style></head>"
            f"<body>{body}</body></html>")


def art_id(a: dict) -> str:
    """ID stabil (din URL/titlu) — numele imaginii comise, independent de slug-ul de render."""
    key = a.get("url") or a.get("original_link") or a.get("title") or ""
    return hashlib.sha1(key.encode()).hexdigest()[:16]
