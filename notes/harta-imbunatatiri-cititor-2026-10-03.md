# HARTA îmbunătățărilor pentru cititor — izz.ro, 0 lei

**Data:** 2026-10-03 · **Tip:** analiză de consultant, fără implementare · **Autor:** agent Arena (sesiune de consultanță)
**Cerere:** harta completă a îmbunătățărilor cu impact mare pentru cititorul din România, ordonate după valoare,
doar soluții gratuite, excluzând ce e deja în lucru (Pagefind, PWA+web push, poze Wikidata pe coperte,
măsurătoare og:image, diagnostic hartă primării).

Fiecare afirmație despre cod e citită în repo la data de mai sus; fiecare afirmație despre live e citită pe
paginile publice în aceeași zi. Ce n-am putut verifica e marcat **[NEVERIFICAT]**.

---

## 0. Ce am verificat înainte să propun ceva

**Pe live (2026-10-03, seara):**

| fapt | unde l-am citit |
|---|---|
| 607 știri · 69 surse · 11 județe în ultimele 24 de ore | dateline pe `izz.ro/` |
| căutarea indexează **9.451** de știri pe 12 zile și spune explicit „titluri și categorii, nu textul integral” | `izz.ro/cauta/` |
| `/instrumente/` are **un singur** instrument: calculator salariu net | `izz.ro/instrumente/` |
| `/ghiduri/` are **7 ghiduri, 4 „Neconfirmat”** | `izz.ro/ghiduri/` |
| pagina de articol **nu are** share, „Raportează o eroare”, „Articole conectate” | `izz.ro/local/incendiu-puternic-la-o-hala-de-vopseluri-din-sutesti-valcea/` |
| `/subiect/valcea/` = titlu + RSS + 6 conexiuni + 12 linkuri, atât | `izz.ro/subiect/valcea/` |
| bara de consimțământ GA4 + Clarity apare pe fiecare pagină | orice pagină |
| mini-harta „România în ultimele 24 de ore” e deja pe prima pagină (faza 2 a aterizat) | `izz.ro/` + `templates/index.html` |

**În repo:**

| fapt | unde |
|---|---|
| există 4.307 pagini de subiect; feedurile de subiect au fost tăiate la un prag pentru că 2.118 feeduri = 11% din plafonul de 20.000 | comentariu `generator/render.py:1005-1015` |
| `OUTPUT_FILE_BUDGET = 17000`, plafon real Workers Free 20.000, live ~17.122 fișiere, marjă ~2.900 | `generator/config.py:414`; `notes/decizie-arhiva-seo-2026-10-01.md` |
| `ARTICLE_TTL_DAYS = 12` | `generator/config.py:394` |
| pagina de newsletter există în cod dar **`content/newsletter.html` lipsește** → secțiunea nu se randează niciodată | `generator/render.py:1229-1237`, `templates/index.html:82` |
| `/instrumente/` promite în meta description „salariu net, TVA, dobândă”, dar `tools` are o singură intrare | `templates/instrumente.html:4`, `generator/render.py:1386-1389` |
| `templates/article.html` conține share, `article-accountability` cu mailto de eroare, `related`, `people` — deci **live-ul e în urma lui main** | `templates/article.html` |
| motor de personalizare client-side (profil în localStorage, „pentru tine”, reorder nav, statistici, retractare consimțământ) | `static/personalize.js` (440 linii) |
| meteo + seisme deja cablate pe surse gratuite (open-meteo, seismicportal.eu, mag ≥ 2.5) | `generator/eventdata.py` |
| directiva Story Intelligence e **adoptată** 2026-10-01 (story → surse → fapte → contradicții → timeline) | `specs/directiva-story-intelligence.md` |
| bugetul AI e saturat la fiecare rulare; ordinea din `config.SOURCES` funcționează ca politică editorială nedeclarată | `specs/ai-budget-ordering.md` |
| arhiva veche e recuperabilă din git (`tools/arhiva.py`), dar „Google nu vede git” | `tools/arhiva.py`, `notes/decizie-arhiva-seo-2026-10-01.md` |
| spec-ul „România Utilă” cere pagini permanente + 4 instrumente; au aterizat 7 ghiduri + 1 calculator | `specs/romania-utila-mvp.md` vs. live |

---

## 1. Cele patru constrângeri care decid tot

