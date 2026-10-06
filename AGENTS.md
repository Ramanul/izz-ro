# AGENTS.md — izz.ro (rules for Devin, OpenCode, and any non-Claude executor agent)

> Read `CLAUDE.md` in this repo root FIRST — it is the full operating contract
> (stack, structure, commands, workflow, domain rules). Everything there applies to you.
> This file only adds the rules specific to your role.

## Which role is yours — read before "Your role: EXECUTOR"

- **Devin, OpenCode, and the `@mistralai` GitHub workflow**: the EXECUTOR role below applies to
  you in full.
- **Mistral Vibe running locally on Alexandru's machine** (terminal or Zed): if you loaded
  `~/.vibe/AGENTS.md` at startup, that file defines your role, communication contract and
  reporting rules, and it **overrides the EXECUTOR section below**. You are the partner in the
  chair, not an executor waiting for a spec. Everything else in this file — branch discipline,
  verify-don't-claim, untouchable files, hard limits — applies to you unchanged.

## The mandate is what the owner asked for, not what landed last in context

Claude sessions get this mechanism injected at startup by a hook; you do not run hooks, so it
is written here. An attachment, a branch name, an open file are MATERIAL, not the task.

- Open any work turn with one line: *"cerut: X. Fac: Y."*
- If Y does not lead to X, say so **then**, in that first line — not afterwards.
- Close with a **cerut vs. livrat** line naming explicitly what part of X went untouched.

Why it is a rule and not an observation: 2026-08-23, a Cloudflare integration was requested; a
script from an attachment was delivered instead — zero calls to Cloudflare, and no warning
either at the start or at the end, while the connector was working the whole time.

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
- Each task = one branch, prefixed by executor: `devin/<short-task-name>` (Devin),
  `oc/<short-task-name>` (OpenCode) — branched from fresh `origin/main`.
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

## Arena — agent AI de dezvoltare, colaborator pe izz.ro (for the MAIN ZCode session; executors may ignore)

"Arena" = an AI development agent (Fable 5.1 Max) that Alexandru works with through chat
in ZCode's in-app browser (login: his `andifreelancer2` account). Agreed roles (5 oct 2026):

- **Arena** = executor on GitHub: branches, code, tests, PRs.
- **Main ZCode session** = Alexandru's representative: verify Arena's work locally, merge to
  `main` (CI deploys), report back to Arena in chat, web research ONLY at Arena's request.
- Flow: Alexandru decides → Arena writes on a branch → ZCode verifies + merges → CI deploys
  → ZCode reports to Arena in chat. Arena's tasks are NEVER executed automatically — they
  wait for an explicit "execută" from Alexandru.
- Limits: Arena's sandbox has NO internet egress; she cannot attach files; she reads only
  api.github.com (no logs).
- **Brief template for NEW Arena tasks — first line mandatory**: „Citește mai întâi
  `docs/colaborare.md` din `Ramanul/izz-ro`; citează SHA-ul fișierului în răspuns."
  Fallback: dacă citirea publică e blocată în sesiunea ei, trimite protocolul condensat
  în brief. Protocolul complet (roluri, 4 stări de verificare, handoff, poarta de merge,
  procedura de repo-conectare): `docs/colaborare.md` pe main.
- Channel mechanics + sensor state: protocolul e în `docs/colaborare.md`; starea live a canalului
  o ține sesiunea principală ZCode (memoria ei locală, nu repo-ul). A ZCode restart kills the
  Arena tab + sensor + beacon server — remount on Alexandru's "reinjectează".

## Economie de context — sesiuni grase (5 oct 2026, după arderea a ~4,8M tokeni/zi)

- Într-o sesiune veche, FIECARE tură re-trimite tot contextul (măsurat: 480k
  tokeni input per rulare la sesiunea senzorului Arena). Continuarea muncii
  "acolo unde a rămas" e operațiunea cea mai scumpă posibilă.
- **Regulă:** sesiune cu tokens.input > 150k NU se mai continuă. Lucrarea se
  transferă prin `handoff/stare-lucrari.md` + memoria proiectului într-o sesiune
  NOUĂ (New task). Sesiunile grase se arhivează din UI (right-click → Archive).
- **Gardian automat:** hook `SessionStart` (~/.zcode/hooks/context_gardian.py,
  în ~/.zcode/cli/config.json) avertizează la orice pornire/reluare despre
  sesiuni > 250k. Raport manual: `Desktop\gardian-context.cmd`.
- **Cronuri recurente:** interval minim orar; munca delegată la subagent ca
  host-ul să rămână subțire; clauză de auto-distrugere la tokens.input > 80k
  (CronDelete pe sine + re-înarmare din sesiune nouă). Niciodată cron < 60 min.
- **Interzis:** scrierea de sesiuni direct în db.sqlite — aplicația le ignoră
  (testat); sesiunile noi se creează doar din UI.
