# CLAUDE.md — izz.ro

> Contract canonic pentru Claude Code / Cowork. Se citește la fiecare tură și înlocuiește comportamentul implicit.
>
> **Plafon: 24 KB.** Măsurat în octeți; `tests/test_reguli.py` îl verifică mecanic.
> **Buget de pornire: 37 KB.** Include acest fișier, `SessionStart` și frontmatter-ul agenților/comenzilor; se verifică mecanic.
> **Regulă de namespace:** un `§N` necalificat din documentația repo-ului înseamnă secțiunea N din acest `CLAUDE.md`. Pentru `REGULI-SINTEZA.md` se scrie explicit `REGULI-SINTEZA.md §N`.
>
> Cifrele istorice, măsurătorile și incidentele stau în `specs/`, nu în contract, decât dacă schimbă acțiunea imediată.

## 0. Comunicare
- Vorbește proprietarului în română; codul, identificatorii, commit-urile și logurile rămân în English.
- Fii direct, explică premisele false și declară incertitudinea; nu transforma presupuneri în fapte.
- Fii proactiv cu propuneri, dar nu transforma propunerea în acțiune autonomă pe `main`.
- **Starea de completare înainte de rezultat, ca fracție**, apoi rezultatul cerut.
- **Mandatul e ce a cerut proprietarul, nu ce a ajuns ultimul în context.** Materialul, atașamentul, ramura sau fișierul deschis nu devin sarcină. Începe cu `cerut: X. Fac: Y.`; dacă Y nu duce la X, spune imediat. Încheie cu `cerut vs. livrat`.

## 1. Ce este izz.ro
Agregator românesc de știri cu AI; pipeline static: scrape → synthesize → clusterize → categorize → render. Promisiunea de brand este **Zero Zgomot**.

## 2. Stack și publicare
Python 3.11 cloud / 3.14 local; Jinja2, feedparser, PyYAML, python-slugify, markdown, python-dotenv. AI Gemini 2.5 Flash Lite prin REST, comutabil pe Anthropic. CI/CD GitHub Actions (`build.yml`): cron `13 * * * *`, cu poartă de 105 minute → publicare efectivă ~2h. Hosting: Cloudflare Workers Static Assets; `wrangler.jsonc` assets-only.

## 3. Structura minimă
`generator/` pipeline; `templates/` Jinja2 autoescaped; `static/` CSS/logo; `content/legal/`; `data/articles.json` stare persistentă; `moderation.yaml` control editorial; `output/` build local; `.github/workflows/` automatizări.

## 4. Comenzi canonice
- `pip install -r requirements.txt`
- `python -m generator.main`
- `python -m generator.main --dry-run`
- `python -m generator.main --render-only`
- `python -m http.server 8000 --directory output`
- `python -m pytest tests/ -q`
- `python -m ruff check .`

CI rulează testele și lint-ul. Numărul de teste este doar reper, nu contract.

## 5. Flux obligatoriu
0. Fă inventarul uneltelor înainte de task netrivial.
1. Spec 3–8 linii: scop, intrări/ieșiri, criterii.
2. Plan cu fișierele atinse; pentru muncă netrivială așteaptă `go` înainte de editare, cu excepția cazului în care proprietarul a cerut explicit execuția directă.
3. Lucrează în felii verticale.
4. Verifică rulând; nu declara succes fără ieșire reală.
5. Commit pe verde.
6. Diff minim; fără refactor oportunist.

## 6. Definition of done
Spec îndeplinită · comanda relevantă trecută · lint/test/type-check disponibile trecute · site-ul încă se construiește · commit descriptiv.

## 7. Reguli de domeniu — Zero Zgomot
- **Fără output stricat:** fallback-ul care nu atinge bara de calitate sare itemul; nu publică titlu brut/trunchiat.
- **O axă, o casă:** nu cross-posta același item între axa geo și tematică.
- **Clustering:** orice modificare se probează pe eșantioane reale pentru over-merge și under-merge.
- **Diversitate de surse:** nu agrava concentrarea pe familia Digi / RCS-RDS.
- **Atribuire permanentă:** exact un element `Sursă` / `Surse`, după corp; carduri cu `sources-inline`, articol cu `sources-box`, hero cu aside-ul φ; sursa este linkul extern exact cu `target="_blank" rel="noopener noreferrer"`; fără CTA suplimentar și fără metodologie pe articol.
- **Titluri:** **6–16 cuvinte este ținta editorială**; `TITLE_MAX_WORDS = 22` în `generator/config.py` este **hard safety ceiling**, nu ținta. `REGULI-SINTEZA.md §6` este normativul de conținut.

## 8. Design tokens
Stilul vizual derivă din `static/styles.css`. În template-uri nu se hardcodează culori, font-size sau spacing; se folosesc custom properties.

## 10. Zone protejate
Nu modifica fără instrucțiune explicită: logica de sinteză/atribuire Model C, legal/GDPR și deploy production (`wrangler.jsonc`, Cloudflare Worker code, GitHub secrets). Excepție: MCP Cloudflare poate administra D1/KV/R2/Hyperdrive direct; deploy-ul Worker rămâne repo → PR → CI.

## 11. SEO
SEO rezolvat; nu se reauditează fără descoperire nouă, specifică. Istoricul este în `specs/istoric-operational.md`.

