# FREE_AI_SETUP.md — infrastructura AI de coding cu $0

> Cerința proprietarului: capacitate AI cât mai mare, **zero abonamente, zero cost API**,
> cu protecție mecanică împotriva oricărei facturări accidentale. Acest document explică
> arhitectura, instalarea, cheile, limitele și — cel mai important — de ce sistemul nu
> poate produce costuri.

---

## 1. Arhitectura

```
client AI de coding (ZCode, Claude Code, Grok CLI, orice client OpenAI-compatibil)
    ↓  http://127.0.0.1:20129/v1   (cheie locală, nu e expus pe internet)
ai_gateway  ← ACEST REPO — FreeQuotaGuard
    │    • buget înainte de fiecare cerere (estimare → respingere → fallback)
    │    • OPENAI_FREE_ONLY + GLOBAL_FREE_ONLY (nimic plătit, mecanic)
    │    • redactarea secretelor din context
    │    • evidența consumului, UTC, alerte 80/90/100%
    ↓  http://127.0.0.1:20128/v1
OmniRoute (extern, MIT — github.com/diegosouzapw/OmniRoute)
    │    • rutare inteligentă, fallback pe cote, compresie RTK/Caveman
    │    • dashboard propriu: http://127.0.0.1:20128/dashboard
    ↓
provideri free: Groq · Cerebras · Gemini · Mistral · GitHub Models · Z.AI ·
                Cloudflare Workers AI · NVIDIA NIM · OpenAI (doar complimentary, protejat)
```

**De ce două straturi?** OmniRoute e excelent la rutare, dar nu poate garanta $0: cascadele
de fallback ale sale pot conține provideri plătiți, iar OpenAI facturează depășirea.
Stratul din acest repo e judecătorul care spune DA/NU înainte de fiecare cerere.

## 2. Instalare (o dată)

```powershell
# 1. OmniRoute (necesită Node ≥ 22.22 — ai 22.23.3, verificat 2026-10-02)
npm install -g omniroute
omniroute          # pornește pe http://127.0.0.1:20128

# 2. gate-ul de siguranță (venv-ul obișnuit al repo-ului, fără dependențe noi)
cd C:\Users\cw_26\izz-ro
python -m ai_gateway status        # verifică registry-ul
python -m ai_gateway serve         # pornește pe http://127.0.0.1:20129

# 3. copiază configurația și completează cheile
copy ai_gateway\.env.example .env
```

## 3. Regula absolută: $0 — cum e garantată mecanic

1. **GLOBAL_FREE_ONLY=true** (implicit): routerul ia în calcul doar provideri cu
   `billing_possible: false` sau cu cotă free confirmată explicit. Dacă niciun provider
   free nu e disponibil, cererea primește **`NO_FREE_PROVIDER_AVAILABLE` (HTTP 429)** —
   NU se trimite niciodată spre un provider plătit.
2. **OPENAI_FREE_ONLY=true** (implicit): OpenAI e exclus până când în `.env` există
   `OPENAI_COMPLIMENTARY_CONFIRMED=true` **și** un plafon oficial > 0. Registry-ul nu
   conține deloc modele OpenAI plătite — nu există ce selecta greșit.
3. **FreeQuotaGuard**: `safe_limit = official_limit × (1 − margine)`, margine implicită
   20%. O cerere estimată peste `safe_limit` NU pleacă (spec: o cerere care depășește
   plafonul oficial OpenAI se facturează integral — de asta o oprim înainte).
4. **Nu există fallback plătit nicăieri în cod**: funcția de fallback alege doar din
   provideri fără facturare.
5. **GATEWAY_HOST e forțat localhost** (validat la pornire) — sistemul nu devine serviciu
   public (spec secțiunea 12).

Pentru ce NU se poate garanta: redactarea secretelor e pe tipare (regex), nu 100%.
De-aia OpenAI rămâne închis până îl activezi tu conștient.

## 4. OpenAI complimentary tokens — verificat din documentația oficială