Orice idee trebuie să treacă de aceste patru porți, altfel e doar o listă de dorințe:

1. **Cota de fișiere: ~2.900 de fișiere libere din 20.000.** O idee care costă mii de pagini e moartă
   înainte de discuție (așa au murit feedurile de subiect). Consecință: **mai întâi eliberăm spațiu,
   apoi construim.** Cea mai ieftină eliberare: imaginile de copertă în dublu format (png + webp) —
   verificat în `_card.html` și `article.html`, ambele variante se scriu pe disc.
2. **Bugetul AI e deja saturat.** Orice feature nou care cere un apel AI în plus pe articol concurează
   cu sintezele existente. Consecință: prioritizăm ce se face **determinist, din date deja adunate**,
   sau ce se face pe un eșantion mic și fix (ex. 20 de articole/zi).
3. **TTL 12 zile.** Conținutul dispare. Asta nu e doar problemă SEO, e problemă de **încredere**:
   un link trimis pe WhatsApp acum două săptămâni e mort.
4. **0 lei.** Există, dar cere atenție la *cota* fiecărui serviciu gratuit, nu doar la preț.
   Mai jos, pentru fiecare idee, „de ce e gratuit” înseamnă: serviciul + plafonul + ce facem dacă plafonul se atinge.

---

## 2. P0 — reparații de valoare: promisiuni făcute și neținute

Acestea sunt primele nu pentru că sunt „drăguțe”, ci pentru că site-ul **promite deja** lucrul respectiv
și nu-l livrează. Costul de încredere e cel mai mare din toată lista.

### 1. Newsletter-ul fantomă — codul există, fișierul lipsește
- **Ce e.** `render._newsletter_html()` citește `content/newsletter.html` și îl injectează pe prima pagină
  (`templates/index.html:82`). Fișierul nu există, deci blocul nu se randează niciodată. Cititorul de azi
  are **exact două** căi de a reveni: RSS și bookmark.
- **De ce contează.** Un agregator fără canal de revenire depinde de Google pentru fiecare vizită.
  „Urmărește IZZ.ro în ritmul tău” (secțiunea deja randată pe prima pagină) oferă doar RSS — pentru
  cititorul român obișnuit, RSS e o tehnologie invizibilă.
- **De ce e gratuit.** Brevo (fostul Sendinblue) are nivel gratuit ~300 de e-mailuri/zi; lista de contacte
  e nelimitată. Alternativa 100% fără cont extern: un briefing zilnic ca pagină statică (`/azi/`),
  generat din `articles.json` la build — zero servicii, zero GDPR, zero cotă. Recomand **ambele în ordinea asta**:
  `/azi/` întâi (nu depinde de nimeni), embed Brevo după.
- **Efort.** `/azi/` = S (3-4 h, un template + o funcție în render). Brevo embed = S (1 h), dar cere contul proprietarului.
- **Risc.** Un newsletter cu conținut AI necitit de un om e o responsabilitate. Soluția: briefingul conține
  doar titluri + linkuri + numărul surselor, nu text sintetic nou.

### 2. „Localitatea mea” — prima pagină a fiecărui cititor
- **Ce e.** Un selector de oraș/județ (o singură dată, salvat în `localStorage`) care: (a) pune secțiunea
  locală a județului meu prima pe home, (b) marchează cardurile din zona mea, (c) filtrează harta și
  `/subiect/<județul-meu>/` în nav.
- **De ce contează.** E cel mai mare diferențiator disponibil: nicio publicație națională nu poate face
  pagina fiecărui cititor. IZZ are deja datele — `data/localities.json` (SIRUTA), `data/harta_localitati.json`,
  `generator/geo.py`, și fiecare card are deja `data-cat`/`data-source`/`data-title` pentru motorul client-side.
- **De ce e gratuit.** 100% client-side: zero fișiere noi, zero AI, zero servicii. Se agață de
  `static/personalize.js`, care face deja exact acest tip de muncă (profil în localStorage, `reorderNav()`).
- **Efort.** M (6-10 h): UI selector + filtrare pe județ + test de randare. Cea mai mare parte e deja scrisă.
- **Ce NU facem.** Nu geolocație prin IP fără consimțământ — ar strica poziția de privacy pe care site-ul o declară.