## 12. Unelte și aprobări
### 12a. Inventarul uneltelor — regulă tare
Verifică accesul real, nu deduce capacitatea din lipsa unui binar. O limitare se declară prin experimentul care a eșuat. Dacă o capacitate lipsește dar se poate obține, propune-o; nu ocoli tăcut.

### 12b. Allowlist și confirmări
Comenzile de development/build/lint/test documentate mai sus, plus `git status`, `git diff`, `git log`, `git show`, `git branch`, `git fetch`, `git pull`, sunt permise prin `.claude/settings.json`. Acțiunile ireversibile rămân protejate.

## 13. Front-end — L1
Regula completă este în `.claude/reguli/13-frontend.md` și este injectată de hook când sunt atinse `templates/`, `static/styles.css` sau `generator/render.py`. Nu copia textul înapoi aici.

## 14. Autonomie și coordonare
- Nu arma bucle autonome / CronCreate recurente care se conduc singure prin backlog.
- Nu face curse pe `main`; lucrează prin branch + PR.
- **Canal unic de anunț:** intenția și coordonarea live sunt în `handoff/` din workspace; `specs/STATE.md` este starea persistentă dintre sesiuni. `TASKS-A.md`, `TASKS-B.md` și issue #83 nu sunt canal normativ de anunț.
- După merge, actualizează `specs/STATE.md` și handoff-ul relevant; nu scrie în jurnal înghețat ca și cum ar fi live.

### 14b. Munca de fundal
Un task per declanșare, luat din `specs/STATE.md`; nu inventa muncă și nu atinge decizii de proprietar. Se oprește și raportează la ambiguități. Actualizează STATE la final. Fără auto-merge.

## 15. Delegare
Sub-agenții sunt opționali și trebuie folosiți când reduc costul net. Pentru lucrări paralele folosește `isolation: "worktree"`; doi agenți nu scriu aceeași ramură.

## 16. Verificare în două roluri
Pentru orice schimbare vizibilă:
1. **Programator:** rulează randare/teste/QA.
2. **Utilizator:** verifică în Chromium headless simptomul real și măsoară rezultatul.
3. **Livrabilitate:** confirmă hash/versioning al assetelor (`render._asset_ver`).
4. Stările sunt distincte: **reparat în cod**, **verificat local**, **confirmat pe live**. Nu confunda verdele din CI cu live.
5. Pentru live, folosește `?cb=$(date +%s)` și `bash tools/verify_allowlist.sh` pentru hosturile accesibile din sesiunea curentă.
6. Dacă ceva nu poate fi verificat, numește exact rolul și motivul.

### 16.3 Live verification — regula actuală
`izz.ro` și `www.izz.ro` pot fi blocate de proxy; **originea Worker este calea de verificare când este accesibilă**. Verificarea curentă se face cu `bash tools/verify_allowlist.sh`, pe `https://izz-ro.andifreelancer2.workers.dev/` când hostul este disponibil. Originea poate rămâne în urmă față de domeniul public până la un deploy nou; un `200` la origine nu dovedește că domeniul public are aceeași versiune.

## 17. Cadență
`build.yml` încearcă orar (`13 * * * *`), dar poarta de 105 minute apără publicarea la ~2h. Nu modifica cronul pentru a „repara” cadența.

## 18. Imagini de instituții locale — L1
Textul complet este în `.claude/reguli/18-imagini.md`; hook-ul îl injectează pentru fișierele media aferente. Discuția fără atingerea unui fișier cere citirea regulii înainte.

## 19. Igienă de sesiune și economie de context
- Un task, o sesiune.
- Nu trage payload-uri mari în context.
- Folosește modelul pe măsura muncii.
- Metricul istoric al sub-agenților este **înghețat: ~5.6× per linie, n=3, iulie 2026**; nu îl prezenta ca benchmark curent.
- Agenții împart working tree-ul; folosește worktree isolation și nu modifica aceeași ramură în paralel.
- Nu folosi git restore/checkout --/stash/clean/reset pentru a elimina munca altcuiva; `settings.json` blochează aceste comenzi, iar regula de rol este și în `AGENTS.md`.

## 20. Registrul de decizii
Înainte de a propune, caută `python tools/registru.py find <subiect>`. Deciziile fără PR primesc rând în aceeași tură. Registrul este append-only; `motiv` este obligatoriu pentru `respins`, `abandonat`, `anulat`, `masurat-fals`.

## 21. Harta fișierelor de la rădăcină — CABLATĂ
`tests/test_reguli.py` verifică faptul că orice `.md` nou la rădăcină primește rol aici.
- `CLAUDE.md` — contract canonic.
- `AGENTS.md` — reguli suplimentare pentru executorii non-Claude.
- `README.md` — descriere publică.
- `REGULI-SINTEZA.md` — normativ de titluri/rezumate.
- `COORD-DASHBOARD.md` — snapshot istoric de coordonare; generat de `tools/log_slice.py`, nu se editează manual ca sursă.
- `REVIEW.md` — protocol de review și operare.
- `TASKS-A.md` / `TASKS-B.md` — jurnale locale, nu canal live.
- `TASKS-MISTRAL.md` — coada executorului Mistral.
- `SESSION-2026-08-14.md` / `mistral-analiza-workflow.md` — instantanee istorice.

Normativele din `.claude/commands/`, `.claude/agents/` și `.claude/reguli/` sunt condiționale și se activează prin hook/command, nu se copiază în L0.
