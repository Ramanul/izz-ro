"""Coperti editoriale per articol — v5 'unic per articol' (fallback Pillow).

Motorul PRINCIPAL de imagini e HTML/CSS + Chromium (generator/htmlart.py, randat
in Actions, comis in media/). Acest modul e FALLBACK-ul offline: cand imaginea
comisa lipseste, render.py genereaza aici una echivalenta, 100% legala:
- paleta cu nuanta continua derivata din continut -> fiecare stire alta culoare
- pictograme tematice (Tabler, MIT) extrase din titlu+entitati (_KW_ICON)
- layout ales din mai multe scheme din seed -> doua articole nu seamana
- tipografie Playfair Display 800 (OFL) pe coperta og, rama aurie
- siguranta: orice eroare -> False, articolul pastreaza og-image static
"""
import colorsys
import hashlib
import math
import os
import random
import re

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    Image = None

PAPER = "#f6f7f9"
INK, INK2 = "#15171c", "#4d5562"           # text pe fond deschis (ca pe site)
GOLD = (201, 162, 39)
GOLD_HEX, GOLD_STRONG = "#c9a227", "#8b6918"
MUTED = "#8b8fa0"                          # text secundar
PHI = 1.618
W, H = 1200, 630
SS = 2
W2, H2 = W * SS, H * SS
ART_W, ART_H = 960, 504

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_FONT_CACHE: dict = {}
_ICON_CACHE: dict = {}


