# 2026-08-15, contul A — inventarul taskurilor din toate sesiunile; un bug de bani găsit din întâmplare; A1 aterizat și revenit

Cerere: „fă inventarul taskurilor neterminate sau neîncepute din toate sesiunile și rezolvă-le pe
toate, începând pe secvențe logice, armonioase, eficiente". Apoi, pe parcurs: „deleagă cele simple
lui haiku, cele medii lui sonnet, cele complexe le faci tu", și mai târziu „caută bune practici și
rezolvă" + „fă cum crezi tu că e mai fiabil".

**Starea la final: `main` = `origin/main` la `fc289c97`. Suita 900 passed, 8 xfailed. Harta e pe
codul de dinainte de A1, confirmat de proprietar pe telefon.**

---

## 1. Inventarul — 4 din taskurile „deschise" erau deja făcute

Surse citite: `TASKS-A.md`, `TASKS-B.md`, `TASKS-MISTRAL.md`, `specs/STATE.md`, `handoff/`.
`handoff/to-A/` e **gol** — nimic în așteptare de la contul B.

**Toate cele 4 taskuri din `TASKS-MISTRAL.md` erau gata, nebifate.** Taskurile 1-3 sunt în
`.github/workflows/mistral.yml` (garda anti-push pe `main` cu `abbrev-ref`, `uv tool install
mistral-vibe==2.24.1`, marcajul `HAS_CHANGES`). Task 4 era „rulează și raportează" — l-am rulat:
suita verde, `--render-only` 2749 articole.

**Închise prin verificare, fără cod:**
- `tools/feed_check.py:32` importă `_fetch_one_guarded` din `generator.fetch` — deci angajamentul
  din 24 iulie de a valida `claude/feedcheck-real-fetcher` înainte de merge e **caduc**. Îl găsisem
  scris în mesajul commitului `c269e8a7` de pe o ramură, dar l-am verificat în cod, nu pe încredere.
- `liternet` are URL valid în `config.py` (`https://feed.liternet.ro/agenda.xml`).
- Nota din `STATE.md` despre „10 erori preexistente în `test_sitemap_editorial.py`" e **învechită** —
  suita e curată.

**`gh` nu e „neautentificat", nu e instalat deloc** (`which gh`, `where.exe gh`, `C:\Program Files\
GitHub CLI\` toate goale). Instalarea a eșuat cu MSI 1602 — cere shell elevat. Rămâne acțiune de
proprietar; blochează item 3 (Model C batching), care are nevoie de `stats["deferred"]` din logurile
Actions.

## 2. Delegare — ce a mers și ce nu

| Executant | Task | Rezultat |
|---|---|---|
| `haiku` | `requirements-dev.txt` | OK (pytest/ruff/pytest-randomly nu erau nicăieri în repo) |
| `haiku` | instalat `gh` | EȘEC — cere drepturi de administrator |
| `sonnet` | triaj 67 ramuri remote | OK — 55 aterizate, 8 moarte, 4 de recuperat |
| `sonnet` | verificat PR #163 | OK — **a găsit un bug real** |

Agenților li s-a interzis explicit `checkout`/`stash`/`switch`/`reset` (repo folosit în paralel).
Triajul a arătat că **`git cherry` singur e insuficient**: a dat „neaterizat" pentru 29 din 67, iar
verificarea conținutului din `main` a răsturnat verdictul pentru 25 — cod aterizat rescris, nu
cherry-pick-uit.

## 3. Bugul care contează: calculatorul de salarii afișa cifre greșite

Ieșit din verificarea PR #163, nu era pe nicio listă.

`static/calc-salariu.js` folosea `Math.floor((brut - salariuMinim) / 50)`. Tabelul din **art. 77
alin. (4)** deschide fiecare tranșă la **+1 leu**, nu la +0:

```
salariul minim                          20,00%
salariul minim + 1 leu   ... + 50 lei   19,50%
salariul minim + 51 lei  ... + 100 lei  19,00%
```

Cu `floor`, un brut de minim+1 leu primea 20,00% în loc de 19,50% → deducere prea mare → impozit
prea mic → **net afișat mai mare decât cel real**. Cele două formule coincid doar pe multiplii
exacți de 50, deci greșeala lovea **49 din 50** de salarii posibile.
Sursa: https://www.noulcodfiscal.ro/titlu-4/capitol-3/articol-77.html

