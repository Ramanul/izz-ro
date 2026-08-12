# Politica de securitate a ingestiei — izz.ro

> Scrisă 2026-08-09, după incidentul Rovinari. Se citește înainte de orice modificare la
> `fetch.py`, `guard.py`, `moderation.py`, `util.clean_html` sau la lista de surse.
> Regulile de aici sunt **obligatorii**, nu recomandări.

## 1. Modelul de amenințare — enunțat o dată, aplicat peste tot

izz.ro citește automat feedurile a ~1274 de primării. Un site de primărie e, aproape fără
excepție, WordPress neîntreținut. **Deci în orice moment o parte dintre ele sunt controlate de
un atacator, iar noi nu știm care.** Asta nu e un scenariu ipotetic: pe 8-9 august 2026 s-a
întâmplat, iar sursa compromisă era o instituție publică reală, cu anunțuri autentice
publicate în paralel cu paginile de warez.

Din enunțul ăsta decurge totul:

> **Niciun text venit dintr-un feed nu e de încredere, indiferent cine e sursa.**
> Reputația emitentului (primărie, minister, agenție de presă) nu e o dovadă de securitate —
> e doar o afirmație despre cine *deținea* domeniul înainte de compromitere.

Corolar operațional: orice apărare care are nevoie să știe *care* sursă e rea (liste negre,
suprimare per-sursă) e **reactivă** — funcționează abia după ce cineva a văzut problema.
Apărările pe *conținut* nu au nevoia asta și sunt stratul primar.

## 2. Incidentul de referință (2026-08-09) — ce s-a rupt, în ordine

| # | Ce a cedat | Unde | Reparat |
|---|-----------|------|---------|
| 1 | Sursa a fost compromisă în amonte | `primariarovinari.ro` (WordPress) | în afara controlului nostru |
| 2 | Nicio verificare de conținut la ingestie | `fetch.py` | `guard.py`, 5 straturi |
| 3 | `clean_html` tăia tagurile ÎNAINTE de decodarea entităților, deci `&lt;img onload=…&gt;` redevenea markup DUPĂ curățare | `util.py:76-77` | iterare până la punct fix |
| 4 | Trunchierea număra **cuvinte**; JS comprimat n-are spații, deci un „cuvânt" avea 866 de caractere | `util.truncate_words` | plafon de caractere derivat |
| 5 | CSS fără `overflow-wrap`: un jeton nerupibil umfla cardul și-l suprapunea peste vecin | `static/styles.css` | `overflow-wrap: anywhere` |
| 6 | Nimic nu observa că se publică asta | — | `guard.autotest()` la fiecare build |

Rezultatul lui 1-5 combinate: 8 articole de piraterie publicate pe izz.ro, dintre care unul cu
payload de script vizibil ca text în teaser, și aranjamentul paginii `/local/` rupt.

**Ce NU s-a întâmplat:** payload-ul nu s-a executat în browserele vizitatorilor. Template-urile
Jinja2 au `autoescape` pornit, deci codul a fost afișat ca text. Asta a fost singurul strat care
a ținut din construcție, și e motivul pentru care incidentul a costat reputație, nu vizitatori
infectați. **Nu-l slăbi:** `| safe` pe orice conținut derivat dintr-un feed e interzis.

## 2b. Auditul din 2026-08-11 — ce s-a mai găsit, fără incident

Căutare deliberată de suprafețe pe care conținut din feed ajunge în contexte pe care escaparea
NU le apără. Trei găuri reale, toate închise; două suprafețe verificate și găsite curate.

| Găsit | Severitate | Stare |
|---|---|---|
| `link` din feed → `href`, fără validare de schemă (`javascript:` executabil la click) | **mare** — XSS stocat pe originea izz.ro | închis: `guard.url_ostil`, 4 puncte de cablare |
| `resp.read()` fără plafon — o sursă poate servi gigaocteți | medie — build mort prin memorie | închis: `fetch._read_limitat`, 8 MiB |
| Text din feed intră în promptul către Gemini, fără filtru de instrucțiuni | medie — AI-ul e strat de spălare, vezi §2 | închis parțial: strat 7 în `guard.verdict` |
| JSON-LD (`{{ jsonld \| tojson }}`) | — | **curat**: `tojson` din Jinja2 e HTML-safe, escapează `<`, `>`, `&`, `'` |
| `feed.xml` construit prin concatenare | — | **curat**: fiecare câmp trece prin `xml_escape` |

