"""Coperti generative per articol (og:image) — grafica proprie, zero surse externe.

Pictograme minimale desenate din primitive (nu AI, nu stock): alese determinist
din categoria + entitatile AI + cuvintele-cheie ale titlului. Unde nimic nu se
potriveste clar -> fallback abstract seeded din hash (niciodata o pictograma
fortata gresit — echivalentul vizual al regulii 'No mangled output').

Estetica: paleta si proportia de aur din static/styles.css (tokens replicati
aici pentru raster; schimbarile de paleta se oglindesc manual).
"""
import hashlib
import math
import os
import re

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                      # Pillow lipsa -> fara coperti, build-ul merge
    Image = None

PAPER2, INK, INK2 = "#ffffff", "#15171c", "#4d5562"
GOLD, GOLD_STRONG, GOLD_WASH, LINE = "#c9a227", "#8b6918", "#faf5e6", "#e4e7ec"
PHI = 1.618
W, H = 1200, 630                          # standardul og:image

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "C:/Windows/Fonts",
]


_FONT_CACHE: dict = {}


def _font(name_bold: bool, size: int):
    key = (name_bold, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    names = ["DejaVuSerif-Bold.ttf"] if name_bold else ["DejaVuSansMono.ttf", "consola.ttf"]
    f = None
    for d in _FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                f = ImageFont.truetype(p, size)
                break
        if f:
            break
    _FONT_CACHE[key] = f or ImageFont.load_default()
    return _FONT_CACHE[key]


_DIA = str.maketrans("ăâîșțĂÂÎȘȚşţŞŢ", "aaistAAISTstST")


def _norm(s: str) -> str:
    return (s or "").translate(_DIA).lower()


# ---- motive: functii(draw, cx, cy, r) ------------------------------------
def _m_persoana(d, cx, cy, r):
    d.ellipse([cx - r * .42, cy - r, cx + r * .42, cy - r * .16], outline=GOLD_STRONG, width=12)
    d.arc([cx - r, cy - r * .1, cx + r, cy + r * 1.6], 200, 340, fill=GOLD_STRONG, width=12)
    d.ellipse([cx + r * .18, cy - r * .86, cx + r * .34, cy - r * .7], fill=GOLD)


def _m_institutie(d, cx, cy, r):
    d.polygon([(cx - r, cy - r * .42), (cx + r, cy - r * .42), (cx, cy - r)],
              outline=GOLD_STRONG, width=12)
    for i in range(4):
        x = cx - r * .72 + i * (r * 1.44 / 3)
        d.line([x, cy - r * .3, x, cy + r * .62], fill=GOLD_STRONG, width=12)
    d.line([cx - r, cy + r * .78, cx + r, cy + r * .78], fill=GOLD, width=14)


def _m_fenomen(d, cx, cy, r):
    d.ellipse([cx - r * .5, cy - r * .5, cx + r * .5, cy + r * .5], outline=GOLD, width=14)
    for i in range(8):
        a = i * math.pi / 4
        l = r * (.75 if i % 2 else .95)
        d.line([cx + math.cos(a) * r * .62, cy + math.sin(a) * r * .62,
                cx + math.cos(a) * l, cy + math.sin(a) * l], fill=GOLD_STRONG, width=10)


def _m_lege(d, cx, cy, r):
    x0, y0, x1, y1 = cx - r * .62, cy - r, cx + r * .62, cy + r * .7
    d.rectangle([x0, y0, x1, y1], outline=GOLD_STRONG, width=12)
    d.polygon([(x1 - r * .34, y0), (x1, y0 + r * .34), (x1 - r * .34, y0 + r * .34)],
              fill=GOLD_WASH, outline=GOLD_STRONG, width=8)
    for i in range(3):
        d.line([x0 + r * .2, y0 + r * .5 + i * r * .28, x1 - r * .36, y0 + r * .5 + i * r * .28],
               fill=LINE, width=12)
    d.ellipse([cx - r * .16, y1 - r * .05, cx + r * .2, y1 + r * .31], fill=GOLD)


def _m_economie(d, cx, cy, r):
    for i, hf in enumerate([.35, .6, .95]):
        x = cx - r + i * r * .75
        d.rectangle([x, cy + r * .8 - 2 * r * hf * .8, x + r * .42, cy + r * .8],
                    fill=GOLD if i == 2 else LINE)
    d.line([cx - r * .9, cy + r * .3, cx + r * .62, cy - r * .75], fill=GOLD_STRONG, width=12)
    d.polygon([(cx + r * .62, cy - r * .75), (cx + r * .25, cy - r * .72),
               (cx + r * .5, cy - r * .38)], fill=GOLD_STRONG)


def _m_sport(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD_STRONG, width=12)
    pts = [(cx + math.cos(a) * r * .38, cy + math.sin(a) * r * .38)
           for a in [(-90 + i * 72) * math.pi / 180 for i in range(5)]]
    d.polygon(pts, fill=GOLD)
    for px, py in pts:
        d.line([px, py, cx + (px - cx) * 2.4, cy + (py - cy) * 2.4], fill=GOLD_STRONG, width=9)


def _m_tech(d, cx, cy, r):
    nodes = [(cx, cy - r), (cx - r, cy + r * .3), (cx + r, cy + r * .3),
             (cx, cy + r * .9), (cx, cy)]
    for a, b in [(0, 4), (1, 4), (2, 4), (3, 4), (0, 1), (0, 2)]:
        d.line([nodes[a], nodes[b]], fill=GOLD_STRONG, width=9)
    for i, (x, y) in enumerate(nodes):
        rr = r * (.22 if i == 4 else .14)
        d.ellipse([x - rr, y - rr, x + rr, y + rr],
                  fill=GOLD if i == 4 else GOLD_WASH, outline=GOLD_STRONG, width=8)


def _m_monograma(d, cx, cy, r, letter="I"):
    f = _font(True, int(r * 2.2))
    d.text((cx, cy), letter.upper(), font=f, fill=GOLD, anchor="mm")


def _m_orbite(d, cx, cy, r, seed=b""):
    rr = int(r * .32)
    for i in range(6):
        col = GOLD if i % 2 == 0 else LINE
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col, width=6)
        f = .9 + (seed[i] / 255 * .4 if i < len(seed) else .2)
        rr = int(rr * PHI ** 0.5 * f)


