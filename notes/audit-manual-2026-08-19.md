# Audit manual hartă știri — 2026-08-19

## Desktop — verificări efectuate

- Pagina publică `/static/harta-stiri/` se încarcă fără erori vizibile; canvasul, statisticile, lista și selectorul de județe sunt prezente.
- Filtrul `Regional` schimbă URL-ul la `?nivel=regional`, afișează 4 evenimente în 2 regiuni și reduce selectorul la Oltenia și Transilvania.
- Butonul `Resetează filtrele` revine la starea inițială.
- Filtrul `Județean` afișează 45 evenimente / 47 relatări și 18 județe, cu listă și markere coerente.
- Filtrul `Local` afișează 319 evenimente / 350 relatări, cu 39 județe și localități mapate.
- Căutarea `Cluj` în modul Local actualizează URL-ul la `?nivel=local&q=Cluj`, afișează 13 rezultate, indică `13 potriviri de loc`, păstrează doar județul Cluj iluminat și ordonează rezultatele relevante.

## Observații

- Nu au fost încă verificate manual toate combinațiile rămase: `Evenimente/Relatări`, click pe fiecare tip de zonă, zoom pe județ, localități, resetarea selecției, back/forward, `Arată mai multe`, linkurile din listă, mobil și tastatura.
- Nu s-a constatat până acum o eroare runtime în fluxurile testate.

## Audit automat desktop + mobil

Scriptul existent `tools/harta_dom_check.py` a fost rulat pe buildul local la 1280px și 390px, cu touch emulat. Au trecut verificările pentru structura listei, căutarea Cluj și accident, consistența hărții cu lista, hit-test pe poligoane, protecția la drag, selecția unei localități, selectorul de județ cu tastatura, serializarea în URL, back, link direct și comportamentul mobil fără overflow orizontal. Pe mobil au trecut 31/36 puncte de atingere în interiorul județelor și protecția la derulare.

Singurele verificări raportate ca neefectuate sunt ordinea între potriviri de loc și potriviri doar în titlu, deoarece datasetul curent nu conține ambele categorii pentru interogarea folosită, și cazul localităților suprapuse, deoarece datasetul curent nu are puncte partajate.

Screenshoturile locale `/tmp/harta-1280px.png` și `/tmp/harta-390px.png` au fost generate cu succes. Vizual, desktopul prezintă harta, selectorul și panoul în două coloane; mobilul elimină overflow-ul orizontal și afișează conținutul într-o singură coloană.

## Extindere UAT — Timiș

Pentru delimitările UAT a fost identificat stratul public WFS `geospatial:ro_uat_poligon` al [geo-spatial.org](https://geo-spatial.org/ghiduri/procesari-etl/administrative-boundaries/ro-admin-lau-line/), care oferă poligoane UAT, denumirea și codul SIRUTA (`natcode`). Interogarea filtrată pentru `county='Timiș'` a furnizat 99 UAT-uri în EPSG:4326. Geometriile au fost proiectate în viewBox-ul hărții și simplificate în `static/harta-stiri/data/uat/TIMIS.json` (57 KB).

În testul local pentru `?judet=TIMIS`, harta a afișat delimitările celor 99 UAT-uri și badge-ul numeric pentru UAT-ul cu știri localizate. Markerul de localitate redundant este suprimat atunci când harta UAT este disponibilă, astfel încât utilizatorul vede o singură cifră agregată per UAT.

În modul regional, harta este acum colorată diferit pe regiunile editoriale și păstrează contururile județelor ca delimitări interne. Verificarea vizuală a confirmat contururi și culori distincte pentru regiunile afișate, precum și etichete cu numărul de rezultate pentru Transilvania și Oltenia. Următoarea ajustare: etichetele cu denumirea regiunii trebuie să rămână vizibile și când regiunea nu are rezultate în filtrul curent.

## Cerințe suplimentare confirmate (imagine utilizator)

1. Transformă fluxul de lucru într-un skill reutilizabil prin `skill-creator`.
2. Extinde generarea poligoanelor UAT la toate județele României, nu numai Timiș.
3. Verifică randarea regiunilor și județelor și la rezoluția mobilă iPhone SE, 375 px.
4. Adaugă un tooltip sau o fereastră modală cu lista știrilor când utilizatorul apasă cifra unui UAT.

## Verificare selector UAT și badge-uri adaptive

La selectarea Timișului, selectorul de sub hartă afișează `Racovița · 1`, nu lista tuturor județelor. Badge-ul UAT rămâne în harta județului și deschide dialogul cu știrea localizată. Captura desktop confirmă dialogul și lista UAT de jos. Captura iPhone SE la 375 px confirmă lățime egală cu viewportul (fără overflow), canvas de 349×247 px, badge vizibil și selector UAT lizibil.

## Diagnostic flux local Timiș — 19 august 2026

Pe pagina publică, selectarea Timișului în modul local a arătat contururile UAT, dar mesajul „Nu există știri localizate pe UAT-uri în TIMIS”; verificarea datasetului a confirmat 0 localități și 0 coordonate pentru articolele Timiș. Cauza a fost ambiguitatea SIRUTA a municipiilor care apar atât ca UAT (NIV 2), cât și ca localitate (NIV 3). După alegerea exactă a candidatului SIRUTA cu punct mapat, build-ul local a afișat 46 evenimente pentru Timiș, 10 localități confirmate, contururi UAT aliniate și badge-uri numerice în UAT-uri.
