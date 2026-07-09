"""Coperti editoriale per articol (og:image) — v4 'scene'.

Fundatie profesionista, 100% legala si offline:
- tipografie: Playfair Display 800 (OFL, fontul masthead-ului site-ului)
- iconografie: Tabler Icons (MIT), pictograme desenate de designeri, folosite ca
  SILUETE tematice in prim-plan (nu icoane care plutesc)
- compozitie: SCENA reala compusa din forme desenate -- cer + soare/luna, linie de
  orizont, siluete pe planuri cu perspectiva atmosferica (departe cetos/deschis,
  aproape inchis). Arhetipuri pe categorie: ORAS (skyline cu ferestre aprinse),
  STADION (nocturne + teren), MARE (tarm + vapor + avion). Totul din seed-ul
  titlului (rng) -> doua stiri din aceeasi categorie au scene vizibil diferite.
- selectie: icoana tematica din AI ('icon') / cuvinte-cheie devine silueta focala
- siguranta: orice eroare -> False, articolul pastreaza og-image static
"""
import hashlib
import math
import os
import random
import re

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
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


# ---- paleta de scena pe categorie ------------------------------------------
# LUMINOS pe fond alb-crema (ca site-ul): cer aproape alb cu tenta, siluete in
# tonuri MEDII (citibile pe deschis, nu negre), accent auriu viu + rama aurie.
# (cer sus tenta, cer jos alb-crema, siluete departe deschise, aproape medii, accent).
PAPER_RGB, CREAM = (246, 247, 249), (250, 247, 238)
PAL = {
    "politic":  [(210, 224, 242), CREAM, (188, 202, 224), (110, 132, 170), (201, 162, 39)],
    "economic": [(206, 234, 224), CREAM, (176, 210, 196), (96, 150, 128), (201, 162, 39)],
    "extern":   [(206, 230, 244), (244, 250, 252), (184, 214, 232), (104, 150, 186), (74, 150, 186)],
    "sport":    [(250, 224, 206), CREAM, (240, 198, 182), (196, 118, 100), (201, 120, 52)],
    "tech":     [(224, 218, 246), (248, 246, 252), (206, 198, 232), (140, 122, 190), (86, 168, 190)],
    "general":  [(218, 226, 236), CREAM, (200, 204, 210), (124, 132, 144), (201, 162, 39)],
}
CITY_AMBIENT = {"politic": ["flag"], "economic": ["coins"], "tech": ["antenna"], "general": ["trees"]}


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---- straturi de scena -----------------------------------------------------
def _sky(sky_top, sky_bot, horizon):
    img = Image.new("RGB", (W2, H2), sky_top)
    d = ImageDraw.Draw(img)
    for y in range(horizon):
        d.line([(0, y), (W2, y)], fill=_lerp(sky_top, sky_bot, y / max(1, horizon)))
    return img


