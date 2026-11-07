# Studiu de caz — Eroarea factuală „penalty Mbappé” (CM 2026) și garda mecanică

> Data: 2026-11-07. Fix livrat pe branch `arena/e234d218-izz-ro` (PR în coadă).
> Eroarea s-a petrecut în iulie 2026 (copiii indexată), nu e în starea curentă a repo-ului.

## 1. Eroarea

În iulie 2026, pe izz.ro (copiii indexată), au apărut intrări contradictorii despre
penalty-ul lui Kylian Mbappé din meciul **Franța – Maroc 2-0** (sferturi de finală
Cupa Mondială 2026, 9 iulie 2026, Foxborough/Boston):

- o intrare spunea că Mbappé a **ratat** penalty-ul;
- alta spunea că l-a **transformat**.

Nicio sursa serioasă nu spune că a transformat penalty-ul. Faptele reale (verificate
mecanic pe surse independente: BBC Sport, Sky Sports, News18, Türkiye Today, ProSport,
Digisport, Stiripesurse, Antena Sport):

- min. 25: penalty pentru Franța (fault Mazraoui pe Mbappé);
- VAR ~3 min 10 sec — Mbappé **ratat**, apărat clar de portarul **Yassine Bounou (Bono)**;
- min. 60: Mbappé marchează din acțiune (gol superb);
- min. 66: Mbappé asistă la golul lui Ousmane Dembele;
- Franța câștigă 2-0, se califică în semifinale.

## 2. Modul de formare a erorii (ipoteza susținută de surse)

AI-ul (sinteză multi-sursă / model C) a confuzat titluri de tip „Mbappé marchează /
deschide scorul” (golul din min. 60) cu „Mbappé penalty” și a amestecat rezumate din
surse multiple înainte de clustering. Eroarea e una de **sintetizare** (modelul scrie
un fapt opus sursei), nu una de clustering sau de sursă.

## 3. Fixul — garda mecanică în `generator/verifica_sinteza.py`

Noua verificare `contradicție_cheie_penalty(rezumat, sursa)` compară rezultatul
penalty menționat în rezumat (titlu + rezumat) cu cel din textul sursei:

- rezumatul spune „transformat/marcat/înscris” în contextul penalty, dar sursa spune
  „ratat/apărat/irosit” acolo → semnal `contradicție_cheie`;
- rezumatul spune „ratat/apărat” în contextul penalty, dar sursa spune
  „transformat/marcat” acolo → semnal;
- dacă sursa menționează ambele rezultate (ex. ProSport: „a transformat penalty-ul.
  Cu Maroc, l-a ratat.”) nu se semnalează — verbele nu se pot atribui mecanic, e
  etapizat conservator.

Contextul nu e o fereastră de caractere, ci **propoziția** penalty-ului — și doar dacă
ea nu enunță un rezultat, propoziția următoare. Motivul e o măsurătoare, nu o preferință:

| Variantă | Sursa reală „…a ratat penalty-ul… . Francezul a marcat în minutul 60.” | Sursa Digisport (rezultatul în propoziția următoare) |
|---|---|---|
| fereastră 100 caractere | **tace** (propoziția 2 contaminează contextul) | prinde |
| doar propoziția penalty-ului | prinde | **tace** (propoziția penalty-ului nu spune rezultatul) |
| propoziție + fallback | prinde | prinde |

Prima variantă ar fi trecut testele naive și ar fi ratat exact cazul care a produs
eroarea; a doua ar fi ratat forma reală Digisport. Regula „citește ca un om” le prinde
pe amândouă, pentru că discriminatorul nu e distanța, ci dacă **propoziția penalty-ului
își spune singură rezultatul**.

**RAPORTEAZA, nu respinge** — codul `contradicție_cheie` e advisory (nu în
`_BLOCKING` din `raport_copiere.py`), ca toate verificarile noi; blocking-ul vine după
măsurarea ratei de fals pozitiv pe rulări reale (disciplina de la `cuvant_deformat_sursa`).

## 3b. Calibrare — ce s-a putut și ce nu s-a putut măsura

Pe corpusul din stare (`data/articles.json`, 7.324 articole + `data/deep_meta.json`;
14.722 texte scanate) există **4 mențiuni de penalty**, toate clasificate corect
(`penalti marcat`, `penalty-uri` la lovituri de departajare, `s-a cerut penalty`,
`lovitura de la 11 metri`). Zero semnale — deci zero falsuri pozitive *pe textul
disponibil*.

Ce **nu** se poate măsura offline: rata pe textul sursă la momentul publicării.
`process.py` șterge textul sursei după procesare (scrub juridic), iar
`tools/masoara_sinteza.py` raportează pe starea curentă **0 articole verificabile**
(1.277 fără AI, 6.047 fără sursă). Deci calibrarea reală se face din
`data/raport_copiere.jsonl`, pe măsură ce pipeline-ul rulează: acolo ajunge codul ca
`advisory_issue`. Pragul de blocking **nu** se activează pe baza acestui document.

## 4. Verificare

- `python -m pytest tests/test_verifica_sinteza.py -q` → 56 trecute (11 noi, inclus
  cazul Mbappé cu formele reale Digisport/ProSport).
- `python -m pytest tests/ -q` → 3164 trecute, 4 sărite, 8 xfailed.
- `python -m ruff check .` → curat.
- `python -m generator.main --render-only` → build OK (6797 articole).

## 4b. Falsuri pozitive evitate deliberat

- **„Codul penal / dosar penal”** — beatul juridic al site-ului, nu fotbal: tiparul
  penalty nu are `\bpenal\b` gol, doar `penalty`, `penalti*`, `penalul`.
- **Lovitura de departajare decisă la penalty-uri** — fără verb de rezultat în
  propoziție, nu se leagă niciun rezultat (corect: nu e un penalty ratat).
- **Știre despre o fază cerută, nu dictată** („s-a cerut penalty și s-a demontat
  critica”) — fără verb de rezultat, tace.

## 5. Îmbunătățiri complementare propuse (nu implementate aici)

- prompt-uri mai stricte pentru „penalty outcome” (few-shot: ratat vs. transformat);
- afișarea unui marcaj „conflict” în transparență pe articole sportive;
- human-in-the-loop prioritar pe evenimente sportive majore.
