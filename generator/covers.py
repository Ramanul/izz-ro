"""Coperti editoriale per articol (og:image) — v3 'dark editorial'.

Fundatie profesionista, 100% legala si offline:
- tipografie: Playfair Display 800 (OFL, fontul masthead-ului site-ului)
- iconografie: Tabler Icons (MIT), 122 pictograme desenate de designeri,
  pre-rasterizate in generator/assets/icons/ si colorate in auriu la compunere
- compozitie: fond ink cu gradient, arta generativa din arce phi translucide
  (stil distinct per categorie), 'bokeh' Fibonacci, icoana cu halo difuz --
  TOATE variate din seed-ul articolului: doua stiri cu aceeasi icoana au
  compozitii vizibil diferite
- selectie: icoana aleasa de AI (campul 'icon', zero apeluri noi) sau, in lipsa,
  harta de cuvinte-cheie; fallback estetic: monograma Playfair aurie
- siguranta: orice eroare -> False, articolul pastreaza og-image static
"""
import hashlib
import math
import os
import re

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    Image = None

INK_TOP, INK_BOT = (26, 28, 34), (13, 14, 19)
PAPER = "#f6f7f9"
GOLD = (201, 162, 39)
GOLD_HEX, GOLD_STRONG = "#c9a227", "#8b6918"
MUTED = "#8b8fa0"                          # text secundar pe fond inchis (AA)
PHI = 1.618
W, H = 1200, 630
SS = 2
W2, H2 = W * SS, H * SS

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


# ---- selectia icoanei ------------------------------------------------------
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
# rotatie seeded per categorie: cand niciun cuvant-cheie nu decide, default-ul
# NU mai e mereu acelasi (feedback owner: "la sport aceeasi pictograma")
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


# ---- straturi compozitionale (toate primesc seed) ---------------------------
_BASE_GRADIENT = None


def _gradient_base():
    """Fundalul cu gradient e identic pentru toate copertile -> se deseneaza o
    singura data (1260 de linii) si se copiaza; economiseste ~40% din randare."""
    global _BASE_GRADIENT
    if _BASE_GRADIENT is None:
        img = Image.new("RGB", (W2, H2), tuple(INK_BOT))
        d = ImageDraw.Draw(img)
        for y in range(H2):
            t = y / H2
            col = tuple(int(INK_TOP[i] + (INK_BOT[i] - INK_TOP[i]) * t) for i in range(3))
            d.line([(0, y), (W2, y)], fill=col)
        _BASE_GRADIENT = img
    return _BASE_GRADIENT.copy()


def _bokeh(do, s):
    """Discuri Fibonacci translucide — caldura si adancime, pozitii din seed."""
    fib = [21, 34, 55, 89, 144]
    for i in range(5):
        r = fib[i] * SS * (0.8 + s[i] / 255 * 0.7)
        x = W2 * (0.52 + (s[i + 5] / 255) * 0.45)
        y = H2 * (0.08 + (s[i + 10] / 255) * 0.84)
        a = 10 + int(s[i + 3] / 255 * 22)
        do.ellipse([x - r, y - r, x + r, y + r], fill=(*GOLD, a))


def _arcs_politic(do, s):
    cx = W2 * (0.78 + s[0] / 255 * 0.08)
    for i, (k, al, w) in enumerate([(1.15, 40, 20), (0.86, 66, 12), (0.6, 30, 26)]):
        r = H2 * k / 2
        cy = H2 * (0.5 + (s[i] / 255 - 0.5) * 0.2)
        do.arc([cx - r, cy - r, cx + r, cy + r], 120, 420, fill=(*GOLD, al), width=w * SS)


def _arcs_economic(do, s):
    for i in range(3):
        r = H2 * (0.34 + i * 0.16)
        cx = W2 * (0.62 + i * 0.1) + (s[i] / 255 - 0.5) * 60 * SS
        cy = H2 * (1.06 - i * 0.16)
        do.arc([cx - r, cy - r, cx + r, cy + r], 180, 305, fill=(*GOLD, 62 - i * 14), width=(16 - i * 3) * SS)


def _arcs_extern(do, s):
    cx, cy = W2 * (0.82 + s[0] / 255 * 0.06), H2 * 0.5
    for i, k in enumerate((0.95, 0.66, 0.4)):
        r = H2 * k
        do.ellipse([cx - r * 0.42, cy - r, cx + r * 0.42, cy + r],
                   outline=(*GOLD, 46 + i * 14), width=(6 + i * 3) * SS)
    do.ellipse([cx - H2 * 0.95 * 1.02, cy - H2 * 0.95, cx + H2 * 0.95 * 1.02, cy + H2 * 0.95],
               outline=(*GOLD, 26), width=4 * SS)


def _arcs_sport(do, s):
    ang = -34 + (s[0] / 255 - 0.5) * 16
    for i in range(3):
        off = i * 46 * SS
        x0 = W2 * 0.5 + off
        y0 = H2 * 1.1
        x1 = x0 + math.cos(math.radians(ang)) * H2 * 1.15
        y1 = y0 + math.sin(math.radians(ang)) * H2 * 1.15
        do.line([x0, y0, x1, y1], fill=(*GOLD, 78 - i * 24), width=(15 - i * 4) * SS)
    r = H2 * 0.55
    do.arc([W2 * 0.6 - r, H2 * 0.65 - r, W2 * 0.6 + r, H2 * 0.65 + r], 200, 320,
           fill=(*GOLD, 40), width=10 * SS)