def _sun(img, accent, rng, horizon):
    cx = int(W2 * rng.uniform(0.15, 0.85))
    cy = int(horizon * rng.uniform(0.45, 0.9))
    r = int(W2 * rng.uniform(0.16, 0.26))
    q = 3
    sm = Image.new("L", (W2 // q, H2 // q), 0)
    ImageDraw.Draw(sm).ellipse([cx // q - r // q, cy // q - r // q, cx // q + r // q, cy // q + r // q], fill=200)
    sm = sm.filter(ImageFilter.GaussianBlur(r // q // 2))
    glow = Image.new("RGB", (W2, H2), accent)
    out = Image.new("RGB", (W2, H2), (0, 0, 0))
    out.paste(glow, (0, 0), sm.resize((W2, H2), Image.BILINEAR))
    disc = Image.new("RGB", (W2, H2), (0, 0, 0))
    dm = Image.new("L", (W2, H2), 0)
    dr = int(r * 0.5)
    ImageDraw.Draw(dm).ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=255)
    disc.paste(Image.new("RGB", (W2, H2), _lerp(accent, (255, 255, 255), 0.4)), (0, 0),
               dm.filter(ImageFilter.GaussianBlur(4 * SS)))
    # aditiv pur (scale=1.0): soarele ADAUGA lumina, nu imparte/intuneca fundalul
    return ImageChops.add(ImageChops.add(img, out), disc)


def _windows(d, x0, y0, x1, y1, col, rng):
    wy = y0 + 12 * SS
    while wy < y1 - 10 * SS:
        wx = x0 + 10 * SS
        while wx < x1 - 12 * SS:
            if rng.random() > 0.35:
                d.rectangle([wx, wy, wx + 5 * SS, wy + 8 * SS], fill=(*col, rng.randint(120, 230)))
            wx += 14 * SS
        wy += 20 * SS


def _skyline(base, col, rng, horizon, ymin, ymax, near, accent):
    layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = -rng.randint(0, 40) * SS
    while x < W2:
        bw = int(W2 * rng.uniform(0.05, 0.11))
        bh = int(H2 * rng.uniform(ymin, ymax))
        top = horizon - bh
        d.rectangle([x, top, x + bw - 3 * SS, horizon], fill=(*col, 255))
        if rng.random() > 0.6:                         # antena / turnulet
            d.rectangle([x + bw // 2 - SS, top - rng.randint(10, 40) * SS, x + bw // 2 + SS, top], fill=(*col, 255))
        if near:
            _windows(d, x, top, x + bw, horizon, accent, rng)
        x += bw + rng.randint(2, 10) * SS
    if not near:
        layer = layer.filter(ImageFilter.GaussianBlur(2 * SS))   # ceata atmosferica
    base.alpha_composite(layer)


def _ground(base, col, horizon):
    g = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ImageDraw.Draw(g).rectangle([0, horizon, W2, H2], fill=(*col, 255))
    base.alpha_composite(g)


def _silhouette(base, name, h, cx, groundy, col, rng, glow=False, accent=None):
    src = _icon_img(name)
    if src is None:
        return
    a = src.split()[3].resize((h, h), Image.LANCZOS)
    layer = Image.new("RGBA", (h, h), (*col, 255))
    layer.putalpha(a)
    if glow and accent:
        gl = Image.new("RGBA", (h * 2, h * 2), (0, 0, 0, 0))
        gl.paste(Image.new("RGBA", (h, h), (*accent, 255)), (h // 2, h // 2), a.point(lambda v: int(v * 0.7)))
        gl = gl.filter(ImageFilter.GaussianBlur(16 * SS))
        base.alpha_composite(gl, (cx - h, groundy - h - h // 2))
    base.alpha_composite(layer, (cx - h // 2, groundy - h))


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


def _stands_crowd(base, cx, horizon, rw, rh, col, rng):
    """Puncte in tribune -> spectatori."""
    layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(460):
        t = rng.uniform(0.08, math.pi - 0.08)
        rr = rng.uniform(0.7, 0.99)
        x = cx + math.cos(t) * rw * rr
        yy = horizon - math.sin(t) * rh * rr
        if yy < horizon - rh * 0.12:
            d.ellipse([x - 2 * SS, yy - 2 * SS, x + 2 * SS, yy + 2 * SS], fill=(*col, rng.randint(110, 210)))
    base.alpha_composite(layer)


def _scene_city(base, pal, rng, horizon, a):
    sky_top, sky_bot, far, near, accent = pal
    _skyline(base, _lerp(far, sky_bot, 0.4), rng, horizon, 0.10, 0.26, False, accent)
    _ground(base, _lerp(near, CREAM, 0.62), horizon)
    _skyline(base, near, rng, horizon, 0.18, 0.42, True, accent)
    focal = _pick_icon(a) or "building-community"
    _silhouette(base, focal, int(H2 * 0.27), int(W2 * rng.uniform(0.42, 0.7)), horizon,
                accent, rng, glow=True, accent=accent)
    # oameni in prim-plan (miting mai dens la politic; oras animat la general)
    dense = a.get("category") in ("politic", "general")
    _crowd(base, horizon + int(H2 * 0.055), _lerp(near, (18, 16, 22), 0.25), rng,
           n=34 if dense else 20)


def _scene_stadium(base, pal, rng, horizon, a):
    sky_top, sky_bot, far, near, accent = pal
    d = ImageDraw.Draw(base)
    cx = W2 // 2
    rw, rh = int(W2 * 0.62), int(H2 * 0.5)
    for i in range(4):                                  # tribune: arce concentrice
        d.ellipse([cx - rw + i * 12 * SS, horizon - rh + i * 10 * SS, cx + rw - i * 12 * SS, horizon],
                  outline=(*_lerp(far, near, i / 4), 255), width=10 * SS)
    _stands_crowd(base, cx, horizon, rw, rh, _lerp(near, accent, 0.35), rng)   # spectatori
    _ground(base, _lerp(near, CREAM, 0.62), horizon)
    for fx in (0.2, 0.8):                               # nocturne
        px = int(W2 * fx)
        d.line([px, horizon, px, int(H2 * 0.14)], fill=(*near, 255), width=5 * SS)
        gl = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        ImageDraw.Draw(gl).ellipse([px - 40 * SS, int(H2 * 0.1) - 30 * SS, px + 40 * SS, int(H2 * 0.1) + 30 * SS],
                                   fill=(*accent, 200))
        base.alpha_composite(gl.filter(ImageFilter.GaussianBlur(30 * SS)))
    d.arc([cx - 60 * SS, horizon - 8 * SS, cx + 60 * SS, horizon + 40 * SS], 180, 360,
          fill=(*_lerp(near, accent, 0.3), 200), width=3 * SS)
    focal = _pick_icon(a)
    if focal not in ("trophy", "medal", "ball-football", "ball-basketball", "ball-tennis", "ball-volleyball"):
        focal = "ball-football"
    _silhouette(base, focal, int(H2 * 0.2), int(W2 * 0.6), horizon + int(H2 * 0.06),
                accent, rng, glow=True, accent=accent)


def _scene_sea(base, pal, rng, horizon, a):
    sky_top, sky_bot, far, near, accent = pal
    pts = [(0, horizon)]
    x = 0
    while x < W2:                                        # tarm/munti departe
        x += rng.randint(60, 140) * SS
        pts.append((x, horizon - rng.randint(20, 90) * SS))
    pts += [(W2, horizon), (0, horizon)]
    land = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ImageDraw.Draw(land).polygon(pts, fill=(*_lerp(far, sky_bot, 0.3), 255))
    base.alpha_composite(land.filter(ImageFilter.GaussianBlur(2 * SS)))
    sea = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ImageDraw.Draw(sea).rectangle([0, horizon, W2, H2], fill=(*_lerp(near, accent, 0.12), 255))
    base.alpha_composite(sea)
    d = ImageDraw.Draw(base)
    for i in range(14):                                  # reflexii pe apa
        yy = horizon + int((i + 1) ** 1.5 * 3 * SS)
        if yy > H2:
            break
        d.line([int(W2 * rng.uniform(0.2, 0.5)), yy, int(W2 * rng.uniform(0.5, 0.8)), yy],
               fill=(*_lerp(accent, near, 0.4), 120), width=2 * SS)
    _silhouette(base, "ship", int(H2 * 0.16), int(W2 * rng.uniform(0.35, 0.7)), horizon + int(H2 * 0.16), near, rng)
    _silhouette(base, "plane", int(H2 * 0.1), int(W2 * rng.uniform(0.15, 0.4)), int(horizon * 0.5),
                _lerp(far, near, 0.5), rng)


_GRAIN = None
def _grain():
    global _GRAIN
    if _GRAIN is None:
        _GRAIN = Image.effect_noise((W2, H2), 20).convert("RGB")
    return _GRAIN


_VIGN = None
def _vignette():
    global _VIGN
    if _VIGN is None:
        m = Image.new("L", (W2 // 3, H2 // 3), 0)
        ImageDraw.Draw(m).ellipse([-W2 // 12, -H2 // 12, W2 // 3 + W2 // 12, H2 // 3 + H2 // 12], fill=255)
        _VIGN = m.filter(ImageFilter.GaussianBlur(80)).resize((W2, H2), Image.BILINEAR)
    return _VIGN


def _compose_scene(a: dict):
    rng = random.Random(a.get("title") or "x")
    cat = a.get("category", "general")
    pal = PAL.get(cat, PAL["general"])
    horizon = int(H2 * rng.uniform(0.6, 0.72))
    img = _sun(_sky(pal[0], pal[1], horizon), pal[4], rng, horizon).convert("RGBA")
    if cat == "sport":
        _scene_stadium(img, pal, rng, horizon, a)
    elif cat == "extern":
        _scene_sea(img, pal, rng, horizon, a)
    else:
        _scene_city(img, pal, rng, horizon, a)
    img = img.convert("RGB")
    return _frame(img)


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
