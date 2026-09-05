#!/usr/bin/env python3
"""Query TED Open Data and normalize procurement observations.

TED documents a public SPARQL endpoint at https://data.ted.europa.eu/ and
publishes procurement data as Linked Open Data. This adapter keeps the query
explicit and stores only normalized observations so downstream products are
not coupled to RDF implementation details.

Usage:
  python tools/sync_ted.py --query-file tools/queries/ted_ro_contracts.rq \
    --since 2026-08-28 --out data/ted_observations.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENDPOINT = "https://data.ted.europa.eu/"


def query_ted(query: str, endpoint: str, timeout: int = 60) -> dict:
    payload = urlencode({"query": query, "format": "application/sparql-results+json"}).encode()
    request = Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json, application/json",
            "User-Agent": "izz-ro-intelligence/1.0",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def normalize(payload: dict, query: str, endpoint: str) -> dict:
    rows = payload.get("results", {}).get("bindings", [])
    observations = []
    for row in rows:
        def val(name: str) -> str | None:
            item = row.get(name)
            return item.get("value") if item else None

        observations.append({
            "source": "TED Open Data",
            "source_url": endpoint,
            "publication_number": val("publicationNumber"),
            "legal_name": val("legalName"),
            "procedure_type": val("procedureType"),
            "country": val("country"),
            "publication_date": val("publicationDate"),
            "value_eur": val("valueEur"),
        })
    return {
        "source": {
            "id": "ted-open-data",
            "name": "TED Open Data",
            "endpoint": endpoint,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
        "query": query,
        "count": len(observations),
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-file", required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--since", help="ISO date injected into {{SINCE}} in the query")
    parser.add_argument("--out", default="data/ted_observations.json")
    args = parser.parse_args()

    query = (ROOT / args.query_file).read_text(encoding="utf-8")
    if "{{SINCE}}" in query:
        if not args.since:
            raise SystemExit("--since este obligatoriu când query-ul conține {{SINCE}}")
        query = query.replace("{{SINCE}}", args.since)
    payload = query_ted(query, args.endpoint)
    result = normalize(payload, query, args.endpoint)
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {result['count']} observații TED normalizate")
    print(f"output: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
