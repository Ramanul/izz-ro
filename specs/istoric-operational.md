# Istoric operațional — arhiva §9, §11, §14, §15, §17

> **Ce e:** secțiuni mutate din `CLAUDE.md` pe 2026-08-06, fiindcă erau deja marcate
> „COMPLETED" / „RESOLVED" / „ENDED / HISTORICAL" sau conțineau naraţiune în loc de regulă.
> Se încărcau în context la fiecare tură; se citesc de câteva ori pe lună.
> Regulile care încă obligă la acțiune au rămas în `CLAUDE.md`, pe scurt, cu trimitere aici.

## §9 — Bootstrap (COMPLETED 2026-06-26)

Secțiunile 3, 4 și 8 din `CLAUDE.md` au fost completate din starea reală a repo-ului. Niciun
placeholder nu a rămas. Nimic de făcut.

## §11 — SEO (RESOLVED 2026-06-26)

Toate golurile listate anterior sunt implementate și verificate față de output-ul real de randare:
- `og:type: article` — prezent pe toate paginile de articol (override de bloc `base.html` în `article.html`)
- `dateModified` — prezent în JSON-LD `NewsArticle` (`render.py::_article_jsonld`)
- `lastmod` — prezent pe toate URL-urile din sitemap (`render.py::_write_sitemap`)

**Nu re-audita fără o descoperire nouă, specifică.** (Regula a rămas în `CLAUDE.md §11`.)

## §14 — Mandatul de livrare autonomă: ÎNCHEIAT (decizie proprietar 2026-07-13)

Mandatul autonom din 2026-07-10 e **TERMINAT**. Backlogul lui s-a livrat (2026-07-11) și site-ul
live e verde. A produs o problemă concretă: mai multe sesiuni, fiecare rulând un cron autonom și
auto-merge-uind în `main`, s-au ciocnit (2026-07-12/13 — munca de GA + security headers a trebuit
refăcută după ce PR-uri paralele au aterizat).

Backlog livrat, a NU se reface: motor de imagini Chromium, `_headers` de cache, declarație de
accesibilitate EAA, pasaj de wording legal, praguri A11y/SEO/perf, suită pytest + `tests.yml`,
curățenie în `covers.py` — toate ✅.

**Fapte despre proprietar (nu inventa fapte juridice):** operator = persoană fizică, inițiale
**S.A.N.**, România — deja în `privacy.md`.

### §14b — Munca în fundal: REINSTAURATĂ, MĂRGINITĂ (decizie proprietar 2026-08-01)

§14 a interzis buclele autonome pentru că *două conturi* rulau fiecare câte una și s-au ciocnit
(12-13 iul). Premisa aia a dispărut: STATE.md consemnează mod cu un singur cont. Proprietarul
lipsește adesea zile întregi și vrea progres între timp, deci un Routine de fundal e permis din nou,
sub limite care fac imposibil eșecul original. Limitele active sunt în `CLAUDE.md §14b`.

## §21 — De ce există harta fișierelor de la rădăcină

