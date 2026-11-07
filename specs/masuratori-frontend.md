# Măsurători front-end — arhiva §13

> **Ce e:** istoricul complet al măsurătorilor de performanță/accesibilitate pe izz.ro, mutat aici
> din `CLAUDE.md §13` pe 2026-08-06. Motivul mutării: §13 avea 5.898 de caractere și se încărca în
> context la FIECARE tură, deși se citește o dată pe lună. Regulile care obligă la acțiune au rămas
> în `CLAUDE.md §13`; aici stau cifrele, ipotezele picate și metodologia.
>
> **Când se citește:** înainte de orice slice care atinge `templates/`, `static/styles.css` sau
> HTML/JSON-LD din `render.py`. Și obligatoriu înainte de a re-investiga CLS.

## Unealta

**Regula de alegere a uneltei:** preferă măsurarea CLI **locală** în locul „site-urilor de
testare" — ieșire JSON structurată, rulează pe `localhost` ÎNAINTE de deploy, fără rate limits.
API-urile externe (PageSpeed Insights, validatorul W3C) sunt un complement **post-deploy** pe
site-ul live, **nu un substitut** pentru măsurătoarea de dinainte de commit.

`bash tools/audit.sh` — Lighthouse + pa11y pe `output/` servit local, JSON în `.audit/` (gitignored).
Setup: `npm i -g lighthouse pa11y`. Auto-detectează Chromium (`CHROME_PATH` pentru override).

Auto-detecția acoperă Linux/CI (Chrome *și* Chromium) și, pe Windows, **doar căile implicite ale
Google Chrome** — Chromium n-are installer oficial de Windows, deci nu există cale canonică de
sondat; acolo se pasează `CHROME_PATH` pentru Chromium sau Edge.

**Atenție la `.audit/` vechi:** până pe 2026-08-02 scriptul era Linux-only pe Windows în trei feluri
separate (niciun browser găsit; o linie de versiune care citea „Opening in existing browser
session."; pa11y murea pe o cale MSYS iar rularea tot tipărea „-1 errors"). Un `.audit/` de dinainte
de data aia, de pe Windows, **nu e o măsurătoare**.

## 2026-09-09 — arta desenată în pagină (migrarea pe Workers Free)

Mediane pe **3 repetări**, aceeași unealtă ca baseline-ul de mai jos (Lighthouse 13.4.1,
Chromium 141.0.7390.37), `output/` servit pe `127.0.0.1:8899`,
`ARTICLE_PATH=/sport/30-de-ani-de-la-moartea-legendarului-fotbalist-ion-oblemenco/`.

| Pagină | Perf | A11y | BP | SEO |
|---|---|---|---|---|
| home | **94** (94/96/92) — baseline 80 → **+14** | 96 | 100 | 100 |
| articol | **97** (97/97/97) — baseline 88 → **+9** | 96 | 100 | 100 |

pa11y WCAG2AA (v10.0.0): **0** erori pe ambele pagini — arta desenată în pagină nu adaugă
niciuna, deși textul ei devine text DOM real.

**De unde vin cele +14 / +9:** homepage-ul face acum **14 cereri în total, dintre care 1 de
imagine** (o fotografie reală de lead) și 258 KB transferați. Înainte, fiecare card cerea propriul
`art.jpg`/`art-card.webp` — 44 de cereri de imagine doar pe home. CLS 0.091, TBT 0 ms, LCP 2,4 s.

**A11y 96, nu 100 — și NU din cauza artei.** Singura penalizare e `target-size`, pe
`nav.subnav > details.subnav-more > summary` și pe linkul din el, adică pe meniul „Mai multe
secțiuni". Suprafața aia nu e atinsă de această felie; e o regresie apărută între 2026-08-02 și
azi, de reparat separat. Blocurile `.art` nu apar în niciun audit picat.

## Baseline — re-măsurat 2026-08-02 pe `main` @ `34cc8d3`

| Pagină | Perf | A11y | BP | SEO |
|---|---|---|---|---|
| home | **80** | 100 | 100 | 100 |
| articol | **88** | 100 | 100 | 100 |

pa11y WCAG2AA: **0** erori.

Măsurat cu Lighthouse 13.4.1, pa11y 9.1.1, Chromium 141.0.7390.37. Un upgrade la oricare dintre
cele trei mută cifrele, de aceea `audit.sh` le scrie în `.audit/versions.txt` la fiecare rulare.
**Compară like cu like:** același corpus pe desktopul Windows sub Chrome 150.0.7871.187 citește
home **83-84** / articol **92** în modul low-CLS de mai jos — deci 80 nu e o cifră de reprodus acolo.

## Varianța e un comutator cu două stări, nu o împrăștiere (măsurat 2026-08-02, PR #106)

