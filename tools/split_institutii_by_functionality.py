#!/usr/bin/env python
"""Generează liste separate pentru instituții județene pe categorii de funcționalitate."""
import csv
import sys
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

INPUT_CSV = "data/institutii_judetene_status.csv"
OUTPUT_DIR = "data/institutii_lists"

CATEGORIES = {
    "rss_working": lambda r: r["rss_ok"] == "yes",
    "rss_not_working_alive": lambda r: r["rss_ok"] == "no" and r["http_status"] and r["http_status"] != "0",
    "dead": lambda r: r["http_status"] == "0" or r["http_status"] == "",
    "recent_content": lambda r: r["last_signal_date"] and r["last_signal_date"].startswith(("2025", "2026")),
    "old_content": lambda r: r["last_signal_date"] and not r["last_signal_date"].startswith(("2025", "2026")),
    "no_content_date": lambda r: not r["last_signal_date"],
    "wordpress": lambda r: r["cms"] == "wordpress",
    "joomla": lambda r: r["cms"] == "joomla",
    "drupal": lambda r: r["cms"] == "drupal",
    "e_adm": lambda r: r["cms"] == "e-adm",
    "other_cms": lambda r: r["cms"] == "other",
    "unknown_cms": lambda r: r["cms"] == "unknown",
    "https": lambda r: r["https_ok"] == "yes",
    "http_only": lambda r: r["https_ok"] == "no" and r["http_status"] and r["http_status"] != "0",
    "real_institutie": lambda r: r["is_institutie"] == "yes",
    "unclear_institutie": lambda r: r["is_institutie"] == "unclear",
    "prefectura": lambda r: r["tip"] == "Prefectură",
    "consiliu_judetean": lambda r: r["tip"] == "Consiliu Județean",
}

def main():
    # Read input CSV
    rows = []
    try:
        with open(INPUT_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except OSError as e:
        print(f"Eroare la citire {INPUT_CSV}: {e}")
        return 1

    print(f"Total instituții județene: {len(rows)}")

    # Categorize
    categorized = defaultdict(list)
    for row in rows:
        for category, predicate in CATEGORIES.items():
            if predicate(row):
                categorized[category].append(row)

    # Write separate CSVs
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for category, category_rows in categorized.items():
        output_path = f"{OUTPUT_DIR}/{category}.csv"
        try:
            with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
                if category_rows:
                    fieldnames = category_rows[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(category_rows)
            print(f"{category}: {len(category_rows)} -> {output_path}")
        except OSError as e:
            print(f"Eroare la scriere {output_path}: {e}")

    # Summary
    print(f"\n=== Rezumat categorii ===")
    for category in sorted(CATEGORIES.keys()):
        count = len(categorized[category])
        print(f"{category}: {count}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
