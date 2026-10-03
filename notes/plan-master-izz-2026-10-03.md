# PLAN MASTER — izz.ro, de la plafon gratuit la produs care ține

**Data:** 2026-10-03 · **Ramură:** `arena/01a1034f-izz-ro`
**Scop:** un singur document din care se pot da sarcini, fără alt context. Orice cifră de aici
e măsurată în repo sau pe live la data de mai sus; ce nu e măsurat e marcat **[NEVERIFICAT]**.
**Cost total al planului: 0 lei.** Constrângerea reală nu e banul, ci cota.

---

## 0. De ce există planul: trei plafoane care se țin unul pe altul

| plafon | valoare măsurată | ce blochează |
|---|---|---|
| fișiere per versiune de Worker (plan Free) | **20.000**; buget intern `OUTPUT_FILE_BUDGET=17000`; live ~17.122 | câte articole intră în fereastră, deci **TTL** |
| `ARTICLE_TTL_DAYS` | **12** zile | cât trăiește un link trimis de un cititor |
| apeluri AI pe rulare | **40** (`MAX_AI_CALLS_PER_RUN`), ~6 rulări/zi | câte sinteze noi, ce ajunge la coadă rămâne nefăcut |

Lanțul: **fișiere puține → TTL mic → 404 pe linkuri vechi → cititorul pierdut.**
De asta planul începe cu eliberarea de spațiu, nu cu funcții noi.

**Măsurători de bază, randare reală (`python -m generator.main --render-only`, 3 oct 2026):**

```
TOTAL 14.483 fisiere | pagini articol 9.451 | imagini articol 1.214 | rest 3.818
extensii: html 11.114 · jpg 3.065 · xml 192 · json 46
directoare: local 3.683 · portraits 1.789 · sport 1.424 · subiect 1.344 · extern 1.221
```

`portraits:1789` a fost descoperirea: `_load_portraits()` copia tot directorul la fiecare
randare, iar scan-ul pe cele 11.114 HTML-uri a arătat **661 de portrete referite**. Deci
**1.128 de fișiere = 6,3% din plafon** erau publicate degeaba.

---

## 1. Fazele

### FAZA 0 — eliberarea cotei *(în lucru pe această ramură)*
**Scop:** același conținut, mai puține fișiere. Nimic nou pentru cititor, dar fără asta
fazele 1–3 se lovesc de plafon.

| felie | ce face | câștig măsurat |
|---|---|---|
| S1 portrete la cerere | `render._portret()` copiază doar portretul pe care o pagină îl arată; `htmlart` declară ce a desenat prin `portrete_cerute()` | **14.483 → 13.355** fișiere, marja 2.517 → **3.645** |
| S3 rutarea cozii lungi | workerul cere pe oglindă și `/subiect/`, `/ghiduri/`, `/legal/`, `/portraits/`, imaginile de articol — listă **pozitivă** | paginile care nu încap pe primar răspund, nu dau 404 |
| S4+S5 buget AI pe cote | `AI_CALLS_PER_PROVIDER × numărul de cote disponibile` | 40 → **80** cu Groq+Cerebras, **120** cu trei |

**Verificat:** `pytest -q` → **1881 passed** (bază 1862 + 19 teste noi), `ruff` curat,
`node --test` 7/7, cascada `groq+cerebras` construită real cu chei false → buget 80.

### FAZA 1 — promisiuni făcute și neținute
Site-ul promite deja aceste lucruri și nu le livrează. Costul de încredere e cel mai mare.

1. **Briefingul zilnic** — `render._newsletter_html()` citește `content/newsletter.html`,
   fișierul **nu există**, deci blocul nu se randează niciodată. Cititorul are azi două căi
   de întoarcere: RSS și bookmark.
2. **Legătura știre ↔ ghid** — articolul care zice „salariul minim" primește chenarul cu
   valoarea verificată și link spre ghid. E arhitectura cerută de `specs/romania-utila-mvp.md`,
   neimplementată. Determinist, zero AI.
3. **Controlul textului** — A−/A+/spațiere + CSS de print. Site-ul are `accessibility.md`
   și pa11y în CI, dar cititorul nicio pârghie.
4. **RSS complet** — `_feed_xml()` emite doar `title/link/guid/pubDate/description`;
   fără imagini, fără `category`, fără feeduri pe categorie/județ.
