#!/usr/bin/env python
"""Verificare vizuala live + regresie Canvas/scroll/redraw."""
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
    return p.evaluate("""() => {const c=document.querySelector('#map canvas.map-canvas');return {canvas:document.querySelectorAll('#map canvas.map-canvas').length,w:c?.width||0,h:c?.height||0,cssW:c?.clientWidth||0,cssH:c?.clientHeight||0};}""")
def canvas_signature(p):
    return p.evaluate("""() => {const c=document.querySelector('#map canvas.map-canvas'); if(!c) return null; const x=c.getContext('2d'); const step=Math.max(1,Math.floor(Math.max(c.width,c.height)/80)); let h=2166136261; for(let y=0;y<c.height;y+=step) for(let xx=0;xx<c.width;xx+=step){const d=x.getImageData(xx,y,1,1).data; for(const v of d){h^=v; h=Math.imul(h,16777619);}} return h>>>0;}""")
def check_map(p,mobile=False):
    p.wait_for_selector('#map canvas.map-canvas',timeout=15000)
    p.wait_for_selector('#news-list .news-item',timeout=15000)
    s0=map_state(p); sig0=canvas_signature(p)
    check(s0['canvas']==1,f"un singur Canvas initial ({s0['canvas']})")
    check(s0['w']>0 and s0['h']>0 and s0['cssW']>0 and s0['cssH']>0,"Canvas are dimensiuni valide")
    check(p.locator('#news-list .news-item').count()>0,"lista are articole")
    # Reproduce bugul: scroll repetat. Canvasul si imaginea randata trebuie sa ramana stabile.
    for _ in range(12):
        p.mouse.wheel(0,900); p.wait_for_timeout(60); p.mouse.wheel(0,-900); p.wait_for_timeout(60)
    s1=map_state(p); sig1=canvas_signature(p)
    check(s1['canvas']==1,f"scroll repetat pastreaza un singur Canvas ({s1['canvas']})")
    check((s1['w'],s1['h'])==(s0['w'],s0['h']),"scrollul nu modifica backing store")
    check(sig1==sig0,f"randarea Canvas ramane identica dupa scroll ({sig0} -> {sig1})")
    # Resize/repaint repetat; fiecare stare trebuie sa aiba exact un Canvas valid.
    for w in [1100,900,700,390,1280,1024]:
        p.set_viewport_size({'width':w,'height':844 if w<600 else 900}); p.wait_for_timeout(150)
        st=map_state(p)
        check(st['canvas']==1,f"resize {w}px pastreaza un Canvas")
        check(st['w']>0 and st['h']>0 and st['cssW']>0 and st['cssH']>0,f"resize {w}px pastreaza Canvas randabil")
    if mobile:
        over=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth'); check(over<=0,f"mobil fara overflow orizontal ({over}px)")
def main():
    os.makedirs(SHOT_DIR,exist_ok=True)
    with sync_playwright() as pw:
        br=pw.chromium.launch(args=['--no-sandbox','--disable-dev-shm-usage'])
        p=br.new_page(viewport={'width':1280,'height':900})
        goto(p,BASE+'/static/harta-stiri/','harta','domcontentloaded'); check_map(p); p.screenshot(path=f'{SHOT_DIR}/harta-regression.png',full_page=True)
        mob=br.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        goto(mob,BASE+'/static/harta-stiri/','mobile','domcontentloaded'); check_map(mob,True); mob.screenshot(path=f'{SHOT_DIR}/harta-mobile-regression.png',full_page=True)
        mob.close(); br.close()
    if fails:
        print('\nFAIL'); [print(' -',x) for x in fails]; return 1
    print('\nOK: regresia Canvas/scroll/resize a trecut.')
    return 0
if __name__=='__main__': sys.exit(main())
