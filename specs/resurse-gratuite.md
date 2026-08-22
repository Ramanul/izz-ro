# DOSAR — resurse gratuite: nevoi, plafoane, marje

> Măsurat 2026-08-21 dintr-o sesiune **remote** (Claude Code pe web), pe `origin/main` @ `63bcc9b`.
> Scop: să nu se mai re-cerceteze „ce avem gratis". Fiecare rând are dovada lângă el.
> **Plafon: ~260 de linii.** Ce crește peste → taie în `specs/istoric-operational.md`.
>
> Ce NU e acest fișier: o listă de servicii de înscris. Constrângerea reală nu e că lipsesc
> resurse gratuite, ci că bugetul gratuit **existent** e prost alocat — două cifre din §3 arată
> exact unde.

---

## 0. Verdictul pe premisă: „resurse gratuite practic nelimitate" — FALS ca formulare, ADEVĂRAT pe fond

Nelimitat nu există: fiecare nivel gratuit are o cuantă, iar cuantele astea **sunt** constrângerile
de design ale izz.ro (cadența de 2h din §17 e efectul direct al unui plafon gratuit).

Ce e adevărat, și e mai util: **una dintre resursele deja deținute e efectiv nelimitată și e
subutilizată, iar cea tratată ca nelimitată e depășită.** Detaliu în §3.

---

## 1. Inventar măsurat în sesiunea asta (§12a)

### 1.1 Binare
| Unealtă | Stare | Consecință |
|---|---|---|
| `ruff`, `pytest`, `node`, `npx`, `jq`, `curl`, `git` | prezente | lint + teste rulează aici |
| `python3` | 3.11.15 | egal cu cloud-ul, nu cu localul (3.14) |
| **`lighthouse`, `pa11y`** | **LIPSESC** | **`tools/audit.sh` (§13) NU rulează din sesiunea asta** |
| `gh` | LIPSEȘTE | *nu* înseamnă lipsă de acces la GitHub — vezi 1.3 |
| `pytest` | prezent, **izolat** | shebang `/root/.local/share/uv/tools/pytest/bin/python` — NU vede pachetele instalate cu `pip`. De aici erorile de colectare (42 măsurate) care arată ca un repo stricat și nu sunt. **Dar nici `python3 -m pytest` nu merge din prima: `No module named pytest`.** Niciuna dintre cele două comenzi nu funcționează pe container curat; reparația e `python3 -m pip install pytest`, după care comanda documentată în §4 rulează suita întreagă (măsurat: 1132 passed, 1 skipped, 8 xfailed). CI nu are problema: `tests.yml` instalează ambele în același interpretor |

### 1.2 Rețea — politica de mediu, nu o pană
`curl -sv` + `$HTTPS_PROXY/__agentproxy/status` → `connect_rejected`,
„gateway answered 403 to CONNECT (policy denial or upstream failure)":

- **Respinse:** `izz.ro`, `api.cloudflare.com`, `openrouter.ai`, `api.openrouter.ai`,
  `huggingface.co`, `api.groq.com`, `api.mistral.ai`, `r.jina.ai`
- **Respinse și sursele de știri** — măsurat separat pe 2026-08-21: `digi24.ro`, `www.digi24.ro`,
  `adevarul.ro`, `www.gsp.ro`, `fcinter1908.it` dau toate `curl: (56) CONNECT tunnel failed,
  response 403`. Deci **nicio sursă RSS nu poate fi verificată din sesiunea asta** — de-aia
  `feedcheck.yml` există ca workflow de dispatch, și de-aia PR #201 stă draft cu 21 de feed-uri
  neverificate până rulează pe runner. Limita e a corpului, nu a proiectului: runnerul le vede.
- **Accesibile:** `generativelanguage.googleapis.com` (404 pe root = host viu), `api.github.com`
  (doar prin conector — vezi 1.3)

**Consecința care contează:** blocajul e pe *sesiunea mea*, nu pe *proiect*. Runnerele GitHub
Actions ajung la toate host-urile de mai sus. Deci „nu pot testa Groq de aici" ≠ „izz.ro nu poate
folosi Groq". Nu confunda cele două limite (§12a).

