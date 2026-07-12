# .claude/agents — project sub-agents for izz.ro

Project-level Claude Code sub-agents, versioned in the repo so every session (local or cloud)
gets the same set. This follows Anthropic's recommended sub-agent setup: each agent has a
**single responsibility**, a **description that drives automatic delegation**, and
**tools scoped to exactly what it needs** (omitting `tools:` would implicitly grant ALL tools —
we never do that here).

## Why sub-agents here

A sub-agent runs in its own context window and returns only a summary to the main thread. The rule
of thumb (from the Anthropic write-up) is: **delegate work that is noisy, bounded, and easy to
summarize.** izz.ro's verification rituals in `CLAUDE.md` are exactly that — they produce a lot of
output (pipeline reports, Lighthouse JSON, article dumps) but the useful result is a short verdict.
Pushing them into sub-agents keeps the main conversation focused on the decision, not the noise.

## The agents

| Agent | Responsibility | Tools | Maps to CLAUDE.md |
|-------|----------------|-------|-------------------|
| `clustering-tuner` | Verify clustering changes empirically (over-merge AND under-merge) on real samples | Read, Grep, Glob, Bash | §7 clustering rule |
| `frontend-auditor` | Run `tools/audit.sh`, report Lighthouse + pa11y deltas before/after | Bash, Read, Grep, Glob | §13 measure, don't eyeball |
| `pipeline-runner` | Run the pipeline safely (`--dry-run` / `--render-only` / `qa_check.py`) and report real output | Bash, Read, Grep, Glob | §5.4 verify by running |
| `editorial-guard` | Read-only review of templates/render against the attribution formula, Zero Zgomot, one-axis, design tokens | Read, Grep, Glob | §7, §8 |

### Tool-scoping rationale

- The three **verifiers** that only need to *measure* (`frontend-auditor`, `pipeline-runner`) and the
  reviewer (`editorial-guard`) get **no Edit/Write** — they report, the human (or main thread) decides
  and drives the change. This is deliberate: CLAUDE.md §13 calls the audit "a compass, not an autopilot".
- `editorial-guard` gets **no Bash** — it is a pure static reviewer of files.
- `clustering-tuner` gets Bash (to run `--dry-run` and throwaway probes in the scratchpad) but **no
  Edit/Write** — per §7 it produces the empirical evidence for a clustering change; it does not make the change.

### Model choice

- Judgment-heavy agents (`clustering-tuner`, `editorial-guard`) use `model: inherit` to match the
  session's model.
- Mechanical run-and-summarize agents (`frontend-auditor`, `pipeline-runner`) pin `model: sonnet` —
  cheaper, and the work is bounded and well-specified.

## Adding a new agent

1. One responsibility per file. If you can't name it in a sentence, it's two agents.
2. Write the `description` so Claude knows *when* to delegate — start with "Use PROACTIVELY when…".
3. List only the tools the agent actually uses. Never leave `tools:` off to "grant everything".
4. Reference real commands and real files (see CLAUDE.md §4) — no invented tooling.
5. Keep it in sync with CLAUDE.md; the house rules live there, the agents just enforce/verify them.

## File format (reference)

```markdown
---
name: agent-name              # lowercase, unique
description: When to use it.   # drives automatic delegation
tools: Read, Grep, Bash        # optional; omit = ALL tools (avoid)
model: inherit                 # optional; inherit | sonnet | opus | haiku
---

System prompt (the agent's instructions) goes here.
```
