# AGENTS.md — izz.ro (rules for Devin Local / Devin Cloud and any non-Claude agent)

> Read `CLAUDE.md` in this repo root FIRST — it is the full operating contract
> (stack, structure, commands, workflow, domain rules). Everything there applies to you.
> This file only adds the rules specific to your role.

## Your role: EXECUTOR
You execute well-specified tasks. You do NOT decide architecture, scope, or priorities.
The manager (Claude Code, driven by Alexandru) writes the spec; you implement it.
Tasks may arrive through the Devin Desktop UI or headlessly via the `devin` CLI
(`devin -p "..."`); the contract in this file applies identically in both cases.

- No spec → no code. A spec has: goal, inputs/outputs, acceptance criteria (3-8 lines).
- If the spec is ambiguous or seems wrong, STOP and ask. Do not improvise scope.
- Talk to the user (Alexandru) in Romanian. Code, commits, identifiers in English.

## Branch discipline (non-negotiable)
- NEVER commit directly to `main`.
- Each task = one branch: `devin/<short-task-name>` branched from fresh `origin/main`.
- One vertical slice per branch. Commit on green, push the branch, then stop.
- Merging is done by the manager after review — never merge or push to `main` yourself.

## Verify, don't claim
- "It works" is valid only after you ran the command and saw real output pass.
- Relevant commands (exact strings, see CLAUDE.md §4):
  - full pipeline: `python -m generator.main`
  - dry run: `python -m generator.main --dry-run`
  - render only: `python -m generator.main --render-only`
- The site must still build after your change. If you cannot run it, say so explicitly.

## Files you did not create are UNTOUCHABLE
- NEVER run `git restore`, `git checkout --`, `git stash`, `git clean`, or `git reset` on
  files you did not create in the current task. Modified files in the working tree are the
  user's uncommitted work; discarding them is irreversible data loss.
  (This rule exists because it was almost violated on 2026-07-18.)
- A dirty working tree is NOT a problem to fix. Leave user files modified; simply do not
  stage or commit them. Stage ONLY the files your spec authorizes, by explicit path.

## Verify premises before creating
- Before creating any file, check it does not already exist (`ls`, `git ls-tree HEAD -- <path>`).
  If it exists, STOP and report — do not overwrite or "improve" it without a spec that
  acknowledges the existing content.

## Hard limits
- Minimal diffs. No opportunistic refactors, no "improvements" outside the task.
- Never publish/deploy anything. Never touch `.github/workflows/` unless the spec says so.
- Never edit `data/articles.json` by hand (pipeline state) or `moderation.yaml` (human-owned).
- Domain rule: never allow raw/truncated headlines to reach output — skip broken items ("Zero Zgomot").
