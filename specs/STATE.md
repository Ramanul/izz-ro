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

- **INCIDENT — the output is past the Cloudflare Pages file ceiling, so deploys fail.** Rendered
  locally: 5240 articles -> 18452 files, 5205 -> 20337, 6195 (`main`) -> 21075 — 2.75 files each.
  The pass/fail line sits between #204/#203/#202's base (5800 articles, build OK) and #205's
  (5922, build FAILED): about 20,000 files. Driver: `ARTICLE_TTL_DAYS` 7 -> 30 (#197) took the
  state 4466 -> 6195 in two days, no plateau for ~4 weeks. `main` is over. Owner call (`IZZ-0238`).
- **PR #199 `fix/recuperare-404-pagini-indexate`** — was red: recovered articles kept the dead
  `zonal` category, which renders no page but still emits links (9 broken; `main` renders 0). Fixed
  at source (`config.CATEGORII_REDENUMITE`), 5 records migrated, 4 tests. Awaiting merge.
- **PR #205 (draft) `claude/getty-images-licensing-d1kupt`** — CC BY / CC BY-SA photos on article
  pages only. pytest green, renders exit 0; its Cloudflare failure is the ceiling above, not its
  diff. Getty rejected (`IZZ-0237`).
- **PR #201 (draft) `claude/surse-din-istoric-si-rubrica-ai`** — AI rubric, geographic scale,
  translation. Green: all 17 new sources answer `ok`; the red `feeds` job is a manual
  `workflow_dispatch` probe whose dead sources are pre-existing on `main`.
- **PRs #202 / #203 / #204 (drafts)** — docs only, every check green, awaiting owner merge.
- **Archive as a separate surface ("varianta 3")** — owner decision; `tools/arhiva.py` rebuilds it.
- **From `specs/atribuire-cercetare-si-plan.md`, in order** — E1 permalink decoupled from category
  (**owner decision, blocks all retroactive correction**), E3 focus score instead of `max()`,
  E4 separate topic/place axes (**owner decision**), E5 gold set ~150 + CI gate.

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
