# Limitele funcționării izz.ro exclusiv pe planuri gratuite

**Data:** 2026-10-04 · **Scop:** răspuns documentat la întrebarea „care sunt limitările faptului
că izz.ro rulează doar pe planuri gratuite — pentru dezvoltare, funcționalități și restul
dimensiunilor". **Metodă:** măsurătorile din repo (fișiere comise, spec-uri, cod) + documentația
oficială a platformelor + presa tehnologică majoră, cu dată de acces și link pentru fiecare
afirmație. Ce nu e verificat e marcat **[NEVERIFICAT]**.

> Politica proiectului rămâne $0. Documentul nu e o recomandare de a plăti acum; descrie
> **prețul real al gratuității** și pragurile la care ele devin vizibile pentru cititor.

---

## 0. Pe scurt — zece concluzii

1. **Constrângerea nr. 1 nu e traficul, e numărul de fișiere.** Planul Free Cloudflare limitează
   o versiune de Worker la **20.000 de fișiere statice** (Paid: 100.000). De aici curge tot
   lanțul: fișiere puține → **TTL de 12 zile** → linkuri vechi moarte → oglindă de rezervă pe
   GitHub Pages. Măsurat în repo la 9 septembrie: 51.896 de fișiere în regimul vechi (259% din
   plafon) → 16.732 după mutarea artei în HTML (−68%). Vezi §2.
2. **Riscul nu e teoretic: s-a întâmplat deja.** Pe 21 august 2026, deploy-ul a fost refuzat
   pentru depășirea plafonului, iar **site-ul a stat înghețat 21 de ore** fără ca pipeline-ul să
   semnaleze nimic. Garda care previne repetarea (`OUTPUT_FILE_CEILING=20000`) a fost scrisă
   exact pentru acel incident.
3. **Arhiva e limitată la ~12 zile pe primar**, iar depozitul complet trăiește pe o **oglindă
   GitHub Pages** — gratuită și ea, dar cu propriile plafoane (1 GB site, ~100 GB/lună, 10
   build-uri/oră, interzisă pentru uz comercial). Un articol salvat de un cititor supraviețuiește
   doar cât timp funcționează lanțul de două origini.
4. **100.000 de invocări de Worker pe zi** (Free) se consumă pe rutele `/push/*`, `/sw.js` și pe
   fallback-ul de 404. Cererile către fișiere statice sunt gratuite și nelimitate — de aceea
   `run_worker_first` e ținut la minimum. Dar într-o lume în care **boții fac 57,5% din cererile
   HTTP** (măsurat de Cloudflare, iunie 2026), un val de scanări pe URL-uri inexistente poate
   arde cota zilei; la depășire Cloudflare răspunde cu **Error 1027**.
5. **10 ms de CPU per cerere** (Free) și 128 MB memorie înseamnă: nimic server-side greu — fără
   căutare pe server, fără recomandări, fără redimensionare de imagini la cerere, fără randare
   dinamică. Site-ul e static din necesitate, nu doar din eleganță.
6. **K=V, Queues, D1, Durable Objects au cote minime pe Free** (ex. KV: 1.000 scrieri/zi). De
   aici și politica de alerte «maximum una pe zi», protejată mecanic în `infra/push.js`. Orice
   funcție cu stare (cont de cititor, salvare articole, comentarii) e practic imposibilă fără
   plată.
7. **Pipeline-ul depinde de cron-ul GitHub Actions**, care e „best effort": întârzieri obișnuite
   de 10–30 de minute, rulări sărite la orele aglomerate, iar în repo-urile publice inactive
   **60 de zile** workflow-urile programate se dezactivează silențios. Regula „încearcă orar,
   publică la ~2h" din `build.yml` e o compensație directă pentru asta.
8. **Cel mai fragil pilon e AI-ul gratuit.** Furnizorii își reduc sau închid cotele free fără
   preaviz: Google a tăiat cotele Gemini cu 50–92% în decembrie 2025 și a scos modelele Pro de
   pe free în aprilie 2026; X a închis free tier-ul API în februarie 2026; Qwen a închis free
   tier-ul OAuth pe 15 aprilie 2026. Dacă toate cotele cad, pipeline-ul rămâne pe **fallback
   determinist** (rezumat din descrierea RSS) — site-ul rămâne funcțional, dar calitatea scade
   vizibil.
