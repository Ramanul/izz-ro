# SPEC — track cost per slice (log-based)

Read `AGENTS.md` in the repo root first and follow it strictly.

**Goal:** enable empirical accounting for when delegating a slice to a free
executor (Devin/OpenCode) is worth the manager overhead vs. Claude solo — via
an append-only CSV log plus a tiny stdlib helper CLI.

**Verified premises** (manager checked these against `origin/main` @ 6adff59 on 2026-07-20):
- `specs/metrics.log` does not exist — verified: `ls specs/metrics.log` → No such file
- `tools/log_slice.py` does not exist — verified: `ls tools/log_slice.py` → No such file
- `specs/metrics.md` does not exist — verified: `ls specs/metrics.md` → No such file
- `CLAUDE.md` §15 spans lines 104–126; §16 starts at 128 — verified: `grep -n "^## " CLAUDE.md`
- `requirements.txt` exists — no new deps needed (stdlib only)
- `specs/_TEMPLATE.md` exists — this spec follows it

**User WIP — UNTOUCHABLE** (do not restore/stash/stage/commit, per STATE.md 2026-07-20):
- `generator/render.py` (modified)
- `data/entities/salariul-minim.yaml` (modified)
- `.claude/commands/delegate-jules.md` (untracked, Jules onboarding WIP)
- `tools/jules_api.py` (untracked, Jules onboarding WIP)

**Scope — authorized files ONLY:**
1. `tools/log_slice.py` — CREATE — argparse CLI, stdlib only (argparse, csv, pathlib, datetime).
   Flags: `--slice STR` (required), `--approach {solo,devin,oc,jules}` (required),
   `--diff-lines INT` (required), `--executor-branch STR` (optional, default ""),
   `--duration-min INT` (optional, default ""), `--notes STR` (optional, default "").
   Behavior: if `specs/metrics.log` missing, create with header row
   `date,slice,approach,executor_branch,diff_lines,duration_min,notes` then append.
   If present, append only. `date` = today in `YYYY-MM-DD`. Use `csv.writer` with
   quoting=`csv.QUOTE_MINIMAL` so notes with commas are safe. Print the appended row to stdout.
   Sanitize `notes` against CSV/formula injection: if it starts with `=`, `+`, `-`, `@`,
   or a tab/CR, prefix it with a single `'` before writing (spreadsheet-safe escaping;
   does not affect CSV parsing, only how spreadsheet apps render the cell).
   No side effects beyond writing `specs/metrics.log`. No network. Exit 0 on success.
2. `specs/metrics.log` — DO NOT commit an empty file; will be created on first run of the helper.
   (Devin: do NOT `touch` this file — verification below creates it.)
3. `specs/metrics.md` — CREATE — max 20 lines. Sections: what the file is (1 line), column
   meanings (7 lines, one per column), the rule ("delegăm implementare estimată >5k tokeni;
   sub asta, overhead spec+review > economia"), how to append (one-line example invocation).
   Romanian text (user language per CLAUDE.md §0).
4. `CLAUDE.md` — MODIFY — insert one short paragraph inside §15, placed after line 126 and
   before the §16 header on line 128. Exactly:
   `**Cost tracking (metrics.log, added 2026-07-20):** manager-owned CSV log at`
   `\`specs/metrics.log\` with one row per verified slice — see \`specs/metrics.md\`.`
   `Rule: delegăm implementare estimată >5k tokeni către Devin/OpenCode; sub asta`
   `overhead spec+review depășește economia.`
   Match the tone of the surrounding §15 paragraphs (English framing, Romanian rule quote OK).

Touch NOTHING else. No changes to `requirements.txt`, `.github/`, tests, or any generator/ file.

**Verification** — run this exact sequence and paste the real output in the final report:

```
python tools/log_slice.py --slice track-cost-per-slice --approach devin \
  --diff-lines $(git diff --stat main | tail -1 | awk '{print $4+$6}') \
  --executor-branch devin/track-cost-per-slice \
  --notes "seed row from the delegation that created this feature"
cat specs/metrics.log
python tools/log_slice.py --slice smoke-test --approach solo --diff-lines 3
cat specs/metrics.log
```

Expected: first run creates file with header + 1 data row; second run appends a 2nd data row.
Header line must be exactly:
`date,slice,approach,executor_branch,diff_lines,duration_min,notes`
Both data rows visible; no exceptions, exit 0 both times.

Also confirm:
- `python -c "import csv, pathlib; import tools.log_slice"` succeeds (module imports clean).
- `head -1 specs/metrics.md | wc -c` > 1 (file non-empty).
- `grep -c "Cost tracking (metrics.log" CLAUDE.md` returns `1`.

**Branch:** `devin/track-cost-per-slice` from fresh `origin/main`.
Commit on green (one commit, message like `feat(metrics): add per-slice cost log + helper`),
then STOP. Do not push, do not merge, do not open a PR. Report in Romanian.
