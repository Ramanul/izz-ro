"""Greutatea primei incarcari: cati octeti plateste cititorul ca sa deschida o pagina.

DIMENSIUNEA 5 din taxonomia din `specs/dimensiuni.md`. Nu dubleaza sect. 13: `tools/audit.sh`
da SCORURI Lighthouse — un indice compus, pe cateva pagini, care spune *cat de bine*, nu *ce
anume e greu*, si care cere Chromium plus doua pachete npm. Unealta asta raspunde la o
intrebare pe care scorul nu o pune: **din ce e facuta greutatea, pe TOATE paginile**, static,
fara browser si fara retea.

De ce conteaza intrebarea asta pentru izz.ro anume: `IZZ-0237` a masurat in august ca
homepage-ul trage ~1.256 KB de imagini pe 62 de carduri — o cifra care nu apare in niciun scor
si care nu are gardă. Un card in plus per rand nu schimba niciun scor Lighthouse cu o unitate,
dar adauga zeci de KB la fiecare vizita.

CE MASOARA (si ce NU): octetii de pe disc ai HTML-ului plus ai fiecarui asset la care pagina
trimite in mod EAGER. Nu masoara transferul real — nu stie de compresia gzip/brotli a lui
Cloudflare, de cache-ul vizitatorului, si nici de imaginile `loading="lazy"`, pe care le
numara separat tocmai fiindca nu intra in prima incarcare. Deci cifrele sunt un PLAFON
comparabil intre pagini, nu o predictie a ce vede utilizatorul pe retea.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

# `src`/`href` din tagurile care declanseaza o descarcare. Atributele sunt cautate pe TAG, nu
# global, ca sa se poata separa `loading="lazy"` de restul — un `<img>` lazy nu e in bugetul
# primei incarcari, iar amestecarea lor a fost exact felul in care cifra din IZZ-0237 parea
# mai mica decat e.
TAG = re.compile(r"<(img|script|link|source)\b([^>]*)>", re.I | re.S)
ATTR = re.compile(r'\b(src|href|srcset|rel|loading|type|media)\s*=\s*"([^"]*)"', re.I)


def _atribute(brut: str) -> dict[str, str]:
    return {c.lower(): v for c, v in ATTR.findall(brut)}


def _prima_din_srcset(srcset: str) -> str:
    return srcset.split(",")[0].strip().split()[0] if srcset.strip() else ""


def referinte(html: str) -> tuple[list[str], list[str]]:
    """(eager, lazy) — caile la care pagina trimite, separate dupa cand se descarca."""
    eager, lazy = [], []
    for tag, brut in TAG.findall(html):
        a = _atribute(brut)
        tag = tag.lower()
        if tag == "link":
            # Doar ce blocheaza sau precarca. `alternate` (RSS) si `canonical` nu se descarca.
            if a.get("rel", "").lower() not in {"stylesheet", "preload"}:
                continue
            cale = a.get("href", "")
        elif tag == "source":
            cale = _prima_din_srcset(a.get("srcset", "")) or a.get("src", "")
        else:
            cale = a.get("src", "") or _prima_din_srcset(a.get("srcset", ""))
        if not cale or cale.startswith(("data:", "http://", "https://", "//", "mailto:")):
            continue
        (lazy if a.get("loading", "").lower() == "lazy" else eager).append(cale)
    return eager, lazy


def _octeti(cale: str, pagina: Path) -> int:
    """Marimea pe disc a fisierului la care trimite `cale`, sau 0 daca nu se rezolva."""
    curata = unquote(urlsplit(cale).path)
    tinta = (OUTPUT / curata.lstrip("/")) if curata.startswith("/") else (pagina.parent / curata)
    try:
        return tinta.stat().st_size if tinta.is_file() else 0
    except OSError:
        return 0


def cantareste(pagina: Path) -> dict:
    html = pagina.read_text(encoding="utf-8", errors="replace")
    eager, lazy = referinte(html)
    pe_tip: Counter[str] = Counter()
    for cale in eager:
        pe_tip[Path(urlsplit(cale).path).suffix.lower() or "(fara)"] += _octeti(cale, pagina)
    return {
        "pagina": str(pagina.relative_to(OUTPUT)),
        "html": pagina.stat().st_size,
        "eager": sum(pe_tip.values()),
        "lazy": sum(_octeti(c, pagina) for c in lazy),
        "nr_eager": len(eager),
        "nr_lazy": len(lazy),
        "pe_tip": dict(pe_tip),
    }


def main(argv: list[str]) -> int:
    if not OUTPUT.is_dir():
        print("output/ lipseste — ruleaza intai `python -m generator.main --render-only`")
        return 2
    pagini = sorted(OUTPUT.rglob("*.html"))
    if not pagini:
        print("output/ nu contine .html")
        return 2
    rezultate = [cantareste(p) for p in pagini]
    rezultate.sort(key=lambda r: r["html"] + r["eager"], reverse=True)

    total = sum(r["html"] + r["eager"] for r in rezultate)
    print(f">> {len(rezultate)} pagini · prima incarcare, mediana "
          f"{sorted(r['html'] + r['eager'] for r in rezultate)[len(rezultate) // 2] / 1024:.0f} KB "
          f"· cea mai grea {(rezultate[0]['html'] + rezultate[0]['eager']) / 1024:.0f} KB")
    print(f"   total pe disc, daca cineva le-ar deschide pe toate: {total / 1024 / 1024:.1f} MB\n")
    print(f"   {'pagina':<44} {'HTML':>8} {'eager':>9} {'lazy':>9}  cereri")
    for r in rezultate[: int(argv[0]) if argv and argv[0].isdigit() else 12]:
        print(f"   {r['pagina'][:44]:<44} {r['html'] / 1024:7.0f}K {r['eager'] / 1024:8.0f}K "
              f"{r['lazy'] / 1024:8.0f}K  {r['nr_eager']:3d}+{r['nr_lazy']}")

    pe_tip: Counter[str] = Counter()
    for r in rezultate:
        pe_tip.update(r["pe_tip"])
    print("\n   greutatea eager pe tip de fisier, insumata peste toate paginile:")
    for ext, oct_ in pe_tip.most_common(8):
        print(f"     {ext:<8} {oct_ / 1024 / 1024:7.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
