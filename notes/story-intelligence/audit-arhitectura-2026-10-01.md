# Audit arhitectural pentru „Story Intelligence" — izz.ro

Data: 2026-10-01 · Branch: `claude/story-audit` (worktree izolat) · Read-only, nimic implementat.
Metodă: fiecare afirmație marcată **[FAPT]** (citit direct în fișier, cu cale:linie) sau
**[INTERPRETARE]** (dedus din cod/date, nu observat direct). Nimic nu a fost rulat (fără venv
funcțional pe Windows; pytest interzis de mandat). Toate numerele de linie au fost verificate pe
versiunea din acest worktree (`origin/main` la `851f831e`).

Scop: pregătirea transformării „gruparea articolelor despre același eveniment într-o unitate
STORY → surse → fapte → contradicții → timeline → sinteză".

---

## A. Arhitectura actuală relevantă — fluxul complet

**Declanșare și infrastructură.** `.github/workflows/build.yml:9` — cron `13 * * * *`, cu poartă
de cadență (job `cadenta`, build.yml:27-47, prag 105 min de la ultimul commit pe
`data/articles.json`) → publicare efectivă ~2 h. Jobul `pipeline` rulează
`python -m generator.main` (build.yml:83) cu `MAX_AI_CALLS_PER_RUN=40` (build.yml:74),
`UPGRADE_RESERVE=4` (build.yml:75), `IZZ_REQUIRE_HUMAN_GATE` variabil (build.yml:82).
Pipeline-ul NU randează în jobul de continut: comite starea (build.yml:126-163) și commitul
declanșează deploy-ul Cloudflare Workers Builds (assets-only, `wrangler.jsonc`: `./output`,
`not_found_handling: 404-page`). Jobul `mirror` face `--render-only` pe content_sha și publică
oglinda pe `gh-pages` al lui `Ramanul/ramanul.github.io` (build.yml:169-209); `release-probe`
verifică live (build.yml:211-225). [INTERPRETARE] comanda efectivă de build a Workers Builds
(echivalentul `--render-only`) trăiește în dashboard-ul Cloudflare, nu în repo — nu există câmp
de build command în `wrangler.jsonc`.

**Fluxul din `generator/main.py:run()` (main.py:339):**

1. **Ingest** — `fetch.fetch_all()` (generator/fetch.py:965): ~99 surse literale din
   `config.SOURCES` (config.py:10-221) + până la 300 surse GOLD fără RSS (config.py:227-236,
   `LOCAL_GOLD_LIMIT`) + până la 250 surse `wp_json`/`html_list` (config.py:242-251,
   `LOCAL_HTML_LIMIT`). Fetch paralel `ThreadPoolExecutor` cu invariant de ORDINE (ordinea din
   config decide prioritatea bugetului AI, fetch.py:970-977), cache ETag/Last-Modified
   (`data/feed_cache.json`), pacer per host, retry 429. Fiecare item: `url` normalizat,
   `original_link`, `source`, `source_name`, `source_lang`, `original_title`, `title`,
   `description`, `category` (a sursei), `published` (ISO UTC), `model: None` (fetch.py:866-878).
   Garda de conținut ostil (`generator/guard.py`, chemată la fetch.py:859-865) respinge itemul,
   nu încearcă repararea. La final `src_extra` = câte cuvinte aduce descrierea peste titlu
   (fetch.py:1071-1072) — baza regulii Zero Zgomot (`MIN_SUBSTANTA_CUVINTE = 5`, config.py:314).
2. **Deduplicare la intrare** — pe URL, în `run()`: față de stare (`known`) ȘI între itemele
   proaspete (`vazute`) — main.py:358-367. Câștigă primul în ordinea din config. [FAPT]
   `state.merge()` (state.py:150) NU e apelată în producție — singurul apelant e
   tests/test_state.py (consemnat și în comentariul main.py:352-356).
3. **TTL la ingest** — `state.expire()` (state.py:163; TTL-ul de la data auditului era 20 de zile, config.py:386)
   taie itemele deja expirate la citire (main.py:374) și din nou pe starea finală (main.py:446).