Măsurători care au susținut deciziile (R3): **7823 de URL-uri** în corpus, 100% `https`, zero
respinse de garda nouă → listă albă fără fals-pozitive. **3369 de articole** trecute prin stratul
de prompt injection → zero potriviri, deci tiparele nu prind știrile despre AI. Plafonul de 8 MiB
= ~40× cel mai mare feed real măsurat (198 139 B, unica.ro; median ~25 kB).

Verificat pe output-ul construit: **3786 de pagini HTML**, zero `href` cu schemă periculoasă.

## 3. Regulile

### R1 — Straturi independente, nu unul singur bun
Fiecare din cele de mai jos trebuie să existe și să funcționeze *singur*. Nu se elimină un strat
pentru că „oricum îl prinde altul": exact combinația asta de raționamente a produs incidentul.

| Strat | Fișier | Prinde | Slăbiciune |
|-------|--------|--------|------------|
| Curățare corectă de HTML | `util.clean_html` | markup, inclusiv dublu-codat | doar formatare |
| Gardă pe conținut | `guard.verdict` | markup rezidual, payload, homoglife, warez, titluri-gunoi, instrucțiuni către model | necunoscutele |
| **Gardă pe URL** | `guard.url_ostil` | `javascript:`/`data:`/`file:` în `href`, evaziune prin caractere de control, `@` de mascare | nu judecă unde duce un http(s) valid |
| **Plafon de răspuns** | `fetch._read_limitat` | epuizare de memorie la build | nu judecă conținutul |
| Escapare la randare | Jinja2 `autoescape` | execuție în browser | **nu apără `href`** — de aceea există stratul de URL |
| CSP | `render._write_headers` | execuția a orice a scăpat | doar browsere moderne |
| Plafon de caractere | `util.truncate_words` | umflarea cardurilor | nu judecă sensul |
| `overflow-wrap` | `styles.css` | ruperea aranjamentului | doar vizual |
| Suprimare per-sursă | `moderation.yaml` | o sursă știută rea | reactivă |
| Autotest | `guard.autotest()` | garda stricată în tăcere | doar ce e în corpus |

