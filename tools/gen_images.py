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
import json
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
LABELS = os.path.join(MEDIA, "labels.json")


def _semnatura(a: dict) -> str:
    """Textul VIZIBIL de pe imagine. Se schimba -> imaginea trebuie redesenata."""
    sig = f"{htmlart._eticheta(a)}|{htmlart._subtitlu(a)}"
    # Coperta din date (prognoza): cifrele se schimba zilnic, deci semnatura le include.
    if a.get("event_chart"):
        sig += "|" + json.dumps(a["event_chart"], sort_keys=True, ensure_ascii=False)
    return sig


def _load_labels() -> dict:
    """{aid: semnatura} de la ultima generare, sau {} daca lipseste.

    Esecul NU e tacut, desi `{}` e un fallback sigur: un manifest corupt ar face fiecare rulare
    sa considere toate imaginile invechite si sa rescrie lotul la nesfarsit. Simptomul (build
    lung, aceleasi imagini refacute mereu) s-ar vedea, cauza nu.
    """
    if not os.path.exists(LABELS):
        return {}
    try:
        with open(LABELS, encoding="utf-8") as fh:
            date = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"!! labels.json necitibil ({e}) — etichetele nu mai pot fi confirmate")
        return {}
    if not isinstance(date, dict):
        print(f"!! labels.json nu e obiect ({type(date).__name__}) — se ignora")
        return {}
    return date


def chrome_bin() -> str:
    cands = [os.getenv("CHROME_BIN"),
             *glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"),
             "chromium-browser", "chromium", "google-chrome", "google-chrome-stable"]
    for c in cands:
        if c and (os.path.exists(c) or shutil.which(c)):
            return c
    raise SystemExit("!! niciun binar Chromium gasit (seteaza CHROME_BIN)")


BIN = None


def _render(html: str, w: int, h: int, out_jpg: str, webp: bool = False) -> bool:
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
        img = Image.open(png).convert("RGB").resize((w, h), Image.LANCZOS)
        img.save(out_jpg, "JPEG", quality=85)
        if webp:
            # varianta moderna din sursa PNG (nu re-comprimata din JPEG): ~70% mai mica
            img.save(out_jpg[:-4] + ".webp", "WEBP", quality=80, method=6)
        return os.path.getsize(out_jpg) > 3000
    finally:
        for p in (hp, png):
            if os.path.exists(p):
                os.remove(p)


def main() -> int:
    arts = [a for a in state.load() if a.get("title")]
    os.makedirs(MEDIA, exist_ok=True)
    # Eticheta e ARSA in JPEG, dar `art_id` e SHA1 din URL — deci nu se schimba cand se schimba
    # eticheta, si o imagine desenata cu o eticheta veche se refoloseste la infinit. Masurat
    # 2026-08-08: 2962 din 2962 de coperti aratau logica dinainte de #164/#165, iar badge-ul ars
    # contrazicea categoria de sub card. Manifestul de mai jos leaga imaginea de textul ei.
    #
    # Alternativa evaluata si RESPINSA: hash-ul etichetei pus in `art_id`. Ar fi schimbat numele
    # TUTUROR fisierelor deodata, iar bucla de curatare de la final ar fi sters ~8900 de imagini
    # intr-o singura rulare, cu site-ul cazut pe fallback-ul Pillow pana la regenerare.
    #
    # La PRIMA rulare (manifest inexistent) imaginile deja pe disc se marcheaza cu eticheta lor
    # curenta FARA sa fie redesenate. Nu e o scurtatura: proprietarul a refuzat explicit
    # regenerarea imaginilor vechi pe 2026-08-06 („de acum incolo conteaza",
    # `handoff/arhiva/2026-08-06-handoff-integral.md`), iar un implicit care ar reface 2962 de
    # imagini ar redeschide singur o decizie inchisa. Cine vrea si trecutul reparat foloseste
    # `FORCE_REGEN=1`, pe loturi — ramane decizia proprietarului, cum a fost.
    seed = not os.path.exists(LABELS)
    labels = _load_labels()
    wanted = set()
    made = invechite = 0
    for a in arts:
        aid = htmlart.art_id(a)
        wanted.add(aid)
        sig = _semnatura(a)
        art_jpg = os.path.join(MEDIA, f"{aid}.jpg")
        cov_jpg = os.path.join(MEDIA, f"{aid}.c.jpg")
        # FORCE_REGEN=1 rescrie imagini care exista deja. Necesar dupa o schimbare de DESIGN:
        # altfel stilul nou se aplica doar articolelor noi, iar site-ul ramane luni de zile cu
        # doua generatii de coperti amestecate (2201 imagini existente la 2026-08-05). Lasat
        # explicit, nu implicit: o regenerare completa rescrie ~204 MB in repo si costa cate
        # doua randari Chromium per articol, deci se face pe loturi (MAX_IMAGES_PER_RUN).
        complet = (os.path.exists(art_jpg) and os.path.exists(cov_jpg)
                   and os.path.exists(art_jpg[:-4] + ".webp"))
        if not os.getenv("FORCE_REGEN") and complet:
            if seed and aid not in labels:
                labels[aid] = sig      # decizie proprietar 2026-08-06: trecutul nu se reface
                continue
            if labels.get(aid) == sig:
                continue
        invechite += 1
        if made >= MAX_PER_RUN:
            continue
        # webp doar pentru arta (cards/articol via <picture>); cover.jpg ramane doar og:image
        ok_a = _render(htmlart.build_html(a, cover=False), htmlart.ART_W, htmlart.ART_H, art_jpg, webp=True)
        ok_c = _render(htmlart.build_html(a, cover=True), htmlart.COVER_W, htmlart.COVER_H, cov_jpg)
        if ok_a or ok_c:
            made += 1
            # Doar la generare REUSITA: altfel un articol sarit de plafon s-ar marca fals ca
            # actualizat si n-ar mai fi redesenat niciodata.
            labels[aid] = sig
            print(f"  img {aid}  {a['title'][:56]}")
    # curata imaginile articolelor care nu mai exista in stare (TTL)
    pruned = 0
    for p in glob.glob(os.path.join(MEDIA, "*.jpg")) + glob.glob(os.path.join(MEDIA, "*.webp")):
        aid = os.path.basename(p).split(".")[0]
        if aid not in wanted:
            os.remove(p)
            pruned += 1
    labels = {k: v for k, v in labels.items() if k in wanted}
    try:
        with open(LABELS, "w", encoding="utf-8") as fh:
            json.dump(labels, fh, ensure_ascii=False, indent=0, sort_keys=True)
    except OSError as e:
        # Ce s-a generat ramane pe disc, dar nemarcat -> urmatoarea rulare il reface. Pierdere
        # de munca, nu de corectitudine — dar trebuie sa se vada, altfel arata ca lentoare.
        print(f"!! labels.json nu s-a putut scrie ({e}) — lotul se va reface la rularea viitoare")
    # `invechite` numara ce ARE NEVOIE de redesenare (eticheta schimbata sau imagini lipsa),
    # nu cate intrari are manifestul: `len(labels)` ar fi raportat „totul confirmat" chiar si
    # cu intrari vechi ramase in el — verificat 2026-08-08, exact asa mintea prima versiune.
    print(f">> gen_images: {made} noi (plafon {MAX_PER_RUN}), {pruned} sterse, "
          f"{len(wanted)} articole, {invechite - made} raman de redesenat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
