# SPEC — dublarea resurselor gratuite: două origini + buget AI pe provideri

**Data:** 2026-10-03 · **Ramură:** `arena/01a1034f-izz-ro` (sesiunea Arena e fixată pe ea — nu pot crea alta)
**Tip:** implementare, PR fără merge · **Cost:** 0 lei

## Cerut

Trei lucruri: (1) două origini gratuite — Workers pentru conținutul cald, oglinda gh-pages (1 GB)
sau R2 free (10 GB) pentru coada lungă, cu rutare; (2) provideri AI gratuiti pentru sinteze
(Groq/Cerebras) prin infrastructura existentă; (3) orice alt plafon care se poate elibera.

## Ce am măsurat înainte (randare reală, `python -m generator.main --render-only`, 3 oct 2026)

```
>> imagini: 1214 fisiere pentru 9451 articole (1200 coperti proprii, 8251 pe coperta de categorie)
>> output: 14483 fisiere (buget 17000, marja 2517)

total fisiere        : 14483
  pagini de articol  : 9451
  imagini de articol : 1214
  rest               : 3818   <- OUTPUT_NON_ARTICLE_RESERVE (configurat 4400)
extensii: html:11114, jpg:3065, xml:192, json:46, webp:34
directoare: local:3683, portraits:1789, sport:1424, subiect:1344, extern:1221
```

**Descoperirea care a schimbat ordinea:** `portraits:1789` — `_load_portraits()` face
`shutil.copytree(media/portraits → output/portraits)` la FIECARE randare. Din cele 1.789 de
fișiere, **661 sunt referite** în cele 11.114 HTML-uri (măsurat cu un scan pe tot `output/`):
**1.128 de fișiere = 6,3% din plafonul gratuit, copiate degeaba.**