### 1.3 Conectori
| Conector | Stare | Măsurat |
|---|---|---|
| **GitHub MCP** | **funcțional** | `get_me` → `Ramanul`. Iar `curl https://api.github.com/` prin releu răspunde „GitHub access is not enabled for this session". **Unealta directă minte, conectorul merge** — exact capcana din §12a, a doua oară |
| Gmail | conectat, activ | neutilizat de proiect |
| higgsfield | conectat, activ | `balance` → **10 credite, plan free**. Practic zero |
| **Ahrefs** | conectat, **MORT** | vezi §5 |
| **Google Drive** | instalat, `enabledInChat: false` | resursă gratuită oprită |
| **Supabase** | instalat, `enabledInChat: false` | resursă gratuită oprită |

### 1.4 Fapt care schimbă toată aritmetica
`Ramanul/izz-ro` → `"private": false, "visibility": "public"` (GitHub API).
**Repo public ⇒ minute GitHub Actions gratuite și nelimitate pe runnere standard.**
La fel `Ramanul/ramanul.github.io` (public, `has_pages: true`) — mirror-ul de failover.

---

## 2. Analiza nevoilor: ce consumă izz.ro, din ce, cu ce marjă

| # | Nevoie | Resursa gratuită | Plafon | Consum măsurat | Marjă |
|---|---|---|---|---|---|
| 1 | Calcul pipeline (fetch+AI+randare) | GitHub Actions, repo public | **fără plafon** | ~12 rulări/zi + ~18 workflow-uri | **enormă** |
| 2 | Inferență AI (sinteză/categorii) | Gemini 2.5 Flash-Lite free | 15 RPM · **1000 cereri/zi** | ~216/zi (12 × 18) | **~78% NEFOLOSIT** |
| 3 | Hosting + CDN | Cloudflare Pages | bandwidth nelimitat | — | ok |
| 4 | **Build-uri de deploy** | **Cloudflare Pages free** | **500/lună**, preview-urile intră la socoteală | **764 commit-uri/30 zile pe `main`** | **DEPĂȘIT ~1,5×** |
| 5 | Hosting redundant | GitHub Pages (mirror) | fără plafon de build-uri | deja deployat din `build.yml` | mare |
| 6 | Stare / stocare | git (`data/*.json`) | ~1 GB recomandat de GitHub | **505 MB** (`.git` 399 MB, `media/` 265 MB) | ~50%, în creștere |
| 7 | Monitorizare uptime | Actions cron `*/10` | — | **livrează 62–200 min real**, nu 10 | funcție care nu-și face treaba |
| 8 | Audit front-end | Lighthouse + pa11y local | — | nerulabil din remote (1.1) | lipsă |
| 9 | Imagini | Wikimedia/Wikidata PD/CC0 + coperți Pillow | fără plafon practic | `fetch_leadphotos.py`, `fetch_portraits.py` | mare, îngrădită de §18 |
| 10 | Review de cod | CodeRabbit + Gemini Code Assist + semgrep + CodeQL | free pe repo public | 4 recenzori activi | saturată |
| 11 | Executori delegați | Jules 15 task/zi (3 paralel) · OpenCode Zen free · Devin free | zilnic | sub-folosite | mare |
| 12 | SEO / analytics | GA4 + Clarity + Cloudflare Analytics | free | active | ok |

Dovezi: (1,4) `git log --since=2026-07-22 --oneline origin/main | wc -l` → 764, din care 237
`update content`; `git ls-remote --heads origin | wc -l` → 68 ramuri. (2) `generator/main.py:379`
(implicit 12), `:226` (măsurat 18); cuantele Gemini din documentația free tier, august 2026 —
**de re-verificat**, Google a tăiat nivelul gratuit cu 50–80% pe 2025-12-07. (6) GitHub API
`size: 505001` KB + `du -sh`. (7) comentariul măsurat din `.github/workflows/monitor.yml`.

---

## 3. Cele două cifre care schimbă premise

