# Inventar: funcții existente care pot răni (2026-11-28)

Felia 1, PR 1. Citit din cod, nu rulat pe live. Decizia e a proprietarului unde scrie „decide Alexandru".
Referință măsurată: `python tools/audit_ton.py` — 472 din 26.239 titluri (1,8%) sunt „subiect greu"; 411 prin lexicul de precizie, 61 prin cel contextual.

| # | Funcție | Unde | Poate răni când | Stare acum | Propunere |
|---|---|---|---|---|---|
| 1 | Butoane „Distribuie" (Facebook, WhatsApp, LinkedIn) | `templates/article.html:262-267` | un articol despre moarte sau viol e împărtășit ca să șocheze sau să umilească | Active pe orice articol | Decide Alexandru: ascunse la `subiect_greu` (PR 3) |
| 2 | Articolul greu ca „lead" pe prima pagină | `templates/index.html:28-49` (`hero`) | prima imagine a vizitatorului e o moarte | Selecția nu ține cont de ton | Decide Alexandru; nu se atinge în Felia 1 (selecția paginii principale e în „Nu se atinge") |
| 3 | Fotografie reală la articolul greu | `templates/_art.html`, `article.html:104` | imaginea unei victime reale | Se arată fotografia/ilustrația locală ca la orice articol | Decide Alexandru; nemăsurat câte articole grele au portret |
| 4 | Alerte push („o alertă pe zi, numai ultimă oră") | `templates/base.html:173-183`, `static/push.js`; trimiterea e în Worker | o alertă despre moarte ajunge pe ecranul blocat | Trimiterea nu e în acest repo; NU verificat aici dacă filtrează tonul | Verificare în Felia 2 (Worker) |
| 5 | Titluri cu violență ca metaforă | generate în `generator/process.py` | „a spulberat", „devastator" pe subiecte obișnuite | 3 din 26.239 titluri (contor: `ton.violenta_in_titlu`) | Regulă de prompt în PR 2 |
| 6 | Căutare și carduri fără semn | `static/search.js`, `templates/_card.html` | cititorul dă peste subiectul greu fără avertisment | Niciun semn | Semn „Subiect greu" pe card în PR 3 |

Nimic din acest tabel nu e oprit prin PR 1: PR 1 doar măsoară și scrie lista. Opririle se fac în PR 2 și PR 3, după decizia pe rândurile 1-3.