9. **Distribuția costă și ea, chiar dacă nu plătești**: presa consacrată documentează scăderea
   traficului din Google către site-urile de știri (~33% global în ultimul an, măsurat de
   Chartbeat, relatat de PCMag în ianuarie 2026), iar politicile Google anti-„scaled content
   abuse" + update-urile spam din 2026 fac riscant un agregator cu sute de pagini pe zi dacă nu
   adaugă „information gain".
10. **Ce NU e limitat pe gratis** (ca să fim cinstiți): cererile către fișiere statice,
    protecția anti-DDoS, TLS, CDN-ul, căutarea Pagefind (index local), PWA/offline, RSS,
    IndexNow, oglinda GitHub Pages. Free-ul e suficient pentru suma de azi de funcții — dar
    fiecare funcție nouă care cere **stare**, **CPU** sau **fișiere** lovește unul din
    plafoanele de mai sus.

---

## 1. Harta plafoanelor — ce e gratuit și ce se termină

| # | Resursă | Limita planului gratuit | Efect funcțional pentru izz.ro |
|---|---|---|---|
| A1 | Cloudflare Workers — fișiere/versiune | **20.000** (Paid: 100.000); 25 MiB/fișier | determină TTL-ul, adâncimea arhivei, câte pagini de subiect/paginare/portret încap |
| A2 | Cloudflare Workers — cereri | **100.000/zi** la Worker; static assets **gratuite și nelimitate**; depășire = Error 1027 | fallback-ul 404, `/push/*`, `/sw.js` consumă cotă; un val de boți o poate arde |
| A3 | Cloudflare Workers — CPU | **10 ms/cerere**, 128 MB RAM, 50 subrequests | niciun calcul server-side serios; fără SSR, imagini dinamice, căutare pe server |
| A4 | Cloudflare — produse conexe | KV 100k citiri / **1.000 scrieri pe zi**; 5 cron triggers/cont; Queues 10k ops/zi; D1 100k rânduri scrise/zi; DO 13.000 GB-s/zi | alerte max. 1/zi; fără conturi, comentarii, salvare preferințe pe server |
| A5 | Cloudflare — Builds | **3.000 min/lună**, 1 build concurent, timeout 20 min | deploys dese consumă; un build blocat blochează rândul |
| A6 | Cloudflare — suport/SLA | **fără SLA**, suport comunitar, prioritate de rețea inferioară | incidentele globale te ating ca orice client (18 nov 2025) |
| B1 | GitHub Actions — cron | best-effort: întârzieri 10–30 min, rulări sărite; 5 min interval minim | „încearcă orar, publică la ~2h”; fereastra de 105 min acoperă firings-urile pierdute |
| B2 | GitHub Actions — repo public | minute nelimitate pe runneri standard; **60 de zile fără activitate → workflows programate oprite silențios** | dacă proiectul ar sta 60 de zile, site-ul ar îngheța fără email citit |
| B3 | GitHub Pages (oglinda) | 1 GB site, ~100 GB/lună soft, 10 builds/oră (nu se aplică la deploy din Actions), **nu pentru uz comercial** | oglinda e frânghia de siguranță pentru linkurile expirate — și ea gratis, cu limite |
| C1 | AI — Gemini free | cote reduse masiv dec. 2025; **doar Flash/Flash-Lite** (Pro scos apr. 2026); datele de pe free pot fi folosite la antrenare | sinteza multi-sursă depinde de bunăvoința Google |
| C2 | AI — Groq/Cerebras/OpenRouter/Mistral | Groq ~1.000 cereri/zi/model; Cerebras „no permanent free tier"; OpenRouter 50 cereri/zi fără credite | bugetul de 40 → 80/120 apeluri/ rulare e dimensionat pe aceste cote |
| C3 | AI — precedente | X API free tier închis (feb. 2026); Qwen OAuth free închis (15 apr. 2026) | risc de „bait and switch": o zi bună, apoi fallback determinist |
| D1 | SEO/distribuție | Google: politici anti-scaled-content-abuse; AI Overviews taie din trafic | agregator cu volum mare = profil de risc; traficul de presă scade per ansamblu |

---

## 2. Dimensiunea A — găzduirea: lanțul „fișiere → TTL → linkuri moarte"

