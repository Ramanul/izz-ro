"""Coperta generativa de fallback pentru `og:image` (1200x630, Pillow).

Acelasi limbaj vizual ca `htmlart.py` (cele 6 palete editoriale sobre, Newsreader 700,
rigla aurie `#c9a227`, compozitie tipografica de ziar). `render.py` prefera coperta comisa in
`media/*.c.jpg` si cade aici pentru articolele din `OG_COVER_MAX_ARTICLES` fara fisier comis,
precum si pentru copertile generice de categorie (`media/og/<cat>.jpg`).

Deseneaza direct la `1200x630` (fara supersampling `2400x1260` si fara `GaussianBlur(220)`),
eliminand stilul vechi cu siluete (`_crowd`), pictograme gigant si culori HSL curcubeu
(`IZZ-0404`) si reducand timpul de randare al celor 1200 de coperți de la ~280s la ~4s.
"""
import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

from . import htmlart

W, H = 1200, 630
# Paleta de baza a copertei = tokenii site-ului (rebranding 2026-11-07): arama mată, tus
# cald, tus secundar. Aurul vechi (201,162,39) aparea portocaliu pe hartie.
GOLD = (168, 130, 58)      # #a8823a — --brass (doar decor: rama, filete)
INK = (20, 22, 26)         # #14161a — --ink
INK2 = (74, 81, 92)        # #4a515c — --ink-2

