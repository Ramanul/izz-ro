# Auditul extern din 4 octombrie 2026 — verificare punct cu punct și propuneri

> **Ce este documentul.** Un audit extern al izz.ro (7 puncte forte, 7 probleme, verdict
> 7/10 tehnic · 4/10 viabilitate) a fost verificat mecanic, pe cod și pe datele reale,
> nu pe impresii. Rezultat: **3 probleme confirmate, 2 parțiale, 2 false** — iar cele două
> false sunt exact cele care ar fi consumat cel mai mult timp degeaba (bannerul de
> consimțământ și manifestul PWA). În plus, auditul ratează problema structurală.
>
> **Stare:** propunere. Nu s-a modificat cod. Fiecare cifră are comanda în anexă (secțiunea 12).

- **Verificat pe:** `main` @ `993b4fc` (4 oct 2026, 12:00 +0300), randare locală pe datele
  comise (`data/articles.json`, 11.892 itemi, max `published` = 4 oct 06:59).
- **Limita sesiunii:** rețeaua de ieșire e blocată (`curl https://izz.ro/` → `000`, exit 35),
  deci **nimic nu e „confirmat pe live"**. Cifrele de mai jos sunt „verificat local".
  Ce trebuie neapărat văzut pe live e în P0.1 (secțiunea 10).

---

## 1. Verdictele, într-un tabel

| # | Punctul din audit | Verdictul meu | Cifra care decide |
|---|---|---|---|
| 1 | Risc SEO: conținut AI la scară | **CONFIRMAT**, cifrele reale sunt mai dure | 28 cuvinte median/articol (nu ~160); **94–97% dintr-o singură sursă**, nu sinteză |
| 2 | Lipsă banner de consimțământ cookies | **FALS** | Bara există și blochează GA4 + Clarity până la opt-in (consimțământ v3) |
| 3a | Diacritice inconsistente | **CONFIRMAT** (mic) | 1,7% din publicațiile ultimelor 24h (13/747) integral fără diacritice |
| 3b | Știri fără sursa afișată | **FALS** | 0 din 11.892 fără `original_link`/`source_name`; `sources-box` pe fiecare pagină |
| 4 | PWA rupt: `manifest.json` = 404 | **FALS** (cu o verificare rămasă) | Manifestul e `/static/site.webmanifest`, linkat în `<head>`, testat în CI |
| 5 | Vizual sărăcuț: 2 imagini, una fără `alt` | **PARȚIAL** | Măsurătoarea e corectă, interpretarea nu: arta e inline, `alt=""` e deliberat |
| 6 | Secțiuni goale („Inteligență artificială”) | **NU SE REPRODUCE** | Azi: 4 carduri în secțiune; categoria are 3 știri/24h |
| 7 | Model de business neclar | **CONFIRMAT** | Zero monetizare; newsletter-ul e *cablat în cod și inactiv* |

**Verdictul meu pe audit:** 7/10 tehnic e subevaluat (auditul nu a văzut gărzile deja
existente: anti-copiere, grounding, etichetare AI Act, human gate, sitemap-news corect
dimensionat). 4/10 pe viabilitate e corect ca notă, dar diagnosticul e greșit: problema nu
e că lipsesc imagini sau un banner, ci că **94% din pagini sunt un rezumat de 28 de cuvinte
dintr-o singură sursă, fără niciun strat propriu și fără audiență deținută**. Acolo se duc
eforturile, nu la simptome.

---

## 2. Problema 1 — conținut AI la scară: confirmată, dar diagnosticați corect

Auditul spune „~160 de cuvinte, fără autor”. Măsurat pe ultimele 24h:

| Tip | n (24h) | Cuvinte median | Max |
|---|---|---|---|
| B — rezumat dintr-o sursă | 699 | **28** | 40 |
| C — sinteză multi-sursă | 45 | 52 | 83 |

Iar compoziția pe model, pe tot setul: **11.261 B vs 631 C**; zi de zi, sinteza multi-sursă
e **3–6%** din volum. Adică promisiunea centrală a brandului („un subiect, toate sursele”)
acoperă sub o zecime din ce se publică, iar restul e exact tiparul pe care Google îl descrie
ca „scaled content abuse”. Cifra auditului (160 de cuvinte) era de fapt *generoasă*.

Ce **există deja** și trebuie contabilizat ca mitigare (nu ca scuză): gardă anti-copiere
(secvențe verbatim de ≥15 cuvinte blocate, `generator/verifica_sinteza.py`), grounding gate,
quality gate + dedup (1.293 duplicate de eveniment eliminate în randarea de azi), etichetare
AI Act (`digitalSourceType: trainedAlgorithmicMedia` + „generat automat” la prima expunere),
human gate, nouă pagini publice de transparență.

