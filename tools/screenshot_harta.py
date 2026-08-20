#!/usr/bin/env python
"""Captura harta la 1280px și 390px."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

BASE = os.getenv("MAP_URL", "http://localhost:8765/")

def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(args=["--no-sandbox"])

        # Desktop 1280px
        p1 = br.new_page(viewport={"width": 1280, "height": 900})
        p1.goto(BASE, wait_until="networkidle")
        p1.wait_for_selector("#news-list li a", timeout=15000)
        p1.screenshot(path="/tmp/harta-1280px.png", full_page=True)
        print("Screenshot 1280px saved to /tmp/harta-1280px.png")

        # Mobile 390px
        p2 = br.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        p2.goto(BASE, wait_until="networkidle")
        p2.wait_for_selector("#news-list li a", timeout=15000)
        p2.screenshot(path="/tmp/harta-390px.png", full_page=True)
        print("Screenshot 390px saved to /tmp/harta-390px.png")

        br.close()

if __name__ == "__main__":
    import sys
    # Windows: cp1252 nu are „ș"/„ț", deci un `print` cu diacritice arunca
    # UnicodeEncodeError si scriptul iese cu 1 — indistingibil de un esec real de
    # continut. Masurat 2026-08-20: `qa_check.py` iesea cu 1 pe date valide, iar cu
    # PYTHONIOENCODING=utf-8 cu 0. In CI (Linux, UTF-8) nu se vede. Acelasi idiom ca
    # in `scan_homepages.py`, extins la toate punctele de intrare cu diacritice.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    main()
