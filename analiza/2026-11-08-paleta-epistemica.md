# IZZ.ro — paleta epistemică: analiză și implementare

**Data:** 8 noiembrie 2026 · **Obiect:** propunerea de „optimizare cromatică" (verde = consens, albastru = traseul sursei, ocru = divergență, indigo = incertitudine) · **Decizie:** `IZZ-0456` · **Stare:** implementat parțial, cu trei schimbări față de propunere

---

## 0. Pe scurt

Propunerea are dreptate în **principiu** și greșește în **trei locuri concrete**:

1. **Trei din patru culori propuse nu trec AA** pe fundalul real al site-ului. Verdictul nu e estetic, e măsurat: `#4E9F6E` = 3,09:1, `#3B82F6` = 3,52:1, `#D97706` = 3,05:1, față de pragul 4,5:1 pentru text mic (etichetele au 11–13px).
2. **Jumătate din paletă exista deja** — și cu valori mai bune. `.trust--ok` (verde, 6,07:1), `.trust--single` (ocru, 5,14:1), `.trust--div` (roșu, 5,69:1) sunt în producție de la rebranding. Problema nu era lipsa culorilor, ci **lipsa acoperirii**: marca exista pe card și pe rândul de stare, dar nu pe afirmațiile din text.
3. **Albastrul propus pentru „traseul sursei" se bate cu `--navy`**, care e deja culoarea de acțiune a site-ului (linkuri, focus, butoane, 11,16:1). Două albastruri cu înțelesuri diferite în aceeași pagină = exact zgomotul cognitiv pe care propunerea voia să-l evite.

**Regula de aur din propunere este singura parte care trebuie păstrată cuvânt cu cuvânt** — și a fost transformată în test automat, nu în convenție.

---

## 1. Ce s-a măsurat înainte de a atinge CSS-ul

Contrast WCAG calculat pe valorile hex față de `--paper` = `#fbfaf7` (tema deschisă) și `#0f1115` (tema întunecată).

| Propus | Rol cerut | `--paper` | `--paper` dark | Verdict |
|---|---|---:|---:|---|
| verde `#2E6F40` | consens | 5,81:1 | 3,12:1 | trece pe lumină, **pică pe întuneric** |
| verde `#4E9F6E` | consens | **3,09:1** | 5,86:1 | pică pe lumină |
| albastru `#3B82F6` | traseu sursă | **3,52:1** | 5,14:1 | pică + conflict cu `--navy` |
| cyan `#60A5FA` | traseu sursă | **2,44:1** | 7,43:1 | cel mai slab din listă |
| ocru `#D97706` | divergență | **3,05:1** | 5,93:1 | pică pe lumină |
| indigo `#6366F1` | incertitudine | **4,28:1** | 4,23:1 | pică pragul la text mic |
| **`--ok` existent** | confirmare | **6,07:1** | 2,98:1 | deja în producție |
| **`--warn` existent** | o singură origine | **5,14:1** | 3,52:1 | deja în producție |
| **`--live` existent** | divergență | **5,69:1** | 3,18:1 | deja în producție, folosit doar ca punct |

Observație de metodă: valorile propuse sunt luate din paletare web standard, unde sunt gândite pentru **fundal alb** și pentru suprafețe mari (butoane, badge-uri pline). IZZ.ro scrie etichetele epistemice ca **text mic, pe hârtie caldă** — exact combinația în care aceste nuanțe nu mai trec.

---

## 2. Ce s-a implementat

### 2.1 Un token nou, nu patru

| Token | Valoare | Contrast | Rol |
|---|---|---:|---|
| `--infer` | `#5b54a8` (lumină) / `#b3abe4` (întuneric) | 6,14:1 / 8,87:1 | formulare cu rezervă la sursă; ce a dedus sistemul |

De ce doar unul: verdele, ocrul și roșul existau deja **și erau deja semantice**. Înlocuirea lor cu variante mai deschise ar fi fost o regresie de contrast deghizată în îmbunătățire. Golul real era un altul: afirmația marcată „*cu rezervă la sursă*" era un `<em>` fără nicio culoare — adică **invizibilă ca stare**, vizibilă doar ca accent tipografic. Acolo nu exista nici token, nici marcaj.

### 2.2 Marca pe fiecare afirmație, nu doar pe card

Sinteza dialectică are acum, pe fiecare fapt cu rezervă, un punct indigo înaintea textului. Forma e **pătrat rotit**, la fel ca `.trust--single` — amândouă înseamnă „dincolo de faptul confirmat"; culoarea și conturul le despart. Un cerc plin ar fi reclamat o certitudine pe care deducerea nu o are.

Pe build-ul real (`--render-only`, 6.659 articole): **183 de marcaje**, **41 de pagini** cu bordura de divergență.

### 2.3 Legenda: singurul loc care traduce punctele în cuvinte

`<p class="trust-key">` stă o dată pe articol, **după** conținut, și se emite condiționat — doar cu marcajele chiar prezente în pagină. Un articol cu o singură origine nu primește legendă pentru „confirmat de origini independente", fiindcă ar promite o distincție care nu se vede nicăieri în text.

