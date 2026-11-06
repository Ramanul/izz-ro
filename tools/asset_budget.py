#!/usr/bin/env python3
"""Asset census for the rendered output (asset budget telemetry).

Counts files by extension and top-level directory, compares the total against
the Workers Free static assets ceiling, and writes output/asset_budget.json so
a trend can be tracked over time (fetch it from the live origin).

Reporting is best-effort by default. --enforce blocks Cloudflare deployment
above the safety budget, the provider ceiling, or the per-file size limit.
Run after rendering and search indexing; this does not limit article length.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import pathlib
import sys

CEILING = int(os.getenv("OUTPUT_FILE_CEILING", "20000"))
BUDGET = int(os.getenv("OUTPUT_FILE_BUDGET", "17000"))
MAX_FILE_BYTES = 25 * 1024 * 1024
WARN, HIGH, CRIT = 0.80, 0.90, 0.95


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("output"))
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    out = args.output_dir
    if not out.is_dir():
        print(f"ASSET CENSUS: {out} lipseste - sar raportarea")
        return 1 if args.enforce else 0
    by_ext: collections.Counter = collections.Counter()
    by_top: collections.Counter = collections.Counter()
    # Reserve the report exactly once, including repeated runs on the same tree.
    report_path = out / "asset_budget.json"
    total = 1
    by_ext["json"] = 1
    by_top["(root)"] = 1
    oversized = []
    for p in out.rglob("*"):
        if p.is_file() and p != report_path:
            total += 1
            if p.stat().st_size > MAX_FILE_BYTES:
                oversized.append(str(p.relative_to(out)))
            by_ext[p.suffix.lower().lstrip(".") or "noext"] += 1
            rel = p.relative_to(out)
            by_top[rel.parts[0] if len(rel.parts) > 1 else "(root)"] += 1
    ratio = total / CEILING
    level = "OK" if ratio < WARN else "WARNING" if ratio < HIGH else "HIGH" if ratio < CRIT else "CRITICAL"
    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": total,
        "limit": CEILING,
        "budget": BUDGET,
        "max_file_bytes": MAX_FILE_BYTES,
        "oversized_files": oversized,
        "headroom": CEILING - total,
        "level": level,
        "by_extension": dict(by_ext.most_common()),
        "by_top_dir": dict(by_top.most_common(15)),
    }
    report_path.write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if report_path.stat().st_size > MAX_FILE_BYTES:
        oversized.append(report_path.name)
    print(f"ASSET CENSUS: {total}/{CEILING} ({ratio:.1%}) | headroom {CEILING - total} | nivel {level}")
    print("extensii:", ", ".join(f"{k}:{v}" for k, v in list(by_ext.most_common())[:8]))
    print("directoare:", ", ".join(f"{k}:{v}" for k, v in list(by_top.most_common())[:8]))
    if level != "OK":
        print(f"::warning::asset budget la {ratio:.1%} din plafon (nivel {level})")
    errors = []
    if total > CEILING:
        errors.append(f"provider ceiling exceeded: {total} > {CEILING}")
    elif total > BUDGET:
        errors.append(f"safety budget exceeded: {total} > {BUDGET}")
    if oversized:
        errors.append(f"file size exceeds {MAX_FILE_BYTES} bytes: {', '.join(oversized)}")
    for error in errors:
        print(f"::{'error' if args.enforce else 'warning'}::{error}")
    if args.enforce and errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
