#!/usr/bin/env python
"""Re-encode the committed portraits so that bytes match the pixels they show.

De ce: portretul cel mai greu din build (`media/portraits/ciprian-deac.jpg`) avea 379.742 B
pentru **232x318 px** — adică 5,15 B/px. La 96-168 px cât se afișează în pagină, asta nu e
„poză mare", e poză prost comprimată: `fetch_portraits.py` scria pe disc octeții primiți de la
Commons, fără să-i re-encodeze. Aceeași imagine la calitate 85 are 19.635 B (34,1 dB PSNR —
diferență invizibilă la dimensiunea de afișare), deci problema nu se rezolva cu `srcset`
(fișierele nu sunt supradimensionate, sunt supracodificate).

Regulile sunt deterministe, ca fișierul comis să fie reproductibil:

  - EXIF-ul se aplică în pixeli (`exif_transpose`) și apoi se aruncă (și orientarea rămâne
    corectă, și dispare EXIF-ul care nu are ce căuta în repo: cameră, dată, uneori GPS);
  - latura mare se plafonează la 640 px (afișarea maximă e 168 px, deci 3,8x pe ecran 1x);
  - JPEG progresiv, calitate 85, `optimize`;
  - fișierul se rescrie doar dacă scade cu cel puțin 15% și are peste 20 KB — sub asta nu
    merită atins, iar o re-encodare care nu câștigă ar fi doar pierdere de generație.

  python tools/usureaza_portrete.py            # raport, nu scrie nimic
  python tools/usureaza_portrete.py --apply    # rescrie fișierele care câștigă

Același `compacteaza_bytes` e chemat de `fetch_portraits.py` pe fiecare portret nou, ca
regula să se aplice și în viitor, nu doar la curățenia de azi.
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTRETE = os.path.join(ROOT, "media", "portraits")

MAX_LATURA = 640        # px pe latura mare; afișarea maximă în pagină e 168 px (arhivă)
QUALITATE = 85          # JPEG; măsurat: 34,1 dB PSNR pe cel mai greu portret
PRAG_SCADERE = 0.85     # rescrie doar dacă noul fișier e sub 85% din cel vechi
PRAG_MINIM = 20_000     # sub 20 KB nu se atinge nimic: câștigul nu plătește generația
# Plafonul pe care îl verifică `tests/test_greutate_portrete.py`. E exprimat în octeți per
# pixel, nu în octeți absoluți: un portret de 120x160 are alt buget decât unul de 330x470.
MAX_OCTETI_PER_PIXEL = 0.75
MAX_OCTETI_FIX = 6_000  # podeaua: antetul JPEG nu scade sub asta indiferent de dimensiune


def _pregateste(img):
    """Orientare arsă în pixeli + RGB (fără canal alfa, fără EXIF)."""
    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    latura = max(img.size)
    if latura > MAX_LATURA:
        nou = (max(1, round(img.width * MAX_LATURA / latura)),
               max(1, round(img.height * MAX_LATURA / latura)))
        img = img.resize(nou, Image.LANCZOS)
    return img


def compacteaza_bytes(data: bytes) -> bytes:
    """Octeții unui portret, re-encodați după regulile modulului.

    Întoarce `data` neatins dacă re-encodarea nu e mai mică (un fișier deja optim nu trebuie
    să piardă o generație de compresie degeaba) sau dacă nu se poate decoda.
    """
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return data
    img = _pregateste(img)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=QUALITATE, optimize=True, progressive=True)
    nou = buf.getvalue()
    return nou if len(nou) < len(data) else data


def optimizeaza(cale: str, aplica: bool = False) -> tuple[int, int] | None:
    """(vechi, nou) dacă fișierul a fost (sau ar fi) rescris, altfel None."""
    vechi = os.path.getsize(cale)
    if vechi < PRAG_MINIM:
        return None
    try:
        with open(cale, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    nou = compacteaza_bytes(data)
    if len(nou) > vechi * PRAG_SCADERE:
        return None
    if aplica:
        tmp = cale + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(nou)
        os.replace(tmp, cale)
    return vechi, len(nou)


def buget_octeti(latime: int, inaltime: int) -> int:
    """Cât are voie să cântărească un portret de dimensiunea dată (folosit și de test)."""
    return max(MAX_OCTETI_FIX, int(MAX_OCTETI_PER_PIXEL * latime * inaltime))


def main(argv: list[str]) -> int:
    aplica = "--apply" in argv
    if not os.path.isdir(PORTRETE):
        print(f"!! lipsește {PORTRETE}")
        return 1
    fisiere = sorted(f for f in os.listdir(PORTRETE)
                     if os.path.isfile(os.path.join(PORTRETE, f))
                     and f.lower().endswith((".jpg", ".jpeg")))
    total_vechi = sum(os.path.getsize(os.path.join(PORTRETE, f)) for f in fisiere)
    schimbate, economie = 0, 0
    for f in fisiere:
        rez = optimizeaza(os.path.join(PORTRETE, f), aplica=aplica)
        if rez:
            schimbate += 1
            economie += rez[0] - rez[1]
    verb = "rescrise" if aplica else "ar fi rescrise"
    print(f"{len(fisiere)} portrete, {total_vechi / 1e6:.1f} MB")
    print(f"{schimbate} {verb}: {economie / 1e3:.1f} KB "
          f"({100 * economie / total_vechi:.0f}% din arbore)"
          + ("" if aplica else " — rulează cu --apply ca să scrie"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
