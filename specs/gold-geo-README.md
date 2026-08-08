# Set de aur — atribuire geografică (2026-08-08)

`gold-geo-2026-08-08.tsv` — 40 de articole judecate **manual**, articol cu articol, de claude-A.
Există fiindcă până acum fiecare măsurătoare de clasificare a fost aruncată după ce a fost făcută
(`WS-0027`: 60 de articole judecate pe 7 august, etichetele pierdute). Fără set de aur nu se poate
spune „am reparat", doar „am schimbat".

## Cum a fost ales eșantionul — determinist, reproductibil

```python
esantion = (sorted([a for a in arts if a['category']=='local'], key=lambda a: md5(a['url']))[:20]
          + sorted([a for a in arts if a['category']=='zonal'], key=lambda a: md5(a['url']))[:20])
```

Cheia de rejoin e `url`, nu indexul: corpusul are TTL de 7 zile, deci aceeași rețetă rulată peste
o săptămână dă alt eșantion. Articolele expirate se marchează absente, nu se reetichetează.

## Coloane

`cat_corecta` — rubrica pe care ar trebui să stea, după regula proprietarului (LOCAL = unde se
întâmplă · sportul iese de pe axa geografică, #155 · niciun loc subiect → rămâne pe temă).
`loc_corect` — localitatea/județul despre care e articolul, fără diacritice.
`badge_verdict` — `ok` · `imprecis` (adevărat dar mai puțin specific decât se putea) · `gresit`.

## Ce spune, la data scrierii (înainte de #165)

| măsură | cifră |
|---|---|
| rubrică stocată ≠ rubrică corectă | **15 / 40** |
| badge `ok` | 25 / 40 |
| badge `imprecis` | 7 / 40 |
| badge `gresit` | 8 / 40 |

Cele 15 se descompun: 6 sport pe axa geografică (acoperit de #155, fereastră oarbă), 8 nivel greșit
`zonal` în loc de `local` (cauza: `_resync_pinned`, reparat de #165), 1 scurgere curată (știre
națională pe rubrică zonală, care cere AI).

Din cele 7 `imprecis`, **5 au localitatea chiar în id-ul sursei** (`pl_alba_oras_zlatna` → badge
„Alba" în loc de „Zlatna"). E metoda `dedicated_source`, cea mai precisă din cele șase documentate
de NewsCatcher, și la noi nu costă nici AI, nici text nou.

## Cum se folosește

Orice felie care atinge clasificarea sau badge-ul se măsoară față de fișierul ăsta ÎNAINTE și DUPĂ.
Un fix care mută cifre fără să miște setul de aur n-a demonstrat nimic.