5. **Jurnal public de corecții** — linkul „Raportează o eroare" există în template;
   lipsește jurnalul datat care transformă cinstea în încredere.

### FAZA 2 — pagina fiecărui cititor
6. **„Localitatea mea"** — pin pe oraș/județ în `localStorage`; secțiunea județului meu
   prima pe home, cardurile din zona mea marcate. Datele există deja
   (`localities.json`, `geo.py`, `personalize.js` cu `reorderNav()`).
7. **Hub-ul de județ** — `/subiect/<județ>/` are azi un titlu, un RSS și o listă
   (verificat pe `/subiect/valcea/`). Devine: hartă + știri + anunțuri oficiale +
   avertizare meteo + ghiduri. **Zero pagini noi, zero AI.**
8. **`/alerte/`** — coduri ANM pe județe + cutremure ≥ 2,5 (deja adunate de `eventdata.py`)
   + calitatea aerului. ANM publică fără cheie; setul e pe data.gov.ro **CC BY 4.0**.

### FAZA 3 — diferențiere
9. **„Cum titrează fiecare sursă"** — `<details>` cu titlurile originale; datele există deja.
10. **Timeline + contradicții între surse** — felia din `specs/directiva-story-intelligence.md`
    (deja adoptată), doar pe cluster-e cu ≥ 3 domenii distincte.
11. **Structură pe anunțurile oficiale** — termen-limită, județ, tip, „expiră în X zile",
    extrase determinist. Azi sunt titlu + „citește la sursă" = zero informație.

### FAZA 4 — decizii de proprietar, nu de execuție
12. **TTL 12 → 15** — posibil după Fază 0, dar e decizia lui Alexandru (precedent IZZ-0421/0424;
    `tests/test_reguli.py` leagă cifra din `config.py` de raționamentul scris).
13. **Arhiva permanentă pe R2** — variantă B din `notes/decizie-arhiva-seo-2026-10-01.md`.
    R2 Free = 10 GB, fără taxă de ieșire. Necesită activare de serviciu + token.
14. **Comutatorul `MEDIA_ORIGIN`** — mecanismul de a muta imaginile pe a doua origine.
    Nu e implementat: ar muta traficul de imagini de pe Cloudflare (cache la margine,
    aceeași zonă) pe GitHub Pages și ar cere schimbare de CSP. Livrez analiza, nu comutatorul.

---

## 2. Dependențe (ordinea obligatorie)

```
FAZA 0 (S1) ──► eliberează 1.128 fișiere ──► FAZA 4.12 (TTL↑)
     │
     └──► S3 rutare ──► FAZA 2.7 (hub de județ) ──► FAZA 3.10 (timeline)
                        FAZA 2.6 (localitatea mea)

FAZA 0 (S4/S5 buget AI) ──► FAZA 3.10 (contradicții, cere AI)
                        └─► FAZA 3.11 (structură anunțuri, doar în varianta AI)

FAZA 1.2 (legătura știre↔ghid) ──► FAZA 1.1 (briefing-ul citează ghidurile)
FAZA 1.3, 1.4, 1.5 — independente, pot merge în paralel
```

**Regula de aur a ordinii:** niciun feature care consumă fișiere sau AI nu intră înainte ca
Faza 0 să fie măsurată pe live. Altfel mutăm plafonul, nu îl ridicăm.

---

## 3. Criterii măsurabile (fiecare se poate verifica cu o comandă)

| # | criteriu | cum se măsoară | țintă |
|---|---|---|---|
| C1 | fișiere în output | `python tools/count_output.py` | ≤ 13.500 (azi 13.355) |
| C2 | marjă sub plafon | idem, linia „sub buget, marja" | ≥ 3.600 |
| C3 | portrete publicate == referite | `tests/test_portrete_doar_folosite.py::test_bijectie…` | diferență 0 |
| C4 | rutare corectă | `pytest tests/test_worker_mirror_rutare.py` + `node --test` | 4 + 7 verzi |
| C5 | apeluri AI folosite/rulare | `build.json` → `ai_calls`, la 3 rulări consecutive | ≥ 70 cu 2 cote |
| C6 | iteme amânate pe buget | jurnalul pipeline, `deferred` | scădere față de baza măsurată |
| C7 | suita | `pytest -q` | 1881 passed, 0 failed |
| C8 | lint | `ruff check generator/ tools/ tests/` | All checks passed |
| C9 | 404 pe link vechi | `curl -o /dev/null -w "%{http_code}" https://izz.ro/<articol de 15 zile>` | 200, nu 404 |
| C10 | ghiduri neconfirmate | `https://izz.ro/ghiduri/` | 0 din 7 (azi **4 din 7**) |