### 3.1 Bugetul Cloudflare e depășit, iar aritmetica din `IZZ-0139` număra doar jumătate
`IZZ-0139` (respins, 2026-07-25) a refuzat îndesirea cadenței cu motivul: „12/zi = ~360" față de
500 build-uri/lună. **Cifra aia numără doar commit-urile de conținut.** Realitatea măsurată pe 30
de zile: **764 de commit-uri pe `main`**, din care doar 237 sunt conținut — restul de 527 sunt
commit-uri de dezvoltare. Plus preview-urile de pe 68 de ramuri, care consumă din același plafon.

**Ce NU spune asta:** că trebuie îndesită cadența. `IZZ-0139` și §17 rămân în picioare — pana din
5–9 iulie a fost reală. Ce spune este că **plafonul e deja depășit din dezvoltare, nu din
publicare**, deci apărarea actuală (poarta de 105 min) păzește partea greșită.

**Nu am putut verifica numărul real de build-uri Cloudflare**: `api.cloudflare.com` → 403 de la
proxy. Prima verificare a proprietarului: dashboard-ul Pages → build-uri consumate luna asta.

### 3.2 Bugetul AI gratuit e folosit pe sfert
Gemini free tier pentru Flash-Lite: **1000 cereri/zi**. izz.ro consumă ~216 (12 rulări × 18 apeluri).
**~78% din cuota deja deținută expiră nefolosită în fiecare zi.**

Ce face fină observația asta: §17 spune explicit „plafonul de debit e bugetul AI (`max_ai_calls`),
**nu programul**". Creșterea `MAX_AI_CALLS_PER_RUN` produce **mai mult conținut per rulare fără
niciun commit în plus** — deci **zero build-uri Cloudflare în plus**. Este singura pârghie de debit
care nu atinge deloc premisa respinsă în `IZZ-0139`.

Constrângeri de respectat: 15 RPM ⇒ `GEMINI_THROTTLE=4s` (deja setat, cauza-rădăcină din `IZZ-0004`)
⇒ 40 de apeluri = ~160 s de throttle per rulare. Timpul de job e gratuit pe repo public (§1.4).

---

## 4. Gratuit și neutilizat — candidați ordonați după raport câștig/efort

1. **Deploy prin Wrangler direct-upload din Actions, nu prin integrarea Git a Cloudflare.**
   Încărcările directe **nu se numără ca build-uri**. Convertește o resursă plafonată la 500/lună
   într-una neplafonată, plătind cu minute de Actions care sunt gratuite și nelimitate (§1.4).
   Rezolvă §3.1 fără să atingă cadența.
2. **`providers/openai_compat.py` + `providers/cascade.py` există deja.** Rutarea multi-furnizor cu
   fallback e **cod scris**, nu de scris. Groq, Cerebras, OpenRouter free, Mistral free, Cloudflare
   Workers AI se conectează prin **configurație**, nu prin cod. Blocate din sesiunea mea (§1.2),
   accesibile din runner. Efect: independență față de o singură cuotă gratuită.
3. **`providers/ollama.py`** — inferență locală gratuită pe mașina proprietarului, pentru sarcini
   care nu cer calitate maximă (dedup, filtre, pre-clasificare). Zero cuotă consumată.
4. **Mirror-ul GitHub Pages ca a doua cale de publicare**, nu doar failover. Fără plafon de build-uri.
5. **Supabase (conector instalat, oprit în chat)** — Postgres gratuit + storage. Candidat direct la
   nevoia 6: scoate starea din git și oprește umflarea repo-ului.
6. **GitHub Releases / artifacts ca depozit gratuit** pentru `media/` (265 MB) și seturile de hărți.
   Scoate greutatea din istoricul git, scurtează fiecare checkout din fiecare workflow.
7. **UptimeRobot free (50 monitoare, 5 min)** pentru nevoia 7 — `monitor.yml` însuși notează că
   detecția sub-oră cere serviciu extern; e „decizie de cont, nu de repo".
8. **GitHub Codespaces free tier** — mediu unde `lighthouse`/`pa11y` rulează, deci §13 redevine
   executabilă când sesiunea e remote (§1.1).
