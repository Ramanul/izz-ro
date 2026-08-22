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

**Updated:** 2026-08-21 (deploy ceiling hit; six open PRs, inventory verified against GitHub)

## Open

- **INCIDENT — output past the Cloudflare Pages file ceiling; `main` cannot deploy.** CONFIRMED:
  #206 is docs-only on `main` and its build FAILED, so the cause is the base's size, not code.
  The 20,000 limit was already written in `render.py:844` (docs, verified 08-07) together with
  "TTL cannot realistically pass ~14 days"; #197 set it to 30 without re-reading that. Owner call.
- **MERGED — PR #199 `31f2b02`** (recovered pages Google has indexed; the dead-`zonal` fix and the
  union-on-`url` conflict resolution are in the merge commit). **Announce to A still owed (§14).**
- **PR #205 (draft) `claude/getty-images-licensing-d1kupt`** — CC BY / CC BY-SA photos on article
  pages only. pytest green, renders exit 0; its red Cloudflare is the ceiling. Getty out (`IZZ-0237`).
- **PR #201 (draft) `claude/surse-din-istoric-si-rubrica-ai`** — AI rubric, geographic scale. Green:
  all 17 new sources answer `ok`; the red `feeds` job is a manual probe whose dead sources predate it.
- **PRs #202 / #203 / #204 / #207 (drafts)** — docs only, awaiting owner merge. #202 also fixes
  CLAUDE.md §14: the announce channel points at `TASKS-B.md`, frozen since 08-04 — a live defect
  on `main` until it lands. **Merge hazards, measured:** `IZZ-0237` is claimed by both #204 and
  #205 (`IZZ-0241`); FOUR branches rewrite this file (#202, #205, #206, #207) and only #202
  carries the `Landed` record for #200 — keep it. None of the four touches `output/`.
- **Archive as a separate surface ("varianta 3")** — owner decision; `tools/arhiva.py` rebuilds it.
- **From `specs/atribuire-cercetare-si-plan.md`** — E1 permalink decoupled from category (**owner
  decision, blocks retroactive correction**), E3 focus score not `max()`, E4 axes, E5 gold ~150.

## Standing rules that keep being rediscovered — do not "fix" these

- **`state.merge()` is dead code, NOT a live bug.** `state.py:95`; the only caller is
  `tests/test_state.py:14`. Dedup between fresh items happens inline at `main.py:227-236` (#158).
  The recurring "lying function" hunt keeps rereading it as a duplicate bug; touching it is an
  opportunistic refactor (§5.6).
- **Map: do not re-land the enlarged hit areas without a scroll guard.** Reverted 2026-08-15
  (`c6397735`), causation confirmed on device by the owner. Before retrying: suppress
  re-selection while a scroll is in flight. Full mechanism in the archive.
- **Attribution: `specs/atribuire-cercetare-si-plan.md` is the dossier — do not re-research it.**
  7 external systems, 8 causes, a 6-stage plan, paid for once. Run `tools/eval_atribuire.py`
  before and after **any** change to `geo.py`. Baseline 2026-08-08: category 25/39 (64%),
  place-on-badge 31/32 (97%). Covers are never redrawn on a first run (`IZZ-0163`, owner refused
  2026-08-06); `FORCE_REGEN=1` is the opt-in.

## Where the rest lives

`specs/istoric-executie.md` (everything cut from here, verbatim — measurements, killed
hypotheses, the bot-challenge diagnosis, owner answers) · `specs/registru.tsv` +
`python tools/registru.py find` (decisions, incl. what was rejected and why) ·
`specs/masuratori-frontend.md` (Lighthouse/CLS) · `specs/istoric-operational.md` (cadence,
delegation, autonomy history) · `../HANDOFF.md` (the cross-account state, ~30 lines).
