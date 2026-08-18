# Raport de progres și plan de definitivare totală

**Proiecte:** Agentic OS și IZZ.ro  
**Data raportului:** 19 august 2026  
**Branch activ pentru IZZ.ro:** `feat/multi-provider-router`  
**Repository:** [Ramanul/izz-ro](https://github.com/Ramanul/izz-ro)

## 1. Rezumat executiv

În acest moment, partea tehnică principală a celor două proiecte este implementată și validată. **Stage 2 pentru Agentic OS este finalizat**, iar integrarea multi-provider pentru IZZ.ro, inclusiv protecția împotriva blocării la surse RSS lente, este pe branchul separat și are verificările automate GitHub verzi.

> Starea corectă nu este încă „proiectul este publicat definitiv”, ci „codul este implementat, testat și pregătit pentru activare prin merge și deploy”.

| Domeniu | Stare actuală | Dovadă | Ce mai trebuie făcut pentru finalizare totală |
|---|---|---|---|
| Agentic OS – Stage 2 | **Finalizat** | 74 teste trecute; streaming și sesiune OpenCode implementate | Doar verificare operațională finală pe calculatorul Windows, dacă se dorește o nouă confirmare |
| IZZ.ro – arhitectură workflow | **Finalizat** | Schema multi-provider și cascadele sunt definite în cod și configurație | Confirmarea parametrilor de producție și a limitelor de cost |
| IZZ.ro – router multi-provider | **Implementat pe branch** | Branch `feat/multi-provider-router`; teste țintite 65/65 | Testare în mod `multi` cu cheile reale disponibile și verificarea calității |
| IZZ.ro – protecție RSS | **Finalizat și împins** | Commit `5c1d67e`; test de timeout nou; 65 teste trecute | Observarea unei rulări reale în mediul Windows și ajustarea plafonului dacă datele reale o cer |
| GitHub Actions | **Verde pentru commitul final** | CI final: `success`; pytest complet și poarta HTML trecute | Merge în `main`, apoi deployul conform infrastructurii existente |
| Producție | **Neactivată încă** | Nu s-a făcut merge/deploy | Merge, rulare controlată după merge și monitorizare post-deploy |

## 2. Agentic OS – etapele executate

| Nr. | Etapă | Implementare | Validare | Observații |
|---:|---|---|---|---|
| 1 | Integrare persistentă OpenCode | Sesiunea OpenCode este păstrată între interacțiuni, cu fallback CLI când sesiunea nu este disponibilă | Funcționalitatea a fost testată în interfața locală | Sesiunea persistentă și fallback-ul sunt mecanisme diferite; fallback-ul nu trebuie confundat cu păstrarea contextului |
| 2 | Streaming pentru chat | Răspunsurile sunt livrate prin endpoint SSE, în loc să aștepte întregul răspuns înainte de afișare | Răspunsurile au fost observate în interfața locală | Latența percepută scade, dar timpul total depinde în continuare de provider și de rețea |
| 3 | Corecția tipului de mesaj OpenCode | Au fost corectate două apariții ale tipului de mesaj care provocau comportament incorect | Serverul a pornit, iar conversațiile au primit răspuns | Fără această corecție, răspunsurile puteau fi întârziate sau afișate greșit |
| 4 | Corecții Windows UTF-8/CRLF | Scripturile PowerShell au fost reparate pentru codare și terminatori de linie | Instalarea și compilarea au fost validate pe Windows | Erorile istorice cu caractere românești și stringuri PowerShell nu mai sunt blocante în varianta corectată |
| 5 | Scheduler și health checks | Schedulerul și endpointurile de stare/health sunt disponibile | Au fost obținute răspunsuri HTTP 200 și `{"healthy":true}` | Portul 8080 trebuie să fie liber înainte de pornire; eroarea `10048` a fost o coliziune de port, nu o eroare a codului |
| 6 | Testarea Stage 2 | Suita completă pentru etapa respectivă a fost executată | **74 teste trecute** | Stage 2 poate fi considerat închis tehnic |

### Observație importantă pentru Agentic OS

Problemele întâlnite în sesiunea Windows — latență de aproximativ 10–25 de secunde, selectarea repetată a OpenCode, un port deja ocupat și răspunsuri repetate — au fost probleme operaționale sau de integrare, nu dovada că Stage 2 este neimplementat. Pentru o definitivare completă mai rămâne doar o verificare practică: pornirea unei singure instanțe a serverului, verificarea porturilor 8080 și 4096, apoi un mesaj streaming cu un răspuns unic și corect.

## 3. IZZ.ro – analiza și proiectarea workflow-ului

| Nr. | Etapă | Rezultat | Stare |
|---:|---|---|---|
| 1 | Analiza pipeline-ului existent | Au fost identificate ingestia RSS, guardurile deterministe, procesarea AI, cache-ul, moderation și generarea rezultatului | **Finalizat** |
| 2 | Definirea routerului logic | A fost stabilită o cascadă în care providerii sunt selectați după mod, disponibilitate, cost și fallback | **Finalizat** |
| 3 | Păstrarea pipeline-ului deterministic | Guardurile de conținut, ingestie, carantină, normalizare, deduplicare și validare rămân înainte și după AI | **Finalizat** |
| 4 | Protecția împotriva răspunsurilor vechi | Cache-ul și rezultatele procesate nu sunt tratate ca răspunsuri noi fără verificări; articolele eșuate sunt amânate, nu publicate brut | **Implementat** |
| 5 | Protecția secretelor | Cheile rămân în `.env`/secretele CI și nu sunt introduse în cod sau commituri | **Respectat** |

### Schema providerilor

| Nivel | Provider / categorie | Rol | Activare |
|---:|---|---|---|
| 1 | Gemini sau Anthropic, conform configurației existente | Provider principal pentru calitate și compatibilitate cu fluxul actual | Modul `legacy` păstrează comportamentul existent |
| 2 | Cerebras, Groq, Mistral, OpenRouter, Perplexity, Upstage | Provideri OpenAI-compatible pentru cost, viteză și disponibilitate alternativă | Modul `multi` și lista `AI_FALLBACK_PROVIDERS` |
| 3 | Ollama | Fallback local, fără cost API, când este disponibil | `AI_FALLBACK_OLLAMA` |
| 4 | Fallback determinist | Nu inventează conținut AI; păstrează sau amână articolul conform regulilor existente | Activ când providerul nu este disponibil sau eșuează |

> Principiul important: routerul poate schimba providerul, dar nu poate elimina guardurile deterministe și nu poate publica un răspuns AI invalid doar pentru a umple pagina.

## 4. Implementarea concretă integrată în repository

| Fișier / zonă | Modificare | Scop | Stare |
|---|---|---|---|
| `generator/config.py` | Configurație pentru modurile routerului și providerii disponibili | Separă modul `legacy` de modul `multi` | Implementat |
| `generator/process.py` | Selecție și integrare a providerului, cascade și procesare controlată | Păstrează fluxul actual și adaugă rutarea | Implementat |
| `generator/providers/openai_compat.py` | Adaptor generic pentru endpointuri OpenAI-compatible | Permite integrarea Groq, Cerebras, Mistral și alte endpointuri compatibile | Implementat |
| `generator/providers/cascade.py` | Încercare ordonată a providerilor disponibili | Fallback controlat la eroare, fără amestecare arbitrară | Implementat |
| `generator/fetch.py` | Timeout global pentru fereastra paralelă RSS și anulare controlată | O sursă blocată nu mai ține întregul fetch captiv | Implementat în commitul `5c1d67e` |
| `generator/local_sources.py` | Quarantine pentru `pl_tulcea_luncavita` | Elimină o sursă care furniza URL-uri invalide și respingea toate itemele | Implementat |
| `tests/test_provider_router.py` | Teste pentru selecție, disponibilitate și cascade | Previne regresii în router | Trecut |
| `tests/test_luncavita_quarantine.py` | Test pentru carantina sursei compromise | Confirmă că sursa nu reintră accidental | Trecut |
| `tests/test_fetch_parallel.py` | Ordine, cache, paralelism, erori și modul secvențial | Confirmă că paralelizarea nu schimbă rezultatul logic | Trecut |
| `tests/test_fetch_batch_timeout.py` | Test nou pentru sursă blocată | Confirmă că fetch-ul se încheie controlat și marchează sursa | Trecut |

## 5. Problema RSS și remedierea aplicată

Problema care a blocat rularea reală era că `ThreadPoolExecutor` era folosit prin context manager și `pool.map`. Când o sursă RSS rămânea blocată, rezultatul putea aștepta toate threadurile; la întreruperea manuală, închiderea executorului putea aștepta din nou threadurile de rețea.

Remedierea introduce un plafon configurabil prin `FETCH_BATCH_TIMEOUT_S`, cu valoare implicită de 90 de secunde. Rezultatele finalizate sunt păstrate în ordinea surselor din configurație, iar taskurile nefinalizate sunt transformate în erori de sursă pentru rularea curentă. Executorul este închis fără a aștepta inutil threadurile rămase.

| Proprietate | Înainte | După remediere |
|---|---|---|
| Așteptare la `pool.map` | Putea aștepta până la terminarea tuturor taskurilor | Are plafon de batch |
| Ordinea articolelor | Depindea de map, dar putea pierde toate rezultatele la întrerupere | Este reconstruită explicit în ordinea configurației |
| Sursă blocată | Putea bloca rularea | Este marcată cu `fetch batch timeout` |
| Cache | Putea să nu fie salvat dacă apărea o excepție la iterarea rezultatelor | Rezultatele disponibile sunt procesate și cache-ul este salvat |
| Configurabilitate | Doar timeout per request | Timeout per request plus timeout per batch |

## 6. Validări executate până acum

| Validare | Rezultat | Interpretare |
|---|---:|---|
| Teste IZZ.ro inițiale pentru router și workflow | 55 passed | Integrarea multi-provider de bază nu a introdus regresii |
| Teste după quarantine Luncavița | 57 passed | Sursa compromisă este izolată corect |
| Teste după timeout RSS și testul nou | **65 passed** | Routerul, guardurile, workflow gates, quarantine și fetch timeout sunt compatibile |
| Ruff local pe repository | Passed | Nu există erori de lint în snapshotul validat |
| CI GitHub pe commitul final | **Success** | Lint, pytest complet și poarta HTML au trecut |
| Poarta HTML | **Passed** | Generarea și verificarea HTML nu au identificat regresii |
| Rulare reală legacy în sandbox | A depășit limita controlată de 150 s | Nu este dovadă de defect al patchului RSS; pipeline-ul real include și procesări/moderare/AI lente |
| Dry-run local | A fost întrerupt la o etapă de deduplicare/moderare lentă | Necesită măsurare separată dacă viteza totală devine obiectiv prioritar |

## 7. Ce este complet, ce este în așteptare și ce mai trebuie făcut

| Prioritate | Activitate | Stare | Cine poate executa | Condiția de închidere |
|---:|---|---|---|---|
| A | Merge `feat/multi-provider-router` în `main` | **Neefectuat** | Agentul poate executa după aprobarea explicită | Branchul este unit în `main`, fără conflicte |
| A | Deployul versiunii din `main` | **Neefectuat** | Agentul poate executa dacă infrastructura permite | Workflow-ul de deploy se încheie cu succes |
| A | Rulare reală controlată după deploy | **Neefectuată** | Necesită mediul local/CI cu secretele reale | Se obține output nou, fără blocare și fără duplicare stale |
| A | Testarea modului `AI_ROUTER_MODE=multi` | **Pregătită, dar neconfirmată în producție** | Agentul poate rula în CI dacă providerii sunt configurați | Se verifică providerul ales, fallback-ul și calitatea outputului |
| B | Confirmarea cheilor și limitelor providerilor | **Neefectuată integral** | Necesită verificarea secretelor disponibile în mediul de execuție | Fiecare provider activ răspunde în timeoutul configurat |
| B | Calibrarea costului și a vitezei | **Parțială** | Agentul poate analiza logurile după rularea multi | Se stabilește ordinea finală a providerilor și bugetul per run |
| B | Verificarea cache-ului după rulare | **Pregătită** | Agentul poate executa automat | Cache-ul nu conține rezultate din rulări întrerupte sau duplicate |
| B | Verificarea calității sintezelor în română | **De făcut pe corpus real** | Agentul poate rula scripturile existente | Se confirmă că titlurile nu se repetă și că sintezele respectă guardurile |
| C | Monitorizare post-deploy | **Neefectuată** | Agentul poate inspecta workflow-urile și logurile | Cel puțin una-două rulări stabile fără creștere de surse moarte |
| C | Curățarea documentației finale | **Parțială** | Agentul poate actualiza README/notițele | Configurația și modul de operare sunt documentate pentru viitor |
| C | Integrarea fișierelor locale necomise | **Intenționat neefectuată** | Necesită păstrarea lor locală sau atașarea lor de utilizator | Se decide separat dacă intră în repository; nu trebuie adăugate automat |

## 8. Ce trebuie făcut pentru definitivarea totală

Definitivarea completă are șase faze, în această ordine:

| Fază | Acțiune | Detalii și criteriu de succes |
|---:|---|---|
| 1 | Confirmarea snapshotului | Se păstrează backup pentru `data/articles.json` și `data/feed_cache.json`; se confirmă că fișierele locale necomise rămân neatinse |
| 2 | Merge în `main` | Se face numai după aprobarea explicită; se verifică faptul că branchul este verde și sincronizat |
| 3 | Deploy | Se execută workflow-ul existent, fără a schimba infrastructura GitHub Actions inutil |
| 4 | Rulare baseline legacy | Se rulează întâi `AI_ROUTER_MODE=legacy` pentru comparație cu fluxul existent |
| 5 | Rulare multi-provider controlată | Se activează `AI_ROUTER_MODE=multi`, cu providerii ale căror chei sunt disponibile, și se compară latența, erorile, costul și calitatea |
| 6 | Stabilizare și închidere | Se păstrează configurația care oferă cel mai bun raport calitate/cost, se actualizează documentația și se monitorizează rulările următoare |

## 9. Observații și riscuri

**Primul risc este diferența dintre sandbox, Windows local și GitHub Actions.** Testele automate pot fi verzi, în timp ce o rulare locală poate fi lentă din cauza rețelei, a procesării HTML, a cache-ului sau a providerilor AI. De aceea, rularea reală trebuie făcută cu backup și cu un timeout global observabil.

**Al doilea risc este activarea modului `multi` fără chei sau limite verificate.** Routerul ignoră providerii fără cheie disponibilă, dar pentru o comparație reală este necesar să știm care provider este activ, ce model folosește, ce timeout are și dacă fallback-ul nu generează costuri neprevăzute.

**Al treilea risc este calitatea, nu doar disponibilitatea.** Un provider care răspunde repede nu este automat mai bun. Înainte de alegerea finală trebuie comparate titlurile, sintezele, categoria, entitățile, repetițiile și numărul de articole amânate de guarduri.

**Al patrulea risc este publicarea accidentală.** Merge-ul și deployul sunt pași reversibili prin Git, dar pot schimba fluxul live și pot produce conținut nou. De aceea, nu au fost executate automat după ce CI a devenit verde.

**Al cincilea risc este performanța deduplicării/moderării.** Rularea reală din sandbox a depășit plafonul de 150 de secunde și dry-run-ul a fost întrerupt în `_dedup_visible`, la compararea evenimentelor. Acest fapt nu invalidează patchul RSS, dar indică o posibilă optimizare separată dacă obiectivul este ca întregul workflow să se încadreze într-o limită strictă de timp.

## 10. Criteriul final de „proiect definitiv”

Proiectul poate fi declarat definitiv numai când toate condițiile următoare sunt adevărate:

| Criteriu | Condiție finală |
|---|---|
| Cod | Branchul este integrat în `main` și nu există modificări neintenționate |
| Teste | CI complet verde, inclusiv lint, pytest și HTML gate |
| RSS | O rulare reală nu rămâne blocată de o sursă lentă; sursele lente sunt raportate și izolate |
| AI legacy | Baseline-ul produce rezultate valide și nu reintroduce răspunsuri stale |
| AI multi | Cel puțin un provider alternativ funcționează, iar fallback-ul este observabil |
| Calitate | Nu apar duplicate evidente, titluri repetate sau sinteze cu text copiat |
| Cost | Ordinea providerilor și bugetul sunt documentate și acceptate |
| Cache | Cache-ul rezultat este coerent după rulare completă și după întrerupere controlată |
| Deploy | Versiunea din `main` este publicată prin infrastructura existentă |
| Operare | Există o procedură simplă pentru rerun, rollback, verificarea logurilor și carantinarea unei surse |

## 11. Concluzie

**Aproximativ 85–90% din munca tehnică este finalizată.** Implementarea, testarea și CI sunt în stare bună. Restul nu mai este o reconstrucție de proiect, ci o etapă de activare și operaționalizare: merge, deploy, rulare reală legacy, rulare multi-provider, comparație de calitate/cost și monitorizare.

În starea actuală, decizia importantă nu mai este „funcționează codul?”, deoarece verificările automate spun că da. Decizia este „activăm această versiune în fluxul oficial și acceptăm configurația multi-provider rezultată după testarea reală?”.

### Referințe interne

1. [Repository IZZ.ro](https://github.com/Ramanul/izz-ro)
2. [Branch `feat/multi-provider-router`](https://github.com/Ramanul/izz-ro/tree/feat/multi-provider-router)
3. [Commitul pentru timeout RSS `5c1d67e`](https://github.com/Ramanul/izz-ro/commit/5c1d67e)
4. [Commitul final de lint `1bad054`](https://github.com/Ramanul/izz-ro/commit/1bad054)
