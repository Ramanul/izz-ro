# `.codex/` — izz.ro's agent definitions, ported to Codex

Ported on 2026-08-22/23 by an external run (Codex CLI, GLM/z.ai). Corrected on 2026-08-30.
**Nothing here has ever been executed.** Read the two lists below before relying on it.

## What is verified

- The four `agents/*.toml` bodies are **byte-identical** to `.claude/agents/*.md` (measured
  2026-08-30 after undoing the file-name substitution). No content drifted.
- `.claude/agents/` remains the source of truth. When it changes, these copies go stale —
  nothing syncs them.
- The hook installs `requirements.txt` only when the deps are actually missing, and resolves
  the repo root from its own path, so it is machine-independent.

## What is NOT verified — do not assume

- **Whether Codex reads `agents/*.toml` and `hooks.json` at these paths, or in this shape.**
  Codex's own docs (`developers.openai.com/codex/config-*`) are blocked by this environment's
  egress proxy, so the schema could not be confirmed. What *is* confirmed: Codex reads
  `AGENTS.md` as its project instructions, keeps config in `~/.codex/config.toml`, and supports
  project-level lifecycle hooks. If these files turn out to be inert, the content still moves
  as-is into whatever Codex does read.

## The guard that could not be ported

Each Claude Code agent carries a tool allowlist in its frontmatter — `tools: Read, Grep, Glob`
for `editorial-guard`, `tools: Bash, Read, Grep, Glob` for the other three. That allowlist is
what makes them read-only; all four are documented as measuring, never editing.

**Codex has no per-agent equivalent.** Its permission model is `sandbox_mode`
(`read-only` | `workspace-write` | `danger-full-access`) plus `approval_policy`, set per profile,
not per agent. The port dropped the allowlist and replaced it with nothing.

The correction restates the boundary as the first paragraph of every agent's instructions, which
Codex does read. That is weaker than an allowlist — it is a rule the model follows, not a wall it
cannot cross. **Run these agents under `sandbox_mode = "read-only"`**; the paragraph is the
second layer, not the only one.

## Known follow-up outside this directory

`.claude/agents/frontend-auditor.md:23` still points at a `"Current scores"` line in CLAUDE.md
§13. That string has zero occurrences in CLAUDE.md — the baseline moved to
`specs/masuratori-frontend.md` on 2026-08-06. The 2026-08-29 fix (`bf971776`) corrected
`.claude/commands/audit.md` but missed this file. Corrected in the ported copy here; the
original still needs it.