4. **Clustering** — `cluster.cluster()` (generator/cluster.py:61): leader clustering (nu
   single-link) pe titluri, tokeni cu stemming RO la 6 litere, intrare în cluster doar dacă
   seamănă cu sămânța: `JACCARD_MIN = 0.30` ȘI `SHARED_TOKENS_MIN = 3` simultan (cluster.py:8-9,
   50-58), doar în fereastra `RECENT_HOURS = 24` (cluster.py:7). Clustering CROSS-RUN:
   `cluster.attach_recent()` (cluster.py:101) lipește la clusterele noi și articole recente din
   stare, cu prag STRICT `_strict_match` (cluster.py:84-93: `inter>=4 și jac>=0.40` sau
   `inter==3 și jac>=0.50`) + gardă pe entități AI disjuncte (cluster.py:127-129). Un cluster cu
   ≥ `CLUSTER_MIN_SOURCES = 2` domenii DISTINCTE e candidat de sinteză C
   (`is_synthesis_candidate`, cluster.py:138-144; config.py:333).
5. **Procesare AI** — `process_new()` (main.py:118), în ordinea bugetului calculată de
   `_cluster_rank` (coroborare = domenii distincte, apoi proaspetime, main.py:40-48;
   specs/ai-budget-ordering.md):
   - itemele fără substanță (`src_extra < 5`) NU ajung la AI — respinse definitiv înainte de
     clustering și buget (main.py:142-148);
   - clustere C întâi, în LOTURI: `process_clusters_batch()` (generator/process.py:666), 1 apel
     per `CLUSTER_BATCH_SIZE = 3` clustere (config.py:326), main.py:184-195;
   - model B în loturi: `process_batch()` (process.py:441), 1 apel per `BATCH_SIZE = 10`
     articole (config.py:318), main.py:198-203;
   - sursele oficiale (`pl_/cj_/pr_`) determinist, fără AI: `process_official()` (process.py:430),
     main.py:205-206.
   Regula transversală „No mangled output": un item nemapat/invalid/curat-de-gardă NU se publică
   brut — rămâne afară din stare și se reia la rularea următoare (process.py:443-444, 724).
   Provider: cascada Gemini → (opțional router multi) → Ollama local (process.py:77-121);
   fără provider disponibil → fallback determinist, marcat `processed_by = "fallback"`, pe care
   `_quality_gate` îl EXCLUDE din publicare (select.py:373-374).
   Clasificare: `_resolve_category` (process.py:267) — axa geografică din TEXT (gazetteer
   `generator/geo.py`, `clasifica` geo.py:505, sate doar pe judetul sursei `judet_sursa`
   geo.py:356), cu garda „locul e subiectul?" (`_locul_e_subiectul` process.py:231) și excepția
   sport; tema vine de la model (`ai_cat` brut păstrat, process.py:498).
6. **Stare** — `state.save()` (generator/state.py:235): scriere atomică (`os.replace`, state.py:253-258),
   scrub juridic al textelor brute de la surse după procesare AI (`_scrub_processed`,
   state.py:174), normalizare UTC, sortare desc pe `published`, gardă anti-colaps
   (`_refuza_colapsul`, state.py:111, `PRAG_COLAPS = 0.20`). `data/articles.json` = listă JSON
   plată, **23 MB** la data auditului, 1.133 articole `model: "C"` în fereastra TTL [FAPT: numărate
   cu grep]. Slug-ul e atribuit ÎNAINTE de save ca să intre în stare: `render.assign_slugs()`
   (render.py:245, apel din main.py:533).
7. **Poarte înainte de publicare** — `eventdata.attach()` (generator/eventdata.py:240, apel
   main.py:426): coperte din date (prognoză Open-Meteo, cutremure EMSC) pe articole noi;
   titlul-doar-dată respins pe toată starea (main.py:437, `util.fara_titluri_data`); grounding
   gate — defer pe URL-urile cu citate/cifre straine detectate de `generator/raport_copiere.py` +
   `tools/grounding_gate.py` (main.py:451-466, env `IZZ_RAPORT_COPIERE_GATE`, build.yml:85-88);
   upgrade AI al fallback-urilor vechi în rezerva de buget (`upgrade_fallbacks` main.py:247,
   rezervă plafonată `ai_reserve` main.py:225).
8. **Moderare** — `moderation.apply()` (generator/moderation.py:259, apel main.py:468-469) peste
   `moderation.yaml` (fail-closed, moderation.py:149-166): blocklist URL/cuvinte, suppress surse,
   corrections, takedowns cu audit trail (`data/takedown_log.jsonl`), `featured`, human gate pe
   sintezele C (`hold_important` sau `IZZ_REQUIRE_HUMAN_GATE`, moderation.py:305-307), garda
   guard.py din nou, apoi dedup editorial final `_dedup_visible` (moderation.py:222, același
   `_strict_match` din cluster + fereastră 48 h, moderation.py:192-219).