def _font(kind: str, size: int):
    key = (kind, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    paths = {
        "display": [os.path.join(_ASSETS, "PlayfairDisplay_800ExtraBold.ttf")],
        "mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                 "C:/Windows/Fonts/consola.ttf"],
    }[kind]
    f = None
    for p in paths:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            break
    _FONT_CACHE[key] = f or ImageFont.load_default()
    return _FONT_CACHE[key]


def _icon_img(name: str):
    if name in _ICON_CACHE:
        return _ICON_CACHE[name]
    p = os.path.join(_ASSETS, "icons", f"{name}.png")
    img = Image.open(p).convert("RGBA") if os.path.exists(p) else None
    _ICON_CACHE[name] = img
    return img


_DIA = str.maketrans("ăâîșțĂÂÎȘȚşţŞŢ", "aaistAAISTstST")


def _norm(s: str) -> str:
    return (s or "").translate(_DIA).lower()


# ---- selectia icoanei tematice (silueta focala) ----------------------------
_KW_ICON = [
    (r"canicul|arsita|tempera", "sun"), (r"furtun|vijel|cod portocaliu|cod rosu", "cloud-storm"),
    (r"inundat|viitur", "droplet"), (r"ninsor|zapad|\bger\b|viscol", "snowflake"),
    (r"incendi", "flame"), (r"tornad", "tornado"), (r"cutremur|seism", "alert-triangle"),
    (r"instanta|tribunal|judecat|proces|condamn|achitat", "gavel"),
    (r"\blege\b|legea |ordonant|decret|amendament|hotarar", "certificate"),
    (r"parlament|senat|camera deputat", "building-monument"),
    (r"guvern|ministr|premier|cabinet", "podium"), (r"presedint", "podium"),
    (r"alegeri|electoral|scrutin|referendum|urne", "writing"),
    (r"inflat|scumpir", "percentage"), (r"buget|fiscal|\btva\b|taxe|impozit", "receipt-tax"),
    (r"banc|\bbnr\b|credit|doband", "building-bank"), (r"\beuro\b|curs valutar", "currency-euro"),
    (r"dolar", "currency-dollar"), (r"salari|pensi", "pig-money"),
    (r"bursa|actiuni|investitor", "chart-line"), (r"fabric|industri|uzin", "building-factory"),
    (r"energie|electric|curent", "bolt"), (r"\bgaz(?:e|ul|ului|elor)?\b|petrol|carburant|benzin|motorin", "gas-station"),
    (r"comert|retail|magazin|consum", "shopping-cart"),
    (r"agricult|fermier|recolt|cereale", "tractor"),
    (r"razboi|militar|armata|front|ofensiv|trupe", "swords"), (r"drona|dronele", "helicopter"),
    (r"rachet", "rocket"), (r"\bnato\b", "shield"), (r"\bonu\b|natiunile unite", "globe"), (r"sanctiun|embargo", "lock"),
    (r"ambasad|diplomat|consulat", "flag"), (r"\bue\b|uniunea europ|bruxelles|comisia europ", "globe"),
    (r"avion|aeroport|zbor|aerian", "plane"), (r"tren|feroviar|\bcfr\b|metrou", "train"),
    (r"camion|\btir\b", "truck"), (r"soferi|rutier|autoturism|masina|automobil", "car"),
    (r"port maritim|naval|vapor|nava", "ship"),
    (r"spital", "building-hospital"), (r"medic|doctor|sanatat", "stethoscope"),
    (r"vaccin", "vaccine"), (r"virus|gripa|covid|epidemi", "virus"),
    (r"medicament|farmaci", "pill"), (r"cancer|cardiac|diabet", "heartbeat"),
    (r"cercetat|studiu|savant|stiint", "microscope"), (r"spatiu|nasa|astronaut|cosmic", "rocket"),
    (r"satelit", "satellite"), (r"inteligenta artificial|\bai\b|chatbot", "robot"),
    (r"\bcip\b|semiconduct|procesor", "cpu"), (r"telefon|smartphone|iphone|android", "device-mobile"),
    (r"laptop|calculator|\bpc\b", "device-laptop"), (r"internet|retea|5g|fibra", "wifi"),
    (r"hacker|cibernetic|phishing|ransomware", "shield-lock"), (r"baza de date|datele", "database"),
    (r"fotbal|liga|gol\b|meci|echipa nationala|cupa mondial|\bcm \d{4}|optimi|sferturi|semifinal", "ball-football"),
    (r"tenis|wimbledon|roland|us open", "ball-tennis"), (r"baschet", "ball-basketball"),
    (r"volei", "ball-volleyball"), (r"inot|natatie", "swimming"), (r"ciclism|turul", "bike"),
    (r"atletism|maraton|alergare", "run"), (r"olimpi", "medal"),
    (r"campioan|trofeu|castiga titlul", "trophy"),
    (r"formula 1|raliu|motogp|automobilism|circuitul", "car"),
    (r"handbal|rugby|polo\b", "trophy"), (r"\bbox\b|mma\b|kickbox|gimnast", "medal"),
    (r"film|cinema|regizor", "movie"), (r"muzic|concert|festival", "music"),
    (r"teatru", "masks-theater"), (r"expozit|muzeu|pictur", "palette"),
    (r"educat|scoal|elevi|bacalaureat|universitat|studenti", "school"),
    (r"biseric|patriarh|manastir", "building-church"),
    (r"politie|politist|jandarm", "shield"), (r"accident|raniti", "ambulance"),
    (r"pompier", "firetruck"), (r"constructi|autostrad|santier|infrastructur", "crane"),
    (r"imobiliar|locuint|chirii|apartament", "home"),
    (r"turism|vacant|litoral|statiun", "umbrella"), (r"padur|mediu|polua|emisii|clima", "trees"),
    (r"munte|alpin", "mountain"), (r"protest|miting|grev|mars", "speakerphone"),
    (r"restaurant|aliment|mancare|gastronom", "tools-kitchen-2"),
]
# rotatie seeded per categorie cand niciun cuvant-cheie nu decide
_CAT_ICONS = {"politic": ["building-monument", "podium"],
              "economic": ["chart-line", "coins", "trending-up"],
              "extern": ["globe", "compass", "world-latitude"],
              "sport": ["ball-football", "trophy", "medal"],
              "tech": ["cpu", "device-laptop"]}


def _pick_icon(a: dict) -> str | None:
    ai = a.get("icon")
    if ai and _icon_img(ai):
        return ai
    text = _norm(a.get("title", "")) + " " + " ".join(_norm(e) for e in a.get("entities") or [])
    for pat, icon in _KW_ICON:
        if re.search(pat, text) and _icon_img(icon):
            return icon
    pool = _CAT_ICONS.get(a.get("category", ""))
    if not pool:
        return None
    seed = hashlib.sha1((a.get("title") or "").encode()).digest()
    return pool[seed[2] % len(pool)]


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))



