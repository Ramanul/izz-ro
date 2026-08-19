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