Ce **lipsește** — și asta e diferența dintre „site de rezumate” și „publicație”:
1. un strat propriu pe pagină (context, „ce urmează”, de ce contează) — nu mai mult text AI,
   ci text care nu se poate scrie decât la IZZ;
2. o identitate editorială numită (azi nu există nici „Redacția IZZ” ca semnătură);
3. distribuție proprie (newsletter-ul e mort, vezi secțiunea 8);
4. semnale E-E-A-T structurate (vezi constatarea 3 din secțiunea 9).

**Propunerile pentru acest punct sunt P0.3 + P1.2 (secțiunea 10).** Nu se rezolvă cu `noindex` și nu
se rezolvă scurtând și mai mult rezumatele.

---

## 3. Problema 2 — consimțământ: **fals pozitiv**

Bara de consimțământ există, e versionată (v3) și e corectă:

- `static/personalize.js`: GA4 și Microsoft Clarity se încarcă **doar** după „Activează”;
  pe „Nu, mulțumesc” nu pleacă nicio cerere; retragerea se face din butonul ◎, la fel de
  ușor ca acordarea (GDPR art. 7 alin. 3), inclusiv `gtag consent update` pe sesiunea curentă;
- Cloudflare Web Analytics e cookieless, deci nu cere consimțământ; politica din
  `content/legal/privacy.md` documentează temeiurile (Legea 506/2004 art. 4 + art. 6 GDPR).
- Detectarea hostului de producție (`HOSTURI_PRODUCTIE = ['izz.ro','www.izz.ro']`) oprește
  poluarea statisticilor din local/preview — un detaliu pe care majoritatea site-urilor
  mici nu-l au.

**De ce a părut absent** (probabil): bara se injectează din JavaScript. Un audit care
descarcă HTML-ul sau rulează un crawler fără JS nu o vede niciodată — iar pe „Nu” nu se
randează nimic, deliberat. Nu e un defect de conformitate; e un defect de *detectabilitate
pentru unelte*.

**Urmă reală, mică (P1.4):** retragerea se face printr-un buton ◎ fără etichetă text. Un
link static în subsol — „Setări consimțământ” → `/legal/privacy/` (cu ancoră dedicată pe
secțiunea de consimțământ) — costă zero, e vizibil fără JS și e standardul la care se uită o
autoritate de supraveghere.

---

## 4. Problema 3 — inconsistențe: jumătate confirmată

### 4a. Diacriticele — confirmat, dar e 1,7%, nu „unele texte”

Măsurat pe `data/articles.json`:

| Metrică | Valoare |
|---|---|
| Titlu **și** teaser fără nicio diacritică, ultimele 24h | **13 / 747 (1,7%)** |
| Idem, pe tot setul | 222 / 11.892 (1,9%) |
| Titluri fără nicio diacritică (24h) | 34 / 747 (4,6%) — dar multe sunt corecte („Cancelarul german Friedrich Merz…”) |

Cauza e identificată: **30 din 34** vin din model B cu `prompt_version = v2-esenta`, adică
output AI care a sărit diacriticele — nu o problemă de sursă, nu text preluat. Nu există
**nicio** verificare: `tools/qa_check.py` nu măsoară diacriticele, deci nimic nu prinde
regresia. Exemplul din audit („brand romanesc de cosmetice pe baza de apa termala”) e real
și tipic, dar e o minoritate — merită o gardă mecanică, nu o campanie de corectare manuală.

### 4b. Sursa afișată — fals pozitiv

`0` articole fără `original_link` sau `source_name` în tot setul; fiecare pagină randează
`sources-box` (verificat pe output și apărat de `tests/test_garda_editoriala.py`); cardurile
au `sources-inline` pentru C. Promisiunea „mereu cu link la sursă” **este** respectată în cod.
Ce a văzut auditorul e cel mai probabil un card „Anunț oficial”, unde sursa e instituția
emitentă și linkul duce la textul integral — comportamentul e cel documentat în metodologie.

---

## 5. Problema 4 — PWA: fals pozitiv, cu o verificare de 1 minut rămasă

- Manifestul e `static/site.webmanifest`, linkat în `<head>` cu `?v=<hash>` (cache-busting
  corect), complet (name, short_name, start_url, scope, display standalone, 3 iconițe,
  shortcuts) și verificat în `tests/test_pwa.py` (câmpuri + pictograme existente pe disc).