def _crowd(base, y, col, rng, n, h=None):
    """Rand de oameni-silueta (cap + corp) pe o linie -> multime, scara umana."""
    h = h or int(H2 * 0.07)
    layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x = rng.uniform(W2 * 0.02, W2 * 0.98)
        ph = h * rng.uniform(0.8, 1.2)
        bw, hr = ph * 0.42, ph * 0.2
        d.rounded_rectangle([x - bw / 2, y - ph * 0.66, x + bw / 2, y], radius=bw * 0.45, fill=(*col, 255))
        d.ellipse([x - hr, y - ph, x + hr, y - ph + 2 * hr], fill=(*col, 255))
    base.alpha_composite(layer)



# ============================================================================
# Agent grafic: imagine UNICA per articol. Preanalizeaza titlul+entitatile ->
# paleta cu nuanta continua (fiecare stire alta culoare), pictograme tematice
# extrase din text, layout ales din mai multe scheme. Doua articole nu produc
# imagini asemanatoare.
# ============================================================================
def _hsl(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h % 1, min(1, max(0, l)), min(1, max(0, s)))
    return (int(r * 255), int(g * 255), int(b * 255))


def _u_palette(seed):
    h = seed[0] / 255
    return {
        "bg1": _hsl(h, 0.93, 0.30 + seed[1] / 255 * 0.2),
        "bg2": _hsl(h + 0.05, 0.86, 0.28),
        "mid": _hsl(h, 0.5, 0.5),
        "dark": _hsl(h, 0.32, 0.52),
        "accent": _hsl((h + (0.5 if seed[2] > 90 else 0.33)) % 1, 0.52, 0.72),
        "gold": GOLD,
    }


def _u_elements(a):
    text = _norm(a.get("title", "")) + " " + " ".join(_norm(e) for e in a.get("entities") or [])
    out = []
    for pat, icon in _KW_ICON:
        if re.search(pat, text) and _icon_img(icon) and icon not in out:
            out.append(icon)
        if len(out) >= 5:
            break
    if a.get("icon") and a["icon"] not in out and _icon_img(a["icon"]):
        out.insert(0, a["icon"])
    for ic in _CAT_ICONS.get(a.get("category", ""), []):
        if len(out) < 3 and ic not in out and _icon_img(ic):
            out.append(ic)
    return out[:5] or ["building-community"]


def _u_grad(c0, c1, diag):
    base = Image.new("RGB", (W2, H2), c0)
    top = Image.new("RGB", (W2, H2), c1)
    mask = Image.new("L", (W2, H2), 0)
    d = ImageDraw.Draw(mask)
    for i in range(0, W2 + H2, 6):
        v = int(255 * i / (W2 + H2))
        d.line([(i, 0), (i - H2, H2)] if diag else [(0, i), (W2, i - W2)], fill=v, width=8)
    base.paste(top, (0, 0), mask)
    return base.convert("RGBA")


def _u_icon(base, name, size, cx, cy, col, op=1.0, glow=None, rot=0):
    src = _icon_img(name)
    if src is None:
        return
    a = src.split()[3].resize((size, size), Image.LANCZOS)
    if rot:
        a = a.rotate(rot, expand=False, resample=Image.BILINEAR)
    if op < 1:
        a = a.point(lambda v: int(v * op))
    if glow:
        gl = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        gl.paste(Image.new("RGBA", (size, size), (*glow, 255)), (size // 2, size // 2), a.point(lambda v: int(v * .7)))
        base.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18 * SS)), (cx - size, cy - size))
    lay = Image.new("RGBA", (size, size), (*col, 255))
    lay.putalpha(a)
    base.alpha_composite(lay, (cx - size // 2, cy - size // 2))


def _u_blobs(base, pal, rng):
    lay = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(3):
        col = rng.choice([pal["mid"], pal["accent"]])
        r = int(W2 * rng.uniform(.25, .5))
        cx, cy = rng.uniform(0, W2), rng.uniform(0, H2)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*col, 40))
    base.alpha_composite(lay.filter(ImageFilter.GaussianBlur(110 * SS)))


