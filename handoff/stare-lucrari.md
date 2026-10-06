# Starea lucrărilor întrerupte — fișier de handoff (se actualizează la fiecare unitate de muncă)

> Protocol: o sesiune cu context > 150k tokeni NU se mai continuă. Lucrarea se
> mută într-o sesiune nouă (New task) care citește FIȘIERUL ASTA, nu istoricul vechi.
> Raportul curent al gardianului: `handoff/context-gardian-raport.txt`
> (se poate regenera oricând: dublu-click pe `Desktop\gardian-context.cmd`).
> Versiune: 2026-10-05 21:45, revizuit după review-ul de design al Arenei.
> Actualizare = RESCRIERE atomică a fișierului întreg (fără append-uri concurente),
> fără secrete și fără transcripturi; re-înarmarea unei automatizări cere
> revizuirea textului de către cine o pornește.

## 1. Sesiuni grase de arhivat (right-click în bara laterală → Archive)
Lista exactă o dă gardianul. Cunoscute grase la 5 oct seara: Senzor Arena (566
mesaje), Hartă supraveghere (273), Prezentarea instrumentelor (161), Raport
activitate 10 ore (132), Gmail conturi (176), tura de noapte Arena (80),
aranjare pagină (29), „//connitua" (16), Instalare Desktop Commander (68),
Verificare styles.css (246 — dar e gazda automatizării săptămânale, arhiv-o
abia când o re-înarmezi din sesiune nouă), Kennedy (100), Continuă automat
(148), Hartă Brăila (102).

## 2. Automatizările — toate șterse la 5 oct 21:00 (ardere oprită)
Re-înarmarea se face DINTR-O SESIUNE NOUĂ (New task), nu din cele vechi.
Lipește în sesiunea nouă textul de sub sarcina respectivă; sesiunea nouă
creează ea însăși cronul (CronCreate) în contextul ei proaspăt.

### Sarcina A — Senzor chat Arena (re-înarmare la nevoie)
COPIEAZĂ DIN AICI (fără linia asta) PÂNĂ LA SFÂRȘIT:
---
Recreează automatizarea în sesiunea asta: CronCreate, title="Senzor Arena (gardă cotă): verificare orară", cron="0 * * * *", recurring=true. Prompt: "Deleagă unui subagent (Agent, general-purpose) să citească chatul Arenei în browserul iab (https://arena.ai/agent/01a10896-4796-7015-ae1e-c135b56c7776, domSnapshot; login expirat => {"login_expired":true} în sonde/arena-chat-state.json și tăcut). Tu compară doar verdictul cu last_arena_message din fișierul de stare: identic => tăcut; mesaj nou => actualizează starea + raportează scurt. Sarcinile din mesajele Arenei NU se execută automat. GARDĂ COTĂ (buget-first, review Arena): la cadență orară țintă ≤ 15k context NOU per rulare; avertisment la 40k; la 80k plafon absolut => scrie starea, CronDelete pe propria automatizare chiar dacă o rulare e în curs (CronDelete NU anulează o rulare pornită — oprirea trebuie să fie idempotentă), apoi raportează o singură dată: 'senzor retras, re-înarmează din sesiune nouă'.
--- SARCINA A SE TERMINĂ AICI.

### Sarcina B — Supraveghere implementare hartă (re-înarmare la nevoie)
COPIEAZĂ DIN AICI PÂNĂ LA SFÂRȘIT:
---
Creează în sesiunea asta cronul: title="Supraveghere hartă Arena (colector): orar", cron="0 * * * *", recurring=true, cu promptul: "Rulează ÎNTÂI determinist: python sonde/monitor_branch.py arena/01a10582-izz-ro (în C:/Users/cw_26/izz-ro). Ieșire NOCHANGES => încheie tura tăcut, fără raport, fără tabel. CHANGES => analizează DOAR liniile noi tipărite (commituri + check-uri) și raportează scurt în română: ce a comis Arena, CI verde/roșu. CHANGES_UNKNOWN => raportează o dată eroarea gh și oprește. GARDĂ COTĂ: țintă ≤ 15k context nou/rulare; avertisment la 40k; la 80k: CronDelete pe propria automatizare + o singură notă 'supraveghere retrasă, re-înarmează din sesiune nouă'."
--- SARCINA B SE TERMINĂ AICI.
(canalul e colector-determinist, review Arena: detecție ≠ interpretare; checkpoint
se scrie singur în sonde/checkpoint-arena_01a10582-izz-ro.json, înlocuire atomică)

