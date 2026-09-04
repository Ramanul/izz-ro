# Axa 3 a gărzii de anomalie: unde duc linkurile din corp

> **Stare: PASUL 1 FĂCUT, implementarea rămâne.** Scris 2026-08-30; corpusul a fost măsurat în
> aceeași zi, pe runner ([run 33319058373](https://github.com/Ramanul/izz-ro/actions/runs/33319058373)).
> Cifrele sunt în §3a. Pasul 2 e acum decidabil.
> Regula care o cere: `specs/securitate-ingestie.md` §5.1 (gaura declarată) și R3 (pragurile se
> **măsoară**, nu se aleg).

## 1. De ce, cu dovada

`specs/securitate-ingestie.md` §5.1 spune deschis că detecția de anomalie e livrată **pe o
singură axă din trei**: limba declarată. Ce nu prinde, scris acolo: *„un defacement scris în
**română**"*. Axa „cadență" a fost măsurată pe 2026-08-12 și e **moartă** (`MAX_PER_SOURCE = 8`
plafonează debitul observat, deci măsori programul nostru de fetch, nu sursa; iar Cajvana avea
max24h = 1). Axa „mix tematic" are aceeași slăbiciune la n=1: o primărie cu **un singur** articol
la noi — chiar atacul — n-are istoric din care să înveți.

**Ce a scăpat, verbatim din commit-ul incidentului (2026-08-11):** articolul „Hacked by
Chinafans" de la `cajvana.ro` a stat live două zile pe izz.ro; corpul lui conținea linkuri către
`t.me/Hack_0xTeam` și `t.me/Hello_root`. Toate cele cinci straturi din `guard.verdict` l-au lăsat
să treacă — corect, fiindcă **în cuvintele lui nu e nimic ostil**. Prins, în cele din urmă, de axa
limbii, fiindcă titlul era englezesc. Scris românește, ar fi trecut și azi.

**Destinația linkurilor e singurul semnal care merge la n=1 și nu depinde de limbă.** O primărie
românească al cărei articol trimite spre un canal de mesagerie, un file-locker sau un tracker e
anormală *prin categorie*, nu prin comparație cu propriul istoric — deci nu are nevoie de istoric.

## 2. Cauza mecanică — de ce stratul 7 nu o acoperă deja

`guard.url_ostil()` verifică **URL-ul articolului** (schemă, caractere de control, credențiale în
autoritate, gazdă internă). Nu se uită în corp. Și nici n-ar avea la ce: `util.clean_html()` scoate
tagurile, deci `href`-urile dispar **înainte** ca `guard.verdict(titlu, corp)` să vadă textul.
Pipeline-ul aruncă exact informația de care garda ar avea nevoie.

Notă care contează pentru prag: linkul supraviețuiește ca **text** dacă ancora era chiar URL-ul
(cazul Cajvana). Deci o parte din semnal e deja în `corp` — dar numai o parte, și tocmai cazul
în care atacatorul a fost neglijent.

## 3. Ce lipsește ca să se poată construi: corpusul

R3 cere praguri măsurate. Ca să știm câte primării **legitime** linkează spre Telegram (unele chiar
au canal oficial), file-lockere sau scurtături de URL, ne trebuie gazdele-destinație pe corpusul
real. Azi nu există: `data/articles.json` ține `teaser` (rezumat AI), nu corpul, iar sursele nu se
pot re-fetch-a dintr-o sesiune web (proxy: `CONNECT tunnel failed 403` pe site-urile de știri).

**Canalul care ajunge: runner-ul de GitHub Actions.** Același truc care a infirmat „`gsp` dă 404".

## 3a. Corpusul, MĂSURAT — 2026-08-30

57 de surse citite pe runner, **437 de articole, 1.973 de linkuri** în corpurile brute:

| clasă | local (368 art., 1.672 linkuri) | național (69 art., 301 linkuri) |
|---|---|---|
| `proprie` | 1.622 (97,0%) | 266 (88,4%) |
| `alta` | 35 (2,1%) | 30 (10,0%) |
| `retea-sociala` | 15 (0,9%) | 5 (1,7%) |
| **`mesagerie`** | **0** | **0** |
| **`file-locker`** | **0** | **0** |
| **`torrent`** | **0** | **0** |
| **`scurtatura`** | **0** | **0** |
| **`paste`** | **0** | **0** |

**Ce decide asta.** Rata de fals-pozitive pentru o gardă care respinge un articol de sursă locală
cu linkuri către `mesagerie` / `file-locker` / `torrent` / `paste` este **0 din 368**. Clasele
alea pur și simplu nu apar în conținut legitim, deci lista se poate scrie cu pragul măsurat, nu
ales.

**Capcana evitată prin măsurare, și motivul pentru care R3 există:** `retea-sociala` **apare**
legitim (15 local + 5 național). O listă scrisă după intuiție ar fi inclus-o — Facebook și
YouTube arată „externe" la fel ca Telegram — și ar fi respins articole reale de primărie.

**Ce NU dovedește.** Eșantion de o singură citire, 8 iteme per sursă. O primărie își poate
deschide mâine un canal de Telegram legitim; 0/368 e un prior tare, nu o garanție. De aceea
garda trebuie să respingă **itemul**, nu sursa întreagă, și să aibă comutator de om mort (R4).

**`scurtatura` e cazul slab:** 0 apariții, dar un shortener nu e ostil prin natură, spre
deosebire de restul. Recomandarea e să intre pe listă doar dacă apare combinat cu alt semnal.

## 4. Pașii, în ordine

1. **~~Măsoară întâi.~~ FĂCUT** — `tools/masoara_gazde.py` + `.github/workflows/masoara-gazde.yml`,
   rulat 2026-08-30. Cifrele în §3a. *(Nota din specul inițial, „trage feed-urile prin
   `generator.fetch`", a fost relaxată conștient: unealta citește feedurile cu `feedparser`.
   Greșeala lui `feed_check.py` era că raporta SĂNĂTATEA sursei cu alt fetcher; aici se numără
   gazde, iar o sursă care nu răspunde înseamnă doar mai puține eșantioane — 3 din 60, tipărite
   în raport.)*
2. **Abia apoi alege pragul**, din cifrele alea, cu fals-pozitivele numărate. Dacă o clasă apare
   la primării legitime, nu intră în listă — sau intră doar combinată cu alt semnal.
3. **Implementează** ca strat 9, după modelul lui `anomalie()`: funcție pură, corpus de autotest
   cu ambele direcții (ostil / curat), legată în `fetch.py` pe cele trei căi de ingestie și în
   `moderation.apply`, cu comutator de om mort (R4).

## 5. Criterii de acceptare

- [ ] Raportul de la pasul 1 e rulat pe ≥ 500 de articole reale și consemnat în `specs/registru.tsv`.
- [ ] Fiecare clasă de gazdă din listă are numărul de apariții **la surse legitime** scris lângă ea.
- [ ] `guard.autotest()` acoperă axa nouă cu ambele direcții, ca la axa limbii.
- [ ] Cazul Cajvana (link `t.me` în corp, titlu în **română**) e prins de test.
- [ ] Zero fals-pozitive pe corpusul curat măsurat la pasul 1; dacă apar, pragul se schimbă, nu testul.

## 6. Ce NU rezolvă, spus explicit

Nimic din asta nu închide gaura „pentru totdeauna": cine citește fișierul ăsta află că un
defacement fără linkuri externe, scris românește, trece în continuare. Axa 3 mută costul
atacatorului, nu îl face infinit. Onestitatea asta e chiar formatul lui §5.1 — o listă deschisă,
nu o bifă.
