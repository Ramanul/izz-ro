# Registrul de decizii — evidența strictă a tot ce s-a propus, făcut, respins sau anulat

**Problema, în cuvintele proprietarului (2026-08-04):** nimic nu e cuantificat. Modificări
discutate și nediscutate, propuneri amintite și niciodată implementate, direcții încercate și
abandonate, anulări — toate există doar împrăștiate prin sesiuni. Ca să afli dacă ceva a fost
propus, implementat sau respins, trebuie să reîncarci contextul mai multor zile de discuții. Multe
discuții au fost șterse între timp.

**Ce trebuie să rezolve, exact:** să răspunzi la „s-a încercat X?" cu un singur `grep`, nu cu
reîncărcarea istoricului. Costul de INTEROGARE trebuie să fie de câteva linii, nu de câteva mii.

## Forma

Un singur fișier tabular, append-only, `specs/registru.tsv`, plus `tools/registru.py` cu
`add` / `find` / `show` / `sync`. Nu un document în proză, nu un director cu multe fișiere:

- **de ce tabular, nu proză:** proza se citește întreagă ca s-o interoghezi. `STATE.md` are deja
  911 linii și tot nu răspunde la „s-a propus vreodată X?".
- **de ce un singur fișier, nu un director:** `grep` peste un fișier compact întoarce 3 linii.
  Un director cere `ls` + citit fișiere, deci două runde.
- **de ce append-only:** ce s-a respins acum o lună trebuie să rămână citibil, cu motivul. Un
  registru care se rescrie pierde exact informația pentru care există.
- **de ce ID-urile nu sunt mereu contigue:** `add` alocă `max+1` din copia locală, iar fiecare
  ramură pornește de la același `main` — deci ramurile paralele primesc aceleași numere. Când
  se întâmplă, una își rezervă un interval mai sus (#217 a sărit la IZZ-0244 ca să lase
  0237-0243 altor șapte ramuri). **Un gol în secvență nu e o eroare de scriere**, și ordinea
  ID-urilor nu mai e cronologică după un astfel de salt. Alocatorul e reparat în #208.

### Coloane

```
id	data	zona	titlu	stare	decident	dovada	motiv	leaga
```

- `id` — `IZZ-0001`, stabil, nu se refolosește niciodată.
- `zona` — `fetch` `cluster` `render` `seo` `surse` `ui` `ci` `legal` `cost` `proces`.
- `stare` — vocabularul e partea importantă (mai jos).
- `decident` — `proprietar` / `claude` / `agent` / `recenzor`.
- `dovada` — `#131`, `cb5b1ff4`, `specs/x.md`, `sessions/A/2026-08-04-...md`. Poate fi goală doar
  la `propus`.
- `motiv` — o linie. **Obligatorie** la `respins`, `abandonat`, `anulat`, `masurat-fals`.
- `leaga` — id-uri legate: ce înlocuiește, ce a anulat, ce a rezultat din ce.

### Vocabularul de stări — asta face registrul interogabil

| stare | înseamnă |
|---|---|
| `propus` | s-a propus, nu s-a decis nimic |
| `acceptat` | s-a decis că se face, nu s-a construit încă |
| `implementat` | a intrat pe main |
| `respins` | s-a decis că NU se face, cu motiv |
| `abandonat` | s-a început și s-a lăsat, cu motiv |
| `anulat` | a fost implementat și apoi dat înapoi, cu motiv |
| `blocat` | așteaptă o decizie de proprietar sau ceva extern |
| `masurat-fals` | o afirmație măsurată care s-a dovedit greșită |
| `inchis-de-proprietar` | „nu redeschide" — decizie finală |

Ultimele două sunt cele mai valoroase și cele care se pierd cel mai ușor. Repo-ul ăsta are deja o
grămadă: „IP-urile runnerilor sunt blocate" (fals, măsurat), „bannerul de consimțământ cauzează
CLS" (fals), „un retry trece de challenge" (fals, 40/40), „`src_extra` se pierde prin căile AI"
(fals, refutat pe cod), „dark mode e stricat" (închis de proprietar, spus de patru ori). Fiecare a
costat timp de re-diagnosticare cel puțin o dată.

