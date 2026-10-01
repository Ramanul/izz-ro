#!/usr/bin/env python3
"""Masurator de contrast WCAG pentru hartă, pe valorile REALE din harta-stiri.css.

Context (5 sep 2026, sesizare proprietar pe live): butonul selectat din chenar avea text
alb pe auriu (3.15:1, sub minimul de 4.5:1), iar umpluturile de canvas erau sub 1.2:1 --
zonele "cu stiri" nu se separau vizibil de cele "fara". Reparatiile au fixat perechile
de mai jos; scriptul e garda care impiedica revenirea la valori pale.

Ce masoara si ce NU masoara: culorile DECLARATE in CSS plus alfa-urile din drawUats()
(harta-stiri.js) -- compozitia pe alb/negru e calculata, nu capturata din browser.
Antialiasing-ul, dithering-ul si calibrarea ecranului pot schimba perceptia cu zecimi,
nu cu unitati; un raport de 1.1 vs 1.5 e vizibil oriunde.

Usage: python tools/harta_contrast.py  (iesire 1 la orice pereche sub prag)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "static" / "harta-stiri" / "harta-stiri.css"

# Alfa-urile din drawUats() (harta-stiri.js) -- daca le schimbi acolo, schimba-le si aici.
ALPHA_UAT_STRONG = 0.85  # UAT cu stiri
ALPHA_UAT_EMPTY = 0.05   # UAT fara stiri
ALPHA_UAT_DIM = 0.12     # UAT din afara selectiei


def lin(channel: float) -> float:
    channel /= 255
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def lum(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ratio(a: tuple, b: tuple) -> float:
    lo, hi = sorted((lum(a), lum(b)))
    return (hi + 0.05) / (lo + 0.05)


def hex_rgb(value: str) -> tuple:
    value = value.strip().lstrip("#")
    if len(value) == 3:  # forme scurte gen #fff, folosite de tema paginii
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def alpha_over(fg: tuple, alpha: float, bg: tuple) -> tuple:
    return tuple(round(f * alpha + g * (1 - alpha)) for f, g in zip(fg, bg))


def parse_vars(block: str) -> dict:
    return {name: hex_rgb(value) for name, value in
            re.findall(r"(--[\w-]+):\s*(#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3}))", block)}


def main() -> int:
    css = CSS.read_text(encoding="utf-8")
    light = parse_vars(re.search(r":root \{(.*?)\}", css, re.S).group(1))
    dark = parse_vars(re.search(r"prefers-color-scheme: dark\) \{\s*:root \{(.*?)\}", css, re.S).group(1))

    fails = []
    row = 0
    print(f"{'tema':6} {'pereche':46} {'raport':>7}  prag  verdict")
    for theme, v in (("deschis", light), ("inchis", dark)):
        checks = [
            # Text peste suprafete pline de accent (buton selectat, cifre pe buline aurii).
            (v["--map-on-accent"], v["--accent"], 4.5, "text: on-accent pe accent"),
            (v["--map-badge-text"], v["--map-hot"], 4.5, "text: badge pe hot"),
            # Contururi de judete/UAT pe fundal (informatie purtata de linie, nu doar culoare).
            (v["--map-stroke"], v["--surface"], 3.0, "grafic: stroke pe surface"),
            # Separarea starilor pe canvas: UAT cu stiri vs UAT fara (compozit pe surface).
            (alpha_over(v["--accent"], ALPHA_UAT_STRONG, v["--surface"]),
             alpha_over(v["--accent-soft"], ALPHA_UAT_EMPTY, v["--surface"]),
             2.5, "stari: UAT cu stiri vs UAT fara"),
            # UAT-ul cu stiri trebuie sa iasa si el singur din fundal.
            (alpha_over(v["--accent"], ALPHA_UAT_STRONG, v["--surface"]),
             v["--surface"], 2.0, "grafic: UAT cu stiri pe surface"),
        ]
        for fg, bg, threshold, label in checks:
            row += 1
            r = ratio(fg, bg)
            ok = r >= threshold
            print(f"{theme:6} {label:46} {r:6.2f}:1  {threshold:4}  {'ok' if ok else 'PICA'}")
            if not ok:
                fails.append(f"{theme}: {label} ({r:.2f} < {threshold})")

    if fails:
        print("\nFAIL: perechi sub prag:")
        for f in fails:
            print(" -", f)
        return 1
    print(f"\nOK: {row} perechi verificate, toate peste prag.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