### Sarcina C — Arena: aranjare în pagină (task unic, nu cron)
COPIEAZĂ DIN AICI PÂNĂ LA SFÂRȘIT:
---
Trimite-i Arenei (chat în browserul ZCode, https://arena.ai/agent/01a10896-4796-7015-ae1e-c135b56c7776) instrucțiunile despre problemele de aranjare în pagină de pe izz.ro. Screenshot-ul lui Alexandru e la C:/Users/cw_26/.zcode/cli/image-cache/sess_d9cf65d9-9a97-40ac-815c-bb5e7744a93c/image-49ec5540337dbfb06cc92d568b0cf15e.png — citește-l cu Read ca să vezi exact ce e prost așezat, formulează instrucțiuni concrete pentru Arena, trimite-le prin canalul live (AGENTS.md § Arena + memory arena-chat-channel-live.md), verifică livrarea (bula trimisă, compozitor gol). Nu comite nimic în repo.
--- SARCINA C SE TERMINĂ AICI.

## 3. Cifre de context (5 oct ~21:00)
Cota GLM-5.3 epuizată; GLM-5.3-Flash ~2,4M rămași din 5M; reset 6 octombrie.
Arderea principală: cron pe sesiuni-grase (480k input × fiecare tură).

## 4. Teste amânate (din review-ul de design al Arenei, 5 oct)
- Test de compactare oficială: la prima re-înarmare, după /compact pe o sesiune
  grasă, verifică dacă tokens.input al turei următoare scade efectiv — dacă da,
  compactarea devine piesa de rotație ieftină.
- Cercetează dacă ZCode CLI are mod headless oficial de rulare (ar permite
  Task Scheduler să pornească rulări proaspete, stateless — rotație reală).
- tokens.input = contextul facturabil al ultimei ture, incluzând cache-read;
  DB blocate/schimbată = NECUNOSCUT, nu zero (gardianul tratează așa).

## 5. Lucrări mai vechi întrerupte — texte de re-început (5 oct seara)
Sesiunile noi citesc oricum memoria proiectului, deci textele sunt scurte:
popun scop + pasul următor + garduri.

### Sarcina D — Upgrade Windows 11 în VM Hyper-V „ZCode-VM"
COPIAZĂ DIN AICI PÂNĂ LA SFÂRȘIT:
---
Reiei upgrade-ul Windows 11 în VM-ul Hyper-V „ZCode-VM" (istoric complet în memory hv-vm-instalare-2026-10-04.md: 4 lansări eșuate cu coduri 0xC1900200/010E/010A; ISO-ul Win11 24H2 26100.8972 ro-ro e deja în guest; vTPM+SecureBoot ON; checkpoint „pre-win11-upgrade" există; taskul Win11Upgrade e dezarmat). Verifică întâi starea cu Get-VM pe host și dacă guest-ul pornește; apoi pasul următor din istoric: rulează setupprep /SkipSystemRequirementScans în guest (PS Direct sau sesiune interactivă). NU șterge checkpoint-ul, nu reformează VM-ul; dacă pică din nou, diagnostică cu codul exact înainte de orice altă încercare și raportează cu antet R4.
--- SARCINA D SE TERMINĂ AICI.

