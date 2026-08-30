# De ce dublează știrile — măsurat 2026-08-30, NU re-cerceta

> Dosarul e plătit o dată. Cifrele de aici vin din rulări reale pe `data/articles.json` de pe
> `main` (11.755 iteme), nu din citit cod. Înainte de orice schimbare pe `generator/cluster.py`,
> vezi §7: se verifică empiric pe eșantioane reale, ȘI over-merge ȘI under-merge.

## Cazul raportat de proprietar (captură de ecran, secțiunea REGIONAL)

Aceeași știre — un feribot cu ~270 de persoane scufundat lângă Ciprul de Nord — a ieșit ca
**patru** sinteze separate, nu două, toate pe 2026-08-30 în 11 minute:

| # | ora | sursă-lider | titlu sintetizat |
|---|-----|-------------|------------------|
| 0 | 11:29 | Economica | Un feribot cu aproape 270 de persoane la bord s-a scufundat în largul Ciprului de Nord |
| 1 | 11:37 | HotNews | Operațiuni de salvare în derulare după scufundarea unui feribot lângă Cipru |
| 2 | 11:39 | Spotmedia | O navă cu 270 de pasageri s-a răsturnat în Marea Mediterană, provocând o operațiune majoră de salvare |
| 3 | 11:40 | Adevărul | Un feribot cu aproximativ 260 de pasageri s-a scufundat în largul Ciprului |

Cardurile din captură sunt **0** și **2**.

## Cauza 1 — garda de entități a ucis o unire CORECTĂ (cea mai gravă)

Perechea 0~3 trecea pragul de absorbție cross-run: `inter=4`, `jac=0.44`, `_strict_match=True`.
A fost oprită de garda de entități din `attach_recent`, care a citit entitățile ca disjuncte:

    [0] ['Ciprul de Nord', 'Kyrenia', 'Murat Senkul', 'Erhan Arıklı']
    [3] ['Cipru']

`_entity_stems` taie la `STEM_LEN = 6`: „Ciprului" → `ciprul`, „Cipru" → `cipru`. Cinci litere,
deci rămâne întreg; șase, deci se taie cu articolul lipit. **Aceeași entitate, două stemuri
diferite.** Garda pusă contra over-merge-ului a produs un under-merge.

Clasa de defect e generală, nu un caz izolat: orice substantiv românesc de ≤6 litere ratează
potrivirea cu forma lui articulată (`cipru`/`ciprul`, `nava`/`navale`).

## Cauza 2 — vocabular disjunct: 0 tokeni comuni, 3 entități comune

Perechea 0~2 — exact cardurile din captură — nu împarte **niciun** token de titlu:

    [0] aproap bord ciprul feribo largul nord persoa scufun
    [2] majora marea medite nava operat pasage provoc rastur salvar
    inter = 0, jaccard = 0.00

Dar entitățile se suprapun pe trei: `Ciprul de Nord`, `Kyrenia`, `Erhan Arıklı`. Semnalul care
le-ar fi unit EXISTĂ deja în date. Arhitectura nu-l poate folosi: în `attach_recent` entitățile
sunt **doar veto**, niciodată dovadă PENTRU unire. Niciun prag pe Jaccard de titlu nu poate
repara asta — „feribot scufundat" vs. „navă răsturnată" sunt lexical străine.

## Cât de des — limita măsurătorii, spusă explicit

Pe ultimele 48h (979 articole), gruparea prudentă „≥2 entități stemuite comune" dă 136 de
grupuri cu ≥2 articole, 544 de articole prinse, iar **115** dintre grupuri conțin cel puțin o
pereche pe care niciun prag actual n-o unește.

**115 NU e numărul de dubluri.** Proxy-ul supra-grupează, verificat pe ieșire: `cluj`+`spital`
a legat un transfer de fotbalist de o inaugurare de centru medical, iar un grup de 27 de
articole ține tot ce atinge Dinamo/Corvinul. Cifra e o **limită superioară** și un semnal că
merită o măsurătoare adevărată, nu o estimare de citat. Singurul caz confirmat manual e Cipru.

## Cauza 3, separată — titlu care e doar o dată calendaristică

Două iteme publicate cu titlul format EXCLUSIV dintr-o dată, ambele de la aceeași sursă:

    2026-08-27T13:26  [CJ Giurgiu]  judetean  titlu='27.08.2026'  slug=27-08-2026
    2026-08-17T08:56  [CJ Giurgiu]  judetean  titlu='17.08.2026'  slug=17-08-2026

§7 e explicit: pipeline-ul nu publică niciodată titluri brute sau stricate — dacă o cale de
fallback nu atinge bara, **sare** itemul. Aici n-a sărit. Sursele oficiale locale ocolesc AI-ul
(`specs/local-official-no-ai.md`), deci titlul din feed ajunge nefiltrat pe site.

## Ce s-a facut si ce a ramas

- **F-A — LIVRAT.** `_entitati_se_ating()` în `generator/cluster.py`: un stem se atinge de altul
  doar dacă unul e PREFIXUL celuilalt și are ≥4 litere. Nu substring oriunde.
  **Verificat empiric pe ambele direcții (§7)**, pe 72h / 1.302 articole: 242 de perechi trec
  pragul de text; înainte uneau 233, acum unesc **234**. Diferența e de exact **+1**, iar acea
  pereche e chiar dublura Cipru raportată. Zero perechi pierdute — schimbarea doar relaxează
  veto-ul, nu atinge pragul de text.
- **F-B, structural:** entitățile devin dovadă POZITIVĂ (≥2 entități comune + aceeași zi ⇒
  același eveniment), nu doar veto. Repară cauza 2, dar e exact genul de schimbare pentru care
  §7 cere eșantioane pe ambele erori înainte de commit.
- **F-C — LIVRAT.** `titlu_e_doar_o_data()` în `generator/util.py`, aplicat în `main.py` chiar
  după filtrul de `skip`. Îngust dinadins: „Anunt 27.08.2026" rămâne titlu valid.
  `tests/test_titlu_doar_data.py`, 3 teste, inclusiv direcția inversă.

**Rămâne F-B**, singura care repară cauza 2 — cardurile din captură, cu 0 tokeni comuni. F-A nu
le atinge: pragul de text nu e trecut deloc, deci veto-ul de entități nici nu ajunge să conteze.
E schimbarea structurală, cea care cere eșantioane pe ambele erori înainte de commit.