### 3. Linkul mort la 12 zile — rezolvat cu ce avem deja
- **Ce e.** La expirare, în loc de 404: (a) 301 spre `/subiect/<entitatea principală>/` — pagină care
  există deja și e permanentă, (b) pe pagina de subiect, articolul rămâne listat ca titlu + sursă
  (deja se întâmplă: `/subiect/valcea/` listează articole din 22 septembrie, adică dincolo de TTL).
- **De ce contează.** Cititorul care primește un link pe WhatsApp și dă de 404 nu mai dă a doua oară.
  Iar pagina de subiect e **singurul** URL permanent pe care site-ul îl are azi — folosită corect,
  devine coloana vertebrală: „știrea moare, subiectul rămâne”.
- **De ce e gratuit.** Zero fișiere noi (paginile de subiect există), 40 de redirecturi folosite din ~2.000
  (măsurat în `notes/decizie-arhiva-seo-2026-10-01.md`), `_redirects` e deja generat (`render.py:1783`).
- **Efort.** M (4-8 h): lista de redirecturi la expirare + un test. Atenție: documentul de decizie recomandă
  varianta A (status quo) — asta e varianta C, dar aplicată **selectiv**, doar pe articolele care au un
  subiect cu ≥ N articole, deci sub plafonul de reguli.
- **Variantă mai scumpă (dar tot 0 lei).** Arhiva text pe Cloudflare R2 Free (10 GB, fără taxă de ieșire)
  cu un worker de rutare. E variantă B din `notes/decizie-arhiva-seo-2026-10-01.md`. Costă 1-2 zile,
  nu bani. O recomand **doar** dacă Search Console arată trafic real pe URL-uri expirate.

### 4. RSS-ul subțire — cel mai ieftin upgrade din listă
- **Ce e.** `_feed_xml()` (`render.py:1848`) emite `title/link/guid/pubDate/description`. Atât.
  Fără `category`, fără imagine, fără `dc:creator`/surse, fără feeduri pe categorie sau pe județ.
- **De ce contează.** Cititorul de RSS (mic, dar cel mai loial) primește azi un flux fără imagini și fără
  filtru pe categorie. Iar un feed pe județ e exact ce lipsește pentru „localitatea mea” fără JavaScript.
- **De ce e gratuit.** Datele sunt deja în `articles.json`; un `feed.xml` pe categorie = ~16 fișiere,
  unul pe județ = ~42. Total sub 60 de fișiere din marja de 2.900.
- **Efort.** S (3-4 h), inclusiv test pe XML.
- **Capcană.** Nu reintroducem mii de feeduri de subiect — au fost tăiate deliberat (`render.py:1005-1015`).

### 5. Pagina de articol: ce e pe main dar nu e pe live
- **Ce e.** **[NEVERIFICAT — semnal, nu concluzie]** Pagina live a articolului despre incendiul din Șuțești
  (publicat 3 oct 19:53) nu conține share, „Transparență și corecții”/„Raportează o eroare”, nici
  „Articole conectate” — toate patru sunt în `templates/article.html` de pe `main` la `093cb47`.
  Clona mea e shallow (un singur commit), deci nu pot data schimbarea.
- **Verificare (10 secunde).** `curl -s https://izz.ro/local/incendiu-puternic-la-o-hala-de-vopseluri-din-sutesti-valcea/ | grep -c "Raporteaz"`,
  apoi `curl -s https://izz.ro/build.json` și compară `BUILD_COMMIT_SHA` cu `git rev-parse origin/main`.
- **De ce contează.** Dacă e o întârziere de deploy, atunci o parte din munca de transparență a ultimelor
  săptămâni **nu ajunge la cititor**. Asta nu e o îmbunătățire, e o scurgere.
- **Efort.** Diagnostic: S (15 min). Dacă e regresie de build: depinde de cauză.

### 6. „Raportează o eroare” vizibil + jurnal public de corecții
- **Ce e.** Linkul mailto există în template. Lipsește **partea care contează**: o pagină
  `/corectii/` cu lista corecțiilor făcute (dată, articol, ce era greșit, ce e acum), generată din
  `content/legal/corrections.md` + un registru simplu, și un flux „cititorul a raportat → apare în jurnal”.
- **De ce contează.** Site-ul publică text generat automat și o spune cinstit (`ai-note`). Singurul mod
  în care cinstea aia devine **încredere** e un jurnal de erori vizibil, cu data. Nicio publicație românească
  nu face asta; e diferențiator de brand, nu doar igienă.
