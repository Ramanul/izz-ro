# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.

**Updated:** 2026-09-05

## Open

- **PR #282 — audit unified hardening:** OPEN, mergeable, branch `audit-unified-hardening-2026-09-05`.
  Current HEAD is the audit-closure branch; K1–K14 have explicit closure status in
  `specs/regim-reguli.md`.
- **CI closure:** after the first CI run exposed missing runtime dependencies, `.github/workflows/ci.yml`
  now installs `requirements.txt` + `requirements-dev.txt`. A second hardening pass makes the grounding
  gate fail closed when its report path is unset or its report is missing. New regression tests cover both cases.
  The final CI result for the latest HEAD must be checked before declaring the repo audit closed.
- **Platform/external controls:** branch protection / required checks, Cloudflare WAF/DNS, operational
  restore/takedown drills, and live verification from proxy-blocked sessions remain external facts.

## Audit closure status

- **K1–K13:** closed in repo with an explicit mechanism and regression coverage where mechanical.
- **K14:** structurally closed; L1 rules are hooked, destructive git operations are denied, and
  control-plane files are protected. It still depends on continued CI enforcement.
- **Grounding:** blocking for deterministic invented quotes and foreign numbers; missing/malformed
  grounding evidence fails closed.
- **Quality/release order:** grounding → QA → commit is enforced in `build.yml`.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`; `COORD-DASHBOARD.md` is historical.

## Standing rules

- Do not treat `izz-ro.pages.dev` as a live origin; Worker origin is the fallback verification path.
- Do not use old task journals or issue #83 as normative coordination channels.
- Do not describe historical benchmark values as current measurements.
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.

## Where the rest lives

`specs/regim-reguli.md` — unified audit closure · `specs/istoric-executie.md` — settled history ·
`specs/registru.tsv` — decisions · `specs/masuratori-frontend.md` — measurements · `CLAUDE.md` — canonical contract.
