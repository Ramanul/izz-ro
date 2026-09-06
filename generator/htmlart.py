"""Agent grafic (HTML/CSS) — compune imaginea articolului din TIPOGRAFIE si GEOMETRIE,
in paleta site-ului. Randata ulterior cu headless Chromium (tools/gen_images.py). Aici doar
construim HTML-ul (pur, testabil, fara Chromium).

De ce HTML/CSS si nu Pillow: gradienturi netede, umbre, blend-modes, tipografie web ->
calitate de design peste ce poate desena Pillow. Chromium nu exista in build-ul Cloudflare,
deci randarea se face in GitHub Actions.

ISTORICUL celei de-a treia iteratii: prima generatie arata „ca de copii" (pictograme
scalate + culori aleatorii), a doua (2026-08-05) a reparat categoria dar a ramas saraca
(spatiu mort, „placeholder neterminat"), iar #295 (2026-09-06, „coperte clasice V1") a
adus DATA ca element de design si a umplut canvasul. V2 „CRONICA VIE" (aceeasi zi,
ramura de redesign vizual) pastreaza TOATE constrangerile (non-figurativ, paleta din
tokenuri, diferentiere prin compozitie si valoare, contract identic de fisiere) si
COMBINA cele doua compoziitii: structurile de valoare (halftone, arce, coloana verticala,
tipografie gigant cu fit pe lungime+inaltime) plus elementele de data si randul de
subtitlu cu filet din #295. `_data_copertei` si `_et_px` sunt pastrate cu semantica fixa
— sunt pin-uite de tests/test_htmlart_redesign.py.
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


# Data publicarii ca ELEMENT DE DESIGN (venita din #295): fapt stabil din stare, nu
# provenienta (sect. 7 nu interzice data; numele surselor raman pe card, nu pe imagine).
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
    """Marimea etichetei treptata pe lungime: numele lungi nu se taie din cadru.
    Pin-uita de tests/test_htmlart_redesign.py — nu-i schimba semantica."""
    n = len((et or "").strip())
    for plafon, px in trepte:
        if n <= plafon:
            return int(px * k)
    return int(trepte[-1][1] * k)


def _fit_linii(text: str, max_linie: int) -> tuple[int, list[str]]:
    """Imparte textul in randuri care incap la tipografie gigant si calculeaza marimea.

    Playfair 800 uppercase: latimea medie a unui glif ≈ 0.62 * fs; marimea = latimea
    disponibila / (0.62 * cel mai lung rand), plafonata si pe INALTIME (~42% din canvas,
    oricate randuri). Determinist: acelasi text -> aceeasi compozitie, pe orice masina.
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
    fs = min(132, int(760 / (0.62 * max(cel_mai_lung, 4))),
             int(ART_H * 0.42 / max(len(linii), 1)))
    return fs, linii


def _rand_sub(sb: str, k: float) -> str:
    """Randul de subtitlu cu filet auriu inline (venit din #295); gol cand subtitlul e gol."""
    if not sb:
        return ""
    return (f'<div style="margin-top:{18 * k:.0f}px;display:flex;align-items:center;gap:{14 * k:.0f}px">'
            f'<span style="width:{64 * k:.0f}px;height:{3 * k:.0f}px;background:{GOLD};'
            f'display:inline-block"></span>'
            f'<span class="sub" style="margin-top:0">{sb}</span></div>')


_GRAIN = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E"
          "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E"
          "%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")")

# Vigneta: intunecare usoara catre colturile opuse punctului focal (φ, φ/2). Da hartiei
# adancime fara sa introduca o culoare noua — e doar cerneala existenta, diluata.
_VIGNETE = ("radial-gradient(140% 120% at 61.8% 38.2%, rgba(0,0,0,0) 55%, rgba(0,0,0,.07) 100%)")


def _dots(color: str, size: int, dot: float, opacity: float) -> str:
    """Camp de puncte (halftone editorial): cercuri mici pe grila patrata."""
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
        # Eticheta: UN singur tratament tipografic per fisier (invatamant 2026-08-05).
        # Marimea de baza e comuna; template-urile o cresc prin _fit_linii/_et_px inline.
        f".eticheta{{font-weight:800;font-size:{30*k:.0f}px;letter-spacing:{5*k:.0f}px;"
        "text-transform:uppercase;line-height:1}"
        f".sub{{font-weight:800;font-size:{15*k:.0f}px;letter-spacing:{4*k:.0f}px;"
        "text-transform:uppercase;opacity:.55;margin-top:" + f"{14*k:.0f}px}}"
        f".filet{{height:{3*k:.0f}px;background:{GOLD};border:0}}"
        f".marca{{position:absolute;font-weight:800;font-size:{13*k:.0f}px;letter-spacing:"
        f"{3*k:.0f}px;text-transform:uppercase;opacity:.4}}"
    )


