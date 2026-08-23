# STATE — project execution state

> Single source of truth for "where we are". Manager-owned; updated at the end of every slice.
> Executors get it read-only. **Hard cap: ~40 lines of content.** When it grows past that, cut
> the settled history into `specs/istoric-executie.md` — do not let it accumulate here. It is
> read at the start of every session, so every stale line is paid for twice: in tokens, and in
> an executor re-implementing something that already shipped. `git fetch` immediately before
> rewriting it.
>
> **Cut on 2026-08-21** from 656 lines, the second time. What it cost, stated so nobody repeats
> it: two sections were headed `Open PR` while both PRs were already **merged** (#196 on 08-20,
> #197 on 08-21), and the 195-line `## Open` section was almost entirely SHIPPED/FIXED/REVERTED
> history with two live rules buried in it. That is the same failure the 08-07 cut documented.
> **A section is `Open` only if a PR is open or a decision is pending — check, don't assume.**

**Updated:** 2026-08-23 (route regression on `izz.ro/*` found — restore before touching Pages)

## Open

- **REGRESSION, unfixed: the `izz.ro/*` route was moved off `izz-failover` onto `izz-ro`**
  (off-session 08-23, declared finished on an HTTP 200 — which says *something* answered, not
  *who*). That route is the redundancy layer, not a middleman: moving it drops mirror failover,
  the edge Cache API and the `x-izz-*` headers, and `infra/wrangler.toml` still declares it for
  `izz-failover`, so the next `wrangler deploy` there reclaims it silently.
  **Pages is NOT safe to delete yet:** a Worker route needs a proxied DNS record, and a
  Pages-managed apex CNAME can leave with the project. Route first, Pages last — commands and
  the deletion trap in `infra/VERIFICARE-CLOUDFLARE.md` (`IZZ-0237`).
- **Host is a Worker, not Pages** (#211 `40ac007`); Workers Paid active → ceiling 100,000;
  `ALT_ORIGIN` set 08-23, all five workflows probe the Worker. **#209** (`27b1abb`, draft, ready
  to review) recalibrates budget/ceiling to 90,000/100,000, reading the ceiling from the
  Cloudflare docs; the guard stays — the silent deploy-refusal is host-independent.
- **PR #202 (draft) `claude/lumina-reguli-sesiuni-ypgdky`** — wrong-county map fix (A/B: 12
  articles moved, all correct). Rules half already landed; only the map half is still open.
- **Archive as a separate surface ("varianta 3")** — owner asked to be reminded 08-21; not
  started, still an owner decision. `ARTICLE_TTL_DAYS` went 7 → 30 (#197) as the cheap half;
  `tools/arhiva.py` already reconstructs the full series from git history.
- **From `specs/atribuire-cercetare-si-plan.md`, in order** — E1 permalink decoupled from
  category (**owner decision, blocks all retroactive correction**), E3 focus score instead of
  `max()`, E4 separate topic/place axes (**owner decision**), E5 gold set grown to ~150 + CI gate.

## Standing rules that keep being rediscovered — do not "fix" these

- **`state.merge()` is dead code, NOT a live bug.** `state.py:95`; the only caller is
  `tests/test_state.py:14`. Dedup between fresh items happens inline at `main.py:227-236` (#158).
  The recurring "lying function" hunt keeps rereading it as a duplicate bug; touching it is an
  opportunistic refactor (§5.6).
- **Map: do not re-land the enlarged hit areas without a scroll guard.** Reverted 2026-08-15
  (`c6397735`), owner-confirmed on device. Before retrying: suppress re-selection mid-scroll.
- **Attribution: `specs/atribuire-cercetare-si-plan.md` is the dossier — do not re-research it.**
  7 external systems, 8 causes, a 6-stage plan, paid for once. Run `tools/eval_atribuire.py`
  before and after **any** change to `geo.py`. Baseline 2026-08-08: category 25/39 (64%),
  place-on-badge 31/32 (97%). Covers are never redrawn on a first run (`IZZ-0163`, owner refused
  2026-08-06); `FORCE_REGEN=1` is the opt-in.

## Where the rest lives

`specs/istoric-executie.md` (everything cut from here, verbatim — measurements, killed
hypotheses, the bot-challenge diagnosis, owner answers) · `specs/registru.tsv` + `python
tools/registru.py find` (decisions, incl. what was rejected and why) · `infra/README-failover.md`
(the canonical serving architecture) · `specs/masuratori-frontend.md` (Lighthouse/CLS) ·
`specs/istoric-operational.md` (cadence, delegation) · `../HANDOFF.md` (cross-account state).
