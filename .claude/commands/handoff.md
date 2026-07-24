---
description: Checkpoint de predare între conturile Claude — scrie jurnalul sesiunii, actualizează STATE.md, listează WIP-ul necomis și face push, ca celălalt cont să poată continua doar din fișiere.
argument-hint: [opțional: notă scurtă despre ce urmează]
---

Rulezi handoff-ul între conturi. Notă de la utilizator despre ce urmează: **$ARGUMENTS**

Scopul: după comanda asta, **celălalt cont trebuie să poată relua firul citind doar fișiere** —
fără transcript, fără să fi fost de față. Nu e o comandă de „final de sesiune": se rulează și la
mijloc, în special când alerta de consum (`usage-alert.ps1`, prag 75%) semnalează că mai ai buget
cât să scrii, dar poate nu cât să termini.

## 0. Determină pe ce cont rulezi

- Ai acces la `C:\Users\cw_26\` sau `C:\claude desktop\` → **contul A** (aplicația desktop, local).
- Nu ai → **contul B** (browser / Claude Code web, cloud).

Nu ghici. Verifică cu un `ls`. Contul decide în ce director scrii jurnalul: `sessions/A/` sau `sessions/B/`.

## 1. Inventariază starea reală — nu din memorie

Rulează `git status --short` și `git log --oneline -5` în **fiecare** repo atins în sesiune
(tipic `C:\claude desktop` și, dacă ai lucrat la izz, `C:\claude desktop\izz`).

Separă explicit trei categorii:
- ce e **comis** (intră în jurnal ca hash + mesaj),
- ce e **necomis și e al tău** (îl comiți la pasul 5),
- ce e **necomis și e WIP-ul utilizatorului** — vezi secțiunea „User WIP — UNTOUCHABLE" din
  `izz/specs/STATE.md`. **Nu-l comite, nu-l face stash, nu-l stage-ui.** Îl LISTEZI în jurnal,
  cu avertismentul că celălalt cont nu-l vede deloc pe remote.

## 2. Citește ultimul jurnal din directorul tău

`ls -t sessions/<A|B>/ | head -1`, apoi citește-l. Scrii **doar ce s-a întâmplat după el**.
Nu rescrie istorie deja jurnalizată — trimite la ea cu numele fișierului.

## 3. Scrie jurnalul

`sessions/<A|B>/YYYY-MM-DD-HHmm-slug-scurt.md`, după regulile din `sessions/README.md`:
detaliat, nu rezumat — ce s-a cerut (în cuvintele utilizatorului), pași concreți și comenzi
rulate, ieșiri verbatim când contează, **fundăturile și de ce n-au mers**, decizii cu
raționamentul lor, starea la final, fișiere și branch-uri atinse.

Fundăturile contează cel mai mult. Fără ele, celălalt cont reface aceleași greșeli.

Dacă sesiunea a fost scurtă și fără rezultate, spune asta într-o linie și treci mai departe —
nu inventa substanță.

## 4. Dacă ai atins izz-ro: actualizează `specs/STATE.md`

E sursa de adevăr pentru „unde am rămas" (`izz/CLAUDE.md` §15). Scrieri deținute de manager,
**suprascrise în loc**, sub ~30 de linii de conținut. Actualizează: `Updated:`, `Current task`,
`Last relevant commits`, `User WIP`, `Blockers`, `Next steps`.

Înainte de orice scriere în izz: `git pull --ff-only` — botul CI comite la ~30 min, main-ul
local e mereu în urmă.

## 5. Predare explicită, dacă e cazul

Dacă rămâne ceva concret pentru celălalt cont, adaugă-l la „În așteptare" în `TASKS-B.md`
(A → B) — un task per punct, cu ce anume e de făcut și unde e spec-ul. Fără asta, celălalt
cont află ce s-a făcut, dar nu ce are de făcut.

Reamintește regula de coliziune: `izz/CLAUDE.md` §14 — **o singură sesiune scrie la `main`**.
Contul B lucrează pe branch propriu și nu face merge.

## 6. Commit + push

Comite jurnalul și STATE.md (mesaje în engleză), apoi `push` explicit în fiecare repo atins.
Workspace-ul are sync automat la 15 minute, dar handoff-ul nu are voie să depindă de el —
dacă comuți contul în următoarele 15 minute, celălalt cont ar citi starea veche.

Dacă push-ul eșuează, **spune-o clar și oprește-te acolo** — un handoff care n-a ajuns pe remote
e mai rău decât niciunul, pentru că pare făcut.

## 7. Raportează, scurt

Trei-cinci linii: unde e jurnalul, ce s-a actualizat în STATE.md, ce a rămas necomis (și de ce),
ce e în TASKS-B.md pentru celălalt cont. Fără reluarea conținutului jurnalului.
