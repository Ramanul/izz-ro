#!/usr/bin/env python
"""Randeaza imaginile per-articol (HTML/CSS -> headless Chromium) in `media/`,
COMISE in repo. Ruleaza in GitHub Actions (Chromium exista acolo; NU in build-ul
Cloudflare). Incremental + plafonat per rulare, ca sa nu dureze niciun build prea
mult. render.py preia din media/ daca exista, altfel cade pe Pillow (covers.py).

  python tools/gen_images.py

Env:
  CHROME_BIN            binar chromium (altfel autodetectie)
  MAX_IMAGES_PER_RUN    plafon imagini noi per rulare (default 80)
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from generator import htmlart, state  # noqa: E402
from PIL import Image  # noqa: E402

MEDIA = os.path.join(ROOT, "media")
MAX_PER_RUN = int(os.getenv("MAX_IMAGES_PER_RUN", "80"))


def chrome_bin() -> str:
    cands = [os.getenv("CHROME_BIN"),
             *glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"),
             "chromium-browser", "chromium", "google-chrome", "google-chrome-stable"]
    for c in cands:
        if c and (os.path.exists(c) or shutil.which(c)):
            return c
    raise SystemExit("!! niciun binar Chromium gasit (seteaza CHROME_BIN)")


BIN = None


def _render(html: str, w: int, h: int, out_jpg: str) -> bool:
    global BIN
    BIN = BIN or chrome_bin()
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        hp = f.name
    png = out_jpg + ".png"
    try:
        subprocess.run([BIN, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        f"--screenshot={png}", f"--window-size={w},{h}", "--force-device-scale-factor=2",
                        f"file://{hp}"], capture_output=True, timeout=120)
        if not os.path.exists(png) or os.path.getsize(png) < 1000:
            return False
        # randat 2x -> micsorat la dimensiunea logica: crisp (supersampling) + fisier mic
        Image.open(png).convert("RGB").resize((w, h), Image.LANCZOS).save(out_jpg, "JPEG", quality=85)
        return os.path.getsize(out_jpg) > 3000
    finally:
        for p in (hp, png):
            if os.path.exists(p):
                os.remove(p)


def main() -> int:
    arts = [a for a in state.load() if a.get("title")]
    os.makedirs(MEDIA, exist_ok=True)
    wanted = set()
    made = 0
    for a in arts:
        aid = htmlart.art_id(a)
        wanted.add(aid)
        art_jpg = os.path.join(MEDIA, f"{aid}.jpg")
        cov_jpg = os.path.join(MEDIA, f"{aid}.c.jpg")
        if os.path.exists(art_jpg) and os.path.exists(cov_jpg):
            continue
        if made >= MAX_PER_RUN:
            continue
        ok_a = _render(htmlart.build_html(a, cover=False), htmlart.ART_W, htmlart.ART_H, art_jpg)
        ok_c = _render(htmlart.build_html(a, cover=True), htmlart.COVER_W, htmlart.COVER_H, cov_jpg)
        if ok_a or ok_c:
            made += 1
            print(f"  img {aid}  {a['title'][:56]}")
    # curata imaginile articolelor care nu mai exista in stare (TTL)
    pruned = 0
    for p in glob.glob(os.path.join(MEDIA, "*.jpg")):
        aid = os.path.basename(p).split(".")[0]
        if aid not in wanted:
            os.remove(p)
            pruned += 1
    print(f">> gen_images: {made} noi (plafon {MAX_PER_RUN}), {pruned} sterse, {len(wanted)} articole")
    return 0


if __name__ == "__main__":
    sys.exit(main())
