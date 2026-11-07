#!/usr/bin/env python3
"""Masuratori reproductibile pentru analiza multidimensionala a site-ului randat.

Ruleaza pe `output/` (site-ul static deja construit) si pe `data/articles.json`.
Nu importa codul generatorului: citeste artefactele, ca sa poata rula si pe un
build de productie descarcat separat.

    python -m generator.main --render-only      # intai, ca output/ sa fie cel real
    python analiza/masuratori.py                # apoi asta

ATENTIE: suita de teste (`pytest`) re-randeaza `output/` cu un set redus de
articole (~190). Daca rulati pytest inainte, cifrele de aici descriu fixture-ul,
nu productia. Verificati `output/build.json` -> `article_count`.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
STATE = os.path.join(ROOT, "data", "articles.json")
CATS = {"general", "regional", "judetean", "local", "politic", "economic", "extern",
        "sport", "sanatate", "tech", "cultura", "lifestyle", "discounturi", "auto", "ai"}

RE_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
RE_DESC = re.compile(r'<meta name="description" content="(.*?)"', re.S)
RE_ROBOTS = re.compile(r'<meta name="robots" content="([^"]*)"')
RE_IMG = re.compile(r"<img\b[^>]*>", re.I)
RE_LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
RE_HREF = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>', re.I)
RE_MAIN = re.compile(r"<main.*?</main>", re.S)
RE_SVG = re.compile(r"<svg.*?</svg>", re.S)
RE_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)


def tip(rel: str) -> str:
    seg = rel.split("/")
    if rel == "index.html":
        return "home"
    if seg[0] in CATS and len(seg) == 2:
        return "categorie"
    if seg[0] in CATS and len(seg) == 3 and seg[1].isdigit():
        return "paginare"
    if len(seg) == 3 and seg[0] in CATS:
        return "articol"
    return "alta"


def pctl(values, q):
    v = sorted(values)
    return v[max(0, min(len(v) - 1, int(len(v) * q) - 1))] if v else 0


def main() -> int:
    if not os.path.isdir(OUT):
        print("output/ lipseste — ruleaza `python -m generator.main --render-only`")
        return 2
    build = {}
    try:
        build = json.load(open(os.path.join(OUT, "build.json"), encoding="utf-8"))
    except OSError:
        pass

    rows = []
    for root, _dirs, files in os.walk(OUT):
        if "_pagefind" in root or "index.html" not in files:
            continue
        path = os.path.join(root, "index.html")
        rel = os.path.relpath(path, OUT)
        html = open(path, encoding="utf-8", errors="replace").read()
        imgs = RE_IMG.findall(html)
        main_m = RE_MAIN.search(html)
        row = {
            "path": rel, "tip": tip(rel), "size": len(html.encode()),
            "gz": len(gzip.compress(html.encode(), 6)),
            "title": (RE_TITLE.search(html).group(1).strip() if RE_TITLE.search(html) else ""),
            "desc": (RE_DESC.search(html).group(1).strip() if RE_DESC.search(html) else ""),
            "robots": (RE_ROBOTS.search(html).group(1) if RE_ROBOTS.search(html) else ""),
            "imgs": len(imgs),
            "imgs_reale": sum(1 for i in imgs if "/static/icons/" not in i),
            "imgs_fara_srcset": sum(1 for i in imgs if "srcset=" not in i and "/static/icons/" not in i),
            "foto_articol": ("article-art-fig" in html) or ("arhiva-foto" in html),
            "linkuri_main": len(RE_HREF.findall(main_m.group(0))) if main_m else 0,
            "svg_bytes": sum(len(s.encode()) for s in RE_SVG.findall(html)),
            "svg_n": len(RE_SVG.findall(html)),
            "links": len(RE_HREF.findall(html)),
            "main_bytes": len(main_m.group(0).encode()) if main_m else 0,
            "ld_bad": False,
        }
        h1 = RE_H1.search(html)
        row["h1"] = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else ""
        for blk in RE_LD.findall(html):
            try:
                json.loads(blk)
            except Exception:
                row["ld_bad"] = True
        rows.append(row)

    by = defaultdict(list)
    for r in rows:
        by[r["tip"]].append(r)
    art = by["articol"]

    def summar(tipuri):
        out = {}
        for t in tipuri:
            rs = by[t]
            if not rs:
                continue
            out[t] = {
                "n": len(rs),
                "size_med_kb": round(statistics.median(r["size"] for r in rs) / 1024, 1),
                "size_p95_kb": round(pctl([r["size"] for r in rs], .95) / 1024, 1),
                "size_max_kb": round(max(r["size"] for r in rs) / 1024, 1),
                "gz_med_kb": round(statistics.median(r["gz"] for r in rs) / 1024, 1),
            }
        return out

    titles = Counter(r["title"] for r in rows)
    descs = Counter(r["desc"] for r in rows if r["desc"])

    rez = {
        "build": build,
        "html": {
            "pagini": len(rows),
            "total_mb": round(sum(r["size"] for r in rows) / 1e6, 1),
            "total_gz_mb": round(sum(r["gz"] for r in rows) / 1e6, 1),
            "pe_tip": summar(["home", "categorie", "paginare", "articol", "alta"]),
        },
        "home": {k: by["home"][0][k] for k in ("size", "gz", "svg_n", "svg_bytes", "links")},
        "articole": {
            "n": len(art),
            "fara_descriere": sum(1 for r in art if not r["desc"]),
            "descriere_sub_70": sum(1 for r in art if 0 < len(r["desc"]) < 70),
            "titlu_med": round(statistics.mean(len(r["title"]) for r in art), 1),
            "titlu_peste_60": sum(1 for r in art if len(r["title"]) > 60),
            "h1_trunchiat": sum(1 for r in art if r["h1"].endswith("…")),
            "main_bytes_med": round(statistics.median(r["main_bytes"] for r in art)),
            "pondere_main_med": round(100 * statistics.median(
                [r["main_bytes"] / r["size"] for r in art if r["size"]]), 1),
            "fara_fotografie": sum(1 for r in art if not r["foto_articol"]),
            "cu_fotografie": sum(1 for r in art if r["foto_articol"]),
            "img_fara_srcset": sum(r["imgs_fara_srcset"] for r in art),
            "img_reale": sum(r["imgs_reale"] for r in art),
            "noindex": sum(1 for r in art if "noindex" in r["robots"]),
            "ld_invalid": sum(1 for r in art if r["ld_bad"]),
            "linkuri_med": round(statistics.median(r["links"] for r in art), 1),
            "linkuri_main_med": round(statistics.median(r["linkuri_main"] for r in art), 1),
        },
        "noindex": {"total": sum(1 for r in rows if "noindex" in r["robots"]),
                    "pe_tip": {t: sum(1 for r in rs if "noindex" in r["robots"]) for t, rs in by.items()}},
        "duplicate": {
            "titluri_grupuri": sum(1 for v in titles.values() if v > 1),
            "titluri_suprapuse": sum(v - 1 for v in titles.values() if v > 1),
            "descrieri_grupuri": sum(1 for v in descs.values() if v > 1),
            "descrieri_suprapuse": sum(v - 1 for v in descs.values() if v > 1),
        },
        "assets": {},
    }

    for f in ("styles.css", "theme.js", "judet.js", "pwa.js",
              "push.js", "editorial-updates.js", "search.js"):
        p = os.path.join(OUT, "static", f)
        if os.path.isfile(p):
            raw = open(p, "rb").read()
            rez["assets"][f] = {"raw": len(raw), "gz": len(gzip.compress(raw, 6))}

    imagini = Counter()
    octeti = Counter()
    for root, _d, files in os.walk(OUT):
        if "_pagefind" in root:
            continue
        for f in files:
            ext = f.rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png", "webp", "woff2"):
                n = os.path.getsize(os.path.join(root, f))
                imagini[ext] += 1
                octeti[ext] += n
    rez["media"] = {k: {"fisiere": imagini[k], "mb": round(octeti[k] / 1e6, 1)} for k in imagini}

    # starea editoriala
    if os.path.isfile(STATE):
        A = json.load(open(STATE, encoding="utf-8"))
        src = Counter(a.get("source_name") for a in A)
        rez["editorial"] = {
            "iteme": len(A),
            "model_b": sum(1 for a in A if a.get("model") == "B"),
            "model_c": sum(1 for a in A if a.get("model") == "C"),
            "oficial": sum(1 for a in A if a.get("processed_by") == "official"),
            "surse_distincte": len(src),
            "top10_pondere": round(100 * sum(c for _, c in src.most_common(10)) / len(A), 1),
            "pe_categorie": dict(Counter(a.get("category") for a in A).most_common()),
            "local_oficial_pondere": round(100 * sum(
                1 for a in A if a.get("category") == "local" and a.get("processed_by") == "official")
                / max(1, sum(1 for a in A if a.get("category") == "local")), 1),
        }

    print(f"pagini: {len(rows)} | articole: {len(art)} | build: {build.get('generated_at')}")
    for t, d in rez["html"]["pe_tip"].items():
        print(f"  {t:10s} n={d['n']:5d} med={d['size_med_kb']:7.1f}K "
              f"p95={d['size_p95_kb']:7.1f}K max={d['size_max_kb']:7.1f}K gz={d['gz_med_kb']:6.1f}K")
    print("home:", rez["home"])
    print("articole:", rez["articole"])
    print("duplicate:", rez["duplicate"])
    print("media:", rez["media"])

    dest = os.path.join(ROOT, "analiza", "masuratori.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(rez, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print("scris", dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
