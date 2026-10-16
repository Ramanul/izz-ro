#!/usr/bin/env python3
"""Incadrarea portretelor: unde e FATA in fiecare `media/portraits/*.jpg`.

De ce exista (sesizarea proprietarului 2026-10-16, /extern/): portretele vin din Wikimedia
Commons in orice format — portret oficial, poza de meci in picioare, poza de grup — iar
medalionul de pe coperta le taia orbeste (`object-position: center 20%`). Masurat pe cele
70 de portrete aflate atunci pe carduri: fata lui Jovo Lukic avea 38 px intr-o poza de
330x522 (jucator intreg, pe teren), Basarab Panduru era unul din trei oameni intr-o poza de
grup, Luca Marchegiani avea fata la marginea dreapta (x=0.75). Ochiul nu poate repara asta
in CSS fara sa stie unde e fata; detectorul da exact informatia care lipsea.

Iesire: `data/portrete_incadrare.json`, cheiat pe calea relativa a imaginii (`portraits/x.jpg`):
  {"sha256": ..., "fete": n,
   "taiere": {"pw": 245.3, "px": -12.1, "py": -20.4},   # medalion: decupaj exact, in %
   "poz": "50% 31%",                                       # `object-position` pt. cover
   "respins": "grup" | "fata-mica"}                        # nu se arata deloc
Fara fata detectata (harti, cladiri, mozaicuri) -> nicio cheie de incadrare: ramane
incadrarea implicita din CSS, care pentru ele e corecta.

Detector: YuNet (OpenCV zoo, licenta MIT), `tools/modele/face_detection_yunet_2023mar.onnx`,
sha256 8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4. OpenCV NU e in
`requirements.txt`: build-ul il instaleaza doar cand exista portrete neincadrate
(`--verifica`), ca rularea orara sa nu plateasca 60 MB de wheel degeaba.

  python tools/incadrare_portrete.py             # incadreaza ce lipseste / s-a schimbat
  python tools/incadrare_portrete.py --verifica  # exit 1 daca exista portrete neincadrate
  python tools/incadrare_portrete.py --tot       # reincadreaza tot (dupa schimbarea regulii)
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTRAITS = os.path.join(ROOT, "data", "portraits.json")
OUT = os.path.join(ROOT, "data", "portrete_incadrare.json")
MEDIA = os.path.join(ROOT, "media")
MODEL = os.path.join(ROOT, "tools", "modele", "face_detection_yunet_2023mar.onnx")

# Regula. Cifrele sunt calibrate pe cele 70 de portrete de pe carduri din 2026-10-16 (vezi
# docstring): sub FATA_MIN_PX, fata intra in medalion marita de 2x+ la DPR 2 — pata, nu chip.
FATA_MIN_PX = 48          # latimea minima a fetei, in pixeli din fisierul sursa
GRUP_RAPORT = 0.6         # a doua fata >= 60% din prima -> poza de grup, nu portret
LATURA_PE_FATA = 2.6      # medalionul cuprinde ~2.6 latimi de fata: cap + umeri
COBORARE = 0.10           # centrul decupajului coboara 10% din inaltimea fetei (barbie, guler)
SCOR_MIN = 0.6


def _sha(path: str) -> str:
    """Amprenta fisierului: detecteaza un portret inlocuit sub acelasi nume."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloc in iter(lambda: fh.read(65536), b""):
            h.update(bloc)
    return h.hexdigest()


def _imagini() -> dict[str, str]:
    """{cale relativa: cale absoluta} pentru toate portretele cu fisier pe disc."""
    try:
        with open(PORTRAITS, encoding="utf-8") as fh:
            raw = json.load(fh) or {}
    except (OSError, ValueError):
        return {}
    out = {}
    for v in raw.values():
        if not isinstance(v, dict) or v.get("miss"):
            continue
        rel = (v.get("img") or "").strip()
        p = os.path.join(MEDIA, rel)
        if rel and os.path.isfile(p):
            out[rel] = p
    return out