9. **Randare** — `render.build()` (generator/render.py:657, apel main.py:536):
   quality gate `_quality_gate` (generator/select.py:337, apel render.py:661 — exclude fallback,
   body gol, titlu trunchiat, cluster C cu surse incoerente `sources_coherent` select.py:310);
   supapa bugetului de fișiere `_articole_publicabile` (render.py:284; `OUTPUT_FILE_BUDGET=17000`,
   `OUTPUT_FILE_CEILING=20000`, `OUTPUT_NON_ARTICLE_RESERVE=4200`, config.py:406-427); coperte og
   (primele `OG_COVER_MAX_ARTICLES=1200`, config.py:433) + copertă per categorie; homepage
   tablou de bord; pagina `/surse/` + harta județeană; **graf de subiect per entitate**
   (`_entity_index` select.py:98, pagini `/subiect/<slug>/` cu timeline `ol.timeline` în
   templates/subject.html:26-33, feed de urmărire de la `SUBJECT_FEED_MIN_ARTICLES=12`,
   conexiuni prin co-ocurență cu departajare IDF, render.py:895-948); pagini de categorie cu
   paginare; pagina de articol (templates/article.html) cu „Surse", „Articole conectate"
   (≥ `RELATED_MIN_SHARED=2` entități comune, render.py:981-1010), marcaj AI Act art. 50(4)
   (`ai_generat`, render.py:686); 404 util; sitemaps, feed RSS, căutare, `build.json`.
   Randarea deterministă e testată (tests/test_determinism_render.py).
10. **QA și livrare** — `tools/qa_check.py` blocant înainte de commit (build.yml:123-124);
    commit `update content` pe `main` (build.yml:126-163) → deploy Cloudflare; IndexNow
    (plan/send, build.yml:119-121, 165-167); `release-probe` confirmă sha-ul pe live.

Modelul de date persistent: **NU există nicio entitate între „articol" și „site"**. Totul e o
listă plată de articole în `data/articles.json`; gruparea de eveniment e EFEMERĂ (există doar în
memoria unei rulări) și persistă doar ca **conținut al sintezei C**: `sources` (listă
nume+URL dedup pe domeniu), `first_source`, `updated` — exemplu real citit în
data/articles.json:172-182.

---

## B. Fișierele care controlează fiecare etapă

