# PLAN — izz.ro pe mai multe Workere gratuite (fără card), împărțit pe categorii

**Cerere proprietar, 2026-11-08:** de ~10 ori mai multe pagini și trafic, imagine pe fiecare
articol, rămânând pe planul Free și **fără niciun card / plată la consum** (R2 respins, IZZ-0453).
**Stare: PLAN, nimic implementat.** Atinge zone protejate (§10: Worker code, `wrangler.jsonc`,
rute Workers) — fiecare felie de mai jos care le atinge cere „da"-ul proprietarului pe felia aceea.

## 1. Fapte de pornire (verificate 2026-11-08, nu din memorie)

| Fapt | Sursa |
|---|---|
| Free: **100 Workere/cont**, **20.000 fișiere/versiune**, 25 MiB/fișier, fără plafon total de spațiu, stocarea assets gratuită | `developers.cloudflare.com/workers/platform/limits/`, `.../static-assets/billing-and-limitations/` |
| Cererile către fișiere statice: **gratuite și nelimitate**, pe fiecare Worker; plafonul de 100.000/zi îl consumă doar scriptul | aceeași pagină de billing |
| La două rute care se potrivesc, **câștigă cea mai specifică** (`izz.ro/sport/*` bate `izz.ro/*`); nu există „cădere" la ruta următoare dacă fișierul lipsește | `.../configuration/routing/routes/` |
| Adresele de articol sunt `izz.ro/<categorie>/<slug>/` — **fără dată în cale** | `output/sitemap.xml` |
| Azi: **11.095 fișiere**; `local/` = **5.141 (46%)**, `subiect/` 902, `sport/` 866, restul sub 700 | `find output -type f`, numărat pe foldere |
| Workerul `izz-ro` **are script** (`infra/worker.js`): la 404 pe articol cere pagina de la oglinda gh-pages `ramanul.github.io` (IZZ-0425). Fiecare astfel de cerere **consumă din cele 100.000/zi** | `wrangler.jsonc`, `infra/worker-404-mirror.js` |
| Oglinda gh-pages: **904 MB din plafonul de ~1 GB** al GitHub Pages (7 nov) | `specs/STATE.md` |
| Repo-ul e **public** → minute GitHub Actions nelimitate | `gh repo view` |

Consultare: Argon (Modul AI Google, nivel nedovedit) și asistentul Cloudflare din dashboard,
2026-11-08 — de acord pe tot ce e tehnic; **în dezacord pe termeni** (§6).

## 2. Diagnosticul — unde e plafonul de fapt

Traficul **nu** e plafonul: fișierele statice sunt gratuite oricât. Plafoanele reale sunt trei:
1. **20.000 de fișiere** pe Workerul unic → supapa taie arhiva (`OUTPUT_FILE_BUDGET` 17.000).
2. **Arhiva veche trece prin script** (oglinda) → la 10× trafic, cererile pe articole vechi pot
   atinge 100.000/zi; peste prag, fallback-ul pică (pagina veche dă eroare), restul site-ului merge.
3. **Oglinda gh-pages se apropie de 1 GB** → `curata_oglinda.py` taie deja pagini.

Planul de mai jos le rezolvă pe toate trei cu același mecanism.

## 3. Arhitectura propusă

- **Workerul principal `izz-ro`** (ruta `izz.ro/*`, neschimbată): prima pagină, `static/`, feeduri,
  sitemap, pagini fixe, `subiect/`, `/push/*`. Scriptul rămâne (alerte + oglindă pentru ce n-a migrat).
- **Câte un Worker assets-only pe categorie** (`izz-cat-sport` pe ruta `izz.ro/sport/*` etc.):
  pagina de categorie, paginarea, articolele ei **cu tot cu imaginile lor**, curente și arhivă.
  Fișierele existente se servesc fără script (gratuit, nelimitat); scriptul de oglindă rulează
  doar când fișierul lipsește (felia 2).
- **`local/` se împarte în continuare** după prima literă a slug-ului (`izz.ro/local/a*`,
  `izz.ro/local/b*`…, grupate în 3–4 Workere), fiindcă singură ar depăși 20.000 la 10×.
  ⚠ Neverificat: că Cloudflare acceptă o rută cu steluța după un fragment de segment. Se testează
  primul (felia 0).
- **Fiecare Worker are bugetul lui** (17.000), iar supapa taie per Worker, nu global.
- **Imaginile stau lângă articol**, în Workerul categoriei — nicio origine nouă, niciun CORS.
- Capacitate: vezi §8 — la 10× cu imagine pe articol trebuie **~25–30 de Workere**, nu 20;
  plafonul de cont (100) rămâne departe.

