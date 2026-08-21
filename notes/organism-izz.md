# izz.ro ca organism — anatomie, eficientizare, dezvoltare, adaptare

> Scris 2026-08-21, la cererea proprietarului. Toate cifrele de mai jos sunt **măsurate în sesiunea
> care a scris nota**, nu citate din memorie. Unde o măsurătoare contrazice registrul, e marcat.
> Nota e descriptivă și propozitivă: **niciuna dintre propunerile din §5-§7 nu e implementată** și
> niciuna nu se implementează fără „go" (CLAUDE.md §5).

## 1. Inventar măsurat

| Ce | Cât | Cum |
|---|---:|---|
| cod pipeline | 8.387 linii, 24 module | `wc -l generator/*.py` |
| unelte | 44 | `ls tools/` |
| fișiere de test | 85 | `ls tests/test_*.py` |
| workflow-uri CI | 19 | `ls .github/workflows/` |
| dependențe runtime | 8, toate fixate | `requirements.txt` |
| stare pipeline | 6,87 MB, 5.800 articole, 26 de zile | `data/articles.json` |
| `CLAUDE.md` | 23.259 din 24.576 octeți (94,6%) | `stat -c %s` |
| registru decizii | 237 rânduri | `wc -l specs/registru.tsv` |
| **fișiere urmărite în git** | **14.653, din care 14.105 în `media/` (96,3%)** | `git ls-files` |
| `media/` pe disc | 265 MB | `du -sh media` |
| `specs/metrics.csv` | 22 rânduri, ultimul **2026-07-25** | `tail specs/metrics.csv` |

Mediul de execuție al sesiunii (remote, Claude Code pe web):

- Python 3.11.15 · clonă **superficială**: 78 commituri, cel mai vechi 2026-08-19
- `chromium` LIPSĂ, `gh` LIPSĂ · `ruff`, `pytest`, `node`, `jq`, `curl` prezente
- `api.github.com` → **200**. `https://izz.ro/` → **`CONNECT tunnel failed, 403`**
- `python -m pytest` (comanda din CLAUDE.md §4) → `No module named pytest`.
  Funcționează: `PYTHONPATH=. pytest tests/ -q` (verificat: `test_reguli.py`, 16 passed).
  Cauză: `pytest` e instalat pentru alt interpretor decât cel care are dependențele.

## 2. Anatomia

| Sistem | Ce e la izz.ro |
|---|---|
| Genom | `CLAUDE.md` + `AGENTS.md` — se execută în fiecare sesiune, nu se citește „la nevoie" |
| Epigenetică | `specs/STATE.md`, `moderation.yaml` — ce se exprimă din genom acum |
| Memorie imunitară | `specs/registru.tsv` — anticorpi împotriva re-litigării |
| Imunitate înnăscută | `guard.py` (511 linii), ruff, semgrep, codeql |
| Imunitate adaptativă | cele 85 de fișiere de test — fiecare născut dintr-o infecție reală |
| Metabolism | `build.yml`: cron orar + poartă la 105 min → publicare la ~2h |
| Aport caloric | `max_ai_calls=18`/rulare · ~500 build-uri Cloudflare/lună · cota Claude a proprietarului |
| Digestie | `fetch.py` → `cluster.py` → `process.py` |
| Excreție | dedup, `select.py`, regula „SARI itemul" (§7). „Zero Zgomot" e o funcție de excreție |
| Piele | Cloudflare edge + `static/styles.css`, reînnoită prin `?v=` hash de conținut |
| Proprioceptie | `tools/audit.sh` (Lighthouse + pa11y) — §13 |
| Sistem nervos periferic | cele 19 workflow-uri: reflexe care se declanșează fără operator |
| Memorie episodică | `data/articles.json`, comis ca să supraviețuiască morții containerului |
| Creier / autoritate | proprietarul — singurul care face merge (§14) |
| Cortex prefrontal | `moderation.yaml`: inhibiția, omul în buclă |

## 3. Ce lipsește din inventarul intuitiv

Enumerarea firească (cod, hardware, dependențe, mediu, interacțiune) descrie **organele**. Ce omite
sunt **condițiile de viață**, care omoară sisteme mult mai des decât organele:

