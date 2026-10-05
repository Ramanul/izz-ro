# Basemap OpenFreeMap pentru harta știrilor

**Data:** 2026-10-05 · **Stare:** implementat pe branch; testele automate trec; verificarea vizuală în browser rămâne de făcut. Fără merge/deploy.

## Scop
Adaugă un basemap vectorial OpenFreeMap în spatele hărții tematice fără a înlocui rendererul Canvas 2D, poligoanele tematice, filtrele, hit-test-urile sau controalele accesibile existente. MapLibre este limitat la randarea fundalului; camera lui urmează vederea Canvas.

## Date și semantică
- `map.json` păstrează `x/y` în viewBox-ul propriu. Proiecția WGS84 și limitele ei vin din `data/harta_localitati.json` și se publică separat în `static/harta-stiri/data/projection.json` pentru sincronizarea camerei.
- Un punct de articol reprezintă o localitate de referință, nu locul exact al incidentului. Precizia poziției sursei nu este măsurată; `confidence` descrie baza atribuirii geografice, nu acuratețea coordonatei, iar UI-ul trebuie să spună asta explicit.
- Markerii se desenează doar în vederea de județ, la coordonatele publicate ale localităților. Datele fără `x/y` rămân agregate în poligon și nu primesc centroid/marker sintetic.
- Culorile continuă să codifice numărul de evenimente sau relatări în setul filtrat. Legenda trebuie să corespundă exact intervalelor produse de rampa curentă.

## Implementare
- Vendorați MapLibre GL JS/CSS local (CSP existentă permite doar scripturi same-origin).
- Încărcați stilul Positron OpenFreeMap ca strat decorativ, fără gesturi proprii; canvasul existent rămâne interactiv și accesibil.
- Sincronizați centrul/scara din `view` și proiecția `map.json`; compensați la centru diferența verticală Mercator/equirectangular și verificați alinierea în browser.
- Faceți poligoanele tematice suficient de translucide pentru ca străzile să rămână vizibile; păstrați contrastul contururilor, badge-urilor și al rampei.
- Dacă MapLibre, WebGL sau serviciul de dale nu pornește, harta Canvas trebuie să rămână utilizabilă pe fundalul actual.
- Afișați atribuirea cerută de furnizor, `OpenFreeMap © OpenMapTiles Data from OpenStreetMap`, și permiteți în CSP numai originile necesare.

## În afara scopului
Migrarea poligoanelor în MapLibre, tiles locale/PMTiles, clustere, geocodare, localizarea exactă a incidentelor, schimbarea filtrelor, pipeline-ul Sharp, merge și deploy.

## Criterii de acceptare
1. Fundalul OpenFreeMap apare în browser când WebGL și rețeaua sunt disponibile; atribuirea rămâne vizibilă.
2. La nivel național, după selectarea unui județ, zoom/pan și fly-to, contururile tematice și basemap-ul rămân aliniate vizual.
3. Toate filtrele/stările URL/lista și selecțiile Canvas existente continuă să funcționeze; dacă fundalul eșuează, poligoanele și filtrele rămân disponibile.
4. Punctele sunt etichetate drept repere de localitate; înregistrările fără coordonate nu capătă puncte; culoarea și totalul explică modul activ și setul filtrat.
5. Testele relevante trec; se verifică DOM-ul și capturi la desktop și mobil. Nu se face merge, PR sau deploy.