## 4. Felii verticale (fiecare se termină verificată și se oprește pentru „da")

**Felia 0 — testul care poate infirma planul (fără efect la cititor).**
Un Worker de probă assets-only cu 2 fișiere, pe ruta `izz.ro/_proba-ruta/a*`. Se verifică:
(a) Cloudflare acceptă tiparul; (b) `izz.ro/_proba-ruta/abc` vine din Workerul de probă, iar
`izz.ro/_proba-ruta/xyz` cade pe `izz-ro` (404 normal); (c) nicio invocare de script contorizată.
Apoi ruta și Workerul de probă se șterg. **Atinge rute Workers (§10) → cere „da".**
Dacă (a) sau (b) pică: `local/` se împarte altfel (subfoldere pe județ), ceea ce schimbă adrese — se oprește și se re-decide.

**Felia 1 — generatorul scrie pe „cioburi", fără nicio schimbare de publicare.**
`generator/render.py` + `generator/config.py`: după randare, un pas `shard` mută arborii de
categorie în `dist/<worker>/` și lasă restul în `output/`; manifest `dist/shards.json`
(worker → rută → nr. fișiere → sha). Bugetul și supapa per ciob. Comutator `SHARDS_ENABLED`,
**oprit implicit** → producția identică. Verificare: teste noi pe partiționare (niciun fișier
pierdut sau dublat; suma ciob + principal = total), `pytest`, `ruff`, `--render-only` cu
comutatorul pornit și oprit.

**Felia 2 — pilot pe o singură categorie mică (`auto`, 132 fișiere).**
`.github/workflows/deploy-worker.yml`: generează `wrangler` config assets-only pentru ciob,
îl publică **înaintea** principalului, oprește tot dacă un ciob pică (fail-closed).
Ciobul NU e pur assets-only: primește același fallback de oglindă (`infra/worker-404-mirror.js`,
doar la ratare), altfel articolele ieșite din fereastra ciobului ar da 404 — ruta lui nu mai
ajunge la scriptul principal. Invocări doar la ratare, ca azi, dar ratările devin rare odată cu
felia 4.
`tools/verify_release.py`: verifică sha-ul și pe ciob. **Atinge Worker code + rute → cere „da".**
Verificare: live — `izz.ro/auto/` și 5 articole (inclusiv unul vechi) 200, imagini 200,
`build.json` al ciobului = commitul; invocările scriptului nu cresc.

**Felia 3 — restul categoriilor, câte 3–4 pe rulare**, aceeași verificare. `local/` ultima, pe
literele confirmate în felia 0.

**Felia 4 — se ridică arhiva.** Cu fiecare ciob sub buget, `ARTICLE_TTL_DAYS` crește treptat
(21 → 45 → 90), măsurând fișierele per ciob după fiecare pas. Oglinda gh-pages rămâne plasă de
siguranță doar pentru ce depășește TTL-ul, deci nu mai crește spre 1 GB.

**Felia 5 — imagine pe fiecare articol: decizie separată.** Găzduirea e rezolvată de feliile 1–3;
**sursa** imaginilor (drepturi, calitate, Wikimedia vs. generat) e altă discuție și alt plan.

## 5. Criterii de „gata", măsurabile

- Fiecare Worker sub 17.000 de fișiere, citit din manifest la fiecare deploy.
- `verify_release.py` verde pe toate cioburile + principal, același commit.
- Pe live: 0 imagini rupte pe un eșantion de 50 de articole din toate categoriile.
- Invocările scriptului `izz-ro` **scad** față de săptămâna dinainte (Analytics).
- Arhiva servită direct (fără oglindă) ≥ 45 de zile după felia 4.

## 6. Riscuri și ce NU acoperă

- **Termenii Cloudflare — neclarificat.** Argon: „zonă gri, ocolirea limitei de plan".
  Asistentul Cloudflare: documentația recomandă mai multe Workere și nu interzice; fără garanție
  juridică. Cel mai rău caz plauzibil (deducție, nedocumentată): avertisment sau blocarea
  Workerelor suplimentare; **nu o factură**, contul neavând card. Atenuare: revenirea e
  `SHARDS_ENABLED=0` + ștergerea rutelor, iar Workerul principal rămâne complet funcțional.