**a) Timpul.** Un organism nu e o structură, e o structură care se repetă. Cron `13 * * * *` cu
poartă la 105 min e pulsul. A fost deja „reparat" o dată prin accelerare — a produs pana din 5-9
iulie (`IZZ-0139`, respins, cu motiv măsurat). Tahicardie iatrogenă.

**b) Bugetul.** Orice organism e definit de constrângerea energetică, nu de ADN. Aici:
18 apeluri AI/rulare, ~500 build-uri Cloudflare/lună, și — conform `COORD-DASHBOARD.md`, măsurat
prin API — **resursa cu adevărat limitată sunt tururile de conversație**, nu minutele Actions, care
pe repo public sunt zero.

O primă versiune a rândului de mai sus scria „~360 din cele 500 consumate de commit-urile de
conținut". E fals, și a fost măsurat fals în aceeași oră, de altă sesiune: pe `origin/main`, în 30
de zile, **764 de commit-uri, din care 237 de conținut** — restul sunt commit-uri de dezvoltare,
fiecare declanșând un build exact ca unul de conținut. Corroborat aici pe fereastra vizibilă dintr-o
clonă shallow: 78 de commit-uri în 2,5 zile, din care 19 de conținut (24%). Deci **dezvoltarea, nu
publicarea, e cea care consumă bugetul** — o inversiune care schimbă unde se caută economia.
Dosarul cu cifra și comanda: `specs/resurse-gratuite.md` §3.1 (`IZZ-0238`).

**c) Membrana selectiv permeabilă.** Măsurat azi: GitHub trece, `izz.ro` nu. Corpul remote e
proiectat să nu-și poată vedea propria piele — de aceea §16.3 impune formularea „reparat +
verificat local; rămâne de confirmat pe live".

**d) Patru feluri de memorie, cu durate radical diferite.**
- *de lucru* — fereastra de context a sesiunii; **se șterge complet la final**
- *pe termen scurt* — clona e superficială: 78 de commituri, două zile de trecut
- *episodică* — `data/articles.json`, comisă tocmai ca să supraviețuiască
- *semantică* — `specs/`, 34 de fișiere; singura care se transmite între generații

Consecință: **ce nu e comis, n-a existat.**

**e) Îmbătrânirea.** Feed-uri care mor, modele care se depreciază, 8 dependențe fixate care
putrezesc încet. Fixarea cumpără reproductibilitate acum cu o datorie plătibilă dintr-o dată — iar
singurul lucru NEfixat din sistem e chiar modelul AI (§7 A3).

**f) Nișa și presiunea de selecție.** Google, supraconcentrarea Digi/RCS (§7), GDPR, Legea 8/1996
(§18), AI Act art. 50 — intrat în vigoare 2026-08-02 și a cerut deja o adaptare (`IZZ-0164`).

**g) Mai mulți creieri, un singur corp.** Contul A, contul B, sesiunile remote, sub-agenții. Cazul
din 25 iulie: un agent a rulat `git checkout` și a mutat ramura de sub ceilalți. `IZZ-0195`: două
suite pytest pe același tree se calcă (27 errors). Nu sunt bug-uri de tooling — sunt **crize
motorii**. Regulile din §14/§19 (worktree, un singur decident, anunț după merge) sunt un corp calos:
nu adaugă putere, adaugă arbitraj.

**h) Executantul nu e un organ, e un simbiont închiriat pe tură.** Se naște, citește genomul ca să
afle unde e, lucrează, moare. Continuitatea nu stă în el, ci în fișiere. De aceea `CLAUDE.md` e la
94,6% din plafon și de aceea plafonul există.

## 4. Unde analogia se rupe

1. **N-are homeostazie.** Fiecare corecție trece printr-un merge făcut de om. Ce pare autoreglare
   sunt reflexe pre-programate, nu feedback biologic. §14 e explicit.
2. **N-are mortalitate, deci n-are selecție.** Codul prost nu dispare, se acumulează: rădăcina
   ajunsese la 15 fișiere de reguli / 82 KB; `CLAUDE.md` a fost slăbit 30→11 KB și a crescut înapoi
   la 21 KB în două săptămâni. Regulile verificate mecanic (`tests/test_reguli.py`, §21) sunt un
   **substitut artificial de mortalitate**.
