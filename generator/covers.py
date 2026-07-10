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
import colorsys
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


# ---- primitive de desen pentru scene tematice ------------------------------
def _house(d, x, by, w, wall, roof):
    h = w * 0.8
    d.rectangle([x - w / 2, by - h, x + w / 2, by], fill=wall)
    d.polygon([(x - w * .62, by - h), (x + w * .62, by - h), (x, by - h * 1.7)], fill=roof)
    d.rectangle([x - w * .12, by - h * .45, x + w * .12, by], fill=roof)


def _cloud(bs, cx, cy, w, col, a=235):
    lay = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    for dx, dy, r in [(-.4, .1, .5), (0, -.1, .62), (.4, .08, .52), (0, .28, .7)]:
        dd.ellipse([cx + dx * w - r * w / 2, cy + dy * w - r * w / 2,
                    cx + dx * w + r * w / 2, cy + dy * w + r * w / 2], fill=(*col, a))
    bs.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2 * SS)))


def _water(bs, y, col, rng):
    lay = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    dd.rectangle([0, y, W2, H2], fill=(*col, 235))
    for i in range(12):
        yy = y + i * (H2 - y) / 12
        dd.line([rng.uniform(0, W2 * .4), yy, rng.uniform(W2 * .5, W2), yy], fill=(255, 255, 255, 60), width=SS)
    bs.alpha_composite(lay)


def _streaks(d, col, rng, n, dx, dy, a=150):
    for _ in range(n):
        x, y = rng.uniform(0, W2), rng.uniform(0, H2)
        d.line([x, y, x + dx, y + dy], fill=(*col, a), width=SS)


def _mountains(bs, horizon, col, rng, amp=110):
    pts = [(0, horizon)]
    x = 0
    while x < W2:
        x += rng.randint(70, 150) * SS
        pts.append((x, horizon - rng.randint(24, amp) * SS))
    pts += [(W2, horizon), (0, horizon)]
    lay = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ImageDraw.Draw(lay).polygon(pts, fill=(*col, 255))
    bs.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2 * SS)))


def _flag(d, x, by, h, cloth):
    d.line([x, by, x, by - h], fill=(90, 82, 72), width=3 * SS)
    d.polygon([(x, by - h), (x + h * .5, by - h * .86), (x, by - h * .72)], fill=cloth)


def _chart(d, box, col, rng, up):
    x0, y0, x1, y1 = box
    n, v, pts = 6, (.2 if up else .85), []
    for i in range(n + 1):
        v = min(.95, max(.05, v + rng.uniform(-.12, .24) * (1 if up else -1)))
        pts.append((x0 + (x1 - x0) * i / n, y1 - (y1 - y0) * v))
    d.line(pts, fill=col, width=6 * SS, joint="curve")
    d.line([x0, y1, x1, y1], fill=col, width=4 * SS)
    ax, ay, s = pts[-1][0], pts[-1][1], 18 * SS
    d.polygon([(ax, ay - s), (ax + s, ay), (ax, ay + s)] if up else [(ax - s, ay), (ax, ay - s), (ax, ay + s)], fill=col)


def _columns(d, cx, by, w, h, col):
    d.polygon([(cx - w / 2 - 8 * SS, by - h), (cx + w / 2 + 8 * SS, by - h), (cx, by - h * 1.32)], fill=col)
    d.rectangle([cx - w / 2, by - h, cx + w / 2, by - h * .9], fill=col)
    for i in range(5):
        x = cx - w / 2 + w * (0.08 + i * 0.21)
        d.rectangle([x, by - h * .9, x + w * .08, by], fill=col)
    d.rectangle([cx - w / 2 - 10 * SS, by, cx + w / 2 + 10 * SS, by + 10 * SS], fill=col)


# ---- scene tematice: fiecare reflecta subiectul articolului -----------------
_MOODS = {
    "light": ((206, 222, 238), (248, 246, 240), (255, 224, 150)),
    "storm": ((150, 158, 172), (206, 210, 216), (210, 214, 220)),
    "fire":  ((70, 46, 54), (226, 120, 60), (255, 180, 90)),
    "heat":  ((250, 208, 150), (252, 240, 214), (255, 236, 170)),
    "snow":  ((214, 224, 238), (246, 249, 252), (240, 246, 252)),
    "night": ((36, 42, 66), (90, 96, 130), (240, 226, 180)),
}


def _mood_base(mood, rng):
    top, bot, sun = _MOODS[mood]
    horizon = int(H2 * 0.62)
    return _sun(_sky(top, bot, horizon), sun, rng, horizon).convert("RGBA")