## Cine îl ține la zi

**Două jumătăți, cu costuri diferite.**

1. **Rândurile derivate din PR-uri se GENEREAZĂ**, nu se scriu de mână: `registru.py sync` citește
   `gh pr list --state all` și emite un rând per PR (titlu, stare, dată, dovadă). Zero tokeni de
   model, poate intra în task-ul de sincronizare de la 15 minute.
2. **Rândurile care NU au PR se adaugă în momentul deciziei** — propuneri, refuzuri, fundături,
   măsurători false, decizii de proprietar. Un singur `registru.py add`. Regula intră în
   `CLAUDE.md`: *o decizie care nu produce un PR se scrie în registru în aceeași tură în care s-a
   luat.* Altfel registrul moare, ca orice log ținut de mână.

**Și regula de consultare, fără de care registrul e doar arhivă:** înainte de a propune ceva,
`registru.py find <subiect>`. Dacă iese `respins` sau `masurat-fals`, se citește motivul înainte
de a redeschide.

## Recuperarea istoricului — trei niveluri, cu costuri onest diferite

| nivel | ce acoperă | volum | cost |
|---|---|---|---|
| **T1** | 128 PR-uri + 651 commits + 20 spec-uri | ~150 rânduri | ~0 tokeni, script |
| **T2** | 41 de jurnale de sesiune: propuneri, fundături, măsurători false | ~60-120 rânduri | tokeni de model, paralelizabil pe agenți |
| **T3** | 52 de transcripturi locale | necunoscut | scump, randament mic, se suprapune cu T2 |

**Ce NU se recuperează, deloc:** discuțiile șterse, și tot ce s-a lucrat înainte de 24 iulie fără
să lase urmă în git (cel mai vechi jurnal e `2026-07-24`, iar proiectul există din 26 iunie).
T1 acoperă perioada aia doar cu ce a devenit cod.

## Unde a ajuns recuperarea, și cum se rulează restul

**T1 — GATA (2026-08-04).** 128 de rânduri generate din PR-uri + 15 adăugate de mână (cele
`masurat-fals`, `inchis-de-proprietar`, `respins`, `anulat`, `blocat` pe care le știam din
`STATE.md` și `CLAUDE.md`). Total 143. Un `find` gol NU înseamnă „nu s-a încercat" — înseamnă că
T2/T3 n-au ajuns acolo.

**T2 și T3 — pregătite mecanic, neexecutate.** Partea scumpă e citirea, deci se face pe agenți
paraleli, nu în firul principal:

1. Corpusul T2: 553 KB de jurnale în `sessions/A/`, `sessions/A/auto/`, `sessions/B/` din
   workspace. Deja distilate — randament mare pe token. Acoperă **de la 24 iulie încoace**.
2. Corpusul T3: `python tools/extrage_conversatii.py --max-kb 200` din workspace transformă cele
   98.3 MB de transcripturi în **2.76 MB** de text de conversație (de 35 de ori mai puțin, fiindcă
   97% erau payload-uri de unelte), împărțit în 13 bucăți. Singura cale către perioada
   **26 iunie – 24 iulie**, unde nu există jurnale. Ieșirea e gitignorată intenționat.
3. Un agent per bucată, cu aceeași instrucțiune: extrage DOAR ce nu are deja PR — propuneri
   neimplementate, direcții abandonate, afirmații măsurate și dovedite false, decizii de proprietar
   — și emite linii `tools/registru.py add` gata de rulat. Interzis să inventeze motive: dacă
   motivul nu e scris în sursă, rândul iese cu motivul gol și se semnalează.
4. Rândurile se dedublează față de cele 143 existente înainte de append (`find` pe titlu).

**Ce rămâne irecuperabil, oricât s-ar cheltui:** discuțiile șterse de proprietar. Nu sunt nici în
git, nici în transcripturi.

## Ce NU rezolvă asta

Registrul e o evidență, nu o memorie semantică. Nu răspunde la „de ce arată prost pagina de
categorie" — răspunde la „s-a atins vreodată pagina de categorie, când, de cine, cu ce rezultat".
Pentru al doilea tip de întrebare rămân `STATE.md` și jurnalele.
