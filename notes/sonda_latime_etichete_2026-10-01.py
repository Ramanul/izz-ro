# Sonda 2026-10-01: de ce se rupe "DÂMBOVIȚA" pe copertele `.art` (raportat pe /judetean/).
# Masoara latimile reale ale PlayfairDisplay 800 (acelasi TTF ca la raster) pentru TOT
# universul de etichete (județe, localități, regiuni, categorii) si le compara cu
# max-width-urile .art-body din static/styles.css, pe toate compozitiile x trepte.
# Criteriu de rupere UGLY: cel mai lat CUVANT simplu al etichetei nu incape pe un rand
# (atunci `overflow-wrap: anywhere` ta prin cuvant, ex. "DÂMBOVIȚ / A"). Etichetele
# multi-cuvant care depasesc max-width dar au cuvintele mici se RANDEAZA pe 2 randuri la
# spatiu — asta e acceptat de design, nu e defect.
# [FAPT] metrici reale din TTF; kerning ignorat (supraestimeaza usor latimea -> conservativ).
import json, re
from fontTools.ttLib import TTFont

font = TTFont("generator/assets/PlayfairDisplay_800ExtraBold.ttf")
upm = font["head"].unitsPerEm
cmap = font.getBestCmap()
hmtx = font["hmtx"]

def latime_em(s: str) -> float:
    total = 0
    for ch in s.upper():
        g = cmap.get(ord(ch))
        if g is None:
            raise SystemExit(f"glif lipseste in font: {ch!r} (U+{ord(ch):04X}) in {s!r}")
        total += hmtx[g][0]
    return total / upm

# universul de etichete, extras direct din gazetteer (acelasi cod ca in geo._incarca_etichete)
_gaz = json.load(open("data/localities.json", encoding="utf-8"))
etichete = set()
for _nume, _intrari in (_gaz.get("by_name") or {}).items():
    for _e in _intrari:
        if (_e.get("judet") or "").strip():
            etichete.add(re.sub(r"^Jude[țtT]ul\s+", "", _e["judet"]).strip())
        if (_e.get("label") or "").strip():
            etichete.add(_e["label"].strip())
etichete |= {"Transilvania", "Banat", "Moldova", "Muntenia", "Oltenia", "Dobrogea"}
etichete |= {"general", "regional", "judetean", "local", "politic", "economic",
             "extern", "sport", "ai", "tech", "auto", "sanatate", "cultura",
             "lifestyle", "discounturi", "stiri"}
etichete = sorted(etichete)

# (nume, --art-et-base cqw, max-width .art-body cqw) — din static/styles.css, citite 2026-10-01
TEMPLATEURI = [("editorial", 13.33, 68.75), ("inversat", 8.75, 52.0),
               ("banda", 4.375, 22.9), ("arc", 9.58, 49.0)]
TREPTE_K = [1, .8, .65, .5]           # .art--t0..t3
PLAFOANE = [8, 13, 18]                # _ET_TREPTE din htmlart.py
LS = 0.21                             # letter-spacing .art-label, cqw

def treapta(n: int) -> int:
    for i, p in enumerate(PLAFOANE):
        if n <= p:
            return i
    return len(PLAFOANE)

def cuvant_lat_eticheta(et: str) -> tuple[str, float, int]:
    """(cuvant, latime_em, n) — cel mai lat cuvant simplu din eticheta (spatiile/liniuta taie)."""
    import re
    cuvinte = [c for c in re.split(r"[\s\-]+", et) if c]
    return max(((c, latime_em(c), len(c)) for c in cuvinte), key=lambda x: x[1])

randuri = []
for et in etichete:
    n = len(et.strip())
    t = treapta(n)
    cuv, lem, nw = cuvant_lat_eticheta(et)
    rez = []
    for nume, base, mx in TEMPLATEURI:
        size = base * TREPTE_K[t]
        w = size * lem + nw * LS          # latimea celui mai lat cuvant, pe un rand
        rez.append({"tpl": nume, "size": size, "w": w, "mx": mx, "rupe": w > mx})
    randuri.append({"et": et, "n": n, "t": t, "cuv": cuv, "lem": lem, "rez": rez})

idx_tpl = {t[0]: i for i, t in enumerate(TEMPLATEURI)}
print("===== ETICHETE CU CUVinte CARE SE TAIE PRIN MIJLOC =====")
for nume, base, mx in TEMPLATEURI:
    rupi = sorted((r for r in randuri if r["rez"][idx_tpl[nume]]["rupe"]),
                  key=lambda r: (-len(r["cuv"]), r["cuv"]))
    print(f"-- {nume} (max-width {mx}cqw): {len(rupi)} etichete se taie prin cuvant")
    for r in rupi[:10]:
        z = r["rez"][idx_tpl[nume]]
        print(f"   {r['et']:<26} cuvantul lat: {r['cuv']:<16} n={r['n']:<3} t{r['t']} "
              f"size={z['size']:5.2f}cqw latime_cuv={z['w']:5.1f}cqw (> {mx})")