def _t_flood(bs, rng, a):
    hz = int(H2 * 0.6)
    _cloud(bs, W2 * .3, H2 * .19, W2 * .3, (150, 158, 170))
    _cloud(bs, W2 * .72, H2 * .16, W2 * .26, (168, 174, 186))
    d = ImageDraw.Draw(bs)
    _house(d, W2 * .3, hz + H2 * .12, W2 * .16, (152, 122, 96), (112, 72, 58))
    _house(d, W2 * .6, hz + H2 * .06, W2 * .12, (142, 112, 90), (104, 66, 54))
    _water(bs, hz + int(H2 * .05), (70, 120, 150), rng)
    _silhouette(bs, "droplet", int(H2 * .19), int(W2 * .8), hz + int(H2 * .03), (60, 120, 156), rng, glow=True, accent=(120, 180, 210))
    _streaks(ImageDraw.Draw(bs), (205, 214, 224), rng, 150, -8 * SS, 20 * SS)


def _t_fire(bs, rng, a):
    hz = int(H2 * .64)
    _cloud(bs, W2 * .4, H2 * .2, W2 * .4, (60, 54, 60))
    _cloud(bs, W2 * .7, H2 * .14, W2 * .3, (80, 70, 74))
    _ground(bs, (60, 44, 40), hz)
    _skyline(bs, (46, 36, 40), rng, hz, .16, .34, True, (255, 150, 60))
    d = ImageDraw.Draw(bs)
    for _ in range(50):
        x, h = rng.uniform(0, W2), rng.uniform(30, 90) * SS
        d.polygon([(x, hz), (x - 14 * SS, hz - h * .6), (x, hz - h), (x + 14 * SS, hz - h * .6)],
                  fill=(rng.randint(230, 255), rng.randint(120, 180), 40))
    _silhouette(bs, "firetruck", int(H2 * .18), int(W2 * .7), hz, (40, 34, 36), rng, glow=True, accent=(255, 150, 60))


def _t_heat(bs, rng, a):
    hz = int(H2 * .7)
    _ground(bs, (222, 196, 150), hz)
    d = ImageDraw.Draw(bs)
    for _ in range(60):
        x, y = rng.uniform(0, W2), rng.uniform(hz, H2)
        d.line([x, y, x + rng.uniform(-40, 40) * SS, y + rng.uniform(-10, 20) * SS], fill=(196, 168, 120), width=SS)
    _silhouette(bs, "sun", int(H2 * .26), int(W2 * .72), hz, (210, 140, 60), rng, glow=True, accent=(255, 190, 90))
    _crowd(bs, hz + int(H2 * .06), (120, 100, 70), rng, n=10)


def _t_snow(bs, rng, a):
    hz = int(H2 * .66)
    _ground(bs, (238, 242, 248), hz)
    d = ImageDraw.Draw(bs)
    for x in (W2 * .28, W2 * .6):
        _house(d, x, hz + H2 * .02, W2 * .14, (150, 158, 176), (110, 120, 140))
    d.ellipse([0, hz - 8 * SS, W2, hz + 30 * SS], fill=(248, 250, 253))
    for _ in range(160):
        x, y, r = rng.uniform(0, W2), rng.uniform(0, H2), rng.uniform(2, 4) * SS
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 220))
    _silhouette(bs, "snowflake", int(H2 * .2), int(W2 * .78), hz, (120, 150, 190), rng, glow=True, accent=(200, 220, 240))


def _t_military(bs, rng, a):
    hz = int(H2 * .62)
    _mountains(bs, hz, (150, 150, 168), rng)
    _ground(bs, (120, 118, 110), hz)
    d = ImageDraw.Draw(bs)
    x, w = W2 * .68, W2 * .2
    h, gy = w * .42, hz + H2 * .22
    d.rounded_rectangle([x - w / 2, gy - h, x + w / 2, gy - h * .35], radius=h * .3, fill=(78, 84, 74))
    d.rounded_rectangle([x - w * .22, gy - h * 1.5, x + w * .22, gy - h], radius=h * .2, fill=(78, 84, 74))
    d.line([x + w * .1, gy - h * 1.3, x + w * .8, gy - h * 1.45], fill=(78, 84, 74), width=5 * SS)
    d.rounded_rectangle([x - w / 2, gy - h * .4, x + w / 2, gy], radius=h * .3, fill=(78, 84, 74))
    _flag(d, W2 * .16, hz + H2 * .05, H2 * .28, (60, 90, 170))
    _flag(d, W2 * .23, hz + H2 * .05, H2 * .28, (196, 70, 60))
    _crowd(bs, hz + int(H2 * .16), (54, 60, 66), rng, n=14, h=int(H2 * .12))
    _silhouette(bs, "plane", int(H2 * .11), int(W2 * .84), int(hz * .5), (70, 76, 86), rng)


