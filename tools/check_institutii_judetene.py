#!/usr/bin/env python
"""Scanner de verificare a site-urilor prefecturilor și consiliilor județene din România.

  python tools/check_institutii_judetene.py --out data/institutii_judetene_status.csv

Auditează fiecare site din data/institutii_judetene.csv: accesibilitate,
verificare dacă e un site real de instituție județeană, detecție CMS, existență RSS feed,
prospetime (last_signal_date). Tolerante complete la erori — un site mort e
o linie în raport, nu un crash.
"""
import argparse
import csv
import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
DEFAULT_TIMEOUT = 15
DEFAULT_WORKERS = 30


class LinkExtractor(HTMLParser):
    """Extrage <link> tags pentru RSS detection."""
    def __init__(self):
        super().__init__()
        self.rss_links = []

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            attrs_dict = dict(attrs)
            link_type = attrs_dict.get("type", "").lower()
            href = attrs_dict.get("href", "")
            if "rss" in link_type or "atom" in link_type:
                self.rss_links.append(href)


def check_dns(hostname: str, timeout: int) -> bool:
    """Verifică dacă hostname-ul are DNS resolution."""
    try:
        socket.gethostbyname(hostname)
        return True
    except (socket.gaierror, socket.timeout):
        return False


def normalize_url(url: str) -> str:
    """Adaugă schema dacă lipsește, curăță trailing slash."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def fetch_url(url: str, timeout: int) -> tuple[int, str, str, str | None]:
    """Returnează (status, final_url, body, error). Tolerant la erori."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            final_url = resp.geturl()
            body = resp.read().decode("utf-8", errors="ignore")
            return status, final_url, body, None
    except urllib.error.HTTPError as e:
        return e.code, url, "", str(e)
    except urllib.error.URLError as e:
        return 0, url, "", str(e.reason) if e.reason else str(e)
    except (socket.timeout, ssl.SSLError, Exception) as e:
        return 0, url, "", str(e)


def detect_institutie(html: str, judet: str, tip: str) -> str:
    """Heuristici pentru a detecta dacă e un site de instituție județeană."""
    if not html:
        return "unclear"
    html_lower = html.lower()
    keywords = ["prefectură", "prefectura", "consiliu județean", "consiliul județean", "cj", "instituția prefectului"]
    judet_lower = judet.lower()
    tip_lower = tip.lower()
    found_primary = any(kw in html_lower for kw in keywords)
    found_judet = judet_lower in html_lower
    found_tip = tip_lower in html_lower
    if found_primary or (found_judet and found_tip):
        return "yes"
    return "unclear"


def detect_cms(html: str) -> str:
    """Detectează CMS din HTML markers."""
    if not html:
        return "unknown"
    html_lower = html.lower()
    if "wp-content" in html_lower or "wordpress" in html_lower:
        return "wordpress"
    if "/joomla/" in html_lower or "joomla" in html_lower:
        return "joomla"
    if "/drupal/" in html_lower or "drupal" in html_lower:
        return "drupal"
    if "e-adm" in html_lower or "eadm" in html_lower:
        return "e-adm"
    return "other"


def extract_rss_links(html: str, base_url: str) -> list[str]:
    """Extrage RSS URLs din <link> tags."""
    parser = LinkExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    links = []
    for href in parser.rss_links:
        if href:
            absolute = urljoin(base_url, href)
            links.append(absolute)
    return links


