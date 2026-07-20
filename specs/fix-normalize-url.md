# Task: fix-normalize-url — scheme-less URLs produce https:///www...

**Executor:** OpenCode (Zen). **Branch:** `oc/fix-normalize-url` from current `main`.
(Same task as GitHub issue #67, reassigned from Jules to OpenCode.)

## Bug (verified by manager 2026-07-19, twice)
`generator/util.py::normalize_url`: for scheme-less input (`www.Example.com/articol`),
`urlsplit` puts everything in `path` (no `//`), netloc stays empty → output
`https:///www.example.com/articol`. `normalize_url` is the DEDUP KEY for articles.

## Goal
- In `normalize_url`, before `urlsplit`, if the stripped input is non-empty and has no
  scheme (no `"://"` and does not start with `"//"`), prepend `"https://"`.
  `www.Example.com/articol` must normalize to `https://example.com/articol`.
- Behavior for inputs WITH a scheme must stay byte-identical (dedup keys must not change).
- Update `tests/test_util_edge.py::test_normalize_url_no_scheme_and_port` to assert the
  corrected output, and add one case for a bare domain (`example.com/x`).

## Hard rules
- Authorized files ONLY: `generator/util.py`, `tests/test_util_edge.py`. Stage by path.
- Minimal diff. No refactors. Do not touch other functions.

## Acceptance
- `python -m pytest tests/ -q` → ALL pass (56 baseline + new case), zero failures.
- Commit on `oc/fix-normalize-url`, message in English, STOP — no push, no merge, no PR.

## UNTOUCHABLE (user WIP)
- `generator/render.py`, `data/entities/salariul-minim.yaml` (modified, uncommitted)
- `specs/**`, `.claude/**` (manager-owned)