def _t_diplomacy(bs, rng, a):
    hz = int(H2 * .66)
    _ground(bs, (208, 210, 216), hz)
    d = ImageDraw.Draw(bs)
    _columns(d, W2 * .5, hz, W2 * .34, H2 * .34, (196, 198, 206))
    cols = [(60, 90, 170), (196, 70, 60), (70, 150, 96), (210, 180, 60)]
    for i in range(6):
        _flag(d, W2 * (.12 + i * .13), hz, H2 * .16, cols[i % 4])
    _crowd(bs, hz + int(H2 * .05), (70, 74, 84), rng, n=16)
    _silhouette(bs, "globe", int(H2 * .14), int(W2 * .8), hz, (90, 130, 170), rng, glow=True, accent=(150, 190, 220))


def _t_economy(bs, rng, a, up):
    hz = int(H2 * .66)
    _skyline(bs, (150, 162, 150), rng, hz, .12, .3, False, GOLD)
    _ground(bs, (210, 206, 196), hz)
    _skyline(bs, (96, 128, 110), rng, hz, .16, .34, True, GOLD)
    d = ImageDraw.Draw(bs)
    _chart(d, (W2 * .12, H2 * .16, W2 * .6, hz - H2 * .04), (60, 150, 90) if up else (201, 100, 52), rng, up)
    _silhouette(bs, "gas-station", int(H2 * .2), int(W2 * .8), hz, (150, 120, 80), rng, glow=True, accent=GOLD)
    _crowd(bs, hz + int(H2 * .06), (60, 64, 60), rng, n=18)


def _t_justice(bs, rng, a):
    hz = int(H2 * .68)
    _ground(bs, (212, 210, 204), hz)
    d = ImageDraw.Draw(bs)
    _columns(d, W2 * .42, hz, W2 * .4, H2 * .4, (200, 194, 182))
    _silhouette(bs, "gavel", int(H2 * .24), int(W2 * .76), hz, (150, 110, 60), rng, glow=True, accent=GOLD)
    _crowd(bs, hz + int(H2 * .05), (74, 70, 66), rng, n=14)


def _t_politics(bs, rng, a, protest):
    hz = int(H2 * .64)
    _skyline(bs, (150, 160, 178), rng, hz, .12, .28, False, GOLD)
    _ground(bs, (206, 208, 214), hz)
    _silhouette(bs, "building-monument", int(H2 * .3), int(W2 * .5), hz, (110, 120, 150), rng, glow=True, accent=GOLD)
    d = ImageDraw.Draw(bs)
    if protest:
        for i in range(6):
            _flag(d, W2 * (.1 + i * .14), hz + H2 * .02, H2 * .14, (196, 70, 60) if i % 2 else (60, 90, 170))
    _crowd(bs, hz + int(H2 * .05), (60, 62, 70), rng, n=36 if protest else 18)


def _t_health(bs, rng, a, virus):
    hz = int(H2 * .66)
    _ground(bs, (224, 230, 234), hz)
    d = ImageDraw.Draw(bs)
    _skyline(bs, (170, 186, 196), rng, hz, .12, .26, False, (90, 170, 190))
    d.rectangle([W2 * .36, hz - H2 * .34, W2 * .6, hz], fill=(226, 232, 236))
    d.rectangle([W2 * .47, hz - H2 * .28, W2 * .49, hz - H2 * .16], fill=(210, 70, 70))
    d.rectangle([W2 * .44, hz - H2 * .23, W2 * .52, hz - H2 * .21], fill=(210, 70, 70))
    _silhouette(bs, "virus" if virus else "stethoscope", int(H2 * .2), int(W2 * .76), hz, (90, 150, 170), rng, glow=True, accent=(120, 190, 200))
    _crowd(bs, hz + int(H2 * .05), (80, 90, 96), rng, n=14)


def _t_transport(bs, rng, a, kind):
    hz = int(H2 * .66)
    _ground(bs, (200, 200, 204), hz)
    d = ImageDraw.Draw(bs)
    _skyline(bs, (176, 184, 176), rng, hz, .1, .24, False, GOLD)
    if kind == "plane":
        for i in range(6):
            d.line([W2 * (.1 + i * .14), hz + H2 * .14, W2 * (.16 + i * .14), hz + H2 * .14], fill=(230, 230, 234), width=4 * SS)
        _silhouette(bs, "plane", int(H2 * .22), int(W2 * .6), hz + int(H2 * .04), (90, 100, 120), rng, glow=True, accent=(150, 190, 220))
    elif kind == "train":
        d.line([0, hz + H2 * .16, W2, hz + H2 * .16], fill=(120, 120, 124), width=4 * SS)
        _silhouette(bs, "train", int(H2 * .2), int(W2 * .55), hz + int(H2 * .16), (90, 110, 130), rng, glow=True, accent=GOLD)
    else:
        d.line([0, hz + H2 * .2, W2, hz + H2 * .2], fill=(150, 150, 154), width=10 * SS)
        _silhouette(bs, "car", int(H2 * .16), int(W2 * .55), hz + int(H2 * .2), (90, 100, 120), rng, glow=True, accent=GOLD)
    _crowd(bs, hz + int(H2 * .05), (70, 74, 82), rng, n=10)


