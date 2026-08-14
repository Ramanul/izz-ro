# Recensământ de predare — 2026-08-14, seara (cont B)

> Cerut de proprietar: „reverifică toate lucrurile nefăcute în toate sesiunile și pregătește
> totul pentru predare". Tot ce urmează e **verificat azi**, cu comanda alături — nu copiat din
> predarea precedentă. Unde n-am putut verifica, scrie explicit ce lipsește ca să se poată.
>
> Fișierul ăsta e **de citit o dată** de sesiunea care reia firul, apoi de actualizat sau șters.
> `specs/STATE.md` rămâne sursa de adevăr pentru „unde suntem"; ăsta e inventarul de sub el.

## 1. Cele 57 de ramuri neintegrate — de ce nu se poate da un verdict ieftin

Predarea precedentă zicea „58 de ramuri, propun o felie care le marchează aterizat / mort /
de recuperat". Am încercat s-o fac aici. **Trei obstacole măsurate, care explică de ce metodele
ieftine dau răspunsuri false — cine reia treaba să nu le redescopere:**

1. **Nu există bază de îmbinare.** `git merge-base origin/main origin/fix/deducere-personala-transe`
   → **gol**, iar `git diff main...branch` răspunde `fatal: no merge base`. Istoria lui `main` a
   fost rescrisă la un moment dat, deci ramurile astea sunt pe rădăcini diferite. **Orice
   comparație în trei puncte e inutilizabilă.**
2. **`main` folosește squash-merge.** Subiectul commit-ului de pe ramură nu mai apare în `main`
   (devine titlul PR-ului), deci „caut subiectul în `git log main`" dă fals-negative. Testat:
   `claude/mistral-work-session-wlsgks` iese „NEATERIZAT" deși a intrat acum o oră ca #179.
3. **Commit-urile botului de conținut înghit logurile** — sute de „update content" între
   commit-urile de muncă, pe fiecare ramură.

**Metoda care chiar funcționează, și e singura:** pentru fiecare ramură, citești commit-urile ei
de muncă, iei artefactul pe care îl introduc (o funcție, un fișier, o linie de config) și
**verifici artefactul în codul de azi**. E per-ramură, nu se poate automatiza credibil, și e
felia separată pe care predarea precedentă o cerea. Rămâne cerută.

**Ce am verificat totuși aici, prin artefact — 9 ramuri, toate ATERIZATE:**

| Ramură | Artefact verificat azi | Verdict |
|---|---|---|
| `ci/ruff-gate` | `ruff.toml` există + pasul `ruff check` în `tests.yml` | aterizat |
| `claude/feedcheck-real-fetcher` | `tools/feed_check.py:32` importă `generator.fetch._fetch_one_guarded` | **aterizat** |
| `oc/free-fallback-routes`, `oc/auto-fallback-runner` | `tools/oc_run.sh` + 12 rute în `opencode.json` | aterizat |
| `claude/harta-surse` | `templates/surse.html` conține harta | aterizat |
| `claude/nota-harta` | `generator/guard.py:301 def anomalie` | aterizat |
| `feat/sitemap-editorial` | `tests/test_sitemap_editorial.py` | aterizat |
| `claude/session-tzvmth` | butonul PWA + `preload` în `templates/base.html` | aterizat |
| `a/liternet-feed-url` | `config.py:23` → `https://feed.liternet.ro/agenda.xml` | **aterizat** |

**Consecința care contează:** ramurile astea pot fi șterse fără pierdere, iar **angajamentul
neonorat din `TASKS-B.md` (24 iulie) — „rulez `feedcheck.yml` pe `claude/feedcheck-real-fetcher`
înainte de merge" — e mort de drept: munca e deja pe `main`.** Nu-l mai reprograma.

**Singura ramură verificată ca NEATERIZATĂ și încă utilă: `fix/deducere-personala-transe`** (§3).

## 2. PR-uri deschise — verdict pe fiecare

| PR | Stare azi | Ce am făcut / ce trebuie |
|---|---|---|
| #180 lint | **merged** `f5ec83b1` | deblochează CI-ul pentru toate |
| #179 predarea contului B | **merged** `003b5347` | — |
| #169 codeql-action (SHA) | **merged** `a104c020` | — |
| #181 fix `@mistralai` + predare | CI verde, de făcut merge | vezi §4 |
| **#170** claude-code-action → SHA nou | **deschis, deliberat** | singurul PR care schimbă cod terț rulat cu `contents: write` și tokenul proprietarului. SHA-ul actual a fost citit și verificat la `IZZ-0189`; unul nou anulează verificarea. **Cere un review nou al SHA-ului, nu un merge.** |
| **#171** setup-node v4→v7 | **deschis, deliberat** | pe tag, nu pe SHA, salt de 3 majore, și nu se poate valida fără să rulezi `harta-data.yml`, care are `contents: write` și scrie datele hărții. |
| **#163** deducere personală | **deschis, de rezolvat altfel** | §3 |

## 3. PR #163 — corectură la ce spuneau și `STATE.md`, și predarea precedentă

Ambele ziceau „probabil redundant, a aterizat prin `5dc92ca7`". **Fals**, verificat linie cu linie
față de `static/calc-salariu.js` de pe `main`:

- **`main` folosește `floor((brut − minim)/50)`; tabelul din art. 77 cere `ceil`.** La brut =
  minim + 10 lei legea dă 19,5%, `main` dă 20% — **o tranșă prea generos**, corect doar pe
  multiplii exacți de 50.
