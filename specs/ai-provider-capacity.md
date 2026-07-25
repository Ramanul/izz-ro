# SPEC/CERCETARE — capacitate AI suplimentară dincolo de Gemini

Research-only. Nu s-a scris cod. Vezi `generator/providers/base.py`,
`generator/providers/gemini.py`, `generator/process.py:get_provider`,
`generator/main.py:run`, `.github/workflows/build.yml`.

## 0. Ce limitează azi numărul de știri publicate — verificat în cod

Bugetul real per rulare e `MAX_AI_CALLS_PER_RUN=18` (setat explicit în
`build.yml:55`, nu implicitul 12 din `main.py:133`), plus `UPGRADE_RESERVE=8`.
12 rulări/zi (cron `13 */2`) × 18 = **max 216 apeluri AI/zi**, plafon *ales*,
nu unul impus de furnizor.

`GeminiProvider` (`generator/providers/gemini.py:30-42`) acceptă deja mai multe
chei separate prin virgulă/spațiu în `GEMINI_API_KEY`, cu failover automat la
429 — dublează/multiplică quota free-tier fără nicio linie de cod nouă, doar
adăugând chei în secret.

Sursele oficiale locale (`pl_*`/`cj_*`/`pr_*`) NU consumă buget AI
(`main.py:40`) — nu sunt relevante aici.

