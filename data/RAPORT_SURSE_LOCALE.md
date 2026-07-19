# Raport: site-urile administrației locale ca surse de informații pentru izz.ro

Scanat 2026-07-19 cu `tools/check_primarii.py` și `tools/check_institutii_judetene.py`.
Date brute: `data/primarii_status.csv` (3187), `data/institutii_judetene_status.csv` (84),
liste pe categorii în `data/primarii_lists/` și `data/institutii_lists/`.

## Primării (3187 scanate)

| Metrică | Nr. | % din total | % din vii |
|---|---|---|---|
| Vii (HTTP OK) | 2513 | 79% | — |
| Moarte (DNS/HTTP fail) | 674 | 21% | — |
| Confirmate site real de primărie | 2450 | 77% | 97% |
| **RSS/Atom funcțional** | **1652** | **52%** | **66%** |
| Conținut recent (2025–2026) | 1801 | 57% | 72% |
| **GOLD: real + RSS + conținut recent** | **1274** | **40%** | **51%** |

- CMS dominant: WordPress (1651 dintre vii; 1200 din lista GOLD) → feed la `/feed` standard.
- Platforme e-adm (222) — șabloane comune, comportament uniform, integrare în bloc posibilă.
- Lista de integrat direct: `data/primarii_lists/gold_integrare.csv` (1274 rânduri).

## Consilii județene (41 + PMB București)

- Vii: 36 la scanare + 3 confirmate manual cu SSL relaxat (Olt, Vâlcea — lanț de certificat
  incomplet; Neamț — DNS local capricios) → **39/42**. Gorj în mentenanță (503),
  Brăila și Prahova picate la momentul scanării.
- **RSS funcțional: 15** — Arad, Bihor, Botoșani, Buzău, Cluj, Călărași, Galați, Giurgiu,
  Ialomița, Iași, Ilfov, Sibiu, Timiș, Vaslui, Vrancea.
- Restul necesită scraper HTML (model `html_list` existent în `generator/fetch.py`).

## Prefecturi (42) — REZULTAT INVALIDAT

Toate pe platforma comună `*.prefectura.mai.gov.ro`. Scanările repetate au declanșat
WAF-ul MAI: primim 502 de pe acest IP inclusiv pe www.mai.gov.ro, dar check-host.net
(nod Israel) primește 200 OK. Deci NU sunt moarte — suntem blocați temporar.
NU re-scana prefecturile de pe acest IP; re-testare peste câteva zile, cu 1 worker
și pauze, sau din GitHub Actions (IP diferit; `feed_check.py` rulează deja acolo).

## Concluzii pentru integrare

1. **Faza 1 — RSS direct (efort mic, acoperire mare):** cele 1274 de primării GOLD +
   15 CJ-uri intră pe modelul existent `config.SOURCES`/`feed_check.py`. Practic
   jumătate din administrația locală vine „gratis", majoritatea WordPress.
2. **Faza 2 — e-adm în bloc:** un singur adaptor pentru cele 222 de site-uri e-adm.
3. **Faza 3 — scrapere `html_list`** pentru CJ-urile fără RSS și orașele mari fără feed.
4. **Nu investi** în cele 674 moarte; prefecturile se re-evaluează din CI după deblocare.
5. Operațional: validarea periodică a feed-urilor trebuie făcută din GitHub Actions, nu
   de pe IP-ul de acasă (lecția WAF).

## Limite cunoscute

- `last_signal_date` e best-effort (regex ISO pe RSS + fallback an din HTML) — datele RFC-822
  din RSS nu sunt parsate; 791 de site-uri vii nu au nicio dată detectată.
- Site-urile cu certificat SSL invalid apar „moarte" în scanare (fals negativ, câteva zeci).
- `is_primarie=unclear` nu înseamnă fals — adesea doar encoding vechi sau JS-rendered.
