"""Portretele comise trebuie să aibă octeți pe măsura pixelilor pe care îi arată.

Contextul măsurat (2026-11-07): cel mai greu portret din build avea 379.742 B pentru
232x318 px, adică 5,15 B/px, la o afișare de maximum 168 px. Nu era o poză mare, era o
poză supracodificată — `fetch_portraits.py` scria pe disc octeții de la Commons fără să-i
re-encodeze. `tools/usureaza_portrete.py` a rescris 220 fișiere (20,6 MB) și regula de
aici e garda care oprește revenirea: bugetul e EXPRIMAT ÎN OCTEȚI PER PIXEL, ca să nu
pedepsească un portret mic și să nu absolve unul mare.

Testele care decodează imagini lucrează pe un eșantion determinist (fiecare al 40-lea
fișier): 2.022 de fișiere peste 20 KB costă ~7 s la decodare, iar suita întreagă durează
un minut — garda trebuie să prindă regresia, nu să o dubleze ca durată.
"""
import io
import os

import pytest

from tools import usureaza_portrete as uu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTRETE = os.path.join(ROOT, "media", "portraits")

pytestmark = pytest.mark.skipif(not os.path.isdir(PORTRETE),
                                reason="fără media/portraits (checkout parțial)")


def _portrete() -> list[str]:
    return sorted(os.path.join(PORTRETE, f) for f in os.listdir(PORTRETE)
                  if f.lower().endswith((".jpg", ".jpeg")))


def _esantion(pas: int = 40) -> list[str]:
    fisiere = _portrete()
    return fisiere[::pas]


def test_portretele_comise_incap_in_buget():
    """Fiecare portret comis: sub bugetul de octeți ȘI sub plafonul de latură.

    Se citesc doar antetele (PIL nu decodează pixeli), deci testul rulează pe tot arborele.
    """
    from PIL import Image

    rele = []
    for cale in _portrete():
        with Image.open(cale) as img:
            latime, inaltime = img.size
        octeti = os.path.getsize(cale)
        buget = uu.buget_octeti(latime, inaltime)
        if octeti > buget or max(latime, inaltime) > 800:
            rele.append(f"{os.path.basename(cale)}: {octeti} B / buget {buget} B, "
                        f"{latime}x{inaltime}")
    assert not rele, ("portrete peste buget (rulează `python tools/usureaza_portrete.py "
                      "--apply`):\n" + "\n".join(rele[:20]))


def test_unealta_nu_mai_are_ce_face():
    """Pe eșantionul comis, re-encodarea nu mai câștigă pragul de 15%.

    Dacă o face, înseamnă că arborele a primit fișiere noi nereencodate — exact regresia pe
    care o prinde `test_portretele_comise_incap_in_buget`, dar aici cu dovada că unealta
    însăși ar rescrie ceva, nu doar că o limită arbitrară e depășită.
    """
    ramase = []
    for cale in _esantion():
        with open(cale, "rb") as fh:
            data = fh.read()
        if len(data) < uu.PRAG_MINIM:
            continue
        nou = uu.compacteaza_bytes(data)
        if len(nou) <= len(data) * uu.PRAG_SCADERE:
            ramase.append(f"{os.path.basename(cale)}: {len(data)} -> {len(nou)} B")
    assert not ramase, "fișiere pe care unealta le-ar rescrie:\n" + "\n".join(ramase)


def test_compacteaza_bytes_aplica_orientarea_si_plafonul():
    """EXIF-ul de orientare e ars în pixeli, apoi aruncat; latura mare se plafonează."""
    from PIL import Image

    img = Image.new("RGB", (900, 1500), (120, 90, 60))
    for x in range(0, 900, 3):                       # textură: ca JPEG-ul să aibă ce comprima
        for y in range(0, 1500, 3):
            img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
    exif = Image.Exif()
    exif[274] = 6                                     # „rotit 90°"
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=98, exif=exif)
    original = buf.getvalue()

    nou = uu.compacteaza_bytes(original)
    assert len(nou) < len(original)
    with Image.open(io.BytesIO(nou)) as rez:
        assert max(rez.size) == uu.MAX_LATURA
        assert rez.size[0] > rez.size[1], "orientarea EXIF nu a fost arsă în pixeli"
        assert not rez.getexif().get(274), "orientarea a rămas în EXIF după re-encodare"


def test_bytes_ilegibili_trec_neatinse():
    """Un fișier care nu se decodează nu se atinge: unealta nu are voie să piardă date."""
    gunoi = b"\xff\xd8\xff\xe0nu-e-jpeg" * 100
    assert uu.compacteaza_bytes(gunoi) is gunoi or uu.compacteaza_bytes(gunoi) == gunoi