- **Ordinea la publicare.** Cioburile întâi, principalul ultimul; un ciob picat oprește principalul.
  Dacă un ciob rămâne în urmă, prima pagină nu trimite spre articole inexistente.
- **Sincronizarea listei de categorii** (worker, oglindă, rute) — păzită deja de
  `tests/test_worker_mirror_rutare.py`; se extinde la manifest.
- **Durata deploy-ului** crește (~20 de publicări); wrangler urcă doar fișierele schimbate, iar
  cioburile cu arhivă se schimbă rar. Minutele Actions sunt nelimitate (repo public).
- **Nu acoperă:** sursa imaginilor (felia 5); traficul de roboți (WAF, IZZ-0452); SEO (§11).

## 7. În ce condiții planul e greșit

Dacă felia 0 arată că rutele cu steluța după fragment nu sunt acceptate, **și** proprietarul nu
vrea adrese noi pentru `local/`, atunci `local/` nu poate crește peste 20.000 de fișiere, iar
planul acoperă doar celelalte categorii. Dacă Cloudflare tratează împărțirea drept abuz, planul
cade cu totul și se revine la un singur Worker.

## 8. Corecturi după revizia Argon (Gemini, „Argon Maximum, verificat pe pagină”, 2026-11-08)

Conversația: `gemini.google.com/app/a2bfc5a14449f2b7`. Ce am acceptat, cu verificarea mea:

1. **Matematica.** O imagine pe articol dublează fișierele: ~1,6 fișiere/articol azi în `local/`
   (5.141 fișiere / 3.183 intrări, măsurat) → ~2,6 cu imagine. La 10× totalul trece de ~200.000,
   `local/` singur de ~80.000–100.000 → **6–7 cioburi pentru `local/`**, nu 3–4.
2. **Literele nu sunt egale** (măsurat în `output/local/`: a 552, p 499, c 329, s 173, u 165…).
   Gruparea se face pe distribuția măsurată, nu pe alfabet; rutele permit doar `*`, deci câte o
   rută pe caracter (`izz.ro/local/a*` … `izz.ro/local/9*`, ~36 de rute) repartizate pe cioburi.
3. **Paginarea `local/` e numerică** (`/local/10/`, `/local/100/`, măsurat) → rutele `local/0*`…`9*`
   o prind. Se pune paginarea în ciobul care deține cifrele, nu pe principal.
4. **`subiect/` primește ciob propriu** — al doilea folder ca mărime, ar sufoca principalul la 10×.
5. **Sitemap-ul se sparge**: `sitemap.xml` are deja 6.582 de URL-uri; plafonul protocolului e
   50.000 → index de sitemap pe principal + câte un sitemap per ciob.
6. **Ordinea de publicare în 3 pași**: `static/` (CSS/JS, pe Workerul lui, `izz.ro/static/*`) →
   cioburile → principalul. Motiv: `_asset_ver` e query-string, deci un ciob nou care cere
   `styles.css?v=nou` înaintea principalului ar putea fixa în cache fișierul vechi sub cheia nouă.
7. **Publicare doar pentru cioburile schimbate** (sha din manifest comparat cu `build.json` al
   ciobului de pe live). Rulări secvențiale. Argon pomenește o limită API Cloudflare de
   1.200 de cereri / 5 minute — **neverificată**, dar secvențial nu o atingem oricum.
8. **Arhiva pe termen lung nu e oglinda.** Ridicarea TTL-ului doar amână umplerea oglinzii
   gh-pages; la 10× ar crește de 10× mai repede. Direcția corectă: **cioburile nu expiră
   articole** — când unul se apropie de 17.000, se împarte (ca `local/`). Capacitatea reală devine
   ~100 de Workere × 17.000. Oglinda îngheață ca arhivă a articolelor dinainte de cioburi.
   Felia 4 se rescrie în sensul ăsta la implementare.
9. **Oglinda nu poate fi scoasă de pe cioburi** — aici NU sunt de acord cu Argon: articolele ieșite
   deja din TTL nu mai există în starea pipeline-ului (le scoate `state.expire()`), deci trăiesc
   doar pe oglindă. Fără scriptul de fallback, adresele lor vechi ar da 404. Expunerea la
   invocări e aceeași ca azi (azi Workerul principal primește toate ratările); scriptul
   respinge din prima ce nu arată a slug de articol, fără fetch către oglindă.
10. **Imaginile articolelor din oglindă nu se copiază acolo** (plafonul de 1 GB): articolul vechi
    servit din oglindă afișează arta generată / imaginea categoriei, nu o imagine ruptă.

