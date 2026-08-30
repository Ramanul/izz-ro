---
name: "source-command-audit"
description: "Run the local front-end audit (Lighthouse + pa11y) and report score deltas vs the AGENTS.md baseline."
---

# source-command-audit

Use this skill when the user asks to run the migrated source command `audit`.

## Command Template

Delegate to the `frontend-auditor` sub-agent (or run it directly): execute `bash tools/audit.sh` and report the result per CLAUDE.md §13.

Report as a small before/after table:
- Lighthouse for BOTH home and article: Performance / Accessibility / Best-practices / SEO.
- pa11y WCAG2AA error count on home.
- The "before" baseline lives in `specs/masuratori-frontend.md` (section "Baseline"), not in
  CLAUDE.md — it was moved there on 2026-08-06. Use it unless I gave you fresh before-numbers.

Rules:
- Tool boundary: the Claude Code command this was ported from is limited to
  `Bash(bash tools/audit.sh:*), Read, Grep, Glob`. Codex has no per-command allowlist, so it is
  binding as text: run `bash tools/audit.sh`, read and search — nothing else, and no edits.
- If `lighthouse` or `pa11y` is missing, the one-time fix is `npm i -g lighthouse pa11y` — say so, don't silently skip.
- Call out any regression explicitly. Do NOT edit templates/CSS and do NOT start an optimization marathon — you measure, I decide the next slice (§13).
- New colors must clear 4.5:1 contrast against BOTH `--paper` AND `--gold-wash`, not just white.