Adăugat și plafonul din **alin. (2)** (deducerea ≤ venitul impozabil), absent complet: la brut sub
minim se afișa „Deducere personală: 865 lei" peste un venit impozabil de 650.

**Testele nu reimplementează formula** — ar fi verificat copia contra copiei. Extrag blocul de calcul
din `.js`-ul livrat cu regex și îl rulează **în node**, rând cu rând contra tabelului din lege.
Mutație `ceil`→`floor`: 5 pică, exact pe deschiderile de tranșă.

**`STATE.md` credita `5dc92ca7`, care e un commit ORFAN** — `git branch --all --contains` gol,
`git fsck --unreachable` îl listează. Cel real e `2d0df92f` (mesaj identic, 4h mai târziu; push
respins, refăcut). Corectat în `STATE.md`.

## 4. `hold_important` — steag mincinos, acum poartă reală

Documentat în `moderation.yaml` ca „clusterele C așteaptă aprobare înainte de publicare"; tot ce
făcea era un `print` la `main.py:359`. Poarta stă acum în `moderation.apply` — singurul loc care
rulează **și** pe build complet **și** pe `--render-only`. Aprobarea: lista nouă `approved`, același
tipar ca `blocklist_urls`, editabilă din browser pe GitHub. Reținerea vine **ultima** în cascadă:
un articol blocat e respins, nu „în așteptare".

Măsurat: `true` → **451 sinteze C reținute**, output 2749 → 2427. Mutație: poarta scoasă → 4 teste pică.

**Domeniul neacoperit, scris explicit:** când o sinteză C e reținută, articolul B din spatele ei
iese în locul ei — de-aia scăderea e 322, nu 451. Poarta ține *sintezele*, nu tot conținutul AI.
Proprietarul a ales doar felia 1; coada de review și jurnalul de aprobări rămân nefăcute.

## 5. A1 — trei încercări, două fundături, revenire finală

### Încercarea 1 (retrasă în aceeași sesiune)
Colecta toate potrivirile la un „inel" care crește, apoi departaja după mărime. **Nu merge:** la
același pas poate potrivi și un județ depărtat, iar departajarea îl alegea pe el în locul celui care
chiar conținea punctul. Centrul Clujului → Sălaj.

### Încercarea 2 (după căutarea de bune practici)
Convenția din bibliotecile de hărți (OpenLayers `forEachFeatureAtPixel`, Leaflet cu SVG): **ordine
ascendentă după mărime, câștigă prima potrivire** — echivalentul testării de sus în jos prin stiva de
randare, cu formele mici deasupra. Modul de eșec de la încercarea 1 devine imposibil.

Plus: **poligoanele înaintea bulinelor**. Cât timp `closestHit` era primul, pasul pentru județe mici
nu se executa niciodată pentru exact perechea pentru care fusese scris — bulinele București/Ilfov
sunt la ~4px una de alta.

**Plafonul de furt, măsurat:** 44px e geometric imposibil pentru o enclavă de 8,6px fără să-i
distrugi vecinii (Bucureștiul ar cere 17,7px/parte, vecinii au 8-11px adâncime). Baleiat
22/14/10/8/6/4/3px. Criteriul care contează e **suprafața utilă**, nu un punct per județ:

```
Bucuresti  59 -> 448px² (x7,6)    Ilfov 323 -> 549px² (x1,7)
Calarasi 1511 -> 2010 · Dambovita 1057 -> 1676 · Ialomita 985 -> 1083
Cluj 1502 -> 1073 · Giurgiu 1361 -> 1086 (-20..29%, raman >1000px²)
```

Verificat 40/42 în browser real la 375px. A aterizat ca `bf55ae9f` + `ab4dd8b8`.

### Două capcane de test care m-au costat mult
1. **Nu testa cu centrul casetei.** Centrul casetei Clujului cade la **3,9px de granița cu Sălajul**
   (Cluj e alungit). A fabricat „regresii" inexistente. Punctul corect e cel mai depărtat de propriul
   contur (pol de inaccesibilitate, aproximat pe grilă).
2. **Verifică resetarea între atingeri.** Primul harness dădea rezultate dintr-o hartă rămasă mărită,
   fără să semnaleze. Al doilea verifică `!judet && .map-back.hidden` înainte de fiecare tap și
   returnează `RESET-ESUAT` altfel.

