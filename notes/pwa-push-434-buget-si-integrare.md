# #434 (PWA + alerte push): bugetul de fișiere și cum se așază lângă #435 și #436

Scris la cererea coordonatorului, pe 2026-10-04. Toate cifrele sunt măsurători, nu estimări;
unde am preluat cifra altui PR, scriu de unde vine și pe ce stare de date a fost făcută.

## 1. Cât costă #434, măsurat pe aceeași stare de date

Două randări complete (`generator.main --render-only`) din același `data/articles.json` —
baza merge-ului meu (`5f02c8f7`) și virful branch-ului — apoi diferența listelor de fișiere:

```
$ find output -type f | wc -l      # main la baza mea (5f02c8f7)
14483
$ find output -type f | wc -l      # branch-ul #434
14487
$ comm -13 <(sort main.txt) <(sort meu.txt)     # doar ce apare la mine
offline/index.html
static/push.js
static/pwa.js
sw.js
```

**#434 adaugă 4 fișiere: 14.483 → 14.487.** Marja sub `OUTPUT_FILE_BUDGET=17.000` trece de
la 2.517 la 2.513; față de plafonul gazdei (20.000, Workers Free) suntem la 72,4%.

Cele 4: `sw.js` (service workerul, la rădăcină), `offline/index.html` (pagina fără net) și
cele două scripturi noi din `static/` (`pwa.js`, `push.js`). Asta e **tot** ce adaugă PR-ul
pe disc: niciun articol, nicio imagine, niciun fișier per cititor. Cache-ul de articole e
Cache API în browser, nu spațiu pe gazdă.

Notă de sincronizare: cineva care numără azi pe `main` va găsi 14.585 — `main` a avansat cu
commituri de conținut între timp. Cifra comparabilă e cea de pe aceeași stare de date.

## 2. Cum se adună cu celelalte PR-uri deschise

| PR | Δ fișiere | sursa cifrei |
|---|---:|---|
| **#434** PWA + alerte | **+4** | măsurat aici, pe baza comună 14.483 |
| **#435** Căutare Pagefind, varianta fără fragmente | **+52** | măsurat de autor, pe aceeași bază 14.483 |
| **#436** Faza 0, portrete la cerere | **−1.128** | măsurat de autor, pe aceeași bază 14.483 |
| **toate trei, împreună** | **−1.072 → 13.411** | calculat: 14.483 + 4 + 52 − 1.128 |

| scenariu | fișiere în `output/` | marjă sub 17.000 | % din 20.000 (gazdă) |
|---|---:|---:|---:|
| baza comună (5f02c8f7) | 14.483 | 2.517 | 72,4% |
| + #434 | 14.487 | 2.513 | 72,4% |
| + #435 | 14.535 | 2.465 | 72,7% |
| + #436 | 13.355 | 3.645 | 66,8% |
| toate trei | **13.411** | **3.589** | **67,1%** |

Concluzia: **#434 nu e o problemă de buget** (0,02% din plafon), iar împreună cu #436 eliberează
mai mult decît consumă. Adevărata constrîngere din combinare e a lui #435, și autorul a rezolvat-o
deja: varianta implicită Pagefind scrie **un fragment per pagină** (14.483 + 9.458 = 23.941,
adică 120% din plafon → deploy refuzat, exact incidentul din 2026-08-21). Varianta fără
fragmente, cea aleasă, costă 52 de fișiere. Dacă cineva „activează fragmentele" mai tîrziu ca
să recapete excerptul din corp, plafonul sare — și o va face pe un deploy care e refuzat **tăcut**.

## 3. Assets vs. deployment: ce se schimbă la publicare

| schimbare | efect la deploy |
|---|---|
| `wrangler.jsonc` primește `main: infra/worker.js` | Workerul compune: `/push/*` (rutele de alerte), `/sw.js` (antet de revalidare), restul prin fallback-ul 404→oglindă, neschimbat |
| `run_worker_first: ["/push/*", "/sw.js"]` | exact două rute trec prin Worker ÎNAINTE de active. Restul traficului rămîne pe calea rapidă a activelor statice |
| legătura KV `PUSH_SUBS` | **comentată dinadins**: un `id` de namespace inexistent face deploy-ul să pice. Se decomentează cu id-ul real, altfel rutele răspund 503 cu mesaj românesc |
| `/sw.js` în `_headers` | `Cache-Control: public, max-age=0, must-revalidate` — fără el, un SW reparat poate sta 30 de zile în cache-ul HTTP |
| 4 fișiere noi în `output/` | +4 din 20.000 |

Costul de rulare pe care-l adaugă `run_worker_first`: fiecare navigare a unui vizitator care
are deja service workerul cere `/sw.js`, iar Workerul răspunde cu un `fetch` către activ și îl
reconstruiește cu antetul nou. Pe Free avem 10 milioane de cereri/lună; la traficul măsurat
al site-ului, ordinul de mărime e zecii de mii — dar **nu e zero**, și e bine să fie scris:
e prețul pentru ca un SW schimbat să ajungă la oameni într-o vizită, nu într-o lună.

## 4. Coexistență cu #435 (căutare Pagefind)

- **SW-ul nu atinge nici `/pagefind/*`, nici `search-index.json`.** Handlerul de `fetch` are
  exact două categorii (`/static/` și navigări); restul trece prin rețea. Asta e acum pinuit
  de test — `test_sw_nu_cacheaza_nimic_in_afara_de_static_si_navigari` — ca să nu apară mai
  tîrziu o „optimizare” care să bage indexul în cache.
- **Riscul evitat:** indexul are 2,04 MB brut / 683 KB comprimat și descrie articolele aflate
  AZI în fereastra TTL. Servit din cache după un deploy, ar întoarce rezultate pentru articole
  care au ieșit din fereastră — iar pagina lor ar cădea pe oglindă, nu pe site.
- **Ce NU funcționează, asumat:** căutarea offline. Indexul e prea mare pentru precache
  (l-am pune în cârca fiecărei instalări pentru un caz rar). Online, căutarea e neschimbată.
  Dacă se vrea căutare și fără net, soluția e cache la PRIMA utilizare, nu precache — și e o
  decizie de produs, nu una tehnică.

## 5. Coexistență cu #432 (harta, deja pe main)

- `static/harta-stiri/data/map.json` se regenerează la fiecare commit de conținut. Fiind sub
  `/static/`, trece prin *stale-while-revalidate*: prima deschidere după un deploy poate arăta
  harta de ieri, următoarea e proaspătă. Pentru o hartă de acoperire județeană e acceptabil;
  dacă nu e, se îngustează regula SW-ului, nu harta.
- Harta e în `shortcuts`-ul din manifest (`/static/harta-stiri/`). În aplicația instalată se
  deschide ca navigare, deci ajunge în cache-ul de articole și funcționează și fără net.

## 6. Dacă plafonul devine strîmt

Ordinea în care aș tăia, cu ce costă fiecare: (1) TTL mai mic — costă arhiva, exact ce refuză
#198; (2) portretele rămase, ca în #436 — deja făcut; (3) fragmentele Pagefind — deja tăiate.
Nimic din #434: cele 4 fișiere sunt, efectiv, rotunjire.