- `/manifest.json` **nu e o cale standard**, e doar o convenție: niciun browser nu o caută
  dacă `<link rel="manifest">` e prezent. Un audit care cere `/manifest.json` primește 404
  pe orice site care nu l-a adăugat „de formă”. Nu-l adăuga de formă.
- Restul real: SW-ul e la rădăcină (`/sw.js`, comentariul din fișier explică de ce nu în
  `/static/`), butonul de instalare e fix și exclus din `<nav>` (test dedicat).

**Ce rămâne de făcut (P0.1):** în sandboxul acesta rețeaua e blocată, deci **nu pot confirma
Content-Type-ul** servit de Workers pentru `.webmanifest`:

```shell
curl -sI "https://izz.ro/static/site.webmanifest?cb=$(date +%s)" | grep -i content-type
# așteptat: application/manifest+json   (dacă iese octet-stream, Chromium ignoră manifestul)
```

Dacă iese greșit, fix-ul e în `_headers`/configurația gazdei (nu în `<head>`). Și, separat,
de proces: **`specs/STATE.md` încă scrie „PWA + alerte push — PR DESCHIS, fără merge”, deși
`#434` e pe `main` din 4 oct, 12:00** — un început de derivă între starea scrisă și starea
reală.

---

## 6. Problema 5 — „vizual sărăcuț”: măsurătoarea e corectă, concluzia nu

Pe homepage-ul randat azi: **65 de carduri, 2 taguri `<img>`, 0 imagini fără atribut `alt`**
(unul are `alt=""`). Explicația e o decizie, nu o scăpare:

- arta ilustrațiilor **se desenează inline din CSS** (`_art.html` → un `div.art` cu compoziție,
  paletă și etape, `aria-hidden="true"`) tocmai ca să nu producă fișiere și cereri HTTP:
  comentariul din `templates/_art.html` o spune explicit — pe Workers Free (20.000 de fișiere
  per versiune), capturile comise consumau singure 65% din plafon. Azi: **1.214 fișiere de
  imagine pentru 9.495 de articole** (1.200 coperți proprii + arhiva pe coperta de categorie);
- `<img>` apare doar când există fotografie reală de lead (pool PD/CC0, #414) sau imagini din
  date (harta epicentrului);
- `alt=""` nu e „alt lipsă”: media din card stă într-un link `aria-hidden="true"
  tabindex="-1"` — e decorativă, iar `alt=""` e exact ce cere WCAG. Un `alt` descriptiv
  acolo ar dubla cititul pentru cine folosește un cititor de ecran.

**Ce e valid din observație:** în share-uri și pe Google Images, articolele din afara ferestrei
recente au ca `og:image` **coperta categoriei** — mii de pagini arată identic. Fereastra e
`OG_COVER_MAX_ARTICLES = 1200`: primele 1200 de articole (cele mai noi) își plătesc o
copertă proprie, restul — 8.295 din 9.495 la randarea de azi, adică 87% — cad pe coperta de
categorie. Deci problema e în arhivă, nu pe prima pagină; P1.3 se citește cu asta în față. Codul o știe deja
(comentariul din `render.py` spune de ce `sitemap-images.xml` listează doar imaginile
proprii). Fix-ul nu e „mai multe poze”, e **og:image propriu per articol** (P1.3), dimensionat
în bugetul de fișiere.

---

## 7. Problema 6 — secțiunea „Inteligență artificială” goală: nu se reproduce

Local, azi: **fiecare categorie are 4 carduri** pe homepage, inclusiv „Inteligență
artificială” (categoria are 3 publicații în ultimele 24h). Mecanismul care ar produce
simptomul există totuși și se poate explica:

- homepage-ul afișează doar itemi mai tineri de **72h** (`generator/home_fresh.py`); o
  categorie fără niciun item în fereastră nu randează nici titlul, nici „Vezi toate”;
- în schimb, **`/sectiuni/` listează toate cele 15 rubrici** ca tile-uri, iar subnav-ul
  afișează primele 11 categorii — inclusiv `ai` — indiferent de volum. Asta e, foarte
  probabil, ce a văzut auditorul: o rubrică listată, fără conținut în spate.

Nu e o eroare de cod, ci o chestiune de design: `ai` e în `SEED_CATEGORIES` (poate fi goală
fără să pice QA). Dacă vrei garanția că nu se mai vede niciodată o rubrică firavă, vezi P2.4.

---

## 8. Problema 7 — model de business: confirmat, cu o descoperire concretă

Zero monetizare vizibilă, corect. Dar auditul ratează faptul că **infrastructura de audiență
proprie există în cod și e inactivă**:

- `render._newsletter_html()` citește `content/newsletter.html` (embed Brevo) **și fișierul nu
  există** → secțiunea „Briefing” nu se randează;
- între timp, `content/legal/contact.md` promite: *„Abonează-te din formularul de pe pagina
  principală”* — promisiune neacoperită, azi, pe site.

Cu ~700–1.200 de articole/zi produse și zero audiență deținută, singurul activ care crește în
timp e cel care lipsește. Discuția de monetizare are deja un loc: issue **#271** (IZZ
Intelligence Hub / verticale comerciale) — decizie de proprietar.

