# Map confirmation lens

## Contract

- Goal: expose the already approved E3 map lens, volume versus measured cross confirmations, without hiding articles or assigning truth/reputation scores.
- Input: the publication-filtered corpus and nonempty `cross_confirmed` domain sets produced by the existing pipeline; output: a measured integer in map JSON and an explicit third color-scale radio alongside volume and per-capita volume.
- Missing, malformed or empty metadata is unknown. A single measured domain is the first report, as in `fetch_deep.cluster_cross_confirmations`, and is explained separately from corroboration across publications.
- Each geographically grouped event uses the maximum measured result from one existing synthesis. A measured single-domain result contributes zero cross confirmations but remains known. Domain sets from different claims are never unioned; event results are counted once even in the article view. Area colors sum these existing measurements, with known/total coverage and a partial-data `+` marker.
- Regional colors delimit editorial regions, not a quantitative scale. The confirmation control is explicitly unavailable at that level; its prior choice is remembered in the address and restored on return to a quantitative level. Region labels/tooltips keep volume counts.
- Acceptance: unknown/one/multiple domains, duplicate domain normalization, grouped events, filters, URL/history/reset, keyboard and UAT/locality details remain coherent; the complete volume/list remains available.
- Files: map producer, standalone map HTML/JS/CSS and focused producer/scale/DOM tests. No synthesis prompt, profile, deploy or external service changes.
- Verification: focused pytest and Node DOM tests, isolated real-data rendering, browser inspection and frontend measurements before publication. Code existence alone is not live evidence.

## Basis and limits

This continues `specs/plan-paradigma-izz.md` E3 (line 151) and the recorded deferral (247–253). P1 (17–21) leaves the choice to the reader; P2 (23–27) distinguishes concordance from independence. These are editorial interpretations of the supplied books, not evidence about the news. No book terminology is added to the interface.

The metric describes the existing deterministic pipeline. It does not establish the truth of a claim, actual editorial independence, or completeness of geographic coverage. A maximum is conservative against double counting; it does not claim that every report in a geographic event corroborates the same fact. Unmeasured old articles stay visible and are not colored as measured zero.

## Local verification, 26 October 2026

- Resumed the existing uncommitted implementation from `codex/izz-map-lens-20261025` onto fresh `origin/main` at `24719a44`; preserved the old worktree and the separate source-observations worktree.
- Browser inspection reproduced mixed units in the county picker: an unmeasured county showed article volume while the map showed an em dash. The new DOM assertions failed with `Brașov · 1` instead of `Brașov · —`; the fix also preserves partial `+` markers and exposes full coverage to assistive technology. Singular/plural wording uses the existing numeral helper.
- `PYTHONUTF8=1 python -m pytest tests/test_harta*.py -q`: 118 passed. UTF-8 mode is required for the existing Python-to-Node numeral test on this Windows host. Four Node DOM tests passed, including direct URLs, history, reset, view changes, partial/unknown measurements, search filters and regional keyboard behavior. Ruff and `git diff --check` passed.
- Current publication-filtered map: 773 articles, 766 events; 26 articles have measured domains, including 21 with at least two. Browser status reports measurement coverage for 26/766 events. This limited coverage is not a claim that other events lack corroboration.
- `tools/audit.sh` completed render-only and audits: home 79/100/100/100, map 66/100/100/100; home pa11y 0 errors. The final JavaScript picker fix was refreshed into the generated assets with matching version references after the render, which started before that fix.
- Three mobile Lighthouse repetitions on the same real map corpus: before performance 68/52/69 (median 68), after 66/66/66 (median 66). Accessibility, best practices and SEO were 100 in all six runs; pa11y WCAG2AA map errors were 0 before and 0 after. Versions: Lighthouse 13.5.0, pa11y 10.0.0, Chrome 156.0.8078.47. The two-point median difference, with a 17-point spread in the baseline, does not establish a performance regression or guarantee identical speed elsewhere.
- No release or live behavior is claimed. Wider reader evaluation and the separate `/surse/` stability slice are not covered by these checks.