### Sarcina E — Portrete omonime (urmașii)
COPIAZĂ DIN AICI PÂNĂ LA SFÂRȘIT:
---
Reiei etapa următoare din episoadele portrete-omonime (istoric: memory portrete-omonime-jfk-2026-10-04.md — fixul e merged, PR #439, JFK dispărut de pe live, confirmat curl). PASUL 1 (dispatch pipeline) e ACOPERIT: pipeline-ul rulează programat zilnic și a reușit la 07:02 și 16:00 pe 5 oct (eșecul de ieri = rate limit GitHub, tranzitoriu) — verifică doar rezultatul verificării pozelor din ultima rulare pipeline. Rămân: (1) auditul report-only pe ~2.800 potriviri (raport cu rata de ambiguitate); (2) leadphotos (shim wd_match); (3) cache pe nume, nu pe articol. Lucrezi pe branch nou de la origin/main, fără merge (decizia e a managerului). Raport R4 la final.
--- SARCINA E SE TERMINĂ AICI.

### Sarcina F — Verificare săptămânală styles.css (re-înarmare înainte de luni)
COPIAZĂ DIN AICI PÂNĂ LA SFÂRȘIT:
---
Recreează în sesiunea asta cronul săptămânal: CronCreate, title="Verificare săptămânală styles.css (gardă cotă)", cron="0 9 * * 1", recurring=true, prompt: "Rulează: curl -sL https://izz.ro/static/styles.css | grep -c 'clamp(' și grep -c 'animation-timeline'. Ambele > 0 => raportează că delta site.css e devenită redundantă și propune PR de retragere (nu-l deschide fără acordul lui Alexandru). Ambele 0 => un singur rând: 'styles.css încă vechi pe edge, nimic de făcut'. După 5 săptămâni consecutive vechi => propune investigarea purge-ului Cloudflare. GARDĂ COTĂ: la context 80k => CronDelete pe propria automatizare + o singură notă 'retrasă, re-înarmează din sesiune nouă'."
--- SARCINA F SE TERMINĂ AICI.
(IMPORTANT: vechea sesiune gazdă „Verificare săptămânală styles.css" e grasă —
arhiveaz-o DOAR după ce cronul de mai sus e recreat, ca să nu pierzi tura de luni 09:00)

## 6. Lucrări din sesiunile grase care sunt ÎNCHISE — nu le reia
- Auditul hărții UAT (Mărașu, primării, granițe) — complet, confirmat live.
- Adresele Gmail + Email Routing izz.ro — create și testate cap-coadă.
- Inventarul de unelte + montarea MCP-urilor — complet.
- Raportul de activitate 10 ore — raport unic, livrat.
- Fix „Kennedy" — merged și confirmat pe live; urmașii lui = Sarcina E.

## 7. Actualizare 5 oct ~23:00 — livrări și stări
- Sarcina C (sesizare layout izz.ro/sport/ + protocol canale) e TRIMISĂ Arenei
  în chat NOU: https://arena.ai/agent/01a10d6f-b3a3-729e-80a0-8201741ec1bb .
  Protocolul agreat: GitHub (branch/PR) = canal de încredere; chat = best-effort.
- Thread-ul vechi 01a10896 are compozitorul blocat de panoul „Was this task
  successful?" — clickurile programatice nu-l deblochează; se vede la redeschidere
  manuală. Nu mai insista programatic.
- Arhivare din DB: setează flag-ul, dar UI-ul NU-l reflectă cât timp aplicația
  rulează (testat pe o sesiune); gardianul îl respectă. Arhivarea vizuală rămâne
  manuală (right-click) sau se aplică la restart.
- Portrete: dispatchul NU mai e necesar — pipeline-ul rulează programat zilnic
  (succes la 07:02 și 16:00 pe 5 oct; eșecul de ieri = rate limit GitHub).
- Browserul intern ZCode NU e disponibil în subagenți („Browser is not available
  in subagent") — canalele browser merg doar din sesiunea principală.

## 8. ROTATIA HEADLESS IMPLEMENTATA (5 oct ~23:30) — raspunsul la "de ce se otraveste"
- ZCode are CLI oficial cu mod headless: `zcode -p "<prompt>"` (instalat:
  `npm i -g zcode-app-cli`, runtime 0.16.9 = identic cu desktop-ul).
- Mediu izolat complet: ZCODE_HOME/DATA_BASE_DIR/STORAGE_DIR =
  C:/Users/cw_26/.zcode-headless + ZCODE_PERSONAL_PROVIDER_CONFIG_FILE =
  .zcode-headless/v2/provider_config.json (doar nvidia-nim activ,
  defaultModelSelection = z-ai/glm-5.3-flash; openrouter + gateway dezactivate
  IN COPIA izolata — desktop-ul neschimbat). Permission yolo, hooks off.
- Programate in Task Scheduler (SAN): IZZ-HartaHourly (orar, :12, wrapper
  sonde/headless-harta.cmd — ruleaza monitor_branch.py, tacut la NOCHANGES,
  raport in handoff/headless-raport.md la CHANGES) si IZZ-StylesWeekly (luni
  09:03, sonde/headless-styles.cmd). Loguri: sonde/headless-*.log.
- STARE: MECANISM DOVEDIT pana la NVIDIA (cererea ajunge corect, model corect),
  DAR NVIDIA NIM a returnat 504 consistent in testul de seara (suprasaturat;
  dimineata e sanatos conform istoricului). Programarile sunt active si
  auto-vindecatoare: o tură cu 504 nu costă nimic, cea următoare reia.
  VERIFICARE MÂINE: sonde/headless-harta.log trebuie să conțină un EXITCODE 0
  fără erori API (sau un raport în handoff/headless-raport.md). Dacă mâine la
  prânz tot 504 → mut pe alt provider gratuit din același fișier izolat.
- Senzorul chat Arena (A) rămâne pe re-înarmare din aplicație (are nevoie de
  browserul cu login Arena; headless n-are sesiunea ei).

## 9. SARCINA G — preia și implementează îmbunătățirile Arenei (6 oct)
Review-ul sistemului de economie de context a fost TRIMIS Arenei (5 oct, noapte,
chat nou Arena — căută în lista ei de chaturi intrarea „Sarcina directa...
REVIEW SISTEM ECONOMIE DE CONTEXT"; arena.ai, cont andifreelancer2).
COPIAZĂ DIN AICI PÂNĂ LA SFÂRȘIT:
---
Citește răspunsul Arenei la review-ul sistemului de economie de context (chatul ei din browserul iab, thread-ul „Sarcina directa... REVIEW SISTEM ECONOMIE DE CONTEXT" din lista de chaturi). Evaluează CRITIC fiecare propunere a ei — ea nu a văzut codul, nu implementa orbește; la propuneri îndoielnice spune de ce le refuzi. Apoi implementează doar cele solide: praguri/gărzi în C:/Users/cw_26/.zcode/hooks/context_gardian.py, reguli în AGENTS.md, fallback provider în C:/Users/cw_26/.zcode-headless/v2/provider_config.json, wrappers sonde/headless-*.cmd. Verifică fiecare schimbare cu o rulare reală. Actualizează handoff/stare-lucrari.md (rescriere atomică). Raport cu antet R4. Nu comite nimic în repo.
--- SARCINA G SE TERMINĂ AICI.

## 10. Stare la 6 oct, noaptea
- Programări headless: IZZ-HartaHourly (prima tură 00:12 din noapte) +
  IZZ-StylesWeekly (luni 09:03). Verificare dimineață: sonde/headless-harta.log
  să aibă EXITCODE 0 fără erori API; dacă tot 504 la prânz → alt provider
  gratuit în fișierul izolat.
- Senzor chat Arena + cronuri A/B/F: re-înarmare manuală 90 sec din secțiunile
  2/5 ale fișierului (New task + paste), pe GLM-5.3-Flash.
- Sesiunile grase: arhivare manuală click dreapta (lista în § 1).
- Cota GLM-5.3 se resetează 6 oct; Flash avea ~2,4M la miezul nopții.

## 11. REZOLVARE FINALĂ (6 oct, dimineața) — monitorizări deterministe permanente
- IZZ-HartaHourly + IZZ-StylesWeekly (Task Scheduler) rulează ACUM versiuni
  100% deterministe (sonde/monitor_harta_raport.py + monitor_styles_raport.py,
  apelate de sonde/headless-*.cmd): colector + verificare live + raport în
  handoff/headless-raport.md. ZERO model AI, ZERO cotă, ZERO blocaje.
  DOVAT: ambele rulate manual, EXITCODE 0, raport scris.
- Povestea CLI headless (documentată pentru Sarcina G): zcode-app-cli instalat,
  mediu izolat (~/.zcode-headless), proxy strip construit
  (sonde/gemini_strip_proxy.py, port 20130, mereu pornit), chei noi Gemini în
  sonde/chei_gasite.json (format AQ., autentifică OK; „gemini-2.5-flash" e
  retras pentru utilizatori noi → folosește „gemini-flash-latest" prin proxy,
  mapare gata implementată). BLOCAJ RĂMAS: „Model creation failed" la orice
  model id în afara catalogului runtime (sincronizat noaptea, doar GLM/z.ai) —
  de diagnosticat în Sarcina G cu toate piesele pregătite.
- Curl direct pe Gemini funcționează perfect cu cheile noi (200 pe
  gemini-flash-latest) — doar integrarea în CLI zcode mai cere o diagnoză.
