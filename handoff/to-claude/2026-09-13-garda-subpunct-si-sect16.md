# Handoff: garda de sub-punct repusă în funcțiune + §16 renumerotată — 13 sep 2026

> Scris de sesiunea care a merge-uit #339 (`2944400b`). Cine preia: orice sesiune Claude.
> Trei lucruri te pot surprinde dacă nu le știi. Nimic din ce urmează nu cere acordul proprietarului.

## 1. `§16.3` NU mai înseamnă ce credeai — ancora s-a mutat

Subsecțiunea de verificare live se numește acum **`§16a`**, nu `§16.3`, după convenția pe care
`CLAUDE.md` o folosea deja (`§12a`, `§12b`, `§14b`).

Motivul: `§16.3` avea **două ținte** — punctul 3 al listei (Livrabilitate) și subsecțiunea
`### 16.3 Live verification`. Nu era o subtilitate: `notes/organism-izz.md:76` cita `§16.3`
pentru regula celor trei stări, care e **punctul 4**. Trimitere greșită, pe care coliziunea o
făcea să pară corectă. Toate cele cinci trimiteri vii au fost corectate.

Deci: **`§16.3` = Livrabilitate. `§16a` = verificare live.** `tools/verify_allowlist.sh`,
`specs/regim-reguli.md` și `specs/audit-unificat.md` sunt deja actualizate.

## 2. §16 are TREI axe, nu două — titlul minţea

Titlul era „Verificare în două roluri" și enumera trei axe (Programator, Utilizator,
**Livrabilitate**). §5 era coerentă tot timpul: §5.8 = roluri, §5.9 = livrabilitate, separat.

Consecință practică pentru tine: **nu raporta „verificat pe ambele axe" când ai făcut doar 1 și 2.**
Dacă livrabilitatea nu se aplică, spune-o explicit (§16.6) — nu o sări tăcut.
Există acum o gardă: titlul §16 trebuie să conțină numeralul cu litere al numărului de axe pe care
le enumeră. Prinde creșterea numărului de axe, nu scăderea la două.

## 3. Garda de sub-punct verifica 1 trimitere din 14 — acum 16 din 16

`tests/test_reguli.py::subpuncte_din_document` avea un regex de split care nu distingea `## 16.`
de `### 16.3`. Două efecte, ambele măsurate:

- un titlu `### N.M` era citit ca **secțiune** și golea lista reală de sub-puncte — `§16.99`,
  trimitere complet inventată, **TRECEA**, în timp ce `§5.99` era prinsă;
- titlurile `### 1.1` … `### 2.9` nu erau recunoscute ca **definiții**, deci §1, §2 și §4 din
  `REGULI-SINTEZA.md` nu aveau niciun sub-punct cunoscut.

Reparat cu un lookahead `(?!\d)` plus un tipar pentru sub-punctul definit ca titlu. Zero încălcări
reale ascunse dedesubt — cele 13 trimiteri erau corecte, dar nimeni nu știa asta.

## 4. CAPCANA care te va lovi: `STATE.md` se auto-invalidează la merge

`test_pr_fantoma` citește `STATE.md` din **checkout-ul PR-ului**, nu de pe main. Deci un main
învechit pică **ORICE** PR din coadă. Și nu e nevoie ca cineva să uite ceva: e de ajuns ca main
să se miște sub o ramură deschisă. S-a întâmplat de trei ori pe 13 sep, o dată în direct (#337 a
aterizat în timpul lucrării și a înroșit și main, și PR-ul care repara asta).

**Trei reguli operaționale, toate plătite scump:**

a) **Scoate-ți propriul PR din `## Open` ÎNAINTE de merge.** Altfel aterizarea lui îl face
   fantomă în aceeași secundă. Se poate face în siguranță: `pr_nelistat` exclude PR-ul pe care
   rulează CI chiar atunci, iar pragul lui e oricum 24h.

b) **Adnotarea `merged` nu trece peste alt `#`.** Regexul e `#(\d+)[^#\n]*\bmerged\b`. Forma
   `#337, #333, #331 merged` adnotează DOAR ultimul număr. Fiecare număr își poartă propriul
   `merged`, altfel garda pică. Măsurat: patru încălcări, prinse înainte de commit.

c) **Clona de sesiune e shallow**, iar garda se sare singură acolo — un verde local NU înseamnă
   nimic. `git fetch --unshallow` înainte să declari ceva verde.

## 5. Ce rămâne deschis, și cine îl poate face

- **`BUILD_COMMIT_SHA` în jobul `mirror`** [IZZ-0373]. Manifestul oglinzii poartă `GITHUB_SHA`,
  un strămoș al conținutului. Patch-ul e de două linii, în pasul „Render (rapid, fara fetch/AI)":
  `env: BUILD_COMMIT_SHA: ${{ needs.pipeline.outputs.content_sha }}`.
  **Blocat de CAPACITATE, nu de politică** — hook-ul de control-plane refuză scrierea, verificat
  cu comanda care a eșuat (`DENY: Bash command writing to protected control-plane path`).
  §10 NU acoperă directorul de workflow-uri; nu o invoca. Nu ocoli hook-ul prin API-ul GitHub —
  IZZ-0374 tocmai a închis două astfel de ocoliri.

- **Decizie de proprietar, neluată:** garda de PR fantomă rămâne blocantă, devine `::warning::`,
  sau `STATE.md` se actualizează automat la merge? A treia ar face garda să păzească un mecanism,
  nu un obicei. Nu o decide singur.

Decizii consemnate: `IZZ-0378`, `IZZ-0379`, `IZZ-0380`.
