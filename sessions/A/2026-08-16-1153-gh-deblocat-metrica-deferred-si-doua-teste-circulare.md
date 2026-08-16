# 2026-08-16, contul A — `gh` deblocat; metrica pe care se lua o decizie era greșită; două teste circulare prinse prin mutație

Continuare directă a sesiunii din 15 aug (`2026-08-15-2326-...`). Cerere: „e sesiune nouă,
rezolvă tot logic armonios și eficient", apoi „reverifică" și „verifică scheduled".

**Stare la final: `main` = `origin/main` la `991fa74e`. Suita 935 passed, 8 xfailed, 0 failed.**

---

## 1. Cel mai valoros lucru de azi e o felie NEconstruită

`specs/STATE.md` se termina cu „**Cadence is next**". M-am apucat de axa de cadență (a doua din
cele trei ale gărzii de anomalie la ingestie). Am citit spec-ul înainte să scriu cod — și scria
exact opusul:

> **Axa „cadență" a fost măsurată pe 2026-08-12 și e MOARTĂ pe datele pe care le avem.**

`python tools/registru.py find cadenta` → `IZZ-0174`, stare `masurat-fals`. Patru motive:
- intervale regulate: Rovinari e **17/21**, mai neregulat decât primăriile legitime (warez
  intercalat cu anunțuri reale, deci fluxul combinat nu e regulat)
- debit susținut: 1/70 la 9 iteme, dar #2-#3 sunt legitime la 8 → prag la 9 = curbă prin n=1
- confound: `config.MAX_PER_SOURCE = 8` plafonează, deci debitul măsurat e al programului NOSTRU
- decisiv: Cajvana are max24h = **1** → un defacement de un articol e invizibil prin construcție

Linia „next" fusese scrisă în **aceeași zi** cu măsurătoarea care o infirma. Am mutat toate cele
patru motive în `STATE.md` — spec-ul nu se citește la început de sesiune, `STATE.md` da. Axa
rămasă deschisă e **mixul tematic**.

**Lecția de proces:** un „next" într-un fișier de stare e o instrucțiune care nu expiră singură.
Registrul a prins-o, dar abia după ce începusem.

## 2. `gh` instalat de proprietar → item 3 deblocat, și poarta lui era greșită

`gh` 2.97.0, autentificat ca `Ramanul` (scopes: gist, read:org, repo, workflow).

`STATE.md` item 3 cerea: citește `stats["deferred"]` din 2-3 rulări reale **înainte** să
construiești batching-ul pentru Model C. Am citit 6, cu `gh run view <id> --log`:

```
run             fara substanta   deferred   buget folosit
31920738670           27            27         11/18
31915086605           28            28         15/18
31909820457           29           107         18/18
31898707192           30           254         18/18
```

**În cele două rulări cu buget neconsumat, `deferred` era EXACT numărul de iteme fără substanță.**
Presiune reală pe buget: zero — raportată ca „buget AI epuizat".

Cauza, în `main.py`: `process_new` scoate itemele fără substanță **înainte** de clustering și de
buget, deci nu intră în `handled`, deci cădeau în contorul de amânate. Dar ele nu se amână — revin
la fiecare rulare și sunt respinse din nou, la nesfârșit. Două mărimi opuse într-o cifră.

Presiunea adevărată, după separare: **0, 0, 78, 224**. Există, dar e mai mică decât părea.
**Decizia de batching NU s-a luat** — regula acelui item cere 2-3 rulări cu cifra reparată.

## 3. Aceeași greșeală de două ori: cod de decizie ascuns unde nu poate fi testat

### Prima: contorul
Am scris testul, a trecut. Am rulat mutația (am pus contorul vechi înapoi) — **testul a trecut și
așa**. Helper-ul din test reimplementa formula în loc s-o apeleze: verifica o copie contra unei
copii. Am scos contorul din `run()` în `numara_amanate()`, testul îl apelează, mutația pică acum
2 din 6.

### A doua: eticheta cauzei, găsită la „reverifică"
Mesajul nou compara `ai_calls >= ai_budget`. Dar `process_new` primește `budget - reserve`. Cu
rezervă > 0, apelurile nu pot atinge totalul → raportul ar fi spus „buget NEepuizat" **exact când
bugetul pentru iteme noi chiar s-a terminat**. Aceeași etichetă falsă, în cealaltă direcție.

**Nu se vedea în date:** în toate cele 6 build-uri rezerva era 0, deci ambele formule dădeau
același rezultat. Măsurătoarea nu putea infirma greșeala.

Condiția stătea **inline într-un `print`**, deci netestabilă — exact cauza de la punctul precedent,
la o oră distanță. Scoasă în `cauza_amanarii()`, trei teste, mutația (`plafon = ai_budget`) pică
exact testul care păzește rezerva.