Șase rulări pe două revizii, articol fixat: home a citit 84·83·84 înainte și 76·83·83 după. Fiecare
scor urmărește CLS aterizând pe exact una din două valori — ~0.156 (home 83-84) sau 0.272 (home 76).
Aceeași bimodalitate pe pagini de articol: 92 la CLS 0.172, 85 la 0.272. Ambele moduri apar pe
**ambele** revizii, deci comutatorul e preexistent, nu introdus de un slice.

**Consecință operațională:** o singură pereche înainte/după **nu poate** rezolva un efect mai mic de
~8 puncte pe home. Se rulează **3+ repetări per revizie și se compară medianele**, cu `ARTICLE_PATH`
fixat. Asta înlocuiește citirea mai veche „5 rulări identice, un outlier la 84" — aceea era același
comutator văzut dintr-o singură parte.

**Fixează pagina de articol când compari.** `audit.sh` scora `find | head -1`, adică ce întorcea
primul sistemul de fișiere, deci scorul „articol" se referea tăcut la pagini diferite între rulări
(măsurat: 87 vs 88 pe același commit). Implicitul e sortat și deci stabil pentru un corpus dat, dar
conținutul se schimbă între randări — pentru un înainte/după real, pasează `ARTICLE_PATH=/cat/slug/`.

## De ce e ținut jos Perf-ul pe home

Măsurat din JSON-ul Lighthouse, nu ghicit: **CLS și FCP**. CLS 0.272 în modul prost scorează 56 la
pondere 25; FCP 2.6 s scorează 65 la pondere 10; `styles.css` blochează randarea ~900 ms; TBT e
100 perfect. **Nimic din asta nu ține de imagini.**

## Vinovatul CLS e `#izz-install-btn` — și cele două explicații anterioare erau greșite

Măsurat 2026-08-02, emulare mobilă 412 px. Lighthouse atribuie 100% din shift unui singur element,
`body > main`, al cărui `boundingRect.top` final e **285**. Comutând butonul de instalare într-un
browser real: ascuns → `main` începe la **236.3**; afișat → **285.3**. Potrivire exactă.

Butonul stă în `.nav`, în grupul de header sticky, e `hidden` în markup, iar
`personalize.js::initInstallButton` îi scoate `hidden` când se declanșează `beforeinstallprompt` —
împingând fiecare articol în jos cu **49 px** în timpul cititului. Momentul evenimentului ăluia nu
e determinist, exact de-aia scorul e bimodal, nu zgomotos.

*(2026-10-03: funcția nu mai e în `personalize.js`, s-a mutat în `static/pwa.js`, iar butonul a
ieșit din `.nav` într-un element `position: fixed`. Măsurătoarea de mai sus rămâne așa cum a
fost făcută — descrie poziția din header, care e exact ce NU trebuie refăcut.)*

### Două ipoteze picate — a NU se redeschide

- **NU e `#izz-consent`:** e `position: fixed; bottom: 0`, adică în afara fluxului — nu are cum să
  miște `main`.
- **NU e swap-ul de web-font:** forțând stivele de fallback declarate și re-măsurând → delta **0 px**
  pe grupul de header, la 412 px și la 1280 px. Fonturile sunt self-hosted, subsetate (7-17 KB), două
  preîncărcate. Înregistrat în registru ca `IZZ-0133 · masurat-fals`.

### Repararea e o decizie de plasare, nu una tehnică

Butonul trebuie să nu mai crească header-ul, iar unde se mută e decizia proprietarului (§8).
Rezervarea permanentă a rândului ar costa 49 px de header mobil pentru un buton pe care majoritatea
vizitatorilor nu-l văd niciodată. **A NU se „repara" prin întârzierea dezvăluirii dincolo de
fereastra CLS** — aia e vânătoare de scor, interzisă de §13.

## Contrast — lecția din 2026-07-02

Fix-ul care a dus A11y la 100 a întunecat două tokenuri (`--ink-3`, `--gold-strong`). Descoperirea
„linkuri de footer" era de fapt **249 de erori pe tot site-ul**; doar măsurarea a arătat scopul real.
Contrastul pentru culori noi trebuie să treacă 4.5:1 față de `--paper` **ȘI** `--gold-wash`, nu doar
față de alb.

## Alarma „fotografiile au stricat Perf" — non-eveniment (2026-08-02)

Home era 80 și înainte, și după. Costul total al adăugării de fotografii reale: **−1 punct** pe o
pagină de articol, +65 KiB, +0.3 s LCP. Tabelul complet înainte/după e în PR #101.

**Regula generală:** o cifră din fișierele astea e o măsurătoare de sandbox local, nu o promisiune
despre izz.ro. Există ca să compare *înainte vs după un slice pe aceeași mașină*. Când un scor pare
o regresie, măsoară commit-ul de dinainte de slice într-un worktree și compară.

## Rebranding „Hârtie curată" — faza 0+1: tokeni și tipografie (2026-11-07)

