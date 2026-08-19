#!/usr/bin/env python3
"""Verifică UAT Timiș și badge-ul numeric la viewport mobil."""
from __future__ import annotations

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.getenv("MAP_URL", "http://localhost:8766/static/harta-stiri/")
OUT = Path("/tmp/harta-timis-uat-390px.png")

with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page.goto(BASE + "?judet=TIMIS", wait_until="networkidle")
    page.wait_for_function("() => document.querySelector('#map canvas') && document.querySelectorAll('#news-list li a').length > 0")
    page.wait_for_timeout(1200)
    result = page.evaluate("""() => {
      const canvas = document.querySelector('#map canvas');
      const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
      let badgePixels = 0;
      for (let i = 0; i < pixels.length; i += 4) {
        if (pixels[i] > 130 && pixels[i + 1] < 180 && pixels[i + 2] < 120) badgePixels += 1;
      }
      return {
        scrollWidth: document.documentElement.scrollWidth,
        viewportWidth: innerWidth,
        canvas: { width: canvas.width, height: canvas.height },
        badgePixels,
        selected: document.querySelector('#county-picker [aria-pressed=\"true\"]')?.textContent || '',
      };
    }""")
    if result["scrollWidth"] > result["viewportWidth"]:
        raise AssertionError(f"Overflow orizontal: {result}")
    if result["badgePixels"] < 20:
        raise AssertionError(f"Badge UAT absent: {result}")
    page.screenshot(path=str(OUT), full_page=True)
    print(result)
    print(f"screenshot={OUT}")
    browser.close()
