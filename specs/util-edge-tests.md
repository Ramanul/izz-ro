# Task: util-edge-tests — edge-case tests for generator/util.py

**Executor:** OpenCode (Zen). **Branch:** `oc/util-edge-tests` from current `main`.

## Goal
Add `tests/test_util_edge.py` (NEW file) with 4–6 edge-case tests for the existing pure
functions in `generator/util.py` (`strip_diacritics`, `normalize_url`, `domain_of`,
`clean_html`, `truncate_words`, `title_tokens`). Suggested cases: empty-string inputs,
`truncate_words` at the exact `max_words` boundary, `normalize_url` on a URL without scheme
or with a port, `title_tokens` with only stopwords/short words.

## Hard rules
- READ the implementation first; tests assert CURRENT behavior. Do NOT modify any
  generator code. If current behavior looks buggy, note it in your report — do not "fix" it.
- Authorized files: `tests/test_util_edge.py` — NOTHING else. Stage only this file, by path.

## Acceptance criteria
- `python -m pytest tests/ -q` → ALL tests pass (49 existing + the new ones), zero failures.
- Commit on branch `oc/util-edge-tests`, message in English, then STOP — no push, no merge, no PR.

## UNTOUCHABLE (user/manager WIP — never touch, stage, restore, or discard)
- `generator/render.py` (modified, uncommitted)
- `data/entities/salariul-minim.yaml` (modified, uncommitted)
- `AGENTS.md` (modified, uncommitted)
- `opencode.json`, `.claude/**`, `specs/**` (manager-owned)
