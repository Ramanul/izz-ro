"""MOSTRE (nu productie): poze de eveniment de pe Wikimedia Commons pt. clusterul
Nepal (viitura 26 aug 2026, declansata de cutremurul M5.2 de langa Kodari).

Nu fabrica potriviri: fiecare poza primeste verdictul EI —
  DE LA EVENIMENT = DateTimeOriginal in fereastra 25 aug - 2 sep 2026;
  ARHIVA DE SUBIECT = relevanta pentru loc/subiect, dar mai veche.
Gate-urile de productie (localities.usable): latime >= 1200, peisaj, licenta
libera (CC0/PD/CC BY/CC BY-SA, fara NC/ND). Verdictul e afisat, nu ascuns.

Iesire: shots/mostre-2026-09-03/commons/ (thumbs) + contact-sheet.html
+ contact-sheet.jpg (grila de verificare rapida).
"""
from __future__ import annotations

import io
import json
import os
import re
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

UA = "izzro-samples/0.1 (editorial demo; contact: contact@izz.ro)"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "shots", "mostre-2026-09-03")
EVENT_WINDOW = ("2026-08-25", "2026-09-02")
QUERIES = ["Kodari", "Nepal flood", "Bhote Koshi", "Sino-Nepal border",
           "Nepal landslide", "Araniko Highway"]
LICENSE_FREE = re.compile(r"^(cc0|cc[ -]?zero|public domain|pd([ -]|$)|"
                          r"copyrighted free use|cc[ -]?by(?![ -]?n[cd]))", re.I)
INK, PAPER, GOLD = "#15171c", "#f6f7f9", "#c9a227"


def api(params: dict) -> dict:
    base = "https://commons.wikimedia.org/w/api.php?"
    qs = urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(base + qs, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=25))


def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def collect() -> list[dict]:
    seen: dict[int, dict] = {}
    for q in QUERIES:
        try:
            r = api({"action": "query", "generator": "search", "gsrsearch": q,
                     "gsrnamespace": 6, "gsrlimit": 10, "prop": "imageinfo",
                     "iiprop": "url|size|extmetadata", "iiurlwidth": 480})
        except OSError:
            continue
        for p in (r.get("query", {}).get("pages") or {}).values():
            if p["pageid"] in seen or not re.search(r"\.(jpe?g|png)$", p.get("title", ""), re.I):
                continue
            ii = (p.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata") or {}
            date = strip_html((em.get("DateTimeOriginal") or {}).get("value", ""))[:10]
            lic = strip_html((em.get("LicenseShortName") or {}).get("value", ""))
            in_window = bool(re.match(r"2026-08-2[5-9]|2026-08-3\d|2026-09-0[0-2]", date))
            w, h = ii.get("width", 0), ii.get("height", 0)
            seen[p["pageid"]] = {
                "title": p["title"], "page": ii.get("descriptionurl", ""),
                "date": date or "?", "license": lic or "necunoscută",
                "artist": strip_html((em.get("Artist") or {}).get("value", ""))[:48] or "?",
                "size": f"{w}×{h}", "w": w, "h": h,
                "gate": bool(w >= 1200 and h and w >= h * 1.2 and LICENSE_FREE.match(lic)),
                "event": in_window, "q": q,
                "thumb": ii.get("thumburl") or ii.get("url", ""),
            }
    rows = list(seen.values())
    rows.sort(key=lambda r: (not r["event"], -r["w"]))
    return rows[:12]


def grid(rows: list[dict], thumbs: list[Image.Image | None]) -> Image.Image:
    TW, TH, PAD, CAP = 460, 300, 16, 74
    cols = 3
    rwn = (len(rows) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (TW + PAD) + PAD, rwn * (TH + CAP + PAD) + PAD + 60), PAPER)
    d = ImageDraw.Draw(sheet)
    fnt = ImageFont.truetype(os.path.join(HERE, "..", "generator", "assets",
                                          "PlayfairDisplay_800ExtraBold.ttf"), 26)
    d.text((PAD, 16), "Commons — candidati pentru clusterul Nepal", font=fnt, fill=INK)
    for i, (r, im) in enumerate(zip(rows, thumbs)):
        cx = PAD + (i % cols) * (TW + PAD)
        cy = 60 + (i // cols) * (TH + CAP + PAD)
        if im:
            im = im.copy()
            im.thumbnail((TW, TH))
            sheet.paste(im, (cx + (TW - im.width) // 2, cy + (TH - im.height) // 2))
        tag = "DE LA EVENIMENT" if r["event"] else "ARHIVĂ DE SUBIECT"
        d.rectangle([cx, cy + TH, cx + TW, cy + TH + CAP], fill="#e8e2d2")
        d.text((cx + 6, cy + TH + 6), tag, fill=(GOLD if r["event"] else "#7a4a18"))
        gate = "gate: DA" if r["gate"] else "gate: NU"
        d.text((cx + TW - 6, cy + TH + 6), f'{r["date"]} · {gate}', fill=INK, anchor="ra")
    return sheet


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "commons"), exist_ok=True)
    rows = collect()
    thumbs: list[Image.Image | None] = []
    for i, r in enumerate(rows):
        try:
            req = urllib.request.Request(r["thumb"], headers={"User-Agent": UA})
            im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=25).read()))
            im = im.convert("RGB")
            im.save(os.path.join(OUT, "commons", f"{i:02d}.jpg"), quality=88)
            thumbs.append(im)
        except OSError:
            thumbs.append(None)
    cards = "".join(
        f'<div style="border:1px solid #d8d2c0;border-radius:8px;overflow:hidden">'
        f'<img src="commons/{i:02d}.jpg" style="width:100%;height:210px;object-fit:cover">'
        f'<div style="padding:10px;font:13px/1.45 Georgia,serif">'
        f'<b style="color:{"#8b6918" if r["event"] else "#7a4a18"}">'
        f'{"DE LA EVENIMENT" if r["event"] else "ARHIVĂ DE SUBIECT"}</b><br>'
        f'<a href="{r["page"]}">{r["title"]}</a><br>'
        f'dată: {r["date"]} · licență: {r["license"]}<br>'
        f'autor: {r["artist"]} · {r["size"]}<br>'
        f'gate producție: {"✓" if r["gate"] else "✗"} · query: {r["q"]}</div></div>'
        for i, r in enumerate(rows))
    html = (f'<!doctype html><meta charset="utf-8"><title>Mostre Commons — Nepal</title>'
            f'<body style="background:{PAPER};font:Georgia,serif;color:{INK};max-width:1100px;'
            f'margin:24px auto"><h1>Candidați Commons — viitura Nepal 26 aug 2026</h1>'
            f'<p>Verdict de potrivire pe dată de captură; "gate producție" = lățime ≥1200px, '
            f'peisaj, licență liberă (CC0/PD/CC BY[-SA], fără NC/ND).</p>'
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">{cards}</div>')
    open(os.path.join(OUT, "contact-sheet.html"), "w", encoding="utf-8").write(html)
    grid(rows, thumbs).save(os.path.join(OUT, "contact-sheet.jpg"), quality=88)
    ev = sum(r["event"] for r in rows)
    ok = sum(r["gate"] for r in rows)
    print(f"candidati: {len(rows)} · de la eveniment: {ev} · gate producție: {ok}")
    for i, r in enumerate(rows):
        print(f'{i:02d} {"EV " if r["event"] else "ARH"} {"gate✓" if r["gate"] else "gate✗"} '
              f'{r["date"]} {r["license"][:16]:16} {r["title"][:60]}')