### A1. Plafonul de 20.000 de fișiere este constrângerea care modelează tot site-ul

Documentația oficială Cloudflare (secțiunea *Static Assets*) dă: **Free = 20.000 de fișiere per
versiune de Worker, Paid = 100.000**, dimensionarea de 25 MiB per fișier rămânând neschimbată.
Motorul de decizie a fost „întoarcerea pe Free" din 22 septembrie 2026 (cerere a proprietarului,
consemnată în `specs/cloudflare-free-2026-09.md`).

Măsurătorile din spec (9 septembrie 2026), cu regimul de atunci:

| Variantă | Fișiere | % din 20.000 |
|---|---|---|
| TTL 9 zile | 14.773 | 74% |
| TTL 12 zile | 20.965 | **105%** |
| TTL 21 zile | 45.663 | **228%** |
| TTL 30 zile (regimul vechi) | 61.620 | **308%** |

Adică: **pe regimul dinainte, planul Free ar fi permis ~9 zile de arhivă**. După mutarea artei
generatoare din fișiere raster în HTML/CSS inline (aceeași calitate vizuală, zero fișiere
`art.jpg`/`webp`), s-a ajuns la 16.732 de fișiere și **TTL 21 de zile**; ulterior ingestul a
crescut, iar TTL-ul a fost coborât la **20 → 11 → 12 zile** (`generator/config.py`), cu urme
exploatate în comentarii: 20.543 de articole în fereastră vs. 12.600 de pagini sub buget
(3 octombrie).

**Consecința pentru cititor, spusă direct:** un link trimis astăzi expiră din primar după ~12
zile. De aici oglinda — `infra/worker-404-mirror.js` — care servește sub aceeași adresă
`izz.ro` paginile pensionate, din setul complet randat cu `OUTPUT_FILE_BUDGET=100000` pe
ghișeul de oglindire. Arhitectura e o soluție de inginerie la o limită de plan gratuit; e
funcțională, dar are **două origini de întreținut în loc de una** și două lanțuri care pot cădea
independent.

### A2. 100.000 de cereri/zi: cota care se poate arde de la boți

Cererile către asset-uri statice nu se taxează (nici pe Free, nici pe Paid) — de aceea în
`wrangler.jsonc` `run_worker_first` este limitat la `["/push/*", "/sw.js"]`, cu comentariul
explicit: „un Worker chemat pentru fiecare imagine ar arde plafonul zilnic de 100.000 de
invocări (plan Free) pentru nimic". Cota se consumă totuși pe fallback-ul de 404 (Worker-ul
rulează la miss) și pe rutele de alerte.

Relevanța externă e directă: Cloudflare a anunțat în iunie 2026 că **traficul de boți a depășit
traficul uman** — 57,5% din cererile HTTP către conținut HTML — cu un an mai devreme decât
prevedea compania, iar OpenAI/GPTBot a crescut 305% într-un an. Pentru un site gratuit, asta
înseamnă că o parte din cota zilnică o consumă roboți: crawleri AI, scanere de securitate,
indexatoare. Cloudflare a răspuns cu instrumente plătite (pay-per-crawl, HTTP 402) — site-ul
nostru nu are contract cu niciun bot plătitor; un „asalt" de scanări pe URL-uri inexistente e
exact cazul care consumă invocările de fallback.

### A3. 10 ms CPU: de ce site-ul e static prin constrângere

Cloudflare publică pentru Free **10 ms CPU per cerere** (Paid: 30 secunde implicit, până la 5
minute) și 128 MB per isolate. CPU-ul nu numără timpul de rețea (fetch/KV), deci un Worker
„de pasare" e posibil — dar orice calculează (randare, filtrare, imagini, căutare) iese imediat
din buget. Funcțional, asta blochează întreaga clasă de funcții „moderne de portal":

- căutare pe server / semantică (la noi: Pagefind, index static construit la build — soluție
  corectă în acest cadru);
- recomandări personalizate server-side;
- redimensionare/optimizare imagini la cerere;
- randare SSR sau feed-uri personalizate;
- orice API intern cu logică.

### A4. Produsele conexe: cotele mici decid funcțiile cu stare

