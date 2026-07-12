---
description: Run the local front-end audit (Lighthouse + pa11y) and report score deltas vs the CLAUDE.md baseline.
allowed-tools: Bash(bash tools/audit.sh:*), Read, Grep, Glob
---

Delegate to the `frontend-auditor` sub-agent (or run it directly): execute `bash tools/audit.sh` and report the result per CLAUDE.md §13.

Report as a small before/after table:
- Lighthouse for BOTH home and article: Performance / Accessibility / Best-practices / SEO.
- pa11y WCAG2AA error count on home.
- The "before" baseline is the "Current scores" line in CLAUDE.md §13 unless I gave you fresh before-numbers.

Rules:
- If `lighthouse` or `pa11y` is missing, the one-time fix is `npm i -g lighthouse pa11y` — say so, don't silently skip.
- Call out any regression explicitly. Do NOT edit templates/CSS and do NOT start an optimization marathon — you measure, I decide the next slice (§13).
- New colors must clear 4.5:1 contrast against BOTH `--paper` AND `--gold-wash`, not just white.