C9 e criteriul care contează pentru cititor și nu se poate măsura decât după ce oglinda are
conținutul — deci după prima rulare a jobului `mirror` cu `keep_files: true` pe o fereastră
completă.

---

## 4. Roluri

| rol | cine | ce face | ce NU face |
|---|---|---|---|
| **Proprietar** | Alexandru | decide la punctele din §5; pune secretele în GitHub (Groq/Cerebras); verifică lunar Search Console | nu scrie cod |
| **Manager** | Claude Code | scrie spec-ul pe felie, ține `specs/STATE.md`, face merge după review | nu execută în orb |
| **Executor** | Arena / Devin / OpenCode / Mistral | implementează o felie, rulează `pytest` + `ruff`, raportează „cerut vs. livrat" | nu atinge fișiere din afara spec-ului, nu face merge |
| **CI** | GitHub Actions | singurul executor care ajunge la internetul real (feedcheck, audit live, deploy) | — |

**Regula de raportare a executorului** (din `AGENTS.md`, obligatorie): prima linie
*„cerut: X. Fac: Y."*, ultima linie *„cerut vs. livrat"* cu ce a rămas neatins numit explicit.

---

## 5. Punctele tale de decizie — doar cinci

Am tăiat tot ce se poate decide fără tine. Rămân astea:

1. **Cheile AI gratuite** — pui `GROQ_API_KEY` / `CEREBRAS_API_KEY` în
   *Settings → Secrets and variables → Actions*? Codul e deja cablat: fără ele nimic nu se
   schimbă, cu ele bugetul se dublează/triplează singur. *(cost: 5 minute, 0 lei)*
2. **TTL 12 → 15** — după ce C1/C2 sunt verificate pe live. Ridică fereastra cu ~3 zile.
3. **Versiunea maghiară** pentru județele cu comunitate maghiară — da/nu. Valoare reală,
   dar consumă buget AI și cere marcaj AI Act pentru traducere.
4. **„Cum titrează fiecare sursă"** — expune cât reformulăm. Eu recomand DA (site-ul deja
   declară asta), dar e decizie de poziționare.
5. **R2 pentru arhiva permanentă** — activare de serviciu nou pe cont, 0 lei. Sau rămânem
   pe gh-pages, care acoperă deja nevoia.

Tot restul din plan se poate executa fără să te întrebăm.

---

## 6. SĂPTĂMÂNA 1 — șase sarcini gata de dat

Fiecare e o felie verticală: un branch, un PR, verificare proprie. Se pot da în paralel,
în afară de W5 care depinde de W1.

### W1 — portrete + rutare *(deja scrisă pe ramura asta, de verificat și împins ca PR)*
- **Fișiere:** `generator/render.py`, `generator/htmlart.py`, `infra/worker-404-mirror.js`,
  `infra/worker-404-mirror.test.mjs`, `tests/test_portrete_doar_folosite.py`,
  `tests/test_worker_mirror_rutare.py`
- **Acceptare:** C1 ≤ 13.500, C3 diferență 0, C4 verde, C7/C8 verzi
- **Verificare:** `python -m generator.main --render-only && python tools/count_output.py`
- **Efort:** gata; rămâne review + merge

### W2 — buget AI pe cote *(deja scrisă, cere W1 doar ca ordine de merge)*
- **Fișiere:** `generator/main.py`, `generator/providers/base.py`, `generator/providers/cascade.py`,
  `.github/workflows/build.yml`, `tests/test_buget_ai_provideri.py`
- **Acceptare:** cu chei false, cascada are 2 cote și bugetul e 80; fără `AI_CALLS_PER_PROVIDER`
  comportamentul e identic cu cel vechi
- **Verificare:** `pytest tests/test_buget_ai_provideri.py -q` → 9 passed
- **Depinde de:** §5.1 (cheile tale) ca să aibă efect în producție

