---
description: Checkpoint de predare între conturile Claude — scrie jurnalul sesiunii, actualizează STATE.md, listează WIP-ul necomis și face push, ca celălalt cont să poată continua doar din fișiere.
argument-hint: [opțional: notă scurtă despre ce urmează]
---

Rulezi handoff-ul între conturi. Notă de la utilizator despre ce urmează: **$ARGUMENTS**

Scopul: după comanda asta, **celălalt cont trebuie să poată relua firul citind doar fișiere** —
fără transcript, fără să fi fost de față. Nu e o comandă de „final de sesiune": se rulează și la
mijloc, în special când alerta de consum (`usage-alert.ps1`, prag 75%) semnalează că mai ai buget
cât să scrii, dar poate nu cât să termini.

**Regula care le acoperă pe toate: pushează devreme și des.** Presupune că sesiunea se poate opri
la orice pas — pentru că exact asta o declanșează. Nimic din ce ai scris nu are voie să stea doar
pe disc cât timp mai ai de scris altceva (vezi pasul 3a și motivul din spate).

## 0. Determină pe ce cont rulezi

- Ai acces la `C:\Users\cw_26\` sau `C:\claude desktop\` → **contul A** (aplicația desktop, local).
- Nu ai → **contul B** (browser / Claude Code web, cloud).

Nu ghici. Verifică cu un `ls`. Contul decide în ce director scrii jurnalul: `sessions/A/` sau `sessions/B/`.

## 1. Inventariază starea reală — nu din memorie

Rulează `git status --short` și `git log --oneline -5` în **fiecare** repo atins în sesiune
(tipic `C:\claude desktop` și, dacă ai lucrat la izz, `C:\claude desktop\izz`).

Separă explicit trei categorii:
- ce e **comis** (intră în jurnal ca hash + mesaj),
- ce e **necomis și e al tău** (îl comiți la pasul 6),
- ce e **necomis și e WIP-ul utilizatorului** — vezi secțiunea „User WIP — UNTOUCHABLE" din
  `izz/specs/STATE.md`. **Nu-l comite, nu-l face stash, nu-l stage-ui.** Îl LISTEZI în jurnal,
  cu avertismentul că celălalt cont nu-l vede deloc pe remote.

## 2. Citește ultimul jurnal din directorul tău

`ls -t sessions/<A|B>/ | head -1`, apoi citește-l. Scrii **doar ce s-a întâmplat după el**.
Nu rescrie istorie deja jurnalizată — trimite la ea cu numele fișierului.

## 3. Scrie jurnalul — schelet întâi, **pushat imediat**, abia apoi îmbogățit

Ordinea contează mai mult decât conținutul, și e contraintuitivă: **push înainte de calitate.**

Pe 2026-08-02 contul B a scris un jurnal de 198 de linii și a rămas fără credit **înainte de
push**. Fișierul a existat doar în sandbox-ul cloud și s-a pierdut integral; `sessions/B/` avea
în continuare doar `README.md` pe origin. Un jurnal scris și nepushat **nu e un jurnal parțial,
e zero** — cu agravanta că cel care l-a scris crede că a predat. Iar momentul în care rulezi
handoff-ul e fix momentul în care poți rămâne fără buget la jumătatea frazei.

Deci în două treceri, nu într-una:

**3a. Schelet minim, comis și pushat în aceeași trecere.**
`sessions/<A|B>/YYYY-MM-DD-HHmm-slug-scurt.md`, cinci-zece linii brute care răspund la: ce s-a
cerut, ce a aterizat (hash + mesaj), ce e necomis, ce a rămas deschis. Fără șlefuire, fără
formatare, fără să recitești. Apoi, **imediat**, fără să te apuci de altceva între timp:

```bash
git add sessions/<A|B>/<fișier>.md && git commit -m "docs(sessions): handoff checkpoint" && git push
```

Din secunda în care push-ul trece, predarea e recuperabilă chiar dacă sesiunea moare pe loc.

**3b. Abia acum scrii jurnalul adevărat**, peste schelet, după regulile de mai jos:
detaliat, nu rezumat — ce s-a cerut (în cuvintele utilizatorului), pași concreți și comenzi
rulate, ieșiri verbatim când contează, **fundăturile și de ce n-au mers**, decizii cu
raționamentul lor, starea la final, fișiere și branch-uri atinse.

Pushează din nou **după fiecare bucată substanțială**, nu o singură dată la final. Comite pur
și simplu peste checkpoint — mai multe commit-uri de jurnal nu deranjează pe nimeni. **Nu face
`commit --amend` + force-push** ca să „cureți" istoricul: force-push-ul cere confirmare
explicită de la Alexandru (regulă globală), iar aici n-ar cumpăra nimic — un istoric urât al
unui fișier de jurnal e prețul corect pentru un handoff care nu se poate pierde.

Fundăturile contează cel mai mult. Fără ele, celălalt cont reface aceleași greșeli.

Dacă sesiunea a fost scurtă și fără rezultate, spune asta într-o linie și treci mai departe —
nu inventa substanță.

## 4. Dacă ai atins izz-ro: actualizează `specs/STATE.md`

E sursa de adevăr pentru „unde am rămas" (`izz/CLAUDE.md` §15). Scrieri deținute de manager,
**suprascrise în loc**, sub ~30 de linii de conținut. Actualizează: `Updated:`, `Current task`,
`Last relevant commits`, `User WIP`, `Blockers`, `Next steps`.

Înainte de orice scriere în izz: `git pull --ff-only` — botul CI comite la ~30 min, main-ul
local e mereu în urmă.

### Gardă anti-suprascriere — obligatorie

`STATE.md` zice despre el însuși „one writer at a time", dar nimic nu impune asta: două sesiuni
paralele care îl rescriu integral se calcă una pe alta **în tăcere**. S-a întâmplat pe 2026-07-24
și a scăpat doar pentru că cele două scrieri au nimerit secțiuni diferite.

Deci, înainte să atingi `STATE.md`:

```bash
git fetch -q origin && git diff --quiet HEAD origin/main -- specs/STATE.md; echo $?
```

- `0` → ești la zi, scrie liniștit.
- `1` → **altcineva a scris între timp.** NU scrie peste. Fă `git pull --ff-only`, **recitește
  fișierul**, și abia apoi aplică modificările.

Și indiferent de rezultat: **modifică `STATE.md` prin editări de secțiune, nu rescriindu-l
integral.** O rescriere completă transformă orice scriere paralelă în pierdere tăcută; o editare
punctuală lasă git să vadă că sunt schimbări diferite. Rescrie tot fișierul doar când îl tai
pentru că a depășit limita de mărime — și atunci fă `fetch` imediat înainte.

Cine scrie `STATE.md`: **sesiunea care face merge în `main`**, oricare cont ar fi (§14, 2026-07-24).
Dacă tu nu integrezi nimic în `main` în sesiunea asta, **nu atinge deloc `STATE.md`** — scrie doar
în jurnalul tău din `sessions/`, unde un fișier per sesiune face coliziunea imposibilă prin
construcție, nu prin disciplină.

## 5. Predare explicită, dacă e cazul

Dacă rămâne ceva concret pentru celălalt cont, adaugă-l la „În așteptare" în `TASKS-B.md`
(A → B) — un task per punct, cu ce anume e de făcut și unde e spec-ul. Fără asta, celălalt
cont află ce s-a făcut, dar nu ce are de făcut.

**Anunță ce ai integrat.** `izz/CLAUDE.md` §14 (regulă din 2026-07-24): merge-ul îl face contul
din care lucrează Alexandru **în acel moment** — nu „cine a deschis PR-ul", nu „contul care
deține main". Un PR verde nu se parchează așteptând celălalt cont. În schimb, **orice merge se
scrie în `TASKS-B.md`**, la „Anunțuri de merge", plus în `specs/STATE.md`. Munca paralelă e
sigură pentru că ambele conturi știu ce a aterizat, nu pentru că doar unul are voie să miște.
Un merge neanunțat e exact ce a cauzat coliziunile pentru care s-a scris §14.

Regula veche „o singură sesiune scrie la `main`, întreabă înainte" e **depășită** — nu o repeta.

## 6. Commit + push — și la pașii 4 și 5, nu doar aici

Jurnalul e deja pe remote de la 3a. Aceeași regulă se aplică însă la tot ce ai scris după:
**`STATE.md` (pasul 4) și `TASKS-B.md` (pasul 5) se comit și se pushează pe măsură ce le
termini**, nu se adună pentru un push final. Nu există motiv să ții pe disc, în ultima parte a
bugetului, un fișier deja terminat.

Push explicit în **fiecare** repo atins (mesaje în engleză). Workspace-ul are sync automat la
15 minute, dar handoff-ul nu are voie să depindă de el — dacă comuți contul în următoarele
15 minute, celălalt cont ar citi starea veche.

Verifică, nu presupune: `git status -sb` trebuie să arate `## main...origin/main` **fără**
`[ahead N]`. Dacă push-ul eșuează, **spune-o clar și oprește-te acolo** — un handoff care n-a
ajuns pe remote e mai rău decât niciunul, pentru că pare făcut.

## 7. Raportează, scurt

Trei-cinci linii: unde e jurnalul, ce s-a actualizat în STATE.md, ce a rămas necomis (și de ce),
ce e în TASKS-B.md pentru celălalt cont. Fără reluarea conținutului jurnalului.
