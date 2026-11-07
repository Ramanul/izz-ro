# Raport de coordonare — PR #435, #434 și costul de operare

- **Data:** 4 octombrie 2026 (UTC)
- **Ramura acestui raport:** `arena/01a1053f-izz-ro`
- **Baza locală:** `main` / `origin/main` la `0c01b21` (include #436)
**Verdict executiv:** nici #435, nici #434 nu au fost integrate. Ambele PR-uri sunt deschise și au CI verde pe SHA-urile curente, dar GitHub le raportează `CONFLICTING` cu `main`. #435 trebuie rezolvat primul; #434 se rebazează după integrarea #435. Am cerut autorilor rebase și am publicat constatările de review în comentarii.

## Răspunsul la „0 lei în orice scenariu”

**NU, nu se poate garanta literal „0 lei în orice scenariu” și disponibilitate nelimitată.** Răspunsul condiționat este: **DA, costul Cloudflare rămâne 0 lei dacă se păstrează contul pe planurile Free și consumul rămâne în cotele lor; depășirea cotelor Free nu este o continuare gratuită garantată — operațiile eșuează.** Dacă se activează Workers Paid sau alte servicii plătite, costul se schimbă; Workers Paid are un minim de **5 USD/lună per cont**.

Răspunsul de mai sus privește costurile Cloudflare ale implementării. Nu garantează prețurile viitoare sau termenii serviciilor externe de push, GitHub Actions ori alte costuri deja existente ale contului. Codul nu introduce un serviciu comercial nou, dar furnizorii de push sunt terți.

Cotele Free verificate în documentația Cloudflare:

| Resursă | Cotă Free relevantă | La depășire |
|---|---:|---|
| Workers | 100.000 invocări/zi, reset la 00:00 UTC | Cloudflare documentează Error 1027 când se atinge limita zilnică; rutele Worker nu au disponibilitate nelimitată. |
| Workers CPU | 10 ms per invocare HTTP | Invocările care depășesc limita pot eșua; performanța lotului de push nu a fost măsurată pe Worker-ul real. |
| Subrequest-uri Worker | 50 externe per invocare; separat, până la 1.000 către servicii Cloudflare | Fiecare `fetch()` extern și fiecare redirect din lanț consumă din limita externă. KV se contabilizează separat la limita serviciilor interne. |
| KV | 100.000 citiri/zi; 1.000 scrieri/zi; 1.000 ștergeri/zi; 1.000 listări/zi | Cotele se resetează zilnic la 00:00 UTC; după depășirea unei cote, operațiile de acel tip eșuează cu eroare, nu sunt facturate ca depășire Free. |
| Active statice | Cererile către active statice Workers sunt gratuite și nelimitate conform paginii de pricing | Căutarea Pagefind și majoritatea resurselor PWA sunt active statice, nu invocări Worker, dacă rămâne configurația din PR. |

Surse oficiale: [Workers limits](https://developers.cloudflare.com/workers/platform/limits/), [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) și [Workers KV pricing](https://developers.cloudflare.com/kv/platform/pricing/). Pagina KV indică explicit că limitele Free se resetează zilnic și operațiile suplimentare eșuează. Workers Paid are minimul de 5 USD/lună per cont.

### Estimarea KV pentru implementarea actuală din #434

Pentru o alertă către `N` abonați, cu lotul implicit `B=40`, în implementarea din head-ul revizuit:

- citiri: aproximativ `N + 1` pentru alertă (un `get` per abonament și un `get` al plafonului zilnic); fiecare dintre `S` abonări noi mai adaugă o citire;
- listări: `ceil(N / 40)` pentru lista de loturi, plus orice listări de stare (`/push/stare`) sau alte activități;
- scrieri: `1 + ceil(N / 40)` (cheia plafonului zilnic și o stare per lot), plus `S` abonări noi și orice alte scrieri;
- ștergeri: câte una pentru fiecare abonament expirat eliminat după răspuns 404/410; acestea au o cotă separată de 1.000/zi.

Fără abonări noi, ștergeri sau alt trafic KV în acea zi, 1.000 de scrieri permit teoretic cel mult **39.960 abonați pentru o alertă** la loturi de 40: 999 loturi × o scriere de stare + o scriere a plafonului = 1.000. Sunt și 39.961 citiri și 999 listări — sub cotele lor. Acesta este un plafon aritmetic KV, **nu** o capacitate sigură de producție: nu include alte scrieri/ștergeri, concurență, erori ale serviciului de push sau limita de 10 ms CPU. Fiecare lot folosește o invocare Worker; la 39.960 abonați sunt 999 invocări de trimitere, mult sub 100.000/zi doar dacă traficul Worker total rămas încape în cotă.

În #434, valoarea implicită 40 este sub limita de 50 subrequest-uri externe. Totuși, codul permite `LIMITA_MAXIMA = 100` și CLI-ul acceptă `--limita` până la 100; un asemenea override poate depăși limita externă Free și poate lăsa o alertă trimisă parțial după ce s-a consumat plafonul zilei. Am cerut limitarea lotului efectiv (preferabil la 40, pentru rezervă la redirecturi) și test pentru clamp. KV intern nu face ca limita externă să devină 1.000.

## Review #435 — Pagefind

**Cerut vs. livrat:** căutare statică Pagefind construită automat, suport română/diacritice, rezultate pe titlu și rezumat, filtre/sortare și highlight în titlu. Fragmentul din corp nu este livrat deliberat: generatorul elimină fragmentele Pagefind pentru a păstra bundle-ul în buget. Autorul măsoară 52 de fișiere Pagefind; acestea sunt active statice și nu adaugă citiri/scrieri KV sau invocări Worker pentru fiecare căutare.

**Teste independente, pe SHA-ul exact `c2f23a970f39e81ecf773364ced23d48e9c38e8d`:**

- `ruff check .` — *All checks passed*;
- `pytest tests/test_cautare_pagefind.py -q -p no:randomly` — **14 passed**;
- GitHub: toate check-urile/statusurile afișate sunt SUCCESS pe acest SHA.

**Stare GitHub la ultima reîmprospătare:** PR #435 este `OPEN`, ramura `arena/01a1034b-izz-ro`, `CONFLICTING` / `DIRTY` față de `main`; check-urile verzi sunt pe SHA-ul vechi, nu pe unul rebazat. Nu a fost făcut merge.

**Rebase solicitat:** după #436, conflictul relevant este în `generator/render.py`. Cererea din comentariu este să se păstreze schimbările din #436 și generarea Pagefind după scrierea HTML, înainte de metadata, apoi să se ruleze build-ul strict, verificarea indexului și CI pe noul SHA. Cu numărul live comunicat de **13.461** și +52 active Pagefind, așteptarea orientativă este **13.513 fișiere**.

**Limită observată:** în ramura care golește căutarea cât o cerere este în zbor, `static/search.js` invalidează răspunsul, dar nu resetează `aria-busy="false"`; am notat această corecție minoră, de accesibilitate, în comentariu. Nu am verificat această interfață într-un browser real sau pe preview Cloudflare.

Comentariu: [review-ul coordonatorului pentru #435](https://github.com/Ramanul/izz-ro/pull/435#issuecomment-5976762650).

## Review #434 — PWA și Web Push

**Cerut vs. livrat:** service worker/PWA și shell offline, opt-in pentru push, rute Worker, VAPID + criptare `aes128gcm`, KV, limită de o alertă pe zi, endpoint/CLI administrativ, privacy și documentație sunt prezente în diff. Testele verifică vectorul criptografic și rutele cu KV/fetch simulate; ele nu probează browser offline sau livrarea către un serviciu push real.

**Teste independente, pe SHA-ul exact `b53be6386c78a23ff023ed11f291ccd7284ddfb5`:**

- `ruff check .` — *All checks passed*;
- `pytest tests/test_pwa.py tests/test_push_criptare.py tests/test_push_rute.py tests/test_reguli.py -q -p no:randomly` — **135 passed**;
- GitHub: toate cele 10 check-uri/statusuri afișate sunt SUCCESS pe acest SHA.

Autorul declară separat un run complet de **1.935 passed, 4 skipped, 8 xfailed**; nu am rerulat independent suita completă. Nici CPU-ul real de 10 ms, nici livrarea push reală nu sunt demonstrate de testele locale.

**Stare GitHub la ultima reîmprospătare:** PR #434 este `OPEN`, ramura `arena/01a1034c-izz-ro`, `CONFLICTING` / `DIRTY` față de `main`; check-urile verzi sunt pe head-ul curent, anterior corecțiilor/rebase-ului. Nu a fost făcut merge.

**Blocaje/cereri transmise autorului:**

1. Limita CLI/API pentru lot trebuie să nu depășească plafonul de subrequest-uri externe Free; valoarea 100 nu este sigură, chiar dacă implicitul 40 este.
2. Perechea ECDH și saltul sunt generate o dată pe lot și refolosite pentru mesaje push independente. RFC 8291 §2 descrie generarea perechii/saltului la trimiterea mesajului, iar §3.1 precizează o **nouă** pereche ECDH la trimiterea unui push message. Am cerut chei/salt per abonament/mesaj, test de lot și măsurarea CPU după schimbare: [RFC 8291 §3.1](https://www.rfc-editor.org/rfc/rfc8291.html#section-3.1).
3. Binding-ul `PUSH_SUBS` este comentat în `wrangler.jsonc`. Proprietarul a comunicat că namespace-ul cu ID `4cc469142f264228942aeac7d4406aba` există; configurația din PR tot trebuie să îl lege. Secretele VAPID sunt, de asemenea, declarate de proprietar ca deja setate; nu le-am citit și nu le-am schimbat. `PUSH_ADMIN_TOKEN` este un secret distinct, a cărui prezență nu este confirmată.
4. Documentația costului trebuie corectată: nota din PR spune „10 milioane/lună” pentru Workers Free, în timp ce limita reală Free este 100.000/zi. Tabelul din `infra/PUSH-SETUP.md` prezintă o listare și o scriere pentru o alertă, dar codul listează și scrie stare per lot.

**Rebase solicitat:** după integrarea #435, rebazare pe `main` actualizat (care include #436 și #435), rezolvarea lui `generator/render.py`, activarea binding-ului KV existent, corectarea limitelor/documentației, teste noi și CI verde pe noul SHA. Nu se face merge înainte.

Comentariu: [review-ul coordonatorului pentru #434](https://github.com/Ramanul/izz-ro/pull/434#issuecomment-5976766358).

## Buget de fișiere după integrarea propusă

Folosind numărul live comunicat de **13.461** (nu l-am măsurat dintr-un deployment în acest review), plus +52 pentru #435 și +4 pentru #434:

- ambele PR-uri: **13.517 fișiere**;
- plafon intern de build de 17.000: marjă de **3.483**;
- plafonul host-ului de 20.000: marjă de **6.483**, utilizare de **67,6%**.

#436 este deja inclus în numărul de bază, deci scăderea lui nu se adună din nou. Valorile +52 și +4 provin din măsurătorile autorilor pe baza veche; totalul 13.517 este o estimare aritmetică, nu un build/redeploy combinat după rebase.

## Măsurarea traficului fără serviciu Cloudflare plătit

Există deja `.github/workflows/trafic.yml`, cu `workflow_dispatch` manual și fără cron sau dependențe instalate. Folosește `CLOUDFLARE_API_TOKEN` și `CLOUDFLARE_ACCOUNT_ID` ca GitHub Actions secrets și interoghează Analytics; nu am declanșat workflow-ul și nu am inspectat secretele. O rulare manuală nu activează un produs Cloudflare Paid și nu adaugă cost Cloudflare; consumă minute de GitHub Actions.

Pentru drepturi minime, tokenul de citire are nevoie de **Account Analytics: Read**, **Zone Analytics: Read** și **Zone: Read** (scriptul rezolvă ID-ul zonei prin REST înainte de interogarea pe căi). Dacă tokenul existent nu are aceste scope-uri, se poate crea unul read-only separat, depozitat ca GitHub secret, și ajusta workflow-ul să îl folosească. Tokenul deployment nu trebuie lărgit automat.

Instrumentul raportează invocările Worker (`workersInvocationsAdaptive`) și, separat, cererile HTTP de zonă pe căi. Interogarea Worker nu are dimensiune URL, iar raportul de zonă include și active media/statice; deci rezultatul poate orienta volumul pe rute, dar nu este o măsurare exactă a invocărilor Worker pe cale. Scriptul actual **nu măsoară operațiile KV**; pentru headroom KV trebuie consultate metricile KV din Cloudflare separat sau extins instrumentul. Nicio cifră live de trafic nu a fost colectată în această rundă.

## Acțiuni efectuate și ce rămâne

- Am citit referința `origin/arena/01a10362-izz-ro` la commitul `32b55f0`; fișierele/checklist-urile solicitate `notes/coordonator/raport.md` și `sarcini-434/435/faza0.md` nu există în arborele acelei referințe. Review-ul s-a bazat pe diff-urile, descrierile/testele PR-urilor și comentariile GitHub disponibile.
- Am reîmprospătat starea PR-urilor și am rulat testele locale țintite în worktree-uri temporare, cu dependențele PR instalate; acestea au fost eliminate după test.
- Am comentat pe ambele PR-uri, cerând rebase în ordinea #435 apoi #434 și documentând blocajele/pașii următori.
- Nu am comis, împins, rebazat, făcut deploy, declanșat workflow-ul de trafic sau integrat vreun PR. Nu am accesat valori de secrete.
- Următorul pas: aștept actualizările autorilor; după rebase verific din nou diff-ul și CI. #435 poate fi integrat primul doar când nu mai are conflicte și noul SHA are CI verde. #434 rămâne după el și nu se integrează până când sunt rezolvate limitele subrequest-urilor, cheile per mesaj, binding-ul KV și documentația, apoi noul CI este verde.