def _masthead(k: float, sus: str) -> str:
    """Randul de masthead de sus (venit din #295): izz.ro stanga, data dreapta, filet auriu."""
    return (
        f'<div style="position:absolute;left:{56 * k:.0f}px;right:{56 * k:.0f}px;top:{30 * k:.0f}px;'
        f'display:flex;justify-content:space-between;align-items:baseline">'
        f'<span class="marca" style="position:static;font-size:{15 * k:.0f}px;opacity:.65">izz.ro</span>'
        f'<span class="marca" style="position:static;font-size:{13 * k:.0f}px">{sus}</span></div>'
        f'<div style="position:absolute;left:{56 * k:.0f}px;right:{56 * k:.0f}px;top:{68 * k:.0f}px;'
        f'height:{3 * k:.0f}px;background:{GOLD}"></div>'
    )


def _t_presara(a, acc, bg, k):
    """„PRESĂRA" — tipografie gigant asezata pe verticala de aur, camp de puncte jos."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    fs, linii = _fit_linii(et, 16)
    tip = "".join(f"<div style=\"font-weight:800;font-size:{fs*k:.0f}px;letter-spacing:{-fs*0.01*k:.0f}px;"
                  f"line-height:.95;text-transform:uppercase\">{l}</div>" for l in linii)
    sus = f"{dt['wk']} {dt['zi_n']} {dt['luna']} {dt['an']}" if dt else "izz.ro"
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'{_masthead(k, sus)}'
        f'<div class="eticheta" style="position:absolute;left:{56*k:.0f}px;top:{int(ART_H*0.36)*k:.0f}px;'
        f'font-size:{fs*k:.0f}px;letter-spacing:{-fs*0.01*k:.0f}px;line-height:.95;white-space:nowrap">{tip}</div>'
        f'<div style="position:absolute;right:{-30*k:.0f}px;bottom:{-40*k:.0f}px;'
        f'width:{int(ART_W/PHI/PHI)*k:.0f}px;height:{int(ART_H/PHI/PHI)*k:.0f}px;{_dots(acc, 13*k, 2.0*k, .34)}"></div>'
        f'<div style="position:absolute;right:{int(ART_W/PHI/PHI)*k - 20*k:.0f}px;bottom:{-40*k:.0f}px;'
        f'width:{int(ART_W/PHI/PHI)*k:.0f}px;height:{int(ART_H/PHI/PHI)*k:.0f}px;{_dots(GOLD, 13*k, 2.0*k, .28)}"></div>'
        f'{_rand_sub(sb, k).replace("margin-top:", f"position:absolute;left:{58*k:.0f}px;top:{int(ART_H*0.36)*k + fs*len(linii)*0.95*k + 26*k:.0f}px;margin-top:", 1)}'
        f'<div class="marca" style="left:{56*k:.0f}px;bottom:{44*k:.0f}px">Portalul știrilor tale</div>'
        f'<div class="vig"></div><div class="grain"></div></div>'
    )


def _t_plenar(a, acc, bg, k):
    """„PLENAR" — fond de accent, tipografia ocupand latimea, cifra zilei uriasa in aur."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    fs, linii = _fit_linii(et, 13)
    tip = "".join(f"<div style=\"font-weight:800;font-size:{fs*k:.0f}px;letter-spacing:{-fs*0.008*k:.0f}px;"
                  f"line-height:1.02;text-transform:uppercase\">{l}</div>" for l in linii)
    numeral_culoare = bg if acc.lower() == GOLD_INCHIS else GOLD
    # pe perechea aurie (acc GOLD_INCHIS), o cifra GOLD dispare in fond — vazut la mostre
    numeral = (f'<div style="position:absolute;right:{56 * k:.0f}px;bottom:{34 * k:.0f}px;'
               f'text-align:right;line-height:1">'
               f'<div class="marca" style="position:static;font-size:{16 * k:.0f}px;opacity:.6">{dt["wk"]}</div>'
               f'<div style="font-weight:800;font-size:{150 * k:.0f}px;color:{numeral_culoare};line-height:.92">{dt["zi"]}</div>'
               f'<div style="font-weight:800;font-size:{18 * k:.0f}px;letter-spacing:{6 * k:.0f}px;'
               f'text-transform:uppercase;opacity:.85">{dt["luna"]} {dt["an"]}</div></div>') if dt else ""
    return (
        f'<div class="stage" style="background:{acc};color:{bg}">'
        f'<div style="position:absolute;inset:{18*k:.0f}px;border:{1*k:.0f}px solid {GOLD};opacity:.5"></div>'
        f'<div class="eticheta" style="position:absolute;left:{64*k:.0f}px;top:{56*k:.0f}px;'
        f'font-size:{fs*k:.0f}px;letter-spacing:{-fs*0.008*k:.0f}px;line-height:1.02">{tip}</div>'
        f'<div style="position:absolute;left:{64*k:.0f}px;bottom:{int(ART_H*0.18)*k:.0f}px;'
        f'width:{int(ART_W*0.45)*k:.0f}px" class="filet"></div>'
        f'<div style="position:absolute;left:{-90*k:.0f}px;top:{-120*k:.0f}px;'
        f'width:{420*k:.0f}px;height:{420*k:.0f}px;border-radius:50%;border:{1.5*k:.0f}px solid {GOLD};opacity:.35"></div>'
        f'{_rand_sub(sb, k).replace("margin-top:", f"position:absolute;left:{64*k:.0f}px;top:{56*k + fs*len(linii)*1.02*k + 20*k:.0f}px;margin-top:", 1)}'
        f'{numeral}'
        f'<div class="marca" style="left:{64*k:.0f}px;bottom:{int(ART_H*0.10)*k:.0f}px;color:{bg};opacity:.6">izz.ro · Portalul știrilor tale</div>'
        f'<div class="vig"></div><div class="grain" style="opacity:.09;mix-blend-mode:screen"></div></div>'
    )


