# Proba de structură — starea `articles.json` + distribuția pe surse

Data: 2026-10-01 · Ramură: `claude/story-proba-structura` · Partea ușoară a probei de clustering STORY.

**Metoda:** `py notes/story-intelligence/proba_structura.py` — încarcă integral `data/articles.json`
(23.257.879 bytes, citire, fără modificare) și printează masurătorile de mai jos. `NOW` = momentul
rulării = 2026-10-01T09:53 UTC. Fereastra „ultimele N zile": `NOW - N zile <= published <= NOW`
(articolele future-dated rămân în afara oricărei ferestre).

## 1. Structura

- **Total articole: 20.238.** — numărarea elementelor din lista JSON (`len(data)`).
- **Date `published`:** toate parsabile (0 erori), interval 2026-09-11T06:08Z → 2027-01-01T00:00Z;
  **1 articol** are published în viitor față de momentul rulării (2027-01-01, sursa `pl_timis_voiteg`
  — data unui anunț programat preluată ca published). Fără el, starea acoperă **21 de zile
  calendaristice** (2026-09-11 → 2026-10-01).
- **Inventarul câmpurilor reale** (listate de script peste toate articolele; „present" = cheia
  există, „populated" = non-null/non-gol):

| Câmp | Tip(uri) observate | Present | Populated |
|---|---|---|---|
| `url` | str | 20.238 | 20.238 |
| `original_link` | str | 20.238 | 20.238 |
| `source` | str | 20.238 | 20.238 |
| `source_name` | str | 20.238 | 20.238 |
| `source_lang` | str | 20.238 | 20.238 (ro 18.179, en 1.485, it 574) |
| `title` | str | 20.238 | 20.238 |
| `category` | str | 20.238 | 20.238 (12 valori; top: local 6.090, sport 3.279, extern 2.275) |
| `published` | str (ISO 8601 cu tz) | 20.238 | 20.238 |
| `model` | str | 20.238 | 20.238 (`B` 19.105, `C` 1.133) |
| `src_extra` | int | 20.238 | 20.238 |
| `processed_by` | str | 20.238 | 20.238 (`gemini` 18.530, `official` 1.708) |
| `featured` | bool | 20.232 | 20.232 |
| `slug` | str | 19.901 | 19.901 |
| `teaser` | str | 19.365 | 19.365 |
| `entities` | list[str] | 18.530 | 17.529 (44.970 de string-uri în total) |
| `ai_cat` | str | 18.530 | 18.229 |
| `icon` | str / null | 18.530 | 18.275 (255 null) |
| `prompt_version` | str | 18.530 | 18.530 |
| `sources` | list[{name,url}] | 1.133 | 1.133 |
| `first_source` | str | 1.133 | 1.133 |
| `synthesis` | str | 1.133 | 1.133 |
| `updated` | str | 394 | 394 |
| `event_chart` | dict | 57 | 57 |

Nu există câmpuri dincolo de aceste 23 (inventarul e calculat pe toate articolele, nu pe un eșantion).

## 2. Sinteza multi-sursă

- Căutate: `is_synthesis`, `article_type`, `type`, `cluster`, `related` — **toate absente**.
- Ce există real: `synthesis` (textul sintezei), `sources` (lista articolelor-sursă `{name,url}`),
  `first_source` și `model == "C"`. **Toate cele patru marchiază exact același set de 1.133 de
  articole** (verificat: seturi identice pe URL). — script secțiunea 2.
- **1.133 sinteze din 20.238 (5,6%)**; restul, 19.105, au `model = "B"`.
- Referințe de sursă în interiorul sintezelor: **2.823**, mediană **2/sinteză**
  (histogramă: 2 surse × 817, 3 × 208, 4 × 48, … max 12).
- **Doar 454 din 2.823 (16,1%) referințe se regăsesc ca articol separat în stare** — sinteza
  înlocuiește articolele-sursă în starea păstrată; restul trăiesc doar ca URL + nume în `sources`.
- **Distribuția pe zile** (sinteze/zi, UTC): 2026-09-11: 45, 09-12: 75, 09-13: 44, 09-14: 66,
  09-15: 61, 09-16: 61, 09-17: 76, 09-18: 66, 09-19: 52, 09-20: 62, 09-21: 44, 09-22: 70,
  09-23: 51, 09-24: 52, 09-25: 66, 09-26: 59, 09-27: 40, 09-28: 35, 09-29: 37, 09-30: 61,
  10-01 (până la 09:53): 10. **Ultimele 14 zile: 781 sinteze** — flux constant de ~40-75/zi.

## 3. Surse (ultimele 30 de zile)

- **347 de surse distincte** au livrat ≥1 articol în fereastră; **187 de surse** au livrat în
  ultimele 48h. — numărare pe `source` distinct.
- Atenție la fereastră: starea conține doar 21 de zile calendaristice (11 sep → 1 oct), deci
  „ultimele 30 de zile" = efectiv toată starea (20.237 din 20.238 articole).
- **Top 15 surse după volum** (count | mediană articole/zi | max/zi; mediana calculată pe cele
  21 de zile calendaristice acoperite de stare, zilele fără livrări = 0):

| Sursă | Articole | Mediană/zi | Max/zi |
|---|---|---|---|
| `adevarul` (Adevărul) | 605 | 30 | 39 |
| `fcinter1908` (FC Inter 1908) | 574 | 28 | 36 |
| `prosport` (ProSport) | 564 | 29 | 39 |
| `gsp` (GSP) | 559 | 27 | 37 |
| `profit` (Profit.ro) | 517 | 24 | 34 |
| `hotnews` (HotNews) | 507 | 26 | 31 |
| `extern` (Digi24 Extern) | 501 | 24 | 31 |
| `as_ro` (Antena Sport) | 490 | 23 | 34 |
| `antena3` (Antena 3 CNN) | 480 | 22 | 35 |
| `g4media` (G4Media) | 479 | 24 | 32 |
| `xda` (XDA Developers) | 479 | 25 | 29 |
| `spotmedia` (Spotmedia) | 473 | 22 | 29 |
| `protv` (Știrile ProTV) | 472 | 22 | 33 |
| `dobrogeaonline` (Dobrogea Online) | 466 | 24 | 28 |
| `sportro` (Sport.ro) | 461 | 21 | 31 |

## 4. Fereastra (ce ar opera un clustering real)

- **13.795 articole în ultimele 14 zile** (`NOW-14z <= published <= NOW`); 20.237 în ultimele
  30 de zile (= starea întreagă); în afara ferestrelor: 1 articol future-dated.
- Un clustering pe 14 zile ar procesa deci ~14k articole + 781 sinteze deja marcate.

## 5. Geo / local

- **Nu există câmp dedicat de localitate/județ pe articol** (căutare după `geo/local/county/
  judet/city/place` în numele câmpurilor: zero rezultate).
- **46 de articole** au `event_chart.localitate` populat (toate `tip: meteo`; cele 11 `cutremur`
  nu au localitate) — singurul loc cu localitate structurată din stare.
- Substitute existente (proxy, nu câmp geo): `category` în (`local`, `judetean`) = **6.658
  articole**; id-uri de sursă cu prefix `pl_` (primării, interpretare din `source_name`) =
  **258 de surse, 1.802 articole în ultimele 30 de zile**.

## Ce NU dovedește

1. **Nu dovedește că articolele se pot grupa semantic corect.** Am măsurat doar că există un
   marker de sinteză și volum suficient; dacă două titluri despre același eveniment se recunosc
   (similaritate, entități comune, contradictorii) e testul părții grele a probei, nu al acesteia.
2. **Nu dovedește că grupurile pot fi reconstruite din stare.** Doar 454/2.823 referințe-sursă
   ale sintezelor mai există ca articole separate; orice „story" care ar vrea articolele-sursă
   complete lângă sinteză depinde de URL-urile din `sources`, nu de articole prezente.
3. **Nu dovedește fezabilitatea grupării locale.** Câmpul de localitate lipsește (46/20.238
   structurat); un clustering local ar trebui derivat din `category`, `entities` sau id-ul sursei,
   iar acuratețea acestei derivări nu e măsurată aici.

**Ce m-ar face să greșesc:** cifrele de fereastră (14/30 zile, 48h) depind de momentul rulării
starea e o fereastră rulantă de ~3 săptămâni; rerularea în altă zi dă valori ușor diferite,
deși ordinele de mărime rămân.

## Concluzie

Structura actuală suportă deja marcatele unui model STORY — 1.133 sinteze distincte prin
`model: C` + `synthesis` + `sources`, la un flux stabil de ~40-75 sinteze/zi peste ~14k
articole/2 săptămâni — dar starea nu conține niciun câmp de cluster, iar articolele-sursă ale
sintezelor nu mai sunt păstrate ca articole, deci gruparea propriu-zisă trebuie construită, nu
citită din stare.