**Constatare centrală, nu presupunere:** cifrele terților converg pe
**gemini-2.5-flash-lite free tier ≈ 15 RPM / 1.000 RPD / 250.000 TPM** per
cheie/proiect (vezi §1 — pagina oficială nu publică cifra fără login în AI
Studio, deci e marcată "neverificat direct"). 216 apeluri/zi e cu mult sub
1.000 RPD *pe o singură cheie*, înainte de orice multi-cheie. **Deci quota
Gemini nu pare a fi saturată — plafonul e bugetul, nu furnizorul.** Dacă
proprietarul vrea mai multe știri/zi, pârghia ieftină și cu risc zero e
`MAX_AI_CALLS_PER_RUN` (+ eventual o a doua cheie Gemini), nu neapărat un
provider nou. Comentariul din `config.py:159` ("TTL mai scurt -> volum mai
mic -> incape in quota free Gemini") arată că quota *a fost* o grijă reală
istoric — dar §17 din `CLAUDE.md` (măsurat 2026-07-25) confirmă că azi
cauza e bugetul explicit, nu epuizarea Gemini. Asta nu invalidează cererea
de mai jos (proprietarul poate vrea capacitate de rezervă / redundanță, nu
doar volum), dar trebuie spus înainte de tabel.

## 1. Tabel comparativ

Legendă card: **Nu** = confirmat fără card · **Da** = confirmat cu card ·
**neclar** = surse contrazictorii, nicio pagină oficială tranșează.

| Furnizor | Limită gratuită reală | Card? | Sursa | Calitate RO (bază) | Efort integrare vs `base.py` | Risc principal |
|---|---|---|---|---|---|---|
| **Gemini (curent)** | ~15 RPM / **1.000 RPD** / 250k TPM per cheie/proiect pt. `gemini-2.5-flash-lite` (convergență terți multipli; pagina oficială trimite la dashboard AI Studio, login necesar → **neverificat direct pe pagina publică**) | Nu | [ai.google.dev/gemini-api/docs/rate-limits](https://ai.google.dev/gemini-api/docs/rate-limits) (trimite la [aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit)); cifre convergente: [tokenmix.ai](https://tokenmix.ai/blog/gemini-api-free-tier-limits), [aifreeapi.com](https://www.aifreeapi.com/en/posts/gemini-api-free-tier-rate-limits) | Deja în producție, calitate confirmată empiric de proprietar | 0 (deja integrat) | Model retras/redenumit (a mai pățit-o site-ul: alias `-latest` repointat pe 3.x, 3 zile de site înghețat, vezi comentariul din `gemini.py:48-51`) |
| **Groq** | Confirmat oficial per-model: `llama-3.1-8b-instant` 30 RPM / **14.400 RPD** / 6k TPM / 500k TPD; `llama-3.3-70b-versatile` 30 RPM / 1k RPD / 12k TPM / 100k TPD; modele Qwen similare. Fără card (consistent pe multiple surse, neconfirmat literal pe pagina de pricing) | Nu (probabil — nu 100% pe o pagină primară) | [console.groq.com/docs/rate-limits](https://console.groq.com/docs/rate-limits) (oficial, cifre exacte); card: [community-groq-com.translate.goog/.../790](https://community-groq-com.translate.goog/t/is-there-a-free-tier-and-what-are-its-limits/790) (comunitate, nu pagină primară) | Găzduiește modele open-weight terțe (Llama/Qwen/Gemma/gpt-oss) — calitatea RO = calitatea modelului de dedesubt, nu a Groq. Nicio evaluare RO oficială găsită; Llama 3.3 70B și Qwen au corpus multilingv documentat, dar fără benchmark RO specific | **Mic.** API compatibil OpenAI (`/openai/v1/chat/completions`), REST simplu cu Bearer token — se poate scrie un `_complete` aproape identic ca formă cu `gemini.py`, fără SDK | Roster de modele instabil istoric (Groq retrage/înlocuiește modele găzduite); trebuie ales explicit un model și verificat că rămâne disponibil |
| **OpenRouter (:free)** | Oficial: **50 RPD** fără nicio achiziție; **1.000 RPD** după o achiziție unică de min. $10 credit (deblocare pe viață, nu sold minim); 20 RPM mereu | Nu pt. 50 RPD; **Da** pt. 1.000 RPD (achiziția de $10 cere card) | [openrouter.ai/docs/api-reference/limits](https://openrouter.ai/docs/api-reference/limits) (oficial) | Agregă rutele `:free` ale MULTOR furnizori (inclusiv Gemini, Llama, DeepSeek, Qwen, GLM) sub UN singur endpoint compatibil OpenAI — calitatea variază pe model ales, aceeași incertitudine RO ca la fiecare furnizor individual | **Mic.** Complet compatibil OpenAI, un singur cont/cheie pentru mai mulți furnizori | Politica de date variază per model gratuit — unii furnizori pot folosi prompturile pentru antrenare pe rutele `:free` (verifică per model în dashboard înainte de a trimite conținut); dependență indirectă de disponibilitatea fiecărui furnizor din spate |
| **Z.ai / GLM** | `GLM-4.5-Flash` și `GLM-4.7-Flash`: preț **$0** confirmat pe pagina oficială de pricing (input/output/cache = "Free", nu credit de probă). Rată-limită ~1 req/s (**neverificat pe pagină oficială** — doar surse terțe convergente) | Nu (convergență multiplă terți; nicio pagină primară confirmă explicit) | [docs.z.ai/guides/overview/pricing](https://docs.z.ai/guides/overview/pricing) (oficial, doar prețul $0); rată-limită: [tokenmix.ai](https://tokenmix.ai/blog/glm-free-api-access-tiers-2026) | GLM (Zhipu, China) — multilingv documentat pentru limbi majore vest-europene, fără benchmark RO cunoscut | **Mic.** "Z.AI uses an OpenAI-compatible API" (documentat oficial în quick-start) | Furnizor mai nou, intrare recentă pe piața API gratuită — riscul explicit cerut de proprietar ("furnizori care închid nivelul gratuit") e real aici, fără istoric lung de stabilitate a nivelului gratuit |
| **Mistral** | Tier "Experiment"/gratuit confirmat că EXISTĂ (anunț oficial 2024, încă menționat în docs curente), dar cifrele exacte RPS/TPM sunt per-workspace, vizibile doar logat în `admin.mistral.ai/plateforme/limits` — **neverificat public** | Neclar | Existență: [docs.mistral.ai/deployment/laplateforme/tier](https://docs.mistral.ai/deployment/laplateforme/tier) (link oficial, conținut needisponibil fără sesiune); anunț: [techcrunch.com/2024/09/17/...](https://techcrunch.com/2024/09/17/mistral-launches-a-free-tier-for-developers-to-test-its-ai-models) | Companie franceză — calitate documentată bine pt. franceză/germană/spaniolă; RO neevaluat oficial | **Mic-mediu.** API propriu dar cu formă apropiată de OpenAI (multe SDK-uri OpenAI merg cu doar schimbarea base_url) | Cifre publice absente = imposibil de dimensionat bugetul fără cont propriu; "doar pentru experimentare", nu producție, per texul oficial |
| **Cerebras** | Confirmat oficial: **5 RPM / 30.000 TPM / 1.000.000 TPD** pe modelele free (`gpt-oss-120b`, `zai-glm-4.7`, `gemma-4-31b`) | **Da** — oficial: "$5 in free credits after making an account" cu "verified payment method"; fără el, Playground/API rămân inactive | [inference-docs.cerebras.ai/support/rate-limits](https://inference-docs.cerebras.ai/support/rate-limits) + [cerebras.ai/pricing](https://www.cerebras.ai/pricing) (ambele oficiale) | Aceleași modele open-weight ca la Groq/OpenRouter (GLM, Gemma, gpt-oss) — aceeași incertitudine RO | Mic — API compatibil OpenAI | **Cere card** — exclus dacă proprietarul vrea zero fricțiune de plată; 5 RPM e restrictiv dar suficient pt. 18 apeluri/rulare distribuite pe 2h |
| **DeepSeek** | **Fără nivel gratuit permanent.** Grant unic de 5M tokeni la cont nou, valabil 30 zile, apoi necesită metodă de plată | Nu pt. grant, **Da** după epuizare | [api-docs.deepseek.com/quick_start/pricing](https://api-docs.deepseek.com/quick_start/pricing) (oficial: nicio mențiune de free tier; prețuri: $0.14/M input cache-miss, $0.28/M output pt. deepseek-v4-flash) | Reasoning puternic documentat, dar corpus RO neconfirmat oficial | Mic — API compatibil OpenAI | E un impuls unic (~2.500-5.000 apeluri), nu capacitate susținută — nu rezolvă o nevoie recurentă la fiecare 2h |
| **Qwen / DashScope (international)** | Cont nou (regiune Singapore): 1.000.000 tokeni input + 1.000.000 output, valabil **90 zile**, apoi níciun nivel gratuit standard (cel vechi permanent s-a închis 15 apr. 2026) | Neclar — surse contrazictorii ("no card" vs. proces standard Alibaba Cloud care include de regulă o metodă de plată la activare) | [alibabacloud.com/help/en/model-studio/new-free-quota](https://www.alibabacloud.com/help/en/model-studio/new-free-quota) (oficial) | Alibaba revendică suport pt. 100+ limbi; RO neconfirmat cu benchmark propriu | Mic — API compatibil OpenAI (endpoint DashScope) | Tot un impuls temporar (90 zile), nu recurent; exact tipul de furnizor pe care CLAUDE.md §7 avertizează să nu se bazeze o funcție permanentă |
| **Together AI** | **Eliminat.** Fără nivel gratuit — docs oficiale: "no free trials... using the platform requires a minimum $5 credit purchase"; complet preplătit | Da (obligatoriu) | [docs.together.ai/docs/billing-credits](https://docs.together.ai/docs/billing-credits) (oficial) | N/A | N/A | Nu e candidat — nu există "gratuit" de evaluat |
| **Cohere** | **Eliminat pentru acest caz.** Trial key: 20 req/min (Chat), **1.000 apeluri/lună** — dar documentația oficială interzice explicit uzul de producție/comercial cu cheia trial | Neclar | [docs.cohere.com/docs/rate-limits](https://docs.cohere.com/docs/rate-limits) + [cohere.com/pricing](https://cohere.com/pricing) (ambele oficiale) | Command R e optimizat pt. ~10 limbi majore, RO nu e listat explicit | Mediu — API propriu, nu compatibil OpenAI | **Interdicție ToS de uz comercial/automat** — izz.ro rulează un pipeline automat comercial-adiacent la fiecare 2h; folosirea cheii trial ar încălca termenii, exact riscul de la §5 al cererii |

## 2. Recomandare clasată

**Locul 1 — Groq.** Cifre oficiale exacte, fără card, REST simplu compatibil
OpenAI (efort de integrare minim, aceeași formă ca `gemini.py`). Singura
incertitudine reală e calitatea RO a modelului ales (nu a Groq ca infra) —
de testat empiric înainte de a-l lăsa să publice, exact cum cere §7 din
CLAUDE.md pentru clustering. Risc principal: roster de modele instabil —
trebuie fixat un model concret și monitorizat pentru retragere (la fel cum
`gemini.py` a fost deja lovit de asta).

**Locul 2 — OpenRouter (`:free`, după achiziția unică de $10).** Avantajul
unic: un singur integrator pentru mai mulți furnizori (inclusiv o a doua
rută spre modele Gemini gratuite prin altă poartă), deci reduce numărul de
integrări de scris dacă se dorește diversitate. Dezavantaj: fără cei $10
(deci cu card), plafonul de 50 RPD e sub un singur run (18 apeluri) de câteva
ori, insuficient ca rezervă serioasă. Cu $10, 1.000 RPD e generos, dar
politica de date pe rutele `:free` trebuie verificată per model înainte de a
trimite text — nu presupune.

**Locul 3 — Z.ai / GLM-4.5-Flash.** Genuinely $0 (nu credit de probă),
compatibil OpenAI, aparent fără card. Coboară pe locul 3 pentru că nimic din
ce am găsit nu vine dintr-o pagină oficială *primară* care confirme simultan
rata-limită și lipsa cardului — doar convergență de agregatori — și pentru
că e un intrat recent, exact profilul de furnizor care "închide nivelul
gratuit" (riscul cerut explicit la §5 din task). Bun ca a treia verigă
opțională, nu ca a doua.

**Nu recomand, motivat:** Cerebras (cere card — barieră de fricțiune fără
beneficiu clar peste Groq), Mistral (cifre nepublice, imposibil de bugetat),
DeepSeek și Qwen/DashScope (impulsuri unice de 30/90 zile, nu capacitate
recurentă pt. un cron la 2h), Together (fără nivel gratuit), Cohere
(interzice explicit uzul automat/comercial — eliminare directă, nu doar
clasare joasă).

## 3. Întrebarea explicită: are sens un fallback în lanț?

**Nu ca multiplicator de capacitate zilnică — da, limitat, ca plasă de
siguranță pentru cădere sistemică.**

Argument:
1. **Plafonul de azi e bugetul, nu quota Gemini** (§0). Un al doilea provider
   nu crește volumul dincolo de ce oricum n-a fost cerut — dacă
   `MAX_AI_CALLS_PER_RUN` rămâne 18, providerul 2 nu se atinge niciodată în
   funcționare normală. Adăugarea lui NU rezolvă "prea puține știri" —
   asta se rezolvă din buget/TTL/clustering, pârghii deja identificate.
2. `main.py` are deja o singură verigă (`get_provider()`, if/else pe
   `AI_PROVIDER`) și un semnal explicit de cădere sistemică
   (`ai_down = provider.calls>0 and failures>=calls`, `main.py`). Un lanț de
   2-3 furnizori triplică suprafața de validare cerută de regula "No mangled
   output" (§7): fiecare furnizor are propriul format JSON, propriile
   refuzuri, proprii timeout-uri — `_parse_json` din `process.py` deja
   tolerează variații Gemini; fiecare provider nou adaugă un mod de eșec
   nou de acoperit, nu doar o sursă de capacitate.
3. Fiecare provider adăugat = un ToS distinct, un secret distinct în
   GitHub Actions, o pagină de pricing de re-verificat periodic (vezi cât
   de des s-au schimbat cifrele Gemini/Groq/Cerebras chiar în ultimele
   luni, conform surselor de mai sus) — cost de întreținere recurent, nu
   doar de integrare inițială.
4. **Unde chiar are sens:** ca plasă de siguranță pt. cădere TOTALĂ Gemini
   (model retras, cheie moartă — exact ce a pățit site-ul cu alias-ul
   `-latest`, 3 zile de site înghețat). Acolo, UN singur backup (Groq,
   locul 1) branșat pe semnalul `ai_down` deja existent — nu round-robin
   pe fiecare apel — dă redundanță reală cu risc minim: se activează rar,
   testat rar, nu concurează cu Gemini pentru volum zilnic.

**Concluzie:** dacă obiectivul e "mai multe știri/zi", pârghia e bugetul +
eventual o a doua cheie Gemini (cost marginal ~0). Dacă obiectivul e
"rezistență la o cădere Gemini de tip 21 iulie", un SINGUR backup (Groq) pe
semnalul de cădere sistemică existent e justificat. Un lanț de 3+ furnizori
rutat pe epuizare de quotă adaugă fragilitate (§5 din cerere) fără o nevoie
dovedită — quota Gemini nu pare epuizată azi (§0).

## 4. Pași concreți de integrare — Groq (câștigătorul), raportat la `base.py`

Neimplementat — doar planul, pentru când proprietarul decide să meargă mai
departe:

1. **`generator/providers/groq.py`** (nou), formă paralelă cu `gemini.py`:
   - `class GroqProvider(Provider)`, `name = "groq"`.
   - `available()` → `bool(os.getenv("GROQ_API_KEY", "").strip())`.
   - `_complete(system, user)` → POST REST simplu cu `urllib.request` (fără
     SDK, consistent cu convenția repo-ului) la
     `https://api.groq.com/openai/v1/chat/completions`, header
     `Authorization: Bearer <key>`, body OpenAI-shape:
     `{"model": MODEL, "messages": [{"role":"system",...},{"role":"user",...}],
     "temperature": 0.2, "response_format": {"type": "json_object"}}`.
   - Model fixat explicit via `GROQ_MODEL` env (implicit ceva testat empiric
     pe română — de ales DUPĂ un test manual, nu presupus), NU un alias
     "-latest" fără verificare (lecția din `gemini.py:15-16` e că aliasurile
     pot schimba comportament peste noapte, dar și fixarea rigidă poate
     lovi 404 la retragere — de decis explicit, nu implicit).
   - Retry pe 429/500/503 cu backoff, aceeași formă ca `gemini.py:67-88`
     (Groq nu are multi-cheie nativ în cod momentan — de adăugat doar dacă
     se dovedește necesar).
2. **`generator/process.py:get_provider()`** — adaugă a treia ramură
   `elif config.AI_PROVIDER == "groq":`, sau (pentru cazul de plasă de
   siguranță de la §3) un mecanism separat de fallback pe `ai_down`, NU
   confundat cu switch-ul manual `AI_PROVIDER` existent — de clarificat cu
   proprietarul care variantă vrea înainte de a scrie cod.
3. **`generator/config.py:162`** — extinde comentariul `AI_PROVIDER` la
   `"gemini" | "anthropic" | "groq"`.
4. **Secret nou** în GitHub Actions: `GROQ_API_KEY`, adăugat în
   `build.yml` lângă `GEMINI_API_KEY` (§10 din CLAUDE.md: config de deploy
   nu se atinge fără instrucțiune explicită — pasul ăsta cere OK-ul
   proprietarului, nu doar al acestui research).
5. **Verificare empirică OBLIGATORIE înainte de commit** (§7 CLAUDE.md,
   aceeași regulă ca la clustering): rulează modelul Groq ales pe 10-15
   articole reale în română, compară títluri/teasere cu ce produce Gemini
   azi pe aceleași articole — dacă nu trece bara "Zero Zgomot", nu se
   integrează, indiferent cât de bun e prețul.

## 5. Ce n-am putut verifica (onest, nu estimat)

- Cifrele exacte Gemini free-tier pe pagina publică oficială (fără login) —
  am folosit convergența a minim 4 surse terțe independente, dar pagina
  primară (`ai.google.dev/gemini-api/docs/rate-limits`) trimite explicit la
  un dashboard autentificat.
- Rata-limită exactă Z.ai pentru GLM-4.5-Flash pe o pagină oficială primară.
- Cifrele Mistral (RPS/TPM/TPM-lună) pentru tier-ul gratuit — pagina oficială
  de tier trimite la admin console, needisponibilă fără cont.
- Dacă DashScope internațional cere card la activare — surse contrazictorii,
  nicio declarație oficială tranșantă găsită.
- Calitatea RO propriu-zisă a oricărui model candidat — nimic din research
  ăsta e un benchmark; e research de limite/preț/ToS, nu de calitate
  lingvistică. Orice candidat ales tot trece prin verificarea empirică de
  la §4 pas 5 înainte de a publica ceva.
