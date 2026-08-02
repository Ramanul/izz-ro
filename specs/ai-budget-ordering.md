# Slice S1 — ordinea in care itemele consuma bugetul AI

**Scop.** Bugetul AI e saturat la FIECARE rulare, iar ordinea in care itemele il consuma
e ordinea din `config.SOURCES` (invariant declarat in `fetch.py:560`: „ce ajunge la coada
e infometat"). Sub saturatie permanenta, ordinea aia functioneaza ca politica editoriala
nedeclarata. Inlocuim ordinea de configurare cu doua criterii neutre, calculabile INAINTE
de orice apel AI: coroborare (nr. de domenii distincte dintr-un cluster) si prospetime.

**Masuratoare care motiveaza slice-ul** (loguri `build.yml`, 2026-08-02, buget 18 − rezerva 8 = 10):

| rulare | iteme noi | B | C | apeluri |
|---|---|---|---|---|
| 13:49 | 261 | 0 | 10 | 10/10 |
| 15:14 | 252 | 20 | 8 | 10/10 |
| 17:11 | 244 | 40 | 6 | 10/10 |

**Intrari.** `new_items` (fetch), `groups` (cluster) — neschimbate.
**Iesiri.** Aceleasi articole procesate, in alta ordine, plus `stats["deferred"]` =
cate iteme noi n-au primit AI in rularea asta.

**Criterii de acceptare.**
1. Un cluster cu 3 domenii distincte consuma buget inaintea unuia cu 2, la orice ordine de intrare.
2. La egalitate de domenii, clusterul cu cel mai proaspat membru intra primul.
3. `singles` se proceseaza in ordinea prospetimii, nu in ordinea din `config.SOURCES`:
   cu buget de un singur apel, itemul proaspat de la coada listei intra, cel vechi din capul ei nu.
4. `stats["deferred"]` numara exact itemele noi ramase fara AI (nici procesate, nici absorbite).
5. Nimic din ce se publica nu se schimba la buget nelimitat — doar ordinea.

**Ce NU face acest slice.** Nu introduce un scor de importanta produs de AI (aia e S3) si nu
inventeaza o ierarhie de surse — o lista de prioritati pe surse e decizie editoriala,
deci a proprietarului, nu a mea. Aici doar semnale deja prezente in date.

**Contraexemplu cunoscut, asumat.** Prospetimea favorizeaza sursele care publica des; plafonul
`MAX_PER_SOURCE = 8` per fetch marginesc efectul, dar nu-l elimina. Daca `stats["deferred"]`
arata ca aceleasi surse mananca constant bugetul, pasul urmator e round-robin pe sursa,
nu inca un criteriu in cheia de sortare.
