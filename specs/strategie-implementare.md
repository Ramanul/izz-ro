# IZZ — harta implementării strategiei

Sursa: `strategie cu detalii.pdf`, 26 pagini. Documentul propune 37 de direcții și recomandă testarea inițială a IZZ Leads, IZZ Business Monitor, IZZ Actions, apoi Market Intelligence, Tools, Commerce și Events.

## Stare

| # | Direcție | Stare | Fundație |
|---:|---|---|---|
| 1 | Ce înseamnă pentru mine? | foundation | Actions + corpus |
| 2 | Radar pentru profesia mea | foundation | monitors |
| 3 | Radar pentru compania mea | foundation | entities + monitors |
| 4 | Monitorizează concurentul | foundation | entities + observations |
| 5 | Oportunități pentru firma mea | foundation | opportunities |
| 6 | IZZ Opportunity Score | implemented | intelligence engine |
| 7 | IZZ Business Radar | foundation | opportunities + entities |
| 8 | IZZ Grants Radar | foundation | public-data adapters |
| 9 | Lead marketplace | foundation | lead schema + deterministic matcher |
| 10 | IZZ Oferte | foundation | lead schema |
| 11 | IZZ Local Business Index | foundation | entities + provider index |
| 12 | IZZ Verified | foundation | entities + observations |
| 13 | IZZ Company Pages | foundation | entities + SSG |
| 14 | Institution Monitor | foundation | monitors + observations |
| 15 | Topic Monitor | foundation | monitors + observations |
| 16 | Dosarele IZZ | foundation | observations |
| 17 | IZZ „Ce s-a schimbat?” | implemented | company monitor changes |
| 18 | Comparatorul de România | foundation | tools + normalized observations |
| 19 | IZZ calculator → afiliere | foundation | tools |
| 20 | IZZ Job Radar | foundation | future public-data adapter |
| 21 | IZZ Salary Intelligence | foundation | tools + observations |
| 22 | IZZ „Ce se construiește?” | foundation | projects + places |
| 23 | Harta banilor publici | foundation | opportunities + observations |
| 24 | IZZ Market Intelligence | implemented | static contract + market cards |
| 25 | Vânzarea datelor / IZZ Data | foundation | D1 schema + export table |
| 26 | White-label IZZ | foundation | tenant-ready owner_key in monitors |
| 27 | IZZ pentru agenții | foundation | tenant-ready monitors |
| 28 | IZZ Reputation Monitor | foundation | observations + monitors |
| 29 | IZZ AI Research | foundation | structured observation corpus |
| 30 | IZZ Reports | foundation | data_exports + observations |
| 31 | „Top 100” sponsorizat | foundation | normalized market data |
| 32 | Evenimente IZZ | implemented | static events contract |
| 33 | Premiile IZZ | foundation | events + commerce |
| 34 | Membrii IZZ / IZZ Club | foundation | owner/session abstraction |
| 35 | Commerce media | implemented | commerce contract |
| 36 | IZZ Actions | implemented | reusable action engine + UI |
| 37 | Infrastructură comună de date | implemented | D1 schema + contracts |

## Criteriul de completare a unei direcții

O direcție nu devine `implemented` doar pentru că există un ecran. Trebuie să aibă:

1. model de date stabil;
2. sursă verificabilă sau contract clar pentru sursă;
3. logică testabilă;
4. interfață sau export utilizabil;
5. mecanism de persistență pentru starea care trebuie păstrată;
6. verificări automate relevante.

`foundation` înseamnă că infrastructura necesară există, dar produsul nu este încă livrat end-to-end cu date reale și operațiuni de producție.

## Prioritatea de execuție

**Valul A:** Leads → Business Monitor → Actions.

**Valul B:** Market Intelligence → Tools → Commerce → Events.

**Valul C:** Grants → Company Pages → Institution/Topic Monitors → Dosare → public money → Job/Salary intelligence.

**Valul D:** API/Data → White-label → Agencies → Reputation → AI Research → Reports → rankings → membership.

Documentul strategic descrie direcția comercială, dar nu furnizează specificații suficiente pentru autentificare, prețuri, contracte cu furnizorii sau condiții juridice. Acestea rămân de implementat după definirea surselor și a fluxurilor reale, nu se inventează din exemplele din PDF.
