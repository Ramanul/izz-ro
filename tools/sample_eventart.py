"""MOSTRE (nu productie): trei coperte "imaginea evenimentului din datele lui".

Demonstreaza clasa B din propunerea 2026-09-03: coperta = harta/diagrama a
faptelor evenimentului, nu poza de agentie. Date reale:
  S1  harta Nepal — epicentrul cutremurului declansator (USGS M5.2, 26.08),
      fundal OpenStreetMap (© OpenStreetMap contributors);
  S2  prognoza Sibiu 7 zile (open-meteo.com);
  S3  seria bilanțului viiturii Nepal 26–30 aug, extrasa din articolele noastre.

Design: paleta si tipografia din static/styles.css prin htmlart.py (§8):
hârtie/cerneala/auriu, Playfair Display 800. Randare PIL (sample-grade;
productia ar rula prin HTML+Chromium ca gen_images).
"""
from __future__ import annotations

import math
import os
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 960, 504
INK, PAPER, GOLD, GOLD_STRONG, GOLD_WASH = (
    "#15171c", "#f6f7f9", "#c9a227", "#8b6918", "#faf5e6")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                      "generator", "assets", "PlayfairDisplay_800ExtraBold.ttf")
UA = "izzro-samples/0.1 (editorial demo; contact: contact@izz.ro)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "shots", "mostre-2026-09-03")

_font_cache: dict[int, ImageFont.FreeTypeFont] = {}


def font(px: int) -> ImageFont.FreeTypeFont:
    if px not in _font_cache:
        _font_cache[px] = ImageFont.truetype(ASSETS, px)
    return _font_cache[px]


def text_spaced(draw: ImageDraw.ImageDraw, xy, s: str, px: int, fill,
                spacing: int = 5, anchor_right: bool = False) -> int:
    """Majuscule cu litere depărtate (echivalentul .eticheta din htmlart)."""
    if anchor_right:
        total = sum(draw.textlength(c, font=font(px)) for c in s) + spacing * (len(s) - 1)
        xy = (xy[0] - total, xy[1])
    x, y = xy
    for c in s:
        draw.text((x, y), c, font=font(px), fill=fill)
        x += draw.textlength(c, font=font(px)) + spacing
    return x


def marca(draw: ImageDraw.ImageDraw, xy, fill, right: bool = False):
    text_spaced(draw, xy, "izz.ro", 13, fill, 3, anchor_right=right)


def filet(draw: ImageDraw.ImageDraw, x, y, w: int, color=GOLD):
    draw.rectangle([x, y, x + w, y + 3], fill=color)


# ---------------------------------------------------------------- harta OSM --
def deg2num(lat: float, lon: float, z: int) -> tuple[int, int]:
    lat_r, n = math.radians(lat), 2 ** z
    return int((lon + 180) / 360 * n), int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)


