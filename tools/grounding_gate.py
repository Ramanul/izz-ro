#!/usr/bin/env python3
"""Blocking gate for deterministic AI/source consistency checks.

`generator.raport_copiere` writes one JSON object per processed AI item to the path in
`IZZ_RAPORT_COPIERE_GATE`.  This command is intentionally separate from the reporting
journal: reports remain observational, while this gate is a release control.

Only deterministic, high-confidence violations block:
- invented quotation text;
- numbers appearing in the AI output that are absent from the source.

The uncertainty marker check (`rezerva_pierduta`) remains advisory because it is a
heuristic and may concern a secondary source detail that was intentionally omitted from
the summary.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPORT_ENV = "IZZ_RAPORT_COPIERE_GATE"


def main() -> int:
    raw_path = os.environ.get(REPORT_ENV, "").strip()
    if not raw_path:
        print(f"OK: {REPORT_ENV} nu este configurat; grounding gate nu are date de verificat.")
        return 0

    path = Path(raw_path)
    if not path.exists():
        print(f"OK: grounding gate — nu exista raport pentru rularea curenta: {path}")
        return 0

    blocking: list[dict] = []
    advisory: list[dict] = []
    malformed = 0
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            for issue in row.get("blocking_issues", []) or []:
                blocking.append({
                    "line": line_no,
                    "id": row.get("id", ""),
                    "model": row.get("model", ""),
                    "issue": issue,
                })
            for issue in row.get("advisory_issues", []) or []:
                advisory.append({
                    "line": line_no,
                    "id": row.get("id", ""),
                    "model": row.get("model", ""),
                    "issue": issue,
                })

    print(
        f"=== AI grounding gate ===\n"
        f"intrari verificate: {sum(1 for _ in path.open('r', encoding='utf-8'))}\n"
        f"blocante: {len(blocking)} | advisory: {len(advisory)} | malformed: {malformed}"
    )
    for item in blocking[:25]:
        print(f"FAIL [{item['model']}] {item['id']}: {item['issue']}")
    if len(blocking) > 25:
        print(f"... si inca {len(blocking) - 25} incalcari blocante")
    for item in advisory[:10]:
        print(f"WARN [{item['model']}] {item['id']}: {item['issue']}")

    if malformed:
        print(f"FAIL: raportul grounding contine {malformed} linii JSON invalide.")
        return 1
    if blocking:
        print("FAIL: publicarea este blocata de verificari deterministe de grounding.")
        return 1
    print("OK: niciun caz blocant de grounding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