et = "Dâmbovița"
n, t = len(et), 1
cuv, lem, nw = cuvant_lat_eticheta(et)
print(f"\n-- cazul raportat: {et!r} -> eticheta randata uppercase {et.upper()!r}, n={n}, treapta=t{t}")
for nume, base, mx in TEMPLATEURI:
    size = base * TREPTE_K[t]
    w = size * lem + nw * LS
    print(f"   {nume:<10} size={size:5.2f}cqw latime_cuvant={w:6.2f}cqw vs max-width={mx}cqw "
          f"-> {'NU INCAPE (se taie)' if w > mx else 'incape'}")

print("\n-- k maxim per compozitie x treapta, ca cel mai lat cuvant REAL din banda sa incape:")
simple_univers = etichete
for nume, base, mx in TEMPLATEURI:
    linie = [f"{nume} (base {base}, mx {mx})"]
    for t, plafon in enumerate(PLAFOANE):
        lo = PLAFOANE[t - 1] + 1 if t else 1
        banda = [e for e in simple_univers if lo <= len(e) <= plafon]
        if not banda:
            linie.append(f"t{t}: banda fara cuvinte simple")
            continue
        cel_lat = max(banda, key=lambda e: latime_em(e))
        lem = latime_em(cel_lat)
        n = len(cel_lat)
        k_max = (mx - n * LS) / (base * lem)
        linie.append(f"t{t}(≤{plafon}): k<={k_max:.2f} [{cel_lat.upper()}]")
    print("   " + "\n   ".join(linie) if False else "   " + " · ".join(linie))

print("\n-- idem pentru t3 (>18 caractere, cele mai lungi cuvinte simple existente):")
for nume, base, mx in TEMPLATEURI:
    banda = [e for e in simple_univers if len(e) > 18]
    if banda:
        cel_lat = max(banda, key=lambda e: latime_em(e))
        lem, n = latime_em(cel_lat), len(cel_lat)
        k_max = (mx - n * LS) / (base * lem)
        print(f"   {nume}: t3 k<={k_max:.2f} [{cel_lat.upper()}]")
    else:
        print(f"   {nume}: t3 fara cuvinte simple reale")

# ===================== VERIFICAREA FIXULUI (cu valorile din PR) =====================
# Geometrie NOUA (styles.css) + praguri NOI (htmlart.py _ET_TREPTE = (8, 11, 14)).
print("\n================= VERIFICARE FIX =================")
FIX_WIDTHS = {"editorial": 84.0, "inversat": 56.0, "banda": 25.4, "arc": 54.0}
FIX_K = {  # (template, treapta) -> --art-et-k efectiv
    "editorial": [1, .77, .6, .5], "inversat": [1, .77, .6, .5],
    "banda": [.87, .66, .52, .5], "arc": [.87, .67, .54, .5],
}
PLAFOANE_FIX = [8, 11, 14]

def treapta_fix(n):
    for i, p in enumerate(PLAFOANE_FIX):
        if n <= p:
            return i
    return 3

esecuri = 0
for et in etichete:
    n = len(et.strip())
    t = treapta_fix(n)
    cuv, lem_w, nw = cuvant_lat_eticheta(et)
    for nume, base, _ in TEMPLATEURI:
        mx = FIX_WIDTHS[nume]
        k = FIX_K[nume][t]
        w = base * k * lem_w + nw * LS
        if w > mx:
            esecuri += 1
            print(f"  ESEC {nume} t{t} {et!r}: cuvantul {cuv!r} = {w:.1f}cqw > {mx}cqw")
print(f"Verificate {len(etichete)} etichete x 4 compozitii: {esecuri} esecuri"
      + (" — FIX INCOMPLET!" if esecuri else " — toate cuvintele incap pe un rand."))

# cazul raportat, dupa fix
et = "Dâmbovița"
cuv, lem_w, nw = cuvant_lat_eticheta(et)
print(f"\n-- DÂMBOVIȚA (t1) dupa fix:")
for nume, base, _ in TEMPLATEURI:
    size = base * FIX_K[nume][1]
    w = size * lem_w + nw * LS
    print(f"   {nume:<10} size={size:5.2f}cqw latime={w:5.1f}cqw vs {FIX_WIDTHS[nume]}cqw "
          f"-> {'INCAPE' if w <= FIX_WIDTHS[nume] else 'NU INCAPE'}")

# starea tranzitorie: paginile generate inainte de PR poarta clase din pragurile VECI
# (8/13/18); pana la urmatoarea rulare de pipeline, etichetele de 12-13 litere raman t1.
print("\n-- tranzitoriu (clase vechi + CSS nou), etichete 12-13 litere care inca se taie:")
tranz = 0
for et in etichete:
    n = len(et.strip())
    if not (9 <= n <= 13):
        continue
    cuv, lem_w, nw = cuvant_lat_eticheta(et)
    for nume, base, _ in TEMPLATEURI:
        k = FIX_K[nume][1]
        w = base * k * lem_w + nw * LS
        if w > FIX_WIDTHS[nume]:
            tranz += 1
            break
print(f"   {tranz} etichete (se auto-repara la prima regenerare: devin t2/t3)")
