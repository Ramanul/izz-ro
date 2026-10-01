# Audit PR #297 vs main actual — matrice de recuperare selectivă

Data: 2026-10-01 · Metodă: citire reală de cod (`gh api`, marker-grep), nu din documentație ·
Baza PR: `642391ea` (6 sept 2026) · Head PR: `3fb86dd5` · Main la audit: `09bb38517d`+ (1 oct)
Verdict: **NU se dă merge**; recuperare selectivă în faze, pe main actual.

## Date brute verificate

- PR #297: 68 fișiere schimbate; cod real (non-media): `generator/htmlart.py` +176/−104,
  `generator/render.py` +142/−12, `static/styles.css` +112/−3, `static/harta-stiri/harta-stiri.css`
  +25/−15, `templates/{base,article,index}.html` +7/+3/+18, `tests/conftest.py` +4/−1,
  `tests/test_sparkline_pe_categorii.py` +53 (nou), `tools/gen_images.py` +1/−1.
- Restul (~58 fișiere) = media generată (`media/*.jpg/.webp/.c.jpg`, binare, +0/−0).

## Matricea (marker-e verificate pe main azi)

| Componentă | În #297 | În main azi | Conflict real | Cost assets | Acțiune recomandată |
|---|---|---|---|---|---|
| Masthead de ziar + data RO | da (base.html+7, index+18) | **NU** (0 marker-e) | aplicare pe șabloane actuale | ~0 | Faza 1 — recuperează |
| „Numerele zilei" | da (index+18, render+142) | **NU** | logică de randare rescrisă de la 9 sept | ~0 | Faza 1 — recuperează/adaptează |
| Mini-harta „România în 24h" | da (index, harta-stiri.css) | **NU** (dar există harta completă separată) | datele vin din pipeline-ul actual | mic (SVG static) | Faza 2 — recuperează/adaptează |
| Tipografie fluidă `clamp(` | da (styles.css +112) | **NU** (0 `clamp(`) | CSS-ul a evoluat; adaptare, nu copiere | 0 | Faza 3 — integrează selectiv |
| Reading progress | da (article+3) | **NU** | minor | 0 | Faza 5 — recuperează |
| Motion la scroll | da (styles.css) | parțial (1 `prefers-reduced-motion` există) | compatibilitate cu CSS actual | 0 | Faza 6 — recuperează cu garda reduced-motion |
| Mobile header | da (styles.css) | **NU** (marker absent) | adaptare la header-ul actual | 0 | Faza 4 — adaptează |
| **Art v2** (coperti generative) | da (htmlart +176/−104 + ~58 media) | **NU** (0 halftone/arcs/giant) | htmlart.py actual = sisteme diferite | **~2.000 fișiere la regen — DECIZIE SEPARATĂ, blocată de asset census** | Ultima fază, doar cu buget verificat |
| Sparkline pe categorii | da (test nou +53) | **NU** | test nou, compatibil | ~0 | Recuperează odată cu felia lui |

## Regula conflictului (important)

Marker-ele arată că #297 NU se suprapune cu main — dar **baza PR e pre-9 septembrie**:
`render.py`-ul din PR a fost scris înainte de mutarea artei în HTML/CSS și înainte de separarea
logicii editoriale în `select.py`. Deci patch-urile NU se aplică curat (cherry-pick va conflictă);
fiecare felie se **re-implemementază pe main actual**, cu PR-ul ca sursă de design, nu ca diff.

## Ce NU mai e valabil / neverificat

- Comenzile de regenerare din PR (FORCE_REGEN) — învechite; orice regen decide după asset census.
- Revizuirea patch-cu-patch a celor +176/+142 rânduri — **neverificat la nivel de hunk**; se face
  per felie, la implementarea fiecărei faze.
- Cum arată vizual feliile pe designul actual — necesită privirea ownerului pe live (recuperarea
  se face pe branch + preview, nu direct pe main).