## 9. Felia 0 — REZULTAT (2026-11-08, confirmat pe live)

Worker de probă `izz-proba-ruta` (assets-only, 2 fișiere), rutele `izz.ro/_proba-ruta/a*` și
`izz.ro/_proba-ruta/1*`, publicat cu `wrangler@4.125.0 deploy`; acceptate fără eroare.
Cereri reale pe `izz.ro`:

| Cerere | Răspuns | Concluzie |
|---|---|---|
| `/_proba-ruta/abc.txt` | 200 „PROBA-WORKER litera” | ruta pe literă funcționează |
| `/_proba-ruta/1x.txt` | 200 „PROBA-WORKER cifra” | ruta pe cifră funcționează |
| `/_proba-ruta/xyz.txt` | 404, pagina 404 a site-ului | ce nu se potrivește rămâne pe `izz-ro` |
| `/_proba-ruta/abzzz.txt` | 404 gol, din ciob | **nu există cădere** la Workerul principal |
| `/_proba-ruta/Abc.txt` | 404, pagina site-ului | rutele sunt sensibile la majuscule |

Testul distinge: dacă rutele n-ar fi fost acceptate, `abc.txt` ar fi întors pagina 404 a
site-ului, nu textul de probă. După `wrangler delete`: ambele adrese → 404 de pe `izz-ro`, prima
pagină 200 (o rută orfană ar fi dat eroare de origine, nu pagina site-ului).
**Planul nu e infirmat.** Consecințe pentru implementare: fiecare ciob are nevoie de propria
pagină 404 (`not_found_handling: 404-page`) și de fallback-ul de oglindă, fiindcă ratările nu
cad pe principal; slug-urile rămân doar cu litere mici.

## 10. Felia 1 — REZULTAT (2026-11-08, verificat local)

`generator/shard.py` (`python -m generator.shard --src output --dest dist`) copiază `output/` în
`dist/<ciob>/` după aceeași regulă ca rutarea Cloudflare (adresa servită, cea mai lungă potrivire,
sensibil la majuscule) și scrie `dist/shards.json` (rute, număr de fișiere, amprentă per ciob).
Grupurile `local/` și prefixul de subiecte stau în `generator/config.py`.

**Abatere de la plan, cu motiv:** bugetul și supapa per ciob NU s-au mutat în felia 1. Cât timp
publicarea e un singur Worker, un buget per ciob ar lăsa randarea să depășească 20.000 de fișiere
pe Workerul unic → deploy refuzat. Bugetul se mută odată cu felia 4, după ce cioburile sunt pe live.
Felia 1 nu e legată de nimic: producția e neschimbată.

Pe randarea reală (11.095 de fișiere-sursă → 11.118 în `dist/`): **23 de cioburi, 0 fișiere
pierdute**; singura dublură e intenționată (`local/index.html`, vezi mai jos), plus 23 de copii
404. Cel mai mare ciob `local-a` = 1.126; principalul rămâne cu 696. 52 s.

Reparat după revizia Argon a diff-ului (gemini, 2026-11-08), fiecare cu test:
- `izz.ro/sport` fără bară ar fi căzut pe principal, care n-are pagina → fiecare categorie are și
  ruta exactă `izz.ro/<cat>` lângă `izz.ro/<cat>/*`;
- `/local/index.html` merge pe ruta `local/i*` → pagina se copiază și în `local-defghi`;
- cioburile goale (categorii în însămânțare) primesc tot 404, ca setul de rute să rămână stabil;
- `shards.json` se scrie doar DUPĂ verificarea plafonului; nume duplicate și un `--dest` care
  ar include sursa (ștergerea ar lua randarea) sunt refuzate.
Neadoptat: legături fizice în loc de copii (câștig de timp mic, risc pe Windows).

Respins: împărțirea `local/` pe an/lună — schimbă adresele existente (SEO, §11).
Felia 0 se extinde: testează și o rută pe cifră (`/_proba-ruta/1*`) și una pe literă.

## 11. Felia 2 — pilot `auto` (2026-11-08, confirmat pe live)

Workerul `izz-ro-cat-auto` (versiunea fe34af06, publicat local cu `wrangler deploy -c
dist/izz-ro-cat-auto.config.json`) are rutele `izz.ro/auto` și `izz.ro/auto/*`. Configul îl scrie
`generator/shard.py` (`worker_config`): scriptul e doar `infra/worker-404-mirror.js`, assets fără
`not_found_handling`, deci ratarea aduce articolul expirat de pe oglindă, ca la principal.
Fiecare ciob primește și `_headers`, `build.json` și `_redirects` filtrat pe rutele lui.

