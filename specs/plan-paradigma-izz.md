# IZZ.ro prin prisma cărților — harta funcțională, revizia site-ului și planul

**Pentru Alexandru · 21 octombrie 2026 · elaborat cu Gemini Argon (nivel maxim), în runde de consultare**

## 0. Ce citești aici

Cerința ta, citată: „site-ul trebuie să funcționeze prin prisma acelor filosofii, nu să facă prozelitism filosofic — el în sine trebuie să conțină ca funcționalitate acele idei transpuse în viață… modul de funcționare, structura interrelațiilor dintre componente, modul de analiză și sinteză a știrilor."

Metoda: cele trei volume sunt **citite integral** (Contactul Ra I: sesiunile 1–56; Contactul Ra II: sesiunile 57–106 + epilog; AlienMind: toate capitolele — împreună ~2,84 milioane de caractere), prin 8 cititori pe intervale, fiecare întorcând distilări cu citate-ancoră (sesiune.întrebare sau număr de linie). Distilările integrale sunt în anexa de lucru și pot fi oricând re-verificate contra surselor.

Distincție onestă, pe care cărțile însele o cer: **[FAPT]** = ce spun cărțile / ce există azi pe site, cu ancoră; **[INTERPRETARE]** = traducerea funcțională. Cărțile nu vorbesc despre site-uri; „ alegerea unor reguli pentru IZZ este interpretarea noastră" — exact cum spune deja /principii/.

## 1. Cele 11 principii funcționale (harta)

Fiecare principiu: ideea din cărți (ancoră) → principiul de construire → ce există azi → ce lipsește.

**P1. Liberul arbitru al cititorului e suprem.**
Cărți: „nu avem dreptul/datoria de a împărtăși percepțiile noastre […] fără a primi o întrebare directă" (Ra 2.6); „Nu ne este permis să învățăm/predăm în locul nimănui" (90.29); „nimeni nu trebuie să fie atras și blocat într-o situație inevitabilă" (AlienMind, l.636).
Construire: site-ul răspunde la chemare (canale pull), nu împinge conținut; nu profilează, nu personalizesază, nu stabilește o ordine de lectură „corectă"; filtrele schimbă ce găsești mai ușor, nu adevărul.
Azi [FAPT]: fără cont, fără profilare, RSS complet, căutare liberă, /azi/, push opt-in.
Lipsește: alertele push nu trimit încă (cheia PUSH_ADMIN_TOKEN) — singurul canal „la chemare" incomplet.

**P2. Distorsiunea e condiția oricărei transmisii → verificarea la sursă.**
Cărți: „înțelegerea noastră… începe și se termină în mister" (Ra 28.1); „Subiectivismul celui care a transcris… influențând prezentarea" (39.9); „Testați informațiile noi pentru a le asigura consecvența" (AM 117); verifică „memoria încorporată… mai degrabă decât caracterul reporterului" (AM 767); observatorii distorsiuni care se verifică reciproc „își înmulțesc erorile" (AM 872) — de aceea afirmația confirmate din surse **independente**, nu doar concordante.
Construire: fiecare afirmație are ancoră la sursă; filtrul de grounding; atribuire nominală a afirmațiilor disputate; limita declarată (prezența cifrei în sursă ≠ asociere semantică corectă).
Azi [FAPT]: `citate_inventate` + `cifre_straine` în `generator/verifica_sinteza.py`; atribuire; marcaj „generat automat".
Lipsește: nimic esențial — limita e deja declarată public pe pagina de metodă.

**P3. Atenția e un buget finit și prețios.**
Cărți: „o entitate nu trebuie să primească o cantitate de experiență mai mare… decât poate îndura" (Ra 22.6); „ignoră numărul celor care îți urmăresc lecturile" (48.5); televizorul creează „distracție și somnolență" (34.13); „umple spațiul mental al observării oamenilor cu distrageri și diversiuni" (AM 889).
Construire: titlul spune faptul, nu momeala; nicio tactică de reținere (infinite scroll, streaks, notificări recursive); ritmul aparține cititorului.
Azi [FAPT]: Zero Zgomot în titluri; /azi/ = doar titluri și surse; push maximum una pe zi, opt-in.
Lipsește [INTERPRETARE]: un audit „buget de atenție" — verificarea sistematică că niciun element de interfață nu trage spre mai multă citire decât cere informația.

