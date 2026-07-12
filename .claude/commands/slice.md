---
description: Run one vertical slice end-to-end the izz.ro way (spec -> plan -> implement -> verify by running -> commit on green).
argument-hint: [short description of the slice]
---

You are running the mandatory izz.ro slice workflow (CLAUDE.md §5–§6) for: **$ARGUMENTS**

Do NOT skip steps. Do NOT do broad multi-area edits.

1. **Spec first (3–8 lines).** State goal, inputs/outputs, and acceptance criteria for this ONE slice. No spec → no code.
2. **Plan.** Name the exact files this slice will touch. Do not edit anything yet. If the slice is non-trivial or touches clustering/synthesis/legal/deploy config (§10), stop and let me confirm the plan before editing.
3. **Implement ONE vertical slice.** Minimal diff — change the least necessary, no opportunistic refactors of adjacent code.
4. **Verify by RUNNING, not claiming.** Run the relevant command and capture the REAL output:
   - pipeline logic → `python -m generator.main --dry-run` (never a full run here — it spends AI quota and mutates state)
   - front-end output (templates / static/styles.css / render.py HTML/JSON-LD) → delegate to the `frontend-auditor` sub-agent, report the Lighthouse/pa11y delta
   - clustering → delegate to the `clustering-tuner` sub-agent (over-merge AND under-merge on real samples)
   - publishable quality → `python tools/qa_check.py` must return 0
   Check the output against the acceptance criteria. If you could not run it, say so — do not assert success.
5. **Commit on green only.** One clear commit for the verified slice. Then stop and report the result — do not roll into the next slice.