def _t_coloana(a, acc, bg, k):
    """„COLOANĂ" — banda verticala cu eticheta rotita; pe hartie, data mare si puncte."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    banda_w = int(ART_W / PHI / PHI / PHI)          # ~226px: banda de fails, nu jumatate de panza
    fs_banda = min(38, max(18, int(banda_w / (0.72 * len(et)) * 1.3)),
                   int(ART_H * 0.9 / max(len(et) * 1.3, 1)))
    data_dr = (f'<div style="position:absolute;right:{64 * k:.0f}px;top:{56 * k:.0f}px;text-align:right">'
               f'<div style="font-weight:800;font-size:{72 * k:.0f}px;color:{GOLD_INCHIS};line-height:1">{dt["zi_n"]}</div>'
               f'<div class="sub" style="margin-top:{8 * k:.0f}px;font-size:{17 * k:.0f}px">{dt["luna"]} {dt["an"]}</div>'
               f'<div style="width:{64 * k:.0f}px;height:{3 * k:.0f}px;background:{GOLD};'
               f'margin:{14 * k:.0f}px 0 0 auto"></div></div>') if dt else ""
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;left:0;top:0;bottom:0;width:{banda_w*k:.0f}px;background:{acc}"></div>'
        f'<div style="position:absolute;left:{banda_w*k:.0f}px;top:0;bottom:0;width:{3*k:.0f}px;background:{GOLD}"></div>'
        f'<div style="position:absolute;left:0;top:0;bottom:0;width:{banda_w*k:.0f}px;display:flex;'
        f'align-items:center;justify-content:center">'
        f'<div class="eticheta" style="writing-mode:vertical-rl;transform:rotate(180deg);color:{bg};'
        f'font-size:{fs_banda*k:.0f}px;letter-spacing:{fs_banda*0.22*k:.0f}px;'
        f'text-transform:uppercase;white-space:nowrap">{et}</div></div>'
        f'<div style="position:absolute;right:0;top:0;width:{int(ART_W - banda_w)*k:.0f}px;height:{int(ART_H*0.62)*k:.0f}px;'
        f'{_dots(acc, 22*k, 2.2*k, .22)}"></div>'
        f'<div style="position:absolute;right:0;top:0;width:{int((ART_W - banda_w)/PHI)*k:.0f}px;height:{int(ART_H*0.62)*k:.0f}px;'
        f'{_dots(GOLD, 12*k, 2.0*k, .42)}"></div>'
        f'{data_dr}'
        + (f'<div style="position:absolute;left:{banda_w*k + 52*k:.0f}px;bottom:{int(ART_H*0.16)*k:.0f}px">'
           f'<div class="eticheta" style="font-size:{22*k:.0f}px">{sb}</div>'
           f'<div style="width:{120*k:.0f}px;margin-top:{18*k:.0f}px" class="filet"></div></div>'
           if sb else
           f'<div style="position:absolute;left:{banda_w*k + 52*k:.0f}px;bottom:{int(ART_H*0.16)*k:.0f}px">'
           f'<div style="width:{160*k:.0f}px" class="filet"></div></div>')
        + f'<div class="marca" style="right:{56*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
        f'<div class="vig"></div><div class="grain"></div></div>'
    )


def _t_arc(a, acc, bg, k):
    """„ARC" — sigiliul din #295 (cerc dublu auriu cu cifra zilei) + tipografie gigant."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    fs, linii = _fit_linii(et, 14)
    tip = "".join(f"<div style=\"font-weight:800;font-size:{fs*k:.0f}px;line-height:1;"
                  f"text-transform:uppercase;letter-spacing:{-fs*0.01*k:.0f}px\">{l}</div>" for l in linii)
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
        f'<div style="position:absolute;left:{56*k:.0f}px;top:{56*k:.0f}px;width:{160*k:.0f}px" class="filet"></div>'
        f'<div class="eticheta" style="position:absolute;left:{56*k:.0f}px;top:{int(ART_H*0.30)*k:.0f}px;'
        f'max-width:{int(ART_W*0.48)*k:.0f}px;font-size:{fs*k:.0f}px;letter-spacing:{-fs*0.01*k:.0f}px;line-height:1">{tip}</div>'
        f'<div style="position:absolute;left:{540 * k:.0f}px;top:{cy}px;width:{cx - r - int(540 * k)}px;'
        f'height:{1 * k:.0f}px;background:{acc};opacity:.2"></div>'
        f'<div style="position:absolute;left:{cx + r - int(7 * k)}px;top:{cy - int(7 * k)}px;'
        f'width:{14 * k:.0f}px;height:{14 * k:.0f}px;border-radius:50%;background:{GOLD}"></div>{sigiliu}'
        f'{_rand_sub(sb, k).replace("margin-top:", f"position:absolute;left:{58*k:.0f}px;top:{int(ART_H*0.30)*k + fs*len(linii)*k + 20*k:.0f}px;margin-top:", 1)}'
        f'<div class="marca" style="left:{56*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
        f'<div class="vig"></div><div class="grain"></div></div>'
    )


