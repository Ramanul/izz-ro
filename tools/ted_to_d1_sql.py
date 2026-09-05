#!/usr/bin/env python3
"""Convert normalized TED observations to idempotent D1 SQL.

The importer intentionally emits plain SQL instead of talking to Cloudflare so it can be
reviewed, tested, and executed with Wrangler in the user's own account.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sql_text(value: str | None) -> str:
    return "NULL" if value is None else "'" + str(value).replace("'", "''") + "'"


def stable_id(*parts: str | None) -> str:
    raw = "\x1f".join(str(part or "") for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def render(payload: dict) -> str:
    source = payload["source"]
    source_id = "ted-open-data"
    source_url = source["endpoint"]
    lines = ["BEGIN TRANSACTION;", "PRAGMA foreign_keys = ON;", ""]
    lines.append(
        "INSERT INTO sources (id, name, url, kind, license, last_seen_at, enabled) "
        f"VALUES ({sql_text(source_id)}, {sql_text(source['name'])}, {sql_text(source_url)}, 'api', NULL, "
        f"{sql_text(source['retrieved_at'])}, 1) "
        "ON CONFLICT(id) DO UPDATE SET last_seen_at=excluded.last_seen_at, enabled=1;"
    )
    for obs in payload.get("observations", []):
        legal_name = obs.get("legal_name") or "Unknown organisation"
        external = obs.get("publication_number") or stable_id(legal_name)
        entity_id = stable_id("company", legal_name, external)
        now = source["retrieved_at"]
        lines.append(
            "INSERT INTO entities (id, kind, canonical_name, external_key, city, region, created_at, updated_at) "
            f"VALUES ({sql_text(entity_id)}, 'company', {sql_text(legal_name)}, {sql_text(external)}, NULL, NULL, "
            f"{sql_text(now)}, {sql_text(now)}) "
            "ON CONFLICT(id) DO UPDATE SET canonical_name=excluded.canonical_name, updated_at=excluded.updated_at;"
        )
        observation_id = stable_id("ted-observation", obs.get("publication_number"), obs.get("publication_date"), legal_name)
        title = obs.get("procedure_type") or "Public procurement notice"
        summary = f"TED publication {obs.get('publication_number') or 'n/a'}"
        lines.append(
            "INSERT OR IGNORE INTO observations "
            "(id, entity_id, source_id, observed_at, published_at, type, title, summary, url, value_number, value_currency, confidence, payload_json) "
            f"VALUES ({sql_text(observation_id)}, {sql_text(entity_id)}, {sql_text(source_id)}, {sql_text(now)}, "
            f"{sql_text(obs.get('publication_date'))}, 'procurement', {sql_text(title)}, {sql_text(summary)}, "
            f"{sql_text(source_url)}, NULL, 'EUR', 100, {sql_text(json.dumps(obs, ensure_ascii=False, separators=(',', ':')))});"
        )
    lines.extend(["", "COMMIT;", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", default="data/ted_observations.json")
    parser.add_argument("--out", default="data/ted_intelligence.sql")
    args = parser.parse_args()
    payload = json.loads((ROOT / args.input).read_text(encoding="utf-8"))
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(payload), encoding="utf-8")
    print(f"OK: {len(payload.get('observations', []))} observații → {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
