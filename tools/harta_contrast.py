#!/usr/bin/env python3
"""Masurator de contrast + distanta perceptiva pentru paleta hartii (valorile REALE din CSS).

Context (5 sep 2026, sesizare proprietar pe live): butonul selectat din chenar avea text
alb pe auriu (3.15:1, sub minimul de 4.5:1), iar umpluturile de canvas erau sub 1.2:1 --
zonele "cu stiri" nu se separau vizibil de cele "fara". De atunci scriptul e garda care
impiedica revenirea la valori pale.

Ce s-a schimbat la 2026-10-04 (F1 = substrat SVG/DOM, vezi
notes/harta-revolutie-proposal-2026-10-04.md): rampa nu mai e compusa pe canvas din alfa
-- e o paleta de cinci umpluturi solide (--map-h0..h4) si doua linii (--map-stroke pe
conturul judetelor, --map-line intre UAT-uri). De aceea verificarea nu mai are sens doar pe
rapoarte WCAG: intre doua trepte deschise (h0 gri vs h1 galben pal) raportul WCAG e ~1.25
desi ochiul le separa imediat. Criteriul corect pentru o scara choropleth e distanta
perceptiva: dL* >= 8 si dE* >= 10 intre trepte alaturate, plus monotonie fata de fundal
("mai inchis = mai multe stiri" sa fie adevarat in ambele teme).

Ce masoara si ce NU masoara: culorile DECLARATE in CSS -- compozitia pe alb/negru e
calculata, nu capturata din browser. Antialiasing-ul, dithering-ul si calibrarea ecranului
pot schimba perceptia cu zecimi, nu cu unitati.

Usage: python tools/harta_contrast.py  (iesire 1 la orice pereche sub prag)
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "static" / "harta-stiri" / "harta-stiri.css"

# Treptele rampei, in ordinea volumului: h0 (fara stiri) .. h4 (30+). Numele trebuie sa
# existe in ambele teme, altfel scriptul pica mai jos (`KeyError` explicit).
RAMPA = ("--map-h0", "--map-h1", "--map-h2", "--map-h3", "--map-h4")

# Praguri de perceptie pentru scara. 8 unitati L* si 10 unitati E* sunt peste pragul la care
# doua umpluturi alaturate se citesc ca "trepte diferite" chiar si pe un ecran prost calibrat.
MIN_DL = 8.0
MIN_DE = 10.0
MIN_DL_TOTAL = 30.0  # h0 -> h4: capetele scarii trebuie sa fie evident diferite


def lin(channel: float) -> float:
    channel /= 255
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def lum(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ratio(a: tuple, b: tuple) -> float:
    lo, hi = sorted((lum(a), lum(b)))
    return (hi + 0.05) / (lo + 0.05)


def lab(rgb: tuple) -> tuple[float, float, float]:
    r, g, b = (lin(channel) for channel in rgb)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    xn, yn, zn = 0.95047, 1.0, 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)  # noqa: E731
    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def dist_e(a: tuple, b: tuple) -> float:
    return math.dist(lab(a), lab(b))


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

    fails: list[str] = []
    row = 0
    print(f"{'tema':6} {'pereche':52} {'valoare':>10}  prag   verdict")
    for theme, v in (("deschis", light), ("inchis", dark)):
        for name in RAMPA:
            if name not in v:
                fails.append(f"{theme}: lipseste tokenul {name} (rampa nu mai are 5 trepte)")
        if any(name not in v for name in RAMPA):
            continue
        checks = [
            # Text peste suprafete pline.
            (v["--map-on-accent"], v["--accent"], 4.5, "text: on-accent pe accent"),
            (v["--map-badge-text"], v["--map-hot"], 4.5, "text: badge pe hot"),
            (v["--map-ink"], v["--surface"], 4.5, "text: eticheta pe suprafata"),
            (v["--map-hot"], v["--surface"], 4.5, "text: cifra aurie pe suprafata"),
            # Contururi (informatie purtata de linie).
            (v["--map-stroke"], v["--surface"], 3.0, "grafic: contur judet pe suprafata"),
            (v["--map-line"], v["--surface"], 1.4, "grafic: linie UAT pe suprafata"),
        ]
        for fg, bg, threshold, label in checks:
            row += 1
            r = ratio(fg, bg)
            ok = r >= threshold
            print(f"{theme:6} {label:52} {r:8.2f}:1  {threshold:4}  {'ok' if ok else 'PICA'}")
            if not ok:
                fails.append(f"{theme}: {label} ({r:.2f} < {threshold})")

        # Scara: distanta perceptiva intre trepte alaturate + monotonie fata de fundal.
        steps = [v[name] for name in RAMPA]
        for i in range(len(steps) - 1):
            row += 1
            dl = lab(steps[i + 1])[0] - lab(steps[i])[0]
            de = dist_e(steps[i], steps[i + 1])
            ok = abs(dl) >= MIN_DL and de >= MIN_DE
            print(f"{theme:6} {'rampa: h' + str(i) + ' -> h' + str(i + 1):52} "
                  f"dL*{dl:+6.1f} dE*{de:5.1f}  {MIN_DL:4}  {'ok' if ok else 'PICA'}")
            if not ok:
                fails.append(f"{theme}: treptele h{i}/h{i + 1} prea apropiate (dL*={dl:.1f}, dE*={de:.1f})")

        row += 1
        total = abs(lab(steps[-1])[0] - lab(steps[0])[0])
        ok = total >= MIN_DL_TOTAL
        print(f"{theme:6} {'rampa: h0 -> h4 (capetele scarii)':52} dL*{total:6.1f}       "
              f"{MIN_DL_TOTAL:4}  {'ok' if ok else 'PICA'}")
        if not ok:
            fails.append(f"{theme}: capetele scarii prea apropiate (dL*={total:.1f})")

        # Monotonie: numerelor mai mari le corespund umpluturi cu contrast crescator fata de
        # fundal, in ambele teme -- altfel "mai inchis = mai multe stiri" e o afirmatie falsa.
        row += 1
        ratios = [ratio(step, v["--surface"]) for step in steps]
        mono = all(b > a for a, b in zip(ratios, ratios[1:]))
        print(f"{theme:6} {'rampa: monotonie fata de fundal':52} "
              f"{'↑' if ratios[-1] > ratios[0] else '↓'}          -      {'ok' if mono else 'PICA'}")
        if not mono:
            fails.append(f"{theme}: rampa nu e monotona fata de fundal ({['%.2f' % r for r in ratios]})")

    if fails:
        print("\nFAIL: perechi sub prag:")
        for f in fails:
            print(" -", f)
        return 1
    print(f"\nOK: {row} verificari, toate peste prag.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
