# Dimensiunile de analiză a codului — lista, așa cum a fost numerotată

> **Ce e fișierul ăsta:** un RECORD, nu un plan. Taxonomia a fost formulată în conversație pe
> 2026-09-02 și n-a ajuns niciodată într-un fișier — o sesiune de pe 2026-09-04 a cerut-o
> explicit fiindcă nu o găsea nicăieri în repo. Asta e cauza pentru care fișierul există.
>
> **Regula de citire, cea mai importantă:** fiecare rând e marcat `[FAPT]` sau `[INTERPRETARE]`.
> `[FAPT]` = îl am din context sau e scris în repo, cu locul indicat. `[INTERPRETARE]` = e
> dedus. **Dimensiunile 5 și 6 au DOAR nume, nu și definiție** — vezi secțiunea dedicată. Nu le
> completa din ce pare plauzibil: o listă ghicită într-un fișier din `specs/` e mai rea decât
> una lipsă, fiindcă sesiunile următoare o citesc ca fapt (același tipar cu `IZZ-0257`).

## Lista

| # | Nume | Ce întreabă | Stare | Unde a aterizat |
|---|------|-------------|-------|-----------------|
| 1 | Ce eșuează **tăcut** | Ce se pierde fără să lase urmă în site, în `articles.json` sau în log? | livrată | `IZZ-0272`, PR #252 |
| 2 | Adevăr **editorial** | Ce publicăm e corect — nu ca sănătate a codului, ci ca produs citit de om? | **blocată pe date** | `IZZ-0268`, `IZZ-0299` |
| 3 | **Cost** | Ce se scumpește în timp și unde e plafonul real? | măsurată | `IZZ-0273`, `IZZ-0274`, `IZZ-0292`, commit `32d6408a` |
| 4 | Ce nu prind **testele** | Testele *verifică* codul sau doar îl *execută*? | livrată | `IZZ-0275`–`IZZ-0283`, commit `b05541e0`, `tools/mutanti.py` |
| 5 | **Perf front-end** | — *fără definiție, vezi mai jos* | neatinsă | — |
| 6 | **Risc** | — *fără definiție, vezi mai jos* | neatinsă | — |
| 7 | Ce există dar **nu e folosit** | Cod fără apelant, documente fără referință, reguli fără gardă | măsurată, parțial curățată | `IZZ-0284`–`IZZ-0293`, commit `9ded4c96`, `tools/nefolosit.py` |

## Provenanța fiecărui rând

- **1, 3, 4, 7** — `[FAPT]`. Numerotarea e verificabilă în repo, nu doar în memoria mea:
  commit-ul `32d6408a` scrie literal *„Dimensiunea 3 din taxonomia de intrebari despre cod
  (dupa «ce esueaza tacut», IZZ-0272)"*, ceea ce fixează și 1, și 3. Pentru 4 și 7 numerele
  vin din cererile proprietarului („continuă cu dimensiunea 4", „continuă cu dimensiunea 7").
- **2** — `[FAPT]` pentru număr și nume; conținutul e documentat în `IZZ-0268` (setul de aur
  erodat la 7 rânduri din 51) și `IZZ-0299` (blocajul).
- **5, 6** — `[FAPT]` **doar pentru număr și etichetă**. Vezi secțiunea următoare.

## Dimensiunile 5 și 6: ce ȘTIU și ce NU știu

`[FAPT]` Etichetele sunt „perf front-end" (5) și „risc" (6), în ordinea asta. Le am din context.

`[FAPT]` **Niciuna nu a fost vreodată definită operațional.** N-au fost începute, deci n-au
produs nici măsurători, nici rânduri de registru, nici commit-uri. Absența lor din repo nu e
o pierdere de informație — nu a existat informație de pierdut.

`[FAPT]` Despre 6, am consemnat explicit în aceeași sesiune, ca autocritică a taxonomiei:
*„D6 («risc») nu e o dimensiune, e un cuvânt. N-am definit-o operațional, deci nu poate fi
nici măsurată, nici declarată neîncepută onest."* Asta rămâne cea mai exactă descriere a ei.

`[INTERPRETARE]` — **și nu trebuie citită ca definiție** — pentru 5 există deja unelte în repo
care ar fi punctul natural de pornire: `tools/audit.sh`, agentul `frontend-auditor`, baseline-ul
din `specs/masuratori-frontend.md`, și §13. Legătura asta o fac ACUM, deducând din ce e în repo;
nu e ce spunea formularea originală, fiindcă formularea originală nu spunea nimic.

**Deci: dacă cineva vrea 5 sau 6, le definește de la zero.** Nu le recupera din fișierul ăsta.

## Critica taxonomiei, consemnată în aceeași sesiune

`[FAPT]` Trei obiecții pe care mi le-am adus singur, păstrate fiindcă schimbă cum se citește lista:

1. **6 nu e o dimensiune, e o etichetă.** (Vezi mai sus.)
2. **Cinci din șapte măsoară CODUL, una măsoară PRODUSUL** — și tocmai aia (2) e blocată. Un
   cititor rău-voitor ar spune că am ales dimensiunile pe care le puteam măsura, nu pe cele
   care contează pentru cititorul lui izz.ro. Obiecția are greutate.
3. **3 și 7 se suprapun** — costul de context al regulilor e și „cost", și „nefolosit". Le-am
   separat după *unde se plătește* (la rulare vs. la fiecare tură), ceea ce e o alegere, nu un
   adevăr.

## Notă despre PR #253, cerută odată cu lista — și ce s-a întâmplat între timp

`[FAPT]` Cererea spunea că „`specs/STATE.md` nu îl pomenește deloc pe #253". Era adevărat
**pentru `main`** și fals pentru ramura `claude/session-g1w3mu`, unde linia îl numea de la
commit-ul `09c55514`. Diferența era doar că #253 nu fusese încă merge-uit.

`[FAPT]` Între scrierea acestui fișier și commit-ul lui, proprietarul a scos #253 din draft
și l-a făcut merge (`de6f0e3e`, 2026-09-04 05:03). **Asta a înroșit `main` imediat**, a patra
oară în două zile, din aceeași cauză: `## Open` numea `#253` fără cuvântul `merged` lângă el,
iar garda `incalcari_pr_fantoma` exact asta caută. Reparat în același commit cu fișierul de față.

`[INTERPRETARE]` De patru ori aceeași greșeală nu mai e o problemă de atenție, e semnalul că
regula ar trebui **automatizată**: ceva care adnotează singur, în `## Open`, PR-urile care au
primit commit de merge pe main. Garda le detectează deja — îi lipsește doar partea care repară.
Observația a fost făcută și în corpul lui #251; o repet aici fiindcă acolo n-a produs nicio
acțiune, și un al patrulea incident e o dovadă mai bună decât al treilea.