- **De ce e gratuit.** Pagină statică + GitHub Issues (gratis, nelimitat, deja folosit). Un workflow
  poate transforma un issue etichetat `corectie` într-o intrare în jurnal la build.
- **Efort.** S-M (4-6 h).

### 7. Anunțurile oficiale primesc structură
- **Ce e.** Azi un „Anunț oficial” = titlu + nota „citește textul integral la sursă”. Adică exact zero
  informație. Extragem **determinist** din titlul instituției: termenul-limită (o dată), județul/localitatea
  (din gazetteer, deja există), tipul (licitație / întrerupere apă / audiențe / taxă) și le afișăm ca
  trei câmpuri + un „expiră în X zile”.
- **De ce contează.** Ăsta e conținutul pe care nimeni altcineva nu-l structurează și care chiar schimbă
  ziua cuiva: „apa se oprește mâine pe strada mea”, „licitația e joi”.
- **De ce e gratuit.** Regex + gazetteer existent (`data/localities.json`, `generator/localities.py`).
  Zero AI, deci zero competiție cu bugetul saturat. Fail-safe ca în `eventdata.py`: dacă nu extrage sigur,
  nu afișează nimic.
- **Efort.** M (6-8 h) pentru varianta deterministă. Varianta cu AI costă buget și o amân.

---

## 3. P1 — valoarea de zi cu zi

### 8. `/alerte/` — pagina pe care o deschizi dimineața
- **Ce e.** O singură pagină cu: codurile meteo ANM active pe județe (cu intervalul de valabilitate),
  cutremurele ≥ 2.5 din ultimele 24 h (deja adunate de `eventdata.py` de la seismicportal.eu), calitatea
  aerului pe orașe mari, și — dacă există — întreruperi de utilități din anunțurile oficiale.
- **De ce contează.** E singurul tip de conținut pentru care un om revine **zilnic, fără să fie împins**.
  IZZ are deja jumătate din el (seisme + meteo pe coperte), dar îl folosește decorativ, pe copertă, nu ca serviciu.
- **De ce e gratuit.** ANM publică fără cheie: `avertizari-nowcasting-xml.php`,
  `wp-json/meteoapi/v2/starea-vremii`, `anm/prognoza-orase-xml.php`, plus RSS
  (`anm2/avertizari-rss.php`); setul e publicat pe data.gov.ro sub **CC BY 4.0**. Cutremure: deja integrat.
  Aer: open-meteo air-quality (fără cheie) sau EEA Discomap; aqicn.org are cheie gratuită cu cotă.
- **Efort.** M (8-12 h): un fetcher nou după modelul `eventdata.py` (care are deja izolare de rețea + fail-safe),
  o pagină, un test offline.
- **Capcană.** Nu promite „alerte în timp real” — build-ul rulează la ~2 h. Formula corectă: „verificat la <ora>”.

### 9. Pagina de județ devine hub local — pe pagini care există deja
- **Ce e.** `/subiect/valcea/` are azi 12 linkuri. Devine: harta județului cu evenimentele (datele sunt în
  `harta_judete.json`), știrile județului, anunțurile oficiale de la primăriile monitorizate, avertizarea
  meteo activă pe județ, portretul (deja cablat, `portraits.get(...)`), ghidurile relevante și RSS-ul.
- **De ce contează.** 4.307 pagini de subiect sunt cel mai mare activ nefolosit al site-ului: URL-uri
  permanente, deja indexate, care azi sunt o listă goală. Pentru un cititor din Râmnicu Vâlcea, pagina
  asta devine „pagina mea”.
- **De ce e gratuit.** Zero pagini noi (le actualizăm pe cele existente), zero AI (toate datele există),
  zero servicii.
- **Efort.** M-L (10-16 h): template + context în `render.py` + teste. Se face în două felii: felia 1 = județe
  (42 de pagini, valoare maximă), felia 2 = persoane/entități.
- **Notă de coordonare.** Nu intră peste „diagnostic hartă primării” (exclus) și nici peste IZZ-0405
  (ierarhia vizuală a markerelor) — astea sunt despre hartă, asta e despre pagină.