3. **Nu e un mamifer, e un lichen.** Nu o ciupercă cu alge înăuntru, ci o entitate care există doar
   ca parteneriat între regnuri: proprietarul (direcție, judecată, autoritate), modelele (muncă,
   zero memorie), infrastructura. Structura dură — codul comis — e *secretată* de organisme moi și
   efemere care mor repede. Ca un recif: stratul viu e subțire, scheletul e tot.

## 5. Eficientizare — același rezultat, mai puțină energie

Criteriul corect nu e „cod mai rapid", ci **mai puține tururi de conversație și mai puține decizii
care cer proprietarul**, fiindcă alea sunt resursele rare (§3b).

**E1. Instrumentul de măsură e mort — cea mai ieftină reparație din listă.**
`specs/metrics.csv` s-a oprit pe 2026-07-25; 27 de zile de muncă neînregistrată, exact eșecul
despre care avertizează antetul lui `COORD-DASHBOARD.md`. Cifra „sub-agenții costă ~5,6×" pe care o
citează §19 vine dintr-un eșantion de **3 slice-uri din iulie**. Nu poți optimiza ce nu mai măsori.
*Propunere:* logare automată (hook post-commit sau pas în `tests.yml`), nu manuală. Un organ pe care
trebuie să ți-l amintești se atrofiază — s-a și întâmplat.

**E2. 96,3% din repo e balast.** 14.105 din 14.653 de fișiere urmărite sunt în `media/`, 265 MB.
Codul real e ~550 de fișiere. Fiecare checkout CI, fiecare build Cloudflare și fiecare clonă de
agent trage masa asta.
*Propunere:* mută `media/` pe un bucket (R2) sau LFS. **Cu avertisment:** `IZZ-0162` și `IZZ-0163`
arată că store-ul de imagini e fragil — redenumirea în masă a fost respinsă fiindcă ar fi șters
~8.900 de imagini într-o rulare. Deci prima felie nu e mutarea, ci **măsurarea**: cât din timpul de
build e checkout? Dacă e sub 10%, propunerea pică singură și nu se mai discută.
Aceeași propunere apare, ajunsă pe altă cale, în `specs/resurse-gratuite.md` (felia 4, `media/` →
Releases). Nu sunt două propuneri, ci una — dosarul ține cifrele de cotă, nota asta ține argumentul.

**E3. Taxa de amnezie e reală și se plătește la fiecare tură.** `CLAUDE.md` 23,3 KB + `STATE.md`
3,9 KB + `AGENTS.md` ≈ 7-8k tokeni înainte de primul lucru util. E o taxă corectă, dar plafonul e la
94,6%: **următoarea regulă trebuie să scoată alta.**

**E4. Gura de context.** `data/articles.json` = 6,87 MB. O citire naivă arde bugetul unei sesiuni.
§19 zice deja „nu trage payload mare"; ce lipsește e un helper care întoarce doar câmpurile cerute,
ca regula să fie mai ieftin de respectat decât de încălcat.

## 6. Dezvoltare — ce organ lipsește

**D1. Nu are nocicepție.** Are proprioceptie (Lighthouse/pa11y: poziția propriului corp), dar nimic
care să spună „un cititor real a dat de un perete". Există deja conectori (Ahrefs, GSC, Web
Analytics). *Propunere:* o buclă săptămânală care întoarce trei cifre — pagini cu 0 clicuri, query-uri
pe pozițiile 8-20, paginile de ieșire — și **alea devin coada de lucru**. Efectul principal nu e SEO:
transformă „ce facem în continuare" dintr-o **decizie a proprietarului** într-o **măsurătoare**. Ăsta
e singurul fel real de a economisi resursa rară.

**D2. Diferențiere celulară, dar numai oportunist.** `render.py` are 1.506 linii, `fetch.py` 894.
Nu propun refactor (§5.6, diff minim). Regula propusă: modulele peste ~800 de linii se divid **atunci
când le atingi oricum pentru altceva**, niciodată ca felie separată.

