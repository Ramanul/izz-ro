"""Măsoară `generator.ton` pe corpusul real: câte articole primesc semnul și ce nimerește.

Doar citește `data/articles.json`; nu modifică nimic. Nu e mecanism de siguranță: semnul se
calculează la randare din `generator/ton.py`, iar `tests/test_ton.py` păzește logica în CI.
Ieșirea e mică: numere pe rubrici și un eșantion determinist (sortat după slug) pentru citire
cu ochiul. Rulare:

    python tools/audit_ton.py [--sample 12] [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generator import ton  # noqa: E402


def _articole(cale: pathlib.Path) -> list[dict]:
    brut = json.loads(cale.read_text(encoding="utf-8"))
    if isinstance(brut, dict):
        brut = brut.get("articles") or list(brut.values())
    return [a for a in brut if isinstance(a, dict)]


def masoara(articole: list[dict]) -> dict:
    pe_rubrica: collections.Counter = collections.Counter()
    total_rubrica: collections.Counter = collections.Counter()
    grele, metafore = [], []
    for a in articole:
        rubrica = a.get("category") or "?"
        total_rubrica[rubrica] += 1
        titlu = a.get("title") or ""
        if ton.subiect_greu(titlu, rubrica):
            pe_rubrica[rubrica] += 1
            grele.append(a)
        if ton.violenta_in_titlu(titlu):
            metafore.append(a)
    return {
        "total": len(articole),
        "subiect_greu": len(grele),
        "metafore_titlu": len(metafore),
        "pe_rubrica": {r: [pe_rubrica[r], total_rubrica[r]] for r in sorted(total_rubrica)},
        "_grele": grele,
        "_metafore": metafore,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(ROOT / "data" / "articles.json"))
    parser.add_argument("--sample", type=int, default=12)
    parser.add_argument("--json", default="")
    args = parser.parse_args()

    rez = masoara(_articole(pathlib.Path(args.data)))
    procent = 100 * rez["subiect_greu"] / max(1, rez["total"])
    print(f"articole: {rez['total']}  subiect_greu: {rez['subiect_greu']} ({procent:.2f}%)  "
          f"metafore_in_titlu: {rez['metafore_titlu']}")
    for rubrica, (greu, total) in rez["pe_rubrica"].items():
        print(f"  {rubrica:<11} {greu:>5} / {total:<6} ({100 * greu / max(1, total):.1f}%)")
    for nume, cheie in (("ESANTION subiect_greu", "_grele"), ("ESANTION metafore", "_metafore")):
        print(f"--- {nume}")
        for a in sorted(rez[cheie], key=lambda x: x.get("slug") or "")[:args.sample]:
            print(f"  [{a.get('category')}] {(a.get('title') or '')[:110]}")
    if args.json:
        iesire = {k: v for k, v in rez.items() if not k.startswith("_")}
        pathlib.Path(args.json).write_text(json.dumps(iesire, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
