# România Utilă — MVP editorial și SEO

## Obiectiv

„România Utilă” este stratul permanent al IZZ.ro: informație administrativă care rămâne utilă după ce știrea zilei a expirat. Nu este o categorie de știri și nu trebuie alimentată prin copierea articolelor din presă.

Principiu: **o pagină = o întrebare concretă pe care un român o caută**. Valoarea trebuie să rămână după schimbarea zilei, iar datele variabile se actualizează fără schimbarea URL-ului.

## MVP — primele 10 pagini

1. `/romania-utila/salariul-minim/` — valoare actuală, istoric, data intrării în vigoare, sursa oficială.
2. `/romania-utila/pensia-minima/` — valoare actuală, condiții și sursă oficială.
3. `/romania-utila/alocatii/` — valori pe categorii de vârstă și situație.
4. `/romania-utila/calendar-anaf/` — termene lunare și obligații uzuale.
5. `/romania-utila/calendar-scolar/` — structură an școlar și vacanțe.
6. `/romania-utila/rabla/` — condiții și calendar pentru ediția curentă.
7. `/romania-utila/noua-casa/` — condiții, plafon, avans, pași.
8. `/romania-utila/acte/` — index de proceduri și documente frecvent cerute.
9. `/romania-utila/taxe/` — index al taxelor importante, fiecare cu fișă proprie ulterior.
10. `/romania-utila/legi-explicate/` — explicații pe înțelesul cititorului, cu textul oficial ca sursă primară.

## Ce trebuie să conțină fiecare pagină

- titlu clar, orientat pe intenția de căutare;
- „Valabil la data de …” vizibil;
- valoarea / regula curentă pusă într-un bloc scurt de tip rezumat;
- sursa oficială primară și data verificării;
- „Ce înseamnă pentru tine” în limbaj simplu;
- condiții / excepții;
- pași practici când este o procedură;
- întrebări frecvente doar pentru întrebări reale și distincte;
- istoric minim când valoarea se modifică în timp;
- linkuri interne către paginile conexe;
- ultima actualizare fără a modifica URL-ul.

## Regula datelor

AI-ul poate rezuma, clasifica și reformula, dar **nu inventează valori, date, plafoane sau condiții**. Valorile provin dintr-o sursă oficială identificabilă. Orice câmp numeric din pagina publică trebuie să poată fi urmărit până la sursa și data de verificare.

Pentru informația volatilă, modelul de date trebuie să permită:

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

## Arhitectură SEO

Ierarhia publică:

`IZZ.ro → România Utilă → domeniu → pagină permanentă → instrument / explicație`

Știrile care tratează aceeași temă trimit spre pagina permanentă. Pagina permanentă trimite înapoi spre cele mai relevante știri recente, dar nu depinde de existența lor pentru a fi utilă.

Nu se creează sute de pagini subțiri doar pentru variații de cuvinte-cheie. Fiecare URL nou trebuie să aibă o întrebare distinctă și o sursă utilă.

## MVP de instrumente interactive

După primele pagini statice, ordinea propusă este:

1. calculator salariu net;
2. calculator termen / calendar fiscal;
3. calculator alocație / beneficiu pe situație;
4. verificator „ce acte îmi trebuie pentru …”.

Instrumentele reutilizează aceleași date structurate ca paginile informative; nu duplică valorile în JavaScript fără o sursă unică.

## Criteriu de lansare

Nu lansăm un volum mare din prima. Prima felie este **3 pagini complete + 1 instrument**. Fiecare trebuie să aibă sursă primară, dată de verificare, legături interne și test de randare.

După indexare se măsoară separat de știri: impresii, CTR, poziții, intrări organice și reveniri. Doar paginile care primesc cerere reală primesc extindere în serii.

## Nu facem încă

- agregator separat de știri pentru „România Utilă”;
- sute de pagini generate doar din șabloane;
- valori preluate din bloguri ca sursă primară;
- calculator care conține reguli fiscale hard-codate în mai multe locuri;
- schimbarea URL-ului când se schimbă anul sau valoarea.

## Felia 1

Livrabilul concret este o zonă permanentă cu primele 3 pagini:

- salariul minim;
- alocații;
- calendar ANAF;

plus un calculator salariu net alimentat din aceeași sursă de date.

Succesul feliei = utilizabilitate mobilă, date trasabile, build determinist și URL-uri stabile; traficul se măsoară după publicare, nu se presupune.