Al doilea lucru măsurat: **oglinda gh-pages primește deja întregul randat** — jobul `mirror`
din `build.yml` rulează cu `OUTPUT_FILE_BUDGET=100000` și publică `./output` cu `keep_files: true`
(IZZ-0423, #198). Deci a doua origine gratuită **există deja și are deja conținutul**, inclusiv
`portraits/` și imaginile de articol la aceleași căi. Ce lipsește e doar (a) să nu mai plătim
imaginile de două ori și (b) rutarea.

## Premise verificate

| premisă | dovadă |
|---|---|
| oglinda randează setul complet, fără plafon | `.github/workflows/build.yml`, jobul `mirror`: `OUTPUT_FILE_BUDGET: "100000"`, `keep_files: true` |
| workerul de fallback există, dar doar pe tiparul de articol | `infra/worker-404-mirror.js`: `CALEA_ARTICOL = /^\ /[a-z0-9-]+\/[a-z0-9-]+\/?$/` |
| suportul multi-provider există în pipeline, dar e oprit | `generator/process.py:102` (`AI_ROUTER_MODE == "multi"`), `generator/providers/openai_compat.py` (catalog cu groq, cerebras, mistral, openrouter…) |
| `build.yml` rulează pipeline-ul cu un singur provider | `AI_PROVIDER: gemini`, `MAX_AI_CALLS_PER_RUN: 40`, fără `AI_ROUTER_MODE` |
| bugetul AI e global, nu pe provider | `generator/main.py:397`: `budget = int(os.getenv("MAX_AI_CALLS_PER_RUN", "12"))` |
| cotele free ale providerilor | `ai_gateway/registry.yaml`, verificate 2026-10-02: Groq = rate-limit doar, nu facturează; Cerebras = 1M tokeni/zi; Gemini/Mistral/GitHub Models = rate-limit doar |
| suita verde înainte de orice schimbare | `pytest -q` → **1862 passed, 4 skipped, 8 xfailed** în 27,58 s |

**R2 vs. gh-pages:** am ales gh-pages, nu R2. Motive măsurate, nu estetice: gh-pages e deja
configurat (`MIRROR_DEPLOY_KEY`), deja populat, deja verificat de `tools/verify_release.py`, și
nu cere activarea unui serviciu nou pe cont. R2 free (10 GB, fără taxă de ieșire) rămâne
varianta de rezervă dacă gh-pages atinge 1 GB — vezi „Ce nu fac" §3.

## Felii (în ordinea în care se pot verifica independent)

**S1 — portrete doar cele folosite.** `_load_portraits()` copiază doar fișierele ale căror chei
sunt în cache-ul încărcat, nu tot directorul. Câștig: **−1.128 fișiere** pe prima origine, fără
nicio schimbare vizibilă (cele 1.128 nu sunt referite). Funcționează și pe oglindă.

**S2 — imaginile pe a doua origine.** `MEDIA_ORIGIN` (gol = comportament neschimbat). Când e
setat, imaginile de articol (`cover.jpg`, `art.jpg/webp`, `photo.jpg/webp`) se generează în
staging, se amprentează pentru `?v=`, iar în HTML pleacă URL absolut spre origine; în `output/`
NU se mai scrie fișierul. Câștig: **−1.214 fișiere** pe prima origine. Fără proxy prin Worker
(anume: ca să nu consumăm din cele 100.000 de cereri/zi ale planului Free) — browserul cere
imaginea direct de la a doua origine.

**S3 — rutarea cozii lungi.** `infra/worker-404-mirror.js` primește o listă pozitivă de prefixe
(`/subiect/`, `/ghiduri/`, `/instrumente/`, `/legal/`, `/despre/`, `/calendar/`, `/sectiuni/`,
`/portraits/`, `/og/`, `/leads/`) pe lângă tiparul de articol. Un 404 pe o pagină de subiect
ieșită din fereastră se servește din oglindă, nu din întuneric. Listă POZITIVĂ, nu negativă:
niciun URL de tip „homepage", „categorie" sau `sitemap` nu poate ajunge să fie servit de o
oglindă mai veche.

**S4 — buget AI pe provideri.** `AI_CALLS_PER_PROVIDER` (gol = `MAX_AI_CALLS_PER_RUN`, deci
comportament identic azi). Când e setat, bugetul e `per_provider × numărul de provideri
disponibili` din `get_provider()`. Adăugarea Groq + Cerebras la Gemini duce bugetul de la 40
la 120 de apeluri/rulare — **×3 pe aceeași cheie Gemini**, pentru că fiecare provider are
propria cotă.

**S5 — cablarea în `build.yml`.** `AI_ROUTER_MODE=multi`, `AI_FALLBACK_PROVIDERS=groq,cerebras`,
cheile opționale din secrets, `AI_CALLS_PER_PROVIDER=40`, plus o poartă care coboară bugetul
la 40 dacă ambele chei lipsesc (ca să nu crească bugetul fără provideri).

## Câștigul total, calculat pe măsurătorile de mai sus

| eliberat | fișiere | zile de arhivă câștigate (la ~660 articole/zi în stare) |
|---|---|---|
| S1 portrete nefolosite | −1.128 | ~1,7 |
| S2 imagini pe a doua origine | −1.214 | ~1,8 |
| **total** | **−2.342** | **~3,5 → TTL 12 poate urca la ~15 fără nicio altă schimbare** |

Nu ridic TTL-ul în PR-ul ăsta: `tests/test_reguli.py` leagă cifra din `config.py` de
raționamentul scris în repo, iar decizia de TTL e a proprietarului (precedent IZZ-0421/0424).
PR-ul eliberează spațiul și lasă decizia unde e.

## Verificare

- `python -m pytest -q` → verde (bază: 1862 passed).
- `python -m ruff check` pe fișierele atinse.
- `python -m generator.main --render-only` + `tools/count_output.py` → cifrele de mai sus, înainte/după.
- `node --test` pe logica de rutare din worker (node e disponibil; testul nu atinge rețeaua).
- S2 e **opt-in** (`MEDIA_ORIGIN` gol în repo): randarea implicită rămâne byte-identică.

## Ce NU fac (și de ce)

1. **Nu activez `MEDIA_ORIGIN` în `build.yml`.** Ar muta traficul de imagini de pe Cloudflare
   (cache la margine, aceeași zonă) pe GitHub Pages, iar asta e o decizie de produs cu un
   cost real de latență pentru cititor. Livrez mecanismul + cifrele; comutatorul e al proprietarului.
2. **Nu tai pagini de subiect.** Ar fi ~400 de fișiere în plus, dar e conținut real și ar cere
   o decizie editorială. Măsurat pentru dosar: 1.462 de entități au ≥ 3 articole în stare,
   1.011 au ≥ 4.
3. **Nu activez R2.** Ar cere activarea unui serviciu pe cont + un token nou. gh-pages acoperă
   aceeași nevoie azi; R2 rămâne planul B la 1 GB.
4. **Nu ating `ARTICLE_TTL_DAYS`.** Vezi mai sus.

## Cerut vs. livrat

Se scrie la finalul PR-ului, cu ce a rămas neatins numit explicit.
