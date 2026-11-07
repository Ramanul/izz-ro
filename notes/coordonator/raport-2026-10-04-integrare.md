# Raport de coordonare a integrării — sesiunea arena/01a10530-izz-ro

**Data:** 2026-10-04 · **Coordonator:** sesiunea curentă (predecesorul și-a închis sesiunea după #436)
**Domeniu:** #436 (merge-uit, LIVE), #435 (deschis), #434 (deschis)

---

## 0. Un lucru care trebuie spus întâi: checklisturile predecesorului NU există

Mi s-a cerut să citesc `notes/coordonator/raport.md`, `sarcini-434.md`, `sarcini-435.md` și
`sarcini-faza0.md` de pe `arena/01a10362-izz-ro`. **Niciunul nu există.** Verificat, nu presupus:

```
git fetch origin arena/01a10362-izz-ro   → OK, ramura există
git ls-tree -r FETCH_HEAD | grep -i coordonator   → (nimic)
git log --all --diff-filter=A --name-only | grep coordonator   → (nimic)
```

Directorul `notes/coordonator/` nu a fost creat niciodată, pe nicio ramură, în niciun commit
din istoricul complet (clona a fost `--unshallow`-ată ca verificarea să fie concludentă).
Autorul lui #435 ajunsese independent la aceeași concluzie și o scrisese în PR: `404` prin
API pe `ref=arena/01a10362-izz-ro`, pe `main` și pe celelalte cinci ramuri `arena/*`.

Fișierul de față este **primul** din acest director. Ce s-a putut recupera din munca
predecesorului — și ce am folosit ca intrare — sunt **comentariile lui pe PR-uri** (poziția de
integrare 2/3, cererea de confirmare a gratuității, id-ul de namespace KV). Restul îl refac eu
de la zero, din diff-uri.

---

## 1. Răspunsul la condiția „0 lei în orice scenariu": **DA**

**Da — zero lei, în orice scenariu de operare, inclusiv în scenariul de abuz.**
Motivul nu este că nu vom depăși plafoanele, ci că **pe planul Free al Cloudflare nu există
facturare la depășire**: operațiile peste plafon **eșuează cu eroare**, nu se taxează.
Nu e atașat niciun instrument de plată, deci nu există cale prin care o depășire să producă
o sumă de plată. Simptomul unei depășiri este o funcție degradată (un `503` pe abonare, o
căutare care cade pe varianta simplificată), nu o factură.

### 1.1 Plafoanele, cu numere (verificate azi pe developers.cloudflare.com)

| Resursă | Plafon Free | Ce se întâmplă la depășire |
|---|---|---|
| Workers — cereri | **100.000/zi** (reset 00:00 UTC) | cererile peste plafon eșuează; **fără taxare** |
| Workers — CPU | 10 ms per invocare | invocarea e oprită; **fără taxare** |
| Workers — active statice (cereri) | **gratuite și nelimitate**, nu consumă cele 100.000 | — |
| Workers — fișiere statice per versiune | **20.000** | deploy **refuzat**, tăcut (incidentul 2026-08-21) |
| KV — citiri | **100.000/zi** | operația eșuează cu eroare; **fără taxare** |
| KV — scrieri | **1.000/zi** | idem |
| KV — ștergeri | **1.000/zi** | idem |
| KV — operații `list` | **1.000/zi** | idem |
| KV — stocare | 1 GB | idem |

**Plafonul de `list` (1.000/zi) lipsea din întrebarea pusă de predecesorul meu autorilor** și
este, pentru #434, cel care se atinge primul. L-am adăugat în calcul.

### 1.2 #435 (Pagefind): consum de rulare **exact zero**

Tot ce adaugă — bundle-ul `/_pagefind/*` (52 de fișiere) și `search-index.json` (2,04 MB brut /
683 KB comprimat) — sunt **active statice**. Cererile către active nu consumă plafonul de
100.000 de invocări (`specs/cloudflare-free-2026-09.md` §1, nota 3 din pricing). Zero
invocări de Worker, zero KV, zero servicii terțe, zero chei. Singura resursă atinsă este
**bugetul de fișiere**, iar acolo avem marjă (§2).

### 1.3 #434 (PWA + Push): singurul consum real, cuantificat

Abonările și trimiterea alertelor sunt operații de Worker + KV. Calculul meu, din citirea
lui `infra/push.js`:

| operație | consum | plafon atins la |
|---|---|---|
| abonare nouă | 1 citire + **1 scriere** KV | **1.000 dispozitive noi/zi** |
| re-abonare (același endpoint) | 1 citire, **0 scrieri** (`if (await kv.get(id)) return`) | practic nelimitat |
| dezabonare | 1 ștergere | 1.000/zi |
| 1 alertă către N abonați | `N+1` citiri · `⌈N/40⌉` `list` · `1 + ⌈N/40⌉` scrieri | **~40.000 abonați/zi** (1.000 `list` × lot de 40) |
| 1 alertă către 5.000 abonați | 5.001 citiri (5%) · 125 `list` (12,5%) · 126 scrieri (12,6%) | confortabil |
| navigare a unui vizitator cu PWA instalat | **1 invocare de Worker** (`run_worker_first` pe `/sw.js`) | **~100.000 navigări/zi** |

Observații de review, ambele transmise autorului pe PR:
- raportul de stare (`kv.put(CHEIE_STARE)`) se scrie **la fiecare lot**, nu o dată per alertă:
  125 de scrieri în loc de 1 la 5.000 de abonați. Nu e blocant, dar arde 12,6% din plafonul
  zilnic de scrieri pe o valoare oricum suprascrisă.
- protecția contra golirii plafonului de scrieri de către un terț este **economică**
  (validarea endpointului contra serviciilor de push cunoscute + re-abonarea fără scriere),
  **nu criptografică**. Web Push nu oferă dovada de posesie a endpointului. Risc rezidual
  asumat; simptomul e `503`, nu cost.

### 1.4 Singura necunoscută rămasă

**Traficul real nu a fost măsurat niciodată** — `tools/trafic_cloudflare.py` cere un token
Cloudflare și nu a rulat (notat și în `notes/plan-master-izz-2026-10-03.md`). Nu știm cât de
departe suntem de 100.000 de invocări/zi. Nu schimbă răspunsul „0 lei" (depășirea nu costă),
dar schimbă răspunsul la „rămâne site-ul funcțional". Am cerut autorului lui #434 să propună
activarea măsurătorii cu un token **read-only pe Analytics**, gratuit.

---

## 2. Bugetul de fișiere, recalculat pe cifrele LIVE (nu pe baza veche)

Ambele PR-uri își calculează marja față de baza **14.483**, dinainte de #436. Pe live, după
#436: **13.461** (`build.json`). Recalculat:

| stare | fișiere | % din 20.000 |
|---|---|---|
| main azi (post-#436, LIVE) | 13.461 | 67,3% |
| + #435 (bundle fără fragmente, +52) | 13.513 | 67,6% |
| + #434 (+4: `sw.js`, `offline/index.html`, `pwa.js`, `push.js`) | **13.517** | **67,6%** · marjă **6.483** |

Ambele PR-uri intră cu marjă mai mare decât credeau autorii. Varianta Pagefind **cu**
fragmente (+9.458) ar fi dus la ~22.919 — peste plafon, deploy refuzat: decizia autorului
lui #435 de a șterge `fragment/` rămâne obligatorie, nu opțională.

---

## 3. Review-ul, pe fond

### 3.1 Conflictele: unul singur, mecanic, în ambele cazuri
`git merge-tree main <branch>` → conflict **exclusiv** în `generator/render.py`, pentru
amândouă. Restul se auto-merge-uiește (inclusiv `.github/workflows/build.yml` la #435).
Zonele atinse sunt disjuncte ca intenție:
- **#435**: coada lui `build()` (apelul indexului înainte de numărătoare), `_write_search` /
  `_write_search_index` (nou), bloc în `_write_headers`;
- **#434**: `_copy_static()` / `_write_sw()`, pagina `/offline/`, `_asset_ver`, bloc în
  `_write_headers`.

Singura suprapunere e `_write_headers`, iar regulile sunt aditive și compatibile
(`/sw.js` vs `/_pagefind/*`). **Nu e un conflict de arhitectură.**

### 3.2 Constatările Gemini pe #434: toate 5 sunt **false pozitive**, închise de mine
Verificate pe sursa reală, nu pe diff-ul trunchiat la 120.000 de caractere care le-a produs:

| constatare | verdict |
|---|---|
| `push.js:497` — `mesaj` nedeclarat | **fals**: `const mesaj` la 507, folosit la 538, aceeași funcție |
| `worker.js:45` — oglinda fără default export | **fals**: `infra/worker-404-mirror.js:96` are `export default {` |
| `test_push_rute.py:373` / `test_push_criptare.py:139` — fișiere trunchiate | **fals**: `ast.parse()` trece pe ambele |
| `push.js:450` — stare KV inconsistentă | **fals ca ERROR**: scrierea plafonului **înainte** de trimitere e deliberată — greșește în direcția „maxim una pe zi" |

Pe #435, Gemini n-a avut nicio constatare.

### 3.3 Ce accept explicit ca risc
- **#435**: fără excerpt din corpul articolului (marcaj doar în titlu) — plafonul de fișiere
  impune forma; documentat în spec §9. Nu s-a apăsat într-un browser real, dar drumul de
  cădere e proiectat (`build.json.search.ok=false` + notice în pagină) și nu poate îngheța
  site-ul.
- **#434**: nicio alertă n-a plecat prin FCM/Mozilla; conformitatea criptografică e dovedită
  pe vectorul RFC 8291 §5 + Anexa A (test care a prins un bug real — octetul NUL lipsă din
  `cek_info`/`nonce_info`, fără de care **nicio** notificare n-ar fi fost decriptabilă).
  Prima alertă reală se trimite cu `--uscat` întâi.

---

## 4. Ordinea de integrare și starea

**#435 → apoi #434**, fiecare doar după CI verde **pe commitul rebazat** și după re-rularea
numerelor de buget.

| PR | review uman | CI | conflict | blocant rămas |
|---|---|---|---|---|
| #435 | **aprobat pe fond** | 10/10 verde pe `c2f23a97` | `render.py` | rebase pe main post-#436 |
| #434 | **aprobat pe fond** | 10/10 verde pe `b53be638` | `render.py` | rebase pe main post-#435 · **decomentare bloc KV cu id-ul real** · propunere măsurare trafic |

Rebase-ul l-am cerut **autorilor**, prin comentarii pe PR-uri (ei au acces GitHub și contextul
deciziilor din codul lor). Nu-l fac eu. Verific după, pe:
1. CI verde pe commitul de după rebase;
2. `mergeable: MERGEABLE`;
3. linia de buget din `--render-only` — **13.5xx, nu 14.5xx** (dacă e 14.5xx, rebase-ul n-a prins #436);
4. pentru #434: `wrangler.jsonc` conține `"id": "4cc469142f264228942aeac7d4406aba"`, **decomentat**.

### Blocantul de configurare pentru #434
Namespace-ul KV `PUSH_SUBS` **există** (id `4cc469142f264228942aeac7d4406aba`, gratuit) și
secretele VAPID sunt **deja setate** pe worker. Blocul `kv_namespaces` din `wrangler.jsonc` e
însă încă **comentat** — motivul original (un id placeholder face deploy-ul să pice) a
dispărut. **Dacă merge-uim așa, livrăm o funcție care răspunde `503` la `/push/abonare`.**
Decomentarea cu id-ul real este condiție de merge, nu curățenie de după.

---

## 5. Comentarii postate

- #435 → https://github.com/Ramanul/izz-ro/pull/435#issuecomment-5976627323
- #434 → https://github.com/Ramanul/izz-ro/pull/434#issuecomment-5976631246