Tot din harness: **aplicația întinde viewBox-ul pe toată pânza** (`canvas.width / view.width`), fără
centrare. Calculam cu `min()` + offset-uri de centrare inexistente.

### Revenirea (`c6397735`)
Proprietarul a raportat pe telefon că **harta se dedublează din nou** — simptomul A2, reparat pe
12 aug. `ensureCanvas` e **intact**, deci cauza veche nu a revenit. Dar singurul cod care a atins
`static/harta-stiri/*.js` de atunci erau commiturile mele, iar live-ul le avea.

**Mecanism plauzibil, neobservat:** zonele mărite fac ca o atingere accidentală în timpul derulării,
care înainte nu nimerea nimic, să selecteze un județ → `applyState` → `buildMap()` recalculează
`canvas.style.height` după raportul noii vederi → **canvasul își schimbă înălțimea în mijlocul
gestului**. Garda tap-vs-drag de 10px nu acoperă cazul.

**Am revenit în loc să peticesc fiindcă NU POT VERIFICA.** Artefactul nu apare headless sau cu scroll
emulat — diagnosticul din 12 aug a cerut filmare de pe telefon + OpenCV. Un fix pe care nu-l pot
vedea eșuând ar fi însemnat „reparat" fără să văd simptomul dispărând (§16).

**Cauzalitatea e CONFIRMATĂ:** după ce revenirea a ajuns pe live, proprietarul a reverificat pe
telefon — dedublarea a dispărut. O variabilă schimbată, simptomul a urmat-o în ambele sensuri.
Mecanismul rămâne nedovedit; responsabilitatea feliilor de hit-test, nu.

**Ordinea corectă la reluare:** (1) gardă de derulare, (2) înălțime de canvas stabilă la zoom,
(3) abia apoi hit-testul, (4) confirmare **pe telefon**, nu de la birou.

## 6. Ce a supraviețuit din A1 și e pe live

Selectorul de județe: butoanele erau **36px**, acum `min-height:44px` + `inline-flex`. CSS pur pe
butoane DOM sub hartă, nu atinge canvasul. Verificat: 41 butoane, toate 44px, 0 cu text tăiat,
click pe „BUCURESTI" selectează București.

**E răspunsul mai bun la nevoia din A1:** Bucureștiul e desenat la 8,6px și nu poate ajunge la 44px
pe canvas fără să-și înghită vecinii — dar în selector are un buton real de **123×44px**, cu
`aria-pressed`, navigabil din tastatură.

**Fals alarmă verificată:** am crezut că pagina hărții n-are cache-busting (`?v=`) și că fixurile
n-ar ajunge la utilizatori. E deja rezolvat — `render.py:1218` scoate `/static/harta-stiri/*` din
regula `immutable` de 30 de zile și îi pune `max-age=300, must-revalidate`, cu tot cu explicația
despre cum Cloudflare unește headerele și de ce e nevoie de `!`. Confirmat pe live.

## 7. Ce rămâne deschis

- **`gh`** — `winget install --id GitHub.cli -e` din PowerShell ca administrator, apoi `gh auth login`
  (OAuth interactiv, doar proprietarul). Deblochează Model C batching.
- **A1 reluat**, în ordinea de la §5.
- Cadența ca a doua axă de anomalie · E3 focus score · E5 setul de aur la 150 · Cernavodă/rază
  națională · `tests/test_workflow_mistral_pr_gate.py` de recuperat de pe
  `claude/mistral-session-blocked-kn73vk` · 2 bump-uri dependabot.
- Decizii de proprietar: E1 permalink (a zis „nu acum"), E4 axe separate, branch protection pe `main`,
  poze pe carduri, casetă separată pentru enclave pe hartă.

## 8. Ce am greșit, ca proces

Am aterizat pe `main` o schimbare de **interacțiune tactilă** verificată doar de la birou, pe o clasă
de bug despre care fișierul propriu al proiectului spunea că se vede doar pe dispozitiv real.
Măsurătorile mele erau corecte și irelevante: măsurau ce se întâmplă la un *click*, nu ce se întâmplă
în timpul unei *derulări*. Tiparul: am tratat „verificat pe axa pe care știu s-o măsor" drept
„verificat".