### W3 — briefingul zilnic `/azi/`
- **Ce:** o pagină statică generată din `articles.json`: data, cele 8 subiecte mari,
  numărul de surse, linkuri. Plus `content/newsletter.html` pentru embed Brevo.
- **Fișiere:** `templates/azi.html` (nou), `generator/render.py` (o funcție + un `_write`),
  `content/newsletter.html` (nou), `tests/test_azi.py` (nou)
- **Acceptare:** pagina răspunde 200, conține ≥ 8 linkuri spre articole, zero text AI nou
  (doar titluri existente), un singur fișier în plus la C1
- **Verificare:** `python -m generator.main --render-only && test -s output/azi/index.html`
- **Efort:** S (3–4 h)

### W4 — controlul textului + print
- **Ce:** trei butoane (A− / A+ / spațiere) care setează un atribut pe `<html>`, salvat în
  `localStorage`; `@media print` pentru articol.
- **Fișiere:** `static/personalize.js`, `static/styles.css`, `templates/article.html`,
  `tests/test_accesibilitate_text.py` (nou)
- **Acceptare:** butoanele există pe pagina de articol, atributul persistă după reload,
  fără JS site-ul rămâne identic, `prefers-reduced-motion` respectat
- **Efort:** S (3–4 h)

### W5 — legătura știre ↔ ghid
- **Ce:** când un articol menționează o entitate de ghid, pagina primește chenarul
  „Ai nevoie să știi: valoarea curentă e X, verificată la <data>" + link; ghidul listează
  ultimele 3 știri pe tema lui.
- **Fișiere:** `generator/render.py`, `templates/article.html`, `templates/ghid.html`,
  `tests/test_legatura_ghid.py` (nou)
- **Acceptare:** un articol cu „salariul minim" în text are chenarul; determinist (fără AI);
  zero fișiere noi; C7 verde
- **Depinde de:** W1 (ordinea de merge, ca să nu ne ciocnim în `render.py`)
- **Efort:** S (3–5 h)

### W6 — RSS complet + feeduri pe categorie
- **Ce:** `_feed_xml()` primește `category`, `dc:creator`/surse și imagine; se scrie un
  `feed.xml` per categorie (~15 fișiere).
- **Fișiere:** `generator/render.py`, `tests/test_feed_rss.py` (existent, de extins)
- **Acceptare:** feedul validează, are `category` pe fiecare item, C1 crește cu ≤ 60
- **Efort:** S (3–4 h)

**Total Săptămâna 1:** ~4 zile de lucru agent, 0 lei, zero decizii blocate în afară de §5.1.

---

## 7. Cerut vs. livrat (starea la ora acestui commit)

**Livrat și verificat pe ramura asta:**
- S1 portrete la cerere: 14.483 → **13.355** fișiere (măsurat cu `tools/count_output.py`),
  6 teste noi, bijecție portrete 661/661
- S3 rutarea cozii lungi: listă pozitivă, 7 teste JS + 4 teste Python de sincronizare
- S4+S5 buget AI pe cote: 9 teste, cascada `groq+cerebras` → buget **80** (măsurat)
- `pytest -q` → **1881 passed, 4 skipped, 8 xfailed**; `ruff check` → All checks passed

**Nelivrat, numit explicit:**
- **`MEDIA_ORIGIN` (mutarea imaginilor pe a doua origine) nu e implementat.** Ar fi eliberat
  încă ~1.214 fișiere, dar cere schimbare de CSP și mută traficul de imagini de pe Cloudflare
  pe GitHub Pages. E o decizie de produs (§5), nu o felie de execuție.
- **TTL-ul nu e atins.** Rămâne 12. Spațiul e eliberat; decizia e a ta.
- **R2 nu e activat.** gh-pages acoperă azi aceeași nevoie, e deja configurat și verificat
  de `tools/verify_release.py`.
- **Nicio funcție nouă pentru cititor din Fazele 1–3.** Planul lor e aici, execuția e în
  Săptămâna 1 și după.
- **Nu am putut măsura traficul real** (100.000 cereri/zi pe Workers Free) — `tools/trafic_cloudflare.py`
  cere tokenul Cloudflare din runner. Până la măsurătoare, rutarea pe oglindă e limitată la
  HTML și la imaginile articolelor, nu la tot static-ul.