9. **Google Search Console API** (gratuit, date reale de interogare) — nu e conectat. Vezi §5.
10. **date.gov.ro / INS / date deschise oficiale** — gratuite și cu licență clară. §18 eliberează
    **textul** actelor oficiale (Legea 8/1996 art. 9), nu fotografiile; partea de text e
    sub-exploatată pentru unghiul instituțiilor locale.
11. **GitHub Issues ca listă de sarcini** — 4 issue-uri deschise, mecanism gratuit deja plătit, în
    timp ce coordonarea stă în `.md`-uri de la rădăcină (§21 documentează exact durerea asta).
12. **Jules (15 task-uri/zi) și OpenCode Zen** — cuote zilnice care expiră nefolosite, la fel ca §3.2.

---

## 5. Gratuit pe hârtie, mort la măsurare — Ahrefs

Conectorul e `connected: true, enabledInChat: true`, dar **fiecare** apel întoarce
`{"error": "Insufficient plan"}` — inclusiv `subscription-info-limits-and-usage`, documentat
literal ca „free and does not consume any API units", și `public-domain-rating-free`.

Costul lui nu e zero: ocupă **peste 150 de nume de unelte** în lista amânată a fiecărei sesiuni.
Capacitate zero, greutate reală, plătită la fiecare tură (§19).

**Propunere:** deconectează-l. Datele SEO gratuite se iau din **Ahrefs Webmaster Tools** și
**Google Search Console** direct — produse separate de API-ul plătit pe care îl cere MCP-ul.

---

## 6. Ce costă, de fapt, „gratuitul"

- **Cuotele se schimbă sub tine.** Google a tăiat nivelul gratuit cu 50–80% pe 2025-12-07. Orice
  cifră din dosarul ăsta e o măsurătoare cu dată, nu o garanție.
- **Fără SLA.** Worker-ul de failover (`infra/`) există deja tocmai din motivul ăsta.
- **Fiecare integrare are un întreținător: o singură persoană.** A cincea cuotă gratuită adaugă a
  cincea cale de eșec, nu doar a cincea capacitate.
- **Fiecare unealtă costă context la fiecare tură** (§19). Ahrefs e demonstrația (§5).
- **Regula tare:** nicio resursă gratuită nu se adaugă fără (a) nevoia din §2 pe care o acoperă și
  (b) ce se dezactivează în schimb.

---

## 7. Felii propuse — fiecare așteaptă „go" (§5.2)

| # | Felie | Deblochează | Efort | Risc |
|---|---|---|---|---|
| 1 | Deploy prin Wrangler direct-upload din Actions | §3.1 — scoate plafonul de 500 | mediu | atinge deploy-ul de producție → **§10, cere instrucțiune explicită** |
| 2 | `MAX_AI_CALLS_PER_RUN` 18 → 36, măsurat A/B pe o rulare | §3.2 — dublează conținutul, zero build-uri în plus | mic | cuotă; reversibil printr-o variabilă |
| 3 | Deconectează Ahrefs, conectează GSC | §5 — greutate de context, date SEO reale | mic | niciunul |
| 4 | `media/` → Releases; `data/` mare → în afara istoricului | nevoia 6 — 505 MB și crește | mediu | rescrie istoric ⇒ **decizie proprietar** |
| 5 | Al doilea furnizor AI gratuit prin `cascade.py` (config, nu cod) | independență de o singură cuotă | mic | necesită cheie nouă |
| 6 | UptimeRobot pentru monitorizare sub-oră | nevoia 7 | mic | decizie de cont |

**Ordinea recomandată: 3 → 2 → 5 → 6 → 1 → 4.** Întâi ce e ieftin și reversibil; producția
(felia 1) și istoricul git (felia 4) la urmă, cu confirmare explicită.

**Prima verificare care nu depinde de mine:** dashboard-ul Cloudflare Pages → câte build-uri s-au
consumat luna asta. Dacă cifra e sub 500, §3.1 se schimbă din „depășit" în „aproape de plafon" și
felia 1 coboară în prioritate. Nu pot citi eu cifra: `api.cloudflare.com` → 403 de la proxy (§1.2).