---

## 9. Ce a ratat auditul (și merită mai mult decât ce a prins)

1. **Aritmetica reală a conținutului** — 28 de cuvinte, 94–97% sursă unică (secțiunea 2). E problema
   centrală și e invizibilă într-un audit de suprafață.
2. **Newsletter mort + promisiune neacoperită** pe `/contact/` (secțiunea 8).
3. **JSON-LD `Organization` fără `publishingPrinciples`, `correctionsPolicy`, `sameAs`** —
   pentru un site care declară deschis că textul e generat automat, acestea două sunt exact
   semnalele pe care Google le documentează pentru încredere. Costă 4 linii în
   `render._org_jsonld()`. E cel mai ieftin E-E-A-T disponibil.
4. **Nicio identitate editorială** (nici persoană, nici „Redacția IZZ” cu rol și contact) în
   niciun template sau pagină legală. Auditul a nimerit-o la recomandarea 6, dar ca „detalie”;
   e de fapt infrastructură de încredere.
5. **Bugetul de fișiere e aproape plin: 13.480 din 17.000** (bugetul intern; plafonul gazdei
   e 20.000 de fișiere/versiune). Orice recomandare de tipul „pune o imagine pe fiecare
   articol” (9.495 pagini) sparge deploy-ul. Arta inline nu e o economie de design, e o
   constrângere asumată — orice propunere de imagini trebuie dimensionată.
6. **Ce e deja corect și nu trebuie „reparat”:** `sitemap-news.xml` (1.000 URL-uri, **0 mai
   vechi de 48h**), 4 sitemap-uri + robots, feed cu 50 de itemi, 404 propriu, offline, CSP
   strict, `_headers` cu cache pe categorii de active. Aici auditul a avut dreptate să laude.

---

## 10. Propuneri prioritizate

### P0 — mecanic, ieftin, verificabil (zile, nu săptămâni)

| # | Ce | Unde | Criteriu de acceptare |
|---|---|---|---|
| P0.1 | Verificare live, 3 comenzi: Content-Type manifest, `/manifest.json` vs linkul real, TTFB | — | 3 rezultate scrise în `specs/STATE.md` (nu „presupus”) |
| P0.2 | **Garda de diacritice** — post-procesare: dacă titlul *și* teaserul n-au nicio diacritică, iar textul sursă are, se cere re-generare (un retry) sau se marchează; plus metrică în `qa_check` | `generator/process.py`, `tools/qa_check.py`, test nou | 0 articole publicate integral fără diacritice; metrica apare în QA |
| P0.3 | **E-E-A-T pack (4 linii + 1 pagină)**: `publishingPrinciples` → `/legal/method/`, `correctionsPolicy` → `/legal/corrections/`, `sameAs`; pagină „Redacția” cu rol responsabil + contact; semnătură „Redacția IZZ” (nu autor inventat) pe articol la nota AI Act | `generator/render.py`, `templates/article.html`, `content/pages/` | JSON-LD validat; orice cititor poate numi cine răspunde editorial |
| P0.4 | Sincronizează `specs/STATE.md` (PWA e pe `main`) + rând în `specs/registru.tsv` pentru analiza asta | `specs/` | starea scrisă = starea reală |

### P1 — produs (1–2 săptămâni)

