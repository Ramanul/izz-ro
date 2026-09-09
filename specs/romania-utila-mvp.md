# România Utilă — MVP editorial și SEO

## Obiectiv

„România Utilă” este stratul permanent al IZZ.ro: informație administrativă care rămâne utilă după ce știrea zilei a expirat. Nu este o categorie de știri și nu trebuie alimentată prin copierea articolelor din presă.

Principiu: o pagină = o întrebare concretă pe care un român o caută. Valoarea rămâne după schimbarea zilei, iar datele variabile se actualizează fără schimbarea URL-ului.

## MVP — primele 10 pagini

1. `/romania-utila/salariul-minim/`
2. `/romania-utila/pensia-minima/`
3. `/romania-utila/alocatii/`
4. `/romania-utila/calendar-anaf/`
5. `/romania-utila/calendar-scolar/`
6. `/romania-utila/rabla/`
7. `/romania-utila/noua-casa/`
8. `/romania-utila/acte/`
9. `/romania-utila/taxe/`
10. `/romania-utila/legi-explicate/`

## Structura obligatorie a unei pagini

- titlu orientat pe intenția de căutare;
- „Valabil la data de …”;
- valoarea/regula curentă într-un rezumat vizibil;
- sursa oficială primară + data verificării;
- „Ce înseamnă pentru tine”;
- condiții și excepții;
- pași practici pentru proceduri;
- istoric minim când valoarea se schimbă;
- linkuri interne;
- ultima actualizare fără schimbarea URL-ului.

## Regula datelor

AI-ul poate rezuma și reformula, dar nu inventează valori, date, plafoane sau condiții. Orice valoare publicată trebuie urmărită la o sursă oficială și la data verificării.

Model minim pentru date volatile:

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

Cheia și URL-ul paginii sunt stabile; valoarea se schimbă când se schimbă regula.

## Arhitectură SEO

`IZZ.ro → România Utilă → domeniu → pagină permanentă → instrument/explicație`

Știrile despre aceeași temă trimit spre pagina permanentă. Pagina permanentă trimite spre știrile relevante, dar nu depinde de ele pentru a fi utilă.

Nu se creează sute de pagini subțiri doar pentru variații de cuvinte-cheie.

## Instrumente MVP

1. calculator salariu net;
2. calculator termene fiscale;
3. calculator alocații/beneficii;
4. verificator „ce acte îmi trebuie”.

Instrumentele reutilizează aceleași date structurate ca paginile informative.

## Felia 1

Livrabil: 3 pagini complete — salariul minim, alocații, calendar ANAF — plus calculator salariu net.

Fiecare trebuie să aibă sursă primară, data verificării, legături interne, utilizare mobilă bună și test de randare. După lansare se măsoară separat traficul organic, CTR, pozițiile și revenirea utilizatorilor.
