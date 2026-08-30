# Axa 3 a gărzii de anomalie: unde duc linkurile din corp

> **Stare: SPEC, neimplementat.** Scris 2026-08-30 după ce măsurătoarea a arătat că axa nu se
> poate construi corect fără un corpus care azi nu există. Nu implementa fără pasul 1 de mai jos.
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

## 4. Pașii, în ordine

1. **Măsoară întâi.** Un tool + un job `workflow_dispatch` care rulează pe runner, trage feed-urile
   **prin `generator.fetch`** — nu cu un fetch propriu; `feed_check.py` a făcut greșeala asta și
   raporta 429/timeout pe surse pe care pipeline-ul le recuperează — extrage gazdele din `href`
   **înainte** de `clean_html`, și raportează: câte articole au linkuri externe, spre ce clase de
   gazde, separat pentru sursele `pl_*` și cele naționale.
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