### R1b — escaparea NU acoperă atributele de URL
Cea mai ușoară eroare de raționament din tot fișierul, și e din familia celei care a produs
incidentul: „Jinja2 escapează, deci suntem acoperiți". Escaparea transformă `<`, `>`, `"` în
entități — dar `href="javascript:alert(1)"` **nu conține niciun caracter de escapat**. E HTML
perfect valid și se execută la click. `link`-ul din feed ajunge direct în `href`
(`templates/article.html`, `_card.html`), deci e conținut ostil într-un context pe care
escaparea nu-l apără. CSP-ul (`script-src 'self'`) îl blochează în browserele moderne, dar
**asta e al doilea strat, nu primul** — se taie la ingestie, în `guard.url_ostil`.

### R2 — Respinge, nu repara
Un item suspect **se sare**, nu se cosmetizează. E §7 din `CLAUDE.md` („dacă nu poate atinge bara
Zero Zgomot, SARE itemul") aplicată la securitate. Un articol pierdut e gratis. Motivul: orice
încercare de „curățare" a conținutului ostil e o cursă în care atacatorul mută ultimul.

### R3 — Pragurile se măsoară, nu se aleg
Orice constantă din lanțul de securitate vine cu măsurătoarea care a produs-o, scrisă în comentariu.
Precedent: plafonul de caractere. Un 600 fix „părea rezonabil" și ar fi tăiat sintezele legitime
de 90 de cuvinte. Cifra corectă s-a obținut măsurând 6714 câmpuri reale — text legitim maximum
**11,60** caractere/cuvânt, conținut otrăvit **32,4-47,8** — deci pragul e 16, cu margine în
ambele direcții. Vezi `LECTII.md` L2.

### R4 — Orice gardă își poartă propriul comutator de om mort
Modul de eșec al unei garzi nu e să dea alarme false. E să **tacă**: cineva strică un regex,
garda încetează să prindă, iar site-ul republică warez fără ca nimic să scârțâie.
`guard.autotest()` rulează corpusul REAL de atac **și** unul curat la fiecare pornire de pipeline
și aruncă `GardaStricata`, oprind build-ul, la orice abatere în oricare direcție. O gardă care
respinge tot e la fel de moartă ca una care nu respinge nimic. Vezi `LECTII.md` L5.

**Corpusul de atac nu se șterge niciodată.** Când apare un incident nou, titlurile lui se adaugă
verbatim în `_CORPUS_OSTIL`. Fișierul ăla e memoria instituțională a atacurilor primite.

### R5 — Homoglifele se tratează structural, nu prin liste de cuvinte
Atacatorul a scris „To𝚛rent" (U+1D69B, literă matematică) și „Frее" (е chirilic) tocmai ca să
treacă de listele de cuvinte. Deci lista de cuvinte e **ultimul** strat, nu primul, iar detecția
adevărată e pe amestecul de alfabete în același cuvânt (ideea din Unicode TR39, „mixed-script
confusables"). Restrângerea la nivel de CUVÂNT e deliberată: „Владимир Путин" ca jeton separat e
conținut legitim de știre; „Frее" cu doi „e" chirilici într-un cuvânt latin nu e.

### R6 — O sursă compromisă se taie întreagă, nu selectiv
Când un CMS e în mâna atacatorului, **niciun** conținut de la sursa aia nu mai e de încredere,
inclusiv anunțurile care par autentice: atacatorul le poate edita. Pe Rovinari s-au tăiat toate
cele 11 articole, inclusiv cele 3 reale. Se ridică suprimarea DOAR după ce site-ul e curățat și
feedul e reverificat manual.

Excluderea se face în **două** locuri, fiindcă fac lucruri diferite:
- `moderation.yaml` → `suppress_sources`: ascunde ce e **deja** în `articles.json`, la fiecare
  randare, fără să aștepte un fetch nou.
- `local_sources._DEAD_SLUGS`: oprește **re-ingestia**. Obligatoriu, fiindcă sursa scorează
  `rss_ok=yes` în `gold_integrare.csv` și altfel reintră la următoarea rulare.

### R6a — Tăierea întreagă se face și AUTOMAT, nu doar de mână (2026-08-12)
Până azi R6 era o regulă pe care o aplica **un om, după ce vedea problema**. Codul respingea
iteme unul câte unul și lăsa să treacă restul — inclusiv anunțurile reale de la un site aflat
sub controlul atacatorului, care e fix scenariul descris mai sus. `guard.carantina` închide
golul: dacă garda respinge **≥2 iteme de la aceeași sursă în aceeași rulare**, întregul lot al
sursei e aruncat pentru runda aia, iar motivul intră în raportul de surse.

**Pragul e măsurat, nu ales** (corpus 3246 de articole, 70 de surse oficiale):
`≥1` → 2 surse (Rovinari 8/10, Cajvana 1/1) · `≥2` → **1 sursă, doar Rovinari, 0 fals-pozitive.**
S-a ales 2 fiindcă §4 acceptă explicit un fals-pozitiv rar la stratul de warez (o știre
legitimă *despre* piraterie); la pragul 1 acel accident ar escalada de la „pierdem un articol"
la „tăiem o sursă întreagă". La 2 e nevoie de un **tipar**, nu de un accident.

**Carantina e per RULARE, nu persistentă** — nu scrie nimic pe disc și nu blochează sursa la
fetch-ul următor. Blocarea durabilă rămâne manuală (`suppress_sources` + `_DEAD_SLUGS`), fiindcă
e o decizie editorială cu consecință publică, nu una pe care s-o ia un prag. Consecința de
acceptat: o sursă compromisă și necurățată va fi pusă în carantină la fiecare rulare, zgomotos
— ceea ce e comportamentul dorit, nu un defect.

### R7 — Conținutul nu are voie să strice aranjamentul
Orice suprafață care afișează text din feed poartă `overflow-wrap: anywhere` și un plafon de
caractere. Nu e o regulă de securitate în sens strict — ține și pentru URL-uri lungi sau nume
compuse, care nu sunt un atac — dar în incidentul ăsta a fost partea vizibilă a pagubei.

## 4. Fals-pozitive asumate

Garda respinge, prin construcție, articole legitime **despre** piraterie („un film a apărut pe
torrente"). E un compromis acceptat: pierdem sub un articol pe an dintr-o categorie care nu e
centrală pentru izz.ro, în schimbul unui strat care nu poate fi ocolit prin reformulare.

Măsurat pe corpusul de 3380 de articole existente: garda respinge **7**, toate de la sursa
compromisă, **zero fals-pozitive** pe celelalte 3373.

## 5. Ce NU e acoperit — lista deschisă, onest

Astea sunt găuri **cunoscute**, nereparate la data scrierii. Nu le trata ca rezolvate.

1. **Detecție de anomalie pe comportamentul sursei — LIVRATĂ PE O SINGURĂ DIMENSIUNE din trei
   (2026-08-12).** Linia de bază propusă avea trei axe: **limbă** așteptată, **cadență**, **mix
   tematic**. Construită e doar prima, `guard.anomalie` (stratul 8), legată în `fetch.py` pe cele
   trei căi de ingestie și în `moderation.apply`.
   **Ce prinde:** un titlu cu markeri englezești și zero markeri românești, de la o sursă declarată
   `ro` în catalog. Măsurat pe corpusul real (3130 de titluri de la surse `ro`): **3 semnalate,
   toate trei ostile — Cajvana „Hacked by Chinafans" și două de la Rovinari; 0 fals-pozitive.**
   Cele 4 surse declarate `en` (BBC, DW, Guardian, Politico) sunt scutite prin construcție.
   **Ce NU prinde, deci nu declara gaura închisă:** un defacement scris **în română**; cadența
   (8 articole la exact 3 ore — semnalul cel mai tare de la Rovinari, încă nemăsurat de nimic);
   mixul tematic. Un atacator care citește fișierul ăsta trece stratul scriind românește.
   **De ce limba DECLARATĂ, nu una învățată din istoric:** o linie de bază învățată se otrăvește
   (atacatorul publică destul și baza se mută sub el), iar Cajvana avea **un singur** articol la
   noi — chiar atacul — deci n-avea istoric din care să înveți. Catalogul de primării e construit
   de noi din lista UAT-urilor românești, deci „e în română" e ceva ce **știm**, nu ghicim.
   **Axa „cadență" a fost măsurată pe 2026-08-12 și e MOARTĂ pe datele pe care le avem.**
   Nu o relua fără un semnal nou; iată de ce, în ordinea în care au picat ipotezele:
   - **Intervale regulate** (coeficient de variație mic — un script publică la interval
     constant): Rovinari iese pe **locul 17 din 21**, adică *mai neregulat* decât majoritatea
     primăriilor legitime (cv 1,67 față de mediana 1,36). Cauza: warez-ul e intercalat cu
     anunțuri reale, deci fluxul **combinat** nu e regulat. Cele 3 ore există doar în
     submulțimea warez, pe care n-o poți izola fără să știi deja care sunt — circular.
   - **Debit susținut** (maxim de articole într-o fereastră de 24h): Rovinari e 1/70 cu 9,
     dar locurile 2-3 sunt primării legitime cu 8 (Ploiești, Țăndărei). Un prag la 9 prinde
     exact singurul caz cunoscut și nimic altceva — asta nu e o măsurătoare, e o curbă trasă
     prin n=1. La prag 6 → 5 surse, 4 legitime = 80% fals-pozitive.
   - **Confound care omoară ambele:** `config.MAX_PER_SOURCE = 8` plafonează câte iteme luăm
     per fetch, deci debitul observat e al **programului nostru de fetch**, nu al sursei.
   - **Și, decisiv: Cajvana are max24h = 1.** Un defacement de un singur articol e invizibil
     pentru orice măsură de cadență, prin construcție. Exact cazul pentru care s-a construit
     stratul 8.
   **Ce s-a construit în loc, fiindcă datele îl susțin: stratul 9, carantina de sursă (§R6a).**
1b. **Cât din catalog a fost efectiv scanat — 54%, și restul e necunoscut, nu curat.**
   Întrebarea lăsată deschisă pe 2026-08-09 („Rovinari e o primărie dintr-un catalog de sute;
   câte altele sunt în aceeași situație și nu ne-am uitat?") are acum o cifră, pentru prima dată.
   Garda completă (straturile 1-8) a fost rulată peste toate cele **3246** de articole din corpus:
   **doar 2 surse au vreo respingere**, cele două deja știute (Rovinari 8/10, Cajvana 1/1).
   **Dar denumitorul e partea importantă:** corpusul acoperă **70 din 129** de surse oficiale
   (54,3%); **59 n-au produs niciun articol** în fereastra de 7 zile, deci **n-au fost măsurate
   deloc.** „Zero respingeri" pentru ele înseamnă „n-am privit", nu „sunt curate".
   O scanare completă ar cere interogarea a 129 de feeduri — fezabilă, dar e o felie separată, cu
   trafic către site-uri de instituții, deci se face deliberat, nu în treacăt.
2. **SSRF prin redirectare.** `urllib` urmează redirectările; o sursă compromisă ne poate trimite
   către o adresă internă a runnerului, iar răspunsul ar putea ajunge publicat. `urllib` respinge
   deja schemele non-http(s) la redirect, iar runnerii GitHub n-au un endpoint de metadate
   interesant fără antet dedicat — deci exploatabilitatea e mică, dar nenulă. Fix corect: handler
   de redirect propriu, cu verificare de IP privat. Nefăcut, cost mediu.
3. **`| safe` — auditat 2026-08-11, cinci apariții, toate curate.** `fonts_css`, `calculator_html`,
   `newsletter_html` sunt generate de noi; `body_html` vine din `content/legal/*.md`;
   `s.continut_html` din `data/entities/*.yaml`, scris de om. **Invariantul e „textul vine dintr-un
   fișier comis în repo".** Dacă vreodată secțiunile de ghid ajung populate de AI sau de un pas
   automat, invariantul cade și trebuie sanitizare înainte de `| safe` — nu există altă poartă.
   Comentariul stă la `render._md_to_html`.
4. **Corpusul de atac e mic** (13 mostre ostile de text + 8 de URL + 3 de anomalie, 6+4+8 curate)
   și acoperă un singur tip de campanie.
   Un atac de altă natură — dezinformare bine scrisă, în română curată, fără markup — trece prin
   toate cele opt straturi. Garda apără împotriva **conținutului tehnic ostil**, nu împotriva
   minciunii plauzibile; aia e o problemă editorială, nu de securitate, și nu are soluție de cod.
5. **Notificarea părților afectate.** Primăria Rovinari probabil nu știe că e spartă, iar DNSC
   (Directoratul Național de Securitate Cibernetică) e autoritatea la care se raportează astfel de
   compromiteri ale instituțiilor publice. Decizie de proprietar — e o acțiune în afară, în numele
   lui.

## 6. Ce se face la următorul incident

1. **Oprește sângerarea:** `suppress_sources` în `moderation.yaml` (se poate edita direct pe
   GitHub, în browser) + `_DEAD_SLUGS` în `local_sources.py`. Push → Cloudflare rebuildează.
2. **Adaugă titlurile verbatim** în `guard._CORPUS_OSTIL` și rulează `pytest tests/test_guard.py`.
   Dacă trec fără să modifici garda, garda le prindea deja. Dacă pică, ai găsit stratul lipsă.
3. **Verifică live, din altă rețea decât runnerii CI**, că sursa chiar e compromisă acum
   (`curl -sSL https://…/feed/`). `LECTII.md` L3: un semnal corect ca observație poate fi fals
   ca verdict.
4. **Scanează întregul corpus** cu garda nouă, ca să afli câte articole vechi trec pe lângă ea.
5. **Scrie un rând în `specs/registru.tsv`** și actualizează secțiunea 2 de mai sus.
