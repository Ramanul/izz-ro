# Raport SEO-TTL — cohortă URL expirate (izz.ro)

URL-uri de site prezente în snapshot-ul vechi și absente din `origin/main` acum — de verificate lunar în Search Console (impressions / clicks / avg. position).

- Generat: 2026-10-01
- Fereastră: 30 zile
- Comit vechi: `3a031a2e1825` (2026-09-01T15:20:44Z)
- Comit curent (origin/main): `09bb38517da1` (2026-10-01T18:09:34+03:00)
- URL construit ca `https://izz.ro/{category}/{slug}/`
- Comandă: `python tools/seottl_raport.py --days 30`

## Contoare

| Metrică | Valoare |
|---|---|
| Intrări în `articles.json` la comitul vechi | 12895 |
| Din ele cu format invalid (fără category/slug valide) | 165 |
| URL-uri unice de site în vechi | 12709 |
| Intrări în `articles.json` în main acum | 20265 |
| Din ele cu format invalid | 326 |
| URL-uri unice de site în main acum | 19900 |
| **URL-uri expirate (în vechi, absente acum)** | **12672** |

## Cohorte, pe vârsta publicării (azi − published)

- 21-60 zile: **12672** URL-uri
- 61+ zile: **0** URL-uri
- sub 21 zile: **0** URL-uri
- fara data parsabila: **0** URL-uri

## Cohorta 21–60 zile — 12672 URL-uri

Publicate între 2026-08-02 și 2026-09-10 inclusiv. Acestea sunt cele mai proaspete scoateri — traficul rezidual e așteptat să scadă treptat.

Exemple (primele 20 din 12672):

- https://izz.ro/auto/grupul-chinez-chery-a-depasit-20-de-milioane-de-autovehicule-vandute-global/ (publicat 2026-08-03)
- https://izz.ro/discounturi/preturile-mici-atrag-romanii-pe-platformele-temu-shein-si-aliexpress/ (publicat 2026-08-03)
- https://izz.ro/extern/pretul-petrolului-a-scazut-pe-fondul-negocierilor-sua-iran/ (publicat 2026-08-03)
- https://izz.ro/extern/uniunea-europeana-solicita-intarirea-frontierelor-dupa-incidentele-din-ceuta/ (publicat 2026-08-03)
- https://izz.ro/general/seceta-extrema-scoate-la-iveala-artefacte-istorice-din-albia-dunarii/ (publicat 2026-08-03)
- https://izz.ro/judetean/compania-timiseana-world-mediatrans-isi-extinde-operatiunile-in-africa-de-nord/ (publicat 2026-08-03)
- https://izz.ro/local/anunt-achizitie-directa-proiect-modernizarea-si-eficientizarea-sistemului-de/ (publicat 2026-08-03)
- https://izz.ro/local/anunt-aplicare-tratamente-pentru-combaterea-insectelor-07-08-2026/ (publicat 2026-08-03)
- https://izz.ro/local/anunt-colectiv-pentru-comunicarea-prin-publicitate-nr-57609-din-30-07-2026/ (publicat 2026-08-03)
- https://izz.ro/local/anunt-concurs-2/ (publicat 2026-08-03)
- https://izz.ro/local/anunt-privind-rezultatele-finale-la-concursul-examenul-pentru-ocuparea-postului/ (publicat 2026-08-03)
- https://izz.ro/local/anunt-puz-2/ (publicat 2026-08-03)
- https://izz.ro/local/anunt-puz/ (publicat 2026-08-03)
- https://izz.ro/local/atacantul-alibek-aliev-a-comentat-concurenta-cu-jovo-lukic-la-u-cluj/ (publicat 2026-08-03)
- https://izz.ro/local/comuna-brazi-in-calitate-de-autoritate-publica-tutelara-asistata-de-expert/ (publicat 2026-08-03)
- https://izz.ro/local/comunicat-de-presa-3/ (publicat 2026-08-03)
- https://izz.ro/local/comunicat-de-presa-incheiere-proiect/ (publicat 2026-08-03)
- https://izz.ro/local/gigi-becali-l-a-criticat-dur-pe-tanarul-padurariu-dupa-meciul-cu-farul/ (publicat 2026-08-03)
- https://izz.ro/local/inscrieri-sambata-22-08-2026-evaluare-medicala-gratuita-omv-petrom-sustine/ (publicat 2026-08-03)
- https://izz.ro/local/lista-autorizatiilor-de-desfiintare-emise-in-iulie-2026/ (publicat 2026-08-03)

## Cohorta 61+ zile — 0 URL-uri

Publicate înainte de 2026-08-02. Vechi de peste două luni — dacă mai aduc impressions, e semnal că merită redirect, nu lăsare în 404.

Niciun URL în această cohortă.

## Expirate sub 21 zile (neasteptat) — 0 URL-uri

Logic imposibil pentru o scoatere într-o fereastră de ≥21 zile: cel mai probabil articol re-publicat sau anomalie de date. De verificat manual dacă apar.

Niciun URL în această cohortă.

## Expirate fără dată de publicare parsabilă — 0 URL-uri

Câmpul `published` lipsea sau n-a putut fi parsat — nu se pot cohorta pe vârstă.

Niciun URL în această cohortă.

## Metodă și limite

- Comparația e pe URL derivat din starea pipeline-ului (`data/articles.json`), nu din pagini publicate efectiv: dacă starea include articole intrate în pipeline dar nemoderate/nepublicate, ele apar și ele în listă — de filtrat la verificare.
- Un articol mutat în altă categorie apare ca „expirat” pe URL-ul vechi (și ca nou pe cel actual) — de verificat dacă URL-ul vechi face redirect.
- Vârsta se calculează la data generării raportului, nu la data scoaterii URL-ului.

## Checklist Search Console — ce măsor lunar, per cohortă

Pentru fiecare din cele două cohorte (21–60 zile, 61+ zile):

1. Search Console → Performanță → Rezultate de căutare; interval: ultimele 28 de zile.
2. Filtru: **Pagină** → URI-uri de pagină; lipește URL-urile cohortei (în seri dacă lista e mare, sau folosește Export și procesează în spreadsheet).
3. Măsoară per cohortă: **Impressions** (de câte ori URL-ul a apărut în rezultate), **Clicks**, **Avg. position** (poziția medie; ≤10 = prima pagină).
4. Semnale de urmărit:
   - Impressions > 0 pe URL expirat: mai primește afișări — candidat la redirect 301.
   - Avg. position bună (prima pagină) pe URL expirat: pierdere reală de SEO — prioritate la redirect.
   - Clicks pe URL expirat: utilizatori ajung pe 404 — de corectat repede.
5. Compară cu raportul lunii trecute: scădere lentă de impressions = normal după scoatere (TTL); cădere bruscă = ceva s-a schimbat la indexare.

Raportul se regenerează cu `python tools/seottl_raport.py` (`--days N` pentru altă fereastră, `--out DIR` pentru alt folder).