Acoperire: **346 pagini**. Cifra mică nu e defect de implementare — doar 6,2% din conținut e sinteză multi-sursă (`analiza/2026-11-07-analiza-multidimensionala.md`). Pe restul, orice legendă ar fi decor.

### 2.4 Divergența are în sfârșit culoare în text

`.dialectic-diverg` avea bordura `--line-strong` (gri). Punctul roșu din card spunea „relatări divergente", dar paragraful care chiar conținea divergența nu era marcat. Acum bordura e `--live`.

### 2.5 Regula de aur, ca gardă executabilă

Propoziția din propunere — *culoarea nu însoțește niciodată emoția știrii, ci doar gradul de verificare* — este verificată de `tests/test_culoare_semantica.py`:

- fiecare token semantic trece AA **și** pe tema deschisă, **și** pe cea întunecată;
- cei patru semantici sunt distincți între ei (prag 20/255 per canal — prinde cazul real „două variante de verde pentru două înțelesuri");
- **nu există token de emoție**: `--breaking`, `--urgent`, `--tragedie`, `--criza`, `--alert`, `--alarm`, `--panic` sunt interzise prin test. Un articol despre un deces și unul despre un meci, cu aceeași bază epistemică, trebuie să arate identic;
- legenda acoperă fiecare semnal folosit;
- marca de rezervă poartă clasa semantică (nu rămâne un `<em>` decorativ).

---

## 3. Ce s-a refuzat, și de ce

| Propunere | Verdict | Motiv |
|---|---|---|
| albastru pentru „traseul sursei la hover" | **respins** | 3,52:1 pică AA; plus conflict cu `--navy` (culoarea de acțiune). Traseul sursă→propoziție cere un mecanism care nu există încă în DOM (ancore per propoziție), deci culoarea ar fi marcat o funcție absentă — exact ce §9 din analiza anterioară interzice |
| verde smarald pentru „≥3 surse" | **respins ca valoare** | `--ok` (6,07:1) e deja acolo și e mai bun. În plus, pragul „≥3" ar contrazice regula editorială existentă: „confirmat" înseamnă **≥2 origini independente**, nu ≥3. Un prag cromatic diferit de pragul logic ar fi două definiții pentru același cuvânt |
| ocru `#D97706` pentru divergență | **respins ca valoare** | 3,05:1. `--live` (5,69:1) e deja folosit pentru divergență. Ocru rămâne pe „o singură origine" (`--warn`), care e altă stare |
| indigo pentru incertitudine | **acceptat**, cu nuanță închisă | `#6366F1` = 4,28:1, sub prag. `#5b54a8` = 6,14:1 |
| legendă permanentă în subsolul fiecărei pagini | **acceptat parțial** | doar pe paginile care au ce explica, și doar cu marcajele prezente |

---

## 4. Cost măsurat

| Indicator | Înainte | După | Delta |
|---|---:|---:|---:|
| CSS (raw) | 89.137 B | 91.837 B | +2.700 B |
| CSS (gzip) | 23.486 B | 24.508 B | **+1,0 KB** |
| HTML pe pagină de sinteză | — | — | ~+430 B (o legendă) |
| Teste | 3.251 trec | **3.263 trec** | +12 |
| `ruff` | curat | curat | — |

Din delta de CSS, ~700 B sunt comentariul-regulă din capul fișierului (nu ajunge la cititor după minificare la deploy). Restul: două declarații de token, regula `--infer`, forma punctului, legenda.

---

## 5. Ce rămâne nemăsurat

- **Lighthouse / pa11y**: sandboxul nu are Chromium, `tools/audit.sh` nu poate rula aici. Rulează pe PR, în `.github/workflows/editorial-frontend-audit.yml`, pentru orice atingere de `static/**` sau șabloane. Scorurile A11y înainte/după trebuie citite de acolo, nu deduse din calculul WCAG de mai sus.
- **Contrastul perceput**: cifrele sunt calculate pe valori hex, nu citite din pixeli randați după antialiasing și cu fonturile reale. Sunt limita superioară a încrederii.
- **Efectul asupra cititorului**: nu avem nicio măsurătoare de audiență (decizie deliberată, `content/legal/method.md` §6). Dacă marcații fac informația mai ușor de citit sau doar mai încărcată, **nu știm** — și e o întrebare la care site-ul nu are acum cum să răspundă fără să introducă exact instrumentul pe care l-a refuzat.

---

## 6. Ce ar urma, în ordine

1. **Amprenta epistemică pe card, nu doar pe articol** — astăzi cardul spune „Sinteză din N publicații · M confirmări încrucișate", dar nu are marcajul de rezervă. Un card care arată „ar fi" altfel decât „a fost" ar face diferența vizibilă din prima pagină, nu doar la al doilea clic.
2. **Traseul afirmație→propoziție din sursă**, care ar da sens albastrului: cere ancore per propoziție în DOM (informația există în `dialectic.py`, `evidence_ids`), nu doar o culoare. Culoarea fără mecanism e decor.
3. **Niciun scor numeric de încredere.** Propunerea nu cere asta, dar e următorul pas „firesc" al oricărei palete epistemice — și ar contrazice `/principii/`: „nu măsurăm adevărul prin voturi, culori sau scoruri AI".

---

## 7. Felia a doua: amprenta pe card și cifra agregată (tot 2026-11-08)

Cele două lucruri lăsate „în continuare" la §6 s-au făcut. Ambele au schimbat cifrele în
timpul lucrului, iar asta e partea utilă a raportului.

### 7.1 Amprenta epistemică pe card

Cardul spunea *„Sinteză din N publicații · M confirmări încrucișate · generată automat"* —
adică **câte** confirmări are sinteza, nu dacă o afirmație din ea și-a pierdut rezerva
sursei. Un card care arată „ar fi" exact ca „a fost" trimite cititorul la al doilea clic
ca să afle diferența.

Acum, când sinteza are cel puțin un fapt `hedged`, rândul de meta primește un punct indigo
+ două cuvinte: **„cu rezervă"** (explicația stă în `title` și în legenda de pe articol).
Textul de stare rămâne **neschimbat** — e contract editorial, fixat de
`test_render_dialectic::test_cardul_spune_cate_confirmari_nu_doar_ca_e_multi_sursa`.

| Măsurat pe date reale (`data/articles.json`) | |
|---|---:|
| Articole cu dialectic | 437 |
| Articole cu cel puțin un fapt cu rezervă | **157** |
| Marcaje „cu rezervă" în build-ul randat | 121 |

Diferența 157 → 121 nu e o eroare: marca apare doar pe cardurile **efectiv randate** (fereastra
de actualitate + paginile de categorie), nu pe toate cele 437 din stare.

### 7.2 Cifra agregată: cea care schimbă prioritățile

Planul inițial era să expun numărul de afirmații scoase **per articol**. Măsurătoarea l-a
desființat înainte de a fi scris:

| Măsurat | |
|---|---:|
| Sinteze publicate | 437 |
| Sinteze cu cel puțin un fapt respins | **11** (2,5%) |
| Afirmații scoase, în total | 11 |

O marcă per articol ar fi apărut pe **11 pagini din 6.659**. Adică exact tipul de funcție care
există în cod, trece testele și nu vede niciun cititor — „verde în CI, invizibil pe live".

Deci am pus-o unde se vede: `/sub-prag/` are acum o secțiune pe **tot conținutul publicat**,
nu pe ultima rulare:

> **Verificarea sintezelor, pe tot ce e publicat acum**
> 336 sinteze au trecut fără nicio afirmație scoasă (97,1% din total); restul au publicat
> varianta verificată, cu afirmațiile căzute eliminate — nu cu ele reformulate.
>
> | | |
> |---|---:|
> | Sinteze publicate acum pe site | 346 |
> | Sinteze în care cel puțin o afirmație a fost scoasă la verificare | 10 |
> | Afirmații scoase în total (citare, cifră sau text copiat) | 11 |

Onestitatea care contează aici e **numitorul**. „10 sinteze cu afirmații scoase" sună
alarmant; „10 din 346, adică 97,1% au trecut curat" e informația. O pagină de transparență
care publică doar numărătorul face exact ce reproșează altora: sugerează o rată fără bază
de comparație.

### 7.3 De ce NU s-a făcut al doilea punct din §6

*„Traseul afirmație→propoziție din sursă"* — ar fi dat sens albastrului. Blocat de o
constrângere legală, nu tehnică: `dialectic.py` păstrează propozițiile sursei **doar în
memorie, în timpul generării** (`Block.chunks`), iar în stare rămân doar faptele
reformulate plus **numele** publicațiilor. `method.md` o spune explicit: *„Textul integral al
surselor e citit doar în timpul generării și nu se păstrează nicăieri"*.

Ca să existe o ancoră afirmație→propoziție ar trebui **stocat textul sursă** (sau hash-uri
per propoziție, plus textul ca să fie afișabil). Asta ar reintroduce prin ușa din dos exact
ce scrubul juridic a scos. Alternativa — o ancoră care nu duce nicăieri — ar fi o culoare
care marchează o funcție absentă, adică decor. **Nu se face fără o decizie de stocare
luată explicit**, iar decizia aceea nu e a mea.

Ce rămâne fezabil și util: albastrul (`--navy`) să marcheze **legătura care există deja** —
numele publicației de lângă afirmație, clicabil spre `sources-box`. Aia e un link real, nu
o promisiune.

### 7.4 Stare

| | Înainte de felie | După |
|---|---:|---:|
| Teste | 3.263 trec | **3.267 trec** |
| `ruff` | curat | curat |
| `a11y_static` | 0 încălcări tari | 0 încălcări tari |
| Marcaje pe card | 0 | 121 |
| Cifre noi pe `/sub-prag/` | 0 | 3 + numitor |
