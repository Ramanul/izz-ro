# TASKS-MISTRAL.md — coadă de lucru pentru Mistral Vibe (local)

> Scris de Claude Opus 5, 14 aug 2026, 18:40. Fiecare task e independent și are criteriu de
> acceptare verificabil prin rulare. Le iei **în ordine**, unul per sesiune.
>
> **Contractul tău e `~/.vibe/AGENTS.md`** — se încarcă automat. Regulile din `CLAUDE.md` și
> `AGENTS.md` din repo se aplică peste el pentru domeniu (ce nu se atinge, cum se verifică).

## REGULI CARE ACOPERĂ TOATE TASK-URILE — citește înainte de orice

1. **Working tree-ul NU e al tău.** Repo-ul e pe branch-ul `fix/harta-lista-rezultate` și are
   modificări necomise ale proprietarului în `static/harta-stiri/` și `tools/`. **Nu le atinge, nu
   le stage-ui, nu le comite, nu da `git checkout`/`stash`/`restore` peste ele.** Un working tree
   murdar nu e o problemă de reparat.
2. **Stage-uiește EXPLICIT, pe cale.** Niciodată `git add -A` sau `git add .`. Doar
   `git add <calea exactă a fișierului pe care spec-ul ți-l dă>`.
3. **Nu face push și nu face merge în `main`.** Comiți pe branch-ul curent și te oprești.
4. **Verifică rulând.** Fiecare task are o comandă de acceptare. Rulează-o, pune ieșirea reală în
   raport. „Merge" fără ieșire nu contează.
5. **Dacă un task e ambiguu sau premisa lui e falsă, OPREȘTE-TE și scrie de ce.** Nu improviza o
   variantă apropiată. Un task nefăcut cu motiv scris e un rezultat bun.
6. **Scrie ce ai făcut** în `sessions/M/AAAA-LL-ZZ-HHmm-slug.md` (creează directorul dacă lipsește):
   ce ai schimbat, comanda de verificare, ieșirea ei, ce n-a mers.

---

## TASK 1 — `mistral.yml`: împiedică push-ul direct pe `main`

**Problema (confirmată, nu ipoteză).** În `.github/workflows/mistral.yml`, pasul care creează
branch-ul de lucru are `if: github.event_name == 'issues' || github.event_name == 'issue_comment'`,
iar pasul `Commit + push changes` **nu are nicio condiție**. La evenimentele
`pull_request_review_comment` și `pull_request_review` nu se creează branch, checkout-ul e pe
branch-ul default al repo-ului, iar `git push origin HEAD` aterizează pe `main`. Dovadă empirică:
`gh run list --workflow=mistral.yml --json headBranch` arată `main` pe toate rulările. Nu există
branch protection pe `main`.

**Ce faci.** Două modificări minime, ambele în `.github/workflows/mistral.yml`:
1. Pune pe pasul `Commit + push changes` condiția `if: env.BRANCH_NAME != ''` — aceeași gardă pe
   care o are deja pasul `Open PR`.
2. În corpul aceluiași pas, înainte de `git push`, adaugă o verificare care oprește execuția dacă
   branch-ul curent e `main`:
   ```bash
   CURRENT="$(git rev-parse --abbrev-ref HEAD)"
   if [ "$CURRENT" = "main" ]; then
     echo "::error::refuz push pe main din workflow"; exit 1
   fi
   ```

**Nu schimba nimic altceva** în fișier. Fără reformatări, fără reordonări de pași.

**Criteriu de acceptare:**
```bash
python -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/mistral.yml',encoding='utf-8')); s=d['jobs']['mistral']['steps']; p=[x for x in s if 'Commit' in str(x.get('name',''))][0]; print('conditie pe push:', p.get('if')); print('garda main in script:', 'abbrev-ref' in p.get('run',''))"
```
Trebuie să tipărească o condiție ne-goală și `True`.

**Comite doar:** `git add .github/workflows/mistral.yml`

---

## TASK 2 — `mistral.yml`: fixează versiunea CLI-ului

**Problema.** Toate acțiunile GitHub din fișier sunt fixate pe SHA, dar pasul
`Install mistral-vibe CLI` rulează `uv tool install mistral-vibe` **fără versiune**. La fiecare
rulare se ia ultima publicată, într-un job care are `contents: write` și cheia de API în mediu.
Pachetul are 79 de versiuni publicate, deci se mișcă des.

**Ce faci.** Schimbă comanda în `uv tool install mistral-vibe==2.24.1`. Adaugă deasupra un
comentariu de o linie care spune de ce e fixată versiunea și că se ridică manual.

**Criteriu de acceptare:**
```bash
grep -n "uv tool install mistral-vibe" .github/workflows/mistral.yml
```
Trebuie să conțină `==2.24.1`.

**Comite doar:** `git add .github/workflows/mistral.yml`

---

## TASK 3 — `mistral.yml`: nu mai raporta eșec când n-a fost nimic de schimbat

**Problema.** Pasul `Open PR (from issue/comment)` are doar `if: env.BRANCH_NAME != ''`. Când vibe
nu modifică niciun fișier, pasul de commit iese cu `exit 0` fără să pusheze branch-ul, iar
`gh pr create` crapă cu `No commits between main and mistral/issue-N-...`. Jobul iese pe eșec și
postează „❌ @mistralai a eșuat" pe issue, deși comportamentul corect era „n-a fost nimic de făcut".
Asta a cauzat două rulări roșii pe 14 aug.

**Ce faci.** În pasul `Commit + push changes`, când nu sunt schimbări, scrie un marcaj în
`$GITHUB_ENV` (de exemplu `HAS_CHANGES=false`, altfel `HAS_CHANGES=true`). Adaugă apoi condiția pe
pasul `Open PR` ca să ruleze doar când `HAS_CHANGES == 'true'`. Ai grijă ca pasul final de raportare
să rămână cu `if: always()`.

**Criteriu de acceptare:** același script de la Task 1, adaptat pentru pasul `Open PR` — trebuie să
arate o condiție care include `HAS_CHANGES`.

**Comite doar:** `git add .github/workflows/mistral.yml`

---

## TASK 4 — inventar de verificare, fără modificări de cod

Rulează, în ordine, și pune ieșirea fiecăreia în jurnal. **Nu repara nimic** — doar raportează.

```bash
python -m pytest tests/ -q 2>&1 | tail -5
python -m generator.main --render-only 2>&1 | tail -5
python -c "import tomllib; tomllib.load(open('C:/Users/cw_26/.vibe/hooks.toml','rb')); print('hooks.toml valid')"
node C:/Users/cw_26/.vibe/hooks/adapter.test.cjs 2>&1 | tail -3
node C:/Users/cw_26/.vibe/hooks/adapter-post-agent.test.cjs 2>&1 | tail -3
```

Dacă vreuna eșuează, **scrie ieșirea exactă și oprește-te acolo** — nu încerca s-o repari.
Task-ul ăsta există ca să știm dacă ceva s-a stricat între timp, nu ca să reparăm.

---

## Ce NU faci, în niciun task

- Nu atinge `data/articles.json`, `moderation.yaml`, `.github/workflows/build.yml`.
- Nu face push, nu deschide PR, nu comenta pe issue-uri. Nimic care iese public.
- Nu șterge și nu muta fișiere pe care nu le-ai creat tu.
- Nu instala pachete și nu modifica setări de sistem.
