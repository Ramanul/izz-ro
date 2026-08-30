# Inventarul complet al problemelor nerezolvate — 2026-08-30, 18:5x ora RO

> Cerut de proprietar înainte de o pauză de o săptămână. Sursele: `specs/STATE.md`, PR-urile și
> issue-urile deschise citite de pe GitHub azi, registrul, și ce a ieșit din sesiunea asta.
> **Ce NU e aici:** ce nu știu că există. Nu am făcut un audit al codului, am inventariat ce e
> deja consemnat plus ce am măsurat azi.

## A. Blocate pe o decizie a ta — nimeni nu le poate mișca fără tine

1. **#198 — arhiva paginilor expirate.** 193 de pagini moarte în Search Console. `IZZ-0260`:
   se decide pe NUMĂRUL de fișiere, nu pe mărimea stării — 3,23 fișiere/articol, deci opțiunile
   2 și 3 mor în 7-24 de zile la plafonul de 100.000 assets; R2 e singura care scapă.
   `IZZ-0261` a corectat o afirmație veche: **nu e blocat pe #214**, ci pe decizia de
   arhitectură plus codul din `izz-failover`.
2. **#225 — trei decizii.** +107 octeți peste plafonul din CLAUDE.md · ștergerea regulii
   «Nu confunda unealta cu capacitatea» (prinsă de censul F3) · `IZZ-0250..0253` se ciocnesc.
   Ramura e cu 52 de commit-uri în urmă.
3. **#214 — o alegere binară.** Renumerotare + rezolvarea a trei conflicte, SAU închidere ca
   depășit, cu extragerea lui `infra/verifica-live.sh`, care rămâne util (`IZZ-0261`).
4. **#207 — planul de date administrative naționale.** Strategie, deschis de 8 zile, neatins.
5. **E1 (permalink decuplat) și E4 (axe separate)** din `specs/atribuire-cercetare-si-plan.md`.

## B. Defecte tehnice cunoscute, NEreparate

6. **F-B — dublurile cu vocabular disjunct.** Cardurile din captura ta: 0 tokeni comuni de
   titlu, 3 entități comune. Entitățile sunt folosite DOAR ca veto, niciodată ca dovadă pentru
   unire. Niciun prag pe Jaccard nu poate repara asta. Cere eșantioane pe ambele erori (§7).
   Măsurătorile sunt gata în `specs/dubluri-clustering-2026-08-30.md`.
7. **Sursele oficiale locale n-au NICIO bară de calitate.** Ocolesc AI-ul
   (`specs/local-official-no-ai.md`), deci `ANUNT LOCUINTE APOLD`, `Publicatie Bujor Elise`,
   `Combatarea buruienii ambrozia` ajung ca titluri pe site. Azi s-a prins doar forma
   „titlul e exact o dată".
8. **Axa 3 a gărzii de anomalie** — spec scris (`specs/anomalie-linkuri.md`, `IZZ-0259`),
   NEimplementat: cere praguri măsurate, iar corpusul de gazde-destinație nu există.
   `masoara-gazde.yml` e doar manual și **nu l-a rulat nimeni**.
9. **Cauza mecanică a lui 8:** `clean_html()` scoate `href`-urile înainte de `guard.verdict()`.
10. **E3 focus score** și **E5 gold set ~150 + poartă CI** din dosarul de atribuire.
11. **Sonda de trafic** — nu se știe încă, măsurat, dacă tokenul CLOUDFLARE existent are scope
    de analytics. `trafic.yml` e scrisă, răspunsul nu a fost citit.
12. **K12 nevalidat** — `revizuire.yml` postează prima oară la 09:40 ora RO pe issue-ul #233.
    Mecanismul e nou; prima rulare e de CITIT, nu de presupus că merge.

## C. Proces și infrastructură

13. **#83 — canal live de coordonare A ↔ B**, deschis din 24 iulie, neatins.
14. **Canalul de anunț din §14 (`handoff/to-A/`) nu e accesibil din sesiunile remote.** Măsurat
    azi: `ls /home/user/` are doar `izz-ro`. Deci jumătate din regula de anunț post-merge nu se
    poate executa de aici, iar §14 nu spune ce se face atunci.
15. **Coliziunile de ID în registru.** `_next_id` calculează max+1 pe vederea PROPRIE a ramurii;
    documentat `IZZ-0241`, s-a repetat azi (#232 și sesiunea asta au cerut amândouă 0261).
    Evitat manual, nu mecanic. Nimic nu-l previne data viitoare.
16. **#230 rămâne deschis** — conținutul lui e absorbit de #236; de închis DUPĂ ce #236 aterizează.
17. **#236 nu e încă merged** — CI rula la momentul scrierii.
18. **Fără marjă în fișierele de reguli.** `STATE.md` la 40/40 linii, `CLAUDE.md` la
    24.106/24.576 octeți. F4 are candidați măsurați (§12, §14, §18, §17, §20) dar nu s-a mutat
    nimic după pilot.

## Dacă ai timp pentru UN singur lucru vineri

**7** — bara de calitate pentru sursele oficiale locale. E singurul din listă care produce
output vizibil stricat pe site chiar acum, în fiecare zi, și nu depinde de nicio decizie a ta.
