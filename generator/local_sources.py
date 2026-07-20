import csv
import os
import re


def _make_slug(judet: str, localitate: str) -> str:
    raw = f"{judet}_{localitate}".lower()
    slug = re.sub(r"[^a-z0-9]", "_", raw)
    slug = re.sub(r"_+", "_", slug)
    slug = slug.strip("_")
    return slug


def load_gold_sources(csv_path: str, limit: int, min_date: str = "2026-01-01") -> dict:
    if limit <= 0:
        return {}
    if not os.path.isfile(csv_path):
        return {}

    rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rss_url = (row.get("rss_url") or "").strip()
            if row.get("rss_ok") == "yes" and rss_url:
                last_date = (row.get("last_signal_date") or "").strip()
                if last_date and last_date >= min_date:
                    rows.append(row)

    rows.sort(key=lambda r: (r["judet"], r["localitate"]))
    rows.sort(key=lambda r: r.get("last_signal_date") or "", reverse=True)

    result = {}
    for row in rows[:limit]:
        slug = _make_slug(row["judet"], row["localitate"])
        key = "pl_" + slug
        if key not in result:
            result[key] = {
                "name": "Primăria " + row["localitate"].title(),
                "url": row["rss_url"].strip(),
                "category": "local",
            }

    return result