def _t_tech(bs, rng, a):
    hz = int(H2 * .66)
    _ground(bs, _lerp((28, 24, 56), (255, 255, 255), .82), hz)
    d = ImageDraw.Draw(bs)
    for gy in range(int(hz + H2 * .04), H2, 44 * SS):
        d.line([0, gy, W2, gy], fill=(150, 160, 200), width=SS)
    for gx in range(0, W2, 60 * SS):
        d.line([gx, hz, gx, H2], fill=(160, 170, 205), width=SS)
    _skyline(bs, (140, 130, 190), rng, hz, .14, .3, True, (120, 210, 225))
    _silhouette(bs, "cpu", int(H2 * .24), int(W2 * .68), hz, (90, 80, 150), rng, glow=True, accent=(120, 210, 225))
    _crowd(bs, hz + int(H2 * .05), (90, 84, 130), rng, n=12)


def _t_environment(bs, rng, a):
    hz = int(H2 * .64)
    _mountains(bs, hz, (150, 178, 160), rng, 130)
    _ground(bs, (150, 176, 120), hz)
    d = ImageDraw.Draw(bs)
    for _ in range(14):
        x, th = rng.uniform(W2 * .05, W2 * .95), rng.uniform(.1, .18) * H2
        d.rectangle([x - 4 * SS, hz - th * .4, x + 4 * SS, hz], fill=(90, 70, 50))
        d.ellipse([x - th * .4, hz - th, x + th * .4, hz - th * .2], fill=(70, 140, 80))
    _silhouette(bs, "trees", int(H2 * .22), int(W2 * .74), hz, (60, 120, 70), rng, glow=True, accent=(140, 200, 120))


def _t_sport(bs, rng, a):
    _scene_stadium(bs, PAL["sport"], rng, int(H2 * .62), a)


# tema detectata din titlu -> (mood cer, builder). Ordinea conteaza (primul care se potriveste).
_THEMES = [
    (r"inundat|viitur|revars", "storm", _t_flood),
    (r"incendi|flacar|arde|pojar|pompier", "fire", _t_fire),
    (r"canicul|arsita|temperatur|seceta", "heat", _t_heat),
    (r"ninso|zapad|viscol|\bger\b", "snow", _t_snow),
    (r"nato|militar|armat|razboi|ofensiv|trupe|tanc|\bfront\b|frontier", "light", _t_military),
    (r"diploma|summit|\bue\b|uniunea europ|bruxelles|ambasad|natiunile unite|\bonu\b", "light", _t_diplomacy),
    (r"inflat|pret|scump|buget|bursa|econom|salari|pensi|\btva\b|impozit", "light",
     lambda b, r, a: _t_economy(b, r, a, up=not re.search(r"scad|ieftin|incetin|scazu|reduce", _norm(a.get("title", ""))))),
    (r"energie|\bgaz|petrol|carburant|benzin|curent electric", "light", lambda b, r, a: _t_economy(b, r, a, up=True)),
    (r"instanta|tribunal|judecat|proces|condamn|\blege\b|justiti|dosar|procuror|achit", "light", _t_justice),
    (r"protest|miting|grev|\bmars\b|manifestat", "light", lambda b, r, a: _t_politics(b, r, a, protest=True)),
    (r"guvern|parlament|coalit|ministr|presedint|alegeri|senat|deputat|referendum", "light", lambda b, r, a: _t_politics(b, r, a, protest=False)),
    (r"spital|medic|sanatat|vaccin|boala|cancer|gripa|epidemi|pacient", "light",
     lambda b, r, a: _t_health(b, r, a, virus=bool(re.search(r"virus|covid|gripa|epidemi", _norm(a.get("title", "")))))),
    (r"avion|aeroport|zbor|aerian", "light", lambda b, r, a: _t_transport(b, r, a, "plane")),
    (r"tren|feroviar|\bcfr\b|metrou|cale ferata", "light", lambda b, r, a: _t_transport(b, r, a, "train")),
    (r"masina|autoturism|rutier|sofer|autostrad|camion|accident", "light", lambda b, r, a: _t_transport(b, r, a, "car")),
    (r"inteligenta artif|\bai\b|\bcip\b|tehnolog|internet|robot|aplicati|software|algoritm", "night", _t_tech),
    (r"padur|mediu|clima|polua|emisii|reciclar|impadur", "light", _t_environment),
    (r"fotbal|meci|\bgol\b|campion|\bliga\b|tenis|baschet|handbal|stadion|olimpi|antrenor", "light", _t_sport),
]


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
