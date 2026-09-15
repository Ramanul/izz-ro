# Handoff: mandatul de merge e PERMANENT din 2026-09-15

> Pentru orice sesiune Claude care pornește după asta. Citește `CLAUDE.md` §5.4 la sursă, nu
> rezumatul de aici.

## Ce s-a schimbat, într-un rând

**Nu mai ceri acordul proprietarului pentru fiecare merge.** #341 a aterizat: §5.4 nu mai cere ca
proprietarul să numească PR-ul în sesiunea curentă. Condițiile au trecut la executor.

## Condițiile, care RĂMÂN și sunt ale tale

1. CI verde pe head-ul **curent** — nu pe o rulare veche de pe un head vechi.
2. Fără conflict.
3. Fără constatare de recenzie neadresată.
4. `specs/STATE.md` **fără PR-ul propriu** în `## Open` înainte de merge.
5. Un PR deschis de altă sesiune **vie** rămâne al ei (IZZ-0140).
6. Auto-merge rămâne interzis — dar pentru judecată absentă, nu pentru delegare permanentă.

## Capcana pe care am lovit-o, ca să nu o relovești

Condiția 4 și garda `pr-nelistat` se contrazic pe un PR deschis de peste 24h: fantoma cere să NU
fie listat la merge, nelistatul cere să FIE listat cât e deschis. Nu se pot satisface simultan
fără o adnotare `(merged)` falsă. Ordinea care produce **o singură** rulare roșie pe main, fără PR
suplimentar: aterizează PR-ul, apoi imediat un PR de curățenie care îl scoate din coadă și se
scoate și pe el. Nu scrie `(merged)` despre ceva ce nu e încă merge-uit.

## Ce am aterizat în sesiunea asta

- **#347** — șase gărzi care citesc stare comisă devin `stare_partajata`: roșul de stare nu mai
  înroșește coada. Consecință utilă imediat: roșul de bookkeeping de mai sus nu blochează PR-uri.
- **#341** — mandatul permanent.
- **#348** — curățenia de coadă din `specs/STATE.md` (PR-ul care poartă nota asta).

## Ce e deschis și are termen

Podeaua de fișiere. Măsurat 2026-09-15: fereastra TTL=20 are 11.250 articole din podeaua de 12.800,
iar ingestul median e 960/zi față de cele 590/zi pe care s-a dimensionat `specs/cloudflare-free-2026-09.md`.
Echilibrul cere TTL ≈ 13 zile. **Nu tăia reflex 7 zile de arhivă:** supapa de la §4.7 a spec-ului e
inactivă (14.336 fișiere din 17.000), iar podeaua e un tripwire care presupune 100% publicare când
măsurat e ~81%. Decizia reală e cât factor de siguranță păstrezi, și se leagă de issue-ul #198.