def _incarca() -> dict:
    try:
        with open(OUT, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def de_incadrat(tot: bool = False) -> dict[str, str]:
    """Portretele fara incadrare sau al caror fisier s-a schimbat (alta amprenta)."""
    gata = {} if tot else _incarca()
    return {rel: p for rel, p in _imagini().items()
            if (gata.get(rel) or {}).get("sha256") != _sha(p)}


def decide(W: int, H: int, fete: list[tuple[float, float, float, float]]) -> dict:
    """Regula pura (testabila fara OpenCV): fete = [(x, y, w, h)] in pixeli sursa."""
    if not fete:
        return {"fete": 0}
    fete = sorted(fete, key=lambda f: -f[2] * f[3])
    x, y, fw, fh = fete[0]
    rez = {"fete": len(fete)}
    if len(fete) >= 2 and fete[1][2] >= GRUP_RAPORT * fw:
        rez["respins"] = "grup"
        return rez
    if fw < FATA_MIN_PX:
        rez["respins"] = "fata-mica"
        return rez
    cx, cy = x + fw / 2, y + fh / 2 + COBORARE * fh
    s = min(max(LATURA_PE_FATA * fw, 1.0), W, H)
    X = min(max(cx - s / 2, 0.0), W - s)
    Y = min(max(cy - s / 2, 0.0), H - s)
    # Decupaj exact pentru medalion: imaginea are latimea W/s din cutie si e mutata cu X/s, Y/s.
    rez["taiere"] = {"pw": round(float(W / s * 100), 2), "px": round(float(-X / s * 100), 2),
                     "py": round(float(-Y / s * 100), 2)}
    # Pentru `object-fit: cover` intr-un patrat (fara zoom): fata cat mai aproape de centru.
    W, H = int(W), int(H)
    m = min(W, H)
    px = 50.0 if W == m else min(max((cx - m / 2) / (W - m), 0.0), 1.0) * 100
    py = 50.0 if H == m else min(max((cy - m / 2) / (H - m), 0.0), 1.0) * 100
    rez["poz"] = f"{px:.0f}% {py:.0f}%"
    return rez


def _detecteaza(path: str):
    import cv2  # noqa: PLC0415 — dependinta optionala, doar pentru acest pas
    im = cv2.imread(path)
    if im is None:
        return None
    H, W = im.shape[:2]
    k = 2 if max(W, H) < 700 else 1   # fete de 40 px se detecteaza mult mai sigur la 2x
    mare = cv2.resize(im, (W * k, H * k), interpolation=cv2.INTER_CUBIC) if k > 1 else im
    det = cv2.FaceDetectorYN.create(MODEL, "", (W * k, H * k), SCOR_MIN, 0.3, 50)
    _, f = det.detect(mare)
    fete = [] if f is None else [tuple(float(v) / k for v in r[:4]) for r in f]
    return W, H, fete


def main(argv: list[str]) -> int:
    tot = "--tot" in argv
    lipsa = de_incadrat(tot)
    if "--verifica" in argv:
        print(f">> incadrare portrete: {len(lipsa)} de incadrat")
        return 1 if lipsa else 0
    if not lipsa:
        print(">> incadrare portrete: nimic nou")
        return 0
    try:
        import cv2  # noqa: F401, PLC0415
    except ImportError:
        print(">> incadrare portrete: OpenCV lipseste (pip install opencv-python-headless)")
        return 2
    gata = {} if tot else _incarca()
    respinse = 0
    for rel, p in sorted(lipsa.items()):
        d = _detecteaza(p)
        if d is None:
            continue
        rez = decide(*d)
        rez["sha256"] = _sha(p)
        gata[rel] = rez
        respinse += "respins" in rez
    # Doar cheile care mai au fisier: un portret sters nu lasa incadrare orfana.
    exista = _imagini()
    gata = {k: v for k, v in sorted(gata.items()) if k in exista}
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(gata, fh, ensure_ascii=False, indent=0, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, OUT)
    print(f">> incadrare portrete: {len(lipsa)} incadrate ({respinse} respinse), {len(gata)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
