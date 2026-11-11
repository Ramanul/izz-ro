---
description: Checkpoint de predare către următoarea sesiune — scrie jurnalul sesiunii, actualizează STATE.md, listează WIP-ul necomis și face push, ca sesiunea următoare să poată continua doar din fișiere.
argument-hint: [opțional: notă scurtă despre ce urmează]
---

Rulezi handoff-ul. Notă de la utilizator despre ce urmează: **$ARGUMENTS**

Scopul: după comanda asta, **următoarea sesiune trebuie să poată relua firul citind doar fișiere** —
fără transcript, fără să fi fost de față. Se rulează și la mijloc, nu doar la final, în special
când alerta de consum (`usage-alert.ps1`, prag 75%) semnalează că mai ai buget cât să scrii, dar
poate nu cât să termini.

**Repo public: în jurnal nu intră chei, tokeni, variabile de mediu, căi către fișiere de
configurare locale sau ieșiri brute necitite.** Rezumă ieșirea; nu o lipi.

## 1. Inventariază starea reală — nu din memorie

Rulează `git status --short` și `git log --oneline -5` în **fiecare** repo atins în sesiune.

Separă explicit trei categorii:
- ce e **comis** (intră în jurnal ca hash + mesaj),
- ce e **necomis și e al tău** (îl comiți la pasul 5),
- ce e **necomis și e WIP-ul altcuiva** (utilizator, alt executor) — vezi secțiunea
  „User WIP — UNTOUCHABLE" din `specs/STATE.md`. **Nu-l comite, nu-l face stash, nu-l stage-ui.**
  Îl LISTEZI în jurnal, cu avertismentul că nu e pe remote.

## 2. Citește ultimul jurnal

`ls -t sessions/A/ | head -1`, apoi citește-l. Scrii **doar ce s-a întâmplat după el**.
Nu rescrie istorie deja jurnalizată — trimite la ea cu numele fișierului.

## 3. Scrie jurnalul

`sessions/A/<YYYY-MM-DD-HHmm-slug-scurt>.md`. Detaliat, nu rezumat: ce s-a cerut (în cuvintele
utilizatorului), pași concreți și comenzi rulate, decizii cu raționamentul lor, starea la final,
fișiere și branch-uri atinse, și mai ales **fundăturile și de ce n-au mers** — fără ele,
următoarea sesiune reface aceleași greșeli.

Dacă sesiunea a fost scurtă și fără rezultate, spune asta într-o linie — nu inventa substanță.

## 4. Dacă ai integrat ceva în `main`: actualizează `specs/STATE.md`

E sursa de adevăr pentru „unde am rămas" (§5.7, §14). Actualizează: `Updated:`, `Current task`,
`Last relevant commits`, `User WIP`, `Blockers`, `Next steps`. Sub ~30 de linii de conținut.

**Gardă anti-suprascriere — obligatorie.** Botul CI și alți executori comit și ei pe `main`, deci
înainte să atingi `STATE.md`:

```bash
git fetch -q origin && git diff --quiet HEAD origin/main -- specs/STATE.md; echo $?
```

- `0` → ești la zi, scrie.
- `1` → altcineva a scris între timp. `git pull --ff-only`, **recitește fișierul**, apoi aplică.

Modifică `STATE.md` prin editări de secțiune, nu rescriindu-l integral: o editare punctuală lasă
git să vadă schimbările diferite; o rescriere completă le pierde în tăcere.

Dacă nu integrezi nimic în `main` în sesiunea asta, **nu atinge `STATE.md`** — scrie doar jurnalul.

Dacă rămâne o sarcină concretă pentru **alt executor**, scrie-i un fișier în
`handoff/to-<executor>/` (un fișier per felie: ce e de făcut, constrângeri, criteriu de verificare).

## 5. Commit + push

Comite jurnalul, `STATE.md` și eventualul fișier de predare pe măsură ce le termini (mesaje în
engleză), apoi push. **Nu face `commit --amend` + force-push** — cere confirmare explicită de la
Alexandru și n-ar cumpăra nimic.

Verifică, nu presupune: `git status -sb` trebuie să arate `## main...origin/main` **fără**
`[ahead N]`. Dacă push-ul eșuează, **spune-o clar și oprește-te acolo** — un handoff care n-a
ajuns pe remote pare făcut și nu e.

## 6. Raportează, scurt

Trei-cinci linii: unde e jurnalul, ce s-a actualizat în STATE.md, ce a rămas necomis (și de ce),
ce ai lăsat în `handoff/`. Fără reluarea conținutului jurnalului.
