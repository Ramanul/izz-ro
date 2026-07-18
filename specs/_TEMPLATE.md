# SPEC — <task title>

Read `AGENTS.md` in the repo root first and follow it strictly.

**Goal:** <one sentence — what exists after this task that does not exist now>

**Verified premises** (manager checked these against the repo on <date>):
- <claim> — verified via <command/file>
- <claim> — verified via <command/file>

**User WIP — UNTOUCHABLE** (do not restore/stash/stage/commit these):
- <path> (modified)

**Scope — authorized files ONLY:**
1. <path> — <create|modify> — <what>
2. <path> — <create|modify> — <what>
Touch NOTHING else.

**Verification:** run `<command>` — expected: <output>.

**Branch:** `devin/<task-slug>` from fresh `main`. Commit on green, then STOP.
Do not push, do not merge, do not open a PR.