- **`main` n-are plafonul de la alin. (2)** („în limita venitului impozabil lunar realizat"),
  deci sub ~1.331 lei brut afișează o deducere mai mare decât venitul rămas după contribuții.

Efectul în bani e mic (impozit mai mic cu ~2 lei), dar cifra afișată e greșită, pe o pagină
publică, într-un calcul fiscal. **Nu merge PR-ul ca atare** (baza lui e din 8 august și se
suprapune peste codul de acum) **și nu-l închide ca redundant.** Felia corectă: `floor`→`ceil`
plus plafonul alin. (2) pe codul de azi, păstrând citarea din #163. Decizie de proprietar.

## 4. `@mistralai` — conectat, cu un defect real reparat azi

Verificat pe `main` și pe GitHub: workflow propriu (nu `obledev`), poartă
`author_association ∈ {OWNER, COLLABORATOR}`, secret `MISTRAL_API_KEY`, label `mistral`,
body-uri prin ENV (fix-ul de injecție #177). Toate în picioare.

**Dar din 28 de rulări, ultimele două reale erau roșii**, iar `SESSION-2026-08-14.md` spunea doar
„testat end-to-end". Cauza, din logul `31788232683`: când `vibe` nu schimbă niciun fișier, pasul
de commit face `exit 0` — care **iese din pas, nu din job** — deci ramura nu ajunge pe remote,
iar `Open PR` rula oricum și cerea un PR pe o ramură inexistentă
(`No commits between main and mistral/issue-175-…`). Rezultat: job roșu și
„❌ @mistralai a eșuat" pe issue, pentru un succes fără modificări.

Reparat în #181 (steag `PUSHED` + `tests/test_workflow_mistral_pr_gate.py`, care rulează
scriptul real al pasului; verificat prin mutație). **Confirmarea pe viu se face cu un `@mistralai`
real după merge** — până atunci, calea reparată e „verificată local", nu „confirmată pe live".

## 5. Issue-uri deschise — unul singur, și ambele lui blocaje sunt rezolvate

**#83 „Canal live de coordonare A ↔ B"** (marcat „nu închideți"). Cele două blocaje concrete din
corpul lui, re-verificate azi:

1. „branch `a/liternet-feed-url`, deschide PR + dispatch `feedcheck.yml`" → **URL-ul e deja pe
   `main`** (`config.py:23`). Blocaj mort; ramura poate fi ștearsă.
2. „issue #82, gunoi de la un test, închide-l tu" → **deja închis** (nu apare în lista deschisă).

Issue-ul rămâne deschis ca infrastructură de canal, nu ca sarcină.

## 6. Muncă nesalvată prin sesiuni — ce s-a putut stabili și ce nu

- Sesiunile de hartă de azi **și-au comis munca pe `main`** între 17:54 și 19:25.
- `fix/harta-lista-rezultate` (ramura celor trei sesiuni arhivate) e **integrată complet**:
  `git log origin/main..origin/fix/harta-lista-rezultate` e gol.
- **Ce NU se poate verifica din cloud:** `ListAgents` întoarce „No reachable agents". Sesiunile
  de pe mașina proprietarului („bridge") nu-mi sunt accesibile — nici transcript, nici working
  tree. Dacă **„Final cleanup and mobile map functionality"** (activă la 19:45, după ultimul
  commit de la 19:25) are ceva necomis, **singurul mod de a afla e un `git status` acolo.**
- **Cauza blocajelor de sesiune e cota, nu un defect:** plafonul de 5 ore a respins sesiunea
  Mistral la 18:07 (reset 19:30), iar cota săptămânală era pe `allowed_warning`. Zece sesiuni
  deschise pe același repo într-o zi consumă același buget.

## 7. Elemente deschise din `STATE.md`, re-verificate azi

| Element | Verificare de azi | Stare |
|---|---|---|
| **A1** — 24 din 42 județe sub 44px pe mobil, bulinele ~11,7px | rămâne decizie de proprietar pe abordare (buline mai mari / hit-area invizibilă / fără tap direct pe mobil) | **deschis, decizie** |
| **E5** — setul gold crescut la ~150 + poartă CI | `specs/gold-geo-2026-08-08.tsv` are **41 de rânduri** | **deschis, muncă** |
| **E1** — permalink decuplat de categorie | `specs/atribuire-cercetare-si-plan.md` C5 „deschis"; blochează orice corecție retroactivă | **deschis, decizie** |
| **E3 / E4** — scor de focus în loc de `max()`, axe separate temă/loc | neatinse | **deschise** |
| Axa **cadență** din garda de ingestie | `specs/securitate-ingestie.md:185` — **măsurată pe 12 aug și declarată MOARTĂ pe datele actuale**. Predarea precedentă zicea „cadence is next" — nu mai e. | **închis, nu redeschide** |
| **Y** — `state.merge()` cod mort | re-verificat a treia oară; a-l „repara" e refactorizare oportunistă (§5.6) | **nu atinge** |
| `sessions/README.md` | **lipsește** în continuare, deși `/handoff` trimite la el | mic, nefăcut |

## 8. Ce urmează, în ordinea în care merită făcut

1. **Merge #181** (fix `@mistralai`), apoi **un `@mistralai` real** ca să confirmi pe viu.
2. **Felia fiscală** din §3 — mică, verificabilă, pe o pagină publică.
3. **#170** — review al noului SHA de `claude-code-action`, cu ochii pe `checkWritePermissions`
   și `checkHumanActor`; abia apoi merge.
4. **Felia de curățenie a ramurilor** — cu metoda din §1 (artefact, nu diff), și ștergerea celor
   confirmate aterizate. Cele 9 din tabel sunt deja gata de șters.
5. **E5** — setul gold de la 41 la ~150 de rânduri, apoi poarta CI.
6. **A1** și **E1/E4** — decizii de proprietar, nu muncă de sesiune.