| Etapă | Fișier:linie | Rol |
|---|---|---|
| Declanșare/cadență | `.github/workflows/build.yml:9,27-47` | cron orar + poartă 105 min |
| Buget AI | build.yml:74 (`MAX_AI_CALLS_PER_RUN=40`), generator/main.py:393 | plafon de apeluri/rulare (12 local default) |
| Ingest RSS/sitemap/wp_json/html | generator/fetch.py:796 (`_fetch_one`), :965 (`fetch_all`) | aducere, parsare, gardă, `src_extra` |
| Surse (catalog) | generator/config.py:10-256; generator/local_sources.py | catalogul + inserarea GOLD/html în ordinea bugetului |
| Garda de conținut | generator/guard.py (verdict la fetch.py:859, moderation.py:287) | respingere item compromis/clickbait-anomalie |
| Dedup la intrare | generator/main.py:358-367 | dedup pe URL față de stare + intra-run |
| TTL / stare | generator/state.py:163 (`expire`), :235 (`save`), :77 (`load`), :111 (anti-colaps) | `data/articles.json`, atomic, scrub juridic |
| Clustering intra-run | generator/cluster.py:61 (`cluster`), praguri :7-10 | leader clustering pe titluri (Jaccard+tokeni) |
| Clustering cross-run | generator/cluster.py:101 (`attach_recent`), :84 (`_strict_match`) | absorbția știrilor noi în evenimente publicate |
| Sinteză C (lot) | generator/process.py:666 (`process_clusters_batch`), :640 (`_prep_cluster_rep`), prompt :46-59 | 1 apel / 3 clustere; rep, surse, `updated` |
| Titlu/rezumat B (lot) | generator/process.py:441 (`process_batch`), :512 (`process_single`), prompt :18-28, :62-74 | titlu+teaser+entități+icon |
| Reprezentant C (cale single) | generator/process.py:553 (`process_cluster`) | **neapelată de producție** (vezi C) |
| Clasificare/geo | generator/process.py:267 (`_resolve_category`), generator/geo.py:505, :356 | axa geografică din text, gazetteer UAT+sate |
| Coperte din date | generator/eventdata.py:240 (`attach`) | meteo/cutremure atașate articolelor noi |
| Grounding gate | generator/raport_copiere.py, tools/grounding_gate.py, main.py:451-466 | defer articole cu citate/cifre străine |
| Moderare | generator/moderation.py:149 (`load`), :259 (`apply`), :222 (`_dedup_visible`) | control-plane `moderation.yaml`, human gate, dedup final |
| Quality gate | generator/select.py:337 (`_quality_gate`), :310 (`sources_coherent`), apel render.py:661 | Zero Zgomot: exclude output degradat |
| Slug/permalink | generator/render.py:245 (`assign_slugs`) | slug unic per categorie, atribuit o singură dată |
| Randare | generator/render.py:657 (`build`), templates/*.html | site static în `output/` |
| Graf de subiect | generator/select.py:98 (`_entity_index`), render.py:895-948, templates/subject.html | pagini `/subiect/` cu timeline (precedent STORY) |
| Buget de fișiere | generator/render.py:284, config.py:406-433 | supapa plafonului de 20.000 fișiere |
| QA pre-commit | tools/qa_check.py, build.yml:123-124 | blocant înainte de `update content` |
| Validare opțională | generator/claude_orchestrator.py, main.py:266 | validator Claude Code, off implicit |

---

## C. Ce există DEJA și poate fi reutilizat pentru STORY

**Verdict pe registre (cerut de mandat):**
- **[FAPT] `generator/agents.py` nu mai există.** A fost cod mort (239 linii), confirmat în
  registru IZZ-0284 (2026-09-02) și șters în IZZ-0289 (2026-09-03): „zero referinte în
  generator/, tools/, scripts/, .github/". Ce a supraviețuit e `generator/claude_orchestrator.py`
  (validatorul Claude Code, importat la main.py:21). Nu e nimic de reutilizat de acolo.
- **[FAPT] `process_cluster` (process.py:553) NU mai e apelat de producție — confirmat.**
  Producția importă și apelează doar `process_clusters_batch` (main.py:19, main.py:188);
  căutarea în generator/ + tests/ arată toate cele 8 utilizări în teste. Registru IZZ-0285
  consemnează exact asta („Productia importa doar process_clusters_batch; nu exista cale de
  rezerva catre calea single"). Partea NON-AI a logicii (rep, surse, `updated`) e duplicată în
  `_prep_cluster_rep` (process.py:640-663), folosită de calea batch — deci logica de sinteză e
  VIUĂ, doar calea single e moartă. IZZ-0294 o ține la decizia proprietarului (§10 — sinteza C
  e zonă protejată).
- **[FAPT] `state.merge()` (state.py:150) nu e chemată în producție** — dedup-ul real stă în
  `run()` (main.py:358-367). De ținut minte: orice plan care „adaugă articole în stare" trebuie
  să treacă prin `combined` din `run()`, nu prin `merge`.

**Reutilizabil direct:**

1. **Clustering-ul pe eveniment există și e calibrat** — cluster.py:61 (leader, anti-chaining),
   praguri măsurate pe corpus: `_strict_match` calibrat pe perechi reale (CFR/Ceară, Ormuz vs
   Messi/Ronaldo, cluster.py:84-93), gardă anti-șablon pe entități disjuncte (cluster.py:127-129),
   dedup editorial ultim (moderation.py:222). STORY nu are nevoie de un detector nou — are nevoie
   ca REZULTATUL grupării să devină persistent și navigabil.
2. **Sinteza C e un mini-STORY incomplet.** Rep-ul C are deja: `sources` dedup pe domeniu cu
   rolul „cine relatează evenimentul" (process.py:649-659), `first_source` (scor de originalitate),
   `updated` (process.py:662 — baza „update-uri"), `synthesis` în care promptul CEREA deja
   „marchează daca sursele se contrazic" (USER_C_BATCH, process.py:57) — dar marcajul, dacă
   apare, e text plat în sinteză, nestructurat. Actualizarea la același permalink e decizie
   IZZ-0151 (comentariu main.py:151-157): sinteza absoarbe știrea nouă și se rescrie.
3. **Câmpurile geo/locale** — categoria geografică (`local/judetean/regional`) e rezolvată la
   ingest din text (gazetteer geo.py:505, sate geo.py:328+ doar pe judetul sursei config.py:56+,
   garda „locul e subiectul" process.py:231) și PINNED (config.py:280). [FAPT] **Nu există câmp
   geo stocat pe articol** (eșantion articles.json: nu are `loc`/`judet`); localitatea derivabilă
   există doar ca funcții (`loc_din_titlu` geo.py:678, `locuri_numite` geo.py:492) și ca
   infrastructură de coordonate în eventdata (`data/localities_coords.json`). Pentru STORY,
   localitatea evenimentului poate fi derivată determinist la nevoie, dar nu e gratis la fiecare
   randare — vezi D.
4. **Timeline-ul de UI există ca precedent** — pagina `/subiect/` randează deja o cronologie
   (`ol.timeline`, templates/subject.html:26-33) și conexiuni între entități (render.py:932-934).
   Este însă timeline de ENTITATE (toate articolele care menționează „ANAF"), nu de EVENIMENT.
5. **Structura `data/articles.json`** — listă plată, sortată desc pe `published`; câmpurile
   pe articol (citite pe eșantioane reale): `url, original_link, source, source_name,
   source_lang, title, category, published, model (B/C), src_extra, teaser | synthesis, entities,
   ai_cat, icon, processed_by, prompt_version, featured, slug`, plus pe C: `sources, first_source,
   updated`, plus opțional `event_chart`, `corrections` aplicate din moderare. Scrub-ul juridic
   șterge `original_title`/`description` de pe articolele procesate AI (state.py:174-184) —
   consecință directă pentru STORY: **textul surselor nu mai există în stare**, deci „faptele"
   trebuie extrase în momentul procesării, nu retroactiv.
6. **Economiile de buget** — batching C (3/apel) și B (10/apel), ordonarea pe coroborare
   (main.py:40-48), rezervă plafonată de upgrade (main.py:225-244): orice pas STORY trebuie
   proiectat să încapă în ACELAȘI răspuns C, nu să adauge apeluri.
7. **Infrastructura gratuita deja acoperită** — GitHub Actions (cron + mirror + probe),
   Cloudflare Workers Free cu plafonul 20.000 fișiere gardat mecanic (render.py:284,
   OUTPUT_FILE_CEILING=20000), fără DB: singura stare e `data/articles.json` comisă în git.

**Dovadă din date că problema STORY e reală [FAPT]:** în `data/articles.json` există DOUĂ
sinteze C SEPARATE despre același eveniment (controalele ANAF la achizițiile de lux): una
`published 2026-10-01T05:50:09Z` cu surse Profit.ro+Economica, alta `05:58:13Z` cu surse
Alba24+G4Media (articles.json:439-455 vs 168-184). Două pagini concurente pentru un eveniment,
imposibil de reunit retroactiv de cititor.

---

## D. Ce LIPSEȘTE pentru modelul STORY

1. **Identitate persistentă a evenimentului (`story_id`).** Clusterul există doar în memoria
   `run()`-ului; singura amprentă persistentă e permalink-ul sintezei C (stabil prin IZZ-0151).
   Nu există un id care să lege: sinteza C → membrii absorbiți → actualizările ulterioare.
2. **Sursele pe eveniment pentru articole.** Articolul B are doar sursa lui; membrii ABSORBIȚI
   de o sinteză C sunt ȘARSI din stare (main.py:431-432, `folded`) — istoricul „cine a relatat
   ce și când" se pierde la fiecare absorbție. Pagina C păstrează doar lista `sources`.
3. **Fapte comune vs. afirmații single-source.** `synthesis` e text plat 40-90 cuvinte
   (SYNTHESIS_MAX_WORDS=90, config.py:332); nu există structură „fapt → care surse îl susțin".
   Promptul C ar putea cere asta, dar răspunsul nu are unde să fie stocat structurat.
4. **Contradicții structurate.** Cerința „marchează dacă sursele se contrazic" din prompt
   (process.py:57) nu are câmp dedicat; dacă modelul o marchează, dispare în prosă.
5. **Timeline de eveniment.** `updated` e UN singur timestamp (ultima rescriere, process.py:662);
   nu există listă „ce s-a schimbat, când, din ce sursă". „Actualizat" e tot ce vede cititorul
   (templates/article.html:33).
6. **Memorie pe evenimente lungi.** `attach_recent` lucrează doar în fereastra de 24 h
   (cluster.py:7) și doar pe potrivire textuală strictă; un eveniment care se derulează peste
   mai mult de o zi, sau cu titluri divergente („incendiu" → „mortul de la incendiu"), se
   RUPE într-o sinteză nouă. Iar articolele expiră la 20 zile ÎMPREUNĂ cu sinteza lor
   (state.expire nu face excepție pentru C, state.py:163-171) — STORY-ul nu poate fi „viu"
   mai mult decât fereastra TTL, în afara unei decizii de arhivă (issue #198, decizie de
   proprietar — STATE.md).
7. **Suprafață de randare STORY.** Nu există template/page pentru „eveniment": niciun
   `/story/<id>/`, iar `templates/article.html` nu are secțiuni pentru fapte/contradicții/
   timeline. Graful `/subiect/` (per entitate) e suprafața cea mai apropiată, dar semantica
   e alta (entitate ≠ eveniment).
8. **[INTERPRETARE] Prioritizarea bugetului pentru update-uri.** Ordinea bugetului (coroborare +
   proaspetime, main.py:40-48) nu știe nimic despre „story deja deschis care merită update în
   detrimentul unui cluster nou". Nu e blocant pentru un STORY v1, dar devine vizibil imediat
   după.

---

## E. Planul minim de implementare — 5 etape incrementale

Constrângerile respectate: zero API plătit, zero embeddings externe, zero apeluri AI suplimentare
(extinderile merg ÎN răspunsul C existent), SQLite/local doar (de fapt: totul în
`data/articles.json`, fără DB nouă — cel mai mic diff), plafonul de fișiere neatins (nu se
adaugă pagini noi în etapele 1-3), regula Zero Zgomot neatinse (gate-urile existente rămân pe
calea fiecărui articol). Ordinea recomandată: întâi ce răpește date (fără care nu se poate
merge retroactiv — procesarea e one-shot, scrub-ul juridic sterge sursa), apoi ce se vede la
cititor.

**Etapa 1 — Persistența evenimentului: `story_id` + păstrarea membrilor absorbiți.**
- Conținut: rep-ului C i se scrie `story_id` (URL-ul canonical al sintezei, deja stabil prin
  IZZ-0151 — sau hash-ul lui); itemele absorbite NU se mai șterg din stare, ci primesc
  `story_url = <story_id>` și rămân ne-published (skip la randare, la QA-count și la
  `_dedup_visible`). Membrii expiră odată cu story-ul (TTL pe cel mai nou membru, de discutat).
- Fișiere atinse: `generator/process.py` (`_prep_cluster_rep`), `generator/main.py` (bucla
  `folded` din `process_new`/`run`, combined), `generator/render.py` (skip la publicare),
  `generator/moderation.py` (`_dedup_visible` să nu le vaneze), `generator/state.py` (TTL pe
  grup), `tests/test_story_id.py` (nou) + `tests/test_sinteza_actualizata.py` (regresie).

**Etapa 2 — Fapte structurate pe sinteza C (aceleași apeluri AI).**
- Conținut: promptul C-batch cere în plus `facts: [{text, sources: [idx]}]` (max 3-5 fapte,
  fiecare cu indecșii surselor din blocul evenimentului); parsare tolerantă, fallback la
  sinteză fără fapte când câmpul lipsește — **niciun apel în plus, niciun buget nou**. Garda
  `prompt_version` se bumpează → upgrade-urile vechi reprocesează treptat din rezerva existentă.
- Fișiere: `generator/process.py` (prompt + parsare în `process_clusters_batch`), `generator/config.py`
  (PROMPT_VERSION), `tests/test_story_facts.py` (nou).

**Etapa 3 — Contradicții + timeline determinist.**
- Conținut: `contradictions` opțional în același răspuns C (text scurt + sursele în conflict);
  `timeline` construită FĂRĂ AI la fiecare absorbție: {published, title, url} pentru fiecare
  membru al story-ului, sortată — datele există deja pe iteme. 
- Fișiere: `generator/process.py` (câmpul contradictions), `generator/main.py` (agregarea
  timeline la combinare), `tests/test_story_timeline.py` (nou).

**Etapa 4 — Randarea STORY pe pagina sintezei existente.**
- Conținut: `templates/article.html` extins pentru `model == "C"`: bloc „Fapte confirmate"
  (fapt + sursele lui), bloc „Surse în conflict" când există, timeline-ul evenimentului cu
  linkuri interne spre membrii existenți. ZERO fișiere noi în `output/` (aceeași pagină,
  conținut în plus) — plafonul de 20.000 nu se mișcă.Marcajele AI Act existente se păstrează.
- Fișiere: `generator/render.py` (pregătirea contextului pentru C), `templates/article.html`,
  `tests/test_story_render.py` (nou, Jinja randare deterministă).

**Etapa 5 — Continuitatea evenimentelor lungi (căutarea story-ului deschis).**
- Conținut: la clustering, itemele noi se potrivește ÎNTÂI cu story-urile deschise (rep C cu
  `story_id`, ferestra extinsă la TTL, potrivire pe `entities` + `_strict_match` — mecanism
  deja existent în `attach_recent`, doar candidatii devin rep-urile C); prag NEschimbat față de
  azi la prima livrare (doar候选人 extinși), recalibrat doar cu probe over/under-merge pe corpus
  real, cum cere CLAUDE.md §7.
- Fișiere: `generator/cluster.py` (`attach_recent`), `generator/main.py` (apelul), 
  `tools/qa_check.py` (metricate story: sinteze separate pe acelasi eveniment), tests.

Cost total estimat al planului: 0 apeluri AI suplimentare pe rulare, 0 fișiere output
suplimentare, +~4 câmpuri JSON pe articol C și +1 câmp pe membri.

---

## F. Riscurile fiecărei etape

- **E1:** (a) `data/articles.json` crește — membrii absorbiți rămân în stare; la 23 MB deja,
  fiecare +1 MB e comis de ~12 ori/zi în git. (b) `_refuza_colapsul` numără articole, nu
  caractere — nu se declanșează, deci creșterea e tăcută: trebuie metrică. (c) Membrii
  „ne-publicați" pot scăpa prin căi care iterează `combined` direct (sitemap, căutare) dacă skip-ul
  se pune doar în `render.build`. (d) Schimbarea semanticii `folded` atinge invariantul
  „no mangled output" doar aparent (itemele rămân, dar nu se publică) — de documentat în
  registru. (e) `state.expire` poate rupe story-ul (membrii mor înaintea sintezei) — alegerea
  TTL-ului de grup e o decizie editorială, nu tehnică.
- **E2:** (a) Răspunsul C per lot crește → risc de trunchiere JSON la `maxOutputTokens=4096`
  (gemini.py; precedent documentat la ridicarea BATCH_SIZE, config.py:327-329) → pierdere tacută
  de lot; atenuare: CLUSTER_BATCH_SIZE rămâne 3, fapte limitate, garda `_parse_json_array` +
  nemapat = amânare (deja sigur). (b) Hallucinare de atribuire (fapt pus pe sursa greșită) —
  atenuare: validați mecanic că idx-ul există în bloc; fapt fără sursă validă → aruncat, nu
  publicat. (c) Bump de PROMPT_VERSION declanșează upgrade în masă — rezerva `ai_reserve` e
  plafonată exact pentru asta (main.py:225-244), dar coada crește câteva zile.
- **E3:** (a) Timeline-ul agregat crește nestrain cu membrii; limită de N intrări (ultimele) +
  „și încă X" editorial. (b) Sursele scrub-uite (fără `original_title` după procesare,
  state.py:174) dau timeline cu titluri AI — acceptabil, dar de numit, nu de ascuns.
  (c) Contradicțiile sunt afirmația cea mai delicată juridic: formularea „sursele raportează
  diferit" (atribuire sursei), niciodată verdict de adevăr — altfel încalcă spiritul REGULI-SINTEZA.md.
- **E4:** (a) Pagina C devine mai lungă → Lighthouse/pa11y baseline (`source-command-audit`)
  poate mișca scoruri — de măsurat înainte/după. (b) Sintezele C fără `facts` (v1 sau fallback)
  trebuie să randeze IDENTIC cu azi — regresie vizibilă altfel. (c) `display_title`/`titlu_afisare`
  nu trebuie atinse (Zero Zgomot: 6-16 cuvinte, hard ceiling 22).
- **E5:** (a) Fiecare relaxare a `attach_recent` = risc de over-merge (două evenimente reunite
  greșit — cel mai scump eșec editorial posibil aici); CLAUDE.md §7 cere probe empirice
  over/under-merge pe eșantioane reale ÎNAINTE de merge. (b) Garda entităților disjuncte
  (cluster.py:127-129) trebuie păstrată pe calea nouă. (c) Supapa `qa_check` nouă poate deveni
  roșie istoric (sinteze duplicate existente, vezi C) — prag de la zero sau listă albă.

---

## G. Criterii de acceptare, test necesar și regresie posibilă — per etapă

| Etapă | Criteriu de acceptare | Test necesar | Regresie posibilă |
|---|---|---|---|
| E1 | După o rulare cu absorbție: rep-ul C are `story_id`; membrii absorbiți EXISTĂ în stare cu `story_url`, nu apar în `output/` și nu dublează contorul QA; `_dry-run` verde | `tests/test_story_id.py`: absorbție simulată (mimic test_sinteza_actualizata.py) → starea finală conține membrul; randare → membrii absenți din `output/` | `test_sinteza_actualizata.py` (perma permalink), `test_dedup_intre_surse.py` (dedup editorial nu mănâncă membrii), `test_buget_fisiere.py` (numărul de pagini nu crește) |
| E2 | Clusterele C procesate cu modelul nou poartă `facts` validat (fiecare `sources[i]` ≤ lungimea blocului); lotul fără `facts` se publică ca azi, fără eșec; `ai_calls` pe rulare NESCHIMBAT | `tests/test_story_facts.py`: răspuns cu fapte → stocate; fără câmp → publicare normală; idx invalid → fapt aruncat | `test_ai_budget_order.py`, `test_ai_cat_persistat.py` (contractul câmpurilor persistate), trunchiere JSON: test cu răspuns tăiat → lot amânat, nu publicat parțial |
| E3 | Rep C are `timeline` sortată crescător, o intrare per membru unic; `contradictions` prezentă doar când modelul o dă, cu surse existente; zero apeluri în plus (timeline e deterministă) | `tests/test_story_timeline.py`: agregare din 3 membri → 3 intrări sortate; membru duplicat (același URL) → 1 intrare | `test_determinism_render.py` (ordinea intrărilor nu depinde de set-uri/hash), `test_substanta_sursa.py` |
| E4 | Pagina C arată blocurile noi doar când există date; pagina fără `facts`/`timeline` e bit-cu-bit identică cu randarea de azi (excepție: conținutul nou); validare pa11y/Lighthouse pe eșantion | `tests/test_story_render.py`: randare Jinja cu și fără date; snapshot/diff pe cazul „fără date" | `test_determinism_render.py`, audit front-end (baseline `AGENTS.md`), `test_entity_sections.py` (subiecte neatinse) |
| E5 | O știre nouă despre un eveniment cu story deschis (>24 h) e absorbită de story-ul vechi la același permalink, cu `updated` scris; zero creșteri de over-merge pe proba de corpus | `tests/test_cluster.py` extins: potrivire pe entități cu pragul strict Neschimbat; probă over-merge pe eșantion real (CLAUDE.md §7), `tools/qa_check.py` cu metrica story | `test_cluster.py` (praguri), `test_dedup_intre_surse.py`, proba mecanică anti-șablon (cronici sportive) din cluster.py:107-110 |

**Poarte transversale pe TOATE etapele:** `python -m pytest tests/ -q` + `python -m ruff check .`
+ `python -m generator.main --dry-run` înainte de fiecare PR; qa_check blocant în CI;
`IZZ_REQUIRE_HUMAN_GATE` rămâne comutatorul editorial pentru sintezele C (și, la E2-E3, pentru
fapte/contradicții — recomandat să extindă hold-ul la câmpurile noi); fiecare decizie primeste
rând în `specs/registru.tsv` (CLAUDE.md §5.19), cu §10 amintit: logica de sinteză/atribuire
Model C e zonă protejată — E2 și E5 o ating și au nevoie de instructiune explicită de proprietar.

---

## Concluzii cheie (rezumat)

1. Arhitectura e deja „story-ready" pe jumătate: clusterul pe eveniment, pragurile calibrate,
   sinteza multi-sursă cu surse dedup și actualizare la permalink (IZZ-0151) EXISTĂ și sunt în
   producție pe calea batch; lipsește doar persistența grupului și structurarea lui.
2. Registrele se confirmă: `agents.py` e șters (IZZ-0289); `process_cluster` e cod accesat doar
   de teste, producția trece prin `process_clusters_batch` (IZZ-0285) — logica de sinteză e vie
   prin `_prep_cluster_rep`.
3. Cel mai mare risc al planului nu e AI-ul (0 apeluri noi), ci starea: membrii absorbiți trebuie
   păstrați în `articles.json` deja la 23 MB, iar TTL-ul de 20 zile rade story-urile împreună cu
   membrii lor — decizie editorială, nu tehnică.
4. Al doilea risc: orice relaxare a clusteringului (E5) e pasul cu cel mai scump eșec posibil
   (două evenimente reunite greșit); §7 cere probe empirice, iar dovezile din starea actuală
   (două sinteze C separate pe același eveniment ANAF) arată că și PRAGURILE DE AZI sub-unesc.
5. Totul încape în infrastructura gratuită existentă dacă randarea STORY rămâne PE pagina
   sintezei existente (zero pagini noi) și extinderile AI merg în răspunsul C existent
   (zero apeluri noi).
