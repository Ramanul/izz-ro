#!/usr/bin/env python3
"""Export the IZZ Intelligence dataset as stable JSON or CSV.

The export keeps product records separate from source metadata. It is suitable as the first
machine-readable surface while the D1/API adapter is being wired in.

Usage:
  python tools/export_intelligence.py --format json --out output/intelligence.json
  python tools/export_intelligence.py --format csv --section market --out output/market.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generator.intelligence import validate_dataset

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "static" / "inteligenta" / "data.json"
SECTIONS = ("catalog", "providers", "companies", "market", "commerce", "events")


def load() -> dict[str, Any]:
    with DATA.open(encoding="utf-8") as handle:
        data = json.load(handle)
    errors = validate_dataset(data)
    if errors:
        raise SystemExit("Invalid intelligence dataset: " + "; ".join(errors))
    return data


def flatten(section: str, value: Any) -> list[dict[str, Any]]:
    if section == "companies":
        rows = []
        for cui, company in value.items():
            for change in company.get("changes", []):
                rows.append({"cui": cui, "name": company.get("name"), "city": company.get("city"), **change})
        return rows
    if isinstance(value, list):
        return value
    return [{"key": key, **(item if isinstance(item, dict) else {"value": item})} for key, item in value.items()]


def export_json(data: dict[str, Any], section: str | None) -> dict[str, Any]:
    payload = data if not section else {section: data[section]}
    return {
        "schema": "izz-intelligence-v1",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "section": section or "all",
        "data": payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--section", choices=SECTIONS)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = load()
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "json":
        output.write_text(json.dumps(export_json(data, args.section), ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        if not args.section:
            raise SystemExit("--section is required for CSV export")
        rows = flatten(args.section, data[args.section])
        if not rows:
            output.write_text("", encoding="utf-8")
        else:
            fields = sorted({key for row in rows for key in row})
            with output.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
    print(f"OK: {args.format} export -> {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