Dovada (curl, 13 adrese, înainte și după): aceleași coduri — `/auto/` 200, `/auto` 307 → `/auto/`,
paginare 200, 3 articole 200, 2 imagini 200, `feed.xml` 200, articol expirat 200 din oglindă,
inexistent 404 cu pagina site-ului, CSP prezent ca înainte. `izz.ro/auto/` are amprenta ciobului
(`d7398d73`), nu a principalului (`aa8a9827`) → răspunde ciobul.

Publicarea automată: `deploy-worker.yml` împarte, publică `config.SHARDS_LIVE` înaintea
principalului și verifică `build.json` pe `izz-ro-<ciob>.andifreelancer2.workers.dev`; orice eșec
oprește principalul. **Neverificat până la prima rulare CI:** dacă tokenul din GitHub are dreptul
de a lega rute pe zonă (local s-a publicat cu contul proprietarului).
Revenire: scoate ciobul din `SHARDS_LIVE` + `npx wrangler delete --name izz-ro-cat-auto`.

**Stare la 2026-11-08 seara: pilot OPRIT** (`wrangler delete --name izz-ro-cat-auto`, cerut de
proprietar — sesiunea se oprește până pe 13 nov, iar fără merge ciobul ar fi rămas înghețat).
După ștergere: aceleași 13 coduri pe `izz.ro`, `izz-ro-cat-auto.andifreelancer2.workers.dev` → 404.
Dovada pilotului de mai sus rămâne valabilă. **Reluare:** fetch + rebase #568, apoi merge și
`gh workflow run deploy-worker.yml -f confirmare=deploy`, urmărit până la verde. Prima rulare
recreează Workerul din `SHARDS_LIVE`. Dacă pică la legarea rutelor (tokenul), principalul NU
se publică: revert #568 imediat, ca publicarea orară să nu rămână blocată.

**Reluat și LIVE la 2026-11-09.** #568 adus la zi cu main (fără conflicte), CI verde pe `a5b273e46`,
squash-merge `3d817ac11`. Rularea `deploy-worker` 42582355846 (push pe main) a trecut toți pașii:
„Publica cioburile live” a legat `izz.ro/auto` și `izz.ro/auto/*` (versiunea ec3a4733), deci
**riscul tokenului e închis: tokenul din GitHub are dreptul de a lega rute.** `build.json` =
`3d817ac11` pe ciob și pe principal. Sonda pe 13 adrese, înainte și după: aceleași coduri, CSP
prezent. Rămâne de măsurat în Analytics: invocările scriptului nu cresc (criteriu §4, felia 2).

## 12. Felia 3, lotul 1 — `ai`, `tech`, `cultura` (2026-11-09, confirmat pe live)

PR #569 (`feat/shard-felia-3`), CI verde pe `afc23c6d1`, squash-merge `e2d08d8be`.
Rularea `deploy-worker` `42584253451` (push pe main) a trecut toți pașii:
- `izz-ro-cat-ai` (57 fișiere, v. `dfff6819`) pe rutele `izz.ro/ai` și `izz.ro/ai/*`;
- `izz-ro-cat-tech` (150 fișiere, v. `6e300f48`) pe rutele `izz.ro/tech` și `izz.ro/tech/*`;
- `izz-ro-cat-cultura` (193 fișiere, v. `2148ab6a`) pe rutele `izz.ro/cultura` și `izz.ro/cultura/*`.
`build.json` = `e2d08d8be` pe toate cele 4 cioburi live și pe principal. Sonda pe 27 de adrese
(`f3_inainte.json` vs `f3_dupa.json`): 0 diferențe (aceleași coduri 200/307/404, Location și CSP).

## 13. Felia 3, lotul 2 — `sanatate`, `general`, `judetean` (2026-11-09, confirmat pe live)