### 10. Calculatoarele promise: TVA, dobândă, alocații, „ce acte îmi trebuie”
- **Ce e.** `templates/instrumente.html` promite în meta description „salariu net, TVA, dobândă”.
  Pe live e doar salariul net. `specs/romania-utila-mvp.md` cere patru instrumente, inclusiv
  **verificatorul „ce acte îmi trebuie”** — singurul care rezolvă o durere reală, nu o curiozitate.
- **De ce contează.** „Ce acte îmi trebuie pentru pașaport / pentru înscrierea la școală / pentru alocație”
  e o căutare cu volum mare și răspunsuri proaste peste tot în web-ul românesc. Ghidurile există deja
  (7 entități YAML) — lipsesc doar formularele.
- **De ce e gratuit.** Același model de date (`data/entities/*.yaml`), aceeași randare. Nicio valoare nouă
  de verificat pentru TVA (19%/21% e în ghidul de taxe dacă există; dacă nu, se adaugă cu sursă oficială).
- **Efort.** S fiecare (2-4 h), pentru că `_render_calc_salariu` e deja șablonul. Total ~2 zile pentru toate patru.
- **Regulă.** Niciun calculator nu se publică fără sursa oficială și data verificării — altfel repetăm
  problema celor 4 ghiduri „Neconfirmat”.

### 11. Curățarea celor 4 ghiduri „Neconfirmat” + un program de verificare
- **Ce e.** Pensia minimă, buletin/pașaport, permis auto, Noua Casă stau pe live cu eticheta „Neconfirmat”.
  Adică site-ul însuși le spune cititorilor „nu te baza pe ele”.
- **De ce contează.** Un ghid neconfirmat e mai rău decât absența lui: ocupă locul din SERP și din mintea
  cititorului. IZZ are deja șablonul corect (verificat: alocații, ANAF, salariul minim au „Verificat: 2026-09-04”).
- **De ce e gratuit.** Muncă de verificare pe surse oficiale (Monitorul Oficial, CNPP, ANAF, DGI) +
  un workflow CI care marchează automat un ghid ca „verificare expirată” după 90 de zile.
- **Efort.** S (2-3 h de documentat) + M (4 h) pentru automatizarea expirării.

### 12. Legătura automată știre ↔ ghid permanent
- **Ce e.** Când un articol menționează „salariul minim”, „alocații”, „pensie”, „ANAF”, „Noua Casă”,
  pagina primește un chenar: „**Ai nevoie să știi:** valoarea curentă e X, verificată la <data>, [ghid]”.
  Și invers: ghidul listează ultimele 3 știri pe tema lui.
- **De ce contează.** Exact arhitectura cerută de `specs/romania-utila-mvp.md` („știrile trimit spre pagina
  permanentă, pagina permanentă trimite spre știri”) și neimplementată. E cea mai ieftină creștere a
  valorii per pagină: transformă o știre de 60 de cuvinte într-un răspuns util.
- **De ce e gratuit.** Potrivire de cuvinte-cheie pe entități existente — determinist, zero AI, zero fișiere.
- **Efort.** S (3-5 h).