def check_rss_url(url: str, timeout: int) -> bool:
    """Verifică dacă URL-ul e un RSS feed valid."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            body = resp.read().decode("utf-8", errors="ignore").lower()
            return "<rss" in body or "<feed" in body
    except Exception:
        return False


def find_rss(base_url: str, html: str, timeout: int) -> tuple[str | None, bool]:
    """Încearcă să găsească și verifice un RSS feed."""
    # 1. Din <link> tags
    for rss_url in extract_rss_links(html, base_url):
        if check_rss_url(rss_url, timeout):
            return rss_url, True
    # 2. Common paths
    common_paths = ["/feed", "/rss", "/feed.xml", "/rss.xml", "/atom.xml"]
    for path in common_paths:
        rss_url = urljoin(base_url, path)
        if check_rss_url(rss_url, timeout):
            return rss_url, True
    return None, False


def extract_last_signal_date(html: str, rss_body: str | None) -> str:
    """Extrage cea mai recentă dată ISO din RSS, sitemap, sau HTML."""
    if rss_body:
        # Parse RSS/Atom for dates
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        dates = re.findall(date_pattern, rss_body)
        if dates:
            return max(dates)
    if html:
        # YYYY patterns in HTML
        year_pattern = r'\b(202[0-9])\b'
        years = re.findall(year_pattern, html)
        if years:
            return max(years) + "-01-01"  # approximare
    return ""


def extract_copyright_year(html: str) -> str:
    """Extrage anul din copyright footer."""
    if not html:
        return ""
    match = re.search(r'©\s*(\d{4})', html)
    if match:
        return match.group(1)
    match = re.search(r'copyright\s*(\d{4})', html, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def check_site(row: dict, timeout: int) -> dict:
    """Verifică un singur site și returnează rezultatul."""
    judet = row.get("Județ", "").strip()
    tip = row.get("Tip", "").strip()
    url_raw = row.get("Website", "").strip()
    url = normalize_url(url_raw)
    parsed = urlparse(url)
    hostname = parsed.hostname if parsed.hostname else ""

    result = {
        "judet": judet,
        "tip": tip,
        "url": url,
        "dns_ok": "no",
        "http_status": "",
        "final_url": "",
        "https_ok": "no",
        "is_institutie": "unclear",
        "cms": "unknown",
        "rss_url": "",
        "rss_ok": "no",
        "last_signal_date": "",
        "copyright_year": "",
        "error": "",
    }

    if not hostname:
        result["error"] = "invalid_url"
        return result

    # DNS check
    if not check_dns(hostname, timeout):
        result["error"] = "dns_failed"
        return result
    result["dns_ok"] = "yes"

    # HTTPS first, fallback to HTTP
    tried_urls = []
    if url.startswith("https://"):
        tried_urls.append(url)
        tried_urls.append(url.replace("https://", "http://"))
    else:
        tried_urls.append(url.replace("http://", "https://"))
        tried_urls.append(url)

    for try_url in tried_urls:
        status, final_url, body, error = fetch_url(try_url, timeout)
        if status and status < 400:
            result["http_status"] = str(status)
            result["final_url"] = final_url
            result["https_ok"] = "yes" if final_url.startswith("https://") else "no"
            result["is_institutie"] = detect_institutie(body, judet, tip)
            result["cms"] = detect_cms(body)
            result["copyright_year"] = extract_copyright_year(body)

            # RSS check
            rss_url, rss_ok = find_rss(final_url, body, timeout)
            result["rss_url"] = rss_url or ""
            result["rss_ok"] = "yes" if rss_ok else "no"

            # RSS body for date extraction
            rss_body = None
            if rss_ok and rss_url:
                try:
                    req = urllib.request.Request(rss_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        rss_body = resp.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
            result["last_signal_date"] = extract_last_signal_date(body, rss_body)
            return result

    result["error"] = error or "http_failed"
    return result


def main():
    parser = argparse.ArgumentParser(description="Scanner de verificare a site-urilor prefecturilor și consiliilor județene")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Număr thread-uri paralele")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout per request (secunde)")
    parser.add_argument("--out", default="data/institutii_judetene_status.csv", help="Path fișier output CSV")
    args = parser.parse_args()

    input_path = "data/institutii_judetene.csv"
    rows = []
    try:
        with open(input_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except OSError as e:
        print(f"Eroare la citire {input_path}: {e}")
        return 1

    print(f"=== Check instituții județene ({len(rows)} site-uri) ===")
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(check_site, row, args.timeout): row for row in rows}
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                print(f"  {result['judet']:15s} {result['tip']:20s} {result['http_status']:>4s} {result['is_institutie']:8s} {result['rss_ok']:3s} {result['error'] or ''}")
            except Exception as e:
                print(f"  EXCEPTION: {e}")

    # Write output CSV
    out_path = args.out
    fieldnames = [
        "judet", "tip", "url", "dns_ok", "http_status", "final_url",
        "https_ok", "is_institutie", "cms", "rss_url", "rss_ok",
        "last_signal_date", "copyright_year", "error"
    ]
    try:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    except OSError as e:
        print(f"Eroare la scriere {out_path}: {e}")
        return 1

    # Summary
    total = len(results)
    alive = sum(1 for r in results if r["http_status"] and r["http_status"] != "0")
    dead = total - alive
    real_institutie = sum(1 for r in results if r["is_institutie"] == "yes")
    rss_working = sum(1 for r in results if r["rss_ok"] == "yes")
    recent = sum(1 for r in results if r["last_signal_date"] and r["last_signal_date"].startswith(("2025", "2026")))

    print(f"\n=== Rezumat ===")
    print(f"Total: {total}")
    print(f"Alive: {alive}")
    print(f"Dead: {dead}")
    print(f"Real instituție județeană: {real_institutie}")
    print(f"RSS working: {rss_working}")
    print(f"Last signal 2025-2026: {recent}")
    print(f"\nScris în: {out_path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