Paginile de prețuri Cloudflare (Free): KV **1.000 scrieri/zi** / 100.000 citiri/zi; Queues
10.000 operații/zi; D1 100.000 rânduri scrise/zi; Durable Objects 100.000 cereri + 13.000 GB-s
pe zi. Efectul e vizibil chiar în cod: `infra/push.js` are un plafon zilnic dur („maxim o
alertă pe zi"), iar comentariile explică de ce — 1.000 de scrieri pe zi pe Free și protecția
împotriva umplerii plafonului de către oricine. Politica editorială «Zero zgomot» coincide cu
limita tehnică; dar orice produs cu stare (cont de cititor, „articolele mele salvate", județul
preferat sincronizat, comentarii moderate) e exclus fără plată.

### A5–A6. Build, suport, SLA: gratuitatea nu e izolare

Workers Builds pe Free: **3.000 minute/lună, un singur build concurent**, timeout 20 de minute.
Suportul e doar comunitar, fără SLA, cu prioritate de rețea inferioară (răspuns oficial al
echipei Cloudflare pe forumul comunității: „Free plans have no SLA, no direct support… lower
priority traffic profiles").

Și Cloudflare cade. Pe **18 noiembrie 2025**, o eroare de configurare în generarea fișierului de
Bot Management a produs o pană globală de ~4 ore: X, ChatGPT, Spotify, Shopify, Uber au fost
afectate, iar bilanțurile de presă vorbesc de peste 7,5 milioane de site-uri și de 2,1 milioane
de raportări pe Downdetector; relatat de The Verge, CNBC, Mashable; post-mortem-ul Cloudflare
recunoaște: „We let you down today". Fiind pe
Free, izz.ro nu are nicio cale de escaladare în astfel de incidente — doar răbdare și oglinda.

---

## 3. Dimensiunea B — pipeline-ul: GitHub Actions și oglinda

### B1. Cron-ul GitHub e „best effort", nu un scheduler

Documentat de GitHub și explicat de mai multe analize tehnice: rulările programate sunt **puse
în coadă**, nu pornite la secundă; întârzieri de 10–30 de minute sunt normale, iar la orele
aglomerate (minutul 0) pot apărea și întârzieri de peste o oră sau **rulări sărite complet**.
Intervalul minim e 5 minute. GitHub însuși nu garantează momentul.

Arhitectura izz.ro compensează exact asta: cron orar dens (`13 * * * *`) + o **poartă de 105
minute** înainte de publicare — „încearcă orar, publică la ~2h". Prețul e că prospețimea știrilor
depinde de un scheduler gratuit al altei companii, iar diagnosticarea e grea: „rulare sărită"
nu produce un eșec vizibil, doar o zi mai săracă. Repo-ul are deja `detectie-tacere.yml` și
`monitor.yml` ca sirene pentru astfel de tăceri.

### B2. Capcana celor 60 de zile

În repo-urile **publice**, GitHub dezactivează automat workflow-urile programate după **60 de
zile fără activitate** — fără eșec, fără log; eventual un email care poate fi ratat. E scenariul
„proiect lăsat în pace o vară": site-ul rămâne pe ultima stare publicată, iar cititorii văd știri
vechi fără ca nimeni să afle. Pentru un proiect cu activitate zilnică nu se declanșează — dar
merită un keep-alive explicit (comis lunar) ca asigurare ieftină.

### B3. Gratuitatea pe repo public depinde de politici care se schimbă

GitHub a anunțat în decembrie 2025 un sistem de taxare pentru **runneri self-hosted** (de la 1
martie 2026), a stârnit reacții puternice și **a amânat** schimbarea; prețurile runner-ilor
hosted au scăzut cu până la 39% de la 1 ianuarie 2026, iar utilizarea în **repo publice rămâne
gratuită**. Concluzia pentru izz.ro: gratuitatea nu e un contract, e o politică — suficient de
stabilă cât să construiești, dar de urmărit la fiecare anunț de pricing.

### B4. Oglinda: GitHub Pages are și ea limite, inclusiv de utilizare

Documentația GitHub Pages: site publicat ≤ **1 GB** (recomandare), **~100 GB/lună** lățime de
bandă (soft), 10 build-uri/oră (nu se aplică la deploy din Actions), și — important pentru un
proiect editorial — „Pages is not intended for or allowed to be used as a free web-hosting
service to run your online business… or any other website… directed at… commercial
transactions". Un portal ad-financed ar putea deveni incompatibil; izz.ro e fără publicitate,
deci azi e în regulă. Peste limite, GitHub nu facturează: **throttlează sau trimite email** —
adică oglinda poate încetini exact când ai cea mai mare nevoie de ea (linkuri vechi, val de
distribuție).

---

## 4. Dimensiunea C — AI-ul gratuit: cel mai fragil pilon

Sinteza multi-sursă, rezumatele re-scrise, titlurile fără cârlige emoționale — toate trec prin
API-uri gratuite. Aici „free" a fost cel mai volatil în ultimul an:

- **Google Gemini** (furnizorul implicit al proiectului): pe 6–7 decembrie 2025, cotele free
  au fost reduse fără anunț — „Gemini 2.5 Flash" de la ~250 la 20–50 cereri/zi în unele
  configurații (−80…−92%), Pro scos parțial din free; în aprilie 2026, modelele Pro au ieșit
  complet de pe free (doar paid/abonament), iar „spending caps" au devenit obligatorii pentru
  conturile noi. Un reprezentant Google a explicat: „We dialed down… to free up compute for
  Gemini 3 Pro". Pe free, datele pot fi folosite la îmbunătățirea produselor — pentru un
  portal care promite „zero zgomot" asta e și o discuție de principiu, nu doar tehnică.
- **Groq**: tabelă oficială Free Plan, specifică pe model (ex. gpt-oss-120b: ~30 RPM, ~1.000
  cereri/zi, 200k tokeni/zi). **Cerebras**: credite de probă, dar documentația spune explicit
  că **nu există tier gratuit permanent**. **OpenRouter**: 20 RPM și **50 cereri/zi** fără
  credite cumpărate (1.000/zi cu ≥$10 credit); modelul servit poate varia. **Mistral**: cotă
  „free mode" în funcție de cont/model.
- **Precedente de „bait and switch"** în industrie: X a închis free tier-ul API în februarie
  2026 (migrare forțată la pay-per-use, credite-voucher), Qwen a închis free tier-ul OAuth pe
  15 aprilie 2026 („Run /auth to switch…"), iar comunitățile de dezvoltatori au documentat
  haosul de migrare.

**Efectul pe izz.ro.** Bugetul AI al pipeline-ului (`MAX_AI_CALLS_PER_RUN` = 40, extins prin
inginerie la 80–120 în funcție de numărul de cote — vezi `specs/ai-budget-ordering.md`) e
dimensionat pe aceste plafoane. Dacă toți furnizorii free cad simultan, pipeline-ul nostru are
un plan B onorabil: **fallback determinist** (rezumat din descrierea RSS) — site-ul nu se
oprește, dar calitatea scade; tot ce ține de reformulare fină dispare. Iar dacă Google mută iar
cotele (probabil, judecând după 2025–2026), coada se re-calibrează automat, dar **calitatea
per-articol fluctuează fără ca noi să controlăm**.

---

## 5. Dimensiunea D — funcționalități blocate sau degradate de planul gratuit

| Funcție „normală" de portal | De ce nu se poate pe gratis | Cost de deblocare (public) |
|---|---|---|
| Optimizare/resizing automat de imagini | polish pe Pro+ (amânat de Cloudflare pe Free). Azi ocolim prin artă HTML, dar fotografiile reale rămân neoptimizate automat | Cloudflare Pro: $20/lună (anual) |
| Protecție avansată bot/WAF, Cache Reserve, Argo | produse plătite (WAF enhanced pe Pro; Cache/Argo add-on, Argo $5/lună + uz) | Pro sau add-on-uri |
| Observabilitate (Logpush, Log Explorer, retenție lungă) | pe Free: `wrangler tail` + propriile probe; log-urile centralizate sunt plătite (Log Explorer ~$1/GB) | Workers Paid + Log Explorer |
| Cont de cititor, salvare articole, preferințe sincronizate | KV 1.000 scrieri/zi + CPU 10 ms + niciun login server-side | Workers Paid + produse conexe (sau D1) |
| Comentarii, moderare comunitară | aceeași cauză + moderare continuă (om în buclă) | infra plătită |
| Alerte push „când e nevoie" | KV 1.000 scrieri/zi + politica «max 1/zi», evaluată mecanic | plată doar dacă se vrea mai mult |
| Analytics avansat propriu / A-B testing server-side | CPU + stocare + log-uri | Workers Paid |
| Newsletter real (nu RSS) | trimiterea de email nu e gratuită (sau e riscantă pe free tier) | serviciu extern ($0 există doar în limite mici) |
| Video/podcast găzduit | R2 free = 10 GB; egress gratuit, dar plafonul se atinge repede | R2 plătit (ieftin, dar nu $0) |
| Analytics de produs (funnel, retenție) | GA4/Clarity acoperă; cloudflare analytics e minim | — |

**Linia de demarcație e limpede:** tot ce e *fișier static* e gratis și nelimitat; tot ce e
*stare + calcul* costă. De aceea izz.ro e (corect!) un SSG.

---

## 6. Dimensiunea E — SEO, distribuție și consum: „gratuit" nu înseamnă „fără risc"

### E1. Politicile Google față de conținut generat la volum

Google nu pedepsește folosirea AI-ului în sine, ci **scaled content abuse**: volum mare de
pagini produse în principal ca să manipuleze căutarea. Update-urile din 2026 au fost relatate ca
ofensive anti-„AI slop" (update-ul Discover din februarie 2026; update-ul spam din august 2026),
iar în mai 2026 Google a clarificat că politicile includ și manipularea răspunsurilor AI
(Overview-uri / AI Mode). Analizele independente estimează că ~19% din primele rezultate conțin
text generat de AI — deci nu e o pedeapsă pentru AI, ci un prag de calitate care crește.

Pentru un agregator care publică sute de pagini pe zi, asta e un **risc de profil**: nu
volumul e problema, ci volumul fără „information gain" (sinteză proprie, valori verificate,
linkuri care se rezolvă, corecții publice). Exact direcția în care merge proiectul (ghiduri
deterministe, entități, sinteze cu surse enunțate) este și răspunsul corect SEO — dar e o
cursă, nu un dat.

### E2. Traficul din căutări scade pentru presă, per ansamblu

Măsurătoare Chartbeat, relatată de PCMag în ianuarie 2026: traficul din Google către 2.756 de
site-uri de știri a scăzut ~33% global, ~38% în SUA, în ultimul an, în mare după AI Overviews.
Pentru un site care depinde de căutare și de linkuri partajate, asta e o veste sistemică: nici
pe gratis, nici pe plătit nu poți compensa scăderea cererii; te poți diferenția doar calitativ.

### E3. „Gratuit" atrage și vizitatori nedoriți

Cloudflare (iun. 2026): **57,5% din cererile HTML sunt de la boți**; peste 5 ani, boții ar putea
depăși omenirea de 1.000×. Cloudflare vinde răspunsul (pay-per-crawl / 402), dar pe planul
gratuit instrumentele de discriminare sunt minimale. Nu e un scenariu ipotetic: orice site
public atrage crawleri; costul lor apare ca cotă zilnică consumată, nu ca factură.

---

## 7. Dimensiunea F — cadru juridic pentru agregatoare (scurt și precaut)

[Punct de atenție, nu consultanță juridică.] Directiva (UE) 2019/790, **Art. 15** (drepturile
conexe ale editorilor de presă) dă editorilor dreptul de a autoriza reutilizarea online a
publicațiilor lor de presă, **cu excepția** introducerii de hyperlinkuri și a „faptelor
simple" sau a „extraselor foarte scurte". Practica izz.ro — titlu reformulat, rezumat în cuvinte
proprii, link la sursă, creditul imaginilor, pagini de transparență — este pe poziția cea mai
defensabilă, dar **extinderea sintezei până la reproducerea substanțială a textului sursă** ar
ieși din zona exceptată. Drepturile editorilor durează 2 ani de la publicare — or, exact
fereastra în care izz.ro păstrează conținutul (12 zile pe primar, mai mult pe oglindă).
Recomandarea de rutină: orice escaladare a lungimii blocurilor preluate se consultă cu un jurist
român înainte de a crește volumul (vezi și paginile `content/` ale site-ului).

---

## 8. Ce NU e limitat de planul gratuit (ca să nu confundăm constrângerile)

- **Cererile către fișiere statice** — gratuite și nelimitate (nota de prețuri Cloudflare);
- **Protecția DDoS și rețeaua edge** — nemăsurate/nemetered pe toate planurile;
- **TLS, DNS, CDN, custom domain** — incluse;
- **Căutarea** — Pagefind (index local, zero serviciu extern);
- **PWA/offline, RSS, IndexNow, sitemapuri, feeduri** — statice;
- **Oglinda** — GitHub Pages, tot gratuit.
- **Pipeline-ul** — GitHub Actions pe repo public, gratuit nelimitat pe runneri standard.

Cu alte cuvinte: arhitectura aleasă maximizează exact ce e gratuit și nelimitat (fișiere, bandă)
și minimizează ce e limitat (CPU, invocări, stare). Limitele reale nu sunt „site-ul nu merge",
ci: **adâncimea arhivei, greutatea funcțiilor cu stare și certitudinea furnizorilor**.

---

## 9. Matricea de risc — ce se rupe primul

| Riscul | Probabilitate | Impact | Semnal de urmărit | Mitigare existentă |
|---|---|---|---|---|
| Depășire plafon fișiere (20k) la ingest mare | medie | deploy refuzat, site înghețat (s-a întâmplat 21 h) | `tools/count_output.py` + test tripwire buget | `OUTPUT_FILE_CEILING`, supapa `_taie_la_buget()`, `release-probe` |
| Epuizarea a 100.000 invocări/zi (boți/404) | medie | Error 1027 pe rute de Worker (parțial: fallback 404, push) | alerte de cotă/analytics | `run_worker_first` minimal; assets nelimitate |
| Furnizor AI care taie cota | **ridicată** | calitate mai mică instant, coadă neprocesată | log-uri pipeline, rate de succes per provider | router multi-provider (cascadă), fallback determinist |
| GitHub cron sărit → știri vechi | medie | prospețime redusă, fără eșec vizibil | `detectie-tacere.yml`, `monitor.yml` | cron orar dens + poartă 105 min |
| Pana globală CDN (tip 18 nov. 2025) | scăzută | site indisponibil complet | status Cloudflare | oglindă (dar și ea în spatele altor servicii) |
| Oglinda GitHub Pages peste limite (bandă/1 GB) | scăzută | articole expirate greu accesibile | `verify_release.py` pe ambele origini | rute cu listă pozitivă, no-worse fallback |
| Trafic de căutare în scădere la nivel de industrie | **ridicată** | mai puțini cititori, indiferent de plan | Search Console (pas manual lunar) | diferențiere editorială, ghiduri, RSS/alerts |

---

## 10. Dacă s-ar decide vreodată plata: ordinea pragurilor

1. **Cloudflare Workers Paid — $5/lună**: deblochează 100.000 de fișiere (TTL 30 din nou),
   ridică CPU-ul la secunde, elimină limita de 100.000 cereri/zi pe Worker. Este, măsurat,
   cea mai mare valoare per dolar — returnează *arhiva* și *starea*.
2. **Un buget mic de AI plătit (sau un free tier contractual)**: stabilitate de model,
   fără antrenare pe date proprii, fără miracole de cotă.
3. **Cloudflare Pro — $20/lună (opțional)**: optimizare imagini, WAF/bot mai bune —
   util mai ales dacă traficul crește și valurile de boți devin zgomotoase.

Notă: ordinea e dictată de măsurători, nu de preferințe. Până atunci, documentul de față este
harta constrângerilor cu care planificăm.

---

## 11. Surse

**Documentație oficială (accesată 2026-10-04):**
- Cloudflare Workers — Limits: <https://developers.cloudflare.com/workers/platform/limits/>
- Cloudflare Workers — Pricing (KV, Queues, D1, Durable Objects, Static Assets):
  <https://developers.cloudflare.com/workers/platform/pricing/>
- Cloudflare Workers Builds — Limits & pricing: <https://developers.cloudflare.com/workers/ci-cd/builds/limits-and-pricing/>
- GitHub Actions — scheduled workflows (întârzieri, dezactivare la 60 de zile):
  <https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule>
- GitHub Pages — Limits: <https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits>
- GitHub Changelog — pricing Actions (dec. 2025; amânare + reduceri): <https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/>
- Gemini API — Rate limits: <https://ai.google.dev/gemini-api/docs/rate-limits>
- Groq — Rate limits: <https://console.groq.com/docs/rate-limits>
- Cerebras — Rate limits (fără tier free permanent): <https://inference-docs.cerebras.ai/support/rate-limits>
- OpenRouter — Limits: <https://openrouter.ai/docs/api_reference/limits>
- EUR-Lex — Directiva (UE) 2019/790, Art. 15 (RO): <https://eur-lex.europa.eu/eli/dir/2019/790/oj?locale=ro>

**Presa tehnologică majoră (accesată 2026-10-04):**
- The Verge — „A massive Cloudflare outage brought down X, ChatGPT, and even Downdetector"
  (18 nov. 2025): <https://www.theverge.com/news/822869/cloudflare-is-down-outage-x-twitter-downdetector>
- CNBC — „Cloudflare says outage that hit X, ChatGPT and other sites is resolved" (18 nov. 2025):
  <https://www.cnbc.com/2025/11/18/cloudflare-down-outage-traffic-spike-x-chatgpt.html>
- Mashable — „Cloudflare down: What we know about the outage so far" (18 nov. 2025):
  <https://mashable.com/article/cloudflare-down-outage-november-18>
- Bilanț de impact al penei din 18 nov. 2025 (7,5 mil. site-uri; 2,1 mil. raportări), sinteză
  cu trimitere la BBC: <https://www.sangfor.com/blog/cloud-and-infrastructure/cloudflare-outage-nov-2025>
- PCMag — „AI Is Still Hammering News Sites, Google Search and Social Referrals Plunge"
  (Chartbeat: −33% global / −38% SUA), ian. 2026:
  <https://www.pcmag.com/news/ai-is-still-hammering-news-sites-google-search-and-social-referrals-plunge>
- TechCrunch — LinkedIn „seems like AI slop" + „more bot traffic than humans" (iul. 2026):
  <https://techcrunch.com/2026/07/30/linkedin-adds-a-button-to-report-ai-generated-slop/>
- Techtimes / Cloudflare Radar — boți 57,5% din cererile HTML (iun. 2026):
  <https://www.techtimes.com/articles/317877/20260605/bot-traffic-passes-humans-online-cloudflare-says-agentic-ai-drove-575-share.htm>
- Forumul dezvoltatorilor Google AI — reducerea cotelor free Gemini, dec. 2025 (inclusiv
  răspunsul Google în fir): <https://discuss.ai.google.dev/t/do-they-really-think-we-wouldnt-notice-a-92-free-tier-quota/111262>
- Analize 2026 anti-„AI slop" (update-uri spam Google, „scaled content abuse"):
  <https://mintec.co/blog/spam-update-agosto-2026-no-es-ia/> ·
  <https://trueranker.com/blog/google-discover-core-update-february-2026-ai-slop/>
- Precedente de închidere a free tier-urilor: X API (feb. 2026) —
  <https://postproxy.dev/blog/x-api-pricing-2026/> · Qwen OAuth (15 apr. 2026) —
  <https://news.ycombinator.com/item?id=47789014>

**Dovezi interne (repo, comise):**
- `specs/cloudflare-free-2026-09.md` — calculul 20.000 fișiere, 51.896 → 16.732, TTL 21,
  confirmarea pe live a cifrei „înainte";
- `generator/config.py` — `OUTPUT_FILE_CEILING=20000`, `OUTPUT_FILE_BUDGET=17000`,
  `ARTICLE_TTL_DAYS=12` și istoricul comentat 30→21→20→11→12, incidentul din 2026-08-21;
- `wrangler.jsonc` — `run_worker_first` minimal, nota despre 100.000 invocări/zi;
- `infra/push.js` — plafonul de 1.000 scrieri KV/zi și «maxim o alertă pe zi»;
- `infra/worker-404-mirror.js` — oglinda ca infrastructură de producție, rute cu listă pozitivă,
  „canary lipsește pe Free";
- `notes/plan-master-izz-2026-10-03.md` — lanțul „fișiere puține → TTL mic → 404 pe linkuri
  vechi → cititorul pierdut".

---

**[NEVERIFICAT] rămas de măsurat:** cota exactă Workers Builds consumată lunar de proiect
(nu e citibilă prin conectorul Cloudflare; de urmărit de proprietar); numărul exact de invocări
zilnice consumate de fallback-ul de 404 pe live; cota free Gemini acordată contului în acest
moment (se vede doar în AI Studio).