# ---- selectie determinista -------------------------------------------------
_KW = [
    (_m_fenomen,   r"canicul|cod rosu|cod portocaliu|furtun|inundat|cutremur|ninsor|meteo|incendi|seceta|grindin"),
    (_m_lege,      r"\blege|ordonant|\boug\b|hotarar|\bvot|adopta|decret|motiun|referendum|amendament"),
    (_m_institutie, r"parlament|guvern|senat|camera deputat|comisia europ|consiliul|minister|primari|anaf|\bbnr\b|\bccr\b|curtea constitut|\bnato\b|\bonu\b|\bue\b"),
    (_m_economie,  r"inflat|doband|\bpret|buget|\btva\b|\bpib\b|salari|\beuro\b|\bleu\b|banc|invest|econom|bursa|export"),
]
_PERSON_HINT = r"declara|critica|anunta|acuza|cere\b|demisio|numit|premier|presedint|ministrul|liderul|selectioner"


def _pick(a: dict):
    text = _norm(a.get("title", "")) + " " + " ".join(_norm(e) for e in a.get("entities") or [])
    cat = a.get("category", "")
    if cat == "sport":
        return _m_sport
    if cat == "tech":
        return _m_tech
    for motif, pat in _KW:
        if re.search(pat, text):
            return motif
    ents = a.get("entities") or []
    if re.search(_PERSON_HINT, text) and any(len(e.split()) >= 2 for e in ents):
        return _m_persoana
    return None                                       # -> abstract seeded


def _wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    if len(lines) > 4:
        lines = lines[:4]
        lines[-1] += "…"
    return lines


def generate(a: dict, path: str) -> bool:
    """Deseneaza coperta articolului la `path`. False la orice problema —
    build-ul nu pica niciodata din cauza unei imagini."""
    if Image is None:
        return False
    try:
        img = Image.new("RGB", (W, H), PAPER2)
        d = ImageDraw.Draw(img)
        gx = int(W / PHI)
        d.rectangle([gx, 0, W, H], fill=GOLD_WASH)
        d.rectangle([0, 0, W, 9], fill=GOLD)
        cx, cy, r = gx + (W - gx) // 2, int(H / PHI), int((W - gx) * .30)
        motif = _pick(a)
        seed = hashlib.sha1((a.get("title") or "").encode()).digest()
        if motif:
            motif(d, cx, cy, r)
        elif seed[0] % 2:
            ents = a.get("entities") or []
            _m_monograma(d, cx, cy, r, (ents[0] if ents else a.get("title") or "I")[0])
        else:
            _m_orbite(d, cx, cy, r, seed)

        serif = _font(True, 58)
        mono = _font(False, 28)
        d.text((50, 46), (a.get("category") or "").upper(), font=mono, fill=GOLD_STRONG)
        y = 110
        for ln in _wrap(d, a.get("title", ""), serif, gx - 90):
            d.text((50, y), ln, font=serif, fill=INK)
            y += 74
        d.text((50, H - 64), "IZZ.ro — Informația Zero Zgomot", font=mono, fill=INK2)

        os.makedirs(os.path.dirname(path), exist_ok=True)
        # culori plate -> paleta de 64: fisier mai mic SI encodare mai rapida decat optimize=True
        img = img.convert("P", palette=Image.ADAPTIVE, colors=64)
        img.save(path, "PNG", compress_level=4)
        return True
    except Exception:
        return False
