# România Utilă — MVP editorial și SEO

## Obiectiv

„România Utilă” este stratul permanent al IZZ.ro: informație administrativă care rămâne utilă după ce știrea zilei a expirat. Nu este o categorie de știri și nu trebuie alimentată prin copierea articolelor din presă.

Principiu: **o pagină = o întrebare concretă pe care un român o caută**. Valoarea trebuie să rămână după schimbarea zilei, iar datele variabile se actualizează fără schimbarea URL-ului.

## MVP — primele 10 pagini

1. `/ghiduri/salariul-minim/` — valoare actuală, istoric, data intrării în vigoare, sursa oficială.
2. `/ghiduri/pensia-minima/` — valoare actuală, condiții și sursă oficială.
3. `/ghiduri/alocatia-copii/` — valori pe categorii de vârstă și situație.
4. `/ghiduri/calendar-anaf/` — termene lunare și obligații uzuale.
5. `/ghiduri/calendar-scolar/` — structură an școlar și vacanțe.
6. `/ghiduri/rabla/` — condiții și calendar pentru ediția curentă.
7. `/ghiduri/noua-casa/` — condiții, plafon, avans, pași.
8. `/ghiduri/acte/` — index de proceduri și documente frecvent cerute.
9. `/ghiduri/taxe/` — index al taxelor importante, fiecare cu fișă proprie ulterior.
10. `/ghiduri/legi-explicate/` — explicații pe înțelesul cititorului, cu textul oficial ca sursă primară.

## Felia 1

Livrabilul concret este o zonă permanentă cu primele 3 pagini:

- salariul minim;
- alocații;
- calendar ANAF;

plus calculatorul salarial existent, legat de entitatea salariului minim și alimentat din aceeași valoare.

## Regula datelor

AI-ul poate rezuma, clasifica și reformula, dar **nu inventează valori, date, plafoane sau condiții**. Valorile provin dintr-o sursă oficială identificabilă. Orice câmp numeric din pagina publică trebuie să poată fi urmărit până la sursa și data de verificare.

Pentru informația volatilă, modelul de date folosește:

```text
key
value
unit
valid_from
valid_until
source_name
source_url
verified_at
status
```

`key` și URL-ul paginii sunt stabile; rândul de valoare se actualizează când se schimbă regula.

## Criteriu de lansare

Fiecare pagină trebuie să aibă sursă primară, dată de verificare, legături interne și test de randare. După indexare se măsoară separat de știri: impresii, CTR, poziții, intrări organice și reveniri.
