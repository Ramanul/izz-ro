#!/usr/bin/env python3
"""Scaneaza homepage-urile tuturor primariilor, capturând semnături de eroare.

Atingere simpla: o cerere GET per domeniu, paralelă max 24, pe domeniile cu
rss_ok != yes și dns_ok != no (vor fi ~1535 - 407 = 1128 rânduri).

Rezultat: data/local/scan_homepages_2026-08-14.json, unde fiecare intrare
înregistrează error_sig, error_type (categorisit), și alte metadate.
"""

import csv
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# Reconfigurează stdout pentru UTF-8 INAINTE de orice print.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Importează constante din generator
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    from generator.fetch import USER_AGENT, TIMEOUT
except ImportError:
    # Fallback ca nu s-a importat bine
    USER_AGENT = "IZZ.ro Bot/1.0 (+https://izz.ro)"
    TIMEOUT = 10

MAX_WORKERS = 24


def fetch_homepage(url: str) -> dict:
    """Cere GET pe url, captură semnătura de eroare. Tolerant la erori."""
    result = {
        "url": url,
        "status": None,
        "error_sig": None,
        "error_type": None,
        "error_msg": None,
    }

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            result["status"] = resp.status
            # Citim doar headers; nu e nevoie de body — doar vrem să lovim domeniul.
            return result
    except urllib.error.HTTPError as e:
        result["status"] = e.code
        result["error_type"] = "http_error"
        result["error_msg"] = str(e)
        return result
    except urllib.error.URLError as e:
        reason = str(e.reason) if e.reason else str(e)
        result["error_type"] = "url_error"
        result["error_msg"] = reason
        result["error_sig"] = reason
        # Semnătura care semnalează SSL UNEXPECTED_EOF (semn de Bitdefender)
        if "UNEXPECTED_EOF" in reason:
            result["error_type"] = "ssl_unexpected_eof"
        elif "getaddrinfo" in reason:
            result["error_type"] = "dns_resolution"
        elif "403" in reason:
            result["error_type"] = "forbidden"
        elif "404" in reason:
            result["error_type"] = "not_found"
        elif "503" in reason:
            result["error_type"] = "service_unavailable"
        elif "timeout" in reason.lower():
            result["error_type"] = "timeout"
        elif "certificate" in reason.lower():
            result["error_type"] = "ssl_cert_error"
        return result
    except (socket.timeout, ssl.SSLError, TimeoutError) as e:
        result["error_type"] = "socket_timeout" if isinstance(e, socket.timeout) else "ssl_error"
        result["error_msg"] = str(e)
        result["error_sig"] = str(e)
        return result
    except Exception as e:
        result["error_type"] = "other"
        result["error_msg"] = str(e)
        result["error_sig"] = str(e)
        return result


def scan_homepages(sample_limit: int | None = None) -> tuple[list, dict]:
    """Scaneaza homepage-urile primariilor. Returneaza (rezultate, histogramă de erori)."""

    # Citește CSV-ul
    csv_path = "data/primarii_status.csv"
    rows = []
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except OSError as e:
        print(f"Eroare la citire {csv_path}: {e}", file=sys.stderr)
        return [], {}

    # Filtrează: rss_ok != yes și dns_ok != no
    to_scan = []
    for row in rows:
        rss_ok = row.get("rss_ok", "").strip()
        dns_ok = row.get("dns_ok", "").strip()
        url = row.get("url", "").strip()
        localitate = row.get("localitate", "").strip()

        if rss_ok == "yes":  # Skip dacă deja am RSS check OK
            continue
        if dns_ok == "no":  # Skip dacă DNS-ul e mort
            continue
        if not url or url == "N/A":
            continue

        to_scan.append({
            "judet": row.get("judet", "").strip(),
            "localitate": localitate,
            "url": url,
        })

    print(f"=== Scan homepages: {len(to_scan)} domeniile de scanat (rss_ok != yes, dns_ok != no) ===")

    if sample_limit:
        to_scan = to_scan[:sample_limit]
        print(f"(eșantion limitat la {len(to_scan)})")

    # Scanare paralelă
    results = []
    errors_by_type = defaultdict(int)
    unexpected_eof_domains = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_homepage, row["url"]): row for row in to_scan}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(to_scan)} ...")

            row = futures[future]
            result = future.result()
            result["judet"] = row["judet"]
            result["localitate"] = row["localitate"]
            results.append(result)

            if result["error_type"]:
                errors_by_type[result["error_type"]] += 1
                if result["error_type"] == "ssl_unexpected_eof":
                    unexpected_eof_domains.append({
                        "url": result["url"],
                        "localitate": result["localitate"],
                        "judet": result["judet"],
                    })

    # Statistici
    print(f"\n=== Rezumat ===")
    print(f"Total scanat: {len(results)}")
    alive = sum(1 for r in results if r["status"])
    dead = len(results) - alive
    print(f"Status OK (2xx-3xx): {alive}")
    print(f"HTTP error sau timeout: {dead}")
    print(f"\nDomenii cu UNEXPECTED_EOF (semnă Bitdefender): {len(unexpected_eof_domains)}")

    print(f"\n=== Histogramă de erori ===")
    for err_type in sorted(errors_by_type.keys()):
        count = errors_by_type[err_type]
        print(f"  {err_type:30s}: {count}")

    return results, unexpected_eof_domains, errors_by_type


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=None, help="Eșantion limitat la N rânduri")
    parser.add_argument("--out", default="data/local/scan_homepages_2026-08-14.json")
    args = parser.parse_args()

    results, unexpected_eof_domains, errors_by_type = scan_homepages(sample_limit=args.sample)

    # Scrie rezultatul
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    output = {
        "timestamp": "2026-08-14T00:00:00Z",  # Simulat
        "total_scanned": len(results),
        "unexpected_eof_count": len(unexpected_eof_domains),
        "error_histogram": dict(errors_by_type),
        "results": results,
        "unexpected_eof_domains": unexpected_eof_domains,
    }

    try:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=1)
        print(f"\nRezultat scris în: {args.out}")
    except OSError as e:
        print(f"Eroare la scriere: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
