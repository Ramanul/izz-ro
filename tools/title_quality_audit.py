#!/usr/bin/env python3
"""Audit determinist pentru titlurile oficiale afișate pe IZZ.ro.

Rulează fără servicii externe și fără judecată AI. Verifică exact contractul editorial
al generatorului: titlul sursei rămâne brut în date, iar titlul de afișare al oricărui
anunț oficial trebuie să fie nevid și să nu depășească limita de citire mobilă.

Exemple:
  python tools/title_quality_audit.py
  python tools/title_quality_audit.py --report /tmp/title-quality.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generator.select import _OFFICIAL_DISPLAY_TITLE_MAX, titlu_afisare  # noqa: E402

DEFAULT_STATE = ROOT / "data" / "articles.json"


def normalized_title(article: dict[str, Any]) -> str:
    """Returnează titlul sursei normalizat, fără a modifica articolul."""
    return " ".join((article.get("title") or "").split())


def audit(articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculează metrici și încălcări pentru anunțurile oficiale cu titlu."""
    official = [
        article for article in articles
        if article.get("processed_by") == "official" and normalized_title(article)
    ]
    rows: list[dict[str, Any]] = []
    for article in official:
        raw = normalized_title(article)
        display = titlu_afisare(article)
        rows.append(
            {
                "id": article.get("id"),
                "url": article.get("url"),
                "source_name": article.get("source_name"),
                "raw": raw,
                "display": display,
                "raw_characters": len(raw),
                "display_characters": len(display),
            }
        )

    too_long = [row for row in rows if row["display_characters"] > _OFFICIAL_DISPLAY_TITLE_MAX]
    empty = [row for row in rows if not row["display"].strip()]
    changed = [row for row in rows if row["raw"] != row["display"]]
    long_raw = [row for row in rows if row["raw_characters"] > _OFFICIAL_DISPLAY_TITLE_MAX]

    return {
        "contract": {
            "official_display_title_max": _OFFICIAL_DISPLAY_TITLE_MAX,
            "status": "pass" if not too_long and not empty else "fail",
        },
        "official_articles": len(rows),
        "raw_titles_over_limit": len(long_raw),
        "display_titles_over_limit": len(too_long),
        "empty_display_titles": len(empty),
        "titles_changed": len(changed),
        "mean_raw_characters": round(sum(row["raw_characters"] for row in rows) / len(rows), 1) if rows else 0,
        "mean_display_characters": round(sum(row["display_characters"] for row in rows) / len(rows), 1) if rows else 0,
        "violations": (too_long + empty)[:20],
        "longest_display_titles": sorted(rows, key=lambda row: row["display_characters"], reverse=True)[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="Fișierul JSON al corpusului")
    parser.add_argument("--report", type=Path, help="Scrie raportul JSON complet în această cale")
    args = parser.parse_args()

    try:
        articles = json.loads(args.state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: nu pot citi corpusul {args.state}: {exc}", file=sys.stderr)
        return 2

    if not isinstance(articles, list):
        print("ERROR: corpusul trebuie să fie o listă JSON de articole", file=sys.stderr)
        return 2

    result = audit(articles)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=== Audit titluri oficiale IZZ.ro ===")
    print(f"anunțuri oficiale evaluate      : {result['official_articles']}")
    print(f"titluri brute peste limită      : {result['raw_titles_over_limit']}")
    print(f"titluri afișate peste limită    : {result['display_titles_over_limit']}")
    print(f"titluri afișate goale           : {result['empty_display_titles']}")
    print(f"titluri ajustate pentru citire  : {result['titles_changed']}")
    print(f"medie caractere brut / afișat   : {result['mean_raw_characters']} / {result['mean_display_characters']}")

    if result["contract"]["status"] == "pass":
        print(f"OK: toate titlurile oficiale afișate respectă limita de {result['contract']['official_display_title_max']} caractere.")
        return 0

    print("FAIL: contractul de lizibilitate mobilă a fost încălcat.")
    for row in result["violations"]:
        print(f"- {row['display_characters']} caractere | {row['source_name']}: {row['display']}")
    return 1


if __name__ == "__main__":
    # Windows: cp1252 nu are „ș"/„ț", deci un `print` cu diacritice arunca
    # UnicodeEncodeError si scriptul iese cu 1 — indistingibil de un esec real de
    # continut. Masurat 2026-08-20: `qa_check.py` iesea cu 1 pe date valide, iar cu
    # PYTHONIOENCODING=utf-8 cu 0. In CI (Linux, UTF-8) nu se vede. Acelasi idiom ca
    # in `scan_homepages.py`, extins la toate punctele de intrare cu diacritice.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