def _lay_hero(base, els, pal, rng):
    _u_blobs(base, pal, rng)
    d = ImageDraw.Draw(base)
    cx, cy = int(W2 * rng.uniform(.42, .6)), int(H2 * .5)
    for i in range(4):
        r = H2 * (.2 + i * .12)
        d.arc([cx - r, cy - r, cx + r, cy + r], 0, 360, fill=(*pal["accent"], 40), width=2 * SS)
    _u_icon(base, els[0], int(H2 * .4), cx, cy, pal["dark"], glow=pal["accent"])
    for e in els[1:4]:
        ang = rng.uniform(0, 6.28)
        _u_icon(base, e, int(H2 * .13), cx + int(math.cos(ang) * W2 * .3), cy + int(math.sin(ang) * H2 * .34),
                pal["mid"], op=.85)


def _lay_horizon(base, els, pal, rng):
    hz = int(H2 * rng.uniform(.6, .72))
    d = ImageDraw.Draw(base)
    d.rectangle([0, hz, W2, H2], fill=pal["dark"])
    sx, sy = int(W2 * rng.uniform(.2, .8)), int(hz * rng.uniform(.4, .8))
    gl = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([sx - H2 * .3, sy - H2 * .3, sx + H2 * .3, sy + H2 * .3], fill=(*pal["gold"], 220))
    base.alpha_composite(gl.filter(ImageFilter.GaussianBlur(40 * SS)))
    xs = [.24, .5, .76]
    for i, e in enumerate(els[:3]):
        _u_icon(base, e, int(H2 * (.26 - i * .03)), int(W2 * xs[i]), hz,
                _lerp(pal["dark"], (255, 255, 255), .12) if i == 0 else pal["mid"],
                glow=pal["gold"] if i == 0 else None)
    _crowd(base, hz + int(H2 * .04), pal["dark"], rng, n=16)


def _lay_diagonal(base, els, pal, rng):
    d = ImageDraw.Draw(base)
    for i, col in enumerate([pal["accent"], pal["mid"], pal["dark"]]):
        off = i * W2 * .18
        d.polygon([(off, H2), (off + W2 * .4, H2), (off + W2 * .7, 0), (off + W2 * .3, 0)], fill=(*col, 90))
    for i, e in enumerate(els[:3]):
        _u_icon(base, e, int(H2 * (.3 - i * .06)), int(W2 * (.28 + i * .26)), int(H2 * (.34 + i * .2)),
                pal["dark"] if i else _lerp(pal["accent"], (0, 0, 0), .1), glow=pal["gold"] if i == 0 else None,
                rot=rng.uniform(-8, 8))


def _lay_constellation(base, els, pal, rng):
    _u_blobs(base, pal, rng)
    pts = [(int(W2 * rng.uniform(.12, .88)), int(H2 * rng.uniform(.18, .82))) for _ in els]
    d = ImageDraw.Draw(base)
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=(*pal["accent"], 120), width=2 * SS)
    for (x, y), e in zip(pts, els):
        _u_icon(base, e, int(H2 * rng.uniform(.16, .28)), x, y, pal["dark"], glow=pal["accent"])


def _lay_tiles(base, els, pal, rng):
    n = max(2, min(4, len(els)))
    tw = W2 // n
    cols = [pal["accent"], pal["mid"], pal["dark"], pal["gold"]]
    rng.shuffle(cols)
    d = ImageDraw.Draw(base)
    for i in range(n):
        d.rectangle([i * tw, 0, (i + 1) * tw - 6 * SS, H2], fill=(*cols[i % 4], 210))
        _u_icon(base, els[i % len(els)], int(H2 * .34), i * tw + tw // 2, H2 // 2,
                _lerp(cols[i % 4], (255, 255, 255), .75))


def _lay_bigduo(base, els, pal, rng):
    _u_icon(base, els[0], int(H2 * 1.15), int(W2 * rng.uniform(.4, .62)), int(H2 * .52), pal["mid"], op=.5)
    d = ImageDraw.Draw(base)
    d.rectangle([0, int(H2 * .78), W2, H2], fill=(*pal["dark"], 255))
    for i, e in enumerate(els[1:4]):
        _u_icon(base, e, int(H2 * .16), int(W2 * (.2 + i * .3)), int(H2 * .82), _lerp(pal["accent"], (255, 255, 255), .3))


