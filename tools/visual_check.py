#!/usr/bin/env python
"""Verificare vizuala live + regresie pentru Canvas/scroll/redraw."""
import os, sys
from playwright.sync_api import sync_playwright
BASE=os.getenv("BASE_URL","https://izz.ro").rstrip("/")
SHOT_DIR=os.getenv("SHOT_DIR","shots")
fails=[]
def check(c,r):
    print(f"  {'ok ' if c else 'FAIL'} {r}")
    if not c: fails.append(r)
def goto(p,u,label,wait="load"):
    try:p.goto(u,wait_until=wait)
    except Exception as e:
        print(f"  FAIL navigare {label}: {e}"); raise
def map_state(p):
    return p.evaluate("""() => {const cs=[...document.querySelectorAll('#map canvas.map-canvas')];return {canvas:cs.length, w:cs[0]?.width||0,h:cs[0]?.height||0, host:document.querySelector('#map')?.getBoundingClientRect().height||0};}""")
def check_map(p,mobile=False):
    p.wait_for_selector('#map canvas.map-canvas',timeout=15000)
    p.wait_for_selector('#news-list .news-item',timeout=15000)
    s0=map_state(p); check(s0['canvas']==1,f"un singur Canvas initial ({s0['canvas']})"); check(s0['w']>0 and s0['h']>0,"Canvas backing store valid")
    check(p.locator('#news-list .news-item').count()>0,"lista are articole")
    # Regresie exact pentru bugul raportat: scroll nu trebuie sa multiplice Canvas-ul sau sa schimbe numarul markerilor.
    # Markerii sunt Canvas, deci numarul lor este expus de aplicatie ca map.__markerCount pentru testare.
    m0=p.evaluate("() => window.__izzMapDebug?.markerCount ?? null")
    for _ in range(12):
        p.mouse.wheel(0,900); p.wait_for_timeout(50); p.mouse.wheel(0,-900); p.wait_for_timeout(50)
    s1=map_state(p); m1=p.evaluate("() => window.__izzMapDebug?.markerCount ?? null")
    check(s1['canvas']==1,f"scroll repetat pastreaza un singur Canvas ({s1['canvas']})")
    check(s1['w']==s0['w'] and s1['h']==s0['h'],"scrollul nu modifica backing store")
    if m0 is not None and m1 is not None: check(m1==m0,f"scrollul nu multiplica markerii ({m0} -> {m1})")
    # Resize/repaint repetat.
    for w in [1100,900,700,390,1280,1024]:
        p.set_viewport_size({'width':w,'height':844 if w<600 else 900}); p.wait_for_timeout(100)
        st=map_state(p); check(st['canvas']==1,f"resize {w}px pastreaza un Canvas")
        check(st['w']>0 and st['h']>0,f"resize {w}px pastreaza Canvas randabil")
    if mobile:
        over=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth'); check(over<=0,f"mobil fara overflow orizontal ({over}px)")
def main():
    os.makedirs(SHOT_DIR,exist_ok=True)
    with sync_playwright() as pw:
        br=pw.chromium.launch(args=['--no-sandbox','--disable-dev-shm-usage'])
        p=br.new_page(viewport={'width':1280,'height':900})
        goto(p,BASE+'/static/harta-stiri/','harta', 'domcontentloaded'); check_map(p); p.screenshot(path=f'{SHOT_DIR}/harta-regression.png',full_page=True)
        mob=br.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        goto(mob,BASE+'/static/harta-stiri/','mobile','domcontentloaded'); check_map(mob,True); mob.screenshot(path=f'{SHOT_DIR}/harta-mobile-regression.png',full_page=True)
        mob.close(); br.close()
    if fails:
        print('\nFAIL'); [print(' -',x) for x in fails]; return 1
    print('\nOK: regresia Canvas/scroll/resize a trecut.')
    return 0
if __name__=='__main__': sys.exit(main())