**P4. Serviciul se face la chemare, nu prin împingere.**
Cărți: „Dacă suntem chemați, noi servim" (Ra 65.15); „abandonați dorința de a servi, când nu există cerere" (67.27); „Serviciul este posibil doar la nivelul la care este cerut" (89.30); „Nu considerăm important ca informația să fie difuzată la scară mare… Dacă încercarea ajută o singură persoană, le ajută pe toate" (17.2).
Construire: nicio metrică de creștere, nicio viralitate, fără reclame; succes = cititorul și-a atins scopul, nu timpul petrecut.
Azi [FAPT]: fără reclame, fără analytics de profilare, fără email marketing.
Lipsește: — (principiu deja încarnat; planul doar îl apără).

**P5. Sursa e umilă și falibilă — eroarea se recunoaște public.**
Cărți: „un umil mesager al Legii lui Unu" (Ra 13.4); sesiunea 17 deschide cu „trebuie să corectăm o eroare… spuneți când ceva pare în neregulă" (17.0); „Tu și Ra ați făcut greșeli" (64.3); „niciun regim nu trebuie să fie pe deplin încrezător, ca și cum ar fi infailibil" (AM 965); regimurile rigide recită obiective „decât să admită că au fost făcute greșeli" (AM 1386).
Construire: corecții publice cu ce/când/de ce; raportarea erorii pe fiecare articol; marcajul generării automate; „nu putem" spus cu motiv (cf. Ra 102.12).
Azi [FAPT]: pagina de corecții + propagarea lor în toate prezentările (PR #497), butonul „Raportează o eroare", limitele declarate pe pagina de metodă.
Lipsește: nimic structural; de păstrat la fiecare funcție nouă.

**P6. Unitatea înseamnă interconexiune, nu uniformizare.**
Cărți: „diferențele individuale sunt accentuate și armonizate automat" (Ra 16.50); „ceea ce este învățat de una din celule este învățat de toate" (81.33); „acorduri transparente între comunități" în loc de „ierarhii stricte… total opresive" (AM 763, 410); infrastructură partajată „pentru a evita redundanța" (AM 550).
Construire: sinteza multi-sursă păstrează contradicțiile (fără consens artificial); dosarele leagă evenimente cu relații explicate; sursele diferite rămân vizibile; harta arată cine vorbește despre un loc.
Azi [FAPT]: contradicții marcate în sinteze; /surse/ cu „cine a publicat prima"; panoul de proveniență pe hartă; dosare editoriale — la scară de pilot.
Lipsește: acoperirea — relațiile explicate și dosarele există pe un lot mic; memoria tematică pe termen lung e limitată de fereastra TTL.

**P7. Strânge tot, analizează, filtrează la esență, sintetizează.**
Cărți: experiența e „analizată și filtrată până când rămâne doar esența" (Ra 10.9); pipeline-ul experienței: „a experimenta toate lucrurile… apoi de a analiza și accepta… sintetizând" (18.5); evaluarea în șase trepte — supraviețuire, identitate personală, relații sociale, iubire universală, comunicare liberă, natură sacră (49.6); „sonda și investiga categorii întregi, mai degrabă decât un caz sau altul" (AM 1121); examinarea repetată din unghiuri diferite „până când… nu există loc de eroare" (AM 1227).
Construire [INTERPRETARE]: structura internă a sintezei ar putea urma explicit un model analitic pe dimensiuni (ce e documentat / cine e afectat / ce relații are / ce nu se știe încă), nu doar o reformulare narativă.
Azi [FAPT]: clusterizare multi-sursă + sinteza B/C cu reguli de titlu/rezumat; contextul editorial pe dimensiuni există în pilot (dosare, adnotări aprobate).
Lipsește: modelul pe dimensiuni nu e aplicat sistematic pe flux; separarea fapt/estimare/interpretare e deocamdată doar în pilotul editorial.

**P8. Discernământul aparține cititorului — site-ul separă, nu judecă.**
Cărți: „Nu este în intenția noastră să judecăm… o foarte atentă citire și o asimilare interioară… Informația va deveni evidentă" (Ra 26.8); „testul efectului" ca discernământ practic (53.17); „putem triumfa printr-o conștientizare informată" (AM 715).
Construire: site-ul etichetează ce e documentat, estimat, interpretat — și lasă verdictul la cititor; nu clasifică oameni sau cititori; nu „corectitudine" morală.
Azi [FAPT]: marcaje editoriale (pilot), trust-label pe carduri, principiul 4 public.
Lipsește: extinderea marcajelor dincolo de pilot.

**P9. Transparența e mecanismul onestității.**
Cărți: „Marele secret este că nu există secrete" (AM 377); „transparența este singura modalitate de a menține universul onest" (1113); Ra cere explicit: „verifica numerele noastre și cereți clarificări pentru cele care vă par suspecte" (57.33).
Construire: metodologie publică verificabilă în clicuri; cod public; sursele la vedere; statistică deschisă.
Azi [FAPT]: pagina „Cum devin ideile funcții", /principii/, repo public, /surse/.
Lipsește: — (cea mai puternic încarnată).

**P10. Totul e finit — atenția, resursele, ecologia.**
Cărți: „nu există cantități nelimitate în univers" (AM 455); presa unui popor = „singura instanță cu relevanță obligatorie… înainte ca planeta lor să fie distrusă" (AM 859); păstrarea rezervei de energie prelungește serviciul (Ra 60.4, 71.22, 99.9).
Construire: fereastră finită de actualitate (TTL) + arhivă oglindă (nu acumulare infinită); buget AI pe rulare; presa locală contează (harta proporțională + proveniența).
Azi [FAPT]: TTL 12 zile, arhivă oglindă, MAX_AI_CALLS 40/zi, harta per 100.000 locuitori, surse locale urmărite.
Lipseste: — (încarnat).

**P11. Anti-prozelitismul e interior filosofiei.**
Cărți: evangheliștii „încearcă să genereze schimbări… fără a respecta Liberul Arbitru. Această încălcare cauzează blocarea… activității" (Ra 73.12); nu câștiga financiar din dezvoltarea conștiinței (AM 789, 1604).
Construire: zero doctrină în interfață; cărțile apar doar în nota de arhitectură a metodei + pe /principii/ cu tensiunile lor declarate; fiecare mecanism rămâne util și celui care respinge cărțile complet.
Azi [FAPT]: exact așa e construită pagina de metodă și /principii/.
Lipsește: nimic — planul are doar obligația de a nu strica asta.

## 2. Revizia site-ului pe cele 3 axe cerute

Legendă: ✅ există azi · 🟡 parțial · ❌ nu există (intră în plan, etapa între paranteze).

### Axa (i) — Modul de funcționare (experiența cititorului, ecologia atenției)

Lentila (Argon R1 + cărți): buget finit de atenție + serviciu la chemare + discernământul cititorului; „interfața trebuie să fie un instrument optic rece, nu un cazinou dopaminic".

- Titluri fără momeală, /azi/ doar titluri și surse ✅
- Listă fină pe zi (fereastra TTL), fără scroll infinit ✅; ❌ linia explicită de final „ai parcurs esența zilei" (E3)
- Adâncime progresivă la cerere (card → articol → sinteză → surse): 🟡 — nivelurile există, dar sinteza nu e încă structurată dialectic (axa iii)
- Zero lexic emoțional în UI; culorile codifică volumul/gradul de divergență, nu urgența ✅
- Comutator de lentilă pe hartă: 🟡 — „Pe locuitor" există; „volum brut vs. confirmări încrucișate" ❌ (E3)
- Contorul de subtracție („azi: X scanate → Y duplicate eliminate → Z subiecte"): ❌ (E3); „numerele zilei" din masthead e o pistă de plecare ✅
- Canale „la chemare": RSS, căutare, /azi/ ✅; push-ul nu trimite încă (cheia PUSH_ADMIN_TOKEN) ❌ (E1)

Corectura Argon integrată aici: **orice selecție și proporționare e și ea o formă de ghidaj** — de aceea lentila trebuie comutabilă de cititor, criteriile declarate public, iar coșul de excluderi deschis la vedere.

### Axa (ii) — Interrelațiile dintre componente (pipeline-ul)

- **fetch** — „neintervenție + ecologie": ✅ robots și timeout respectate, sursele intră egale (catalog, nu scor de reputație); ❌ snapshot de text-sursă + hash + diff pe modificări tăcute (E0–E1); limita structurală: azi se păstrează doar descrierea RSS + meta-description.
- **state** (articles.json = „memoria"): ✅ stare persistentă comisă în repo; corecțiile au istoricul lor; 🟡 fără jurnal append-only per articol; ❌ versiuni de sinteze cu diff public (E4).
- **cluster**: ✅ grupare pe eveniment cu dedup editorial masiv (logat: 1.235 duplicate eliminate într-o rulare); ❌ scor de divergență internă per cluster (E2–E3); ❌ first-publisher după densitatea informației, nu doar după ordinea în flux (E1 — azi e limită declarată public).
- **select**: ✅ determinist, cu metodologie publică; ❌ pagina /sub-prag/ cu ce n-a trecut și de ce, motive strict mecanice (E3) — dedup-ul e logat intern, coșul nu e public.
- **process**: ✅ grounding mecanic (citate inventate, cifre străine, rezervă pierdută, text copiat); ❌ blocurile dialectice common_facts / divergences / omissions cu citări per afirmație (E2); ❌ grounding per propoziție cu ID de chunk (E2); ❌ Protocolul de Tăcere Asumată (E2).
- **covers**: ✅ grafică proprie programatică; titlul de pe copertă e cel reformulat, factual.
- **moderation**: ✅ om în buclă (moderation.yaml), dedup vizibil; ❌ amprenta publică a intervenției pe cluster („cluster ajustat manual: motivul") (E4).
- **render**: ✅ separare card/articol, trust-label, proveniență pe hartă; ❌ separarea vizuală Consens / Fricțiune + tab „Radiografia surselor" (E2); ❌ caseta „acum 4 luni, pe același subiect…" (E4); /subiect/ există ca formă slabă de thread 🟡.
- **corrections**: ✅ publice, propagate în toate prezentările, cu istoric post-expirare; ❌ RSS propriu de corecții (E4); 🟡 istoric textual da, toggle UI „vezi versiunea inițială" nu.

### Axa (iii) — Analiza și sinteza știrilor

Lentila: filtrarea la esență + păstrarea contradicțiilor („unitate fără uniformizare") + separarea faptului de judecată.

- Azi: sinteza B/C reformulează titlul și rezumatul de la zero, păstrează verbele de rezervă („ar fi declarat"), grounding contra descrierii-sursă; contradicțiile marcate în textul sintezelor multi-sursă ✅ — dar în formă narativă.
- Lipsește: structura dialectică explicită (fapte comune / diferențe de raportare / omisiuni, fiecare cu citare) ❌ (E2); interdicția de mediere („pe de o parte… pe de altă parte") — 🟡 implicit prin regulile de ton, ne-mecanizată (E2); extracția omisiunilor ca informație ❌ (E2); Tăcerea Asumată la divergență haotică ❌ (E2); materia primă — text integral ❌ (E0, decizia-cheie).
- Surse epistemice independente ❌ (E3): azi limita e declarată onest pe pagina de metodă („două publicații care preiau același comunicat sunt tratate tehnic drept două confirmări") — planul o transformă din limită declarată în mecanism.

## 3. Planul de implementare — E0–E4 (validat de Argon la gândire maximă, rundele 1–3 — verdict final: **PORNIM**, 21 octombrie 2026)

Principiu de inginerie: fiecare etapă = felii verticale (PR-uri mici), site-ul rămâne în producție. Bugetul AI (40 apeluri/rulare orară) rămâne 100% dedicat sintezei: toate celelalte mecanisme noi sunt deterministe (Python pur, cost zero apeluri).

**E0 — Materia primă (fundal, fără UI)**
- `fetch_deep`: DOAR pentru clusterele selectate (15–30/oră) — extragere text curat (readability/trafilatura), păstrat **strict local, nu în build-ul static** (zero risc de reproducere), hash SHA-256, șters la expirarea TTL.
- Fetch-ul rămâne ușor (RSS + meta-description) pentru tot fluxul — fără ban-uri, fără încetiniri.
- Gardă obligatorie (punctul orb recunoscut de Argon): validator de lungime + fallback instantaneu pe descrierea RSS când textul extras nu conține cuvintele din titlu (altfel paginile de consent/paywall otrăvesc extragerea).
- **Regula de timp (Argon R3)**: timeout de conexiune + citire la `fetch_deep` strict 3,5 s/URL, rulat asincron (asyncio/ThreadPoolExecutor), cu cădere instantanee pe descrierea RSS — rularea orară trebuie să încapă sub 45 de minute în cel mai rău caz, ca să nu se suprapună cu cronul următor.
- **Tăietura Argon**: fără sistem de diff pe descrieri RSS — redacțiile nu rescriu meta-description după publicare; diff-ul are sens doar pe textul integral din `fetch_deep`.

**E1 — Verificabilitatea completă**
- First-publisher după densitatea ancorelor (fereastră glisantă de 15 minute, prag 1,5× numărul de ancore), nu doar după timestamp — o investigație de 2.000 de cuvinte nu pierde în fața unui alert de două rânduri.
- /surse/: „A publicat prima" **cuplată obligatoriu** cu „rata de stabilitate" — câte dintre știrile date primele de o redacție au fost contrazise sau modificate tăcut ulterior. Anti-fetisizare a vitezei („publică acum, verifică mai târziu" e mecanismul toxic, nu meritul).
- Metadată de proprietar/grup media per domeniu din catalog — secă, din acte, fără judecăți de valoare.
- Detecția modificărilor tăcute cu efect real: hash schimbat + distanță de editare pe ancore >20% → cluster marcat `dirty` → regenerare prioritară la rularea următoare (altfel minciuna înghețată rămâne în build-ul static).
- Terminarea push-ului (cheia PUSH_ADMIN_TOKEN) — singurul canal „la chemare" incomplet.

**E2 — Sinteza dialectică (miezul, axa cerută de proprietar)**
- 1 singur apel AI per cluster selectat; intrare: propoziții indexate determinist în Python înainte de apel ([S1.1], [S2.1]…), cu fanioanele de independență pre-calculate.
- Schema JSON validată de Argon: `canonical_title` (≤90 caractere, strict factual) · `epistemic_state` (SYNTHESIS_VALID / ASSUMED_SILENCE) · `confusion_ratio` · `common_facts` (statement + chunk_ids + has_hedging) · `divergences` (axa contradicției + pozițiile fiecărei surse, cu citări) · `uncorroborated_claims` (informație prezentă într-o singură sursă + de unde lipsește) — redenumire onestă a „omissions", care pe texte scurte ar fi acuzat fals o redacție că a omis ce nu avea cum să încapă în lead.
- **[Argon R3]** Flag `is_milestone` (bool) în schema E2 — true doar pentru decizii finale/evenimente consumate; doar acelea intră în `memory_ledger` (cost: zero apeluri AI suplimentare).
- 4 praguri deterministe (în Python, după LLM) pentru **Tăcerea Asumată**: modelul o declară · zero fapte comune valide după grounding · mai multe axe de contradicție decât fapte comune · >34% propoziții respinse de filtrul mecanic. Pragul de 34% stă în variabila de configurare `SILENCE_REJECTION_THRESHOLD`, nu hardcodat — calibrabil după primele rulări reale (Argon R3).
- UI: Consens / Fricțiune separat vizual; metadatele sub tab-ul „Radiografia surselor"; la ASSUMED_SILENCE — zero narativ, doar declarațiile exacte ale fiecărei publicații, cu mesaj neutru („Datele din surse sunt în acest moment ireconciliabile.").
- Promptul de sistem — 6 reguli absolute: interdicția de netezire (100 vs. 10 → se raportează fractura, nu „zeci") · ancorare strictă (nimic dedus din cunoștințele modelului) · conservarea incertitudinii („ar fi" rămâne „ar fi") · puritate lexicală (zero adjective/adverbe de evaluare, verbe neutre de declarație) · anti-plagiat (≤12 cuvinte consecutive) · tăcerea asumată.

**E3 — Ecologia atenției**
- **Sursele epistemice independente — algoritm determinist, 0 apeluri AI** (în etapa cluster): amprenta de ancore per articol (cifre, citate scurte, entități cu pseudo-stemming românesc, trigrame rare) → sortare cronologică penalizată de densitate → graful de noutate (greedy set cover): fiecare articol e ROOT, INDEPENDENT_CONTRIBUTOR (≥2 ancore noi ȘI ≥30% rată de noutate) sau ECHO; atribuirea explicită către altă publicație/agție → DERIVED. Rezultat onest: „20 articole (1 sursă independentă)".
- **Limbajul UI: „Confirmări Încrucișate"**, nu „surse independente" — capcana semnalată de Argon: un site de propagandă care inventează detalii false ar avea rată de noutate uriașă; se numără faptele prezente în ≥2 publicații ne-clonate, nu anomaliile izolate.
- Pagina **/sub-prag/** (nu „excluse" — peretele rușinii ar judeca subiecte, nu starea filtrului): motive strict mecanice și neutre — [1 singură sursă] · [fără fapte noi față de ieri] · [sub pragul de publicații].
- Comutator pe hartă: volum brut ↔ confirmări încrucișate; contorul de subtracție în antet; linia de final „ai parcurs esența zilei".
- Glosar de ~200 entități frecvente (partide, instituții, lideri, reședințe de județ) extrase ca ancore chiar la început de propoziție — remediul punctului orb recunoscut de Argon.

**E4 — Umilința sistemică**
- `memory_ledger`: tabel minuscul separat de TTL (dată, titlu canonic, sinteza-consens pe un rând, embedding cuantificat; <5 MB/an) → fire de memorie pe 12 luni („acum 4 luni, pe același subiect, sursele raportau X") fără încălcarea ferestrei de 12 zile a datelor brute.
- **Garda Memoriei (Argon R3 — singura eroare fatală rămasă, reparată în plan)**: în `memory_ledger` intră DOAR fapte instituționale sau evenimente închise (legi promulgate, bugete aprobate, dezastre naturale, decizii definitive) — niciodată stări judiciare în curs („suspectat", „anchetat", „acuzat") și niciodată fapte cu `has_hedging: true`; orice corecție din /corectii/ sau ștergere de nume face purge/update și în `memory_ledger`, nu doar în clusterele active. Fără regula asta, ledger-ul ar îngheța persoane într-o stare trecută incompletă — „cazier automat fără drept de apel", trădarea directă a dreptului la transformare.
- Versiuni de sinteze: zero UPDATE distructiv — fiecare corecție adaugă o versiune nouă, diff public, toggle „vezi versiunea inițială".
- Amprenta publică a moderării: „cluster ajustat manual: motivul".
- RSS propriu pentru corecții.
- **[Argon R3]** E4 e singura etapă amânabilă fără să cadă miezul: integritatea e asigurată integral de E0–E3, iar sistemul de corecții publice există deja în producție — sistemul poate rula luni de zile doar cu E0–E3.

**Artefacte livrate de Argon în chat** („Arhitectura izz.ro: Filosofie și Practică", gata pentru sesiunea de implementare): schema JSON completă, promptul de sistem, cele 4 praguri, algoritmul de independență pas cu pas, și — la cererea mea finală — codul Python complet (amprenta de ancore + graful de noutate + validatorul de grounding per chunk).

**Ordinea de execuție (permutarea tactică din Argon R3)**: E0 → E1-core (algoritmul de ancore + Confirmările Încrucișate în backend) → E2 (schema JSON + Tăcerea Asumată + UI Consens/Fricțiune) → E1-UI + E3 (/surse/ cu rata de stabilitate, /sub-prag/, comutatorul de lentilă pe hartă) → E4. Motivul: rata de stabilitate și detecția contradicțiilor au nevoie de output-ul structurat din E2 (`divergences`, `dirty`) ca să aibă ce număra — altfel UI-ul din E1 s-ar scrie pe logică provizorie, rescrisă apoi în E2. Fiecare etapă se deschide cu spec de 3–8 rânduri și se livrează în felii verticale pe branch + PR, după disciplina repo-ului.

## 4. Garda anti-doctrinară (permanentă)

1. **Nicio doctrină în interfață**: niciun cuvânt din cosmologia cărților fără ancoră funcțională directă.
2. **Fiecare mecanism trebuie util și cititorului care respinge cărțile complet** (testul proprietarului, pe /principii/).
3. **Citatul din cărți nu e dogmă**: cărțile se autocorectează în text (Ra 17.0, 64.3, 80.0, 85.13) — orice transpunere care tratează citatul ca infailibil contrazice chiar textul citat.
4. **Descrierea unui mecanism ≠ recomandarea lui**: cărțile descriu și manipularea, ierarhia sclavagistă, informația alterată ca să pară credibilă — ca instrumente de diagnostic, nu ca modele.
5. **Cărțile nu verifică știrile**: dovada unei știri vine din documentele și relatările evenimentului (regula existentă pe /principii/, reconfirmată de citirea integrală).

Liniile roșii Argon R1 (interzise expres):

6. **Contrabandă terminologică în UI** — interziși în interfață termenii „Legea Confuziei", „distorsiune", „catalizator", „densitate", „polaritate", „recoltă"; se traduc în limbaj civic-ingineresc: „eroare de transmisie", „bias de selecție", „autonomie", „fapte vs. interpretări", „buget de timp". „Filosofia trebuie să fie invizibilă ca scheletul într-un corp viu: susține totul, dar dacă iese prin piele, e o fractură deschisă."
7. **Ton oracular sau moralizator al AI-ului** — interzis orice aer de superioritate („în timp ce publicațiile se întrec în titluri alarmiste…"). Tonul sintezei: plat, funcționăresc, de grefier care întocmește proces-verbal.
8. **Paternalism „Zero Zgomot"** — interzis să tai pe ascuns (tabloide, sport, subiecte „frivole") fără cale de verificare: filtrezi strict pe criterii structurale declarate și lași coșul public (/excluse/).
9. **Ecosistem închis** — interzis să îngroși linkurile către surse ca să ții cititorul pe izz.ro: sinteza economisește balastul de agenție, dar trimite masiv spre presa originală și prima sursă („ecologia finită", AM 859).

## Anexă

**Dovada citirii complete**: distilările celor 8 intervale de lectură, cu citate-ancoră exacte (sesiune.întrebare pentru Ra, număr de linie pentru AlienMind), stau în `carti/distilari-8-intervale.md`, alături de extrasele integrale ale cărților (`carti/ra_vol1.txt`, `carti/ra_vol2.txt`, `carti/alienmind.txt`). Orice afirmație din acest document poate fi verificată contra lor și contra surselor PDF/DOCX de pe Desktop.

**Consultările cu Argon** (modelul de top al contului, gândire la maxim, setată de proprietar): chatul „Arhitectura izz.ro: Filosofie și Practică" din Gemini — runda 1 (lentilele de revizuire + 4 mecanisme + liniile roșii) și runda 2 (validarea planului + schema JSON + promptul de sistem + algoritmul de independență + cele 3 capcane) sunt persistate acolo integral, cu artefactele de implementare. Runda 3 — verdictul final (21 octombrie 2026, 13:55): o singură eroare fatală rămasă (Capcana Memoriei Eterne — reparata integrată la E4), permutarea tactică E1-UI/E2, flagul `is_milestone`, `SILENCE_REJECTION_THRESHOLD` calibrabil și regula celor 3,5 s la `fetch_deep`; E4 declarată singura etapă amânabilă. Încheierea Argon: „Arhitectura este completă, etanșă, imună la derapaje doctrinare și perfect încadrată în bugetul tehnic. Nu mai este nevoie de nicio rundă de proiectare; orice minut în plus petrecut pe planificare de aici înainte este amânare a execuției." **PORNIM.**

## 5. Jurnal de execuție (23 octombrie 2026)

**Felia 1 — E0-fix + E1-core** (`oc/e1-core-epistemic-roles`). Review peste munca necomisă a
sesiunii Antigravity, cu Argon runda 4 (chat `9d6abed40b448b65`). Abateri de la §3, cu motiv:
- **Rol nou `CLONE`** (al cincilea): conținerea shingle-urilor de 4 cuvinte de conținut ≥0,65 față
  de o sursă anterioară, fără atribuire — „text comun cu alte publicații (posibil comunicat)".
  Nici CLONE, nici DERIVED nu se numără drept confirmare. Motiv: §3 E3 cere numărarea faptelor
  din „publicații ne-clonate"; fără detecția clonei, ECHO-ul unui comunicat preluat de trei
  redacții refăcea exact iluzia „3 publicații = 3 confirmări" pe care pagina metodei o declară limită.
- **`cross_confirmations` = mărimea setului `cross_confirmed`** (domenii), unit peste rulări —
  versiunea preluată număra orice ECHO drept confirmare, anulând garda de ≥2 ancore comune.
- **Glosarul de entități**: rădăcini ≥5 litere pe prefix, acronime/nume scurte doar exact (≤3
  litere doar cu majuscule) — prefixele scurte făceau din „Potrivit"/„Mai mult" ancore universale.
- **Ancorele de citat se stochează ca hash** (deep_meta.json e comis într-un repo public).
- **Eșantion bottom-k pe hash** pentru cele 80 de ancore stocate: driftul compara un set trunchiat
  alfabetic (stocat) cu unul întreg (proaspăt) → orice articol lung ieșea „modificat tăcut".
- **build.yml comite `data/deep_meta.json`**, altfel driftul pornea gol pe fiecare runner.
- Măsurat pe 14 sinteze reale (29 de articole, rețea reală, 3,8 s): 29/29 text integral; roluri
  ROOT 14 · INDEPENDENT_CONTRIBUTOR 12 · ECHO 3 · DERIVED 3 · CLONE 1.

**Felia 2 — E2, decizii luate înainte de cod** (Argon R4, revizuind B.3–B.7):
- Rămâne lotul de 3 clustere/apel (bugetul de 40 nu suportă 1 apel/cluster — măsurat aug.).
  ID-urile de propoziție poartă indicele clusterului (`C1S2.3`), ca o citare din alt cluster al
  lotului să fie respinsă mecanic, nu „crezută".
- Plafon de context per cluster pe propoziții întregi, distribuit round-robin între surse (o sursă
  lungă nu le lasă pe celelalte fără nicio propoziție în prompt).
- Afirmațiile modelului NU conțin citate directe (parafrază atribuită; L69/2022); Python verifică
  cifrele (normalizate) și existența chunk-urilor citate.
- Rata de respingere numără DOAR chunk inexistent/străin și cifră absentă din chunk-urile citate.
  Faptul „comun" citat dintr-o singură sursă e retrogradat (nu respins); faptul fără rezervă
  citat din chunk-uri cu rezervă e marcat `has_hedging` (nu respins, nu rescris gramatical).
- **Tăcerea Asumată** (abatere de la cele 4 praguri din §3): modelul o declară · zero fapte comune
  valide DUPĂ grounding · respinse/total > `SILENCE_REJECTION_THRESHOLD` (0,34). Criteriul
  „mai multe divergențe decât fapte comune" e scos: o știre cu un fapt cert și două detalii
  divergente (ora, numărul) ar fi ascuns miezul cert — eșec de utilitate, nu prudență.
- `synthesis` (card, RSS, meta) devine DERIVAT DETERMINIST din faptele comune valide, ordonate de
  model după importanță; faptele cu rezervă nu intră în el. La Tăcere: text neutru prefixat de
  subiect, pe pagină doar pozițiile atribuite (parafraze), niciodată propoziții-sursă.
- JSON dialectic invalid pentru un cluster → clusterul se amână (ca la eșecul AI de azi); celelalte
  din lot se publică. Nu există cădere pe sinteza narativă veche.

**Felia 2 — E2, ce a schimbat măsurătoarea** (probe reale pe PC: text integral real + Gemini
Flash Lite real, 3 runde pe 9 + 12 + 15 clustere, 23.10.2026):
- **Etichete de propoziție unice în lot** (`S{n}.{k}`, numerotarea surselor continuă între
  evenimente), nu prefixe de cluster compuse de model: cu `C{i}S{j}.{k}`, 10 din 33 de citări ale
  unui lot ieșeau greșite. Modelul copiază etichete pe care le vede; apartenența la eveniment o
  decide dicționarul blocului.
- **Peste pragul de respingere → amânare, nu Tăcere Asumată.** Prima rundă a declarat
  „ireconciliabil" un meci relatat identic de toate sursele, din cauza citărilor greșite ale
  modelului. Tăcerea e o afirmație despre presă: se publică doar când există poziții divergente
  validate și niciun fapt comun. Starea o decide conținutul validat, nu declarația modelului.
- **A treia stare, `SINGLE_ORIGIN`**: zero fapte comune fără divergențe = o singură origine
  (ROOT + clonele/preluările lui), nu Tăcere. E rezultatul onest „N articole, 1 origine".
- **Copierea scoate faptul, dar nu numără la prag** (e formă, nu temei — Argon R4).
- **Loturi fără clustere vecine** (≥2 entități comune în titluri): sub-unirea la clustering
  punea trei clustere despre același meci în același lot, iar modelul cita firesc între ele.
- **Parsare tolerantă per obiect**: o liniuță rătăcită înaintea unei chei a pierdut un lot întreg.
- Rezultat pe ultimele două runde (27 de clustere): 23 publicate (85%), 4 amânate (reluate la
  rularea următoare); 0 citări străine acceptate; afirmații scoase: 5 copiate, 2 citări greșite.

**Felia 3 — E3 livrat**: etichetele cardului („Sinteză din N publicații · K confirmări
încrucișate" / „o singură origine" / „Relatări divergente"); rolul fiecărei surse în
`sources-box`; contorul de subtracție în antet („X relatări → Y subiecte"); linia de final pe
/azi/; registrul public /sub-prag/ (contoare per filtru, fără titluri și fără nume de
publicații — Argon R4: o listă de linkuri oarbe ar fi fost momeală, iar un motiv lângă un brand,
o judecată publică). Amânat: comutatorul de lentilă pe hartă (volum ↔ confirmări) și „rata de
stabilitate" pe /surse/ — au nevoie de câteva zile de date `cross_confirmed`/`deep_meta` acumulate.

**Conținut**: /principii/ și /legal/method/ descriu mecanismele, nu doctrina (decizia
proprietarului, 23.10: „să nu amintim în diverse locuri de acele idei"; Argon R4: și nota de
proveniență cu titlurile cărților iese). Rezumatele cosmologice au fost scoase; rămâne trimiterea
la depozitul public de cod, unde stă acest document. Garda e mecanică:
`tests/test_garda_anti_doctrina.py` scanează tot textul public scris de mână.

**Argon R5 (23.10.2026, seara; chat `54dc9bd7a5b6d75f`) — aplicat înainte de merge:**
- `SINGLE_ORIGIN` se desparte după numărul ORIGINILOR din afirmații (`dialectic.origini`): una
  singură → „o singură origine" (prima relatare + clonele/preluările ei); două sau mai multe →
  „fapte neconfirmate reciproc" (redacții independente, fapte diferite). Textul vechi ar fi
  afirmat fals „aceeași origine" despre redacții independente.
- Memoria subiectelor: vocabularul exclus cuprinde și faza pre-penală, contravențiile și
  integritatea (audiat, percheziție, plângere, amendă, conflict de interese, incompatibilitate,
  plagiat, corupție); deciziile CCR rămân. Legătura cere ≥2 entități NE-generice („Guvernul",
  „România", partidele, județele nu se numără) + un cuvânt-cheie comun (rădăcină de 6 litere).
  Data intrării = `updated` (ziua deciziei), nu prima publicare a sintezei.
- Nota de actualizare NU mai listează „fapte care nu mai apar" (o reformulare a modelului ar fi
  apărut drept retragere); spune doar ce publicații au intrat și starea anterioară — ambele
  deterministe. Eticheta driftului: „actualizat de redacție după prima citire"; coloana de pe
  /surse/: „Actualizate ulterior", cu explicația că include actualizările firești ale știrilor
  în curs. Contorul din antet: „X articole → Y subiecte".
- Respins din R5: incrementarea unui număr de versiune (nu există; `v` e versiunea schemei).
