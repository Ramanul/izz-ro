#!/usr/bin/env python3
"""Verifică harta UAT pentru Timiș la nivel de browser."""
from __future__ import annotations

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.getenv("MAP_URL", "http://localhost:8766/static/harta-stiri/")
OUT = Path("/tmp/harta-timis-uat.png")
REGIONAL_OUT = Path("/tmp/harta-regional.png")

with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(BASE + "?judet=TIMIS", wait_until="networkidle")
    page.wait_for_function("() => document.querySelector('canvas') && document.querySelectorAll('#news-list li a').length > 0")
    page.wait_for_timeout(1200)
    result = page.evaluate("""() => {
      const canvas = document.querySelector('#map canvas');
      const context = canvas.getContext('2d');
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      const hot = [];
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index] > 130 && pixels[index + 1] < 180 && pixels[index + 2] < 120) {
          hot.push(index / 4);
        }
      }
      const rect = canvas.getBoundingClientRect();
      const average = hot.reduce((sum, pixel) => ({
        x: sum.x + (pixel % canvas.width), y: sum.y + Math.floor(pixel / canvas.width),
      }), {x: 0, y: 0});
      const badge = hot.length ? {
        x: rect.left + (average.x / hot.length) * rect.width / canvas.width,
        y: rect.top + (average.y / hot.length) * rect.height / canvas.height,
        pixels: hot.length,
      } : null;
      return {
        url: location.search,
        uatRequestVisible: canvas?.width > 0,
        selected: document.querySelector('#county-picker [aria-pressed=\"true\"]')?.textContent || '',
        count: document.querySelector('#panel-count')?.textContent || '',
        markers: [...document.querySelectorAll('#county-picker button')].filter(b => b.textContent.includes('TIMIS')).map(b => b.textContent),
        badge,
      };
    }""")
    if not result["badge"] or result["badge"]["pixels"] < 20:
        raise AssertionError(f"Nu a fost găsit un badge UAT vizibil: {result}")
    page.mouse.click(result["badge"]["x"], result["badge"]["y"])
    page.wait_for_timeout(250)
    result["url_after_uat_click"] = page.url
    page.screenshot(path=str(OUT), full_page=True)
    print(result)
    print(f"screenshot={OUT}")

    page.goto(BASE + "?nivel=regional", wait_until="networkidle")
    page.wait_for_function("() => document.querySelector('canvas') && document.querySelector('#panel-count')?.textContent")
    page.wait_for_timeout(350)
    regional = page.evaluate("""() => ({
      url: location.search,
      selected: [...document.querySelectorAll('[data-level]')].find(b => b.getAttribute('aria-pressed') === 'true')?.textContent || '',
      count: document.querySelector('#panel-count')?.textContent || '',
      regions: [...document.querySelectorAll('#county-picker button')].map(b => b.textContent),
    })""")
    page.screenshot(path=str(REGIONAL_OUT), full_page=True)
    print(regional)
    print(f"regional_screenshot={REGIONAL_OUT}")
    browser.close()
