#!/usr/bin/env python3
"""Asset census for the rendered output (asset budget telemetry).

Counts files by extension and top-level directory, compares the total against
the Workers Free static assets ceiling, and writes output/asset_budget.json so
a trend can be tracked over time (fetch it from the live origin).

Best-effort reporting only: never fails the build. Thresholds (80/90/95% of the
ceiling) surface as warnings in the deploy log; blocking stays the renderer's
own OUTPUT_FILE_BUDGET/OUTPUT_FILE_CEILING logic.
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import pathlib
import sys

CEILING = int(os.getenv("OUTPUT_FILE_CEILING", "20000"))
WARN, HIGH, CRIT = 0.80, 0.90, 0.95


def main() -> int:
    args = sys.argv[1:]
    out = pathlib.Path(args[args.index("--output-dir") + 1]) if "--output-dir" in args else pathlib.Path("output")
    if not out.is_dir():
        print(f"ASSET CENSUS: {out} lipseste - sar raportarea")
        return 0
    by_ext: collections.Counter = collections.Counter()
    by_top: collections.Counter = collections.Counter()
    total = 0
    for p in out.rglob("*"):
        if p.is_file():
            total += 1
            by_ext[p.suffix.lower().lstrip(".") or "noext"] += 1
            rel = p.relative_to(out)
            by_top[rel.parts[0] if len(rel.parts) > 1 else "(root)"] += 1
    ratio = total / CEILING
    level = "OK" if ratio < WARN else "WARNING" if ratio < HIGH else "HIGH" if ratio < CRIT else "CRITICAL"
    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": total,
        "limit": CEILING,
        "headroom": CEILING - total,
        "level": level,
        "by_extension": dict(by_ext.most_common()),
        "by_top_dir": dict(by_top.most_common(15)),
    }
    (out / "asset_budget.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"ASSET CENSUS: {total}/{CEILING} ({ratio:.1%}) | headroom {CEILING - total} | nivel {level}")
    print("extensii:", ", ".join(f"{k}:{v}" for k, v in list(by_ext.most_common())[:8]))
    print("directoare:", ", ".join(f"{k}:{v}" for k, v in list(by_top.most_common())[:8]))
    if level != "OK":
        print(f"::warning::asset budget la {ratio:.1%} din plafon (nivel {level})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
