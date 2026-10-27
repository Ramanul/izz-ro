# Editorial map and source observation integration

- Goal: combine map lens `96ed1e24` and source observations `d16c7545` over fetched `origin/main` at `c29f7e50` without changing either feature's semantics.
- Inputs: the two committed slices, their specifications, and the publication-filtered data saved on the new base; output: one isolated local branch ready for review and CI.
- Scope: the union of the slices' files plus this specification. Preserve both original commits/worktrees; no config, TTL, synthesis prompts, workflows, production data or service changes.
- Acceptance: reconcile only `specs/STATE.md`, keep its 40-line limit, pass combined relevant Python/Node tests and Ruff, render the full corpus, and verify `/harta/`, `/surse/` and delivered asset versions in the browser.
- Retain the individual performance audits as historical evidence; repeat only if integration introduces a measured interaction. Never convert unknown metadata into zero or truth/reputation scores.
- Output remains local: no push, PR, merge, deployment or live confirmation by this executor.

## Integration evidence

- Cherry-picks: `96ed1e24 -> b82bef22` and `d16c7545 -> 7a6e1722`. The sole conflict was `specs/STATE.md`; all 14 other inherited files are byte-identical to their original slice. Original branches/worktrees remain intact.
- The first combined run found the new STATE summary exceeded the unchanged startup budget (38,296 > 37,888 bytes). The exact startup test passed on isolated `c29f7e50`; shortening only the integration note and updated-date summary restored the guard. No threshold, config or TTL was changed.
- Final combined Python execution: `PYTHONUTF8=1`, all `tests/test_harta*.py`, `test_mini_harta.py`, `test_htmlart_harta.py`, `test_text_observations.py`, `test_render_source_observations.py`, `test_fetch_deep.py`, `test_render_sources.py`, `test_reguli.py`: **313 passed**, including STATE size and startup budget. Node: `node --test tests/harta_confirmation_lens.test.cjs tests/harta_basemap_camera.test.mjs`: **8 passed**, using the existing jsdom installation through NODE_PATH. `python -m ruff check .`: passed.
- Final `python -m generator.main --render-only`, executed after all output-mutating tests: **11,843** visible saved inputs, **15,988 / 17,000** files. Map: **770 articles / 763 events**, measurements for **26 events**; the browser displays **43 measured confirmations**. Sources: **78** statistical rows, **636** eligible first-source URLs, **0 comparisons**, all observation cells `Nemăsurat`. These are current-base snapshot counts, not the older standalone-slice counts.
- Headless Chrome, `/harta/` and `/surse/`, **390 and 1440 px**: no page overflow or script errors; map lens preserves the 763-event count and 42 counties, with 28 unmeasured counties; regional disabling, restoration on a quantitative level, reset and direct query URLs pass. All 78 source rows have six columns and explicit unknown observations.
- Delivered asset bytes match the local output and sources, and HTML references their content versions: map JavaScript `980be45a`, map CSS `e962a980`, common CSS `3c9a66cd`. `data/articles.json` and `data/deep_meta.json` match `c29f7e50` byte-for-byte. The 16-file scope passed a six-pattern credential scan with zero hits; this does not certify arbitrary secret formats.
- No new functional interaction or shared style change was introduced; individual performance audits were not repeated. Their historical corpus/scoring limits remain in the two slice specifications. This integration has no full-suite CI, remote review or live-release evidence. Source observations still accumulate only when selected URLs are genuinely reread, not through periodic polling.

## Publication continuation, 27 October

- Combine this verified local integration with the publication repair at `b2428eec`, retaining its approved 11-day window and HTTP-only live probes. Original worktrees and commits remain preserved.
- Reconcile `specs/STATE.md`; validate the complete combined suite, render, browser behavior, asset versions and current-head CI before integration and live release checks.
- Repair `.github/workflows/editorial-frontend-audit.yml`: its fixed 16–18 October article returns 404 after the approved retention change (all three after-reports in run `40390123283` contain `ERRORED_DOCUMENT_REQUEST`). Render both revisions and pin one actual article route common to both outputs for all six audits. Keep null scores and missing common articles as failures.
- This audit repair changes verification only. It must select the same existing category/slug route on both revisions, exclude map/dossier routes, and fail explicitly if none exists. No score threshold or safety test is relaxed.

## Release and visual probe follow-up

- PR #521 merged as `14ad9f2a`; `tools/verify_release.py` confirmed that exact release on izz.ro and www.izz.ro, with 10,568 articles. The live map preserved 749 events across lens changes and showed 50 measured confirmations across 28/749 events; all 79 source rows displayed six columns and `Nemăsurat`.
- Final local integration: 2,913 Python tests passed, 5 skipped, 8 xfailed; 137 focused tests passed after the content merge, 8 Node tests passed. Render: 16,004/17,000 files. Browser at 390/1,440 px and served asset comparisons passed. Current-head CI and the repaired frontend audit passed. Three-run medians unchanged: home 86/100/100/100; common article 95/100/100/66; home WCAG2AA errors 0/0/0 on both revisions.
- The post-merge visual job `40481966575` selected a real dialectic article but counted zero `.body`/`.official-note` blocks. `tools/visual_check.py` must also accept one direct `.dialectic` content section. Count direct children to avoid counting its nested silence paragraph twice; retain rejection of absent or duplicate content containers. This follow-up changes the visual probe and release documentation only.
- Follow-up local evidence: the exact live article produced old selector count 0 and corrected count 1, with visible attributed facts. Six DOM cases pass (classic summary, official note, dialectic, nested silence, absent and duplicate containers); 100 focused Python tests pass, 1 skipped; Ruff and diff checks pass. Site templates and delivered assets are unchanged.