Sursă (citită 2026-10-02): [help.openai.com — Sharing feedback, evaluation and fine-tuning
data, and API inputs and outputs with OpenAI](https://help.openai.com/en/articles/10306912-sharing-feedback-evaluation-and-fine-tuning-data-and-api-inputs-and-outputs-with-openai)

Ce spune documentația oficială [FAPT]:

- cotă **zilnică**, reset la **00:00 UTC**, împărțită pe **grupuri de modele**;
- grupul mare: **1M tokeni/zi** (conturi eligibile) sau **250K** (usage tiers 1–2);
- grupul mini/nano: **10M tokeni/zi** (eligibile) sau **2.5M** (tiers 1–2);
- condiția: **activarea partajării datelor** (data sharing) pentru proiectul respectiv;
- **cererea care depășește plafonul poate fi facturată integral** — motivul pentru care
  guard-ul estimează ÎNAINTE de trimitere și oprește cu margine de 20%;
- pentru utilizare e necesar **balance pozitiv** pe cont;
- oferta poate înceta cu **preaviz de 30 de zile**.

Lista modelelor eligibile din fiecare grup e în `ai_gateway/registry.yaml` (grupuri
`1m` și `10m`), cu sursa citată. **Re-verifică lista la activare** — se schimbă des.

### Ce trebuie să faci TU pentru OpenAI (dacă vrei grupul de 10M)

1. Creează proiect API pe platform.openai.com și o cheie; pune-o în `.env`
   (`OPENAI_API_KEY=`).
2. În dashboard, la setările organizației/proiectului, activează **data sharing**
   („Share inputs and outputs with OpenAI") pentru proiectul folosit de gate.
3. Verifică în dashboard ce limită ți s-a acordat (10M / 2.5M / 1M / 250K / nimic).
4. Completează în `.env`:
   ```
   OPENAI_COMPLIMENTARY_CONFIRMED=true
   OPENAI_LIMIT_GROUP_10M=2500000        # exemplu tier 1-2; pune limita TA reală
   OPENAI_LIMIT_GROUP_1M=0               # lasă 0 dacă nu folosești grupul mare
   ```
   Sistemul funcționează identic indiferent că limita ta e 10M, 2.5M, 1M, 250K sau 0
   (0 = OpenAI marcat `FREE_QUOTA_DISABLED`, restul lanțului preia).
5. Margine: `OPENAI_SAFETY_MARGIN=0.20` (implicit) — cu 2.5M oficial, ne oprim la 2.0M.

### Data sharing și ce pleacă din mașina ta

- **Nu activăm sharing-ul noi** — e butonul tău, în dashboard-ul OpenAI.
- Cu sharing activ, REDACT_SECRETS=true (implicit) filtrează din contextul trimis:
  chei API (sk-…, sk-ant-…, ghp_…, github_pat_…, AIza…), chei AWS, chei private PEM,
  DATABASE_URL, atribuiri `password=/secret=/token=`, plus **valorile reale din .env**.
- Totuși: redactarea pe tipare nu e perfecțiune. Nu cereți gate-ului să trimită fișiere
  cu credentiale deschise (ex. `wrangler-account.json`, `.wrangler/`).

## 5. Cheile de provider — unde se creează, ce e free real

| Provider | Cheia (env) | Se creează la | Cotă free | Tip | Reset |
|---|---|---|---|---|---|
| Groq | `GROQ_API_KEY` | console.groq.com | rate limits (RPM/RPD) | rate_limit_only | per provider |
| Cerebras | `CEREBRAS_API_KEY` | cloud.cerebras.ai | 1M tokeni/zi | daily | 00:00 UTC |
| Gemini | `GEMINI_API_KEY` | aistudio.google.com | RPD/TPM pe model | rate_limit_only | per provider |
| Mistral | `MISTRAL_API_KEY` | console.mistral.ai | rate limits plan gratuit | rate_limit_only | per provider |
| GitHub Models | `GITHUB_TOKEN` | github.com/settings/tokens (PAT, `models:read`) | rate limits pe nivel | rate_limit_only | per provider |
| Z.AI | `ZAI_API_KEY` | z.ai (consolă API) | modelele flash, free | rate_limit_only | per provider |
| Cloudflare AI | `CLOUDFLARE_API_TOKEN` | dash.cloudflare.com (API token) | 10K neurons/zi | rate_limit_only | per provider |
| NVIDIA NIM | `NVIDIA_API_KEY` | build.nvidia.com | ~40 RPM | rate_limit_only | per provider |
| OpenAI | `OPENAI_API_KEY` | platform.openai.com | **doar** complimentary, vezi §4 | daily | 00:00 UTC |

Adevăruri importante (spec secțiunile 21, 22, 25, 27, 33):

- **rate_limit_only ≠ tokeni/lună garantată.** Providerii de mai sus resping cererile
  peste limită; nu facturează. Nu transformăm RPM în „cotă garantată".
- **Contul web ≠ API.** Gemini web, ZCode plan → nu dau acces API. Cheile se creează
  separat, în consolele de dezvoltator.
- **Creditul de signup nu e ofertă recurentă** — exemplu în registry: DeepSeek,
  `quota: one_time`, marcat UNVERIFIED și dezactivat.
- **NU am adăugat provideri doar pentru că apar în liste „free"** — CAUTION (OpenRouter,
  Pollinations) e dezactivat și se activează doar cu `ALLOW_CAUTION=true`; UNVERIFIED
  (DeepSeek) nu se activează deloc până nu-l verificăm.

## 6. Cum urmărești cota

```powershell
python -m ai_gateway status                     # tabel în terminal
# → http://127.0.0.1:20129/guard/dashboard      # tabel HTML (în timp ce rulează serve)
# → http://127.0.0.1:20129/guard/status         # JSON complet
```

Răspuns la întrebările din spec: tokeni azi (input/output/cache/estimate), cereri,
provider, model, remaining, reset (totul în UTC; Windows-ul local nu influențează
nimic). Consumul fără usage exact de la provider se marchează **ESTIMATED** și apare
separat.

Alerte (spec secțiunea 19): la 80% din limita internă → `WARNING`, 90% → `HIGH`,
100% → `BLOCKED`; alertele apar în stderr, în status și în dashboard, cu „ce provider,
cât, când se resetează".

## 7. Clientul de coding (cum lucrai efectiv prin gate)

În orice client OpenAI-compatibil setezi:

```
base_url: http://127.0.0.1:20129/v1
api_key:  <valoarea GATEWAY_API_KEY din .env>
model:    <provider>/<model>   ex: groq/llama-3.3-70b-versatile
```

- Modelele explicite `provider/model` sunt recomandate. `auto` e respins implicit
  (cu GLOBAL_FREE_ONLY nu putem garanta ce ar alege auto-rutarea).
- Fallback-ul: dacă ținta primară e blocată de cotă, gate-ul rescrie cererea către cel
  mai bun provider free disponibil (scor = calitate pe clasa task + prioritate + cota
  rămasă, toate din `registry.yaml` — nu e hardcodat).
- Header-e de răspuns: `X-FreeGuard-Provider`, `X-FreeGuard-Decision` (trace-ul deciziei).

## 8. DRY_RUN și simularea

```powershell
# server în mod simulare: pipeline complet, zero rețea
$env:DRY_RUN="true"; python -m ai_gateway serve

# scenariul din spec: OpenAI 2.5M oficial, safe 2.0M, consumat 2.0M, cerere 700K
python -m ai_gateway simulate
# → openai_decision: allowed=False reason=WOULD_EXCEED_SAFE_LIMIT
# → plan_target: <cel mai bun provider free din registry>
```

## 9. Adăugarea unui provider nou (spec secțiunea 31)

1. Răspunde la cele 10 întrebări din spec (API oficial? free real? recurring? card?
   limite? proxy permis? ToS?). Nesigur → `tos_status: UNVERIFIED`, rămâne închis.
2. Adaugă blocul în `ai_gateway/registry.yaml` (doar date, fără cod).
3. Pune cheia în `.env` (variabila din `api_key_env`).
4. `python -m ai_gateway status` — verifică că apare cu statusul așteptat.

## 10. Dezactivarea unui provider

În `registry.yaml`: `enabled: false`, sau golind cheia din `.env` (apare `NO_KEY`).
OpenAI se dezactivează oricând cu `OPENAI_COMPLIMENTARY_CONFIRMED=false`.

## 11. Ce NU face acest sistem

- nu publică nimic pe internet (localhost only, validat la pornire);
- nu stochează chei în repo (doar `.env`, în `.gitignore` dinainte);
- nu decompresiează/reia conversații; compresia RTK/Caveman rămâne la OmniRoute;
- nu garantează redactare perfectă — de-aia OpenAI rămâne opt-in.