PR #570 (`feat/shard-felia-3-lot2`), CI verde pe `632381560`, squash-merge `ff3bd0d10`.
Rularea `deploy-worker` `42587666973` (push pe main) a trecut toți pașii:
- `izz-ro-cat-sanatate` (188 fișiere, v. `e1613b53`) pe rutele `izz.ro/sanatate` și `izz.ro/sanatate/*`;
- `izz-ro-cat-general` (299 fișiere, v. `c058768e`) pe rutele `izz.ro/general` și `izz.ro/general/*`;
- `izz-ro-cat-judetean` (330 fișiere, v. `8c055b40`) pe rutele `izz.ro/judetean` și `izz.ro/judetean/*`.
`build.json` = `ff3bd0d10` pe toate cele 7 cioburi live și pe principal. Sonda pe 27 de adrese
(`f3_lot2_inainte.json` vs `f3_lot2_dupa.json`): 0 diferențe (aceleași coduri 200/307/404, Location și CSP).

## 14. Felia 3, lotul 3 — `lifestyle`, `politic`, `economic` (2026-11-09, confirmat pe live)

PR #571 (`feat/shard-felia-3-lot3`), CI verde pe `e6aa8107c`, squash-merge `c7da73f68`.
Rularea `deploy-worker` `42588777721` (push pe main) a trecut toți pașii:
- `izz-ro-cat-lifestyle` (405 fișiere, v. `7986f554`) pe rutele `izz.ro/lifestyle` și `izz.ro/lifestyle/*`;
- `izz-ro-cat-politic` (v. `4ea3d9da`) pe rutele `izz.ro/politic` și `izz.ro/politic/*`;
- `izz-ro-cat-economic` (448 fișiere, v. `fceedadb`) pe rutele `izz.ro/economic` și `izz.ro/economic/*`.
`build.json` = `c7da73f68` pe toate cele 10 cioburi live și pe principal. Sonda pe 27 de adrese
(`f3_lot3_inainte.json` vs `f3_lot3_dupa.json`): 0 diferențe (aceleași coduri 200/307/404, Location și CSP).

## 15. Felia 3, lotul 4 — `extern`, `sport` (2026-11-09, confirmat pe live)

PR #572 (`feat/shard-felia-3-lot4`), CI verde pe `26bef7b7b`, squash-merge `860de0dff`.
Rularea `deploy-worker` `42589959048` (push pe main) a trecut toți pașii:
- `izz-ro-cat-extern` (v. `1d562040`) pe rutele `izz.ro/extern` și `izz.ro/extern/*`;
- `izz-ro-cat-sport` (v. `a409f81f`) pe rutele `izz.ro/sport` și `izz.ro/sport/*`.
`build.json` = `860de0dff` pe toate cele 12 cioburi live și pe principal. Sonda pe 19 adrese
(`f3_lot4_inainte.json` vs `f3_lot4_dupa.json`): 0 diferențe (aceleași coduri 200/307/404, Location și CSP).

## 16. Felia 3, lotul 5 — `discounturi`, `regional` (2026-11-09, confirmat pe live)

PR #573 (`feat/shard-felia-3-lot5`), CI verde pe `a6624ca4d`, squash-merge `46e2d26d8`.
Rularea `deploy-worker` `42591958419` (push pe main) a trecut toți pașii:
- `izz-ro-cat-discounturi` (v. `d699d48a`) pe rutele `izz.ro/discounturi` și `izz.ro/discounturi/*`;
- `izz-ro-cat-regional` (v. `3d9b1992`) pe rutele `izz.ro/regional` și `izz.ro/regional/*`.
`build.json` = `46e2d26d8` pe toate cele 14 cioburi `cat-*` live și pe principal. Sonda pe 19 adrese
(`f3_lot5_inainte.json` vs `f3_lot5_dupa.json`): 0 diferențe (aceleași coduri 200/307/404, Location și CSP).

## 17. Felia 3, lotul 6a — `local-cifre`, `local-a`, `local-p` (2026-11-09, confirmat pe live)

PR #574 (`feat/shard-felia-3-lot6a`), CI verde pe `eb67eade9`, squash-merge `023101545`.
Rularea `deploy-worker` `42593967577` (push pe main) a trecut toți pașii:
- `izz-ro-local-cifre` (v. `88c967e6`) pe rutele `izz.ro/local/0*` .. `izz.ro/local/9*` (inclusiv paginarea `/local/2/`, `/local/3/`);
- `izz-ro-local-a` (v. `ad8ac2bc`) pe ruta `izz.ro/local/a*`;
- `izz-ro-local-p` (v. `b398755f`) pe ruta `izz.ro/local/p*`.
`build.json` = `023101545` pe toate cele 17 cioburi live și pe principal. Sonda pe 35 de adrese
(`f3_local_inainte.json` vs `f3_local6a_dupa.json`): 0 diferențe (aceleași coduri 200/307/404, Location și CSP).
