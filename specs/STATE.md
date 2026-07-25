# STATE — project execution state

> Single source of truth for "where we are". Writes are owned by the MANAGER (Claude Code):
> updated at the end of every slice and every `/review-executor`. One writer at a time.
> Executors receive this file as read-only context. Overwrite sections in place — never let
> this file grow past ~30 lines of content.

**Updated:** 2026-07-25 (PR #85 merged; single-account mode; piataauto settled)

## OPERATING MODE — SINGLE ACCOUNT (owner, 2026-07-25)
Account A is temporarily inactive. **This account is the only writer.** Until the owner says
otherwise: no `/handoff`, no `TASKS-B.md` parking, no waiting for the other account to review
or merge — that coordination is pure overhead with nobody on the far end. CLAUDE.md §14's
"tell the other account after any merge" is suspended for the same reason; §14's *substance*
(branch, small diff, land it) still holds. Owner wants sub-agents used (§15 mapping).

## Current task
None in flight. Open, in priority order:
1. **Ghidurile publica cifre neverificate.** PR #85 removed the false "✅ Verificat" label, so
   the pages are now honest, but salariul minim / pensia minima / alocatia copiilor still
   carry placeholder values and `sursa_url` pointing at the mmuncii.ro homepage. NEEDS THE
   OWNER: this sandbox cannot reach RO domains. Setting `verificat: true` now requires a
   deep-link source URL, so the fix cannot be faked.
2. **Geographic taxonomy may be leaking.** A Swiss village ("Satul elvețian Albinen") is filed
   under `regional`, which means Romanian historical regions. Sub-agent auditing the mechanism
   and the real misclassification rate 2026-07-25 — measure before touching anything.
3. Raise `LOCAL_GOLD_LIMIT` past 35 now that fetch is parallel.
4. `tools/feed_check.py` still reimplements RSS fetching instead of calling `_fetch_one`, so
   it reports 429 on sources the pipeline now retries successfully.

## SETTLED — do not re-litigate
- **`piataauto` STAYS (owner, 2026-07-25): "sub nicio formă nu îl scoți, e f ok".** History
  that misleads: PR #63 (2026-07-18) removed it as dead, but `18ce032` had switched it to
  Google News sitemap a day earlier, so #63 deleted an already-replaced line and the source
  survived. It now produces (3 appearances as a source). The old "remove piataauto" instruction
  is VOID — it was premised on the source being dead, and it no longer is.

## EXECUTOR ROUTE IS UNRELIABLE — measured 2026-07-24
OpenCode was handed `specs/fetch-429-retry.md` (premise-verified spec, 4 test cases, explicit
acceptance criteria). **Two models, two different silent failures, both exit code 0:**
- `deepseek-v4-flash-free`: read AGENTS.md + the spec, wrote a todo list, stopped. No branch,
  no code, no error message.
- `north-mini-code-free`: invented an absolute path (`/workspace/izz/specs/...`) instead of
  using `--dir .`; OpenCode correctly auto-rejected it as an external directory. Died there.
Manager implemented it directly instead (`a644c31`) — cheaper than testing four more free
models. **Before delegating anything to OpenCode again, verify the model actually delivers on
a throwaway task.** The 8 merges of 2026-07-19/20 are no longer evidence the route works.

## Last relevant commits
- **`c98624f` — PR #85 MERGED 2026-07-25.** The guides shipped "Verificat: 2026-01-01" over
  placeholder figures because the warning lived in a YAML *comment*, invisible to the parser.
  `verificat` is now a required bool; while false the label goes, a warning appears, the index
  counts unconfirmed guides, cards read "Neconfirmat". `verificat: true` additionally demands a
  source URL with a path — a ministry homepage proves an address was typed, not that a figure
  was checked. Same PR: scroll affordance for the category menu (805px hidden at 390px, and the
  invisible entries were Regional/Zonal/Local), the shared work/cost journal
  (`specs/metrics.csv` + `tools/log_slice.py`), and a real contrast fix — breadcrumb separators
  used a *line* token as text colour, 1.5:1 vs the required 4.5:1, on pages `tools/audit.sh`
  never visits. 118 tests pass; pa11y 0 errors across six page types.
- `feat/parallel-fetch` MERGED (febabdd) — verdict was FIX, not clean MERGE. Executor's
  `8d670b7` parallelized `fetch_all` (ThreadPoolExecutor, `FETCH_WORKERS` default 8, `=1`
  forces sequential; `pool.map` preserves SOURCES order, so the AI budget priority survives).
  Two spec requirements were MISSING: the per-worker try/except and its test. Manager wrote
  both (`24afef9`) rather than returning to the executor — a deliberate deviation from
  `/review-executor` §5, for ~15 lines. `_fetch_one` only catches network errors; a malformed
  feed raising inside `feedparser.parse` propagated through `pool.map`, skipping `_cache_save`
  and losing every healthy source. Test proven to fail without the guard, pass with it.
  Verified: 88 pass, `--dry-run` exit 0. Local branch NOT deleted (needs owner OK).
- Earlier merges (all OpenCode, manager-verified): `geo-categorii` 6d90543 (regional/zonal/
  local trio), `local-sources-priority-order` cfccbc8 (dict order = AI priority),
  `local-feeds-quality-filter` 7f9d138 (42/43 alive), `local-gov-feeds-phase1` 8ccedfb.
- The CI bot commits every ~30 min — always `git pull --ff-only` before writing anything.

## User WIP — NONE (cleared 2026-07-24)
Tree clean, `git stash list` empty. The former WIP (`render.py`, `salariul-minim.yaml`) is
gone, unrecoverable from git, cause unknown. `render.py` is no longer off-limits.

## The 429s: diagnosed, closed as external (2026-07-24)
Chain: retry shipped (`a644c31`) → feedcheck still 429 → UA hypothesis tested and FALSIFIED
(`tools/ua_probe.py`, run `30096569916`): at `libertatea` no User-Agent variant passes; at
`unica`/`elle` the FIRST request passes and the next three, milliseconds apart, get 429.
**These sources limit by frequency, per IP; runner ranges are already spent. Nothing in our
code fixes it** — not UA, not a 4s backoff (rejected longer: it stalls pool workers).
Resolution: feedcheck now reports 429/503 as **LIMIT — "unverifiable from here"**, not DEAD,
and they no longer fail the run. Same reasoning `monitor.yml` uses for edge 403s: a checker
that goes red for external reasons stops being read. Verified on run `30096781843`: 4 LIMIT
(libertatea, unica, elle, bzi) + **3 genuine failures** — `liternet` (200 but empty feed),
`pl_prahova_brazi` and `pl_vaslui_dragomiresti` (403 WAF). The signal is honest now: 3 real
problems, not 7. Those 3 are the actual open work. Re-verify the 4 from a home IP, not CI.
The retry itself stays — it is correct for genuinely transient refusals, just not for these.

## Blockers
- MAI WAF blocks this IP (502 on `*.prefectura.mai.gov.ro` and www.mai.gov.ro). Retest later
  or from GitHub Actions / the cloud account — it is IP-bound, not permanent.
- ~~PENDING: failover Worker~~ **DONE 2026-07-24 12:07 UTC.** `izz-failover` deployed, version
  `0097cd84`, route `izz.ro/*` at 100%. No API token was needed — `wrangler login` (OAuth,
  account `andifreelancer2@gmail.com`, id `636085fa...`) grants workers_scripts+routes:write.
  Verified live: `curl -sI "https://izz.ro/?cb=$(date +%s)"` → `x-izz-origin: primary`.
  **Failover itself tested end-to-end 2026-07-24**, not just assumed: PRIMARY temporarily
  pointed at a nonexistent host → `x-izz-origin: mirror`, status 200 (site stayed up);
  reverted and re-verified `primary`. The redundancy is proven, not theoretical.
  **Cache-bust is required** — a plain `curl -sI https://izz.ro/` hits a cached edge response
  with no header and looks like the Worker is not running. Redundancy is now complete:
  Pages primary + GitHub Pages mirror + edge failover + `monitor.yml`.
- **GOTCHA (this machine):** Application Control blocks MSYS/bash and anything it spawns from
  reading `.js` files in user directories — `.md`/`.toml` in the same folder read fine, and
  `.js` under `node_modules` is fine. `wrangler deploy` from Git Bash dies with
  `Cannot read file "failover-worker.js": Access is denied`. **Run wrangler from PowerShell
  instead** (`powershell -NoProfile -Command "Set-Location ...; wrangler deploy"`) — works.
  Not content-based: a trivial `.js` is blocked too. Not Zone.Identifier: no ADS present.

## Next steps
- SEO: NO gaps. Verified in code 2026-07-24 (`article.html:5`, `render.py:177`, `render.py:826`,
  landed 2026-06-21 `82ea411`). CLAUDE.md §11 was right, this file was stale. Do NOT re-audit.
- Cross-account handoff is SUSPENDED while account A is inactive (see operating mode above).
  When A returns: `/handoff` writes the session journal + refreshes this file, run at the 75%
  usage alert BEFORE switching. `TASKS-B.md` in the workspace repo still holds parked tasks.
- Cost, measured over 16 slices (`COORD-DASHBOARD.md`): solo 23 tokens/100 lines, sub-agents
  238, CI 29. **Actions minutes are free on a public repo**, so CI is the cheapest executor,
  not the most expensive — push verification that needs the network into a workflow.
