# Munca si consumul — jurnal comun A + B

> Generat din `specs/metrics.csv` cu `python tools/log_slice.py --report`.
> Ambele conturi scriu in el. Nu edita tabelele de mai jos manual — se suprascriu.
> **Generat: 2026-07-25 09:29 UTC** · ultimul slice raportat: 2026-07-25. Daca cele doua difera mult, raportul e vechi pentru ca jurnalul n-a fost completat, nu pentru ca n-a fost munca.

> **Cine lucreaza acum si ce e blocat** nu sta aici (s-ar invechi intre rulari), ci pe canalul live: [issue #83](https://github.com/Ramanul/izz-ro/issues/83) — intentia se anunta acolo INAINTE de a atinge fisiere.

**21 slice-uri** · **1461 linii** de diff · **~669k tokeni** raportati

## Pe cont

| cont | slice-uri | linii diff | ~tokeni (k) |
|---|---:|---:|---:|
| B | 21 | 1461 | 669 |

## Pe mod de lucru

| mod | slice-uri | linii diff | ~tokeni (k) | tokeni / 100 linii |
|---|---:|---:|---:|---:|
| solo | 16 | 1106 | 251 | 23 |
| agent | 3 | 306 | 394 | 129 |
| ci | 2 | 49 | 24 | 49 |

## Slice-uri, cele mai recente primele

| data | cont | slice | mod | linii | ~tok | note |
|---|---|---|---|---:|---:|---|
| 2026-07-25 | B | primarie-moarta-tacuta | ci | 4 | 11 | PR #90: feedcheck x2 confirma pl_vaslui_tacuta 403 WAF; slotul merge… |
| 2026-07-25 | B | ui-dark-subnav-manifest | agent | 41 | 160 | PR #91: --ink-3 pica contrastul in dark, 305 erori pa11y ascunse;… |
| 2026-07-25 | B | surse-catalog-complet | agent | 225 | 139 | PR #89: /surse/ arata 2 linkuri externe pe live; acum 189 surse, 121… |
| 2026-07-25 | B | cadence-docs-si-ci-nonblocking | solo | 37 | 26 | PR #88: CLAUDE.md zicea cron 30min, real 13 */2; reviewerii nu mai… |
| 2026-07-25 | B | ci-reviewer-read-access | solo | 9 | 18 | PR #86: reviewerii Claude picau pe ORICE PR - allowed-tools fara… |
| 2026-07-25 | B | review-fixes-85 | solo | 90 | 14 | review CodeRabbit: test fail-open inchis, limita 70, gramatica;… |
| 2026-07-25 | B | ghiduri-neverificate | solo | 150 | 32 | 3 ghiduri afisau ✅Verificat peste valori placeholder; steag… |
| 2026-07-25 | B | subnav-scroll-hint | solo | 12 | 9 | meniul de categorii: 805px ascunsi pe mobil fara niciun indiciu;… |
| 2026-07-24 | B | cost-dashboard | solo | 260 | 28 | jurnal CSV + COORD-DASHBOARD.md; A cedeaza artefactul, da datele… |
| 2026-07-24 | B | dead-primarii-denylist | ci | 45 | 13 | 174617f 12 primării moarte scoase; sloturile eliberate merg la… |
| 2026-07-24 | B | coord-live-channel | solo | 12 | 11 | issue #83 canal live; POST /pulls dă 500 pt ambele conturi |
| 2026-07-24 | B | impact-tier-wordboundary | solo | 22 | 7 | PR #81 bug real găsit de review-ul lui A: ORASTIOARA clasificat ca… |
| 2026-07-24 | B | impact-first-120 | solo | 30 | 14 | PR #80 regulă statică municipiu>oraș>comună; 35 → 120 de primării |
| 2026-07-24 | B | regional-sources | agent | 40 | 95 | PR #79 2 agenți cercetare (~46k fiecare) + feedcheck: 16 din 21 vii |
| 2026-07-24 | B | spec-parallel-fetch | solo | 55 | 8 | PR #73 spec fetch paralel; executat de A, 6x mai rapid |
| 2026-07-24 | B | spec-geo-categorii | solo | 62 | 9 | PR #66 spec pentru executor; premisele au expirat în ore — lecție |
| 2026-07-24 | B | two-tier-nav | solo | 57 | 20 | PR #63 meniu 2 niveluri + etichete localizate + scos piataauto mort |
| 2026-07-24 | B | county-papers-pin | solo | 62 | 15 | PR #62 7 ziare județene + PINNED_CATEGORIES (axa geografică) |
| 2026-07-24 | B | monitor-local-engine | solo | 210 | 22 | PR #60 motor html_list generic + scrape_probe + probe.yml; 7 teste… |
| 2026-07-24 | B | taxonomy-local | solo | 34 | 12 | PR #59 categoria local + SEED_CATEGORIES; 16 candidați, feedcheck a… |
| 2026-07-24 | B | brand-tagline | solo | 4 | 6 | PR #57 siglă: Informația Zilei / Portalul știrilor tale |

---

## Ce costa efectiv

Contraintuitiv, si e important ca sa nu se optimizeze lucrul gresit (masurat de contul A prin API, 2026-07-24):

| resursa | cost | de ce |
|---|---|---|
| minute GitHub Actions | **zero** | repo public → minute gratuite si nelimitate; 129 min intr-o zi = 0 lei |
| tururi de conversatie | **cota Claude a owner-ului** | resursa cu adevarat limitata; fiecare mesaj costa |
| rulari `pipeline` | **cota AI Gemini** | singurul workflow care consuma altceva decat minute |

**Regula care rezulta:** nu „rulati mai putine workflow-uri", ci **muta in Actions tot ce e mecanic si taie din tururile de conversatie**. CI-ul e cel mai ieftin executor pe care il avem, nu cel mai scump — si e singurul care ajunge la internetul real.

**Cum se citeste `tokeni / 100 linii`:** cost aproximativ al modului de lucru. Numarul mic = ieftin pentru cat livreaza. Coloana e utila abia dupa ~20 de randuri; sub atat, variatia intre slice-uri o face inselatoare.

**Tokenii sunt estimati de cel care raporteaza**, nu masurati automat — sunt un ordin de marime, nu o factura.