_ROOT = os.path.dirname(os.path.dirname(__file__))
_FONT_PATHS = {
    "display": [
        os.path.join(_ROOT, "generator/assets/Newsreader_700Bold.ttf"),
        os.path.join(_ROOT, "static/fonts/Newsreader-700.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ],
    # Etichetele mici (categorie, data, cod) sunt SANS, ca in interfata site-ului.
    # JetBrains Mono a iesit din identitate in rebranding; fara un TTF real, Pillow cadea
    # pe fontul bitmap implicit si coperta arata ca un terminal.
    "mono": [
        os.path.join(_ROOT, "generator/assets/Inter_600SemiBold.ttf"),
        os.path.join(_ROOT, "static/fonts/Inter-SemiBold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}
_FONTS: dict = {}


def _hex_rgb(hx: str) -> tuple[int, int, int]:
    h = hx.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def _font(kind: str, size: int):
    key = (kind, size)
    if key not in _FONTS:
        f = None
        for p in _FONT_PATHS.get(kind, ()):
            if os.path.exists(p):
                try:
                    f = ImageFont.truetype(p, size)
                    break
                except Exception:
                    pass
        _FONTS[key] = f or ImageFont.load_default()
    return _FONTS[key]


def _wrap(d, text: str, font, maxw: int, max_lines: int = 4) -> list[str]:
    words, lines, cur = (text or "").split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(",;:") + "…"
    return lines or [""]


def _draw_cover(a: dict):
    seed = htmlart._seed(a)
    acc_hex, bg_hex = htmlart._PALETE[seed[0] % len(htmlart._PALETE)]
    acc = _hex_rgb(acc_hex)
    bg = _hex_rgb(bg_hex)
    dark = _lerp(acc, (17, 17, 17), 0.45)
    layout = htmlart._NUME_TEMPLATE[seed[4] % len(htmlart._NUME_TEMPLATE)]

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    # Geometrie editoriala discreta, aliniata cu cele 5 layouturi din htmlart.py
    if layout == "diagonal":
        d.polygon([(int(W * 0.56), 0), (W, 0), (W, H), (int(W * 0.38), H)],
                  fill=_lerp(bg, acc, 0.14))
        d.polygon([(int(W * 0.72), 0), (W, 0), (W, H), (int(W * 0.54), H)],
                  fill=_lerp(bg, dark, 0.22))
        d.line([(int(W * 0.56), 0), (int(W * 0.38), H)], fill=GOLD, width=3)
    elif layout == "horizon":
        y_split = int(H * 0.74)
        d.rectangle([0, y_split, W, H], fill=dark)
        d.line([(0, y_split), (W, y_split)], fill=GOLD, width=4)
    elif layout == "column":
        x_col = int(W * 0.68)
        d.rectangle([x_col, 0, W, H], fill=_lerp(bg, acc, 0.16))
        d.line([(x_col, 44), (x_col, H - 44)], fill=GOLD, width=3)
    elif layout == "split":
        x_split = int(W * 0.66)
        d.rectangle([x_split, 0, W, H], fill=dark)
        d.line([(x_split, 0), (x_split, H)], fill=GOLD, width=4)
    else:  # arc
        d.ellipse([int(W * 0.52), -int(H * 0.28), int(W * 1.18), int(H * 0.92)],
                  fill=_lerp(bg, acc, 0.15), outline=GOLD, width=3)

    # Grila editoriala fina (asigura si marime >5 KB pentru smoke_live fara costul ImageChops)
    grid_col = _lerp(bg, acc, 0.07)
    for gx in range(48, W - 48, 48):
        d.line([(gx, 24), (gx, H - 24)], fill=grid_col, width=1)
    for gy in range(48, H - 48, 48):
        d.line([(24, gy), (W - 24, gy)], fill=grid_col, width=1)

    # Paspartu exterior (curata orice forma care depaseste rama de 24px) + rama aurie inset
    m = 24
    d.rectangle([0, 0, W, m - 1], fill=bg)
    d.rectangle([0, H - m, W, H], fill=bg)
    d.rectangle([0, 0, m - 1, H], fill=bg)
    d.rectangle([W - m, 0, W, H], fill=bg)
    d.rectangle([m, m, W - m - 1, H - m - 1], outline=GOLD, width=3)

    mono = _font("mono", 24)
    mono_s = _font("mono", 19)
    num_font = _font("display", 148)

    eyebrow = htmlart._eticheta(a)
    sub = htmlart._subtitlu(a)
    head_txt = f"{eyebrow.upper()}  ·  {sub.upper()}" if sub else eyebrow.upper()
    # Kicker-ul sta pe acelasi rand cu arcul, deci se scurteaza daca iese din zona sigura
    # („CV ȘI RECRUTARE · INTELIGENȚĂ ARTIFICIALĂ" ajungea in cerc).
    kicker_w = int(W * 0.50) - 64 - 16
    while head_txt and d.textlength(head_txt, font=mono) > kicker_w:
        head_txt = head_txt.rsplit(" ", 1)[0].rstrip(" ·")
    d.text((64, 54), head_txt, font=mono, fill=acc)   # nu aur inchis: iesea maroniu
    d.line([(64, 96), (380, 96)], fill=GOLD, width=3)

    # Data in dreapta (sau pe banda intunecata la split)
    dt = htmlart._data_copertei(a)
    if dt:
        zi, luna, an = dt["zi"], dt["luna"], dt["an"]
        num_col = _lerp(bg, GOLD, 0.45) if layout == "split" else _lerp(acc, bg, 0.35)
        meta_col = (228, 224, 214) if layout == "split" else INK2
        d.text((W - 72, 130), zi, font=num_font, fill=num_col, anchor="ra")
        d.text((W - 72, 310), f"{luna} {an}", font=mono_s, fill=meta_col, anchor="ra")

    # Titlu pe stanga. Latimea sigura depinde de layout: geometria din dreapta incepe la
    # 0,52-0,72 din latime, iar un titlu care o atinge se citeste ca text taiat (masurat
    # 2026-11-07: Newsreader e mai ingust, deci titlurile ajungeau pana in arc).
    # `_NUME_TEMPLATE` are 4 nume, dar desenul are 5 geometrii: editorial/inversat/banda
    # cad toate pe arcul din ramura `else`. Mapam pe GEOMETRIA desenata, altfel „banda"
    # primea toata latimea si titlul intra in cerc.
    geo = "arc" if layout in ("editorial", "inversat", "banda", "arc") else layout
    safe_right = {"diagonal": 0.54, "column": 0.66, "split": 0.64, "arc": 0.50}.get(geo, 0.80)
    max_title_w = int(W * safe_right) - 64 - 24
    # Titlurile lungi coboara in corp pana incap in 4 randuri, in loc sa fie taiate cu „…”.
    titlu = a.get("title") or "IZZ.ro"
    size, lines = 56, []
    while size >= 34:
        display = _font("display", size)
        lines = _wrap(d, titlu, display, max_title_w, max_lines=99)
        if len(lines) <= 4:
            break
        size -= 4
    lines = _wrap(d, titlu, _font("display", size), max_title_w, max_lines=4)
    display = _font("display", size)
    y = 126
    line_h = int(size * 1.28)
    for ln in lines:
        d.text((64, y), ln, font=display, fill=INK)
        y += line_h

    foot_col = (240, 236, 226) if layout == "horizon" else INK2
    code_col = GOLD if layout in ("horizon", "split") else acc
    d.text((64, H - 56), "IZZ.ro — Informația Zero Zgomot", font=mono_s, fill=foot_col, anchor="ls")
    d.text((W - 64, H - 56), f"Nº {seed.hex()[:6]}", font=mono_s, fill=code_col, anchor="rs")
    return img


def generate(a: dict, path: str) -> bool:
    """Coperta de SHARE (`og:image`, 1200x630, cu titlu) la `path`. False la orice problema."""
    if Image is None:
        return False
    try:
        img = _draw_cover(a)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path, "JPEG", quality=90)
        return True
    except Exception:
        return False
