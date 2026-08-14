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
    main()
