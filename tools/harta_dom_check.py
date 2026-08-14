#!/usr/bin/env python
"""Verificare DOM randat pentru harta stirilor. Ruleaza cu serverul local pornit:
   python -m http.server 8765 --directory static/harta-stiri
Asserteaza pe STRUCTURA VIZIBILA (id-uri + taguri), nu pe clase CSS -- clasele s-au dovedit
de doua ori identificatori morti in repo-ul asta (vezi IZZ-0177, IZZ-0182)."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

BASE = os.getenv("MAP_URL", "http://localhost:8765/")
fails = []

def check(cond, label):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}")
    if not cond:
        fails.append(label)

def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(args=["--no-sandbox"])
        p = br.new_page(viewport={"width": 1280, "height": 900})
        p.goto(BASE, wait_until="networkidle")
        p.wait_for_selector("#news-list li", timeout=15000)

        # --- FELIA 1: lista de rezultate ---
        # Asteapta explicit sa avem cel putin un element de stire (nu doar placeholder)
        p.wait_for_function("() => document.querySelector('#news-list li a') !== null", timeout=15000)
        box = p.evaluate("""() => {
          const li = document.querySelector('#news-list li');
          const a = li ? li.querySelector('a') : null;
          const s = li ? li.querySelector('span') : null;
          if (!a || !s) return { error: "missing a or span" };
          const ra = a.getBoundingClientRect(), rs = s.getBoundingClientRect();
          return {
            tag: document.querySelector('#news-list').tagName,
            aDisplay: getComputedStyle(a).display,
            sDisplay: getComputedStyle(s).display,
            sameLine: Math.abs(ra.top - rs.top) < 2,
            gap: rs.top - ra.bottom,
            count: document.querySelector('#panel-count').textContent.trim(),
          };
        }""")
        print("  ", box)
        check(box["tag"] == "UL", f"#news-list este <ul> (e {box['tag']})")
        check(box["aDisplay"] == "block", f"titlul e bloc ({box['aDisplay']})")
        check(box["sDisplay"] == "block", f"meta e bloc ({box['sDisplay']})")
        check(not box["sameLine"], "titlul si meta NU sunt pe acelasi rand")
        check(box["gap"] >= 3, f"exista spatiu vertical intre titlu si meta ({box['gap']:.1f}px)")
        check(" din " in box["count"], f"panel-count arata totalul ('{box['count']}')")

        br.close()
    if fails:
        print("\nFAIL:"); [print(" -", f) for f in fails]; return 1
    print("\nOK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