def _t_retea(a, acc, bg, k):
    """„REȚEA" — camp de puncte pe tot canvasul, doua densitati; eticheta in bloc solid."""
    et, sb = _eticheta(a), _subtitlu(a)
    dt = _data_copertei(a)
    fs, linii = _fit_linii(et, 14)
    tip = "".join(f"<div style=\"font-weight:800;font-size:{fs*0.55*k:.0f}px;letter-spacing:{3*k:.0f}px;"
                  f"line-height:1.18;text-transform:uppercase\">{l}</div>" for l in linii)
    data_dr = (f'<div style="position:absolute;right:{0 * k:.0f}px;top:{0 * k:.0f}px;text-align:right;'
               f'background:{bg};padding:{26 * k:.0f}px {44 * k:.0f}px {16 * k:.0f}px;line-height:1">'
               f'<div style="font-weight:800;font-size:{64 * k:.0f}px;color:{GOLD_INCHIS};line-height:.95">{dt["zi"]}</div>'
               f'<div class="sub" style="margin-top:{6 * k:.0f}px;font-size:{15 * k:.0f}px">{dt["luna"]}</div></div>') if dt else ""
    return (
        f'<div class="stage" style="background:{bg};color:{acc}">'
        f'<div style="position:absolute;inset:0;{_dots(acc, 24*k, 2.2*k, .20)}"></div>'
        f'<div style="position:absolute;right:0;top:0;width:{int(ART_W/PHI)*k:.0f}px;height:{int(ART_H/PHI)*k:.0f}px;'
        f'{_dots(GOLD, 14*k, 2.4*k, .5)}"></div>'
        f'{data_dr}'
        f'<div style="position:absolute;left:0;bottom:0;background:{acc};color:{bg};'
        f'padding:{42*k:.0f}px {52*k:.0f}px {46*k:.0f}px;'
        f'max-width:{int(ART_W*0.66)*k:.0f}px">'
        f'<div class="eticheta" style="font-size:{fs*0.55*k:.0f}px;letter-spacing:{3*k:.0f}px;line-height:1.18">{tip}</div></div>'
        + (f'<div class="sub" style="position:absolute;left:{52*k:.0f}px;bottom:{16*k:.0f}px;color:{bg};opacity:.75;margin-top:0">{sb}</div>'
           if sb else "")
        + f'<div class="marca" style="right:{44*k:.0f}px;bottom:{44*k:.0f}px">izz.ro</div>'
        f'<div class="vig"></div><div class="grain"></div></div>'
    )


def _t_meteo(a, ch, acc, bg, k):
    """Coperta din date: prognoza pe 7 zile pentru localitatea stirii (venita din #293).

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


_TEMPLATES = [_t_presara, _t_plenar, _t_coloana, _t_arc, _t_retea]


def build_html(a: dict, cover: bool = False) -> str:
    """HTML pentru imaginea articolului. cover=True -> 1200x630 (og); altfel 960x504 (banner).

    Stirile cu `event_chart` meteo atasat (eventdata.attach) primesc coperta cu grafic,
    nu compozitia generica — datele reale bat decorul.
    """
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
