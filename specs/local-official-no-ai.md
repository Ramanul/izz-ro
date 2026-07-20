# Spec: local-official-no-ai

**Goal:** Official local-government items (source keys `pl_*`, `cj_*`, `pr_*`) must NOT
consume the AI budget. Evidence (builds 2026-07-20): they are mostly older than the
clustering RECENT window, so they queue behind ALL fresh national news and expire (TTL 7d)
before the 12-18 calls/run budget ever reaches them; with 1274 primării planned, per-item
AI can never scale. These are official public announcements, not clickbait — process them
deterministically via the existing fallback path (original title + truncated teaser),
zero AI calls. Branch: `oc/local-official-no-ai`.

## Files you may touch — NOTHING else
- `generator/process.py` (one new function)
- `generator/main.py` (partition in `process_new`)
- `tests/test_local_official.py` (NEW)

## UNTOUCHABLE — do not touch, stage, stash, or discard
- `generator/render.py` (user WIP, uncommitted)
- `data/entities/salariul-minim.yaml` (user WIP, uncommitted)
- `.claude/commands/delegate-jules.md`, `tools/jules_api.py` (untracked, not yours)
- any other file in the repo

## Task 1 — `generator/process.py`: new function

```python
OFFICIAL_PREFIXES = ("pl_", "cj_", "pr_")

def process_official(items: list) -> list:
    """Surse oficiale (primarii/CJ): fara AI. Titlu original + teaser trunchiat
    (fallback determinist), marcate 'official' ca sa nu fie reluate de
    upgrade_fallbacks."""
    done = []
    for it in items:
        out = process_single(it, None)
        if out is None or out.get("skip"):
            continue
        out["processed_by"] = "official"
        done.append(out)
    return done
```

Place it near `process_batch`. Do not modify `process_single` or anything else.

## Task 2 — `generator/main.py`: partition inside `process_new`
At the TOP of `process_new` (before `new_urls = ...`), partition:

```python
official = [i for i in new_items if str(i.get("source", "")).startswith(process_official_prefixes)]
new_items = [i for i in new_items if i not in official]
```

(Import `process_official` and `OFFICIAL_PREFIXES` from `.process` — extend the existing
`from .process import ...` line; use `OFFICIAL_PREFIXES` directly, the name above is
illustrative.) Then at the end, include the official items in the return:
`processed` must contain `process_official(official)` results IN ADDITION to the existing
flow, and official items must NOT go through clustering or consume `budget`/`used`.
Implementation: call `process_official(official)` right after the partition and extend
`processed` with the result just before `return`. Docstring of `process_new`: add one
line noting official sources bypass the AI budget.

## Task 3 — `tests/test_local_official.py` (NEW)
Build fake items (dicts with `source`, `original_title`, `description`, `category`,
`url`, `source_lang`="ro") and assert:
- `process_official` returns items with `model == "B"`, `processed_by == "official"`,
  `title == original_title`, non-empty `teaser`;
- teaser is truncated to `config.TEASER_MAX_WORDS` words at most;
- `process_new(items, provider=None, budget=0)` (mixed official + normal fake items, no
  existing) returns the official ones processed even with ZERO budget, and the normal
  ones untouched by the official path;
- an item with `source_lang == "en"` and official prefix is dropped (skip), not published.

## Acceptance
- `python -m pytest tests/ -q` → ALL tests pass.
- `python -c "from generator.process import process_official; print(process_official([{'source':'pl_x_y','original_title':'T','description':'d '*60,'source_lang':'ro','url':'https://e.x/1'}])[0]['processed_by'])"` → `official`.
- `git diff --stat` shows ONLY the 3 authorized files.

## Handoff
Work on branch `oc/local-official-no-ai` (create from current `main`, after
`git pull --ff-only`). When acceptance passes: commit with a clear message, then
**STOP — no push, no merge, no PR**.
