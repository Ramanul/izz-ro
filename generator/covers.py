"""Coperti generative per articol (og:image) — grafica proprie, zero surse externe.

v2 'rafinata': supersampling 2x (linii netede), spirala de aur ca semnatura,
motive supradimensionate taiate de margine (tensiune vizuala), transparente
stratificate si o RAMA distincta per categorie — sport dinamic, tech precis,
extern cu meridiane, politic solemn, economic ascendent, general broadsheet.
Semnatura de ediție (hash-ul seed-ului) in colt, ca numerotarea unei serigrafii.

Pictogramele raman alese determinist (categorie + entitati AI + cuvinte-cheie);
fara potrivire clara -> fallback abstract seeded (niciodata o pictograma fortata
gresit). Orice eroare -> False, articolul pastreaza og-image static.
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
GOLD_A = (201, 162, 39)                   # gold ca tuplu, pentru straturi cu alpha
PHI = 1.618
W, H = 1200, 630                          # standardul og:image
SS = 2                                    # supersampling: desenam 2x, redimensionam LANCZOS
W2, H2 = W * SS, H * SS

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "C:/Windows/Fonts",
]
_FONT_CACHE: dict = {}


def _font(bold_serif: bool, size: int):
    key = (bold_serif, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    names = ["DejaVuSerif-Bold.ttf"] if bold_serif else ["DejaVuSansMono.ttf", "consola.ttf"]
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


# ---- motive (draw pe strat RGBA, coordonate 2x) ---------------------------
def _m_persoana(d, cx, cy, r):
    d.ellipse([cx - r * .42, cy - r, cx + r * .42, cy - r * .16],
              outline=GOLD_STRONG, width=10 * SS)
    d.arc([cx - r, cy - r * .1, cx + r, cy + r * 1.6], 200, 340,
          fill=GOLD_STRONG, width=10 * SS)
    d.ellipse([cx - r * .8, cy - r * 1.25, cx - r * .45, cy - r * .9],
              fill=(*GOLD_A, 110))                       # aura discreta
    d.ellipse([cx + r * .16, cy - r * .84, cx + r * .34, cy - r * .66], fill=GOLD)


def _m_institutie(d, cx, cy, r):
    d.polygon([(cx - r, cy - r * .42), (cx + r, cy - r * .42), (cx, cy - r)],
              outline=GOLD_STRONG, width=10 * SS)
    for i in range(4):
        x = cx - r * .72 + i * (r * 1.44 / 3)
        d.line([x, cy - r * .3, x, cy + r * .62], fill=GOLD_STRONG, width=10 * SS)
    d.rectangle([cx - r * 1.06, cy + r * .74, cx + r * 1.06, cy + r * .86], fill=GOLD)
    d.rectangle([cx - r * .8, cy - r * .55, cx + r * .8, cy - r * .42],
                fill=(*GOLD_A, 90))


def _m_fenomen(d, cx, cy, r):
    d.ellipse([cx - r * .52, cy - r * .52, cx + r * .52, cy + r * .52],
              fill=(*GOLD_A, 70))
    d.ellipse([cx - r * .5, cy - r * .5, cx + r * .5, cy + r * .5],
              outline=GOLD, width=11 * SS)
    for i in range(8):
        a = i * math.pi / 4
        l = r * (.78 if i % 2 else 1.0)
        d.line([cx + math.cos(a) * r * .64, cy + math.sin(a) * r * .64,
                cx + math.cos(a) * l, cy + math.sin(a) * l],
               fill=GOLD_STRONG, width=8 * SS)


def _m_lege(d, cx, cy, r):
    x0, y0, x1, y1 = cx - r * .62, cy - r, cx + r * .62, cy + r * .7
    d.rectangle([x0 + r * .1, y0 + r * .1, x1 + r * .1, y1 + r * .1],
                fill=(*GOLD_A, 55))                      # umbra aurie decalata
    d.rectangle([x0, y0, x1, y1], fill=PAPER2, outline=GOLD_STRONG, width=10 * SS)
    d.polygon([(x1 - r * .34, y0), (x1, y0 + r * .34), (x1 - r * .34, y0 + r * .34)],
              fill=GOLD_WASH, outline=GOLD_STRONG, width=7 * SS)
    for i in range(3):
        d.line([x0 + r * .2, y0 + r * .5 + i * r * .28,
                x1 - r * .36, y0 + r * .5 + i * r * .28], fill=LINE, width=10 * SS)
    d.ellipse([cx - r * .16, y1 - r * .05, cx + r * .2, y1 + r * .31], fill=GOLD)


def _m_economie(d, cx, cy, r):
    for i, hf in enumerate([.35, .6, .95]):
        x = cx - r + i * r * .75
        d.rectangle([x, cy + r * .8 - 2 * r * hf * .8, x + r * .42, cy + r * .8],
                    fill=GOLD if i == 2 else (*GOLD_A, 60))
    d.line([cx - r * .9, cy + r * .3, cx + r * .62, cy - r * .75],
           fill=GOLD_STRONG, width=10 * SS)
    d.polygon([(cx + r * .68, cy - r * .82), (cx + r * .25, cy - r * .72),
               (cx + r * .52, cy - r * .36)], fill=GOLD_STRONG)


def _m_sport(d, cx, cy, r):
    for k, al in ((1.28, 45), (1.14, 80)):               # arce de miscare
        d.arc([cx - r * k, cy - r * k, cx + r * k, cy + r * k], 130, 240,
              fill=(*GOLD_A, al), width=7 * SS)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD_STRONG, width=10 * SS)
    pts = [(cx + math.cos(a) * r * .38, cy + math.sin(a) * r * .38)
           for a in [(-90 + i * 72) * math.pi / 180 for i in range(5)]]
    d.polygon(pts, fill=GOLD)
    for px, py in pts:
        d.line([px, py, cx + (px - cx) * 2.4, cy + (py - cy) * 2.4],
               fill=GOLD_STRONG, width=7 * SS)


def _m_tech(d, cx, cy, r):
    nodes = [(cx, cy - r), (cx - r, cy + r * .3), (cx + r, cy + r * .3),
             (cx, cy + r * .9), (cx, cy)]
    for a, b in [(0, 4), (1, 4), (2, 4), (3, 4), (0, 1), (0, 2)]:
        d.line([nodes[a], nodes[b]], fill=GOLD_STRONG, width=7 * SS)
    for i, (x, y) in enumerate(nodes):
        rr = r * (.24 if i == 4 else .13)
        d.ellipse([x - rr, y - rr, x + rr, y + rr],
                  fill=GOLD if i == 4 else PAPER2, outline=GOLD_STRONG, width=7 * SS)


def _m_monograma(d, cx, cy, r, letter="I"):
    f = _font(True, int(r * 2.3))
    d.text((cx + 6 * SS, cy + 6 * SS), letter.upper(), font=f,
           fill=(*GOLD_A, 70), anchor="mm")              # umbra
    d.text((cx, cy), letter.upper(), font=f, fill=GOLD, anchor="mm")


def _m_orbite(d, cx, cy, r, seed=b""):
    rr = int(r * .3)
    for i in range(6):
        w = (7 if i % 2 == 0 else 4) * SS
        col = GOLD if i % 2 == 0 else (*GOLD_A, 70)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col, width=w)
        f = .9 + (seed[i] / 255 * .4 if i < len(seed) else .2)
        rr = int(rr * PHI ** 0.5 * f)


# ---- rame per categorie (personalitatea domeniului) ------------------------
def _fr_politic(d, gx):                                  # pinstripes solemne
    for i, x in enumerate((gx + 14 * SS, gx + 26 * SS)):
        d.line([x, 0, x, H2], fill=INK if i == 0 else GOLD, width=2 * SS)


def _fr_economic(d, gx):                                 # gradatii de axa, ascendente
    for i in range(9):
        x = gx + int((W2 - gx) * i / 9)
        h = (10 + i * 4) * SS
        d.line([x, H2 - h, x, H2], fill=GOLD_STRONG, width=3 * SS)


def _fr_extern(d, gx):                                   # meridiane
    cx = W2 + 40 * SS
    for k in (1.5, 1.1, .7):
        r = int((W2 - gx) * k)
        d.arc([cx - r, H2 // 2 - r, cx + r, H2 // 2 + r], 90, 270,
              fill=(*GOLD_A, 60), width=3 * SS)


def _fr_sport(d, gx):                                    # dungi de viteza
    for i, al in enumerate((150, 90, 45)):
        off = i * 26 * SS
        d.line([gx - 60 * SS + off, H2, gx + 130 * SS + off, H2 - 190 * SS],
               fill=(*GOLD_A, al), width=12 * SS)


def _fr_tech(d, gx):                                     # grila de puncte
    step = 42 * SS
    for x in range(gx + step // 2, W2, step):
        for y in range(step // 2, H2, step):
            d.ellipse([x - 2 * SS, y - 2 * SS, x + 2 * SS, y + 2 * SS],
                      fill=(*GOLD_A, 70))


def _fr_general(d, gx):                                  # rigle duble broadsheet
    for y in (18 * SS, H2 - 18 * SS):
        d.line([gx + 12 * SS, y, W2 - 12 * SS, y], fill=GOLD_STRONG, width=2 * SS)
        d.line([gx + 12 * SS, y + 5 * SS if y < H2 // 2 else y - 5 * SS,
                W2 - 12 * SS, y + 5 * SS if y < H2 // 2 else y - 5 * SS],
               fill=LINE, width=2 * SS)


_FRAMES = {"politic": _fr_politic, "economic": _fr_economic, "extern": _fr_extern,
           "sport": _fr_sport, "tech": _fr_tech, "general": _fr_general}


def _spiral(d):
    """Spirala de aur — semnatura casei, hairline, ancorata dreapta-jos."""
    x, y = W2, H2
    r = int(H2 / PHI)
    quads = [(90, 180), (180, 270), (270, 360), (0, 90)]
    cxy = [(x, y), (x - 0, y - 0)]
    cx, cy = x, y
    for i in range(5):
        a0, a1 = quads[i % 4]
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=LINE, width=2 * SS)
        if i % 4 == 0:
            cy -= 0
            cx -= 0
        r = int(r / PHI)


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
    return None


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
        base = Image.new("RGB", (W2, H2), PAPER2)
        over = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        db, do = ImageDraw.Draw(base), ImageDraw.Draw(over)

        gx = int(W2 / PHI)
        db.rectangle([gx, 0, W2, H2], fill=GOLD_WASH)
        _spiral(db)
        _FRAMES.get(a.get("category", ""), _fr_general)(do, gx)
        db.rectangle([0, 0, W2, 9 * SS], fill=GOLD)

        # motiv supradimensionat, usor peste linia de aur (taiat de margine = tensiune)
        seed = hashlib.sha1((a.get("title") or "").encode()).digest()
        panel = W2 - gx
        cx = gx + int(panel * .58)
        cy = int(H2 / PHI)
        r = int(panel * .40)
        motif = _pick(a)
        if motif:
            motif(do, cx, cy, r)
        elif seed[0] % 2:
            ents = a.get("entities") or []
            _m_monograma(do, cx, cy, r, (ents[0] if ents else a.get("title") or "I")[0])
        else:
            _m_orbite(do, cx, cy, r, seed)

        base.paste(over, (0, 0), over)
        d = ImageDraw.Draw(base)
        serif = _font(True, 58 * SS)
        mono = _font(False, 27 * SS)
        mono_s = _font(False, 21 * SS)
        d.text((50 * SS, 44 * SS), (a.get("category") or "").upper(),
               font=mono, fill=GOLD_STRONG)
        y = 108 * SS
        for ln in _wrap(d, a.get("title", ""), serif, gx - 88 * SS):
            d.text((50 * SS, y), ln, font=serif, fill=INK)
            y += 73 * SS
        d.text((50 * SS, H2 - 62 * SS), "IZZ.ro — Informația Zero Zgomot",
               font=mono, fill=INK2)
        d.text((W2 - 30 * SS, H2 - 30 * SS), f"Nº {seed.hex()[:6]}",
               font=mono_s, fill=GOLD_STRONG, anchor="rs")   # semnatura de editie

        img = base.resize((W, H), Image.LANCZOS)
        img = img.convert("P", palette=Image.ADAPTIVE, colors=128)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path, "PNG", compress_level=4)
        return True
    except Exception:
        return False
