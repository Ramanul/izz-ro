#!/usr/bin/env python
"""Debug script — verifica ce se intampla pe pagina."""
import os
from playwright.sync_api import sync_playwright

BASE = os.getenv("MAP_URL", "http://localhost:8765/")

def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(args=["--no-sandbox"])
        p = br.new_page(viewport={"width": 1280, "height": 900})

        # Captura console logs și request-uri
        p.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        p.on("requestfailed", lambda req: print(f"[FAILED] {req.method} {req.url} -> {req.failure.error_text if hasattr(req.failure, 'error_text') else 'unknown'}"))

        p.goto(BASE, wait_until="networkidle")
        p.screenshot(path="/tmp/harta-debug.png")

        # Debug: structura DOM
        body_html = p.evaluate("() => document.body.innerHTML.substring(0, 500)")
        print(f"[DOM] body: {body_html[:200]}...")

        news_list_html = p.evaluate("() => { const nl = document.querySelector('#news-list'); return nl ? nl.innerHTML.substring(0, 500) : 'NOT FOUND'; }")
        print(f"[DOM] news-list: {news_list_html}")

        # Check de errors in window
        errors = p.evaluate("""() => {
          return window.__errors || [];
        }""")
        print(f"[JS] errors in window: {errors}")

        br.close()
        print("Screenshot saved to /tmp/harta-debug.png")

if __name__ == "__main__":
    main()