Garda din `tests/test_reguli.py::test_harta_acopera_exact_fisierele_de_la_radacina` există fiindcă
rădăcina ajunsese la **15 fișiere `.md`** și nimeni nu mai știa care e canonic. Cifrele, măsurate
pe commit-ul de dinaintea curățeniei (2026-08-21): **166.326 de octeți** în total pe cele 15, din
care **82.890** în cele opt fișiere propriu-zis „de reguli" (fără `README.md` și fără rapoartele
mutate atunci în `notes/`). Textul mai vechi din `CLAUDE.md §21` împerechea cele două cifre greșit
(„15 fișiere, 82 KB", numitori diferiți) și mai afirma că treisprezece fuseseră înghețate în
același commit — nesusținut: cel mai mare grup cu același ultim commit era de **trei** fișiere.
Corectat 2026-08-29.

## §15 — Sub-agenți și comenzi (detaliu)

**De ce `CLAUDE.md §15` nu mai repetă plafonul lui `STATE.md`:** până pe 2026-08-21 erau scrise
două cifre diferite pentru aceeași regulă (~30 de linii în `CLAUDE.md`, ~40 în antetul lui
`STATE.md`) — iar fișierul ajunsese la 656 de linii, deci nu se ținea niciuna. O regulă, o cifră,
un loc. Garda mecanică e `tests/test_reguli.py::test_fiecare_plafon_e_declarat_intr_un_singur_loc`.

Sub-agenții de proiect stau în `.claude/agents/` (versionați, vezi README-ul lor). Fiecare izolează
o treabă zgomotoasă, mărginită și rezumabilă, și întoarce un verdict.

| Când schimbi… | Agent | Ce impune |
|---|---|---|
| `generator/cluster.py` sau pragurile lui | `clustering-tuner` | §7 — verifică over-merge ȘI under-merge pe eșantioane reale. Raportează, nu editează. |
| `templates/` · `static/styles.css` · HTML/JSON-LD din `render.py` | `frontend-auditor` | §13 — rulează `tools/audit.sh`, raportează delta Lighthouse/pa11y |
| „mai construiește?" / verifică rulând | `pipeline-runner` | §5.4 — `--dry-run` / `--render-only` / `qa_check.py` |
| orice schimbare pe o suprafață de știre | `editorial-guard` | §7, §8 — formula de atribuire, Zero Zgomot, o axă-o casă, tokenuri de design. Read-only. |

### Fluxul cu executanți (Devin, adăugat 2026-07-18)

Task-urile de implementare bine specificate pot fi delegate la Devin (model swe-1-6-slow, cotă
gratuită — costă zero tokeni Claude). **`/delegate-devin`** scrie un spec cu premise verificate în
`specs/` și îl predă headless prin
`python tools/devin_headless.py -- -p "..." --permission-mode smart`.
**NICIODATĂ nu rula `devin.exe` direct** — un mesaj interactiv de pornire blochează rulările pe pipe;
docstring-ul wrapper-ului explică. Devin lucrează pe o ramură `devin/<task>` sub contractul din
`AGENTS.md`; **`/review-devin`** apoi recenzează ramura text-only (git diff + teste) cu verdict
MERGE/FIX/REJECT. Managerul recenzează și face merge; executantul nu împinge și nu face merge
niciodată.

### Două niveluri de agenți, cu rază DIFERITĂ — a nu se confunda

- *Subagenți Claude în sesiune* (`Explore`, `general-purpose`, agenții de verificare) rulează în
  ORICE mediu, inclusiv Claude pe web. Ăsta e executantul implicit dintr-o sesiune web/Linux.
- *Executanți de cod gratuiți* (Devin, OpenCode) rulează DOAR dintr-o sesiune desktop locală, prin
  wrapper-ul de Windows — **nu** sunt accesibili dintr-un container web/Linux (verificat 2026-07-24:
  fără `devin.exe`, fără `pywinpty`). De pe web nu pretinde altceva: folosește subagenți în sesiune
  sau fă-o direct, și spune care.

### Comenzi slash și hook-uri

`.claude/commands/`: **`/slice`** conduce fluxul obligatoriu §5 pentru un slice vertical;
**`/audit`** rulează auditul de front-end. Lista de permisiuni pentru comenzile documentate ca sigure
stă în `.claude/settings.json`. Un hook `SessionStart` doar-pe-web (`.claude/hooks/session-start.sh`)
instalează dependențele pipeline-ului (cu `SETUPTOOLS_USE_DISTUTILS=stdlib`, necesar pentru
feedparser/sgmllib3k), ca să poată rula pipeline-ul și agenții din Claude Code pe web.

## §17 — Cadență de publicare și debit (MĂSURAT 2026-07-25)

De două ori o sesiune a citit „cron 30 min" în fișier, a văzut rulări la 1.5-4.5h distanță și a
conchis că pipeline-ul e stricat. Nu e. Documentația era greșită.

- **Cadența: vezi `CLAUDE.md §17`, care e sursa unică.** Cifra din paragraful ăsta era `13 */2`
  („la fiecare 2 ore") și a rămas în urmă: `build.yml` a trecut între timp la cron **orar**
  (`13 * * * *`) cu o poartă de 105 minute, care păstrează publicarea la ~2h. Corectat 2026-08-29,
  după ce arhiva asta a fost găsită contrazicând regula vie — deci nu re-cita cadența de aici.
  Ce rămâne valabil și e motivul de fond: fiecare commit de stare declanșează un build Cloudflare,
  iar planul gratuit permite ~500/lună. Mai des = bugetul de build se epuizează și deploy-urile se
  opresc — aia e literalmente pana din 5-9 iulie 2026. **Nu „repara" cadența făcând-o mai deasă.**
- **Plafonul de debit e bugetul AI, nu programul:** `max_ai_calls` implicit 18 per rulare
  (≈216/zi). `workflow_dispatch` acceptă un override punctual pentru însămânțarea unei categorii noi.
- **Volum măsurat** (`data/articles.json`, 2026-07-25): 25 de articole la prânz, față de 198 în ziua
  precedentă completă, și 92, 40, 101, 229, 286 pentru zilele dinainte. Varianța zi-cu-zi e mare și
  normală; un număr mic la prânz nu e dovadă de pipeline blocat. **Verifică istoricul de rulări**
  (`gh run list --workflow=pipeline`) înainte de a pretinde că pipeline-ul e picat.
- Dacă proprietarul vrea mai multe articole pe zi, pârghia e bugetul AI per rulare (costă cotă
  Gemini) sau randamentul de clustering — **nu** cron-ul. Aia e o decizie de cost, deci a lui.