Slice: `static/styles.css` `:root` + blocul dark, `static/fonts.css`, `templates/base.html`
(preload), `static/sw.js` (precache), `tools/fetch_fonts.py`. Șabloanele nu s-au atins dincolo
de preload-uri; structura de informație e identică, deci diferențele de mai jos sunt integral
efectul tokenilor.

**Măsurat local** (`--render-only` pe `state`-ul real: `build.json` = 6496 articole / 11.089
fișiere — verificat ÎNAINTE de citire, fiindcă `pytest` rescrie `output/` cu fixture-ul de ~190
articole). Coloana „înainte" e contrafactualul obținut prin înlocuirea blocului de fonturi din
`<head>` cu cel de la `HEAD`, pe aceeași pagină randată: markup-ul e identic, deci diferența e
integral efectul acestui slice.

| Indicator | Înainte | După | Δ |
|---|---:|---:|---:|
| Fonturi auto-găzduite (`static/fonts/*.woff2`) | 87.960 B / 7 fișiere | 76.224 B / 5 fișiere | −11.736 B (−13%), −2 fișiere |
| `fonts.css` inlineat în `<head>` | 1.160 B | 794 B | −366 B |
| Prima pagină, gzip | 109.205 B | 109.179 B | −26 B |
| Articol (`/extern/slabirea-timpurie-a-vortexului-polar-…/`), gzip | 20.563 B | 20.542 B | −21 B |
| `styles.css` | 80.768 B | 81.764 B | +996 B (comentarii + regula `tabular-nums`) |
| Prima încărcare, mediană pe 7679 pagini (`tools/greutate.py`) | — | 155 KB | neschimbat de acest slice |
| Fișiere în `output/` | 11.088 | 11.089 | +1 (licența OFL Newsreader) |

Corecție de cifră: tabelul de ținte din `analiza/rebranding/PROPUNERE.md` §6 spunea „104 KB / 7
fișiere" la fonturi; măsurat pe disc, cele 7 fișiere însumau 87.960 B (85,9 KiB). Ținta de ≤55 KB
rămâne neatinsă; vezi §8.2 din propunere pentru de ce (Newsreader are nevoie de două fete, Inter
700 nu poate fi scos fără bold sintetizat la `<strong>`).

**Contrast (WCAG 2.1, text mic) — toate tokenii de text, pe cele trei fundaluri, în ambele teme.**
Regula din acest fișier (§Contrast) cere 4,5:1 față de `--paper` **și** `--gold-wash`:

| Token | pe `--paper` | pe `--paper-2` | pe `--gold-wash` | Verdict |
|---|---:|---:|---:|---|
| `--ink` #14161a | 17,35 | 18,11 | 16,05 | AA |
| `--ink-2` #4a515c | 7,67 | 8,01 | 7,09 | AA |
| `--ink-3` #6a6a73 | 5,13 | 5,35 | 4,74 | AA |
| `--gold-strong` #7c5f22 | 5,72 | 5,97 | 5,29 | AA |
| `--navy` #173a5e | 11,16 | 11,65 | 10,32 | AA |
| `--live` #b23a2e | 5,69 | 5,94 | 5,26 | AA |
| dark: `--ink` / `--ink-2` / `--ink-3` | 15,2 / 8,6 / 6,1 | 14,0 / 7,9 / 5,6 | 14,0 / 7,9 / 5,6 | AA |
| dark: `--gold-strong` #d3b26a / `--navy` #a9c7e9 | 9,3 / 10,8 | 8,6 / 10,0 | 8,6 / 10,0 | AA |

Nota de implementare: `--ink-3` a fost coborât de la #6f7683 (4,38:1 pe `--paper`, **sub AA**) la
#6a6a73. Culorile de accent au trecut din aramă în navy pentru *acțiuni*; arama (`--gold`) rămâne
doar decor (3,40:1 — nu se folosește pe text, exact ca înainte cu aurul viu).

**Trei reparații colaterale găsite la măsurare** (ar fi fost regresii in vizibil, nu în scor):
`color: #fff` fix pe fundal `var(--ink)` / `var(--gold)` (`.btn-source`, `.pagination .current`,
hover pe `.theme-toggle`, `.back-to-top`, `.pagination a`, `.btn-preset`) — albul nu supraviețuiește
inversării temelor; acum textul e `var(--paper)`, care se inversează o dată cu fundalul. Butonul de
instalare PWA a pierdut gradientul metalic (aramă) în favoarea navy-ului solid.

**Ce NU s-a putut măsura aici:** `bash tools/audit.sh` cere un Chromium și `lighthouse`/`pa11y`
instalate; sandbox-ul de lucru nu are nici browser, nici pachetele, deci **scorurile Lighthouse și
numărul de erori pa11y rămân nemăsurate pentru acest slice** — de rulat pe o mașină cu browser
înainte de merge. Ce s-a rulat: `pytest` (3100 passed, 4 skipped, 8 xfailed), `ruff check .`
(curat), `csstree-validator` (singurul avertisment e preexistent: `url(#art-gold-grad, ...)`).