def _arcs_tech(do, s):
    step = 64 * SS
    ox = int(s[0] / 255 * step)
    for x in range(int(W2 * 0.55) + ox, W2, step):
        for y in range(step // 2, H2, step):
            do.ellipse([x - 2 * SS, y - 2 * SS, x + 2 * SS, y + 2 * SS], fill=(*GOLD, 46))
    r = H2 * 0.52
    cx, cy = W2 * 0.8, H2 * (0.42 + s[1] / 255 * 0.2)
    do.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*GOLD, 44), width=5 * SS)


def _arcs_general(do, s):
    x, y = W2 * (0.98 + s[0] / 255 * 0.04), H2 * (0.96 + s[1] / 255 * 0.06)
    r = H2 * 0.78
    for i in range(4):
        do.arc([x - r, y - r, x + r, y + r], 150, 300, fill=(*GOLD, 30 + i * 12),
               width=(5 + i * 2) * SS)
        r /= PHI


_ARCS = {"politic": _arcs_politic, "economic": _arcs_economic, "extern": _arcs_extern,
         "sport": _arcs_sport, "tech": _arcs_tech, "general": _arcs_general}


def _place_icon(base, name: str, s, cxf: float = 0.70):
    src = _icon_img(name)
    if src is None:
        return False
    size = int(W2 * (0.21 + s[15] / 255 * 0.05))
    icon = src.resize((size, size), Image.LANCZOS)
    alpha = icon.split()[3]
    gold_layer = Image.new("RGBA", icon.size, (*GOLD, 255))
    tinted = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    tinted.paste(gold_layer, (0, 0), alpha)
    # halo difuz sub icoana
    q = 4                                            # glow la 1/4 rezolutie: blur ~16x mai ieftin
    gs = size * 2 // q
    glow_small = Image.new("RGBA", (gs, gs), (0, 0, 0, 0))
    ga = alpha.resize((gs // 2, gs // 2)).point(lambda v: int(v * 0.55))
    glow_small.paste(Image.new("RGBA", (gs // 2, gs // 2), (*GOLD, 255)), (gs // 4, gs // 4), ga)
    glow_small = glow_small.filter(ImageFilter.GaussianBlur(26 * SS // q))
    glow = glow_small.resize((size * 2, size * 2), Image.BILINEAR)
    x = int(W2 * (cxf + (s[16] / 255 - 0.5) * 0.06))
    y = int(H2 / PHI * (1.0 + (s[17] / 255 - 0.5) * 0.22))
    base.paste(glow, (x - size, y - size), glow)
    base.paste(tinted, (x - size // 2, y - size // 2), tinted)
    return True


def _monogram(base, letter: str, s, cxf: float = 0.72):
    f = _font("display", int(H2 * 0.62))
    layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = int(W2 * (cxf + (s[16] / 255 - 0.5) * 0.05))
    y = int(H2 / PHI)
    d.text((x, y), letter.upper(), font=f, fill=(*GOLD, 235), anchor="mm")
    glow = layer.filter(ImageFilter.GaussianBlur(30 * SS))
    base.paste(glow, (0, 0), glow.point(lambda v: int(v * 0.5)))
    base.paste(layer, (0, 0), layer)


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


def _compose(a: dict, s, with_text: bool):
    base = _gradient_base()
    over = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    do = ImageDraw.Draw(over)
    _bokeh(do, s)
    _ARCS.get(a.get("category", ""), _arcs_general)(do, s)
    base.paste(over, (0, 0), over)

    cxf = 0.70 if with_text else 0.5      # arta de site: icoana centrata (nu e text langa ea)
    icon = _pick_icon(a)
    if icon:
        _place_icon(base, icon, s, cxf)
    else:
        ents = a.get("entities") or []
        _monogram(base, (ents[0] if ents else a.get("title") or "I")[0], s, cxf + 0.02)

    if not with_text:
        return base

    d = ImageDraw.Draw(base)
    mono = _font("mono", 26 * SS)
    mono_s = _font("mono", 20 * SS)
    display = _font("display", 62 * SS)
    d.text((56 * SS, 48 * SS), (a.get("category") or "știri").upper(),
           font=mono, fill=GOLD_HEX)
    rule_w = int((W2 / PHI - 112 * SS) / PHI)
    d.line([56 * SS, 96 * SS, 56 * SS + rule_w, 96 * SS], fill=GOLD_HEX, width=2 * SS)
    y = 128 * SS
    for ln in _wrap(d, a.get("title", ""), display, int(W2 / PHI) - 88 * SS):
        d.text((56 * SS, y), ln, font=display, fill=PAPER)
        y += 82 * SS
    d.text((56 * SS, H2 - 66 * SS), "IZZ.ro — Informația Zero Zgomot",
           font=mono, fill=MUTED)
    seed = hashlib.sha1((a.get("title") or "").encode()).digest()
    d.text((W2 - 34 * SS, H2 - 34 * SS), f"Nº {seed.hex()[:6]}",
           font=mono_s, fill=GOLD_STRONG, anchor="rs")
    return base


def _save(base, path: str, size) -> None:
    img = base.resize(size, Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=84)


def generate(a: dict, path: str) -> bool:
    """Coperta de SHARE (og:image, cu titlu) la `path`. False la orice problema."""
    if Image is None:
        return False
    try:
        seed = hashlib.sha1((a.get("title") or "").encode()).digest()
        _save(_compose(a, list(seed), True), path, (W, H))
        return True
    except Exception:
        return False


ART_W, ART_H = 960, 504


def generate_art(a: dict, path: str) -> bool:
    """Varianta de SITE (fara text -- titlul e deja pe pagina): aceeasi arta
    generativa cu icoana centrata, 960x504. False la orice problema."""
    if Image is None:
        return False
    try:
        seed = hashlib.sha1((a.get("title") or "").encode()).digest()
        _save(_compose(a, list(seed), False), path, (ART_W, ART_H))
        return True
    except Exception:
        return False