**D3. Arhiva ca suprafață separată** (deja în `STATE.md`, decizie de proprietar în așteptare, cu
memento cerut chiar pe 08-21). E cea mai aliniată dezvoltare cu natura sistemului: o structură
permanentă construită din scheletul lăsat de sesiuni moarte. `tools/arhiva.py` reconstruiește deja
seria din istoricul git, iar `ARTICLE_TTL_DAYS` a trecut 7→30 (#197) ca jumătatea ieftină.

## 7. Adaptare — mediul se schimbă sub tine

**A1. Membrana s-a schimbat în 27 de zile.** `IZZ-0134` (25 iulie) consemnează ca **fals** că
sandbox-ul nu poate ajunge la `izz.ro`. Azi, din sesiune remote: `403 connect_rejected`. Ambele sunt
corecte — pentru corpuri diferite. Mediul de execuție se schimbă fără preaviz.
*Propunere:* `tools/inventar.sh` — inventarul §12a devine **o comandă de 5 secunde, nu o disciplină**.
Disciplina se erodează; scriptul nu.

**A2. Căutarea se mută sub tine.** Cititorii nu mai vin exclusiv din zece linkuri albastre.
„Zero Zgomot" + atribuire curată e exact formatul pe care motoarele AI îl citează.
*Propunere:* măsoară dacă ești **citat**, nu doar dacă ești indexat (Brand Radar există în unelte).
Nu e o schimbare de produs — e o schimbare de metrică.

**A3. Îmbătrânirea e deja acoperită pe doi din trei vectori — al treilea e cel care contează.**
- *dependențe*: `.github/dependabot.yml` rulează **săptămânal** pe pip și pe actions, cu grup pe
  `codeql-action` (fără el, fiecare release deschidea două PR-uri care nu puteau trece niciunul —
  măsurat 2026-08-06, #147/#148). **Acoperit.**
- *feed-uri moarte*: `feedcheck.yml` + `tools/feed_check.py`. **Acoperit.**
- *modelul AI*: **neacoperit — și e singura dependență nefixată din tot sistemul.**
  `generator/providers/gemini.py:17` → `GEMINI_MODEL` implicit `gemini-flash-lite-latest`, un
  **alias flotant**. Cele 8 dependențe runtime sunt fixate la versiune exactă „pentru randări
  reproductibile", în timp ce dependența care determină cel mai mult comportamentul se poate
  schimba peste noapte: fără PR, fără notificare, fără test care s-o prindă — calitatea unei
  sinteze nu e diff-abilă în CI.

  Nu susțin că trebuie fixat: un model fixat e retras la un moment dat și pică pipeline-ul brusc,
  pe când `-latest` degradează lin. Susțin că **compromisul e asimetric și neconsemnat**, iar
  singura apărare reală e verificarea editorială (`verifica_sinteza.py`, `masoara_sinteza.py`,
  `editorial-quality.yml`).
  *Propunere ieftină:* un **canar** — același set fix de ~10 articole trecut prin sinteză periodic,
  cu scorul comparat față de o linie de bază comisă. E test de regresie pentru un organ care nu e
  cod. Fără el, driftul de model e invizibil până îl vede un cititor.

**A4. Presiunea legală se mișcă cel mai repede și nu e opțională.** AI Act art. 50 a cerut deja o
adaptare de conținut (`IZZ-0164`). Ăsta e singurul cadran unde întârzierea nu e o economie.

## 8. Ce NU se face — verificat în registru, ca să nu se relitigheze

- **Nu mări cadența cron** — `IZZ-0139`, respins, motiv măsurat (build-uri Cloudflare, pana 5-9 iulie).
- **Nu regenera copertile vechi** — `IZZ-0163`, închis de proprietar.
- **Nu porni bucle autonome cu auto-merge** — `IZZ-0140`, anulat după incidentul din 12-13 iulie.
- **Nu rula două suite pytest pe același working tree** — `IZZ-0195`, cauza e concurența pe `output/`.
- **Nu atinge `state.merge()`** — `STATE.md`: e cod mort, nu bug; vânătoarea se repetă.

## 9. Cele trei mișcări cu cel mai bun raport

Ordonate după cât din **resursa rară** (atenția proprietarului) eliberează, nu după cât cod cer:

1. **E1 — logare automată a metricilor.** Cost: o felie mică. Deblochează orice altă optimizare,
   fiindcă acum se optimizează pe cifre din iulie.
2. **D1 — bucla de durere a cititorului.** Cost: o felie medie, conectorii există. Transformă
   prioritizarea din decizie în măsurătoare. Cel mai mare efect asupra gâtului de sticlă.
3. **A1 — `tools/inventar.sh`.** Cost: o oră. Transformă o regulă care se erodează într-o comandă
   care nu se erodează.

Restul sunt corecte, dar plătesc mai puțin per unitate de atenție consumată.