_U_LAYOUTS = [_lay_hero, _lay_horizon, _lay_diagonal, _lay_constellation, _lay_tiles, _lay_bigduo]


def _compose_scene(a: dict):
    seed = hashlib.sha1((a.get("title") or "x").encode()).digest()
    rng = random.Random(seed)
    pal = _u_palette(seed)
    els = _u_elements(a)
    img = _u_grad(pal["bg1"], pal["bg2"], seed[3] % 2)
    _U_LAYOUTS[seed[4] % len(_U_LAYOUTS)](img, els, pal, rng)
    return _frame(img.convert("RGB"))


def _frame(img):
    """Rama aurie subtire, inset -> delimiteaza scena luminoasa pe fundalul alb al site-ului."""
    d = ImageDraw.Draw(img)
    m = int(W2 * 0.02)
    d.rectangle([m, m, W2 - m - 1, H2 - m - 1], outline=GOLD, width=3 * SS)
    return img


# scena e identica pentru cover.jpg si art.jpg -> o calculam O DATA per articol
_SCENE_CACHE: dict = {}
def _scene(a: dict):
    key = a.get("title") or ""
    if key not in _SCENE_CACHE:
        _SCENE_CACHE.clear()                # pastreaza doar ultimul articol
        _SCENE_CACHE[key] = _compose_scene(a)
    return _SCENE_CACHE[key].copy()


# ---- text pentru coperta de share ------------------------------------------
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
        lines[-1] = lines[-1].rstrip(",;:") + "…"
    return lines


_SCRIM = None
def _scrim():
    """Val ALB stanga+jos -> titlul inchis ramane lizibil peste scena luminoasa."""
    global _SCRIM
    if _SCRIM is None:
        left = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        dl = ImageDraw.Draw(left)
        span = int(W2 * 0.6)
        for x in range(span):
            dl.line([(x, 0), (x, H2)], fill=(250, 249, 245, int(220 * (1 - x / span) ** 1.3)))
        _SCRIM = left
    return _SCRIM


def _draw_text(img, a: dict):
    img = Image.alpha_composite(img.convert("RGBA"), _scrim()).convert("RGB")
    d = ImageDraw.Draw(img)
    mono = _font("mono", 26 * SS)
    mono_s = _font("mono", 20 * SS)
    display = _font("display", 62 * SS)
    d.text((56 * SS, 48 * SS), (a.get("category") or "știri").upper(), font=mono, fill=GOLD_STRONG)
    rule_w = int((W2 / PHI - 112 * SS) / PHI)
    d.line([56 * SS, 96 * SS, 56 * SS + rule_w, 96 * SS], fill=GOLD_HEX, width=2 * SS)
    y = 128 * SS
    for ln in _wrap(d, a.get("title", ""), display, int(W2 / PHI) - 88 * SS):
        d.text((56 * SS, y), ln, font=display, fill=INK)
        y += 82 * SS
    d.text((56 * SS, H2 - 66 * SS), "IZZ.ro — Informația Zero Zgomot", font=mono, fill=INK2)
    seed = hashlib.sha1((a.get("title") or "").encode()).digest()
    d.text((W2 - 34 * SS, H2 - 34 * SS), f"Nº {seed.hex()[:6]}", font=mono_s, fill=GOLD_STRONG, anchor="rs")
    return img


def _save(base, path: str, size) -> None:
    img = base.resize(size, Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=84)


def generate(a: dict, path: str) -> bool:
    """Coperta de SHARE (og:image, cu titlu) la `path`. False la orice problema."""
    if Image is None:
        return False
    try:
        _save(_draw_text(_scene(a), a), path, (W, H))
        return True
    except Exception:
        return False


def generate_art(a: dict, path: str) -> bool:
    """Varianta de SITE (fara text -- titlul e deja pe pagina): aceeasi scena, 960x504."""
    if Image is None:
        return False
    try:
        _save(_scene(a), path, (ART_W, ART_H))
        return True
    except Exception:
        return False