def num2pixel(lat: float, lon: float, z: int, x0: int, y0: int) -> tuple[float, float]:
    n = 2 ** z
    xt = (lon + 180) / 360 * n
    lat_r = math.radians(lat)
    yt = (1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n
    return (xt - x0) * 256, (yt - y0) * 256


def fetch_map(lat: float, lon: float, z: int, cols: int, rows: int) -> Image.Image:
    x0, y0 = deg2num(lat, lon, z)
    x0 -= cols // 2
    y0 -= rows // 2
    img = Image.new("RGB", (cols * 256, rows * 256))
    for dx in range(cols):
        for dy in range(rows):
            url = f"https://tile.openstreetmap.org/{z}/{x0 + dx}/{y0 + dy}.png"
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            tile = Image.open(__import__("io").BytesIO(urllib.request.urlopen(req, timeout=20).read()))
            img.paste(tile, (dx * 256, dy * 256))
    # duotone in paleta site-ului: alb -> hârtie, negru -> cenusa de cerneala
    return ImageOps.colorize(img.convert("L"), black="#3a3d44", white=PAPER), (x0, y0)


def sample_nepal_harta() -> Image.Image:
    LAT, LON, Z = 28.271, 85.515, 10
    mapa, (x0, y0) = fetch_map(LAT, LON, Z, 4, 3)          # 1024x768
    mx, my = num2pixel(LAT, LON, Z, x0, y0)
    left, top = int(mx) - 620, int(my) - 210                # marcatorul la ~2/3 dreapta
    img = mapa.crop((left, top, left + W, top + H)).convert("RGBA")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for r, alpha in ((46, 60), (30, 110), (16, 200)):       # inele concentrice
        d.ellipse([mx - left - r, my - top - r, mx - left + r, my - top + r],
                  outline=(*tuple(int(GOLD[i:i + 2], 16) for i in (1, 3, 5)), alpha), width=3)
    d.ellipse([mx - left - 7, my - top - 7, mx - left + 7, my - top + 7], fill=GOLD,
              outline=PAPER, width=2)
    # panou stanga
    d.rectangle([0, 0, 300, H], fill=GOLD_WASH)
    d.rectangle([300, 0, 303, H], fill=GOLD)
    d = ImageDraw.Draw(img)
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    filet(d, 56, 56, 120)
    text_spaced(d, (56, 132), "NEPAL", 44, INK)
    text_spaced(d, (56, 186), "EXTERNE", 15, INK)
    d.text((56, 226), "M 5,2", font=font(78), fill=GOLD_STRONG)
    d.text((56, 316), "cutremurul care a declanșat", font=font(19), fill=INK)
    d.text((56, 342), "viitura de la granița Nepal–Tibet", font=font(19), fill=INK)
    d.text((56, 368), "26 august 2026 · epicentru 55 km NV de Kodari", font=font(15), fill="#4a4d55")
    marca(d, (56, H - 64), "#4a4d55")
    text_spaced(d, (W - 20, H - 28), "© OPENSTREETMAP CONTRIBUTORS", 10, "#4a4d55", 1, anchor_right=True)
    return img.convert("RGB")


# ------------------------------------------------------------ prognoza meteo --
def sample_meteo_sibiu() -> Image.Image:
    import json
    url = ("https://api.open-meteo.com/v1/forecast?latitude=45.7983&longitude=24.1256"
           "&daily=temperature_2m_max,temperature_2m_min&timezone=Europe%2FBucharest&forecast_days=7")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    daily = json.load(urllib.request.urlopen(req, timeout=20))["daily"]
    tmax, tmin, days = daily["temperature_2m_max"], daily["temperature_2m_min"], daily["time"]
    zile = ["L", "M", "M", "J", "V", "S", "D"]

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    filet(d, 56, 56, 120)
    text_spaced(d, (56, 78), "SIBIU", 44, INK)
    text_spaced(d, (56, 132), "PROGNOZĂ · 7 ZILE", 15, INK)
    marca(d, (56, H - 64), "#4a4d55")

    x0, x1, y0, y1 = 350, 905, 120, 400
    lo, hi = min(tmin) - 2, max(tmax) + 2
    bw = (x1 - x0) / 7 * 0.52
    for i, (tM, tm, day) in enumerate(zip(tmax, tmin, days)):
        cx = x0 + (i + .5) * (x1 - x0) / 7
        yM = y1 - (tM - lo) / (hi - lo) * (y1 - y0)
        ym = y1 - (tm - lo) / (hi - lo) * (y1 - y0)
        d.rounded_rectangle([cx - bw / 2, yM, cx + bw / 2, ym], 9, fill=GOLD)
        d.text((cx, yM - 34), f"{round(tM)}°", font=font(24), fill=INK, anchor="ma")
        d.text((cx, ym + 8), f"{round(tm)}°", font=font(17), fill="#4a4d55", anchor="ma")
        d.text((cx, y1 + 16), zile[(int(day[8:]) + 1) % 7], font=font(22), fill=INK, anchor="ma")
        d.text((cx, y1 + 44), day[8:], font=font(14), fill="#4a4d55", anchor="ma")
    d.line([x0 - 10, y1 + 4, x1, y1 + 4], fill="#d8d2c0", width=2)
    text_spaced(d, (W - 20, H - 28), "SURSA DATELOR: OPEN-METEO.COM", 10, "#4a4d55", 1, anchor_right=True)
    return img


# ------------------------------------------------------------- seria bilanț --
def sample_bilanț_nepal() -> Image.Image:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    d.rectangle([18, 18, W - 18, H - 18], outline=GOLD, width=1)
    filet(d, 64, 64, 120)
    text_spaced(d, (64, 86), "BILANȚ VIITURĂ", 34, PAPER)
    text_spaced(d, (64, 132), "NEPAL · GRANIȚA CU TIBETUL", 15, PAPER)

    serie = [("26 aug", 160), ("28 aug", 543), ("29 aug", 600), ("30 aug", 800)]
    x0, x1, y0, y1 = 64, 700, 400, 200
    pts = []
    for i, (_, v) in enumerate(serie):
        pts.append((x0 + i * (x1 - x0) / 3, y1 - v / 900 * (y1 - y0)))
    d.polygon(pts + [(x1, y1), (x0, y1)], fill=(201, 162, 39, 38))
    d.line(pts, fill=GOLD, width=4, joint="curve")
    for (x, y), (lbl, v) in zip(pts, serie):
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=GOLD, outline=INK)
        approx = "≈" if v in (600, 800) else ""
        d.text((x, y - 40), f"{approx}{v}", font=font(26), fill=PAPER, anchor="ma")
        d.text((x, y1 + 14), lbl, font=font(15), fill="#9aa0aa", anchor="ma")
    d.text((64, 436), "morți raportați în sintezele izz.ro", font=font(16), fill="#9aa0aa")
    d.text((700, 210), "≈800", font=font(92), fill=GOLD)
    d.text((704, 306), "morți", font=font(24), fill=PAPER)
    d.text((704, 348), "1500+ dispăruți", font=font(17), fill="#9aa0aa")
    marca(d, (W - 40, H - 64), "#9aa0aa", right=True)
    return img


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    jobs = {"nepal-harta": sample_nepal_harta,
            "meteo-sibiu": sample_meteo_sibiu,
            "bilant-nepal": sample_bilanț_nepal}
    names = sys.argv[1:] or list(jobs)
    for name in names:
        img = jobs[name]()
        path = os.path.join(OUT, f"{name}.jpg")
        img.save(path, quality=90)
        print("scris", os.path.normpath(path))
