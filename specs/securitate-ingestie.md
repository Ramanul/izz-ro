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

## 3. Regulile

### R1 — Straturi independente, nu unul singur bun
Fiecare din cele de mai jos trebuie să existe și să funcționeze *singur*. Nu se elimină un strat
pentru că „oricum îl prinde altul": exact combinația asta de raționamente a produs incidentul.

| Strat | Fișier | Prinde | Slăbiciune |
|-------|--------|--------|------------|
| Curățare corectă de HTML | `util.clean_html` | markup, inclusiv dublu-codat | doar formatare |
| Gardă pe conținut | `guard.py` | markup rezidual, payload, homoglife, warez, titluri-gunoi | necunoscutele |
| Escapare la randare | Jinja2 `autoescape` | execuție în browser | nu curăță datele |
| Plafon de caractere | `util.truncate_words` | umflarea cardurilor | nu judecă sensul |
| `overflow-wrap` | `styles.css` | ruperea aranjamentului | doar vizual |
| Suprimare per-sursă | `moderation.yaml` | o sursă știută rea | reactivă |
| Autotest | `guard.autotest()` | garda stricată în tăcere | doar ce e în corpus |

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

1. **Detecție de anomalie pe comportamentul sursei.** O primărie care publică brusc 8 articole în
   engleză despre software, la interval de exact 3 ore, e anormală indiferent ce cuvinte
   folosește. O linie de bază per sursă (limbă așteptată, cadență, mix tematic) care pune sursa
   în carantină automat la deviație ar fi prins atacul ăsta **din primul articol**, nu din al
   optulea. **Ăsta e următorul lucru de construit, și e cel mai valoros.**
2. **Antet CSP** (`Content-Security-Policy`) pe Cloudflare Pages, prin fișier `_headers`. Ar face
   ca un eventual eșec al escapării să nu poată executa nimic. Apărare în adâncime pură — nu
   repară nimic din ce s-a rupt, dar acoperă modul de eșec pe care nu-l vedem.
3. **Audit de `| safe` în template-uri.** Nu a fost făcut. O singură apariție pe conținut derivat
   din feed anulează stratul de escapare.
4. **Corpusul de atac e mic** (10 mostre ostile, 6 curate) și acoperă un singur tip de campanie.
   Un atac de altă natură — dezinformare bine scrisă, în română curată, fără markup — trece prin
   toate cele cinci straturi. Garda apără împotriva **conținutului tehnic ostil**, nu împotriva
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
