#!/usr/bin/env python3
"""Discover public datasets from data.gov.ro using its CKAN API.

This tool deliberately stores metadata, not arbitrary third-party payloads. A later dataset-
specific adapter can normalize licensed resources into `observations` without coupling the
core pipeline to a single CKAN schema.

Usage:
  python tools/sync_datagov.py "achizitii publice" --out data/intelligence_sources.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CKAN_BASE = "https://data.gov.ro/api/3/action/package_search"


def search_datasets(query: str, rows: int = 20, timeout: int = 20) -> dict:
    params = urlencode({"q": query, "rows": max(1, min(rows, 100))})
    url = f"{CKAN_BASE}?{params}"
    request = Request(url, headers={"User-Agent": "izz-ro-intelligence/1.0"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if payload.get("success") is not True:
        raise RuntimeError("CKAN returned an unsuccessful response")
    return payload["result"]


def normalize(result: dict, query: str) -> dict:
    datasets = []
    for package in result.get("results", []):
        resources = []
        for resource in package.get("resources", []):
            resources.append({
                "id": resource.get("id"),
                "name": resource.get("name"),
                "format": resource.get("format"),
                "url": resource.get("url"),
                "last_modified": resource.get("last_modified"),
            })
        datasets.append({
            "id": package.get("id"),
            "name": package.get("name"),
            "title": package.get("title"),
            "notes": package.get("notes"),
            "url": package.get("url") or package.get("metadata_created"),
            "organization": (package.get("organization") or {}).get("title"),
            "metadata_modified": package.get("metadata_modified"),
            "license_id": package.get("license_id"),
            "resources": resources,
        })
    return {
        "source": {
            "id": "data.gov.ro",
            "name": "data.gov.ro",
            "api": CKAN_BASE,
            "query": query,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
        "count": len(datasets),
        "datasets": datasets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--rows", type=int, default=20)
    parser.add_argument("--out", default="data/intelligence_sources.json")
    args = parser.parse_args()

    result = normalize(search_datasets(args.query, args.rows), args.query)
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {result['count']} dataset-uri găsite pentru {args.query!r}")
    print(f"output: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
