# Task: fix-smoke-brand — update stale brand descriptor in smoke_live.py

**Executor:** OpenCode (Zen). **Branch:** `oc/fix-smoke-brand` from current `main`.

## Context (verified by manager, 2026-07-19)
Commit `771a5ed` (PR #57) rebranded the site: descriptor "Raportul știrilor principale" was
replaced by "Portalul știrilor tale" (live homepage title is now "IZZ.ro — Portalul știrilor
tale"). `tools/smoke_live.py` line 57 still asserts the OLD phrase, so the scheduled
`smoke-live` CI job fails on every run with exactly one violation: `/: descriptorul brand prezent`.

## Goal
In `tools/smoke_live.py`, update ONLY the brand-descriptor check to assert the CURRENT
descriptor "Portalul știrilor tale" on the homepage. Keep the check's message meaningful.
Do not touch any other check, string, or logic.

## Hard rules
- Authorized files: `tools/smoke_live.py` — NOTHING else. Stage only it, by explicit path.
- Minimal diff: one check updated; no refactors, no encoding "fixes", no Node warnings work.

## Acceptance criteria
- `PYTHONIOENCODING=utf-8 python tools/smoke_live.py` (run from repo root, hits live izz.ro)
  → exits 0, output ends with zero violations (baseline before fix: FAIL — 1 incalcari,
  `/: descriptorul brand prezent`). The env var is required on Windows (cp1252 print crash).
- Commit on branch `oc/fix-smoke-brand`, message in English, then STOP — no push, no merge, no PR.

## UNTOUCHABLE (user WIP — never touch, stage, restore, or discard)
- `generator/render.py` (modified, uncommitted)
- `data/entities/salariul-minim.yaml` (modified, uncommitted)
- `specs/**`, `.claude/**` (manager-owned)