### 13. „Ce înseamnă pentru tine” — dar fără AI nou
- **Ce e.** O propoziție care traduce știrea în consecință pentru cititor. **Nu** o cerem modelului pe
  fiecare articol (bugetul e saturat, `specs/ai-budget-ordering.md`). O generăm acolo unde e calculabilă:
  articolele care ating o entitate de ghid (vezi #12), plus un eșantion fix de 20 de articole/zi.
- **De ce contează.** E diferența dintre „a aflat” și „a înțeles” — exact promisiunea „Zero Zgomot”.
- **De ce e gratuit.** Fie din date existente (determinist), fie din bugetul AI existent, realocat, nu suplimentat.
- **Efort.** M (6-8 h), inclusiv garda de grounding (există `tools/grounding_gate.py`).
- **Dependență reală.** Dacă vrem asta pe scară largă, întâi trebuie rezolvată ordinea bugetului AI
  (`specs/ai-budget-ordering.md`): azi „ce ajunge la coada e infometat”.

---

## 4. P2 — diferențiere (ce nu mai face nimeni în România)

### 14. Timeline-ul poveștii + contradicțiile între surse
- **Ce e.** Pe un subiect cu ≥ 3 surse: „cum a evoluat” (o listă cronologică a faptelor noi) și
  „sursele nu sunt de acord” (când Digi24 zice 30 de tone și altă publicație zice altceva).
- **De ce contează.** E singura funcție care face un agregator **necesar** în loc de comod. Iar pentru
  un site care sintetizează automat, transparența pe contradicții e cea mai puternică formă de onestitate.
- **De ce e gratuit.** Datele sunt deja în cluster (`generator/cluster.py`) și în `sources`. Partea de
  extragere a faptelor costă AI — deci se face doar pe cluster-e mari (≥ 3 domenii distincte), care sunt
  puține, nu pe toate articolele.
- **Efort.** L (2-3 zile). **Atenție:** `specs/directiva-story-intelligence.md` e deja adoptată și acoperă
  exact acest teritoriu — asta nu e o idee nouă, e implementarea feliei „contradicții + timeline” din ea.
- **Interzis prin directivă:** scoruri de bias, scoruri de factualitate, procente de tip „87% sigur”.

### 15. „Cum titrează fiecare sursă” — transparență totală
- **Ce e.** Pe o sinteză multi-sursă, un `<details>` cu titlurile originale, exact cum au fost publicate.
- **De ce contează.** Cititorul vede într-o secundă cum același fapt devine „Incendiu puternic” la o sursă
  și „Momentul în care flăcările cuprind clădirea” la alta. E lecția de media literacy pe care nimeni
  nu o predă și pe care IZZ o poate arăta cu datele pe care le are deja.
- **De ce e gratuit.** Titlurile originale sunt deja stocate (`a.title` vs `a.display_title`; `sources`).
  Un `<details>`, zero fișiere.
- **Efort.** S (2-3 h).
- **Risc de gestionat.** Expune cât de mult reformulăm. Eu zic că e un avantaj (site-ul deja declară asta),
  dar e o decizie de proprietar.

### 16. Controlul asupra textului: mărime, spațiere, contrast, print
- **Ce e.** Trei butoane care setează un atribut pe `<html>` (A− / A+ / spațiere), un CSS de print,
  și un mod contrast mărit.
- **De ce contează.** Cititorii de știri locale au o medie de vârstă mai mare decât a publicului tech.
  Site-ul are deja `content/legal/accessibility.md` și pa11y în CI — adică își asumă accesibilitatea,
  dar nu-i dă cititorului nicio pârghie.
- **De ce e gratuit.** CSS + ~40 de linii JS în `static/personalize.js` (care gestionează deja localStorage).
- **Efort.** S (3-4 h). Cea mai bună raport valoare/efort din toată lista.

### 17. „De la ultima ta vizită”
- **Ce e.** Un marcaj pe prima pagină: „ai mai fost acum 3 ore · 47 de știri noi” + punct pe cardurile nevăzute.
- **De ce contează.** Transformă o vizită întâmplătoare în obicei, fără notificări, fără e-mail, fără cont.
- **De ce e gratuit.** `personalize.js` stochează deja `reads`, `interactions` și profilul.
- **Efort.** S (3-4 h). Se completează cu PWA + web push (deja în lucru) — nu le înlocuiește.

### 18. „Ce e IZZ și ce nu e” — pentru primul vizitator
- **Ce e.** Un chenar pe prima pagină (dispare după prima vizită): trei rânduri despre ce face site-ul
  (rezumate fără clickbait, surse afișate, generat automat) și ce **nu** face (nu are presă proprie,
  nu are editor uman pe fiecare articol, nu are publicitate).
- **De ce contează.** Un vizitator nou care nu înțelege în 10 secunde de ce titlurile „sună ciudat”
  (sunt reformulate) pleacă și nu se întoarce. Conținutul există deja în `content/pages/despre.md`
  și `/legal/method/` — nu-l citește nimeni pentru că nu e pe drumul lui.
- **De ce e gratuit.** HTML + localStorage.
- **Efort.** S (2 h).

### 19. Un index de date publice gratuite, folosit editorial
- **Ce e.** Nu un produs nou, ci o regulă: când o știre atinge o firmă, un dosar sau o instituție,
  pagina primește un link „verifică la sursă” către datele oficiale. Sursele verificate ca gratuite
  și fără cheie: **portal.just.ro** (`portalquery.just.ro/query.asmx`, metadate dosare publice),
  **ANAF** (`webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva` și `webservicesp.anaf.ro/bilant`),
  **ONRC** și **situațiile financiare** pe data.gov.ro, **cursul BNR** (`curs.bnr.ro/nbrfxrates.xml`).
  Există și un index de ~350 MB cu 4,2 milioane de firme, publicat pe GitHub Releases de un proiect
  open-source (`sergiudanstan/anaf-mcp`) — dar ăsta e un pachet terț, de evaluat separat.
- **De ce contează.** „Uite cum verifici singur” e cea mai puternică formă de respect pentru cititor
  și costă zero.
- **De ce e gratuit.** Toate cele patru sunt publice, fără cont și fără cheie (verificat în documentația
  proiectului open-source care le folosește). Atenție la capcană: resellerii (demoanaf.ro, api-date.ro,
  plusfirme.ro) și-au retras nivelul gratuit — nu pe ei îi folosim.
- **Efort.** S pentru linkurile statice (2-3 h); L-XL pentru un verificator de firmă propriu (nu recomand acum).

---

## 5. P3 — potențial mare, cost sau risc pe măsură

### 20. Verificator de firmă (CUI → date oficiale)
- **Ce e.** Un instrument care, dat un CUI, arată datele oficiale ANAF/ONRC și trimite mai departe la sursă.
- **De ce contează.** „Cine e firma din știrea asta” e o întrebare pe care presa românească o lasă
  aproape mereu fără răspuns.
- **De ce e gratuit.** Endpointurile ANAF sunt publice și fără cheie. Dar: cotă de cereri necunoscută,
  risc de blocare IP la rulare din Actions (proiectul are deja istoric cu 429-uri — `TASKS-A.md`),
  și o problemă editorială reală de defăimare dacă datele sunt prezentate greșit.
- **Efort.** L-XL (3-5 zile) + decizie editorială. **Recomandare: nu acum.**

### 21. Versiunea maghiară pentru județele cu comunitate maghiară
- **Ce e.** 10-20 de pagini/zi traduse pentru Harghita, Covasna, Mureș, Satu Mare, Bihor, Sălaj, Cluj.
- **De ce contează.** Nicio publicație națională românească nu rezumă știrile în maghiară. Ar fi un
  serviciu public real, nu un gest simbolic.
- **De ce e gratuit.** AI existent — dar concurează cu bugetul saturat.
- **Efort.** M-L, plus marcaj AI Act pentru traducere și o regulă de nume proprii.
- **Risc.** Traducerea automată a unui text deja automat e un strat suplimentar de risc factual.

### 22. Urmărirea banilor publici (achiziții / bugete locale)
- **Ce e.** Un strat „cine a primit banii” peste știrile locale.
- **De ce contează.** Valoare editorială enormă.
- **De ce NU e (încă) gratuit și simplu.** SEAP/e-licitatie cere cont și API autentificat; datele pe
  data.gov.ro există dar sunt incomplet întreținute. **Nu recomand** fără o cercetare dedicată.
- **Efort.** XL.

### 23. Eliberarea cotei de fișiere (nu e o idee pentru cititor, e condiția celorlalte)
- **Ce e.** Audit al `output/`: câte fișiere costă fiecare articol (HTML + png + webp), ce se poate
  servi din R2 Free în loc de Workers Assets, ce se poate tăia (ex. variantele de copertă nefolosite).
- **De ce contează.** Fără cei ~2.900 de fișiere eliberați, ideile 3, 8, 9 și 10 se lovesc de plafon.
- **Efort.** M (o zi de măsurat + decis). Există deja `tools/asset_budget.py`, `tools/count_output.py`,
  `tools/greutate.py` — deci se măsoară, nu se ghicește.

---

## 6. Tabelul de priorități

| # | Idee | Valoare pt. cititor | Cost bani | Efort | Fișiere noi | AI în plus |
|---|---|---|---|---|---|---|
| 1 | Newsletter / briefing `/azi/` | ★★★★★ | 0 | S | 1 | nu |
| 2 | „Localitatea mea” | ★★★★★ | 0 | M | 0 | nu |
| 3 | Zero 404 (redirect la subiect) | ★★★★★ | 0 | M | 0 | nu |
| 5 | Verificare live vs. main (share/eroare/related) | ★★★★ | 0 | S | 0 | nu |
| 8 | `/alerte/` meteo + seisme + aer | ★★★★★ | 0 | M | 1 | nu |
| 9 | Pagina de județ = hub local | ★★★★★ | 0 | M-L | 0 | nu |
| 12 | Legătura știre ↔ ghid | ★★★★ | 0 | S | 0 | nu |
| 16 | Control text + print | ★★★★ | 0 | S | 0 | nu |
| 4 | RSS complet + feeduri pe categorie/județ | ★★★★ | 0 | S | ~60 | nu |
| 10 | Calculatoare promise (TVA, acte, alocații) | ★★★★ | 0 | M | 4 | nu |
| 6 | Jurnal public de corecții | ★★★★ | 0 | S-M | 1 | nu |
| 7 | Structură pe anunțuri oficiale | ★★★★ | 0 | M | 0 | nu (determinist) |
| 17 | „De la ultima ta vizită” | ★★★ | 0 | S | 0 | nu |
| 11 | Curățat ghiduri „Neconfirmat” | ★★★ | 0 | S | 0 | nu |
| 18 | „Ce e IZZ și ce nu e” | ★★★ | 0 | S | 0 | nu |
| 15 | „Cum titrează fiecare sursă” | ★★★★ | 0 | S | 0 | nu |
| 13 | „Ce înseamnă pentru tine” | ★★★★ | 0 | M | 0 | **da** (realocat) |
| 14 | Timeline + contradicții | ★★★★★ | 0 | L | puține | **da** (pe cluster-e mari) |
| 19 | Linkuri „verifică la sursă” (just/ANAF/BNR) | ★★★ | 0 | S | 0 | nu |
| 23 | Eliberarea cotei de fișiere | (condiție) | 0 | M | −N | nu |
| 20 | Verificator firmă | ★★★★ | 0 | L-XL | puține | nu |
| 21 | Versiune maghiară | ★★★★ | 0 | M-L | multe | **da** |
| 22 | Banii publici | ★★★★ | 0 | XL | multe | da |

---

## 7. Ce NU aș face (și de ce)

- **Comentarii pe articole.** Ar cere moderare umană pe un flux generat automat. Costul de încredere
  al unui comentariu nemoderat sub o sinteză AI e mai mare decât beneficiul.
- **Scoruri de bias sau „cât de sigur e”.** Interzise explicit de `specs/directiva-story-intelligence.md` §4.
- **Sute de pagini subțiri pentru SEO.** Interzis de `specs/romania-utila-mvp.md`; ar consuma și cota de fișiere.
- **Feeduri de subiect pentru toate cele 4.307 pagini.** Deja tăiate deliberat (11% din plafon).
- **Orice feature care adaugă un apel AI per articol.** Bugetul e saturat; ar însemna sinteze mai proaste
  ca să facem o funcție nouă.
- **Geolocație fără consimțământ.** Ar contrazice poziția de privacy deja publicată.

---

## 8. Săptămâna 1 recomandată (5 felii, toate gratis)

1. **#5 Diagnostic live vs. main** — 15 minute, poate descoperi că o parte din munca de transparență nu e livrată.
2. **#16 Control text + print** — 3 h, vizibil imediat pe fiecare pagină.
3. **#12 Legătura știre ↔ ghid** — 4 h, crește valoarea fiecărei pagini fără nicio pagină nouă.
4. **#4 RSS complet** — 3 h, cel mai ieftin câștig de loialitate.
5. **#2 „Localitatea mea”** — felia 1 (selector + secțiunea județului meu prima pe home), 6 h.

Abia după: `/alerte/` (#8) și hub-ul de județ (#9), care sunt cele două cu cel mai mare impact,
dar cer întâi #23 (măsurarea cotei de fișiere) ca să nu ne lovim de plafon.

---

## 9. Ce n-am verificat (onest)

- Nu pot accesa izz.ro prin `curl` din acest mediu (politica de rețea a containerului respinge
  CONNECT — exact situația documentată în `specs/resurse-gratuite.md` §1.2). Paginile live le-am citit
  prin intermediar; `build.json` **nu** l-am putut citi, deci întârzierea de deploy din #5 rămâne ipoteză.
- Clona e shallow (un singur commit, `093cb47`), deci nu pot data când au intrat share/accountability în
  `templates/article.html`.
- Plafoanele serviciilor gratuite citate (Brevo, aqicn.org, EEA) sunt din documentația lor publică,
  nu dintr-un cont al proiectului — de re-verificat la implementare.
- Nu am rulat pipeline-ul, testele sau `tools/arhiva.py` în această sesiune: e o analiză de consultanță,
  fără implementare, conform cererii.