**Tiparul, numit:** cod care ia o decizie, ascuns într-un mesaj de log. Arată ca text, se comportă
ca logică, și nu are cum să fie testat acolo unde stă.

## 4. Restul, pe scurt

- **Setul de aur +11 rânduri** (`#41-#51`), toate `judetean` de la surse **neoficiale** — singurele
  care ajung la `clasifica` în producție (`_cazuri_nivel()` exclude `pl_`/`cj_`/`pr_`, fiindcă
  `process_official` nu atinge `category`). Măsurat prin mutație (`clasifica` → mereu `local`):
  **pică 12, era 1**. Prag ridicat de la „măcar unul" la 8, verificat în ambele sensuri.
  **Patru candidați lăsați NEînghețați intenționat**, cu motivul scris: o eclipsă clasificată
  `judetean`, producția eoliană din Dobrogea, „zona seismică Vrancea" și **„Curtea de Apel
  București"** — exact clasa de substantiv compus pe care o țintește #160, deci posibil un miss viu.
- **Testul Mistral recuperat** de pe `claude/mistral-session-blocked-kn73vk` (delegat la `sonnet`).
  Nu copiere: pe ramură steagul era `PUSHED`, pe `main` aterizase ca `HAS_CHANGES`. Adaptat fără
  slăbire. Mutație: scoți `env.HAS_CHANGES` din `Open PR` → pică 1 din 4. Adăugat `/mingw64/bin`
  în PATH-ul subprocesului (pe Git-Bash `git` stă acolo); aditiv, inert pe `ubuntu-latest`.
- **`harta-data.yml` fixat pe SHA** — era ultimul fișier cu tag-uri moi, toate trei acțiunile.
  Contează fiindcă jobul are `contents: write`. SHA-ul pentru `setup-node` v7 verificat pe **două**
  endpointuri GitHub API, nu luat din raportul agentului. **CONFIRMAT ÎN CI** ulterior: rularea
  `31921976071` pe `18da4eae` a descărcat acțiunea pe SHA-ul fixat, Node v22.23.2, `node --check` a
  rulat. `grep "uses: .*@v[0-9]*$"` nu mai întoarce nimic pe tot repo-ul.

## 5. Alarma falsă care merita notată — `IZZ-0195`

Suita a dat la un moment dat **899 passed / 27 errors** în `test_sitemap_editorial`,
`test_pagination`, `test_pagina_404`. Nu era nimic stricat: **agentul și cu mine rulam suita în
paralel**, iar fixtura `output_randat` randează în același `output/`, pe care „reset output" îl
golește **fără lock**.

Dovada: aceleași fișiere rulate singure → 12 passed; suita întreagă rulată singură după → **926
passed, 0 errors**.

Docstring-ul din `conftest.py` afirma „nu există drum prin care un test să vadă jumătate din
randarea altcuiva". Adevărat într-o rulare, fals între două. Corectat, cu instrucțiunea: **verifică
întâi dacă rulează altcineva** înainte să investighezi acele erori. Agenți paraleli →
`isolation: "worktree"` (§19).

## 6. Verificat pe live / în CI (nu doar în cod)

- `https://izz.ro/instrumente/calculator-salariu/` — formula `ceil` **și** textul nou sunt acolo,
  pragul afișat 2.000 lei (nu 1.950 cel greșit). Pagina **nu** e la `/calculator/`; am ghicit greșit
  adresa și am crezut o clipă că lipsește ceva.
- Gărzile programate, toate verzi: `pipeline` 03:13, `uptime-monitor` 02:36, `smoke-live` 02:10
  (200), `visual-live` 02:01 — care raportează explicit **„OK: regresia Canvas/scroll/resize a
  trecut"** și „lista are articole (120)", deci revenirea hărții de ieri e verificată automat.
- Poarta `@claude`/`@mistralai` a sărit corect de două ori (`skipped`) pe comentarii de issue.
- **Nu există nicio sarcină programată în Claude Code** — tot ce e automat sunt cron-urile GitHub.

## 7. Ce rămâne, în ordine

1. **Decizia de batching Model C** — așteaptă 2-3 build-uri cu cifra reparată. Ultimul build a rulat
   pe `2c776929`, adică **înainte** de fix, deci acea linie de log e încă doar „verificată local".
2. **Harta, partea 2 (A1)** — retrasă ieri; ordinea de reluare e în jurnalul de ieri: gardă de
   derulare, înălțime stabilă la zoom, hit-test, confirmare **pe telefon**.
3. **Cele patru cazuri de aur** neînghețate, mai ales „Curtea de Apel București".
4. **Mixul tematic** — a treia axă de anomalie, singura rămasă reală.
5. Decizii de proprietar, vechi: E1 permalink (a zis „nu acum"), E4 axe separate, branch protection
   pe `main`, poze pe carduri, casetă separată pentru enclave pe hartă, `hold_important` feliile 2-3.