| # | Ce | De ce |
|---|---|---|
| P1.1 | **Newsletter**: fie pui `content/newsletter.html` (Brevo, cost 0), fie scoți promisiunea din `contact.md` până există. Recomandat: pune-l | singura audiență care se acumulează; fără ea, fiecare articol moare în feed |
| P1.2 | **Strat original**: „Briefing de dimineață” (1/zi, marcat explicit *comentariu editorial*, nu rezumat AI) + 1 analiză semnată/săptămână | separă site-ul de „scaled content” prin ce nu poate fi agregat: judecată umană, marcată ca atare |
| P1.3 | **og:image propriu per articol**: rasterizarea artei inline (sau extinderea pool-ului PD/CC0), cu numărătoare în bugetul de fișiere | 87% din share-uri arată identic azi; CTR-ul din social e direct afectat |
| P1.4 | Link static în subsol „Setări consimțământ” → ancoră în politica de privacy | descoperirea retragerii nu mai depinde de un buton ◎ fără etichetă și de JS |

### P2 — decizie de proprietar (ating zone protejate sau bugete)

| # | Ce | De ce e decizie |
|---|---|---|
| P2.1 | Creșterea ratei de sinteză multi-sursă (azi 3–6%) | atinge clusteringul — zonă protejată (§10); cere probă empirică over/under-merge (§7) |
| P2.2 | Monetizare: sponsorizări locale marcate, membri/fondatori, IZZ Intelligence (#271) | model comercial + reguli de separare editorial/ comercial |
| P2.3 | Campanie de fotografii lead PD/CC0 pe verticalele cu trafic (nu pe tot volumul) | cost de licențiere/atribuire + buget de fișiere |
| P2.4 | Prag minim per rubrică pe homepage (ex. ≥3 itemi, altfel rubrica nu apare) | schimbă ce vede cititorul pe prima pagină |

---

## 11. Ce NU recomand (și de ce)

- **Nu adăuga încă un banner de cookie-uri.** Există, e corect și blochează tot până la opt-in;
  o a doua bară scade UX-ul și nu adaugă conformitate.
- **Nu crea `/manifest.json` doar ca să treacă un tool.** Întâi verifică Content-Type-ul
  (P0.1); linkul din `<head>` e contractul, nu calea.
- **Nu pune `alt` descriptiv pe arta decorativă din carduri** (`aria-hidden="true"` +
  `tabindex="-1"`): `alt=""` e alegerea corectă, nu o scăpare.
- **Nu „repara” problema de conținut cu `noindex`** sau scurtând și mai mult rezumatele.
  Ascunderea nu produce valoare; stratul editorial propriu (P1.2) da.
- **Nu umbla la cron ca să „repari” cadența** și nu relaxa clusteringul fără probă — ambele
  au deja articole în `specs/` care documentează de ce nu funcționează.

---

## 12. Anexă — comenzile care produc cifrele

```shell
pip install -r requirements.txt
python -m generator.main --render-only          # output/ pe datele comise

# structura publicabilă (modele, surse, ferestre)
python - <<'PY'
import json, collections
d = json.load(open('data/articles.json'))
print(collections.Counter(a['model'] for a in d))          # B 11261, C 631
print(collections.Counter(a['processed_by'] for a in d))   # gemini, official
PY

# calitatea publicabilă (rulat în CI)
python tools/qa_check.py

# homepage: câte imagini și câte carduri are, de fapt
python - <<'PY'
import re
h = open('output/index.html', encoding='utf-8').read()
print('img:', len(re.findall(r'<img', h)), '| carduri:', len(re.findall(r'<article class="card', h)))
PY

# sitemap-news: fereastra reală
python - <<'PY'
import re, datetime as dt
h = open('output/sitemap-news.xml', encoding='utf-8').read()
d = sorted(re.findall(r'<news:publication_date>(.*?)</news:publication_date>', h))
mx = dt.datetime.fromisoformat(d[-1])
print(len(d), 'URL-uri; mai vechi de 48h:', sum(1 for x in d if mx - dt.datetime.fromisoformat(x) > dt.timedelta(hours=48)))
PY

# diacritice (nu există unealtă în repo — măsurat pentru analiza asta)
python - <<'PY'
import json, re
d = json.load(open('data/articles.json'))
diac = re.compile('[ăâîșțĂÂÎȘȚ]')
last24 = [a for a in d if a['published'] > '2026-10-03T07:00:00+00:00']
bad = [a for a in last24 if not diac.search(a['title'] or '') and not diac.search(a.get('teaser') or '')]
print(len(bad), '/', len(last24))
PY
```

**Nu au putut fi verificate din sesiunea asta** (rețea blocată, `curl` → `000`):
Content-Type-ul manifestului pe live, starea reală a PWA pe producție, TTFB și greutatea
paginii pe rețea reală, dacă bara de consimțământ se vede pentru un vizitator real.
Numele exact al rolului neputut verifica: „confirmat pe live” — rămâne „verificat local”.
