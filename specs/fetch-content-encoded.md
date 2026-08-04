# fetch: citește și `<content:encoded>`, nu doar `<description>`

**Scop.** `fetch.py` pierde corpul articolului la feedurile care îl trimit în `<content:encoded>`.
`feedparser` pune acel conținut în `entry.content[0].value`, iar `_fetch_one` citea doar
`entry.get("summary") or entry.get("description")`. Itemul ieșea fără substanță și era respins
tăcut de `_quality_gate` — un defect de FETCH raportat până acum ca defect de SURSĂ.

**Măsurat 2026-08-04, pe feeduri live, nu presupus — și cu o corecție proprie.** Prima măsurătoare
a comparat lungimea HTML **brută** și a dat „9 din 12 surse trimit un corp real". **Cifra aia era
umflată:** la majoritatea, `content:encoded` e markup și navigație, care după `clean_html` nu adaugă
niciun cuvânt. Măsurat corect, după curățare, pe 14 surse × 8 iteme:
**27 din 111 iteme (24%) trec pragul de `MIN_SUBSTANTA_CUVINTE` (5 cuvinte peste titlu); 84 rămân
fără corp.** Câștigul e concentrat, nu uniform: `pl_neamt_municipiul_roman` sare de la `summary` gol
la o mediană de **112 cuvinte** peste titlu, în timp ce `pl_botosani_todireni`, `pl_suceava_oras_frasin`
și `pl_ialomita_oras_amara` rămân pe 0/8.

Contra-verificat pe `digisport`: are `content:encoded` pe toate cele 100 de iteme, dar **delta
maximă 0** față de `summary` — acolo sursa chiar nu trimite nimic peste titlu, deci #130 rămâne
corect pentru ea. Cele două cazuri nu se confundă.

**Consecință directă pentru #131:** felia 2 NU devine inutilă. 76% dintre anunțuri chiar n-au corp,
deci forma „titlu + link" rămâne necesară — dar se aplică unui set mai mic, iar 24% dintre iteme
primesc acum un teaser real în loc de `"Detalii pe sursa."`.

**Intrare / ieșire.** Intrare: un `entry` de la `feedparser`. Ieșire: `item["description"]` =
textul cel mai bogat pe care îl trimite feedul, curățat de HTML.

**Decizia de design și de ce.** Se alege candidatul cel mai lung **după** `clean_html`, nu înainte:
un `content` plin de markup poate curăța mai scurt decât un `summary` de text simplu, iar
comparația pe HTML brut ar alege atunci varianta mai săracă. Nicio sursă nu pierde ce avea —
`summary` rămâne candidat, deci schimbarea nu poate decât să adauge text.

**Criterii de acceptare.**
1. `content:encoded` mai bogat decât `summary` → `description` îl ia pe el.
2. `summary` mai bogat după curățare → `description` rămâne `summary` (fără regresie).
3. Feed fără `content` → comportament identic cu cel de dinainte.
4. Nici `content`, nici `summary`, nici `description` → `""`, nu excepție.
5. Suita existentă rămâne verde; calea `sitemap_news` rămâne neatinsă (nu are corp prin format).

**Ce NU face felia asta.** Nu atinge poarta, nu atinge `process_*`, nu re-decide ce se publică.
Efectul asupra anunțurilor de primărie (#131) se măsoară DUPĂ ce fixul e în main.
