# PREDARE — continuarea planului IZZ.RO (fazele din PR #297) · 1 oct 2026, seara

Predat către: orice agent fără context (Grok/altul). Scris de sesiunea ZCode GLM-5.3-Flash (cota aproape epuizată, 13%).

## Ce este proiectul
- izz.ro = generator static de știri „Informația Zero Zgomot": Python + Jinja2 (`generator/`, `templates/`, `static/styles.css`), starea în `data/articles.json` (pipeline — NU edita manual), output în `output/` publicat pe Cloudflare **Workers Free — plafon 20.000 fișiere/versiune, acum ~17.100 (WARNING)**.
- Repo: `Ramanul/izz-ro`. `main` = producție, deploy automat la push. Owner: Alexandru, NU programează — rapoarte în română, pe înțelesul lui; cod și comite în engleză.
- Reguli de aur: branch per sarcină, niciodată push direct pe main; merge doar după CI verde; diff minim; zero fișiere noi în `output/`; zero servicii plătite; nu schimba URL-uri/canonical/sitemap/TTL (20 zile); fără FORCE_REGEN.

## Starea la predare
- main: `aad739e4`+ — bot de conținut comită orar; informația „main e la X" expiră într-o oră, fă mereu `git fetch origin main` înainte.
- **Faza 1 (masthead + numerele zilei) MERGED** (PR #379): dateline cu data RO pe toate paginile + „X știri · Y surse · Z județe în ultimele 24 de ore" pe prima pagină. De confirmat pe live: `curl -s https://izz.ro/ | grep dateline`.
- **PR #380 DESCHIS** (fazele 3/4/6, doar CSS): la `gh pr checks 380` toate pass → `gh pr merge 380 --merge`. Dacă pică: citește logul jobului căzut, nu re-push orbește.
- PR #375 (calibrare etichete coperte) — deja pe main, confirmat live.
- Watchdog: worker `izz-watchdog` în Cloudflare (cron 20 min, KV `izz-kv` cheia `status`, alerte în Workers Observability). Capcană: fetch worker→workers.dev același cont = 404; oglinda corectă = `ramanul.github.io/build.json`.
- SEO-TTL: `tools/seottl_raport.py` pe main (12.672 URL-uri expirate, cohorta 21–60 zile) + automatizare lunară (prima rulare 1 noiembrie).

## Ce rămâne (ordine)
1. Închide PR #380 (CI verde → merge).
2. Confirmă live fazele 1 și 3/4/6.
3. **Faza 2 — mini-harta „România în ultimele 24 de ore"**: branch `feat/faza2-mini-harta` pregătit în worktree `C:/Users/cw_26/izz-ro-wt-miniharta` (bazat pe faza 1). Sursa de design (nu diff — reimplementează pe main actual): `git show feat/cronica-vie-puls:generator/render.py` (funcția `_mini_harta`), `:templates/index.html` (blocul .puls), `:static/styles.css` (.puls*). `_numerele_zilei()` există pe main, expune `zi["pe_judet"]`; contururi în `data/harta_judete.json`. Zero JS, SVG inline, un singur link accesibil spre /static/harta-stiri/. Teste noi în `tests/test_mini_harta.py` după convenția din `tests/test_numerele_zilei.py`.
4. Faza 5 (reading progress): mică; elementul lipsește din `templates/article.html` — se adaugă + CSS, cu garda `prefers-reduced-motion`.
5. **Faza 7 (Art v2 + regenerare imagini) BLOCATĂ** până la primul trend de asset-uri (1 noiembrie: `notes/buget-assets-trend.md` + `https://izz.ro/asset_budget.json`, nivel WARNING 85,5%). NU regenera.
6. Manual (Alexandru): lunar, Search Console pe cohorte — lista în `notes/seottl-cohorte-2026-10-01.md`.

## Mediu (Windows, Git Bash)
- `python` (nu python3); `grep` = alias la ugrep → folosește `git grep`; lint: `python -m ruff check <fișiere>`.
- Teste: `python -m pytest tests/<fișier> -q`. Suita completă ~22 min — la faze mici rulează doar ce atinge. 2 teste `test_workflow_mistral_pr_gate` pică pre-existent pe main curat (mediu local) — nu sunt ale tale.
- Worktree-uri: `izz-ro-wt-miniharta` (faza 2), `izz-ro-wt-css` (PR #380). Restul NU sunt ale tale — nu le atinge; `git restore/checkout --` pe fișiere străine = interzis.
- Limită cont: UN singur subagent simultan (la 2 → „user concurrency limit exceeded"). Cota AI ~100M tokeni/zi/cont, reset la 19:00 România; 3 agenți paraleli au omorât o sesiune azi.

## Raportare
Antet final: Stare (fracție) · Verdict pe înțelesul lui · Ai de făcut: DA/NU → ce · Încredere n/10. [FAPT] = ai rulat și ai văzut; [INTERPRETARE] = inferență; „funcționează" doar după execuție.
